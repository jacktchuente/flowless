import logging

from celery import shared_task

from editorial_flow.configs import SegmentationConfig
from editorial_planning.models import EditorialFlowRun
from editorial_planning.services.generation_service import EditorialPlanningGenerationService
from editorial_planning.services.matching_service import EditorialPlanningMatchingService
from project_ops.constants import AnalyzeStatus
from tv_channel.models import Catalog
from utils.task_status_service import broadcast_refresh, save_status_and_broadcast

logger = logging.getLogger(__name__)


@shared_task
def generate_editorial_planning(
    catalog_id: int,
    media_collection_ids: list[int],
    max_channel_candidates: int | None = None,
    target_channel_count: int | None = None,
    allow_multi_segment: bool = True,
):
    try:
        catalog = Catalog.objects.get(pk=catalog_id)
    except Catalog.DoesNotExist:
        logger.warning("generate_editorial_planning skipped unknown catalog_id=%s", catalog_id)
        return

    if catalog.analyze_status == AnalyzeStatus.ANALYZING:
        logger.info("generate_editorial_planning skipped catalog_id=%s already_analyzing=true", catalog_id)
        return

    save_status_and_broadcast(catalog, object_type="Catalog", status=AnalyzeStatus.ANALYZING)
    try:
        EditorialPlanningGenerationService(
            catalog=catalog,
            media_collection_ids=media_collection_ids,
            max_channel_candidates=max_channel_candidates,
            target_channel_count=target_channel_count,
            segmentation_config=SegmentationConfig(allow_multi_segment=allow_multi_segment),
        ).generate()
    except Exception:
        logger.exception("generate_editorial_planning failed catalog_id=%s", catalog_id)
        status = AnalyzeStatus.COMPLETE_WITH_ERRORS
    else:
        status = AnalyzeStatus.COMPLETE

    save_status_and_broadcast(catalog, object_type="Catalog", status=status)
    broadcast_refresh("EditorialFlowRun")
    broadcast_refresh("EditorialChannelCandidate")


@shared_task
def match_new_media_to_editorial_run(run_id: int):
    try:
        run = EditorialFlowRun.objects.get(pk=run_id)
    except EditorialFlowRun.DoesNotExist:
        logger.warning("match_new_media_to_editorial_run skipped unknown run_id=%s", run_id)
        return

    try:
        result = EditorialPlanningMatchingService(run=run).match_new_media()
    except Exception:
        logger.exception("match_new_media_to_editorial_run failed run_id=%s", run_id)
    else:
        logger.info(
            "match_new_media_to_editorial_run completed run_id=%s evaluated=%s accepted=%s "
            "secondary=%s ambiguous=%s rejected=%s created_memberships=%s",
            run_id,
            result.evaluated_count,
            result.accepted_count,
            result.secondary_count,
            result.ambiguous_count,
            result.rejected_count,
            result.created_membership_count,
        )

    broadcast_refresh("EditorialFlowRun")
    broadcast_refresh("EditorialChannelCandidate")
