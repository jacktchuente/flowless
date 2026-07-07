import logging
from datetime import datetime, timedelta

from django.db.models import Q

from grid_schedule.models import ScheduleMediaItem, TvPlayout
from media_source.constants import MediaProgrammingRole

logger = logging.getLogger(__name__)

GAP_THRESHOLD_SECONDS = 120


def make_issue(
    code: str,
    severity: str,
    message: str,
    *,
    schedule_item_id: int | None = None,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
) -> dict:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "schedule_item_id": schedule_item_id,
        "starts_at": starts_at.isoformat() if starts_at else None,
        "ends_at": ends_at.isoformat() if ends_at else None,
    }


def load_playout_timeline(tv_playout: TvPlayout) -> tuple[list[ScheduleMediaItem], dict[int, list[ScheduleMediaItem]]]:
    """Items MAIN ordonnes + enfants post-roll groupes par parent."""
    main_items = list(
        ScheduleMediaItem.objects
        .filter(
            Q(block_container_selection__tv_playout=tv_playout)
            | Q(flexible_selection__tv_playout=tv_playout),
        )
        .select_related(
            "item",
            "block_container_selection__block__post_filler_policy",
            "block_container_selection__media_container",
        )
        .order_by("starts_at", "id")
    )
    children_by_parent: dict[int, list[ScheduleMediaItem]] = {}
    children = (
        ScheduleMediaItem.objects
        .filter(parent_schedule_item__in=[item.id for item in main_items])
        .order_by("starts_at", "id")
    )
    for child in children:
        children_by_parent.setdefault(child.parent_schedule_item_id, []).append(child)
    return main_items, children_by_parent


def occupied_end(main_item: ScheduleMediaItem, children: list[ScheduleMediaItem]) -> datetime:
    end = main_item.post_roll_filler_ends_at or main_item.ends_at
    for child in children:
        if child.ends_at > end:
            end = child.ends_at
    return end


class PlayoutValidationService:
    """Validation commune aux deux modes de generation.

    Retourne des issues serialisables ({code, severity, message, ...});
    ne leve jamais - la decision d'echouer appartient a l'appelant.
    """

    def __init__(self, *, tv_playout: TvPlayout, editorial_line=None):
        self.tv_playout = tv_playout
        self.editorial_line = editorial_line

    def validate(self, *, occurrences=None) -> list[dict]:
        issues: list[dict] = []
        main_items, children_by_parent = load_playout_timeline(self.tv_playout)

        previous = None
        previous_occupied = None
        for main_item in main_items:
            children = children_by_parent.get(main_item.id, [])
            issues.extend(self._check_bounds(main_item))
            issues.extend(self._check_container_mismatch(main_item))
            for child in children:
                issues.extend(self._check_bounds(child))
                issues.extend(self._check_child_window(main_item, child))

            if previous is not None:
                if main_item.starts_at < previous_occupied:
                    issues.append(
                        make_issue(
                            "overlap",
                            "error",
                            f"Overlap between scheduled item {previous.id} and {main_item.id}.",
                            schedule_item_id=main_item.id,
                            starts_at=main_item.starts_at,
                            ends_at=previous_occupied,
                        )
                    )
                else:
                    issues.extend(self._check_gap(previous_occupied, main_item))

            previous = main_item
            previous_occupied = occupied_end(main_item, children)

        if occurrences is not None:
            issues.extend(self._check_block_occurrences(occurrences))

        return issues

    @staticmethod
    def _check_bounds(scheduled: ScheduleMediaItem) -> list[dict]:
        if scheduled.ends_at <= scheduled.starts_at:
            return [
                make_issue(
                    "invalid_bounds",
                    "error",
                    f"Scheduled item {scheduled.id} has invalid time bounds.",
                    schedule_item_id=scheduled.id,
                    starts_at=scheduled.starts_at,
                    ends_at=scheduled.ends_at,
                )
            ]
        return []

    @staticmethod
    def _check_container_mismatch(main_item: ScheduleMediaItem) -> list[dict]:
        if main_item.block_container_selection_id is None:
            return []
        if main_item.item.container_id != main_item.block_container_selection.media_container_id:
            return [
                make_issue(
                    "item_container_mismatch",
                    "error",
                    f"Scheduled item {main_item.id} item/container mismatch.",
                    schedule_item_id=main_item.id,
                )
            ]
        return []

    @staticmethod
    def _check_child_window(main_item: ScheduleMediaItem, child: ScheduleMediaItem) -> list[dict]:
        window_end = main_item.post_roll_filler_ends_at or main_item.ends_at
        if child.starts_at < main_item.ends_at or child.ends_at > window_end:
            return [
                make_issue(
                    "child_outside_window",
                    "warning",
                    f"Post-roll item {child.id} exceeds the window of its parent {main_item.id}.",
                    schedule_item_id=child.id,
                    starts_at=child.starts_at,
                    ends_at=child.ends_at,
                )
            ]
        return []

    def _check_gap(self, previous_occupied: datetime, main_item: ScheduleMediaItem) -> list[dict]:
        gap_seconds = int((main_item.starts_at - previous_occupied).total_seconds())
        if gap_seconds <= GAP_THRESHOLD_SECONDS:
            return []
        severity = "warning" if self._gap_intersects_editorial_day(previous_occupied, main_item.starts_at) else "info"
        return [
            make_issue(
                "gap",
                severity,
                f"Gap of {gap_seconds}s before scheduled item {main_item.id}.",
                schedule_item_id=main_item.id,
                starts_at=previous_occupied,
                ends_at=main_item.starts_at,
            )
        ]

    def _gap_intersects_editorial_day(self, gap_start: datetime, gap_end: datetime) -> bool:
        if self.editorial_line is None:
            return True
        day_start = gap_start.replace(
            hour=self.editorial_line.start_at.hour,
            minute=self.editorial_line.start_at.minute,
            second=self.editorial_line.start_at.second,
            microsecond=0,
        )
        if gap_start.time() < self.editorial_line.start_at:
            day_start -= timedelta(days=1)
        day_end = day_start.replace(
            hour=self.editorial_line.end_at.hour,
            minute=self.editorial_line.end_at.minute,
            second=self.editorial_line.end_at.second,
        )
        if self.editorial_line.end_at <= self.editorial_line.start_at:
            day_end += timedelta(days=1)
        return gap_start < day_end and gap_end > day_start

    def _check_block_occurrences(self, occurrences) -> list[dict]:
        issues: list[dict] = []
        for occurrence in occurrences:
            qs = ScheduleMediaItem.objects.filter(
                block_container_selection__tv_playout=self.tv_playout,
                block_container_selection__block=occurrence.block,
                starts_at__lt=occurrence.ends_at,
                ends_at__gt=occurrence.starts_at,
            ).order_by("starts_at")
            for scheduled in qs:
                end = scheduled.post_roll_filler_ends_at or scheduled.ends_at
                if scheduled.starts_at < occurrence.starts_at or end > occurrence.ends_at:
                    issues.append(
                        make_issue(
                            "outside_block_occurrence",
                            "warning",
                            f"Scheduled item {scheduled.id} falls outside its block occurrence.",
                            schedule_item_id=scheduled.id,
                            starts_at=scheduled.starts_at,
                            ends_at=end,
                        )
                    )
        return issues
