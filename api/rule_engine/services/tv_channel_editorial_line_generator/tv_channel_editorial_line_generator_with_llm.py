from __future__ import annotations

import json
import re
from datetime import time
from typing import TypedDict

from django.conf import settings

from media_source.constants import MediaContainerKind, MediaNature
from rule_engine.services import category_service
from utils.format_with_jinja import format_with_jinja
from utils.llm_service import LLMService


class TvChannelEditorialLineInput(TypedDict):
    name: str
    description: str
    specification: str


class PreparedTvChannelEditorialLine(TypedDict):
    allowed_categories: list[str]
    forbidden_categories: list[str]
    preferred_categories: list[str]
    allowed_natures: list[int]
    forbidden_natures: list[int]
    preferred_natures: list[int]
    allowed_container_kinds: list[int]
    forbidden_container_kinds: list[int]
    preferred_container_kinds: list[int]
    start_at: time
    end_at: time
    allow_filler: bool


class TvChannelEditorialLineGenerationError(ValueError):
    pass


class TvChannelEditorialLineGeneratorWithLlm:
    TEMPLATE_PATH = (
        settings.BASE_DIR
        / "templates"
        / "rule_engine"
        / "prompts"
        / "tv_channel_editorial_line_generator_prompt.j2"
    )

    def __init__(self, tv_channel_data: TvChannelEditorialLineInput):
        self.tv_channel_data = tv_channel_data

    def get_editorial_line(self) -> PreparedTvChannelEditorialLine:
        prompt = format_with_jinja(
            self.TEMPLATE_PATH,
            {
                "channel_name": self.tv_channel_data["name"],
                "channel_description": self.tv_channel_data.get("description") or "",
                "channel_specification": self.tv_channel_data.get("specification") or "",
                "available_categories": category_service.get_all_category_names(),
                "available_natures": [choice.label for choice in MediaNature],
                "available_container_kinds": [choice.label for choice in MediaContainerKind],
            },
        )
        response = LLMService().complete(prompt=prompt)
        return self._validate_payload(self._parse_llm_response(response.content))

    def _parse_llm_response(self, content: str) -> dict:
        if not content or not content.strip():
            raise TvChannelEditorialLineGenerationError("LLM returned an empty response.")

        match = re.search(r"<editorial_line_output>\s*(\{.*?\})\s*</editorial_line_output>", content, re.DOTALL)
        candidate = match.group(1) if match else content.strip()

        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise TvChannelEditorialLineGenerationError("LLM returned an invalid editorial JSON payload.") from exc

        if not isinstance(payload, dict):
            raise TvChannelEditorialLineGenerationError("LLM returned an invalid editorial payload.")

        return payload

    def _validate_payload(self, payload: dict) -> PreparedTvChannelEditorialLine:
        available_categories = set(category_service.get_all_category_names())
        nature_by_label = {choice.label: choice.value for choice in MediaNature}
        container_kind_by_label = {choice.label: choice.value for choice in MediaContainerKind}

        allowed_categories = self._validate_string_choices(
            payload.get("allowed_categories", []),
            available_categories,
            "allowed_categories",
        )
        forbidden_categories = self._validate_string_choices(
            payload.get("forbidden_categories", []),
            available_categories,
            "forbidden_categories",
        )
        preferred_categories = self._validate_string_choices(
            payload.get("preferred_categories", []),
            available_categories,
            "preferred_categories",
        )

        allowed_natures = self._validate_mapped_choices(
            payload.get("allowed_natures", []),
            nature_by_label,
            "allowed_natures",
        )
        forbidden_natures = self._validate_mapped_choices(
            payload.get("forbidden_natures", []),
            nature_by_label,
            "forbidden_natures",
        )
        preferred_natures = self._validate_mapped_choices(
            payload.get("preferred_natures", []),
            nature_by_label,
            "preferred_natures",
        )

        allowed_container_kinds = self._validate_mapped_choices(
            payload.get("allowed_container_kinds", []),
            container_kind_by_label,
            "allowed_container_kinds",
        )
        forbidden_container_kinds = self._validate_mapped_choices(
            payload.get("forbidden_container_kinds", []),
            container_kind_by_label,
            "forbidden_container_kinds",
        )
        preferred_container_kinds = self._validate_mapped_choices(
            payload.get("preferred_container_kinds", []),
            container_kind_by_label,
            "preferred_container_kinds",
        )

        self._ensure_no_overlap(allowed_categories, forbidden_categories, "categories")
        self._ensure_no_overlap(preferred_categories, forbidden_categories, "categories")
        self._ensure_no_overlap(allowed_natures, forbidden_natures, "natures")
        self._ensure_no_overlap(preferred_natures, forbidden_natures, "natures")
        self._ensure_no_overlap(allowed_container_kinds, forbidden_container_kinds, "container_kinds")
        self._ensure_no_overlap(preferred_container_kinds, forbidden_container_kinds, "container_kinds")

        start_at = self._parse_time(payload.get("start_at"), "start_at")
        end_at = self._parse_time(payload.get("end_at"), "end_at")
        if start_at == end_at:
            raise TvChannelEditorialLineGenerationError("Editorial line window cannot be zero.")

        allow_filler = payload.get("allow_filler", True)
        if not isinstance(allow_filler, bool):
            raise TvChannelEditorialLineGenerationError("allow_filler must be a boolean.")

        return {
            "allowed_categories": allowed_categories,
            "forbidden_categories": forbidden_categories,
            "preferred_categories": preferred_categories,
            "allowed_natures": allowed_natures,
            "forbidden_natures": forbidden_natures,
            "preferred_natures": preferred_natures,
            "allowed_container_kinds": allowed_container_kinds,
            "forbidden_container_kinds": forbidden_container_kinds,
            "preferred_container_kinds": preferred_container_kinds,
            "start_at": start_at,
            "end_at": end_at,
            "allow_filler": allow_filler,
        }

    @staticmethod
    def _validate_string_choices(value: object, allowed: set[str], field_name: str) -> list[str]:
        if not isinstance(value, list):
            raise TvChannelEditorialLineGenerationError(f"{field_name} must be a list.")
        cleaned: list[str] = []
        for item in value:
            if not isinstance(item, str) or item not in allowed:
                continue
            if item not in cleaned:
                cleaned.append(item)
        return cleaned

    @staticmethod
    def _validate_mapped_choices(value: object, allowed: dict[str, int], field_name: str) -> list[int]:
        if not isinstance(value, list):
            raise TvChannelEditorialLineGenerationError(f"{field_name} must be a list.")
        cleaned: list[int] = []
        for item in value:
            if not isinstance(item, str) or item not in allowed:
                continue
            mapped_value = allowed[item]
            if mapped_value not in cleaned:
                cleaned.append(mapped_value)
        return cleaned

    @staticmethod
    def _ensure_no_overlap(left: list, right: list, field_name: str) -> None:
        if set(left) & set(right):
            raise TvChannelEditorialLineGenerationError(f"{field_name} preferred/allowed cannot overlap forbidden.")

    @staticmethod
    def _parse_time(value: object, field_name: str) -> time:
        if not isinstance(value, str):
            raise TvChannelEditorialLineGenerationError(f"{field_name} must be a HH:MM string.")
        try:
            hour, minute = value.split(":", 1)
            return time(hour=int(hour), minute=int(minute))
        except (TypeError, ValueError) as exc:
            raise TvChannelEditorialLineGenerationError(f"{field_name} must be a HH:MM string.") from exc
