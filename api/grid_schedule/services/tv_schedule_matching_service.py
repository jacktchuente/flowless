from __future__ import annotations

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import QuerySet

from project_ops.constants import AnalyzeStatus
from media_source.models import MediaContainer, MediaItem
from tv_channel.models import EditorialLine, GridBlock, TvChannel


class TvScheduleMatchingService:
    def __init__(self, *, tv_channel: TvChannel):
        self.tv_channel = tv_channel
        self.editorial_line = self._get_editorial_line(tv_channel)

    def get_block_match_stats(self, block: GridBlock) -> dict[str, int]:
        matching_container_ids: set[int] = set()
        matching_media_item_count = 0

        for container in self._matching_containers(block):
            if container.id in matching_container_ids:
                continue

            items_qs = self._matching_items_qs(block, container)
            item_count = items_qs.count()
            if item_count <= 0:
                continue

            matching_container_ids.add(container.id)
            matching_media_item_count += item_count

        return {
            "matching_media_container_count": len(matching_container_ids),
            "matching_media_item_count": matching_media_item_count,
        }

    def _matching_containers(self, block: GridBlock):
        queryset = (
            MediaContainer.objects
            .filter(
                analyze_status=AnalyzeStatus.COMPLETE,
                media_collection__is_active=True,
                is_missing=False,
            )
            .select_related("media_collection")
            .distinct()
            .order_by("id")
        )

        seen_container_ids: set[int] = set()
        for container in queryset.iterator():
            if container.id in seen_container_ids:
                continue
            seen_container_ids.add(container.id)
            if self._passes_strict_filters(block, container):
                yield container

    @staticmethod
    def _matching_items_qs(block: GridBlock, container: MediaContainer) -> QuerySet[MediaItem]:
        items_qs = MediaItem.objects.filter(
            container=container,
            is_active=True,
            is_missing=False,
        )
        if block.min_duration_seconds_per_item is not None:
            items_qs = items_qs.filter(duration_seconds__gte=block.min_duration_seconds_per_item)
        if block.max_duration_seconds_per_item is not None:
            items_qs = items_qs.filter(duration_seconds__lte=block.max_duration_seconds_per_item)
        return items_qs

    def _passes_strict_filters(
        self,
        block: GridBlock,
        container: MediaContainer,
    ) -> bool:
        categories = self._container_categories(container)

        if not self._passes_allowed_categories(categories, self.editorial_line.allowed_categories):
            return False
        if not self._passes_allowed_categories(categories, block.allowed_categories):
            return False
        if self._intersects(categories, self.editorial_line.forbidden_categories):
            return False
        if self._intersects(categories, block.forbidden_categories):
            return False

        container_nature = self._container_nature(container)
        container_kind = self._container_kind(container)

        if not self._passes_allowed_choice(container_nature, self.editorial_line.allowed_natures):
            return False
        if not self._passes_allowed_choice(container_nature, block.allowed_natures):
            return False
        if self._matches_forbidden_choice(container_nature, self.editorial_line.forbidden_natures):
            return False
        if self._matches_forbidden_choice(container_nature, block.forbidden_natures):
            return False

        if not self._passes_allowed_choice(container_kind, self.editorial_line.allowed_container_kinds):
            return False
        if not self._passes_allowed_choice(container_kind, block.allowed_container_kinds):
            return False
        if self._matches_forbidden_choice(container_kind, self.editorial_line.forbidden_container_kinds):
            return False
        if self._matches_forbidden_choice(container_kind, block.forbidden_container_kinds):
            return False

        duration_min = container.duration_min_seconds or container.total_duration_seconds
        duration_max = container.duration_max_seconds or container.total_duration_seconds
        if block.min_duration_seconds_per_item is not None and duration_min is not None:
            if duration_min < block.min_duration_seconds_per_item:
                return False
        if block.max_duration_seconds_per_item is not None and duration_max is not None:
            if duration_max > block.max_duration_seconds_per_item:
                return False

        return True

    @staticmethod
    def _container_categories(container: MediaContainer) -> set[str]:
        values: set[str] = set()
        for source in (container.categories or [], container.genres or [], container.tags or []):
            for value in source:
                if isinstance(value, str) and value:
                    values.add(value)
        return values

    @staticmethod
    def _container_nature(container: MediaContainer):
        return getattr(container.media_collection, "nature", None)

    @staticmethod
    def _container_kind(container: MediaContainer):
        return getattr(container.media_collection, "container_kind", None)

    @staticmethod
    def _get_editorial_line(tv_channel: TvChannel) -> EditorialLine:
        try:
            return tv_channel.editorialline
        except ObjectDoesNotExist as exc:
            raise ValidationError("TvChannel must have an editorial line.") from exc

    @staticmethod
    def _passes_allowed_categories(container_categories: set[str], allowed_categories: list[str]) -> bool:
        allowed = {value for value in (allowed_categories or []) if isinstance(value, str)}
        if not allowed:
            return True
        return bool(container_categories.intersection(allowed))

    @staticmethod
    def _intersects(left: set[str], right: list[str]) -> bool:
        values = {value for value in (right or []) if isinstance(value, str)}
        return bool(left.intersection(values))

    @staticmethod
    def _passes_allowed_choice(value, allowed_values: list) -> bool:
        allowed = TvScheduleMatchingService._choice_values(allowed_values or [])
        if not allowed:
            return True
        return bool(TvScheduleMatchingService._choice_values([value]).intersection(allowed))

    @staticmethod
    def _matches_forbidden_choice(value, forbidden_values: list) -> bool:
        forbidden = TvScheduleMatchingService._choice_values(forbidden_values or [])
        if not forbidden:
            return False
        return bool(TvScheduleMatchingService._choice_values([value]).intersection(forbidden))

    @staticmethod
    def _choice_values(values) -> set[str]:
        normalized: set[str] = set()
        for value in values:
            if value is None:
                continue
            normalized.add(str(value))
            enum_value = getattr(value, "value", None)
            if enum_value is not None:
                normalized.add(str(enum_value))
            enum_name = getattr(value, "name", None)
            if enum_name is not None:
                normalized.add(str(enum_name))
        return normalized
