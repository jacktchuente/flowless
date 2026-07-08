import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Max, Q
from django.utils import timezone

from grid_schedule.models import PlayoutGenerationReport, ScheduleMediaItem, TvPlayout
from grid_schedule.services.flexible_tv_schedule_service import FlexibleTvPlayoutGenerationService
from grid_schedule.services.tv_schedule_service import TvPlayoutGenerationService
from project_ops.constants import AnalyzeStatus
from tv_channel.models import Catalog, GridLayoutMode, TvChannel
from tv_channel.services.catalog_service import CatalogService
from tv_channel.services.etv_channel_push_service import EtvChannelPushService
from tv_channel.services.logo_generation import LogoGenerationService
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
    trigger: str = PlayoutGenerationReport.TRIGGER_GENERATE,
):
    logger.info(
        "generate_tv_channel_playout started channel_id=%s days=%s reset=%s trigger=%s",
        channel_id,
        days,
        reset,
        trigger,
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
        extend = trigger == PlayoutGenerationReport.TRIGGER_EXTEND
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
                extend=extend,
            )
        else:
            service = TvPlayoutGenerationService(
                tv_channel=instance,
                days=days,
                reset=reset,
                extend=extend,
            )
        result = service.generate()
    except Exception as exc:
        logger.exception(
            "generate_tv_channel_playout failed channel_id=%s days=%s reset=%s",
            channel_id,
            days,
            reset,
        )
        _save_generation_report(instance, trigger=trigger, error=exc)
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
        _save_generation_report(instance, trigger=trigger, result=result)
        status = AnalyzeStatus.COMPLETE

    save_status_and_broadcast(
        instance,
        object_type="TvChannel",
        status=status,
    )


def _save_generation_report(instance: TvChannel, *, trigger: str, result=None, error=None) -> None:
    try:
        if result is not None:
            issues = [
                {
                    "code": "generation",
                    "severity": "warning",
                    "message": warning,
                    "schedule_item_id": None,
                    "starts_at": None,
                    "ends_at": None,
                }
                for warning in result.warnings
            ] + list(result.issues)
            PlayoutGenerationReport.objects.create(
                tv_playout=result.tv_playout,
                trigger=trigger,
                window_start=result.window_start,
                window_end=result.window_end,
                generated_items=result.generated_items,
                filled_items=result.filled_items,
                repaired_gaps=result.repaired_gaps,
                trimmed_overlaps=result.trimmed_overlaps,
                issues=issues,
            )
            return

        playout = TvPlayout.objects.filter(tv_channel=instance, is_active=True).first()
        if playout is None:
            return
        PlayoutGenerationReport.objects.create(
            tv_playout=playout,
            trigger=trigger,
            issues=[
                {
                    "code": "generation_failed",
                    "severity": "error",
                    "message": str(error),
                    "schedule_item_id": None,
                    "starts_at": None,
                    "ends_at": None,
                }
            ],
        )
    except Exception:
        logger.exception("Failed to persist generation report channel_id=%s", instance.id)


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
        last_end = _get_playout_last_end(playout)
        if last_end is None or last_end >= horizon_target:
            continue
        logger.info(
            "extend_channel_playouts channel_id=%s horizon=%s target=%s",
            channel.id,
            last_end,
            horizon_target,
        )
        generate_tv_channel_playout.delay(
            channel.id,
            days=settings.DAYS_TO_BUILD,
            reset=False,
            trigger=PlayoutGenerationReport.TRIGGER_EXTEND,
        )


def _get_playout_last_end(playout: TvPlayout):
    bounds = ScheduleMediaItem.objects.filter(
        Q(flexible_selection__tv_playout=playout)
        | Q(block_container_selection__tv_playout=playout)
        | Q(parent_schedule_item__flexible_selection__tv_playout=playout)
        | Q(parent_schedule_item__block_container_selection__tv_playout=playout),
    ).aggregate(
        ends_at=Max("ends_at"),
        post_roll_filler_ends_at=Max("post_roll_filler_ends_at"),
    )
    values = [value for value in bounds.values() if value is not None]
    return max(values) if values else None


@shared_task
def generate_tv_channel_logo(channel_id: int, backend: str | None = None):
    try:
        instance = TvChannel.objects.get(pk=channel_id)
    except TvChannel.DoesNotExist:
        logger.warning("generate_tv_channel_logo skipped unknown channel_id=%s", channel_id)
        return

    if instance.analyze_status == AnalyzeStatus.ANALYZING:
        logger.info("generate_tv_channel_logo skipped channel_id=%s already_analyzing=true", channel_id)
        return

    save_status_and_broadcast(
        instance,
        object_type="TvChannel",
        status=AnalyzeStatus.ANALYZING,
    )
    try:
        LogoGenerationService(instance, backend=backend).generate()
    except Exception:
        logger.exception(
            "generate_tv_channel_logo failed channel_id=%s backend=%s",
            channel_id,
            backend,
        )
        status = AnalyzeStatus.COMPLETE_WITH_ERRORS
    else:
        logger.info("generate_tv_channel_logo completed channel_id=%s", channel_id)
        status = AnalyzeStatus.COMPLETE

    save_status_and_broadcast(
        instance,
        object_type="TvChannel",
        status=status,
    )


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
