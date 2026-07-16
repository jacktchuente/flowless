from __future__ import annotations

import re

from django.conf import settings

from media_source.constants import MUSIC_CONTAINER_KINDS
from rule_engine.services import category_service
from utils.format_with_jinja import format_with_jinja
from utils.llm_service import LLMService


class CategoryNormalizerWithLlm:
    RESPONSE_MARKER = "###response###"
    TEMPLATE_PATH = settings.BASE_DIR / "templates" / "rule_engine" / "prompts" / "category_normalization_prompt.j2"
    MUSIC_TEMPLATE_PATH = (
        settings.BASE_DIR / "templates" / "rule_engine" / "prompts" / "music_category_normalization_prompt.j2"
    )

    def __init__(self, media_container):
        self.media_container = media_container

    def get_categories(self) -> list[str]:
        # Vocabulaire scinde par type de contenu: un container musical est
        # categorise avec un prompt dedie sur music + genres musicaux, les
        # autres containers ne voient jamais les genres musicaux.
        if self._is_music_container():
            return self._get_music_categories()
        return self._get_general_categories()

    def _is_music_container(self) -> bool:
        collection = getattr(self.media_container, "media_collection", None)
        return getattr(collection, "container_kind", None) in MUSIC_CONTAINER_KINDS

    def _get_general_categories(self) -> list[str]:
        available_categories = category_service.get_general_category_names()
        if not available_categories:
            return []

        prompt = format_with_jinja(
            self.TEMPLATE_PATH,
            context={
                "available_categories": available_categories,
                "title": self.media_container.title,
                "description": self.media_container.description,
                "genres": self.media_container.genres or [],
                "tags": self.media_container.tags or [],
                "countries": self.media_container.countries or [],
                "audio_languages": self.media_container.audio_languages or [],
                "subtitle_languages": self.media_container.subtitle_languages or [],
                "min_age": self.media_container.min_age,
                "max_age": self.media_container.max_age,
                "release_date": (
                    self.media_container.release_date.isoformat()
                    if self.media_container.release_date
                    else None
                ),
                "response_marker": self.RESPONSE_MARKER,
            },
        )
        response = LLMService().complete(prompt=prompt)
        return self._filter_available_categories(
            self._parse_categories(response.content),
            available_categories,
        )

    def _get_music_categories(self) -> list[str]:
        # Genres uniquement: "music" serait redondant avec le kind du container.
        available_categories = sorted(category_service.get_music_category_names())
        if not available_categories:
            return []

        prompt = format_with_jinja(
            self.MUSIC_TEMPLATE_PATH,
            context={
                "available_categories": available_categories,
                "title": self.media_container.title,
                "title_parts": self._split_title_parts(self.media_container.title),
                "genres": self.media_container.genres or [],
                "tags": self.media_container.tags or [],
                "release_year": self.media_container.release_year_min,
                "response_marker": self.RESPONSE_MARKER,
            },
        )
        response = LLMService().complete(prompt=prompt)
        return self._filter_available_categories(
            self._parse_categories(response.content),
            available_categories,
        )

    @staticmethod
    def _split_title_parts(title: str | None) -> list[str]:
        # Convention "Artiste - Morceau" ou l'inverse selon les bibliotheques:
        # on fournit les deux parties sans presumer de l'ordre.
        if not title or " - " not in title:
            return []
        return [part.strip() for part in title.split(" - ") if part.strip()]

    @classmethod
    def _parse_categories(cls, response_content: str) -> list[str]:
        content = response_content.split(cls.RESPONSE_MARKER, 1)[-1].strip()
        if not content:
            return []

        return [
            value.strip()
            for value in re.split(r"[\n,]+", content)
            if value.strip()
        ]

    @classmethod
    def _filter_available_categories(
            cls,
            categories: list[str],
            available_categories: list[str],
    ) -> list[str]:
        normalized_available_categories = {
            cls._normalize_category(value): value
            for value in available_categories
        }
        filtered_categories: list[str] = []
        for category in categories:
            normalized_category = cls._normalize_category(category)
            matched_category = normalized_available_categories.get(normalized_category)
            if matched_category and matched_category not in filtered_categories:
                filtered_categories.append(matched_category)

        return filtered_categories

    @staticmethod
    def _normalize_category(value: str) -> str:
        return value.strip().casefold()
