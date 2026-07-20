from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
import logging

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Max, Q
from django.utils import timezone

from grid_schedule.constants import ScheduledContainerStatus
from grid_schedule.models import ScheduleMediaItem, TvPlayout
from media_source.models import MediaItem
from tv_channel.models import EditorialLine, GridLayout, TvChannel

logger = logging.getLogger(__name__)


@dataclass
class PlayoutGenerationResult:
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


class BasePlayoutGenerationService:
    """
    Shared plumbing for the playout generation services (fixed blocks,
    flexible bottom-up, marathon). Subclasses set `selection_model` and
    `selection_field` (the ScheduleMediaItem FK name pointing to their
    selection model) and implement `generate()`.
    """

    LOOKBACK_HOURS = 600

    # ScheduleMediaItem FK name: "block_container_selection" | "flexible_selection"
    selection_field: str
    selection_model: type

    def __init__(self, *, tv_channel: TvChannel, days: int, reset: bool = False, extend: bool = False):
        self.tv_channel = tv_channel
        self.days = days
        self.reset = reset
        self.extend = extend
        self.editorial_line = self._get_editorial_line(tv_channel)

    @property
    def day_start(self) -> time:
        return self.editorial_line.start_at

    @property
    def day_end(self) -> time:
        return self.editorial_line.end_at

    @staticmethod
    def _get_editorial_line(tv_channel: TvChannel) -> EditorialLine:
        try:
            return tv_channel.editorialline
        except ObjectDoesNotExist as exc:
            raise ValidationError("TvChannel must have an editorial line.") from exc

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

    def _resolve_window_start(self, tv_playout: TvPlayout) -> datetime:
        now = timezone.now()
        cycle_anchor = now.replace(
            hour=self.day_start.hour,
            minute=self.day_start.minute,
            second=self.day_start.second,
            microsecond=0,
        )
        if now.time() < self.day_start:
            cycle_anchor -= timedelta(days=1)
        if self.extend and not self.reset:
            last_end = self._get_playout_last_end(tv_playout)
            if last_end is not None:
                return max(last_end, now)
        return cycle_anchor

    def _resolve_window_end(self, start_at: datetime) -> datetime:
        if self.extend and not self.reset:
            return self._align_end_to_editorial_day(timezone.now() + timedelta(days=self.days))
        return start_at + timedelta(days=self.days)

    def _align_end_to_editorial_day(self, end_at: datetime) -> datetime:
        """La fenetre de generation se termine a la fermeture de la journee
        editoriale, jamais en plein milieu: sans cela le programme s'arrete
        a l'heure d'execution de la tache d'extension periodique."""
        return max(end_at, self._resolve_day_end_at(end_at))

    def _get_playout_last_end(self, tv_playout: TvPlayout) -> datetime | None:
        bounds = ScheduleMediaItem.objects.filter(
            Q(**{f"{self.selection_field}__tv_playout": tv_playout})
            | Q(**{f"parent_schedule_item__{self.selection_field}__tv_playout": tv_playout}),
        ).aggregate(
            ends_at=Max("ends_at"),
            post_roll_filler_ends_at=Max("post_roll_filler_ends_at"),
        )
        values = [value for value in bounds.values() if value is not None]
        return max(values) if values else None

    def _resolve_post_cleanup_window_start(self, *, tv_playout: TvPlayout, cleanup_start: datetime) -> datetime:
        if self.reset:
            return cleanup_start
        last_end = self._get_playout_last_end(tv_playout)
        if last_end is None:
            return cleanup_start
        return max(cleanup_start, last_end)

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

    def _delete_future_items_and_rollback_cursors(self, *, tv_playout: TvPlayout, start_at: datetime) -> datetime:
        cleanup_start = start_at
        if not self.reset:
            cleanup_start = max(cleanup_start, timezone.now())
        # Enfants post-roll dont le parent (avant start_at) est conserve mais dont la
        # fenetre depasse start_at: le CASCADE ne les couvre pas, suppression explicite.
        ScheduleMediaItem.objects.filter(
            **{
                f"parent_schedule_item__{self.selection_field}__tv_playout": tv_playout,
                "starts_at__gte": cleanup_start,
            }
        ).delete()
        future_qs = ScheduleMediaItem.objects.filter(
            **{
                f"{self.selection_field}__tv_playout": tv_playout,
                "starts_at__gte": cleanup_start,
            }
        )
        affected_selection_ids = set(future_qs.values_list(f"{self.selection_field}_id", flat=True).distinct())
        deleted_count, _ = future_qs.delete()
        logger.info(
            "%s.cleanup playout_id=%s deleted_future_rows=%s affected_selections=%s",
            type(self).__name__,
            tv_playout.id,
            deleted_count,
            len(affected_selection_ids),
        )
        if not affected_selection_ids:
            return cleanup_start

        selections = self.selection_model.objects.filter(id__in=affected_selection_ids)
        for selection in selections:
            last_scheduled = (
                ScheduleMediaItem.objects.filter(
                    **{self.selection_field: selection, "starts_at__lt": cleanup_start}
                )
                .order_by("-starts_at", "-id")
                .select_related("item")
                .first()
            )
            selection.last_scheduled_item = last_scheduled.item if last_scheduled else None
            selection.status = self._rollback_selection_status(selection, last_scheduled)
            selection.save(update_fields=["last_scheduled_item", "status"])
        return cleanup_start

    def _rollback_selection_status(self, selection, last_scheduled) -> int:
        return ScheduledContainerStatus.COMPLETED if last_scheduled else ScheduledContainerStatus.PENDING

    @staticmethod
    def _resolve_post_roll_filler_end_for_policy(*, policy, allow_filler: bool, item_end: datetime, window_end: datetime) -> datetime | None:
        if not allow_filler or policy is None:
            return None
        filler_seconds = policy.duration_seconds or 0
        if filler_seconds <= 0:
            return None
        filler_end = item_end + timedelta(seconds=filler_seconds)
        if filler_end > window_end:
            return None
        return filler_end

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
