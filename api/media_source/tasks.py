from celery import shared_task
from django.conf import settings
from django.utils.timezone import now

from media_source.models import MediaSource, MediaCollection, MediaContainer
from media_source.services.media_collection_service import MediaCollectionService
from media_source.services.media_container_service import MediaContainerService
from media_source.services.media_source_service import MediaSourceService
from project_ops.constants import AnalyzeStatus
from utils.task_status_service import broadcast_refresh, save_status_and_broadcast


@shared_task
def analyze_media_source_data(media_source_id: int):
    try:
        media_source = MediaSource.objects.get(pk=media_source_id)
    except MediaSource.DoesNotExist:
        print("Not found")
    else:
        if media_source.analyze_status == AnalyzeStatus.ANALYZING:
            print("analyzing already")
            return
        save_status_and_broadcast(
            media_source,
            object_type="MediaSource",
            status=AnalyzeStatus.ANALYZING,
        )
        service = MediaSourceService(media_source)
        try:
            service.sync_collection()
        except Exception as e:
            print(e)
            status = AnalyzeStatus.COMPLETE_WITH_ERRORS
        else:
            status = AnalyzeStatus.COMPLETE
            media_source.analyzed_at = now()
        save_status_and_broadcast(
            media_source,
            object_type="MediaSource",
            status=status,
        )
        broadcast_refresh("MediaCollection")


@shared_task
def analyze_media_collection_data(media_collection_id: int, force: bool = False):
    try:
        media_collection = MediaCollection.objects.get(pk=media_collection_id)
    except MediaCollection.DoesNotExist:
        print("Not found")
    else:
        if media_collection.analyze_status == AnalyzeStatus.ANALYZING:
            print("analyzing already")
            return
        save_status_and_broadcast(
            media_collection,
            object_type="MediaCollection",
            status=AnalyzeStatus.ANALYZING,
        )
        service = MediaCollectionService(media_collection)
        try:
            print("retrieve data")
            service.load_collection_data()
            print("normalize & clean up")
            service.analyze_collection_data(
                use_llm=settings.MEDIA_CONTAINER_ANALYSE_USE_LLM,
                new_data_only=not force,
            )
            print("done")
        except Exception as e:
            print(e)
            status = AnalyzeStatus.COMPLETE_WITH_ERRORS
        else:
            status = AnalyzeStatus.COMPLETE
            media_collection.analyzed_at = now()
        save_status_and_broadcast(
            media_collection,
            object_type="MediaCollection",
            status=status,
        )
        broadcast_refresh("MediaContainer")


@shared_task
def analyze_media_container_data(media_container_id: int):
    try:
        instance = MediaContainer.objects.get(pk=media_container_id)
    except MediaCollection.DoesNotExist:
        print("Not found")
    else:
        if instance.analyze_status == AnalyzeStatus.ANALYZING:
            print("analyzing already")
            return
        save_status_and_broadcast(
            instance,
            object_type="MediaContainer",
            status=AnalyzeStatus.ANALYZING,
        )

        try:
            service = MediaContainerService(media_container=instance)
            instance = service.normalize_data(use_llm=settings.MEDIA_CONTAINER_ANALYSE_USE_LLM)
        except Exception as exc:
            print(exc)
            status = AnalyzeStatus.COMPLETE_WITH_ERRORS
        else:
            status = AnalyzeStatus.COMPLETE
        save_status_and_broadcast(
            instance,
            object_type="MediaContainer",
            status=status,
        )


@shared_task
def analyze_all_media_container_data():
    queryset = MediaContainer.objects.all()
    queryset.update(analyze_status=AnalyzeStatus.IDLE)

    instances = list(queryset)
    if not instances:
        return

    for instance in instances:
        instance.analyze_status = AnalyzeStatus.ANALYZING
    MediaContainer.objects.bulk_update(instances, ["analyze_status"])
    broadcast_refresh("MediaContainer")

    current_time = now()
    processed_instances: list[MediaContainer] = []
    for instance in instances:
        try:
            service = MediaContainerService(media_container=instance)
            instance = service.normalize_data(use_llm=settings.MEDIA_CONTAINER_ANALYSE_USE_LLM)
        except Exception as exc:
            print(exc)
            instance.analyze_status = AnalyzeStatus.COMPLETE_WITH_ERRORS
        else:
            instance.analyze_status = AnalyzeStatus.COMPLETE
            instance.analyzed_at = current_time
        processed_instances.append(instance)

    MediaContainer.objects.bulk_update(
        processed_instances,
        ["categories", "analyze_status", "analyzed_at"],
    )
    broadcast_refresh("MediaContainer")


@shared_task
def analyze_active_media_collections():
    collection_ids = list(
        MediaCollection.objects
        .filter(is_active=True)
        .values_list("id", flat=True)
    )

    for media_collection_id in collection_ids:
        try:
            analyze_media_collection_data(media_collection_id)
        except Exception as exc:
            print(exc)
