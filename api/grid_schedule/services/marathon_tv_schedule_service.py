from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Max, Q

from grid_schedule.constants import ScheduledContainerStatus
from grid_schedule.models import FlexiblePlayoutSelection, ScheduleMediaItem, TvPlayout
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
from tv_channel.models import GridLayout, GridLayoutMode, MarathonKindPolicy, TvChannel

logger = logging.getLogger(__name__)

MarathonGenerationResult = PlayoutGenerationResult


@dataclass
class _ContainerState:
    container: MediaContainer
    items: list[MediaItem]
    preferred: float
    last_scheduled_at: datetime | None = None
    last_item_id: int | None = None

    def lru_key(self) -> tuple:
        if self.last_scheduled_at is None:
            return (0, datetime.min.replace(tzinfo=None), -self.preferred, self.container.id)
        return (1, self.last_scheduled_at.replace(tzinfo=None), -self.preferred, self.container.id)

    def next_items(self, count: int) -> list[MediaItem]:
        """Next `count` items after the cursor; wraps back to the first item
        (S01E01) when the container is exhausted, without wrapping inside a
        single run."""
        if not self.items:
            return []
        start_index = 0
        if self.last_item_id is not None:
            for index, item in enumerate(self.items):
                if item.id == self.last_item_id:
                    start_index = index + 1
                    break
        if start_index >= len(self.items):
            start_index = 0
        return self.items[start_index:start_index + count]


@dataclass
class _KindState:
    policy: MarathonKindPolicy
    containers: list[_ContainerState] = field(default_factory=list)
    run_count: int = 0

    @property
    def quota(self) -> int:
        return max(self.policy.quota, 1)

    def eligible_containers(self) -> list[_ContainerState]:
        min_items = max(self.policy.min_run, 1)
        return [state for state in self.containers if len(state.items) >= min_items]


