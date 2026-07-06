"""
Implementation of the segment path generation process for TV programming.

``generate_segment_path`` takes a channel candidate and its associated
segments and produces an ordering (or loop) of segments that respects
transition quality, editorial variety and anchor return patterns. The
function does not schedule specific media or time slots; it operates
solely at the level of segments.
"""

from __future__ import annotations

import math
from typing import List, Dict, Optional, Any, Tuple

from .outputs import (
    ProgrammableSegment,
    ChannelCandidate,
    SegmentPathElement,
    SegmentPathResult,
)
from .configs import SegmentPathConfig
from .scoring import similarity


def generate_segment_path(
    channel: ChannelCandidate,
    segments: List[ProgrammableSegment],
    config: Optional[SegmentPathConfig] = None,
) -> SegmentPathResult:
    """Generates an editorial ordering of segments for a channel.

    The algorithm constructs a greedy path starting from the highest
    weighted anchor segment and repeatedly selecting the next segment
    with the highest transition score. It avoids immediate repetition
    of the same segment beyond ``max_immediate_repetition``. If
    ``generate_loop`` is True, the path is considered circular. Only
    one main path is produced; alternative paths are not generated.
    """
    if config is None:
        config = SegmentPathConfig()
    # Map segment ID to ProgrammableSegment
    seg_by_id: Dict[str, ProgrammableSegment] = {s.segment_id: s for s in segments}
    # Filter segments that appear in channel
    chan_seg_ids = [s.segment_id for s in channel.segments]
    chan_segments = [seg_by_id[sid] for sid in chan_seg_ids if sid in seg_by_id]
    # If no segments, return empty path
    if not chan_segments:
        return SegmentPathResult(
            channel_id=channel.channel_id,
            main_path=[],
            is_loop=False,
            global_score=0.0,
            alternative_paths=[],
            transition_scores={},
            diagnostics={"message": "No segments in channel"},
        )
    # Determine path length
    path_length = config.path_length or len(chan_segments)
    path_length = min(path_length, len(chan_segments))
    # Build transition score matrix
    transition_scores: Dict[str, Dict[str, float]] = {}
    for s1 in chan_segments:
        transition_scores[s1.segment_id] = {}
        for s2 in chan_segments:
            if s1.segment_id == s2.segment_id:
                transition_scores[s1.segment_id][s2.segment_id] = 0.0
            else:
                transition_scores[s1.segment_id][s2.segment_id] = similarity(s1.reference_vector, s2.reference_vector)
    # Determine initial segment: anchor with highest weight
    anchor_segments = [s for s in channel.segments if s.role == "anchor"]
    if anchor_segments:
        initial = max(anchor_segments, key=lambda x: x.weight).segment_id
    else:
        # Fallback: pick segment with highest weight
        initial = max(channel.segments, key=lambda x: x.weight).segment_id
    # Build path
    visited: Dict[str, int] = {sid: 0 for sid in chan_seg_ids}
    sequence: List[str] = []
    current = initial
    for pos in range(path_length):
        sequence.append(current)
        visited[current] += 1
        # Determine next segment
        candidates = [sid for sid in chan_seg_ids if visited[sid] < config.max_immediate_repetition and sid not in sequence]
        # If no unvisited candidates remain, break
        if not candidates:
            break
        # Choose candidate with highest transition score from current
        scores_candidates: List[Tuple[str, float]] = []
        for c in candidates:
            score = transition_scores[current][c]
            scores_candidates.append((c, score))
        # Filter by minimum transition score
        scores_candidates = [(c, s) for c, s in scores_candidates if s >= config.min_transition_score]
        if not scores_candidates:
            # Fallback: pick the candidate with highest channel weight
            next_seg = max(candidates, key=lambda sid: next((x.weight for x in channel.segments if x.segment_id == sid), 0.0))
        else:
            next_seg, _ = max(scores_candidates, key=lambda x: x[1])
        current = next_seg
    # Compute path elements and global score
    path_elements: List[SegmentPathElement] = []
    total_transition = 0.0
    for i, sid in enumerate(sequence):
        seg = seg_by_id[sid]
        role = next((cs.role for cs in channel.segments if cs.segment_id == sid), "secondary")
        if i == 0:
            reason = "start anchor"
            trans_score = 0.0
        else:
            prev_sid = sequence[i - 1]
            trans_score = transition_scores[prev_sid][sid]
            reason = "best transition from previous"
            total_transition += trans_score
        path_elements.append(
            SegmentPathElement(
                position=i + 1,
                segment_id=sid,
                segment_name=seg.name,
                role=role,
                reason=reason,
                transition_from_previous_score=trans_score,
            )
        )
    global_score = total_transition / max(1, len(path_elements) - 1)
    return SegmentPathResult(
        channel_id=channel.channel_id,
        main_path=path_elements,
        is_loop=config.generate_loop,
        global_score=global_score,
        alternative_paths=[],
        transition_scores=transition_scores,
        diagnostics={
            "path_length": len(path_elements),
            "total_transition": total_transition,
        },
    )
