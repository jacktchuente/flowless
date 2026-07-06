from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass, replace
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from editorial_flow import discover_channel_candidates, generate_segment_path, run_segmentation
from editorial_flow.configs import ChannelDiscoveryConfig, SegmentPathConfig, SegmentationConfig
from editorial_flow.inputs import MediaInput
from editorial_planning.models import (
    EditorialChannelCandidate,
    EditorialChannelCandidateStatus,
    EditorialChannelSegment,
    EditorialFlowRun,
    EditorialSegment,
    EditorialSegmentMembership,
    EditorialSegmentMembershipStatus,
    EditorialSegmentPath,
    EditorialSegmentPathElement,
)
from editorial_planning.services.media_input_builder import build_media_input
from media_source.models import MediaCollection, MediaContainer
from project_ops.constants import AnalyzeStatus
from tv_channel.models import Catalog


class EditorialPlanningGenerationService:
    def __init__(
        self,
        *,
        catalog: Catalog,
        media_collection_ids: Iterable[int],
        max_channel_candidates: int | None = None,
        target_channel_count: int | None = None,
        segmentation_config: SegmentationConfig | None = None,
        channel_discovery_config: ChannelDiscoveryConfig | None = None,
        segment_path_config: SegmentPathConfig | None = None,
        activate_run: bool = True,
    ):
        self.catalog = catalog
        self.media_collection_ids = self._unique_ids(media_collection_ids)
        self.max_channel_candidates = max_channel_candidates
        self.target_channel_count = target_channel_count
        self.segmentation_config = segmentation_config or SegmentationConfig()
        self.channel_discovery_config = channel_discovery_config or ChannelDiscoveryConfig()
        self.segment_path_config = segment_path_config or SegmentPathConfig()
        self.activate_run = activate_run

        # The requested channel count needs at least that many segments to
        # exist: force the explored k range to cover it.
        target = self._effective_target_channel_count()
        if (
            target
            and self.segmentation_config.min_segment_target is None
            and not self.segmentation_config.candidate_cluster_counts
        ):
            self.segmentation_config = replace(self.segmentation_config, min_segment_target=target + 1)

    def generate(self) -> EditorialFlowRun:
        started_at = timezone.now()
        run = EditorialFlowRun.objects.create(
            catalog=self.catalog,
            status=AnalyzeStatus.ANALYZING,
            is_active=False,
            started_at=started_at,
            config=self._config_payload(),
        )

        diagnostics: dict = {
            "media_collection_ids": self.media_collection_ids,
            "ignored_collections": [],
            "attempts": [],
        }

        try:
            collections = self._load_collections(diagnostics)
            containers = self._load_media_containers(collections)
            media_inputs = [self._to_media_input(container) for container in containers]

            segmentation = run_segmentation(media_inputs, self.segmentation_config)
            discovery, discovery_config = self._discover_channels(segmentation.segments, diagnostics)
            selected_candidates = self._select_channel_candidates(discovery.channel_candidates)
            paths = {
                candidate.channel_id: generate_segment_path(
                    candidate,
                    segmentation.segments,
                    self.segment_path_config,
                )
                for candidate in selected_candidates
            }

            diagnostics.update(
                {
                    "source_media_count": len(media_inputs),
                    "segment_count": len(segmentation.segments),
                    "membership_count": len(segmentation.memberships),
                    "channel_candidate_count": len(selected_candidates),
                    "outliers": segmentation.outliers,
                    "weak_clusters": segmentation.weak_clusters,
                    "segmentation": segmentation.diagnostics,
                    "channel_discovery": discovery.diagnostics,
                    "segment_links": discovery.segment_links,
                    "communities": discovery.communities,
                    "selected_channel_ids": [candidate.channel_id for candidate in selected_candidates],
                    "selected_channel_discovery_config": asdict(discovery_config),
                }
            )

            status = AnalyzeStatus.COMPLETE
            completed_at = timezone.now()

            with transaction.atomic():
                self._persist_results(
                    run=run,
                    containers=containers,
                    segmentation=segmentation,
                    channel_candidates=selected_candidates,
                    paths=paths,
                )
                if self.activate_run:
                    EditorialFlowRun.objects.filter(catalog=self.catalog, is_active=True).exclude(pk=run.pk).update(
                        is_active=False
                    )
                    run.is_active = True
                run.status = status
                run.completed_at = completed_at
                run.model_state = self._json_safe(asdict(segmentation.model_state))
                run.diagnostics = self._json_safe(diagnostics)
                run.source_media_count = len(media_inputs)
                run.segment_count = len(segmentation.segments)
                run.channel_candidate_count = len(selected_candidates)
                run.save(
                    update_fields=[
                        "status",
                        "is_active",
                        "completed_at",
                        "model_state",
                        "diagnostics",
                        "source_media_count",
                        "segment_count",
                        "channel_candidate_count",
                        "updated_at",
                    ]
                )
            return run
        except Exception as exc:
            run.status = AnalyzeStatus.COMPLETE_WITH_ERRORS
            run.completed_at = timezone.now()
            diagnostics["error"] = str(exc)
            run.diagnostics = self._json_safe(diagnostics)
            run.save(update_fields=["status", "completed_at", "diagnostics", "updated_at"])
            raise

    def _discover_channels(self, segments, diagnostics: dict):
        target = self._effective_target_channel_count()
        base_max = self.max_channel_candidates or self.channel_discovery_config.max_channel_candidates

        base_config = replace(
            self.channel_discovery_config,
            max_channel_candidates=base_max,
        )

        best_result = None
        best_config = None
        best_count = -1

        for attempt_index, config in enumerate(self._channel_discovery_attempts(base_config, target), start=1):
            result = discover_channel_candidates(segments, config)
            candidates = self._select_channel_candidates(result.channel_candidates)
            diagnostics["attempts"].append(
                {
                    "index": attempt_index,
                    "config": asdict(config),
                    "candidate_count": len(candidates),
                    "raw_candidate_count": len(result.channel_candidates),
                }
            )

            if len(candidates) > best_count:
                best_result = result
                best_config = config
                best_count = len(candidates)

            if target and len(candidates) >= target:
                return result, config

        return best_result, best_config

    def _channel_discovery_attempts(self, base_config: ChannelDiscoveryConfig, target: int):
        """Yields discovery configs until the channel target can be met.

        Without a target, the base config runs alone. With a target, the
        compatibility threshold sweeps upward so the segment graph splits
        into more communities; a second, relaxed sweep (single-segment
        channels allowed, lower score floor) runs if the first one was not
        enough. Communities are disjoint per attempt, so raising the
        threshold can only split channels, never duplicate them.
        """
        yield base_config
        if not target:
            return

        for relaxed in (False, True):
            threshold = base_config.compatibility_threshold
            while threshold < 0.95:
                threshold = round(min(0.95, threshold + 0.05), 3)
                overrides = {"compatibility_threshold": threshold}
                if relaxed:
                    overrides["min_segments_per_channel"] = 1
                    overrides["min_channel_score"] = max(0.3, base_config.min_channel_score - 0.2)
                yield replace(base_config, **overrides)

    def _select_channel_candidates(self, candidates):
        selected = sorted(candidates, key=lambda candidate: candidate.viability_score, reverse=True)
        limit = self.max_channel_candidates or self.target_channel_count
        if limit is not None:
            selected = selected[:limit]
        return selected

    def _load_collections(self, diagnostics: dict) -> list[MediaCollection]:
        collections = list(
            MediaCollection.objects.filter(id__in=self.media_collection_ids)
            .select_related("media_source")
            .order_by("id")
        )
        found_ids = {collection.id for collection in collections}
        for missing_id in [value for value in self.media_collection_ids if value not in found_ids]:
            diagnostics["ignored_collections"].append(
                {
                    "id": missing_id,
                    "reason": "not_found",
                }
            )

        usable_collections = []
        for collection in collections:
            if not collection.is_active:
                diagnostics["ignored_collections"].append(
                    {
                        "id": collection.id,
                        "name": collection.name,
                        "reason": "inactive",
                    }
                )
                continue
            usable_collections.append(collection)
        return usable_collections

    @staticmethod
    def _load_media_containers(collections: list[MediaCollection]) -> list[MediaContainer]:
        collection_ids = [collection.id for collection in collections]
        if not collection_ids:
            return []
        return list(
            MediaContainer.objects.filter(
                media_collection_id__in=collection_ids,
                media_collection__is_active=True,
                analyze_status=AnalyzeStatus.COMPLETE,
                is_missing=False,
            )
            .select_related("media_collection")
            .order_by("id")
        )

    @staticmethod
    def _to_media_input(container: MediaContainer) -> MediaInput:
        return build_media_input(container)

    def _persist_results(self, *, run, containers, segmentation, channel_candidates, paths) -> None:
        containers_by_key = {str(container.id): container for container in containers}
        segments_by_key = {}

        for segment in segmentation.segments:
            persisted_segment = EditorialSegment.objects.create(
                run=run,
                segment_key=segment.segment_id,
                name=segment.name[:120],
                description=segment.description or "",
                profile=self._json_safe(segment.profile),
                reference_vector=self._json_safe(segment.reference_vector),
                reference_profile=self._json_safe(segment.reference_profile),
                observed_profile=self._json_safe(segment.observed_profile),
                programmable_score=segment.programmable_score,
                cohesion_score=segment.cohesion_score,
                separation_score=segment.separation_score,
                format_consistency_score=segment.format_consistency_score,
                volume_score=segment.volume_score,
                labelability_score=segment.labelability_score,
                acceptance_threshold=segment.acceptance_threshold,
                media_count=len(segment.media_ids),
            )
            segments_by_key[segment.segment_id] = persisted_segment

        memberships = []
        membership_counts: dict[str, int] = {}
        for membership in segmentation.memberships:
            segment = segments_by_key.get(membership.segment_id)
            container = containers_by_key.get(membership.media_id)
            if segment is None or container is None:
                continue
            membership_counts[membership.segment_id] = membership_counts.get(membership.segment_id, 0) + 1
            memberships.append(
                EditorialSegmentMembership(
                    segment=segment,
                    media_container=container,
                    score=membership.score,
                    is_primary=membership.is_primary,
                    status=EditorialSegmentMembershipStatus.ACCEPTED,
                )
            )
        EditorialSegmentMembership.objects.bulk_create(memberships)

        # media_count reflects the full composition (primary + secondary members)
        for segment_key, persisted_segment in segments_by_key.items():
            count = membership_counts.get(segment_key, 0)
            if count != persisted_segment.media_count:
                persisted_segment.media_count = count
                persisted_segment.save(update_fields=["media_count"])

        for candidate in channel_candidates:
            persisted_candidate = EditorialChannelCandidate.objects.create(
                run=run,
                channel_key=candidate.channel_id,
                name=candidate.name[:120],
                description=candidate.description or "",
                viability_score=candidate.viability_score,
                status=self._channel_status(candidate.status),
                profile=self._json_safe(candidate.profile),
                diagnostics=self._json_safe(candidate.diagnostics),
            )
            for position, channel_segment in enumerate(candidate.segments, start=1):
                segment = segments_by_key.get(channel_segment.segment_id)
                if segment is None:
                    continue
                EditorialChannelSegment.objects.create(
                    channel_candidate=persisted_candidate,
                    segment=segment,
                    role=channel_segment.role,
                    weight=channel_segment.weight,
                    position=position,
                )

            path_result = paths.get(candidate.channel_id)
            if path_result is None:
                continue
            path = EditorialSegmentPath.objects.create(
                channel_candidate=persisted_candidate,
                is_loop=path_result.is_loop,
                global_score=path_result.global_score,
                transition_scores=self._json_safe(path_result.transition_scores),
                diagnostics=self._json_safe(path_result.diagnostics),
            )
            for element in path_result.main_path:
                segment = segments_by_key.get(element.segment_id)
                if segment is None:
                    continue
                EditorialSegmentPathElement.objects.create(
                    path=path,
                    segment=segment,
                    position=element.position,
                    role=element.role,
                    reason=element.reason,
                    transition_from_previous_score=element.transition_from_previous_score,
                )

    def _config_payload(self) -> dict:
        return self._json_safe(
            {
                "media_collection_ids": self.media_collection_ids,
                "max_channel_candidates": self.max_channel_candidates,
                "target_channel_count": self.target_channel_count,
                "effective_target_channel_count": self._effective_target_channel_count(),
                "segmentation": asdict(self.segmentation_config),
                "channel_discovery": asdict(self.channel_discovery_config),
                "segment_path": asdict(self.segment_path_config),
            }
        )

    def _effective_target_channel_count(self) -> int:
        target = self.target_channel_count or 0
        if self.max_channel_candidates is None:
            return target
        return min(target, self.max_channel_candidates)

    @staticmethod
    def _channel_status(status: str) -> str:
        valid_statuses = {value for value, _ in EditorialChannelCandidateStatus.choices}
        if status in valid_statuses:
            return status
        return EditorialChannelCandidateStatus.WEAK

    @staticmethod
    def _unique_ids(values: Iterable[int]) -> list[int]:
        unique_values = []
        seen = set()
        for value in values:
            value = int(value)
            if value in seen:
                continue
            unique_values.append(value)
            seen.add(value)
        return unique_values

    @classmethod
    def _json_safe(cls, value):
        if is_dataclass(value):
            value = asdict(value)
        return json.loads(json.dumps(value, default=str))
