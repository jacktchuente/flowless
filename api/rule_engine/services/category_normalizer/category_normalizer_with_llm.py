from __future__ import annotations

import re

from django.conf import settings

from rule_engine.models import Category
from utils.format_with_jinja import format_with_jinja
from utils.llm_service import LLMService


class CategoryNormalizerWithLlm:
    RESPONSE_MARKER = "###response###"
    TEMPLATE_PATH = settings.BASE_DIR / "templates" / "rule_engine" / "prompts" / "category_normalization_prompt.j2"

    def __init__(self, media_container):
        self.media_container = media_container

    def get_categories(self) -> list[str]:
        available_categories = list(
            Category.objects.values_list("category", flat=True),
        )
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
