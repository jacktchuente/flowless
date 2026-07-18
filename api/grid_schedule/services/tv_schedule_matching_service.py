from __future__ import annotations

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import QuerySet

from project_ops.constants import AnalyzeStatus
from grid_schedule.services import editorial_matching
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
        if not editorial_matching.container_passes_rules(container, (self.editorial_line, block)):
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
    def _get_editorial_line(tv_channel: TvChannel) -> EditorialLine:
        try:
            return tv_channel.editorialline
        except ObjectDoesNotExist as exc:
            raise ValidationError("TvChannel must have an editorial line.") from exc
