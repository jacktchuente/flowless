from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
import logging

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone

from editorial_planning.models import EditorialSegmentMembership, EditorialSegmentMembershipStatus
from grid_schedule.constants import ScheduledContainerStatus
from grid_schedule.models import FlexiblePlayoutSelection, ScheduleMediaItem, TvPlayout
from grid_schedule.services.playout_repair_service import PlayoutRepairService
from grid_schedule.services.playout_validation_service import PlayoutValidationService
from grid_schedule.services.post_roll_filler_service import PostRollFillerService
from media_source.constants import MediaProgrammingRole
from media_source.models import MediaContainer, MediaItem
from tv_channel.models import EditorialLine, GridLayout, GridLayoutMode, TvChannel

logger = logging.getLogger(__name__)


@dataclass
class FlexibleGenerationResult:
    tv_playout: TvPlayout
    created: bool
    generated_items: int
    warnings: list[str]
    filled_items: int = 0
    repaired_gaps: int = 0
    trimmed_overlaps: int = 0
    issues: list[dict] = field(default_factory=list)
    window_start: datetime | None = None
    window_end: datetime | None = None


class FlexibleTvPlayoutGenerationService:
    LOOKBACK_HOURS = 600
    PLAYABLE_MEMBERSHIP_STATUSES = (
        EditorialSegmentMembershipStatus.ACCEPTED,
        EditorialSegmentMembershipStatus.MANUAL_OVERRIDE,
    )
    OVERFLOW_STRICT = "strict"
    OVERFLOW_SOFT = "soft"

    def __init__(self, *, tv_channel: TvChannel, days: int, reset: bool = False):
        self.tv_channel = tv_channel
        self.days = days
        self.reset = reset
        self.editorial_line = self._get_editorial_line(tv_channel)
        self.grid_layout: GridLayout | None = None
        self.overflow_mode = str(settings.FLEXIBLE_PLAYOUT_OVERFLOW_MODE).strip().lower()
        if self.overflow_mode not in (self.OVERFLOW_STRICT, self.OVERFLOW_SOFT):
            self.overflow_mode = self.OVERFLOW_STRICT

    @property
    def day_start(self) -> time:
        return self.editorial_line.start_at

    @property
    def day_end(self) -> time:
        return self.editorial_line.end_at

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
            consecutive_misses = 0
            max_iterations = max(1, len(path_elements) * 500)

            for _ in range(max_iterations):
                if cursor >= end_at:
                    break

                day_end_at = self._resolve_day_end_at(cursor)
                if cursor >= day_end_at:
                    cursor = self._next_day_start_at(cursor)
                    continue

                if self.overflow_mode == self.OVERFLOW_SOFT:
                    fit_window_end = end_at
                else:
                    fit_window_end = min(day_end_at, end_at)

                path_element = path_elements[path_index % len(path_elements)]
                path_index += 1
                remaining_seconds = int((fit_window_end - cursor).total_seconds())
                selection_data = self._select_next_container(
                    segment_id=path_element.segment_id,
                    remaining_seconds=remaining_seconds,
                    history=history,
                )
                if selection_data is None:
                    warnings.append(f"No flexible candidate for segment {path_element.segment_id}.")
                    consecutive_misses += 1
                    if consecutive_misses >= len(path_elements):
                        consecutive_misses = 0
                        next_day_start_at = self._next_day_start_at(cursor)
                        if next_day_start_at >= end_at:
                            warnings.append("No flexible candidate for any segment of the path, stopping generation.")
                            break
                        warnings.append("No flexible candidate fits the current day window, moving to the next day.")
                        cursor = next_day_start_at
                    continue
                consecutive_misses = 0

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
                    window_end=fit_window_end,
                )
                if scheduled is None:
                    warnings.append(f"Could not schedule item {item.id}.")
                    break

                self._mark_history_after_schedule(history, scheduled)
                generated_items += 1
                cursor = scheduled.post_roll_filler_ends_at or scheduled.ends_at

            if generated_items == 0:
                warnings.append("Flexible playout generated no item.")

            filled_items = 0
            if self.editorial_line.allow_filler:
                filler_result = PostRollFillerService(
                    tv_playout=tv_playout,
                    window_start=start_at,
                    window_end=end_at,
                ).fill()
                filled_items = filler_result.created_items
                warnings.extend(filler_result.warnings)
                logger.info(
                    "FlexibleTvPlayoutGenerationService.generate post-roll fill done playout_id=%s filled_items=%s",
                    tv_playout.id,
                    filled_items,
                )

            repair_result = PlayoutRepairService(
                tv_playout=tv_playout,
                editorial_line=self.editorial_line,
                window_start=start_at,
                window_end=end_at,
            ).repair()

            issues = PlayoutValidationService(
                tv_playout=tv_playout,
                editorial_line=self.editorial_line,
            ).validate()

            return FlexibleGenerationResult(
                tv_playout=tv_playout,
                created=created,
                generated_items=generated_items,
                warnings=warnings,
                filled_items=filled_items,
                repaired_gaps=repair_result.repaired_gaps,
                trimmed_overlaps=repair_result.trimmed_overlaps,
                issues=issues,
                window_start=start_at,
                window_end=end_at,
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
            hour=self.day_start.hour,
            minute=self.day_start.minute,
            second=self.day_start.second,
            microsecond=0,
        )
        if now.time() < self.day_start:
            cycle_anchor -= timedelta(days=1)
        return cycle_anchor

    def _resolve_day_end_at(self, cursor: datetime) -> datetime:
        day_anchor = cursor.replace(
            hour=self.day_start.hour,
            minute=self.day_start.minute,
            second=self.day_start.second,
            microsecond=0,
        )
        if cursor.time() < self.day_start:
            day_anchor -= timedelta(days=1)
        day_end_at = day_anchor.replace(
            hour=self.day_end.hour,
            minute=self.day_end.minute,
            second=self.day_end.second,
        )
        if self.day_end <= self.day_start:
            day_end_at += timedelta(days=1)
        return day_end_at

    def _next_day_start_at(self, cursor: datetime) -> datetime:
        candidate = cursor.replace(
            hour=self.day_start.hour,
            minute=self.day_start.minute,
            second=self.day_start.second,
            microsecond=0,
        )
        while candidate <= cursor:
            candidate += timedelta(days=1)
        return candidate

    def _delete_future_items_and_rollback_cursors(self, *, tv_playout: TvPlayout, start_at: datetime) -> None:
        # Enfants post-roll dont le parent (avant start_at) est conserve mais dont la
        # fenetre depasse start_at: le CASCADE ne les couvre pas, suppression explicite.
        ScheduleMediaItem.objects.filter(
            parent_schedule_item__flexible_selection__tv_playout=tv_playout,
            starts_at__gte=start_at,
        ).delete()
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
        # Secondary memberships (multi-segment media) are playable too, as
        # long as their status was accepted or manually overridden.
        memberships = (
            EditorialSegmentMembership.objects.filter(
                Q(media_container__media_collection__programming_role__isnull=True)
                | Q(media_container__media_collection__programming_role=MediaProgrammingRole.MAIN),
                segment_id=segment_id,
                status__in=self.PLAYABLE_MEMBERSHIP_STATUSES,
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
            duration_seconds = item.duration_seconds or 0
            if duration_seconds <= 0:
                continue
            occupied_seconds = self._scheduled_occupied_duration_seconds(duration_seconds)
            if occupied_seconds <= remaining_seconds:
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
