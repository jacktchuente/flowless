from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max, Q
# Les tests patchent timezone.now via ce module (la plomberie qui l'appelle
# vit dans BasePlayoutGenerationService, le module django est partage).
from django.utils import timezone  # noqa: F401

from grid_schedule.constants import ScheduledContainerStatus
from grid_schedule.models import BlockContainerSelection, ScheduleMediaItem, TvPlayout
from grid_schedule.services import editorial_matching
from grid_schedule.services.base_playout_generation_service import (
    BasePlayoutGenerationService,
    PlayoutGenerationResult,
)
from grid_schedule.services.playout_repair_service import PlayoutRepairService
from grid_schedule.services.playout_validation_service import PlayoutValidationService
from grid_schedule.services.post_roll_filler_service import PostRollFillerService
from media_source.constants import MediaProgrammingRole
from media_source.models import MediaContainer, MediaItem
from project_ops.constants import AnalyzeStatus
from tv_channel.models import GridBlock, GridLayout, TvChannel
from tv_channel.services.editorial_rules_validation import STRING_RULE_AXES

logger = logging.getLogger(__name__)


@dataclass
class CandidateScore:
    media_container: MediaContainer
    score: float
    reasons: dict = field(default_factory=dict)


@dataclass
class BlockOccurrence:
    block: GridBlock
    starts_at: datetime
    ends_at: datetime


GenerationResult = PlayoutGenerationResult


class NextItemState(Enum):
    READY = "ready"
    NO_NEXT_ITEM = "no_next_item"
    DOES_NOT_FIT = "does_not_fit"


@dataclass
class NextItemResult:
    state: NextItemState
    item: MediaItem | None = None


