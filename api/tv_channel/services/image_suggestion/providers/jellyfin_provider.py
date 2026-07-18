from __future__ import annotations

import logging

import requests
from django.conf import settings

from grid_schedule.services import editorial_matching
from media_source.models import MediaContainer, MediaSource
from media_source.services.media_server_services.jellyfin_service import JellyfinService
from project_ops.constants import AnalyzeStatus
from tv_channel.models import ChannelImageEntityType
from tv_channel.services.image_suggestion.providers.base import ImageResult, ImageSearchProvider
from tv_channel.services.image_suggestion.query_service import ImageQuery

logger = logging.getLogger(__name__)


class JellyfinImageProvider(ImageSearchProvider):
    name = "jellyfin"

    THUMBNAIL_WIDTH = 400
    # Marge sur la limite: certains items n'ont pas de backdrop.
    ITEMS_FETCH_FACTOR = 4

    def __init__(self, tv_channel):
        super().__init__(tv_channel)
        self.media_source = MediaSource.objects.filter(is_active=True).order_by("id").first()
        self._service: JellyfinService | None = None
        self._token: str | None = None
        self._user_id: str | None = None

    def is_available(self) -> bool:
        return self.media_source is not None

    def search(self, query: ImageQuery, limit: int) -> list[ImageResult]:
        self._ensure_authenticated()
        if query.entity_type == ChannelImageEntityType.STUDIO:
            return self._search_by_entity(query, limit, path="/Studios", items_filter="studioIds")
        if query.entity_type == ChannelImageEntityType.PERSON:
            return self._search_by_entity(query, limit, path="/Persons", items_filter="personIds")
        return self._search_theme(limit)

    def download(self, url: str) -> bytes:
        self._ensure_authenticated()
        response = requests.get(
            url,
            headers={"X-Emby-Token": self._token},
            timeout=30,
        )
        response.raise_for_status()
        return response.content

    def _ensure_authenticated(self) -> None:
        if self._token is not None:
            return
        if self.media_source is None:
            raise ValueError("No active media source for the Jellyfin image provider.")
        self._service = JellyfinService(credentials=self.media_source.credentials)
        self._token, self._user_id = self._service._authenticate()

    def _search_by_entity(self, query: ImageQuery, limit: int, *, path: str, items_filter: str) -> list[ImageResult]:
        payload = self._service._request(
            self._token,
            path,
            {"searchTerm": query.query, "limit": 3, "userId": self._user_id},
        )
        entities = payload.get("Items") or []
        results: list[ImageResult] = []

        # 1. Image propre de l'entite (logo du studio / portrait de la personne)
        for entity in entities:
            if len(results) >= limit:
                return results
            if (entity.get("ImageTags") or {}).get("Primary"):
                results.append(self._image_result(entity, image_type="Primary", attribution=entity.get("Name", "")))

        # 2. Backdrops des titres rattaches a la premiere entite trouvee
        if entities:
            entity_id = entities[0].get("Id")
            items = self._service._request(
                self._token,
                "/Items",
                {
                    items_filter: entity_id,
                    "recursive": "true",
                    "includeItemTypes": "Movie,Series",
                    "fields": "BackdropImageTags",
                    "limit": max(1, limit * self.ITEMS_FETCH_FACTOR),
                    "userId": self._user_id,
                },
            ).get("Items") or []
            results.extend(self._backdrop_results(items, limit - len(results)))
        return results

    def _search_theme(self, limit: int) -> list[ImageResult]:
        editorial_line = getattr(self.tv_channel, "editorialline", None)
        if editorial_line is None:
            return []
        candidates = []
        containers = (
            MediaContainer.objects
            .filter(
                analyze_status=AnalyzeStatus.COMPLETE,
                media_collection__is_active=True,
                is_missing=False,
                media_source=self.media_source,
            )
            .select_related("media_collection")
            .order_by("id")
        )
        for container in containers.iterator():
            if not editorial_matching.container_passes_rules(container, (editorial_line,)):
                continue
            bonus = editorial_matching.preferred_bonus(container, (editorial_line,))
            candidates.append((-bonus, container.id, container))
        candidates.sort()
        pool_size = int(getattr(settings, "CHANNEL_IMAGE_THEME_POOL_SIZE", 25))
        pool_ids = [container.external_id for _, _, container in candidates[:pool_size]]
        if not pool_ids:
            return []

        items = self._service._request(
            self._token,
            "/Items",
            {
                "ids": ",".join(pool_ids),
                "fields": "BackdropImageTags",
                "userId": self._user_id,
            },
        ).get("Items") or []
        return self._backdrop_results(items, limit)

    def _backdrop_results(self, items: list[dict], limit: int) -> list[ImageResult]:
        results: list[ImageResult] = []
        for item in items:
            if len(results) >= max(limit, 0):
                break
            if item.get("BackdropImageTags"):
                results.append(
                    self._image_result(item, image_type="Backdrop/0", attribution=item.get("Name", ""))
                )
        return results

    def _image_result(self, item: dict, *, image_type: str, attribution: str) -> ImageResult:
        base_url = JellyfinService.normalize_url(self.media_source.credentials["application_url"])
        image_url = f"{base_url}/Items/{item.get('Id')}/Images/{image_type}"
        return ImageResult(
            provider=self.name,
            source_url=image_url,
            thumbnail_url=f"{image_url}?fillWidth={self.THUMBNAIL_WIDTH}",
            attribution=attribution,
        )
