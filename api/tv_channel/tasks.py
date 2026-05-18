import logging

from celery import shared_task

from grid_schedule.services.tv_schedule_service import TvPlayoutGenerationService
from project_ops.constants import AnalyzeStatus
from tv_channel.models import Catalog, TvChannel
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
