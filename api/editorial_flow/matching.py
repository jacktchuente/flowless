"""
Implementation of the media-to-segment matching process for TV programming.

``match_media_to_segments`` takes new media items and assigns them to
existing segments based on the model state produced by the segmentation
process. It computes similarity and distance between the media and
segment centroids, applies acceptance thresholds and configurable
criteria, and outputs a match result per media item. Segments are not
modified by this process.
"""

from __future__ import annotations

from typing import List, Dict, Optional, Any, Tuple

import numpy as np

from .inputs import MediaInput
from .outputs import (
    ProgrammableSegment,
    SegmentationModelState,
    MediaMatch,
    MediaSegmentMatchingResult,
)
from .configs import MatchingConfig
from .features import FEATURE_STATE_VERSION, FeatureExtractor
from .scoring import cosine_similarity, similarity


def match_media_to_segments(
    media: List[MediaInput],
    segments: List[ProgrammableSegment],
    model_state: SegmentationModelState,
    config: Optional[MatchingConfig] = None,
) -> MediaSegmentMatchingResult:
    """Evaluates new media against existing segments.

    Uses the feature extractor stored in ``model_state`` to vectorise the
    media exactly as during segmentation. Each media item is compared
    against all segments using both cosine similarity and Euclidean
    distance. A media is accepted into a segment if its distance to the
    segment's reference vector does not exceed the acceptance threshold
    and its similarity exceeds the configured primary or secondary
    thresholds. Ambiguity is detected when multiple segments achieve
    similar similarity scores within ``ambiguity_delta``.
    """
    if config is None:
        config = MatchingConfig()
    # Reconstruct feature extractor
    fe = FeatureExtractor.from_state(model_state.feature_state)
    # The similarity scale must match the one used when the model state
    # was persisted: raw cosine for v2 states, mapped cosine for legacy.
    if (model_state.feature_state or {}).get("version") == FEATURE_STATE_VERSION:
        similarity_fn = cosine_similarity
    else:
        similarity_fn = similarity
    # Build lookup maps for segment centroids and thresholds
    centroids = model_state.cluster_centroids
    thresholds = model_state.acceptance_thresholds
    seg_dict: Dict[str, ProgrammableSegment] = {s.segment_id: s for s in segments}
    matches: List[MediaMatch] = []
    unmatched: List[str] = []
    ambiguous: List[str] = []
    # Precompute centroid arrays
    centroid_arrays: Dict[str, np.ndarray] = {sid: np.array(vec, dtype=float) for sid, vec in centroids.items()}
    for m in media:
        # Vectorise media
        m_vec = np.array(fe.transform(m), dtype=float)
        scores: List[Tuple[str, float, float]] = []  # (segment_id, similarity_score, distance)
        for sid, centroid_vec in centroid_arrays.items():
            # Euclidean distance for acceptance threshold
            dist = float(np.linalg.norm(m_vec - centroid_vec))
            sim = similarity_fn(m_vec, centroid_vec)
            scores.append((sid, sim, dist))
        # Sort by similarity descending
        scores.sort(key=lambda x: x[1], reverse=True)
        if not scores:
            unmatched.append(m.id)
            continue
        # Identify candidates within thresholds
        primary_candidate: Optional[Tuple[str, float, float]] = None
        secondary_candidates: List[Tuple[str, float]] = []
        for sid, sim, dist in scores:
            threshold = thresholds.get(sid, float('inf'))
            if dist <= threshold and sim >= config.primary_acceptance_threshold:
                primary_candidate = (sid, sim, dist)
                break
        # If no primary candidate with strict threshold, allow those above secondary threshold
        if primary_candidate is None:
            for sid, sim, dist in scores:
                threshold = thresholds.get(sid, float('inf'))
                if dist <= threshold and sim >= config.secondary_acceptance_threshold:
                    primary_candidate = (sid, sim, dist)
                    break
        # Determine status
        if primary_candidate is None:
            # No segment passed the distance/score thresholds
            unmatched.append(m.id)
            matches.append(
                MediaMatch(
                    media_id=m.id,
                    status="rejected",
                    primary_segment_id=None,
                    primary_score=None,
                    secondary_matches=[],
                    decision_reason="No segment meets acceptance thresholds",
                )
            )
            continue
        # Extract primary info
        primary_sid, primary_sim, primary_dist = primary_candidate
        # Find secondary matches if allowed
        for sid, sim, dist in scores:
            if sid == primary_sid:
                continue
            threshold = thresholds.get(sid, float('inf'))
            if config.allow_secondary_matches and dist <= threshold and sim >= config.secondary_acceptance_threshold:
                secondary_candidates.append((sid, sim))
                if len(secondary_candidates) >= config.max_secondary_matches:
                    break
        # Check ambiguity: if there is another candidate with similarity within ambiguity_delta of the primary
        ambiguous_flag = False
        for sid, sim, dist in scores:
            if sid != primary_sid and abs(sim - primary_sim) <= config.ambiguity_delta:
                ambiguous_flag = True
                break
        if ambiguous_flag:
            ambiguous.append(m.id)
            status = "ambiguous"
        elif primary_sim >= config.primary_acceptance_threshold:
            status = "accepted"
        elif primary_sim >= config.secondary_acceptance_threshold:
            status = "secondary"
        else:
            status = "rejected"
        decision_reason = ""
        if status == "accepted":
            decision_reason = "Primary segment meets acceptance threshold"
        elif status == "secondary":
            decision_reason = "Primary segment meets secondary threshold"
        elif status == "ambiguous":
            decision_reason = "Multiple segments have similar match scores"
        else:
            decision_reason = "No segment meets acceptance thresholds"
        matches.append(
            MediaMatch(
                media_id=m.id,
                status=status,
                primary_segment_id=primary_sid,
                primary_score=primary_sim,
                secondary_matches=secondary_candidates if config.allow_secondary_matches else [],
                decision_reason=decision_reason,
            )
        )
    return MediaSegmentMatchingResult(
        matches=matches,
        unmatched=unmatched,
        ambiguous=ambiguous,
        diagnostics={},
    )