class MarathonPlayoutGenerationService(BasePlayoutGenerationService):
    """
    Rule-driven looping rotation: the editorial line alone defines the pool,
    kinds alternate by weighted round-robin (quota) and containers rotate by
    strict LRU inside their kind. Runs of min_run..max_run consecutive items
    never get truncated by the daily activity window: the cursor jumps to the
    next morning and the run resumes.
    """

    selection_field = "flexible_selection"
    selection_model = FlexiblePlayoutSelection

    MAX_RUNS_PER_DAY = 500

    grid_layout: GridLayout | None = None

    def generate(self) -> MarathonGenerationResult:
        if self.days <= 0:
            raise ValidationError("days must be > 0")

        with transaction.atomic():
            tv_channel = TvChannel.objects.select_for_update().get(pk=self.tv_channel.pk)
            self.editorial_line = self._get_editorial_line(tv_channel)
            grid_layout = self._validate_channel(tv_channel)
            self.grid_layout = grid_layout
            policies = self._get_enabled_policies(grid_layout)

            tv_playout, created = self._get_or_create_playout(tv_channel, grid_layout=grid_layout, reset=self.reset)
            start_at = self._resolve_window_start(tv_playout)
            end_at = self._resolve_window_end(start_at)
            cleanup_start = self._delete_future_items_and_rollback_cursors(tv_playout=tv_playout, start_at=start_at)
            adjusted_start = self._resolve_post_cleanup_window_start(
                tv_playout=tv_playout,
                cleanup_start=cleanup_start,
            )
            if adjusted_start > start_at:
                start_at = adjusted_start
                if not self.extend:
                    end_at = self._align_end_to_editorial_day(start_at + timedelta(days=self.days))

            kind_states = self._build_pool(
                tv_channel=tv_channel,
                tv_playout=tv_playout,
                policies=policies,
                start_at=start_at,
            )
            generated_items = 0
            warnings: list[str] = []

            if not any(state.eligible_containers() for state in kind_states.values()):
                warnings.append("No marathon candidate matches the editorial line and kind policies.")

            cursor = start_at
            max_runs = max(1, self.days) * self.MAX_RUNS_PER_DAY

            resumed = self._resume_unfinished_run(
                tv_playout=tv_playout,
                kind_states=kind_states,
                cursor=cursor,
                end_at=end_at,
                warnings=warnings,
            )
            if resumed is not None:
                generated_items += resumed[0]
                cursor = resumed[1]

            for _ in range(max_runs):
                if cursor >= end_at:
                    break
                day_end_at = self._resolve_day_end_at(cursor)
                if cursor >= day_end_at:
                    cursor = self._next_day_start_at(cursor)
                    continue

                kind_state = self._pick_kind(kind_states)
                if kind_state is None:
                    warnings.append("No marathon candidate left for any configured kind, stopping generation.")
                    break
                container_state = min(kind_state.eligible_containers(), key=_ContainerState.lru_key)
                run_items = container_state.next_items(max(kind_state.policy.max_run, 1))
                if not run_items:
                    warnings.append(f"Container {container_state.container.id} has no schedulable item.")
                    break

                selection = self._create_selection(
                    tv_playout=tv_playout,
                    media_container=container_state.container,
                    planned_item_count=len(run_items),
                )
                scheduled_count, cursor = self._schedule_run(
                    selection=selection,
                    container_state=container_state,
                    run_items=run_items,
                    cursor=cursor,
                    end_at=end_at,
                )
                generated_items += scheduled_count
                kind_state.run_count += 1
                if scheduled_count < len(run_items):
                    # Fin de fenetre de generation en plein run: la selection
                    # reste PENDING et sera reprise par la prochaine passe.
                    break

            if generated_items == 0 and start_at < end_at:
                warnings.append("Marathon playout generated no item.")

            filled_items = 0
            if self.editorial_line.allow_filler:
                filler_result = PostRollFillerService(
                    tv_playout=tv_playout,
                    window_start=start_at,
                    window_end=end_at,
                ).fill()
                filled_items = filler_result.created_items
                warnings.extend(filler_result.warnings)

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

            return MarathonGenerationResult(
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
        if grid_layout.mode != GridLayoutMode.MARATHON:
            raise ValidationError("Active grid layout is not marathon.")
        if not tv_channel.is_enabled:
            raise ValidationError("TvChannel is disabled.")
        return grid_layout

    @staticmethod
    def _get_enabled_policies(grid_layout: GridLayout) -> list[MarathonKindPolicy]:
        config = getattr(grid_layout, "marathon_config", None)
        if config is None:
            raise ValidationError("Marathon grid layout must have a marathon config.")
        policies = [policy for policy in config.kind_policies.all() if policy.max_run >= 1]
        if not policies:
            raise ValidationError("Marathon config must enable at least one container kind.")
        return policies

    def _build_pool(
        self,
        *,
        tv_channel: TvChannel,
        tv_playout: TvPlayout,
        policies: list[MarathonKindPolicy],
        start_at: datetime,
    ) -> dict[int, _KindState]:
        kind_states = {policy.container_kind: _KindState(policy=policy) for policy in policies}

        containers = (
            MediaContainer.objects
            .filter(
                Q(media_collection__programming_role__isnull=True)
                | Q(media_collection__programming_role=MediaProgrammingRole.MAIN),
                analyze_status=AnalyzeStatus.COMPLETE,
                media_collection__is_active=True,
                media_collection__container_kind__in=list(kind_states),
                is_missing=False,
            )
            .select_related("media_collection")
            .distinct()
            .order_by("id")
        )
        for container in containers:
            kind = editorial_matching.container_kind(container)
            kind_state = kind_states.get(kind)
            if kind_state is None:
                continue
            if not editorial_matching.container_passes_rules(container, (self.editorial_line,)):
                continue
            items = [
                item
                for item in MediaItem.objects.filter(container=container, is_active=True, is_missing=False)
                if (item.duration_seconds or 0) > 0
            ]
            if not items:
                continue
            items.sort(key=self._media_item_sort_key)
            kind_state.containers.append(
                _ContainerState(
                    container=container,
                    items=items,
                    preferred=editorial_matching.preferred_bonus(container, (self.editorial_line,)),
                )
            )

        self._apply_history(tv_channel=tv_channel, tv_playout=tv_playout, kind_states=kind_states, start_at=start_at)
        return kind_states

    def _apply_history(
        self,
        *,
        tv_channel: TvChannel,
        tv_playout: TvPlayout,
        kind_states: dict[int, _KindState],
        start_at: datetime,
    ) -> None:
        container_states = {
            state.container.id: state
            for kind_state in kind_states.values()
            for state in kind_state.containers
        }

        lookback_start = start_at - timedelta(hours=self.LOOKBACK_HOURS)
        past_items = (
            ScheduleMediaItem.objects.filter(
                flexible_selection__tv_playout__tv_channel=tv_channel,
                starts_at__gte=lookback_start,
                starts_at__lt=start_at,
            )
            .select_related("item")
            .order_by("starts_at")
        )
        for scheduled in past_items:
            state = container_states.get(scheduled.item.container_id)
            if state is None:
                continue
            state.last_scheduled_at = scheduled.starts_at
            state.last_item_id = scheduled.item_id

        # Un run par selection: les compteurs de rotation par kind repartent
        # des selections deja posees sur ce playout (continuite en extend).
        run_counts = (
            FlexiblePlayoutSelection.objects
            .filter(tv_playout=tv_playout, segment__isnull=True)
            .values("media_container__media_collection__container_kind")
            .annotate(total=Count("id"))
        )
        for row in run_counts:
            kind_state = kind_states.get(row["media_container__media_collection__container_kind"])
            if kind_state is not None:
                kind_state.run_count = row["total"]

    @staticmethod
    def _pick_kind(kind_states: dict[int, _KindState]) -> _KindState | None:
        candidates = [state for state in kind_states.values() if state.eligible_containers()]
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda state: (state.run_count / state.quota, -state.quota, state.policy.container_kind),
        )

    def _resume_unfinished_run(
        self,
        *,
        tv_playout: TvPlayout,
        kind_states: dict[int, _KindState],
        cursor: datetime,
        end_at: datetime,
        warnings: list[str],
    ) -> tuple[int, datetime] | None:
        last_selection = (
            FlexiblePlayoutSelection.objects
            .filter(tv_playout=tv_playout, segment__isnull=True)
            .order_by("-order")
            .select_related("media_container", "last_scheduled_item")
            .first()
        )
        if last_selection is None:
            return None
        scheduled_count = ScheduleMediaItem.objects.filter(flexible_selection=last_selection).count()
        remaining = last_selection.planned_item_count - scheduled_count
        if remaining <= 0:
            return None

        container_state = None
        for kind_state in kind_states.values():
            for state in kind_state.containers:
                if state.container.id == last_selection.media_container_id:
                    container_state = state
                    break
        if container_state is None:
            warnings.append(
                f"Unfinished run {last_selection.id} cannot resume: container no longer matches the editorial line."
            )
            self._complete_selection(last_selection)
            return None

        container_state.last_item_id = last_selection.last_scheduled_item_id
        run_items = container_state.next_items(remaining)
        if not run_items:
            self._complete_selection(last_selection)
            return None
        return self._schedule_run(
            selection=last_selection,
            container_state=container_state,
            run_items=run_items,
            cursor=cursor,
            end_at=end_at,
        )

    def _create_selection(
        self,
        *,
        tv_playout: TvPlayout,
        media_container: MediaContainer,
        planned_item_count: int,
    ) -> FlexiblePlayoutSelection:
        max_order = (
            FlexiblePlayoutSelection.objects.filter(tv_playout=tv_playout).aggregate(value=Max("order"))["value"] or 0
        )
        return FlexiblePlayoutSelection.objects.create(
            tv_playout=tv_playout,
            segment=None,
            media_container=media_container,
            path_position=0,
            order=max_order + 1,
            planned_item_count=planned_item_count,
            status=ScheduledContainerStatus.PENDING,
        )

    def _schedule_run(
        self,
        *,
        selection: FlexiblePlayoutSelection,
        container_state: _ContainerState,
        run_items: list[MediaItem],
        cursor: datetime,
        end_at: datetime,
    ) -> tuple[int, datetime]:
        scheduled_count = 0
        for item in run_items:
            day_end_at = self._resolve_day_end_at(cursor)
            if cursor >= day_end_at:
                # La sequence est premiere, l'horloge est seconde: le run
                # entame reprend le lendemain matin au lieu d'etre tronque.
                cursor = self._next_day_start_at(cursor)
            item_end = cursor + timedelta(seconds=item.duration_seconds or 0)
            if cursor >= end_at or item_end > end_at:
                break

            post_roll_filler_ends_at = self._resolve_post_roll_filler_end_for_policy(
                policy=self.grid_layout.post_filler_policy if self.grid_layout.post_filler_policy_id else None,
                allow_filler=self.editorial_line.allow_filler,
                item_end=item_end,
                window_end=end_at,
            )
            scheduled = ScheduleMediaItem.objects.create(
                added_to_playout=False,
                starts_at=cursor,
                ends_at=item_end,
                post_roll_filler_ends_at=post_roll_filler_ends_at,
                item=item,
                flexible_selection=selection,
            )
            scheduled_count += 1
            cursor = scheduled.post_roll_filler_ends_at or scheduled.ends_at
            container_state.last_scheduled_at = scheduled.starts_at
            container_state.last_item_id = item.id
            selection.last_scheduled_item = item
            selection.save(update_fields=["last_scheduled_item"])

        total_scheduled = ScheduleMediaItem.objects.filter(flexible_selection=selection).count()
        if total_scheduled >= selection.planned_item_count:
            self._complete_selection(selection)
        return scheduled_count, cursor

    @staticmethod
    def _complete_selection(selection: FlexiblePlayoutSelection) -> None:
        if selection.status != ScheduledContainerStatus.COMPLETED:
            selection.status = ScheduledContainerStatus.COMPLETED
            selection.save(update_fields=["status"])

    def _rollback_selection_status(self, selection: FlexiblePlayoutSelection, last_scheduled) -> int:
        remaining = ScheduleMediaItem.objects.filter(flexible_selection=selection).count()
        if remaining >= selection.planned_item_count:
            return ScheduledContainerStatus.COMPLETED
        return ScheduledContainerStatus.PENDING
