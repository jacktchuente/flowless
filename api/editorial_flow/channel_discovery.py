"""
Implementation of the channel discovery process for TV programming.

``discover_channel_candidates`` groups programmable segments into
communities based on their compatibility, scores each community as a
potential channel, assigns roles to segments within each channel, and
returns a list of channel candidates. The process relies on simple
graph clustering and heuristic scoring; it does not perform any
optimisation over schedules or individual media items.
"""

from __future__ import annotations

import uuid
from typing import List, Dict, Optional, Tuple, Any

import numpy as np

from .outputs import (
    ProgrammableSegment,
    SegmentInChannel,
    ChannelCandidate,
    ChannelDiscoveryResult,
)
from .configs import ChannelDiscoveryConfig
from .scoring import similarity, diversity_score, distinctiveness_score

import math


def discover_channel_candidates(
    segments: List[ProgrammableSegment],
    config: Optional[ChannelDiscoveryConfig] = None,
) -> ChannelDiscoveryResult:
    """Group segments into channel candidates based on compatibility.

    Each segment is treated as a node in a graph where edge weights
    correspond to the cosine similarity between segment reference
    vectors. Edges below the compatibility threshold are discarded. The
    resulting graph is decomposed into connected components which
    represent candidate channels. Each community is scored for
    viability; only those meeting minimum criteria are returned as
    channel candidates. Roles within channels are assigned based on
    relative weights derived from the segments' programmability and
    volume scores.
    """
    if config is None:
        config = ChannelDiscoveryConfig()
    n = len(segments)
    # Return early if there are no segments
    if n == 0:
        return ChannelDiscoveryResult(
            channel_candidates=[],
            communities=[],
            segment_links=[],
            diagnostics={"message": "No segments provided"},
        )
    # Compute pairwise similarity matrix and build edges
    segment_ids = [s.segment_id for s in segments]
    vectors = [np.array(s.reference_vector, dtype=float) for s in segments]
    segment_links: List[Tuple[str, str, float]] = []
    adjacency: Dict[int, List[int]] = {i: [] for i in range(n)}
    for i in range(n):
        for j in range(i + 1, n):
            sim = similarity(vectors[i], vectors[j])
            if sim >= config.compatibility_threshold:
                # Record undirected edge
                adjacency[i].append(j)
                adjacency[j].append(i)
                segment_links.append((segment_ids[i], segment_ids[j], sim))
    if config.allow_segment_sharing:
        # One community per anchor segment: the anchor plus its direct
        # compatible neighbours. Communities may overlap, which allows up
        # to one channel per segment; identical neighbourhoods collapse.
        communities_indices = []
        seen_components: set[frozenset[int]] = set()
        for i in range(n):
            component = sorted({i, *adjacency[i]})
            key = frozenset(component)
            if key in seen_components:
                continue
            seen_components.add(key)
            communities_indices.append(component)
    else:
        # Compute communities as connected components
        visited = [False] * n
        communities_indices = []
        for i in range(n):
            if not visited[i]:
                # BFS/DFS
                stack = [i]
                component = []
                visited[i] = True
                while stack:
                    v = stack.pop()
                    component.append(v)
                    for nb in adjacency[v]:
                        if not visited[nb]:
                            visited[nb] = True
                            stack.append(nb)
                communities_indices.append(component)
    # Build community lists of segment IDs
    communities: List[List[str]] = [[segment_ids[idx] for idx in comp] for comp in communities_indices]
    scored_candidates: List[Tuple[ChannelCandidate, np.ndarray]] = []
    # Compute centroids for distinctiveness
    community_centroids: List[np.ndarray] = []
    for comp in communities_indices:
        comp_vecs = [vectors[idx] for idx in comp]
        centroid = np.mean(comp_vecs, axis=0) if comp_vecs else np.zeros_like(vectors[0])
        community_centroids.append(centroid)
    # Evaluate each community
    diagnostics: Dict[str, Any] = {
        "num_communities": len(communities_indices),
    }
    for idx, comp in enumerate(communities_indices):
        # Extract segments
        segs = [segments[i] for i in comp]
        # Skip communities smaller than minimum segments
        if len(segs) < config.min_segments_per_channel:
            continue
        # Internal coherence: average pairwise similarity within community.
        # A single-segment community has no pairs: fall back to the
        # segment's own cohesion instead of punishing it with 0.
        internal_scores = []
        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                sim = similarity(segs[i].reference_vector, segs[j].reference_vector)
                internal_scores.append(sim)
        if internal_scores:
            internal_coherence = float(np.mean(internal_scores))
        else:
            internal_coherence = float(np.mean([s.cohesion_score for s in segs])) if segs else 0.0
        # Volume: average of segment volume scores
        avg_volume = float(np.mean([s.volume_score for s in segs])) if segs else 0.0
        # Diversity: categories across segments
        cat_sets = [s.profile.get("dominant_categories", []) for s in segs]
        diversity = diversity_score(cat_sets)
        # Transition density: same as internal coherence
        transition_density = internal_coherence
        # Labelability: average labelability scores
        avg_labelability = float(np.mean([s.labelability_score for s in segs])) if segs else 0.0
        # Distinctiveness compared to other communities
        other_centroids = [community_centroids[j] for j in range(len(community_centroids)) if j != idx]
        distinctiveness = distinctiveness_score(community_centroids[idx], other_centroids)
        # Viability score: weighted combination
        viability = (
            0.25 * internal_coherence
            + 0.2 * avg_volume
            + 0.15 * diversity
            + 0.15 * transition_density
            + 0.1 * avg_labelability
            + 0.15 * distinctiveness
        )
        # Determine status
        if viability >= config.min_channel_score:
            status = "viable"
        elif viability >= 0.4:
            status = "weak"
        else:
            status = "rejected"
        # Only include channels that meet minimum total duration if specified
        total_duration = sum(s.profile.get("avg_duration_seconds", 0.0) or 0.0 for s in segs)
        if config.min_total_duration_seconds and total_duration < config.min_total_duration_seconds:
            status = "rejected"
        # Build channel candidate if not rejected
        if status != "rejected":
            channel_id = str(uuid.uuid4())
            # Determine name: combine dominant nature and top categories across segments
            natures = [s.profile.get("dominant_nature") for s in segs if s.profile.get("dominant_nature")]
            cat_counts: Dict[str, int] = {}
            for s in segs:
                for c in s.profile.get("dominant_categories", []):
                    cat_counts[c] = cat_counts.get(c, 0) + 1
            top_cats = sorted(cat_counts, key=cat_counts.get, reverse=True)[:2]
            dominant_nature = None
            if natures:
                counts = {}
                for n_val in natures:
                    counts[n_val] = counts.get(n_val, 0) + 1
                dominant_nature = max(counts, key=counts.get)
            # Build name string; a single-segment channel reuses the segment
            # name, which already carries the format and stays unique.
            if len(segs) == 1:
                channel_name = segs[0].name
            else:
                name_parts = []
                if dominant_nature:
                    name_parts.append(dominant_nature.capitalize())
                if top_cats:
                    name_parts.append(" / ".join([c.capitalize() for c in top_cats]))
                channel_name = " / ".join(name_parts) if name_parts else f"Chaîne {channel_id[:8]}"
            description = f"Chaîne éditoriale composée de {len(segs)} segments."
            # Assign roles and weights
            # Weight per segment: use programmable_score * volume_score
            raw_weights = [s.programmable_score * s.volume_score for s in segs]
            total_weight = sum(raw_weights) if raw_weights else 1.0
            norm_weights = [w / total_weight for w in raw_weights]
            # Determine roles: top 20% anchors, next 30% support, rest secondary
            sorted_indices = sorted(range(len(segs)), key=lambda i: norm_weights[i], reverse=True)
            roles = ["secondary"] * len(segs)
            if len(segs) >= 1:
                anchor_count = max(1, int(math.ceil(len(segs) * 0.2)))
                support_count = max(0, int(math.ceil(len(segs) * 0.3)))
                for i in sorted_indices[:anchor_count]:
                    roles[i] = "anchor"
                for i in sorted_indices[anchor_count : anchor_count + support_count]:
                    roles[i] = "support"
            segment_in_channel_list: List[SegmentInChannel] = []
            for i, seg in enumerate(segs):
                segment_in_channel_list.append(
                    SegmentInChannel(
                        segment_id=seg.segment_id,
                        role=roles[i],
                        weight=norm_weights[i],
                    )
                )
            profile = {
                "num_segments": len(segs),
                "dominant_categories": top_cats,
                "dominant_nature": dominant_nature,
                "avg_viability": viability,
            }
            scored_candidates.append(
                (
                    ChannelCandidate(
                        channel_id=channel_id,
                        name=channel_name,
                        description=description,
                        segments=segment_in_channel_list,
                        viability_score=viability,
                        status=status,
                        profile=profile,
                        diagnostics={
                            "internal_coherence": internal_coherence,
                            "avg_volume": avg_volume,
                            "diversity": diversity,
                            "transition_density": transition_density,
                            "avg_labelability": avg_labelability,
                            "distinctiveness": distinctiveness,
                            "total_duration": total_duration,
                        },
                    ),
                    community_centroids[idx],
                )
            )

    # Keep the most viable candidates, dropping any whose centroid is
    # quasi identical to an already accepted one (overlapping communities
    # must never degenerate into duplicate channels).
    scored_candidates.sort(key=lambda entry: entry[0].viability_score, reverse=True)
    channel_candidates: List[ChannelCandidate] = []
    accepted_centroids: List[np.ndarray] = []
    duplicates_dropped = 0
    for candidate, centroid in scored_candidates:
        if len(channel_candidates) >= config.max_channel_candidates:
            break
        if any(
            similarity(centroid, accepted) >= config.duplicate_similarity_threshold
            for accepted in accepted_centroids
        ):
            duplicates_dropped += 1
            continue
        channel_candidates.append(candidate)
        accepted_centroids.append(centroid)
    diagnostics["duplicates_dropped"] = duplicates_dropped

    return ChannelDiscoveryResult(
        channel_candidates=channel_candidates,
        communities=communities,
        segment_links=segment_links,
        diagnostics=diagnostics,
    )
