from __future__ import annotations

import re
from typing import TypedDict

from django.conf import settings

from grid_layout_preset.models import GridBlockPreset, GridLayoutPreset
from media_source.constants import MediaContainerKind, MediaNature
from rule_engine.services import category_service
from rule_engine.services.tv_channel_grid_generator.tv_channel_grid_generator_with_randomness import (
    PreparedGridBlock,
    TvChannelGridGeneratorPayload,
)
from utils.format_with_jinja import format_with_jinja
from utils.llm_service import LLMService


class TvChannelGridPresetSelectionError(ValueError):
    pass


class PresetBlockOverrides(TypedDict):
    # dicts keyed by rule axis: categories / natures / container_kinds
    allowed: dict[str, list]
    preferred: dict[str, list]
    forbidden: dict[str, list]


class TvChannelGridGeneratorWithPresetAndLlm:
    PRESET_SELECTION_TEMPLATE_PATH = (
        settings.BASE_DIR
        / "templates"
        / "rule_engine"
        / "prompts"
        / "tv_channel_grid_preset_selection_prompt.j2"
    )
    PRESET_ENRICHMENT_TEMPLATE_PATH = (
        settings.BASE_DIR
        / "templates"
        / "rule_engine"
        / "prompts"
        / "tv_channel_grid_preset_enrichment_prompt.j2"
    )

    def __init__(self, tv_channel_data: TvChannelGridGeneratorPayload):
        self.tv_channel_data = tv_channel_data

    def get_blocks(self) -> list[PreparedGridBlock]:
        presets = list(GridLayoutPreset.objects.order_by("name", "id"))
        if not presets:
            raise TvChannelGridPresetSelectionError("No grid layout presets available.")

        preset = self._select_preset_with_retry(presets)
        preset_blocks = list(
            GridBlockPreset.objects
            .filter(grid_layout=preset)
            .order_by("starts_at", "id")
        )
        if not preset_blocks:
            raise TvChannelGridPresetSelectionError("Selected grid layout preset has no blocks.")

        block_overrides = self._enrich_preset_blocks_with_retry(preset, preset_blocks)
        return self._build_blocks_from_preset(preset_blocks, block_overrides)

    def _select_preset_with_retry(self, presets: list[GridLayoutPreset]) -> GridLayoutPreset:
        retry_errors: list[str] = []
        max_attempts = max(1, int(getattr(settings, "LLM_RETRY_GRID_PRESET", 3)))

        for attempt in range(1, max_attempts + 1):
            response = LLMService().complete(
                prompt=self._build_preset_selection_prompt(presets=presets, retry_errors=retry_errors)
            )
            try:
                preset_id = self._parse_selected_preset_id(response.content)
                preset = next((item for item in presets if item.id == preset_id), None)
                if preset is None:
                    raise TvChannelGridPresetSelectionError(f"Unknown preset id: {preset_id}.")
                return preset
            except TvChannelGridPresetSelectionError as exc:
                retry_errors = [str(exc)]
                if attempt == max_attempts:
                    raise

        raise TvChannelGridPresetSelectionError("Unable to select a grid layout preset.")

    def _enrich_preset_blocks_with_retry(
        self,
        preset: GridLayoutPreset,
        preset_blocks: list[GridBlockPreset],
    ) -> list[PresetBlockOverrides]:
        retry_errors: list[str] = []
        max_attempts = max(1, int(getattr(settings, "LLM_RETRY_GRID_PRESET", 3)))

        for attempt in range(1, max_attempts + 1):
            response = LLMService().complete(
                prompt=self._build_preset_enrichment_prompt(
                    preset=preset,
                    preset_blocks=preset_blocks,
                    retry_errors=retry_errors,
                )
            )
            overrides, errors = self._parse_preset_block_overrides(response.content, block_count=len(preset_blocks))
            if not errors:
                return overrides
            retry_errors = errors
            if attempt == max_attempts:
                raise TvChannelGridPresetSelectionError("\n".join(errors))

        raise TvChannelGridPresetSelectionError("Unable to enrich preset blocks.")

    def _build_preset_selection_prompt(
        self,
        *,
        presets: list[GridLayoutPreset],
        retry_errors: list[str],
    ) -> str:
        return format_with_jinja(
            self.PRESET_SELECTION_TEMPLATE_PATH,
            {
                "channel_name": self.tv_channel_data.get("name", ""),
                "channel_description": self.tv_channel_data.get("description", ""),
                "channel_specification": self.tv_channel_data.get("specification", ""),
                "available_presets": [
                    {
                        "id": preset.id,
                        "name": preset.name,
                        "description": preset.description,
                    }
                    for preset in presets
                ],
                "retry_errors": retry_errors,
            },
        )

    def _build_preset_enrichment_prompt(
        self,
        *,
        preset: GridLayoutPreset,
        preset_blocks: list[GridBlockPreset],
        retry_errors: list[str],
    ) -> str:
        return format_with_jinja(
            self.PRESET_ENRICHMENT_TEMPLATE_PATH,
            {
                "channel_name": self.tv_channel_data.get("name", ""),
                "channel_description": self.tv_channel_data.get("description", ""),
                "channel_specification": self.tv_channel_data.get("specification", ""),
                "preset_id": preset.id,
                "preset_name": preset.name,
                "preset_description": preset.description,
                "available_categories": category_service.get_all_category_names(),
                "available_natures": [choice.label for choice in MediaNature],
                "available_container_kinds": [choice.label for choice in MediaContainerKind],
                "preset_blocks": [
                    {
                        "index": index,
                        "starts_at": block.starts_at.strftime("%H:%M"),
                        "ends_at": block.ends_at.strftime("%H:%M"),
                        "priority": block.priority,
                        "min_items": block.min_items,
                        "max_items": block.max_items,
                        "min_duration_seconds_per_item": block.min_duration_seconds_per_item,
                        "max_duration_seconds_per_item": block.max_duration_seconds_per_item,
                    }
                    for index, block in enumerate(preset_blocks, start=1)
                ],
                "retry_errors": retry_errors,
            },
        )

    @staticmethod
    def _parse_selected_preset_id(content: str) -> int:
        if not content or not content.strip():
            raise TvChannelGridPresetSelectionError("LLM returned an empty preset-selection response.")

        marker_index = content.lower().find("###response###")
        candidate = content[marker_index + len("###response###"):] if marker_index >= 0 else content
        match = re.search(r"(\d+)", candidate)
        if not match:
            raise TvChannelGridPresetSelectionError("LLM did not return any preset id after ###response###.")
        return int(match.group(1))

    def _parse_preset_block_overrides(
        self,
        content: str,
        *,
        block_count: int,
    ) -> tuple[list[PresetBlockOverrides], list[str]]:
        if not content or not content.strip():
            raise TvChannelGridPresetSelectionError("LLM returned an empty preset-enrichment response.")

        marker_index = content.lower().find("###response###")
        candidate = content[marker_index + len("###response###"):] if marker_index >= 0 else content

        section_pattern = re.compile(
            r"block\s*#?\s*(\d+)\s*[:\-]?\s*(.*?)(?=block\s*#?\s*\d+\s*[:\-]?|$)",
            re.IGNORECASE | re.DOTALL,
        )
        raw_sections = list(section_pattern.finditer(candidate))

        errors: list[str] = []
        if not raw_sections:
            return [], ["LLM did not return any block section after ###response###."]

        available_categories = set(category_service.get_all_category_names())
        nature_by_label = {choice.label.lower(): choice.value for choice in MediaNature}
        container_kind_by_label = {choice.label.lower(): choice.value for choice in MediaContainerKind}
        fields = (
            "allowed_categories",
            "forbidden_categories",
            "preferred_categories",
            "allowed_natures",
            "forbidden_natures",
            "preferred_natures",
            "allowed_container_kinds",
            "forbidden_container_kinds",
            "preferred_container_kinds",
        )

        overrides_by_index: dict[int, PresetBlockOverrides] = {}
        for section in raw_sections:
            block_index = int(section.group(1))
            if block_index < 1 or block_index > block_count:
                errors.append(f"Unknown block index: {block_index}.")
                continue

            body = section.group(2)
            values_by_field: dict[str, str] = {}
            for line in body.splitlines():
                if ":" not in line:
                    continue
                field_name, raw_value = line.split(":", 1)
                normalized_field_name = field_name.strip().lower()
                if normalized_field_name in fields:
                    values_by_field[normalized_field_name] = raw_value.strip()

            missing_fields = [field for field in fields if field not in values_by_field]
            if missing_fields:
                errors.append(
                    f"Block #{block_index} is missing fields: {', '.join(missing_fields)}."
                )
                continue

            overrides_by_index[block_index] = {
                level: {
                    "categories": self._sanitize_string_list(
                        values_by_field[f"{level}_categories"], available_categories
                    ),
                    "natures": self._sanitize_mapped_list(
                        values_by_field[f"{level}_natures"], nature_by_label
                    ),
                    "container_kinds": self._sanitize_mapped_list(
                        values_by_field[f"{level}_container_kinds"], container_kind_by_label
                    ),
                }
                for level in ("allowed", "preferred", "forbidden")
            }

        for block_index in range(1, block_count + 1):
            if block_index not in overrides_by_index:
                errors.append(f"Missing block section for block #{block_index}.")

        if errors:
            return [], errors

        return [overrides_by_index[index] for index in range(1, block_count + 1)], []

    def _build_blocks_from_preset(
        self,
        preset_blocks: list[GridBlockPreset],
        block_overrides: list[PresetBlockOverrides],
    ) -> list[PreparedGridBlock]:
        result: list[PreparedGridBlock] = []
        for preset_block, override in zip(preset_blocks, block_overrides, strict=True):
            result.append(
                PreparedGridBlock(
                    starts_at=preset_block.starts_at,
                    ends_at=preset_block.ends_at,
                    priority=preset_block.priority,
                    min_items=preset_block.min_items,
                    max_items=min(preset_block.max_items, 3),
                    min_duration_seconds_per_item=preset_block.min_duration_seconds_per_item,
                    max_duration_seconds_per_item=preset_block.max_duration_seconds_per_item,
                    allowed=override["allowed"],
                    preferred=override["preferred"],
                    forbidden=override["forbidden"],
                )
            )
        return result

    @staticmethod
    def _sanitize_string_list(raw_value: str, allowed_values: set[str]) -> list[str]:
        values: list[str] = []
        for token in re.split(r"[,|\n]", raw_value):
            candidate = token.strip()
            if not candidate or candidate.lower() in {"none", "null", "-"}:
                continue
            if candidate in allowed_values and candidate not in values:
                values.append(candidate)
        return values

    @staticmethod
    def _sanitize_mapped_list(raw_value: str, mapping: dict[str, int]) -> list[int]:
        values: list[int] = []
        for token in re.split(r"[,|\n]", raw_value):
            candidate = token.strip().lower()
            if not candidate or candidate in {"none", "null", "-"}:
                continue
            mapped = mapping.get(candidate)
            if mapped is not None and mapped not in values:
                values.append(mapped)
        return values