class TvPlayoutGenerationService(BasePlayoutGenerationService):
    selection_field = "block_container_selection"
    selection_model = BlockContainerSelection

    def generate(self) -> GenerationResult:
        if self.days <= 0:
            raise ValidationError("days must be > 0")
        logger.info(
            "TvPlayoutGenerationService.generate starting channel_id=%s channel_name=%s days=%s reset=%s extend=%s",
            self.tv_channel.id,
            self.tv_channel.name,
            self.days,
            self.reset,
            self.extend,
        )

        with transaction.atomic():
            tv_channel = TvChannel.objects.select_for_update().get(pk=self.tv_channel.pk)
            self.editorial_line = self._get_editorial_line(tv_channel)
            grid_layout = self._validate_channel(tv_channel)
            logger.info(
                "TvPlayoutGenerationService.generate validated channel_id=%s grid_layout_id=%s",
                tv_channel.id,
                grid_layout.id,
            )

            tv_playout, created = self._get_or_create_playout(tv_channel, grid_layout=grid_layout, reset=self.reset)
            start_at = self._resolve_window_start(tv_playout)
            end_at = self._resolve_window_end(start_at)
            logger.info(
                "TvPlayoutGenerationService.generate playout ready channel_id=%s playout_id=%s created=%s window_start=%s window_end=%s",
                tv_channel.id,
                tv_playout.id,
                created,
                start_at.isoformat(),
                end_at.isoformat(),
            )

            cleanup_start = self._delete_future_items_and_rollback_cursors(tv_playout=tv_playout, start_at=start_at)
            adjusted_start = self._resolve_post_cleanup_window_start(
                tv_playout=tv_playout,
                cleanup_start=cleanup_start,
            )
            if adjusted_start > start_at:
                start_at = adjusted_start
                if not self.extend:
                    end_at = start_at + timedelta(days=self.days)
            logger.info(
                "TvPlayoutGenerationService.generate future items cleanup done playout_id=%s start_at=%s",
                tv_playout.id,
                start_at.isoformat(),
            )

            occurrences = self._build_block_occurrences(grid_layout, start_at, end_at)
            history = self._build_history(tv_playout=tv_playout, tv_channel=tv_channel, start_at=start_at)
            logger.info(
                "TvPlayoutGenerationService.generate planning data ready playout_id=%s occurrences=%s history_containers=%s",
                tv_playout.id,
                len(occurrences),
                len(history["container_counts"]),
            )

            candidates_by_block: dict[int, list[CandidateScore]] = {}
            for block in grid_layout.gridblock_set.all().order_by("starts_at", "id"):
                candidates_by_block[block.id] = self._build_candidates_for_block(
                    tv_channel=tv_channel,
                    block=block,
                    history=history,
                )
                logger.info(
                    "TvPlayoutGenerationService.generate candidates built playout_id=%s block_id=%s block=%s candidates=%s",
                    tv_playout.id,
                    block.id,
                    self._block_label(block),
                    len(candidates_by_block[block.id]),
                )

            self._prime_initial_block_selections(
                tv_playout=tv_playout,
                grid_layout=grid_layout,
                candidates_by_block=candidates_by_block,
                history=history,
            )

            generated_items = 0
            warnings: list[str] = []

            for occurrence in occurrences:
                logger.info(
                    "TvPlayoutGenerationService.generate scheduling occurrence playout_id=%s block_id=%s block=%s starts_at=%s ends_at=%s candidates=%s",
                    tv_playout.id,
                    occurrence.block.id,
                    self._block_label(occurrence.block),
                    occurrence.starts_at.isoformat(),
                    occurrence.ends_at.isoformat(),
                    len(candidates_by_block.get(occurrence.block.id, [])),
                )
                created_count, block_warnings = self._schedule_block_occurrence(
                    tv_playout=tv_playout,
                    occurrence=occurrence,
                    candidates=candidates_by_block.get(occurrence.block.id, []),
                    history=history,
                )
                generated_items += created_count
                warnings.extend(block_warnings)
                logger.info(
                    "TvPlayoutGenerationService.generate occurrence done playout_id=%s block_id=%s generated_items=%s warnings=%s",
                    tv_playout.id,
                    occurrence.block.id,
                    created_count,
                    len(block_warnings),
                )
                for warning in block_warnings:
                    logger.warning(
                        "TvPlayoutGenerationService.generate warning playout_id=%s block_id=%s message=%s",
                        tv_playout.id,
                        occurrence.block.id,
                        warning,
                    )

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
                    "TvPlayoutGenerationService.generate post-roll fill done playout_id=%s filled_items=%s",
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
            ).validate(occurrences=occurrences)

            mismatches = [issue for issue in issues if issue["code"] == "item_container_mismatch"]
            if mismatches:
                logger.error(
                    "TvPlayoutGenerationService.generate validation failed playout_id=%s errors=%s",
                    tv_playout.id,
                    mismatches,
                )
                raise ValidationError([issue["message"] for issue in mismatches])

            logger.info(
                "TvPlayoutGenerationService.generate completed channel_id=%s playout_id=%s generated_items=%s warnings=%s issues=%s",
                tv_channel.id,
                tv_playout.id,
                generated_items,
                len(warnings),
                len(issues),
            )
            return GenerationResult(
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
            GridLayout.objects
            .filter(tv_channel=tv_channel, is_active=True)
            .order_by("-created_at", "-id")
            .first()
        )
        if grid_layout is None:
            raise ValidationError("TvChannel must have an active grid layout.")
        if not tv_channel.is_enabled:
            raise ValidationError("TvChannel is disabled.")
        return grid_layout

    def _rollback_selection_status(self, selection: BlockContainerSelection, last_scheduled) -> int:
        if self._selection_has_next_item(selection):
            return ScheduledContainerStatus.PENDING
        if last_scheduled:
            return ScheduledContainerStatus.COMPLETED
        return ScheduledContainerStatus.PENDING

    def _build_block_occurrences(
        self,
        grid_layout: GridLayout,
        window_start: datetime,
        window_end: datetime,
    ) -> list[BlockOccurrence]:
        occurrences: list[BlockOccurrence] = []
        current_day = (window_start - timedelta(days=1)).date()
        last_day = (window_end + timedelta(days=1)).date()
        blocks = list(grid_layout.gridblock_set.all().order_by("starts_at", "id"))

        while current_day <= last_day:
            for block in blocks:
                starts_at = datetime.combine(current_day, block.starts_at, tzinfo=window_start.tzinfo)
                ends_at = datetime.combine(current_day, block.ends_at, tzinfo=window_start.tzinfo)
                if block.ends_at <= block.starts_at:
                    ends_at += timedelta(days=1)

                if ends_at > window_start and starts_at < window_end:
                    occurrences.append(
                        BlockOccurrence(
                            block=block,
                            starts_at=max(starts_at, window_start),
                            ends_at=min(ends_at, window_end),
                        )
                    )
            current_day += timedelta(days=1)

        occurrences.sort(key=lambda value: (value.starts_at, value.block.starts_at, value.block.id))
        return occurrences

    def _prime_initial_block_selections(
        self,
        *,
        tv_playout: TvPlayout,
        grid_layout: GridLayout,
        candidates_by_block: dict[int, list[CandidateScore]],
        history: dict,
    ) -> None:
        blocks = list(grid_layout.gridblock_set.all().order_by("-priority", "starts_at", "id"))
        for block in blocks:
            current_selection = self._get_current_selection(tv_playout=tv_playout, block=block)
            if current_selection is not None:
                continue

            selection = self._create_next_selection_for_block(
                tv_playout=tv_playout,
                block=block,
                candidates=candidates_by_block.get(block.id, []),
                history=history,
            )
            if selection is None:
                logger.info(
                    "TvPlayoutGenerationService.prime no selection channel_id=%s playout_id=%s block_id=%s block=%s",
                    self.tv_channel.id,
                    tv_playout.id,
                    block.id,
                    self._block_label(block),
                )
                continue

            logger.info(
                "TvPlayoutGenerationService.prime selection reserved channel_id=%s playout_id=%s block_id=%s selection_id=%s media_container_id=%s priority=%s",
                self.tv_channel.id,
                tv_playout.id,
                block.id,
                selection.id,
                selection.media_container_id,
                block.priority,
            )

    def _build_history(self, *, tv_playout: TvPlayout, tv_channel: TvChannel, start_at: datetime) -> dict:
        lookback_start = start_at - timedelta(hours=self.LOOKBACK_HOURS)
        past_items = (
            ScheduleMediaItem.objects
            .filter(
                block_container_selection__tv_playout__tv_channel=tv_channel,
                starts_at__gte=lookback_start,
                starts_at__lt=start_at,
            )
            .select_related("item", "item__container", "block_container_selection__block")
            .order_by("starts_at")
        )

        container_counts = Counter()
        last_item_by_selection: dict[int, int] = {}
        last_end_by_container: dict[int, datetime] = {}
        last_block_id_by_container: dict[int, int] = {}

        for scheduled in past_items:
            container_id = scheduled.item.container_id
            container_counts[container_id] += 1
            last_item_by_selection[scheduled.block_container_selection_id] = scheduled.item_id
            last_end_by_container[container_id] = scheduled.post_roll_filler_ends_at or scheduled.ends_at
            last_block_id_by_container[container_id] = scheduled.block_container_selection.block_id

        used_container_ids_by_block: dict[int, set[int]] = defaultdict(set)
        used_container_ids_for_playout: set[int] = set()
        for block_id, container_id in (
            BlockContainerSelection.objects
            .filter(tv_playout=tv_playout)
            .values_list("block_id", "media_container_id")
        ):
            used_container_ids_by_block[block_id].add(container_id)
            used_container_ids_for_playout.add(container_id)

        return {
            "container_counts": container_counts,
            "last_item_by_selection": last_item_by_selection,
            "last_end_by_container": last_end_by_container,
            "last_block_id_by_container": last_block_id_by_container,
            "used_container_ids_for_playout": used_container_ids_for_playout,
            "used_container_ids_by_block": used_container_ids_by_block,
            "scheduled_in_run": [],
            "scheduled_item_ids_in_run": set(),
        }

    def _build_candidates_for_block(
        self,
        *,
        tv_channel: TvChannel,
        block: GridBlock,
        history: dict,
    ) -> list[CandidateScore]:
        qs = (
            MediaContainer.objects
            .filter(
                Q(media_collection__programming_role__isnull=True)
                | Q(media_collection__programming_role=MediaProgrammingRole.MAIN),
                analyze_status=AnalyzeStatus.COMPLETE,
                media_collection__is_active=True,
                is_missing=False,
            )
            .select_related("media_collection")
            .distinct()
            .order_by("id")
        )

        candidates: list[CandidateScore] = []
        seen_container_ids: set[int] = set()

        for container in qs.iterator():
            if container.id in seen_container_ids:
                continue
            if not self._passes_strict_filters(tv_channel, block, container):
                continue
            if not self._has_compatible_item(block, container):
                continue

            score = self._score_container(
                tv_channel=tv_channel,
                block=block,
                container=container,
                history=history,
            )
            candidates.append(score)
            seen_container_ids.add(container.id)

        candidates.sort(key=lambda candidate: candidate.score, reverse=True)
        if candidates:
            logger.info(
                "TvPlayoutGenerationService.candidates block_id=%s block=%s top_container_id=%s top_score=%.2f total=%s",
                block.id,
                self._block_label(block),
                candidates[0].media_container.id,
                candidates[0].score,
                len(candidates),
            )
        else:
            logger.warning(
                "TvPlayoutGenerationService.candidates block_id=%s block=%s no_candidates=true",
                block.id,
                self._block_label(block),
            )
        return candidates

    def _passes_strict_filters(self, tv_channel: TvChannel, block: GridBlock, container: MediaContainer) -> bool:
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

    def _has_compatible_item(self, block: GridBlock, container: MediaContainer) -> bool:
        return self._compatible_items_qs(block=block, container=container).exists()

    def _count_compatible_items(self, *, block: GridBlock, container: MediaContainer) -> int:
        return self._compatible_items_qs(block=block, container=container).count()

    def _compatible_items_qs(self, *, block: GridBlock, container: MediaContainer):
        qs = MediaItem.objects.filter(container=container, is_active=True, is_missing=False)
        if block.min_duration_seconds_per_item is not None:
            qs = qs.filter(duration_seconds__gte=block.min_duration_seconds_per_item)
        if block.max_duration_seconds_per_item is not None:
            qs = qs.filter(duration_seconds__lte=block.max_duration_seconds_per_item)
        return qs

    def _score_container(
        self,
        *,
        tv_channel: TvChannel,
        block: GridBlock,
        container: MediaContainer,
        history: dict,
    ) -> CandidateScore:
        score = 0.0
        reasons = {}

        for axis in STRING_RULE_AXES:
            axis_bonus = editorial_matching.preferred_values_bonus(
                editorial_matching.container_axis_values(container, axis),
                self.editorial_line.preferred.get(axis, []) + block.preferred.get(axis, []),
            )
            score += axis_bonus
            reasons[f"preferred_{axis}"] = axis_bonus

        nature_bonus = editorial_matching.preferred_choice_bonus(
            editorial_matching.container_nature(container),
            self.editorial_line.preferred.get("natures", []) + block.preferred.get("natures", []),
        )
        score += nature_bonus
        reasons["preferred_natures"] = nature_bonus

        kind_bonus = editorial_matching.preferred_choice_bonus(
            editorial_matching.container_kind(container),
            (
                self.editorial_line.preferred.get("container_kinds", [])
                + block.preferred.get("container_kinds", [])
            ),
        )
        score += kind_bonus
        reasons["preferred_container_kinds"] = kind_bonus

        priority_bonus = block.priority / 100.0
        score += priority_bonus
        reasons["block_priority"] = priority_bonus

        previous_count = history["container_counts"].get(container.id, 0)
        redundancy_penalty = min(previous_count * 0.5, 5.0)
        score -= redundancy_penalty
        reasons["redundancy_penalty"] = redundancy_penalty

        if history["last_block_id_by_container"].get(container.id) == block.id:
            score -= 0.75
            reasons["same_block_penalty"] = 0.75

        return CandidateScore(media_container=container, score=score, reasons=reasons)

    def _schedule_block_occurrence(
        self,
        *,
        tv_playout: TvPlayout,
        occurrence: BlockOccurrence,
        candidates: list[CandidateScore],
        history: dict,
    ) -> tuple[int, list[str]]:
        created_count = 0
        warnings: list[str] = []
        cursor = occurrence.starts_at
        block_duration_seconds = int((occurrence.ends_at - occurrence.starts_at).total_seconds())
        max_items = max(occurrence.block.max_items, 0)
        blocked_container_ids: set[int] = set()

        while cursor < occurrence.ends_at and created_count < max_items:
            remaining_seconds = int((occurrence.ends_at - cursor).total_seconds())
            if remaining_seconds <= 0:
                break

            selection = self._get_current_selection(tv_playout=tv_playout, block=occurrence.block)
            if selection is None:
                selection = self._create_next_selection_for_block(
                    tv_playout=tv_playout,
                    block=occurrence.block,
                    candidates=candidates,
                    history=history,
                    blocked_container_ids=blocked_container_ids,
                )
                if selection is None:
                    warnings.append(f"No compatible selection for block {self._block_label(occurrence.block)}")
                    break

            next_item = self._get_next_item_for_selection(
                selection=selection,
                remaining_seconds=remaining_seconds,
                history=history,
            )
            if next_item.state == NextItemState.NO_NEXT_ITEM:
                blocked_container_ids.add(selection.media_container_id)
                self._mark_selection_completed(selection)
                continue

            if next_item.state == NextItemState.DOES_NOT_FIT:
                duration_seconds = self._scheduled_occupied_duration_seconds(
                    occurrence.block,
                    next_item.item.duration_seconds if next_item.item else 0,
                )
                if duration_seconds > block_duration_seconds:
                    warnings.append(
                        f"Selection {selection.id} / block {self._block_label(occurrence.block)} has next item "
                        f"{next_item.item.id if next_item.item else None} longer than the full block; "
                        f"selection marked completed."
                    )
                    blocked_container_ids.add(selection.media_container_id)
                    self._mark_selection_completed(selection)
                    continue
                break

            if next_item.item is None:
                break

            scheduled = self._schedule_item(
                occurrence=occurrence,
                selection=selection,
                item=next_item.item,
                cursor=cursor,
                history=history,
            )
            if scheduled is None:
                break

            created_count += 1
            cursor = scheduled.post_roll_filler_ends_at or scheduled.ends_at

            if not self._selection_has_next_item(selection):
                self._mark_selection_completed(selection)

        if created_count < occurrence.block.min_items:
            warnings.append(
                f"Block {self._block_label(occurrence.block)} generated {created_count} item(s), "
                f"minimum expected is {occurrence.block.min_items}."
            )

        return created_count, warnings

    def _get_current_selection(self, *, tv_playout: TvPlayout, block: GridBlock) -> BlockContainerSelection | None:
        return (
            BlockContainerSelection.objects
            .filter(tv_playout=tv_playout, block=block, status=ScheduledContainerStatus.PENDING)
            .select_related("block", "media_container", "last_scheduled_item")
            .order_by("order", "id")
            .first()
        )

    def _create_next_selection_for_block(
        self,
        *,
        tv_playout: TvPlayout,
        block: GridBlock,
        candidates: list[CandidateScore],
        history: dict,
        blocked_container_ids: set[int] | None = None,
    ) -> BlockContainerSelection | None:
        unique_candidates = self._unique_candidates_by_container_id(candidates)
        if not unique_candidates:
            return None
        blocked_container_ids = blocked_container_ids or set()

        used_by_block: dict[int, set[int]] = history["used_container_ids_by_block"]
        used_for_playout: set[int] = history["used_container_ids_for_playout"]
        current_block_used = used_by_block.get(block.id, set())
        used_by_other_blocks = used_for_playout - current_block_used

        fresh_candidates: list[CandidateScore] = []
        same_block_replay_candidates: list[CandidateScore] = []
        cross_block_fallback_candidates: list[CandidateScore] = []
        last_resort_candidates: list[CandidateScore] = []

        for candidate in unique_candidates:
            container_id = candidate.media_container.id
            if container_id in blocked_container_ids:
                continue
            used_here = container_id in current_block_used
            used_elsewhere = container_id in used_by_other_blocks

            if not used_here and not used_elsewhere:
                fresh_candidates.append(candidate)
            elif used_here and not used_elsewhere:
                same_block_replay_candidates.append(candidate)
            elif not used_here and used_elsewhere:
                cross_block_fallback_candidates.append(candidate)
            else:
                last_resort_candidates.append(candidate)

        for pool in (
            fresh_candidates,
            same_block_replay_candidates,
            cross_block_fallback_candidates,
            last_resort_candidates,
        ):
            selection = self._create_first_selection_from_pool(
                tv_playout=tv_playout,
                block=block,
                pool=pool,
                history=history,
            )
            if selection is not None:
                return selection

        return None

    def _create_first_selection_from_pool(
        self,
        *,
        tv_playout: TvPlayout,
        block: GridBlock,
        pool: list[CandidateScore],
        history: dict,
    ) -> BlockContainerSelection | None:
        if not pool:
            return None

        max_order = (
            BlockContainerSelection.objects
            .filter(tv_playout=tv_playout, block=block)
            .aggregate(value=Max("order"))["value"]
            or 0
        )

        for candidate in pool:
            planned_item_count = self._count_compatible_items(block=block, container=candidate.media_container)
            if planned_item_count <= 0:
                continue

            selection = BlockContainerSelection.objects.create(
                tv_playout=tv_playout,
                block=block,
                order=max_order + 1,
                media_container=candidate.media_container,
                planned_item_count=planned_item_count,
                status=ScheduledContainerStatus.PENDING,
                last_scheduled_item=None,
            )
            container_id = candidate.media_container.id
            history["used_container_ids_for_playout"].add(container_id)
            history["used_container_ids_by_block"][block.id].add(container_id)
            logger.info(
                "TvPlayoutGenerationService.selection created playout_id=%s block_id=%s selection_id=%s media_container_id=%s planned_item_count=%s score=%.2f",
                tv_playout.id,
                block.id,
                selection.id,
                container_id,
                planned_item_count,
                candidate.score,
            )
            return selection

        return None

    @staticmethod
    def _unique_candidates_by_container_id(candidates: list[CandidateScore]) -> list[CandidateScore]:
        unique_candidates: list[CandidateScore] = []
        seen_container_ids: set[int] = set()
        for candidate in candidates:
            container_id = candidate.media_container.id
            if container_id in seen_container_ids:
                continue
            unique_candidates.append(candidate)
            seen_container_ids.add(container_id)
        return unique_candidates

    def _get_next_item_for_selection(
        self,
        *,
        selection: BlockContainerSelection,
        remaining_seconds: int,
        history: dict,
    ) -> NextItemResult:
        items = list(self._compatible_items_qs(block=selection.block, container=selection.media_container))
        if not items:
            return NextItemResult(NextItemState.NO_NEXT_ITEM)

        items.sort(key=self._media_item_sort_key)
        cursor_item = self._resolve_selection_cursor_item(selection=selection, history=history)
        if cursor_item is not None:
            cursor_key = self._media_item_sort_key(cursor_item)
            items = [item for item in items if self._media_item_sort_key(item) > cursor_key]
        if not items:
            return NextItemResult(NextItemState.NO_NEXT_ITEM)

        next_item = items[0]
        occupied_duration_seconds = self._scheduled_occupied_duration_seconds(
            selection.block,
            next_item.duration_seconds or 0,
        )
        if occupied_duration_seconds <= 0:
            return NextItemResult(NextItemState.NO_NEXT_ITEM)
        if occupied_duration_seconds > remaining_seconds:
            return NextItemResult(NextItemState.DOES_NOT_FIT, item=next_item)
        return NextItemResult(NextItemState.READY, item=next_item)

    def _selection_has_next_item(self, selection: BlockContainerSelection) -> bool:
        result = self._get_next_item_for_selection(
            selection=selection,
            remaining_seconds=10 ** 12,
            history={"last_item_by_selection": {}},
        )
        return result.state == NextItemState.READY

    def _resolve_selection_cursor_item(self, *, selection: BlockContainerSelection, history: dict) -> MediaItem | None:
        if selection.last_scheduled_item_id:
            return selection.last_scheduled_item

        fallback_item_id = (history.get("last_item_by_selection") or {}).get(selection.id)
        if not fallback_item_id:
            return None

        try:
            return MediaItem.objects.get(pk=fallback_item_id)
        except MediaItem.DoesNotExist:
            return None

    def _schedule_item(
        self,
        *,
        occurrence: BlockOccurrence,
        selection: BlockContainerSelection,
        item: MediaItem,
        cursor: datetime,
        history: dict,
    ) -> ScheduleMediaItem | None:
        duration_seconds = item.duration_seconds or 0
        if duration_seconds <= 0:
            return None

        item_end = cursor + timedelta(seconds=duration_seconds)
        if item_end > occurrence.ends_at:
            return None

        post_roll_filler_ends_at = self._resolve_post_roll_filler_end(
            block=occurrence.block,
            item_end=item_end,
            occurrence_end=occurrence.ends_at,
        )
        scheduled = ScheduleMediaItem.objects.create(
            added_to_playout=False,
            starts_at=cursor,
            ends_at=item_end,
            post_roll_filler_ends_at=post_roll_filler_ends_at,
            item=item,
            block_container_selection=selection,
        )
        logger.info(
            "TvPlayoutGenerationService.item scheduled playout_id=%s selection_id=%s block_id=%s item_id=%s starts_at=%s ends_at=%s filler_ends_at=%s",
            selection.tv_playout_id,
            selection.id,
            selection.block_id,
            item.id,
            cursor.isoformat(),
            item_end.isoformat(),
            post_roll_filler_ends_at.isoformat() if post_roll_filler_ends_at else None,
        )

        selection.last_scheduled_item = item
        if selection.status != ScheduledContainerStatus.PENDING:
            selection.status = ScheduledContainerStatus.PENDING
            selection.save(update_fields=["last_scheduled_item", "status"])
        else:
            selection.save(update_fields=["last_scheduled_item"])

        self._mark_history_after_schedule(history, scheduled)
        return scheduled

    def _mark_selection_completed(self, selection: BlockContainerSelection) -> None:
        if selection.status == ScheduledContainerStatus.COMPLETED:
            return
        selection.status = ScheduledContainerStatus.COMPLETED
        selection.save(update_fields=["status"])

    def _resolve_post_roll_filler_end(
        self,
        *,
        block: GridBlock,
        item_end: datetime,
        occurrence_end: datetime,
    ) -> datetime | None:
        return self._resolve_post_roll_filler_end_for_policy(
            policy=block.post_filler_policy if block.post_filler_policy_id else None,
            allow_filler=self.editorial_line.allow_filler,
            item_end=item_end,
            window_end=occurrence_end,
        )

    def _mark_history_after_schedule(self, history: dict, scheduled: ScheduleMediaItem) -> None:
        container_id = scheduled.item.container_id
        block_id = scheduled.block_container_selection.block_id
        history["container_counts"][container_id] += 1
        history["last_item_by_selection"][scheduled.block_container_selection_id] = scheduled.item_id
        history["last_end_by_container"][container_id] = scheduled.post_roll_filler_ends_at or scheduled.ends_at
        history["last_block_id_by_container"][container_id] = block_id
        history["used_container_ids_for_playout"].add(container_id)
        history["used_container_ids_by_block"][block_id].add(container_id)
        history["scheduled_in_run"].append(scheduled.id)
        history["scheduled_item_ids_in_run"].add(scheduled.item_id)

    def _scheduled_occupied_duration_seconds(self, block: GridBlock, item_duration_seconds: int) -> int:
        filler_seconds = 0
        if self.editorial_line.allow_filler and block.post_filler_policy_id:
            filler_seconds = block.post_filler_policy.duration_seconds or 0
        return item_duration_seconds + max(filler_seconds, 0)

    @staticmethod
    def _block_label(block: GridBlock) -> str:
        return f"{block.starts_at.strftime('%H:%M')}-{block.ends_at.strftime('%H:%M')}#{block.id}"
