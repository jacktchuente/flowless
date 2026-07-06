from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from editorial_planning.models import (
    EditorialChannelCandidate,
    EditorialChannelCandidateStatus,
    EditorialPlannedGrid,
    EditorialSegmentMembership,
    EditorialSegmentMembershipStatus,
)
from tv_channel.models import GridLayoutMode, TvChannel

PLAYABLE_STATUSES = (
    EditorialSegmentMembershipStatus.ACCEPTED,
    EditorialSegmentMembershipStatus.MANUAL_OVERRIDE,
)


@dataclass
class ReconciliationProposal:
    tv_channel: TvChannel
    old_candidate: EditorialChannelCandidate
    proposed_candidate: EditorialChannelCandidate | None
    confidence: float


class EditorialRunReconciliationService:
    """Re-attaches promoted flexible channels to a newly generated run.

    Channels promoted from an older run of the same catalog keep playing
    that run's memberships forever. This service proposes, for each such
    channel, the equivalent candidate of the given run, using the Jaccard
    overlap of playable media containers - a signal independent of the
    feature space, so it works across model versions. Applying a mapping
    re-points the channel's planned grid to the new candidate.
    """

    def __init__(self, *, run):
        self.run = run

    def build_proposals(self) -> list[ReconciliationProposal]:
        old_candidates = list(
            EditorialChannelCandidate.objects.filter(
                run__catalog=self.run.catalog,
                tv_channel__isnull=False,
            )
            .exclude(run=self.run)
            .select_related("tv_channel", "run")
            .order_by("tv_channel_id", "-updated_at")
        )
        # One entry per channel: keep the most recent promoted candidate
        old_by_channel: dict[int, EditorialChannelCandidate] = {}
        for candidate in old_candidates:
            old_by_channel.setdefault(candidate.tv_channel_id, candidate)

        new_candidates = [
            candidate
            for candidate in self.run.channel_candidates.all()
            if candidate.tv_channel_id is None
        ]
        new_container_sets = {
            candidate.id: self._playable_container_ids(candidate)
            for candidate in new_candidates
        }

        # Score every (channel, new candidate) pair, then assign greedily
        # by confidence so a new candidate hosts at most one channel.
        pairs: list[tuple[float, int, int]] = []
        old_container_sets: dict[int, set[int]] = {}
        for channel_id, old_candidate in old_by_channel.items():
            old_set = self._playable_container_ids(old_candidate)
            old_container_sets[channel_id] = old_set
            for candidate in new_candidates:
                confidence = self._jaccard(old_set, new_container_sets[candidate.id])
                pairs.append((confidence, channel_id, candidate.id))
        pairs.sort(key=lambda entry: entry[0], reverse=True)

        assigned_channels: set[int] = set()
        assigned_candidates: set[int] = set()
        best_by_channel: dict[int, tuple[int, float]] = {}
        for confidence, channel_id, candidate_id in pairs:
            if confidence <= 0 or channel_id in assigned_channels or candidate_id in assigned_candidates:
                continue
            assigned_channels.add(channel_id)
            assigned_candidates.add(candidate_id)
            best_by_channel[channel_id] = (candidate_id, confidence)

        candidates_by_id = {candidate.id: candidate for candidate in new_candidates}
        proposals = []
        for channel_id, old_candidate in old_by_channel.items():
            candidate_id, confidence = best_by_channel.get(channel_id, (None, 0.0))
            proposals.append(
                ReconciliationProposal(
                    tv_channel=old_candidate.tv_channel,
                    old_candidate=old_candidate,
                    proposed_candidate=candidates_by_id.get(candidate_id),
                    confidence=confidence,
                )
            )
        proposals.sort(key=lambda proposal: proposal.confidence, reverse=True)
        return proposals

    def apply(self, mappings: list[dict]) -> list[dict]:
        """Applies channel → candidate mappings. Returns a report per mapping."""
        report = []
        for mapping in mappings:
            channel = TvChannel.objects.get(pk=mapping["tv_channel"])
            new_candidate = self.run.channel_candidates.get(pk=mapping["candidate"])
            if new_candidate.tv_channel_id is not None and new_candidate.tv_channel_id != channel.id:
                raise ValidationError(
                    f"Candidate {new_candidate.id} is already attached to another channel."
                )
            if EditorialPlannedGrid.objects.filter(channel_candidate=new_candidate).exists():
                raise ValidationError(
                    f"Candidate {new_candidate.id} already drives a planned grid."
                )

            with transaction.atomic():
                planned_grid = (
                    EditorialPlannedGrid.objects.filter(
                        grid_layout__tv_channel=channel,
                        grid_layout__is_active=True,
                        grid_layout__mode=GridLayoutMode.FLEXIBLE,
                    )
                    .select_related("channel_candidate")
                    .first()
                )
                if planned_grid is None:
                    raise ValidationError(
                        f"Channel {channel.name} has no active flexible planned grid."
                    )

                old_candidate = planned_grid.channel_candidate
                planned_grid.channel_candidate = new_candidate
                planned_grid.save(update_fields=["channel_candidate", "updated_at"])

                new_candidate.tv_channel = channel
                new_candidate.status = EditorialChannelCandidateStatus.SELECTED
                new_candidate.save(update_fields=["tv_channel", "status", "updated_at"])

                EditorialChannelCandidate.objects.filter(
                    tv_channel=channel,
                ).exclude(pk=new_candidate.pk).update(
                    tv_channel=None,
                    status=EditorialChannelCandidateStatus.VIABLE,
                )

            report.append(
                {
                    "tv_channel": channel.id,
                    "candidate": new_candidate.id,
                    "previous_candidate": old_candidate.id if old_candidate else None,
                }
            )
        return report

    @staticmethod
    def _playable_container_ids(candidate: EditorialChannelCandidate) -> set[int]:
        return set(
            EditorialSegmentMembership.objects.filter(
                segment__channel_segments__channel_candidate=candidate,
                status__in=PLAYABLE_STATUSES,
            ).values_list("media_container_id", flat=True)
        )

    @staticmethod
    def _jaccard(a: set[int], b: set[int]) -> float:
        if not a and not b:
            return 0.0
        union = len(a | b)
        if union == 0:
            return 0.0
        return len(a & b) / union
