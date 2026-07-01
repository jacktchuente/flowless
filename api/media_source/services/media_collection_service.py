from django.utils.timezone import now

from media_source.constants import MediaContainerKind
from media_source.models import MediaCollection, MediaContainer, MediaSource, MediaItem
from media_source.services.media_container_service import MediaContainerService
from media_source.services.media_server_services.jellyfin_service import JellyfinService, MediaServerMediaContainer
from project_ops.constants import AnalyzeStatus
from utils.hash_data import hash_data


class MediaCollectionService:
    CONTAINER_KIND_MAP = {
        "movie": MediaContainerKind.STANDALONE_VIDEO,
        "series": MediaContainerKind.SERIES,
        "music_release": MediaContainerKind.MUSIC_RELEASE,
        "music_video_release": MediaContainerKind.MUSIC_VIDEO_RELEASE,
        "other": MediaContainerKind.OTHER,
    }

    def __init__(self, media_collection: MediaCollection):
        self.media_collection = media_collection

    @classmethod
    def _resolve_collection_container_kind(cls, medias: list[MediaServerMediaContainer]):
        for media in medias:
            container_kind = media.get("container_kind")
            if container_kind in cls.CONTAINER_KIND_MAP:
                return cls.CONTAINER_KIND_MAP[container_kind]
        return None

    def load_collection_data(self):
        media_source = self.media_collection.media_source

        jellyfin_service = JellyfinService(
            credentials=media_source.credentials,
        )

        medias = jellyfin_service.get_media(
            self.media_collection.external_id,
        )

        existing_medias_by_external_id = {
            media.external_id: media
            for media in MediaContainer.objects.filter(
                media_source=media_source,
                media_collection=self.media_collection,
            )
        }

        existing_external_ids = set(existing_medias_by_external_id.keys())

        found_external_ids = {
            media["external_id"]
            for media in medias
        }

        missing_external_ids = existing_external_ids - found_external_ids

        collection_container_kind = self._resolve_collection_container_kind(medias)
        if self.media_collection.container_kind != collection_container_kind:
            self.media_collection.container_kind = collection_container_kind
            self.media_collection.save(update_fields=["container_kind"])

        self.manage_media_containers(medias, missing_external_ids, media_source, existing_medias_by_external_id)
        self.manage_media_items(
            medias=medias,
            media_source=media_source,
        )

    def manage_media_containers(self,
                                medias: list[MediaServerMediaContainer],
                                missing_external_ids: set[str],
                                media_source: MediaSource,
                                existing_medias_by_external_id
                                ):
        media_to_create = []
        media_to_update = []

        for media in medias:
            payload = {
                "external_id": media["external_id"],
                "title": (media.get("title") or "")[:255],
                "description": media.get("description"),
                "categories": media.get("categories", []),
                "item_count": media.get("item_count"),
                "duration_min_seconds": media.get("duration_min_seconds"),
                "duration_max_seconds": media.get("duration_max_seconds"),
                "total_duration_seconds": media.get("total_duration_seconds"),
                "min_video_width": media.get("min_video_width"),
                "min_video_height": media.get("min_video_height"),
                "min_age": media.get("min_age"),
                "max_age": media.get("max_age"),
                "release_date": media.get("release_date"),
                "release_date_start": media.get("release_date_start"),
                "release_date_end": media.get("release_date_end"),
                "release_year_min": media.get("release_year_min"),
                "release_year_max": media.get("release_year_max"),
                "countries": media.get("countries", []),
                "audio_languages": media.get("audio_languages", []),
                "subtitle_languages": media.get("subtitle_languages", []),
                "audio_languages_any": media.get("audio_languages_any", []),
                "subtitle_languages_any": media.get("subtitle_languages_any", []),
                "community_rating_score": media.get("community_rating_score"),
                "critic_rating_score": media.get("critic_rating_score"),
                "overall_rating_score": media.get("overall_rating_score"),
                "people": media.get("people", []),
                "directors": media.get("directors", []),
                "writers": media.get("writers", []),
                "creators": media.get("creators", []),
                "actors": media.get("actors", []),
                "studios": media.get("studios", []),
                "tags": media.get("tags", []),
                "genres": media.get("genres", []),
            }

            original_data_hash = hash_data(payload)

            existing_media = existing_medias_by_external_id.get(
                media["external_id"],
            )

            if existing_media is None:
                media_to_create.append(
                    MediaContainer(
                        **payload,
                        media_source=media_source,
                        media_collection=self.media_collection,
                        is_missing=False,
                        original_data_hash=original_data_hash,
                        raw_data=media.get("raw_metadata", payload),
                    )
                )
                continue

            if (existing_media.original_data_hash == original_data_hash and existing_media.is_missing is False):
                continue

            for field, value in payload.items():
                setattr(existing_media, field, value)

            existing_media.is_missing = False
            existing_media.original_data_hash = original_data_hash
            existing_media.raw_data = media.get("raw_metadata", payload)

            media_to_update.append(existing_media)

        if media_to_create:
            MediaContainer.objects.bulk_create(media_to_create, ignore_conflicts=True)

        if media_to_update:
            MediaContainer.objects.bulk_update(
                media_to_update,
                [
                    "title",
                    "description",
                    "categories",
                    "item_count",
                    "duration_min_seconds",
                    "duration_max_seconds",
                    "total_duration_seconds",
                    "min_video_width",
                    "min_video_height",
                    "min_age",
                    "max_age",
                    "release_date",
                    "release_date_start",
                    "release_date_end",
                    "release_year_min",
                    "release_year_max",
                    "countries",
                    "audio_languages",
                    "subtitle_languages",
                    "audio_languages_any",
                    "subtitle_languages_any",
                    "community_rating_score",
                    "critic_rating_score",
                    "overall_rating_score",
                    "people",
                    "directors",
                    "writers",
                    "creators",
                    "actors",
                    "studios",
                    "tags",
                    "genres",
                    "is_missing",
                    "original_data_hash",
                    "raw_data",
                ],
            )

        if missing_external_ids:
            MediaContainer.objects.filter(
                media_source=media_source,
                media_collection=self.media_collection,
                external_id__in=missing_external_ids,
            ).update(is_missing=True)

    def manage_media_items(
            self,
            medias: list[MediaServerMediaContainer],
            media_source: MediaSource,
    ):

        media_item_update_fields = [
            "container",
            "title",
            "description",
            "item_kind",
            "duration_seconds",
            "sequence_number",
            "season_number",
            "episode_number",
            "min_age",
            "max_age",
            "release_date",
            "release_year",
            "countries",
            "audio_languages",
            "subtitle_languages",
            "video_width",
            "video_height",
            "community_rating_score",
            "critic_rating_score",
            "overall_rating_score",
            "tags",
            "genres",
            "people",
            "directors",
            "writers",
            "creators",
            "actors",
            "studios",
            "is_missing",
            "original_data_hash",
            "raw_data",
        ]
        containers_by_external_id = {
            container.external_id: container
            for container in MediaContainer.objects.filter(
                media_source=media_source,
                media_collection=self.media_collection,
            )
        }

        existing_items_by_external_id = {
            item.external_id: item
            for item in MediaItem.objects.filter(
                media_source=media_source,
                container__media_collection=self.media_collection,
            ).select_related("container")
        }

        found_item_external_ids = {
            item["external_id"]
            for media in medias
            for item in media.get("items", [])
            if item.get("external_id")
        }

        existing_item_external_ids = set(existing_items_by_external_id.keys())

        missing_item_external_ids = existing_item_external_ids - found_item_external_ids

        item_to_create = []
        item_to_update = []

        for media in medias:
            container = containers_by_external_id.get(media["external_id"])

            if container is None:
                continue

            for item in media.get("items", []):
                external_id = item.get("external_id")

                if not external_id:
                    continue

                payload = {
                    "external_id": external_id,
                    "title": (item.get("title") or "")[:255],
                    "description": item.get("description"),
                    "item_kind": item.get("item_kind"),
                    "duration_seconds": item.get("duration_seconds"),
                    "sequence_number": item.get("sequence_number"),
                    "season_number": item.get("season_number"),
                    "episode_number": item.get("episode_number"),
                    "min_age": item.get("min_age"),
                    "max_age": item.get("max_age"),
                    "release_date": item.get("release_date"),
                    "release_year": item.get("release_year"),
                    "countries": item.get("countries", []),
                    "audio_languages": item.get("audio_languages", []),
                    "subtitle_languages": item.get("subtitle_languages", []),
                    "video_width": item.get("video_width"),
                    "video_height": item.get("video_height"),
                    "community_rating_score": item.get("community_rating_score"),
                    "critic_rating_score": item.get("critic_rating_score"),
                    "overall_rating_score": item.get("overall_rating_score"),
                    "tags": item.get("tags", []),
                    "genres": item.get("genres", []),
                    "people": item.get("people", []),
                    "directors": item.get("directors", []),
                    "writers": item.get("writers", []),
                    "creators": item.get("creators", []),
                    "actors": item.get("actors", []),
                    "studios": item.get("studios", []),
                }

                hash_payload = {
                    **payload,
                }

                original_data_hash = hash_data(hash_payload)

                existing_item = existing_items_by_external_id.get(external_id)

                if existing_item is None:
                    item_to_create.append(
                        MediaItem(
                            **payload,
                            container=container,
                            media_source=media_source,
                            is_missing=False,
                            original_data_hash=original_data_hash,
                            raw_data=item.get("raw_metadata", payload),
                        )
                    )
                    continue

                if (
                        existing_item.original_data_hash == original_data_hash
                        and existing_item.is_missing is False
                        and existing_item.container_id == container.id
                ):
                    continue

                for field, value in payload.items():
                    setattr(existing_item, field, value)

                existing_item.container = container
                existing_item.is_missing = False
                existing_item.original_data_hash = original_data_hash
                existing_item.raw_data = item.get("raw_metadata", payload)

                item_to_update.append(existing_item)

        if item_to_create:
            MediaItem.objects.bulk_create(
                item_to_create,
                ignore_conflicts=True,
            )

        if item_to_update:
            MediaItem.objects.bulk_update(
                item_to_update,
                media_item_update_fields,
            )

        if missing_item_external_ids:
            MediaItem.objects.filter(
                media_source=media_source,
                container__media_collection=self.media_collection,
                external_id__in=missing_item_external_ids,
            ).update(is_missing=True)

    def analyze_collection_data(self, use_llm=False, new_data_only=True):
        media_containers_qs = MediaContainer.objects.filter(
            media_collection=self.media_collection
        )

        if new_data_only:
            media_containers_qs = media_containers_qs.filter(analyze_status=AnalyzeStatus.IDLE)

        media_containers = list(media_containers_qs)
        MediaContainer.objects.filter(id__in=[element.id for element in media_containers]).update(
            analyze_status=AnalyzeStatus.ANALYZING,
        )

        objs = []

        for element in media_containers:
            service = MediaContainerService(media_container=element)
            try:
                instance = service.normalize_data(use_llm=use_llm)
            except Exception as e:
                print(e)
                instance = element
                instance.analyze_status = AnalyzeStatus.COMPLETE_WITH_ERRORS
            else:
                instance.analyze_status = AnalyzeStatus.COMPLETE
            instance.analyzed_at = now()
            objs.append(instance)
        MediaContainer.objects.bulk_update(objs, fields=['categories', "analyze_status", "analyzed_at"])
