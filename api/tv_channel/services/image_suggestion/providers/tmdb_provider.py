from __future__ import annotations

import logging

import requests
from django.conf import settings

from tv_channel.models import ChannelImageEntityType
from tv_channel.services.image_suggestion.providers.base import ImageResult, ImageSearchProvider
from tv_channel.services.image_suggestion.query_service import ImageQuery

logger = logging.getLogger(__name__)


class TmdbImageProvider(ImageSearchProvider):
    name = "tmdb"

    API_BASE = "https://api.themoviedb.org/3"
    IMAGE_BASE = "https://image.tmdb.org/t/p"
    THUMBNAIL_SIZE = "w342"
    TIMEOUT = 15

    def is_available(self) -> bool:
        return bool(getattr(settings, "TMDB_API_KEY", None))

    def search(self, query: ImageQuery, limit: int) -> list[ImageResult]:
        if query.entity_type == ChannelImageEntityType.STUDIO:
            return self._search_studio(query.query, limit)
        if query.entity_type == ChannelImageEntityType.PERSON:
            return self._search_person(query.query, limit)
        return self._search_theme(query.query, limit)

    def download(self, url: str) -> bytes:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content

    def _search_studio(self, query: str, limit: int) -> list[ImageResult]:
        companies = self._get("/search/company", {"query": query}).get("results") or []
        if not companies:
            return []
        company = companies[0]
        results: list[ImageResult] = []
        logos = self._get(f"/company/{company['id']}/images", {}).get("logos") or []
        for logo in logos[:limit]:
            results.append(self._image_result(logo, attribution=company.get("name", "")))
        if len(results) < limit:
            movies = self._get(
                "/discover/movie",
                {"with_companies": company["id"], "sort_by": "popularity.desc"},
            ).get("results") or []
            results.extend(self._backdrop_results(movies, limit - len(results)))
        return results

    def _search_person(self, query: str, limit: int) -> list[ImageResult]:
        persons = self._get("/search/person", {"query": query}).get("results") or []
        results: list[ImageResult] = []
        for person in persons:
            if len(results) >= limit:
                break
            if person.get("profile_path"):
                results.append(
                    self._image_result({"file_path": person["profile_path"]}, attribution=person.get("name", ""))
                )
        if persons and len(results) < limit:
            known_for = persons[0].get("known_for") or []
            results.extend(self._backdrop_results(known_for, limit - len(results)))
        return results

    def _search_theme(self, query: str, limit: int) -> list[ImageResult]:
        entries = self._get("/search/multi", {"query": query}).get("results") or []
        return self._backdrop_results(entries, limit)

    def _backdrop_results(self, entries: list[dict], limit: int) -> list[ImageResult]:
        results: list[ImageResult] = []
        for entry in entries:
            if len(results) >= max(limit, 0):
                break
            if entry.get("backdrop_path"):
                results.append(
                    self._image_result(
                        {"file_path": entry["backdrop_path"]},
                        attribution=entry.get("title") or entry.get("name") or "",
                    )
                )
        return results

    def _image_result(self, image: dict, *, attribution: str) -> ImageResult:
        path = image["file_path"]
        return ImageResult(
            provider=self.name,
            source_url=f"{self.IMAGE_BASE}/original{path}",
            thumbnail_url=f"{self.IMAGE_BASE}/{self.THUMBNAIL_SIZE}{path}",
            width=image.get("width"),
            height=image.get("height"),
            attribution=attribution,
        )

    def _get(self, path: str, params: dict) -> dict:
        response = requests.get(
            f"{self.API_BASE}{path}",
            params={**params, "api_key": settings.TMDB_API_KEY},
            timeout=self.TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
