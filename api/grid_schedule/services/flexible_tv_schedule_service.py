from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import logging

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from editorial_planning.models import EditorialSegmentMembership
from grid_schedule.constants import ScheduledContainerStatus
from grid_schedule.models import FlexiblePlayoutSelection, ScheduleMediaItem, TvPlayout
from media_source.models import MediaContainer, MediaItem
from tv_channel.models import EditorialLine, GridLayout, GridLayoutMode, TvChannel

logger = logging.getLogger(__name__)


@dataclass
class FlexibleGenerationResult:
    tv_playout: TvPlayout
    created: bool
    generated_items: int
    warnings: list[str]


class FlexibleTvPlayoutGenerationService:
    LOOKBACK_HOURS = 600

    def __init__(self, *, tv_channel: TvChannel, days: int, reset: bool = False):
        self.tv_channel = tv_channel
        self.days = days
        self.reset = reset
        self.editorial_line = self._get_editorial_line(tv_channel)
        self.grid_layout: GridLayout | None = None

    def generate(self) -> FlexibleGenerationResult:
        if self.days <= 0:
            raise ValidationError("days must be > 0")

        with transaction.atomic():
            tv_channel = TvChannel.objects.select_for_update().get(pk=self.tv_channel.pk)
            self.editorial_line = self._get_editorial_line(tv_channel)
            grid_layout = self._validate_channel(tv_channel)
            self.grid_layout = grid_layout
            planned_grid = self._get_planned_grid(grid_layout)
            path_elements = list(
                planned_grid.channel_candidate.segment_path.elements.select_related("segment").order_by("position", "id")
            )
            if not path_elements:
                raise ValidationError("Flexible grid must have an editorial segment path.")

            tv_playout, created = self._get_or_create_playout(tv_channel, grid_layout=grid_layout, reset=self.reset)
            start_at = self._resolve_window_start()
            end_at = start_at + timedelta(days=self.days)
            self._delete_future_items_and_rollback_cursors(tv_playout=tv_playout, start_at=start_at)

            history = self._build_history(tv_channel=tv_channel, start_at=start_at)
            generated_items = 0
            warnings: list[str] = []
            cursor = start_at
            path_index = 0
            max_iterations = max(1, len(path_elements) * 500)

            for _ in range(max_iterations):
                if cursor >= end_at:
                    break

                path_element = path_elements[path_index % len(path_elements)]
                path_index += 1
                remaining_seconds = int((end_at - cursor).total_seconds())
                selection_data = self._select_next_container(
                    segment_id=path_element.segment_id,
                    remaining_seconds=remaining_seconds,
                    history=history,
                )
                if selection_data is None:
                    warnings.append(f"No flexible candidate for segment {path_element.segment_id}.")
                    if path_index >= len(path_elements):
                        break
                    continue

                container, item = selection_data
                occupied_seconds = self._scheduled_occupied_duration_seconds(item.duration_seconds or 0)
                if occupied_seconds <= 0 or occupied_seconds > remaining_seconds:
                    warnings.append(f"Selected item {item.id} does not fit remaining flexible window.")
                    break

                selection = self._create_selection(
                    tv_playout=tv_playout,
                    segment_id=path_element.segment_id,
                    media_container=container,
                    path_position=path_element.position,
                    item=item,
                )
                scheduled = self._schedule_item(
                    selection=selection,
                    item=item,
                    cursor=cursor,
                    window_end=end_at,
                )
                if scheduled is None:
                    warnings.append(f"Could not schedule item {item.id}.")
                    break

                self._mark_history_after_schedule(history, scheduled)
                generated_items += 1
                cursor = scheduled.post_roll_filler_ends_at or scheduled.ends_at

            if generated_items == 0:
                warnings.append("Flexible playout generated no item.")

            return FlexibleGenerationResult(
                tv_playout=tv_playout,
                created=created,
                generated_items=generated_items,
                warnings=warnings,
            )

    def _validate_channel(self, tv_channel: TvChannel) -> GridLayout:
        grid_layout = (
            GridLayout.objects.select_related("post_filler_policy")
            .filter(tv_channel=tv_channel, is_active=True)
            .order_by("-created_at", "-id")
            .first()
        )
        if grid_layout is None:
            raise ValidationError("TvChannel must have an active grid layout.")
        if grid_layout.mode != GridLayoutMode.FLEXIBLE:
            raise ValidationError("Active grid layout is not flexible.")
        if not tv_channel.is_enabled:
            raise ValidationError("TvChannel is disabled.")
        return grid_layout

    @staticmethod
    def _get_planned_grid(grid_layout: GridLayout):
        try:
            return grid_layout.editorial_planning_source
        except ObjectDoesNotExist as exc:
            raise ValidationError("Flexible grid layout must be linked to an editorial planned grid.") from exc

    def _get_or_create_playout(
        self,
        tv_channel: TvChannel,
        *,
        grid_layout: GridLayout,
        reset: bool,
    ) -> tuple[TvPlayout, bool]:
        active_qs = TvPlayout.objects.select_for_update().filter(tv_channel=tv_channel, is_active=True)
        if reset:
            active_qs.update(is_active=False)
            return TvPlayout.objects.create(tv_channel=tv_channel, is_active=True, grid=grid_layout), True

        existing = active_qs.order_by("-created_at").first()
        if existing:
            if existing.grid_id != grid_layout.id:
                existing.grid = grid_layout
                existing.save(update_fields=["grid", "updated_at"])
            return existing, False

        return TvPlayout.objects.create(tv_channel=tv_channel, is_active=True, grid=grid_layout), True

    def _resolve_window_start(self) -> datetime:
        now = timezone.now()
        cycle_anchor = now.replace(
            hour=self.editorial_line.start_at.hour,
            minute=self.editorial_line.start_at.minute,
            second=self.editorial_line.start_at.second,
            microsecond=0,
        )
        if now.time() < self.editorial_line.start_at:
            cycle_anchor -= timedelta(days=1)
        return cycle_anchor

    def _delete_future_items_and_rollback_cursors(self, *, tv_playout: TvPlayout, start_at: datetime) -> None:
        future_qs = ScheduleMediaItem.objects.filter(
            flexible_selection__tv_playout=tv_playout,
            starts_at__gte=start_at,
        )
        affected_selection_ids = set(future_qs.values_list("flexible_selection_id", flat=True).distinct())
        future_qs.delete()
        if not affected_selection_ids:
            return

        selections = FlexiblePlayoutSelection.objects.filter(id__in=affected_selection_ids)
        for selection in selections:
            last_scheduled = (
                ScheduleMediaItem.objects.filter(flexible_selection=selection, starts_at__lt=start_at)
                .order_by("-starts_at", "-id")
                .select_related("item")
                .first()
            )
            selection.last_scheduled_item = last_scheduled.item if last_scheduled else None
            selection.status = ScheduledContainerStatus.COMPLETED if last_scheduled else ScheduledContainerStatus.PENDING
            selection.save(update_fields=["last_scheduled_item", "status"])

    def _build_history(self, *, tv_channel: TvChannel, start_at: datetime) -> dict:
        lookback_start = start_at - timedelta(hours=self.LOOKBACK_HOURS)
        past_items = (
            ScheduleMediaItem.objects.filter(
                starts_at__gte=lookback_start,
                starts_at__lt=start_at,
            )
            .filter(
                flexible_selection__tv_playout__tv_channel=tv_channel,
            )
            .select_related("item", "item__container", "flexible_selection")
            .order_by("starts_at")
        )
        container_counts = Counter()
        last_item_by_container: dict[int, int] = {}
        for scheduled in past_items:
            container_id = scheduled.item.container_id
            container_counts[container_id] += 1
            last_item_by_container[container_id] = scheduled.item_id

        return {
            "container_counts": container_counts,
            "last_item_by_container": last_item_by_container,
            "scheduled_item_ids_in_run": set(),
            "scheduled_container_ids_in_run": set(),
        }

    def _select_next_container(self, *, segment_id: int, remaining_seconds: int, history: dict):
        memberships = (
            EditorialSegmentMembership.objects.filter(
                segment_id=segment_id,
                is_primary=True,
                media_container__is_missing=False,
                media_container__media_collection__is_active=True,
            )
            .select_related("media_container")
            .order_by("-score", "media_container_id")
        )
        candidates = []
        for membership in memberships:
            container = membership.media_container
            item = self._get_next_item(container=container, remaining_seconds=remaining_seconds, history=history)
            if item is None:
                continue
            score = membership.score
            score -= history["container_counts"].get(container.id, 0) * 0.5
            if container.id in history["scheduled_container_ids_in_run"]:
                score -= 0.25
            candidates.append((score, container.id, container, item))

        if not candidates:
            return None
        candidates.sort(key=lambda value: (-value[0], value[1]))
        _, _, container, item = candidates[0]
        return container, item

    def _get_next_item(self, *, container: MediaContainer, remaining_seconds: int, history: dict) -> MediaItem | None:
        items = list(MediaItem.objects.filter(container=container, is_active=True, is_missing=False))
        if not items:
            return None
        items.sort(key=self._media_item_sort_key)

        last_item_id = history["last_item_by_container"].get(container.id)
        if last_item_id:
            last_item = next((item for item in items if item.id == last_item_id), None)
            if last_item is not None:
                last_key = self._media_item_sort_key(last_item)
                items = [item for item in items if self._media_item_sort_key(item) > last_key]

        items = [item for item in items if item.id not in history["scheduled_item_ids_in_run"]]
        for item in items:
            occupied_seconds = self._scheduled_occupied_duration_seconds(item.duration_seconds or 0)
            if occupied_seconds > 0 and occupied_seconds <= remaining_seconds:
                return item
        return None

    def _create_selection(
        self,
        *,
        tv_playout: TvPlayout,
        segment_id: int,
        media_container: MediaContainer,
        path_position: int,
        item: MediaItem,
    ) -> FlexiblePlayoutSelection:
        max_order = (
            FlexiblePlayoutSelection.objects.filter(tv_playout=tv_playout).aggregate(value=Max("order"))["value"] or 0
        )
        return FlexiblePlayoutSelection.objects.create(
            tv_playout=tv_playout,
            segment_id=segment_id,
            media_container=media_container,
            path_position=path_position,
            order=max_order + 1,
            planned_item_count=1,
            status=ScheduledContainerStatus.COMPLETED,
            last_scheduled_item=item,
        )

    def _schedule_item(
        self,
        *,
        selection: FlexiblePlayoutSelection,
        item: MediaItem,
        cursor: datetime,
        window_end: datetime,
    ) -> ScheduleMediaItem | None:
        duration_seconds = item.duration_seconds or 0
        if duration_seconds <= 0:
            return None
        item_end = cursor + timedelta(seconds=duration_seconds)
        if item_end > window_end:
            return None

        post_roll_filler_ends_at = self._resolve_post_roll_filler_end(item_end=item_end, window_end=window_end)
        return ScheduleMediaItem.objects.create(
            added_to_playout=False,
            starts_at=cursor,
            ends_at=item_end,
            post_roll_filler_ends_at=post_roll_filler_ends_at,
            item=item,
            flexible_selection=selection,
        )

    def _resolve_post_roll_filler_end(self, *, item_end: datetime, window_end: datetime) -> datetime | None:
        if not self.editorial_line.allow_filler:
            return None
        grid = self.grid_layout
        if grid is None or grid.post_filler_policy_id is None:
            return None
        filler_seconds = grid.post_filler_policy.duration_seconds or 0
        if filler_seconds <= 0:
            return None
        filler_end = item_end + timedelta(seconds=filler_seconds)
        if filler_end > window_end:
            return None
        return filler_end

    @staticmethod
    def _mark_history_after_schedule(history: dict, scheduled: ScheduleMediaItem) -> None:
        container_id = scheduled.item.container_id
        history["container_counts"][container_id] += 1
        history["last_item_by_container"][container_id] = scheduled.item_id
        history["scheduled_item_ids_in_run"].add(scheduled.item_id)
        history["scheduled_container_ids_in_run"].add(container_id)

    @staticmethod
    def _media_item_sort_key(item: MediaItem) -> tuple:
        is_episode = item.season_number is not None or item.episode_number is not None
        if is_episode:
            return (
                0,
                item.season_number if item.season_number is not None else 0,
                item.episode_number if item.episode_number is not None else 0,
                item.sequence_number if item.sequence_number is not None else 0,
                item.release_date or date.min,
                item.id,
            )
        return (
            1,
            item.sequence_number if item.sequence_number is not None else 0,
            item.release_date or date.min,
            item.id,
        )

    @staticmethod
    def _scheduled_occupied_duration_seconds_for_grid(grid: GridLayout, item_duration_seconds: int) -> int:
        filler_seconds = 0
        if grid.post_filler_policy_id:
            filler_seconds = grid.post_filler_policy.duration_seconds or 0
        return item_duration_seconds + max(filler_seconds, 0)

    def _scheduled_occupied_duration_seconds(self, item_duration_seconds: int) -> int:
        grid = self.grid_layout
        if grid is None:
            return item_duration_seconds
        return self._scheduled_occupied_duration_seconds_for_grid(grid, item_duration_seconds)

    @staticmethod
    def _get_editorial_line(tv_channel: TvChannel) -> EditorialLine:
        try:
            return tv_channel.editorialline
        except ObjectDoesNotExist as exc:
            raise ValidationError("TvChannel must have an editorial line.") from exc
