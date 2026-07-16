from __future__ import annotations

from datetime import time
from functools import cached_property

from django.conf import settings
from rest_framework import serializers

from media_source.constants import MediaContainerKind, MediaNature
from rule_engine.services import category_service


class GenerationBaseSerializer(serializers.Serializer):
    @staticmethod
    def _dedupe_str_list(values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            normalized = value.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
        return result

    @staticmethod
    def _dedupe_int_list(values: list[int]) -> list[int]:
        result: list[int] = []
        seen: set[int] = set()
        for value in values:
            if value not in seen:
                seen.add(value)
                result.append(value)
        return result

    def _validate_choice_list(self, value: list[str], allowed: set[str], field_name: str) -> list[str]:
        filtered = [item for item in value if item in allowed]
        return self._dedupe_str_list(filtered)

    def _validate_enum_choice_list(self, value: list, enum_cls, field_name: str) -> list[int]:
        value_by_label = {choice.label: choice.value for choice in enum_cls}
        value_by_value = {choice.value: choice.value for choice in enum_cls}

        normalized: list[int] = []
        for item in value:
            if isinstance(item, str) and item in value_by_label:
                normalized.append(value_by_label[item])
                continue
            if isinstance(item, int) and item in value_by_value:
                normalized.append(item)
                continue
        return self._dedupe_int_list(normalized)

    @staticmethod
    def _validate_no_overlap(left: list, right: list, left_name: str, right_name: str) -> None:
        if set(left) & set(right):
            raise serializers.ValidationError(f"{left_name} and {right_name} cannot overlap.")


class EditorialLineGenerationSerializer(GenerationBaseSerializer):
    allowed_categories = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    forbidden_categories = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    preferred_categories = serializers.ListField(child=serializers.CharField(), required=False, default=list)

    allowed_natures = serializers.ListField(child=serializers.JSONField(), required=False, default=list)
    forbidden_natures = serializers.ListField(child=serializers.JSONField(), required=False, default=list)
    preferred_natures = serializers.ListField(child=serializers.JSONField(), required=False, default=list)

    allowed_container_kinds = serializers.ListField(child=serializers.JSONField(), required=False, default=list)
    forbidden_container_kinds = serializers.ListField(child=serializers.JSONField(), required=False, default=list)
    preferred_container_kinds = serializers.ListField(child=serializers.JSONField(), required=False, default=list)

    start_at = serializers.TimeField()
    end_at = serializers.TimeField()
    allow_filler = serializers.BooleanField(default=True)

    @cached_property
    def allowed_categories_set(self) -> set[str]:
        # Lu en BDD au moment de la validation, pas fige a l'import du module.
        return set(category_service.get_all_category_names())

    def validate_allowed_categories(self, value: list[str]) -> list[str]:
        return self._validate_choice_list(value, self.allowed_categories_set, "allowed_categories")

    def validate_forbidden_categories(self, value: list[str]) -> list[str]:
        return self._validate_choice_list(value, self.allowed_categories_set, "forbidden_categories")

    def validate_preferred_categories(self, value: list[str]) -> list[str]:
        return self._validate_choice_list(value, self.allowed_categories_set, "preferred_categories")

    def validate_allowed_natures(self, value: list) -> list[int]:
        return self._validate_enum_choice_list(value, MediaNature, "allowed_natures")

    def validate_forbidden_natures(self, value: list) -> list[int]:
        return self._validate_enum_choice_list(value, MediaNature, "forbidden_natures")

    def validate_preferred_natures(self, value: list) -> list[int]:
        return self._validate_enum_choice_list(value, MediaNature, "preferred_natures")

    def validate_allowed_container_kinds(self, value: list) -> list[int]:
        return self._validate_enum_choice_list(value, MediaContainerKind, "allowed_container_kinds")

    def validate_forbidden_container_kinds(self, value: list) -> list[int]:
        return self._validate_enum_choice_list(value, MediaContainerKind, "forbidden_container_kinds")

    def validate_preferred_container_kinds(self, value: list) -> list[int]:
        return self._validate_enum_choice_list(value, MediaContainerKind, "preferred_container_kinds")

    def validate(self, attrs):
        if attrs["start_at"] == attrs["end_at"]:
            raise serializers.ValidationError("Editorial line duration cannot be zero.")

        self._validate_no_overlap(
            attrs["allowed_categories"],
            attrs["forbidden_categories"],
            "allowed_categories",
            "forbidden_categories",
        )
        self._validate_no_overlap(
            attrs["preferred_categories"],
            attrs["forbidden_categories"],
            "preferred_categories",
            "forbidden_categories",
        )
        self._validate_no_overlap(
            attrs["allowed_natures"],
            attrs["forbidden_natures"],
            "allowed_natures",
            "forbidden_natures",
        )
        self._validate_no_overlap(
            attrs["preferred_natures"],
            attrs["forbidden_natures"],
            "preferred_natures",
            "forbidden_natures",
        )
        self._validate_no_overlap(
            attrs["allowed_container_kinds"],
            attrs["forbidden_container_kinds"],
            "allowed_container_kinds",
            "forbidden_container_kinds",
        )
        self._validate_no_overlap(
            attrs["preferred_container_kinds"],
            attrs["forbidden_container_kinds"],
            "preferred_container_kinds",
            "forbidden_container_kinds",
        )
        return attrs


class GridBlockGenerationSerializer(GenerationBaseSerializer):
    starts_at = serializers.TimeField()
    ends_at = serializers.TimeField()
    priority = serializers.IntegerField(min_value=0, max_value=100, default=50)
    min_items = serializers.IntegerField(min_value=1, default=1)
    max_items = serializers.IntegerField(min_value=1, default=1)
    min_duration_seconds_per_item = serializers.IntegerField(required=False, allow_null=True, default=None, min_value=0)
    max_duration_seconds_per_item = serializers.IntegerField(required=False, allow_null=True, default=None, min_value=0)
    post_filler_policy_id = serializers.IntegerField(required=False, allow_null=True, default=None, min_value=1)

    allowed_categories = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    forbidden_categories = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    preferred_categories = serializers.ListField(child=serializers.CharField(), required=False, default=list)

    allowed_natures = serializers.ListField(child=serializers.JSONField(), required=False, default=list)
    forbidden_natures = serializers.ListField(child=serializers.JSONField(), required=False, default=list)
    preferred_natures = serializers.ListField(child=serializers.JSONField(), required=False, default=list)

    allowed_container_kinds = serializers.ListField(child=serializers.JSONField(), required=False, default=list)
    forbidden_container_kinds = serializers.ListField(child=serializers.JSONField(), required=False, default=list)
    preferred_container_kinds = serializers.ListField(child=serializers.JSONField(), required=False, default=list)

    @cached_property
    def allowed_categories_set(self) -> set[str]:
        # Lu en BDD au moment de la validation, pas fige a l'import du module.
        return set(category_service.get_all_category_names())

    def validate_allowed_categories(self, value: list[str]) -> list[str]:
        return self._validate_choice_list(value, self.allowed_categories_set, "allowed_categories")

    def validate_forbidden_categories(self, value: list[str]) -> list[str]:
        return self._validate_choice_list(value, self.allowed_categories_set, "forbidden_categories")

    def validate_preferred_categories(self, value: list[str]) -> list[str]:
        return self._validate_choice_list(value, self.allowed_categories_set, "preferred_categories")

    def validate_allowed_natures(self, value: list) -> list[int]:
        return self._validate_enum_choice_list(value, MediaNature, "allowed_natures")

    def validate_forbidden_natures(self, value: list) -> list[int]:
        return self._validate_enum_choice_list(value, MediaNature, "forbidden_natures")

    def validate_preferred_natures(self, value: list) -> list[int]:
        return self._validate_enum_choice_list(value, MediaNature, "preferred_natures")

    def validate_allowed_container_kinds(self, value: list) -> list[int]:
        return self._validate_enum_choice_list(value, MediaContainerKind, "allowed_container_kinds")

    def validate_forbidden_container_kinds(self, value: list) -> list[int]:
        return self._validate_enum_choice_list(value, MediaContainerKind, "forbidden_container_kinds")

    def validate_preferred_container_kinds(self, value: list) -> list[int]:
        return self._validate_enum_choice_list(value, MediaContainerKind, "preferred_container_kinds")

    def validate(self, attrs):
        if attrs["min_items"] > attrs["max_items"]:
            raise serializers.ValidationError("min_items cannot be greater than max_items.")
        if (
            attrs["min_duration_seconds_per_item"] is not None
            and attrs["max_duration_seconds_per_item"] is not None
            and attrs["min_duration_seconds_per_item"] > attrs["max_duration_seconds_per_item"]
        ):
            raise serializers.ValidationError(
                "min_duration_seconds_per_item cannot be greater than max_duration_seconds_per_item."
            )

        self._validate_no_overlap(
            attrs["allowed_categories"],
            attrs["forbidden_categories"],
            "allowed_categories",
            "forbidden_categories",
        )
        self._validate_no_overlap(
            attrs["preferred_categories"],
            attrs["forbidden_categories"],
            "preferred_categories",
            "forbidden_categories",
        )
        self._validate_no_overlap(
            attrs["allowed_natures"],
            attrs["forbidden_natures"],
            "allowed_natures",
            "forbidden_natures",
        )
        self._validate_no_overlap(
            attrs["preferred_natures"],
            attrs["forbidden_natures"],
            "preferred_natures",
            "forbidden_natures",
        )
        self._validate_no_overlap(
            attrs["allowed_container_kinds"],
            attrs["forbidden_container_kinds"],
            "allowed_container_kinds",
            "forbidden_container_kinds",
        )
        self._validate_no_overlap(
            attrs["preferred_container_kinds"],
            attrs["forbidden_container_kinds"],
            "preferred_container_kinds",
            "forbidden_container_kinds",
        )
        return attrs


class GridGenerationSerializer(serializers.Serializer):
    start_at = serializers.TimeField()
    end_at = serializers.TimeField()
    blocks = GridBlockGenerationSerializer(many=True, required=False, default=list)

    @staticmethod
    def _to_minutes(value: time) -> int:
        return value.hour * 60 + value.minute

    def validate(self, attrs):
        start = self._to_minutes(attrs["start_at"])
        end = self._to_minutes(attrs["end_at"])
        frame_end = end if end > start else end + 24 * 60
        if frame_end == start:
            raise serializers.ValidationError("Grid duration cannot be zero.")
        if not attrs["blocks"]:
            raise serializers.ValidationError("Grid must contain at least one block.")

        normalized_intervals: list[tuple[int, int]] = []
        for block in attrs["blocks"]:
            block_start = self._to_minutes(block["starts_at"])
            block_end = self._to_minutes(block["ends_at"])
            normalized_start = block_start
            normalized_end = block_end if block_end > block_start else block_end + 24 * 60

            if normalized_start < start:
                normalized_start += 24 * 60
                normalized_end += 24 * 60

            if normalized_start < start or normalized_end > frame_end:
                raise serializers.ValidationError("A block falls outside grid bounds.")
            if normalized_end <= normalized_start:
                raise serializers.ValidationError("A block has an invalid duration.")

            normalized_intervals.append((normalized_start, normalized_end))

        normalized_intervals.sort()
        if normalized_intervals[0][0] != start:
            raise serializers.ValidationError("Blocks must start exactly at grid start_at.")
        if normalized_intervals[-1][1] != frame_end:
            raise serializers.ValidationError("Blocks must end exactly at grid end_at.")

        for index in range(1, len(normalized_intervals)):
            previous_end = normalized_intervals[index - 1][1]
            current_start = normalized_intervals[index][0]
            if current_start != previous_end:
                raise serializers.ValidationError("Blocks must be contiguous with no gaps or overlaps.")

        return attrs


class CatalogGeneratedChannelSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50)
    description = serializers.CharField(allow_blank=True, required=False, default="")
    specification = serializers.CharField(allow_blank=True, required=False, default="")


class CatalogGenerationSerializer(serializers.Serializer):
    channels = CatalogGeneratedChannelSerializer(many=True, required=False, default=list)

    def validate_channels(self, value):
        max_count = getattr(settings, "CATALOG_GENERATOR_MAX_CHANNELS", 30)
        if len(value) > max_count:
            raise serializers.ValidationError(f"Cannot generate more than {max_count} channels.")
        names = [item["name"] for item in value]
        if len(names) != len(set(names)):
            raise serializers.ValidationError("Duplicate channel names are not allowed.")
        return value
