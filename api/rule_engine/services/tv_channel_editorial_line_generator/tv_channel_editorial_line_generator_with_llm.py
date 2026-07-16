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
    # dicts keyed by rule axis: categories / natures / container_kinds
    allowed: dict[str, list]
    preferred: dict[str, list]
    forbidden: dict[str, list]
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

        rules: dict[str, dict[str, list]] = {}
        for level in ("allowed", "preferred", "forbidden"):
            raw_level = payload.get(level, {})
            if not isinstance(raw_level, dict):
                raise TvChannelEditorialLineGenerationError(f"{level} must be a dict keyed by rule axis.")
            rules[level] = {
                "categories": self._validate_string_choices(
                    raw_level.get("categories", []),
                    available_categories,
                    f"{level} categories",
                ),
                "natures": self._validate_mapped_choices(
                    raw_level.get("natures", []),
                    nature_by_label,
                    f"{level} natures",
                ),
                "container_kinds": self._validate_mapped_choices(
                    raw_level.get("container_kinds", []),
                    container_kind_by_label,
                    f"{level} container_kinds",
                ),
            }

        for axis in ("categories", "natures", "container_kinds"):
            self._ensure_no_overlap(rules["allowed"][axis], rules["forbidden"][axis], axis)
            self._ensure_no_overlap(rules["preferred"][axis], rules["forbidden"][axis], axis)

        start_at = self._parse_time(payload.get("start_at"), "start_at")
        end_at = self._parse_time(payload.get("end_at"), "end_at")
        if start_at == end_at:
            raise TvChannelEditorialLineGenerationError("Editorial line window cannot be zero.")

        allow_filler = payload.get("allow_filler", True)
        if not isinstance(allow_filler, bool):
            raise TvChannelEditorialLineGenerationError("allow_filler must be a boolean.")

        return {
            "allowed": rules["allowed"],
            "preferred": rules["preferred"],
            "forbidden": rules["forbidden"],
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
