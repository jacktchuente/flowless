from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from editorial_flow import match_media_to_segments
from editorial_flow.configs import MatchingConfig
from editorial_flow.outputs import ProgrammableSegment, SegmentationModelState
from editorial_planning.models import (
    EditorialFlowRun,
    EditorialSegment,
    EditorialSegmentMembership,
    EditorialSegmentMembershipStatus,
)
from editorial_planning.services.media_input_builder import build_media_input
from media_source.models import MediaContainer
from project_ops.constants import AnalyzeStatus


@dataclass
class MatchingRunResult:
    run: EditorialFlowRun
    evaluated_count: int
    accepted_count: int
    secondary_count: int
    ambiguous_count: int
    rejected_count: int
    created_membership_count: int


class EditorialPlanningMatchingService:
    """Matches media added after an editorial flow run to its persisted segments.

    This is the incremental counterpart of the full generation: instead of
    re-running the segmentation, new media containers are vectorised with the
    run's persisted model state and attached to existing segments, so that
    flexible channels built from the run pick up new content.
    """

    def __init__(
        self,
        *,
        run: EditorialFlowRun,
        matching_config: MatchingConfig | None = None,
    ):
        self.run = run
        self.matching_config = matching_config or MatchingConfig()

    def match_new_media(self) -> MatchingRunResult:
        model_state = self._load_model_state()
        segments_by_key = {segment.segment_key: segment for segment in self.run.segments.all()}
        if not segments_by_key:
            raise ValidationError("Editorial flow run has no persisted segment.")

        containers = self._load_new_containers()
        media_inputs = [build_media_input(container) for container in containers]
        containers_by_key = {str(container.id): container for container in containers}

        result = match_media_to_segments(
            media_inputs,
            self._to_programmable_segments(segments_by_key),
            model_state,
            self.matching_config,
        )

        created_memberships: list[EditorialSegmentMembership] = []
        accepted_segment_ids: list[int] = []
        counts = {
            EditorialSegmentMembershipStatus.ACCEPTED: 0,
            EditorialSegmentMembershipStatus.SECONDARY: 0,
            EditorialSegmentMembershipStatus.AMBIGUOUS: 0,
            EditorialSegmentMembershipStatus.REJECTED: 0,
        }

        for match in result.matches:
            status = self._membership_status(match.status)
            if status is None:
                continue
            counts[status] = counts.get(status, 0) + 1
            if status == EditorialSegmentMembershipStatus.REJECTED:
                continue

            container = containers_by_key.get(match.media_id)
            primary_segment = segments_by_key.get(match.primary_segment_id or "")
            if container is None or primary_segment is None:
                continue

            created_memberships.append(
                EditorialSegmentMembership(
                    segment=primary_segment,
                    media_container=container,
                    score=match.primary_score or 0.0,
                    is_primary=True,
                    status=status,
                    decision_reason=match.decision_reason,
                )
            )
            if status == EditorialSegmentMembershipStatus.ACCEPTED:
                accepted_segment_ids.append(primary_segment.id)

            for secondary_key, secondary_score in match.secondary_matches:
                secondary_segment = segments_by_key.get(secondary_key)
                if secondary_segment is None or secondary_segment.id == primary_segment.id:
                    continue
                created_memberships.append(
                    EditorialSegmentMembership(
                        segment=secondary_segment,
                        media_container=container,
                        score=secondary_score,
                        is_primary=False,
                        status=EditorialSegmentMembershipStatus.SECONDARY,
                        decision_reason="Secondary match against segment reference profile",
                    )
                )

        with transaction.atomic():
            EditorialSegmentMembership.objects.bulk_create(created_memberships)
            for segment_id in set(accepted_segment_ids):
                EditorialSegment.objects.filter(pk=segment_id).update(
                    media_count=F("media_count") + accepted_segment_ids.count(segment_id)
                )
            self._record_diagnostics(
                evaluated_count=len(media_inputs),
                counts=counts,
                created_membership_count=len(created_memberships),
            )

        return MatchingRunResult(
            run=self.run,
            evaluated_count=len(media_inputs),
            accepted_count=counts[EditorialSegmentMembershipStatus.ACCEPTED],
            secondary_count=counts[EditorialSegmentMembershipStatus.SECONDARY],
            ambiguous_count=counts[EditorialSegmentMembershipStatus.AMBIGUOUS],
            rejected_count=counts[EditorialSegmentMembershipStatus.REJECTED],
            created_membership_count=len(created_memberships),
        )

    def _load_model_state(self) -> SegmentationModelState:
        state = self.run.model_state or {}
        if not state.get("cluster_centroids"):
            raise ValidationError("Editorial flow run has no usable segmentation model state.")
        return SegmentationModelState(
            feature_state=state.get("feature_state") or {},
            cluster_centroids={
                key: [float(value) for value in vector]
                for key, vector in (state.get("cluster_centroids") or {}).items()
            },
            acceptance_thresholds={
                key: float(value) for key, value in (state.get("acceptance_thresholds") or {}).items()
            },
            algorithm=state.get("algorithm") or "",
            version=state.get("version") or "1.0",
        )

    def _load_new_containers(self) -> list[MediaContainer]:
        queryset = MediaContainer.objects.filter(
            media_collection__is_active=True,
            analyze_status=AnalyzeStatus.COMPLETE,
            is_missing=False,
        )
        collection_ids = (self.run.config or {}).get("media_collection_ids") or []
        if collection_ids:
            queryset = queryset.filter(media_collection_id__in=collection_ids)
        return list(
            queryset.exclude(
                editorial_segment_memberships__segment__run=self.run,
            )
            .select_related("media_collection")
            .order_by("id")
        )

    @staticmethod
    def _to_programmable_segments(segments_by_key: dict[str, EditorialSegment]) -> list[ProgrammableSegment]:
        return [
            ProgrammableSegment(
                segment_id=segment.segment_key,
                name=segment.name,
                description=segment.description,
                profile=segment.profile or {},
                reference_vector=[float(value) for value in (segment.reference_vector or [])],
                reference_profile=segment.reference_profile or {},
                observed_profile=segment.observed_profile or {},
                programmable_score=segment.programmable_score,
                cohesion_score=segment.cohesion_score,
                separation_score=segment.separation_score,
                format_consistency_score=segment.format_consistency_score,
                volume_score=segment.volume_score,
                labelability_score=segment.labelability_score,
                acceptance_threshold=segment.acceptance_threshold,
                media_ids=[],
            )
            for segment in segments_by_key.values()
        ]

    @staticmethod
    def _membership_status(status: str) -> str | None:
        valid_statuses = {value for value, _ in EditorialSegmentMembershipStatus.choices}
        if status in valid_statuses:
            return status
        return None

    def _record_diagnostics(self, *, evaluated_count: int, counts: dict, created_membership_count: int) -> None:
        diagnostics = dict(self.run.diagnostics or {})
        history = list(diagnostics.get("incremental_matching") or [])
        history.append(
            {
                "matched_at": timezone.now().isoformat(),
                "evaluated_count": evaluated_count,
                "accepted_count": counts[EditorialSegmentMembershipStatus.ACCEPTED],
                "secondary_count": counts[EditorialSegmentMembershipStatus.SECONDARY],
                "ambiguous_count": counts[EditorialSegmentMembershipStatus.AMBIGUOUS],
                "rejected_count": counts[EditorialSegmentMembershipStatus.REJECTED],
                "created_membership_count": created_membership_count,
                "config": {
                    "primary_acceptance_threshold": self.matching_config.primary_acceptance_threshold,
                    "secondary_acceptance_threshold": self.matching_config.secondary_acceptance_threshold,
                    "ambiguity_delta": self.matching_config.ambiguity_delta,
                    "allow_secondary_matches": self.matching_config.allow_secondary_matches,
                    "max_secondary_matches": self.matching_config.max_secondary_matches,
                },
            }
        )
        diagnostics["incremental_matching"] = history
        self.run.diagnostics = diagnostics
        self.run.save(update_fields=["diagnostics", "updated_at"])
