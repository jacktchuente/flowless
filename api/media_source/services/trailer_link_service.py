import logging

from django.db.models import QuerySet

from media_source.constants import MediaProgrammingRole
from media_source.models import MediaContainer, MediaItem

logger = logging.getLogger(__name__)


class TrailerLinkService:
    """Links trailer containers to the media they advertise.

    Convention: trailer collections (programming_role=TRAILER) come from a
    Jellyfin "Shows" library where each folder is named after an identifier
    of the target media - its Jellyfin GUID or a provider id (raw "12345"
    or prefixed "tmdb-12345"). Each video inside the folder is a potential
    trailer for that media.
    """

    def __init__(self):
        self._title_index: dict[str, list[int]] | None = None

    def find_trailer_items(self, target_container: MediaContainer) -> QuerySet[MediaItem]:
        index = self._get_title_index()
        keys = self._target_keys(target_container)
        container_ids = sorted({
            container_id
            for key in keys
            for container_id in index.get(key, [])
        })
        return (
            MediaItem.objects
            .filter(container_id__in=container_ids, duration_seconds__gt=0)
            .order_by("id")
        )

    def find_target_for_trailer_container(self, trailer_container: MediaContainer) -> MediaContainer | None:
        key = self._normalize(trailer_container.title)
        if not key:
            return None
        for candidate in (
            MediaContainer.objects
            .filter(external_id__iexact=key)
            .exclude(media_collection__programming_role=MediaProgrammingRole.TRAILER)
        ):
            return candidate
        raw_key = key.split("-", 1)[-1]
        for candidate in (
            MediaContainer.objects
            .exclude(media_collection__programming_role=MediaProgrammingRole.TRAILER)
            .exclude(provider_ids={})
        ):
            if key in self._provider_keys(candidate) or raw_key in self._provider_keys(candidate):
                return candidate
        return None

    def _get_title_index(self) -> dict[str, list[int]]:
        if self._title_index is None:
            index: dict[str, list[int]] = {}
            trailer_containers = (
                MediaContainer.objects
                .filter(
                    media_collection__programming_role=MediaProgrammingRole.TRAILER,
                    media_collection__is_active=True,
                )
                .values_list("id", "title")
            )
            for container_id, title in trailer_containers:
                key = self._normalize(title)
                if key:
                    index.setdefault(key, []).append(container_id)
            self._title_index = index
        return self._title_index

    @classmethod
    def _target_keys(cls, container: MediaContainer) -> set[str]:
        keys = {cls._normalize(container.external_id)}
        keys.update(cls._provider_keys(container))
        keys.discard("")
        return keys

    @classmethod
    def _provider_keys(cls, container: MediaContainer) -> set[str]:
        keys: set[str] = set()
        provider_ids = container.provider_ids or {}
        for provider, value in provider_ids.items():
            keys.add(cls._normalize(value))
            keys.add(cls._normalize(f"{provider}-{value}"))
        keys.discard("")
        return keys

    @staticmethod
    def _normalize(value) -> str:
        if value is None:
            return ""
        return str(value).strip().lower()
