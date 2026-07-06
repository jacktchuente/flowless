import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Max, Q
from django.utils import timezone

from grid_schedule.models import ScheduleMediaItem, TvPlayout
from grid_schedule.services.flexible_tv_schedule_service import FlexibleTvPlayoutGenerationService
from grid_schedule.services.tv_schedule_service import TvPlayoutGenerationService
from project_ops.constants import AnalyzeStatus
from tv_channel.models import Catalog, GridLayoutMode, TvChannel
from tv_channel.services.catalog_service import CatalogService
from tv_channel.services.etv_channel_push_service import EtvChannelPushService
from tv_channel.services.tv_channel_service import TvChannelService
from utils.task_status_service import broadcast_refresh, save_status_and_broadcast

logger = logging.getLogger(__name__)


@shared_task
def generate_catalog_channels(catalog_id: int, reboot: bool = False):
    try:
        catalog = Catalog.objects.get(pk=catalog_id)
    except Catalog.DoesNotExist:
        return
    if catalog.analyze_status == AnalyzeStatus.ANALYZING:
        print("already analyzing")
        return
    save_status_and_broadcast(
        catalog,
        object_type="Catalog",
        status=AnalyzeStatus.ANALYZING,
    )
    service = CatalogService(catalog=catalog)
    try:
        service.generate_channels(reboot=reboot)
    except Exception as exc:
        print(exc)
        status = AnalyzeStatus.COMPLETE_WITH_ERRORS
    else:
        status = AnalyzeStatus.COMPLETE
    save_status_and_broadcast(
        catalog,
        object_type="Catalog",
        status=status,
    )
    broadcast_refresh("TvChannel")


@shared_task
def generate_channel_editorial_line(
    channel_id: int,
    grid_generation_mode: str = TvChannelService.GRID_GENERATION_MODE_FULL_LLM,
    reboot: bool = False,
    regenerate_editorial_line: bool = False,
):
    try:
        instance = TvChannel.objects.get(pk=channel_id)
    except TvChannel.DoesNotExist:
        return
    if instance.analyze_status == AnalyzeStatus.ANALYZING:
        print("already analyzing")
        return
    save_status_and_broadcast(
        instance,
        object_type="TvChannel",
        status=AnalyzeStatus.ANALYZING,
    )
    service = TvChannelService(tv_channel=instance)

    try:
        service.generate_editorial_line_and_grid(
            grid_generation_mode=grid_generation_mode,
            reboot=reboot,
            regenerate_editorial_line=regenerate_editorial_line,
        )
    except Exception as e:
        print(e)
        status = AnalyzeStatus.COMPLETE_WITH_ERRORS
    else:
        status = AnalyzeStatus.COMPLETE
    save_status_and_broadcast(
        instance,
        object_type="TvChannel",
        status=status,
    )


@shared_task
def generate_tv_channel_playout(
    channel_id: int,
    days: int = 1,
    reset: bool = False,
):
    logger.info(
        "generate_tv_channel_playout started channel_id=%s days=%s reset=%s",
        channel_id,
        days,
        reset,
    )
    try:
        instance = TvChannel.objects.get(pk=channel_id)
    except TvChannel.DoesNotExist:
        logger.warning("generate_tv_channel_playout skipped unknown channel_id=%s", channel_id)
        return

    if instance.analyze_status == AnalyzeStatus.ANALYZING:
        logger.info("generate_tv_channel_playout skipped channel_id=%s already_analyzing=true", channel_id)
        return
    save_status_and_broadcast(
        instance,
        object_type="TvChannel",
        status=AnalyzeStatus.ANALYZING,
    )
    try:
        active_grid = (
            instance.gridlayout_set.filter(is_active=True)
            .only("id", "mode")
            .order_by("-created_at", "-id")
            .first()
        )
        if active_grid is not None and active_grid.mode == GridLayoutMode.FLEXIBLE:
            service = FlexibleTvPlayoutGenerationService(
                tv_channel=instance,
                days=days,
                reset=reset,
            )
        else:
            service = TvPlayoutGenerationService(
                tv_channel=instance,
                days=days,
                reset=reset,
            )
        result = service.generate()
    except Exception as exc:
        logger.exception(
            "generate_tv_channel_playout failed channel_id=%s days=%s reset=%s",
            channel_id,
            days,
            reset,
        )
        status = AnalyzeStatus.COMPLETE_WITH_ERRORS
    else:
        logger.info(
            "generate_tv_channel_playout completed channel_id=%s playout_id=%s created=%s generated_items=%s warnings=%s",
            channel_id,
            result.tv_playout.id,
            result.created,
            result.generated_items,
            len(result.warnings),
        )
        status = AnalyzeStatus.COMPLETE

    save_status_and_broadcast(
        instance,
        object_type="TvChannel",
        status=status,
    )


@shared_task
def extend_channel_playouts():
    """Keeps channels programmed ahead of time, whatever the grid mode.

    For each enabled channel with an active grid layout and an existing
    active playout, the playout is regenerated when its horizon (last
    scheduled end) drops below DAYS_TO_BUILD days from now; the generation
    task dispatches to the flexible or standard service according to the
    layout mode. Channels that were never generated stay untouched (first
    generation remains a manual decision), and the ErsatzTV push stays
    manual too.
    """
    horizon_target = timezone.now() + timedelta(days=settings.DAYS_TO_BUILD)
    channels = (
        TvChannel.objects.filter(
            is_enabled=True,
            gridlayout__is_active=True,
        )
        .distinct()
    )
    for channel in channels:
        playout = TvPlayout.objects.filter(tv_channel=channel, is_active=True).first()
        if playout is None:
            continue
        last_end = ScheduleMediaItem.objects.filter(
            Q(flexible_selection__tv_playout=playout)
            | Q(block_container_selection__tv_playout=playout),
        ).aggregate(value=Max("ends_at"))["value"]
        if last_end is None or last_end >= horizon_target:
            continue
        logger.info(
            "extend_channel_playouts channel_id=%s horizon=%s target=%s",
            channel.id,
            last_end,
            horizon_target,
        )
        generate_tv_channel_playout.delay(channel.id, days=settings.DAYS_TO_BUILD, reset=False)


@shared_task
def push_tv_channel_to_etv(channel_id: int):
    try:
        instance = TvChannel.objects.get(pk=channel_id)
    except TvChannel.DoesNotExist:
        return

    if instance.analyze_status == AnalyzeStatus.ANALYZING:
        print("already analyzing")
        return

    save_status_and_broadcast(
        instance,
        object_type="TvChannel",
        status=AnalyzeStatus.ANALYZING,
    )

    try:
        EtvChannelPushService(tv_channel=instance).run()
    except Exception as exc:
        print(exc)
        status = AnalyzeStatus.COMPLETE_WITH_ERRORS
    else:
        status = AnalyzeStatus.COMPLETE

    save_status_and_broadcast(
        instance,
        object_type="TvChannel",
        status=status,
    )
