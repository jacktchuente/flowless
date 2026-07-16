from __future__ import annotations

import json
import re
from datetime import date, datetime, time, timedelta
from typing import TypedDict

from django.conf import settings

from media_source.constants import MediaContainerKind, MediaNature
from rule_engine.services import category_service
from rule_engine.services.tv_channel_grid_generator.tv_channel_grid_generator_with_randomness import PreparedGridBlock
from utils.format_with_jinja import format_with_jinja
from utils.llm_service import LLMService


class TvChannelGridGeneratorWithLlmPayload(TypedDict):
    name: str
    description: str
    specification: str
    start_at: time
    end_at: time
    # dicts keyed by rule axis: categories / natures / container_kinds
    allowed: dict[str, list]
    preferred: dict[str, list]
    forbidden: dict[str, list]
    allow_filler: bool


class TvChannelGridGenerationError(ValueError):
    pass


class TvChannelGridGeneratorWithLlm:
    BASE_DATE = date(2000, 1, 1)
    MAX_BLOCK_DURATION_SECONDS = 180 * 60
    MIN_DURATION_SPREAD_SECONDS = 10 * 60
    TEMPLATE_PATH = (
        settings.BASE_DIR
        / "templates"
        / "rule_engine"
        / "prompts"
        / "tv_channel_grid_generator_prompt.j2"
    )

    def __init__(self, tv_channel_data: TvChannelGridGeneratorWithLlmPayload):
        self.tv_channel_data = tv_channel_data

    def get_blocks(self) -> list[PreparedGridBlock]:
        retry_errors: list[str] = []
        max_attempts = max(1, int(getattr(settings, "LLM_RETRY_BLUEPRINT", 1)))

        for attempt in range(1, max_attempts + 1):
            response = LLMService().complete(prompt=self._build_prompt(retry_errors=retry_errors))
            try:
                raw_blocks = self._parse_llm_response(response.content)
            except TvChannelGridGenerationError as exc:
                retry_errors = [str(exc)]
                if attempt == max_attempts:
                    raise
                continue

            blocks, validation_errors = self._validate_blocks(raw_blocks)
            if not validation_errors:
                return blocks

            retry_errors = validation_errors
            if attempt == max_attempts:
                raise TvChannelGridGenerationError("\n".join(validation_errors))

        raise TvChannelGridGenerationError("Grid generation failed.")

    def _build_prompt(self, *, retry_errors: list[str]) -> str:
        return format_with_jinja(
            self.TEMPLATE_PATH,
            {
                "channel_name": self.tv_channel_data["name"],
                "channel_description": self.tv_channel_data.get("description") or "",
                "channel_specification": self.tv_channel_data.get("specification") or "",
                "start_at": self.tv_channel_data["start_at"].strftime("%H:%M"),
                "end_at": self.tv_channel_data["end_at"].strftime("%H:%M"),
                "allow_filler": self.tv_channel_data["allow_filler"],
                "allowed": self._labels_for(self.tv_channel_data.get("allowed", {})),
                "forbidden": self._labels_for(self.tv_channel_data.get("forbidden", {})),
                "preferred": self._labels_for(self.tv_channel_data.get("preferred", {})),
                "available_categories": category_service.get_all_category_names(),
                "available_natures": [choice.label for choice in MediaNature],
                "available_container_kinds": [choice.label for choice in MediaContainerKind],
                "retry_errors": retry_errors,
            },
        )

    def _parse_llm_response(self, content: str) -> list[dict]:
        if not content or not content.strip():
            raise TvChannelGridGenerationError("LLM returned an empty response.")

        match = re.search(r"<grid_output>\s*(\{.*?\})\s*</grid_output>", content, re.DOTALL)
        candidate = match.group(1) if match else content.strip()

        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise TvChannelGridGenerationError("LLM returned an invalid grid JSON payload.") from exc

        if not isinstance(payload, dict):
            raise TvChannelGridGenerationError("LLM returned an invalid grid payload.")

        raw_blocks = payload.get("blocks", [])
        if not isinstance(raw_blocks, list):
            raise TvChannelGridGenerationError("Grid payload must contain a blocks list.")

        return raw_blocks

    def _validate_blocks(self, raw_blocks: list[dict]) -> tuple[list[PreparedGridBlock], list[str]]:
        category_set = set(category_service.get_all_category_names())
        nature_by_label = {choice.label: choice.value for choice in MediaNature}
        container_kind_by_label = {choice.label: choice.value for choice in MediaContainerKind}

        blocks: list[PreparedGridBlock] = []
        errors: list[str] = []
        for index, raw_block in enumerate(raw_blocks, start=1):
            if not isinstance(raw_block, dict):
                errors.append(f"Block #{index}: block must be an object.")
                continue

            try:
                starts_at = self._parse_time(raw_block.get("starts_at"), "starts_at")
                ends_at = self._parse_time(raw_block.get("ends_at"), "ends_at")
                priority = self._parse_int(raw_block.get("priority", 50), "priority", minimum=0, maximum=100)
                min_items = self._parse_int(raw_block.get("min_items", 1), "min_items", minimum=1)
                max_items = self._parse_int(raw_block.get("max_items", 1), "max_items", minimum=1, maximum=3)
                min_duration = self._parse_optional_int(
                    raw_block.get("min_duration_seconds_per_item"),
                    "min_duration_seconds_per_item",
                )
                max_duration = self._parse_optional_int(
                    raw_block.get("max_duration_seconds_per_item"),
                    "max_duration_seconds_per_item",
                )
                block_duration_seconds = self._block_duration_seconds(starts_at, ends_at)

                if min_items > max_items:
                    raise TvChannelGridGenerationError("min_items cannot be greater than max_items.")
                if (
                    min_duration is not None
                    and max_duration is not None
                    and min_duration > max_duration
                ):
                    raise TvChannelGridGenerationError(
                        "min_duration_seconds_per_item cannot be greater than max_duration_seconds_per_item."
                    )

                min_items, max_items = self._normalize_item_count_range(
                    min_items=min_items,
                    max_items=max_items,
                    block_duration_seconds=block_duration_seconds,
                )
                min_duration, max_duration = self._normalize_duration_range(
                    min_duration=min_duration,
                    max_duration=max_duration,
                    block_duration_seconds=block_duration_seconds,
                    max_items=max_items,
                )

                rules: dict[str, dict[str, list]] = {}
                for level in ("allowed", "preferred", "forbidden"):
                    raw_level = raw_block.get(level, {})
                    if not isinstance(raw_level, dict):
                        raise TvChannelGridGenerationError(f"{level} must be a dict keyed by rule axis.")
                    rules[level] = {
                        "categories": self._validate_string_choices(
                            raw_level.get("categories", []),
                            category_set,
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

                blocks.append(
                    PreparedGridBlock(
                        starts_at=starts_at,
                        ends_at=ends_at,
                        priority=priority,
                        min_items=min_items,
                        max_items=max_items,
                        min_duration_seconds_per_item=min_duration,
                        max_duration_seconds_per_item=max_duration,
                        allowed=rules["allowed"],
                        preferred=rules["preferred"],
                        forbidden=rules["forbidden"],
                    )
                )
            except TvChannelGridGenerationError as exc:
                errors.append(f"Block #{index}: {exc}")

        blocks = self._adjust_last_block_end_if_close(blocks)
        errors.extend(self._collect_time_coherence_errors(blocks))
        return blocks, errors

    def _adjust_last_block_end_if_close(self, blocks: list[PreparedGridBlock]) -> list[PreparedGridBlock]:
        if not blocks:
            return blocks

        window_start = datetime.combine(self.BASE_DATE, self.tv_channel_data["start_at"])
        window_end = datetime.combine(self.BASE_DATE, self.tv_channel_data["end_at"])
        if window_end <= window_start:
            window_end += timedelta(days=1)

        normalized_blocks = sorted(
            (
                self._normalize_block_interval(block, window_start)
                for block in blocks
            ),
            key=lambda item: item[1],
        )
        last_block, _, last_end = normalized_blocks[-1]
        delta_seconds = int((window_end - last_end).total_seconds())
        max_adjustment_seconds = int(getattr(settings, "GRID_END_ADJUSTMENT_MAX_SECONDS", 15 * 60))

        if delta_seconds <= 0 or delta_seconds > max_adjustment_seconds:
            return blocks

        last_block.ends_at = window_end.time()
        return blocks

    def _collect_time_coherence_errors(self, blocks: list[PreparedGridBlock]) -> list[str]:
        if not blocks:
            return ["Grid must contain at least one block."]
        errors: list[str] = []

        window_start = datetime.combine(self.BASE_DATE, self.tv_channel_data["start_at"])
        window_end = datetime.combine(self.BASE_DATE, self.tv_channel_data["end_at"])
        if window_end <= window_start:
            window_end += timedelta(days=1)

        normalized_blocks = sorted(
            (
                self._normalize_block_interval(block, window_start)
                for block in blocks
            ),
            key=lambda item: item[1],
        )

        first_start = normalized_blocks[0][1]
        last_end = normalized_blocks[-1][2]
        if first_start != window_start:
            errors.append("Grid blocks must start exactly at channel start_at.")
        if last_end != window_end:
            errors.append("Grid blocks must end exactly at channel end_at.")

        for index, (_, current_start, current_end) in enumerate(normalized_blocks):
            if current_end <= current_start:
                errors.append(f"Block #{index + 1}: A grid block has an invalid duration.")
            if int((current_end - current_start).total_seconds()) > self.MAX_BLOCK_DURATION_SECONDS:
                errors.append(f"Block #{index + 1}: A grid block is too long.")
            if index == 0:
                continue
            previous_end = normalized_blocks[index - 1][2]
            if current_start != previous_end:
                errors.append("Grid blocks must be contiguous with no gaps or overlaps.")
        return errors

    def _normalize_block_interval(
        self,
        block: PreparedGridBlock,
        window_start: datetime,
    ) -> tuple[PreparedGridBlock, datetime, datetime]:
        start = datetime.combine(self.BASE_DATE, block.starts_at)
        end = datetime.combine(self.BASE_DATE, block.ends_at)

        if end <= start:
            end += timedelta(days=1)
        if start < window_start:
            start += timedelta(days=1)
            end += timedelta(days=1)

        return block, start, end

    def _labels_for(self, level_rules: dict[str, list]) -> dict[str, list[str]]:
        level_rules = level_rules or {}
        return {
            "categories": [
                value for value in level_rules.get("categories", []) if isinstance(value, str)
            ],
            "natures": self._labels_from_values(level_rules.get("natures", []), MediaNature),
            "container_kinds": self._labels_from_values(
                level_rules.get("container_kinds", []), MediaContainerKind
            ),
        }

    @staticmethod
    def _labels_from_values(values: list[int], enum_cls) -> list[str]:
        label_by_value = {choice.value: choice.label for choice in enum_cls}
        return [
            label_by_value[value]
            for value in values
            if value in label_by_value
        ]

    @staticmethod
    def _validate_string_choices(value: object, allowed: set[str], field_name: str) -> list[str]:
        if not isinstance(value, list):
            raise TvChannelGridGenerationError(f"{field_name} must be a list.")
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
            raise TvChannelGridGenerationError(f"{field_name} must be a list.")
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
            raise TvChannelGridGenerationError(f"{field_name} preferred/allowed cannot overlap forbidden.")

    @staticmethod
    def _parse_time(value: object, field_name: str) -> time:
        if not isinstance(value, str):
            raise TvChannelGridGenerationError(f"{field_name} must be a HH:MM string.")
        try:
            hour, minute = value.split(":", 1)
            return time(hour=int(hour), minute=int(minute))
        except (TypeError, ValueError) as exc:
            raise TvChannelGridGenerationError(f"{field_name} must be a HH:MM string.") from exc

    @staticmethod
    def _parse_int(value: object, field_name: str, *, minimum: int, maximum: int | None = None) -> int:
        if not isinstance(value, int):
            raise TvChannelGridGenerationError(f"{field_name} must be an integer.")
        if value < minimum or (maximum is not None and value > maximum):
            raise TvChannelGridGenerationError(f"{field_name} is out of bounds.")
        return value

    @staticmethod
    def _parse_optional_int(value: object, field_name: str) -> int | None:
        if value is None:
            return None
        if not isinstance(value, int) or value < 0:
            raise TvChannelGridGenerationError(f"{field_name} must be a positive integer or null.")
        return value

    def _block_duration_seconds(self, starts_at: time, ends_at: time) -> int:
        start = datetime.combine(self.BASE_DATE, starts_at)
        end = datetime.combine(self.BASE_DATE, ends_at)
        if end <= start:
            end += timedelta(days=1)
        return int((end - start).total_seconds())

    def _normalize_item_count_range(
        self,
        *,
        min_items: int,
        max_items: int,
        block_duration_seconds: int,
    ) -> tuple[int, int]:
        max_items = min(max_items, 3)
        if block_duration_seconds >= 150 * 60:
            max_items = max(max_items, 3)
        elif block_duration_seconds >= 90 * 60:
            max_items = max(max_items, 2)
        min_items = min(min_items, max_items)
        return min_items, max_items

    def _normalize_duration_range(
        self,
        *,
        min_duration: int | None,
        max_duration: int | None,
        block_duration_seconds: int,
        max_items: int,
    ) -> tuple[int | None, int | None]:
        if min_duration is None and max_duration is None:
            return None, None

        if min_duration is None:
            min_duration = max(5 * 60, max_duration - self.MIN_DURATION_SPREAD_SECONDS)
        if max_duration is None:
            max_duration = min(block_duration_seconds, min_duration + self.MIN_DURATION_SPREAD_SECONDS)

        if min_duration >= max_duration:
            spread = max(self.MIN_DURATION_SPREAD_SECONDS, int(min_duration * 0.2))
            min_duration = max(5 * 60, min_duration - spread)
            max_duration = min(block_duration_seconds, max_duration + spread)

        if max_duration <= min_duration:
            max_duration = min_duration + self.MIN_DURATION_SPREAD_SECONDS

        max_allowed_per_item = max(10 * 60, block_duration_seconds)
        if max_items > 1:
            max_allowed_per_item = max(10 * 60, block_duration_seconds - 10 * 60)

        max_duration = min(max_duration, max_allowed_per_item)
        min_duration = min(min_duration, max_duration - 60) if max_duration > 60 else min_duration

        if max_duration <= min_duration:
            max_duration = min_duration + 60

        return min_duration, max_duration
