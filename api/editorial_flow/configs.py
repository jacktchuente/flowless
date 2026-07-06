"""
Configuration dataclasses for the TV programming algorithm.

These dataclasses encapsulate tunable parameters for each process. Each
function in the API accepts an optional config object; when no config
is provided sensible defaults are used. Callers may adjust these
parameters to tailor the behaviour of the algorithm to their catalogue
size, editorial preferences or platform constraints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SegmentationConfig:
    """Configuration for the segmentation process.

    ``min_cluster_size`` controls the minimum number of media items
    required to consider a cluster as a potential segment. ``min_total
    _duration_seconds`` and ``min_items_per_segment`` enforce minimum
    content volume. ``min_programmable_score`` is the lower bound for
    programmable segments; clusters scoring below this threshold are
    considered weak. ``candidate_cluster_counts`` allows callers to
    explicitly provide a list of k values to test when using k-means; if
    ``None`` the algorithm will infer a reasonable range. ``max_features``
    limits the number of distinct categories, languages and countries
    tracked during feature extraction. ``allow_outliers`` permits media
    items to remain unclustered.

    ``min_df_count`` / ``max_df_ratio`` drive the generic noise filter of
    the feature extractor: vocabulary values carried by fewer than
    ``min_df_count`` media or by more than ``max_df_ratio`` of the corpus
    have no discriminative power and are dropped. ``block_weights``
    overrides the default relative weight of each feature block.

    ``allow_multi_segment`` lets a media belong to several segments: on
    top of its primary cluster, it joins any other segment whose
    acceptance threshold it satisfies, or that sits at most
    ``multi_segment_distance_ratio`` times farther than its own segment
    (scale-free criterion, so it generalises across libraries). When
    disabled the segmentation is a strict partition.

    ``max_cluster_ratio`` / ``cluster_imbalance_penalty`` penalise k
    choices where the biggest cluster exceeds a share of the corpus, to
    avoid trivial binary splits.
    """

    min_cluster_size: int = 2
    min_total_duration_seconds: int = 0
    min_items_per_segment: int = 1
    min_programmable_score: float = 0.4
    allow_outliers: bool = True
    max_features: int = 1000
    candidate_cluster_counts: Optional[List[int]] = None
    algorithm: str = "kmeans"
    random_state: Optional[int] = 42
    min_df_count: int = 2
    max_df_ratio: float = 0.9
    block_weights: Optional[Dict[str, float]] = None
    allow_multi_segment: bool = True
    multi_segment_distance_ratio: float = 1.5
    max_cluster_ratio: float = 0.6
    cluster_imbalance_penalty: float = 1.0


@dataclass
class ChannelDiscoveryConfig:
    """Configuration for the channel discovery process."""

    min_channel_score: float = 0.5
    min_segments_per_channel: int = 2
    min_total_duration_seconds: int = 0
    compatibility_threshold: float = 0.3
    allow_segment_sharing: bool = False
    max_channel_candidates: int = 10


@dataclass
class SegmentPathConfig:
    """Configuration for the segment path generation process."""

    path_length: Optional[int] = None  # if None, use all segments in the channel
    generate_loop: bool = True
    number_of_variants: int = 1
    min_transition_score: float = 0.0
    max_immediate_repetition: int = 1
    anchor_return_strength: float = 0.5
    diversity_strength: float = 0.5
    transition_strength: float = 0.5


@dataclass
class MatchingConfig:
    """Configuration for the matching process."""

    primary_acceptance_threshold: float = 0.6
    secondary_acceptance_threshold: float = 0.4
    ambiguity_delta: float = 0.05
    allow_secondary_matches: bool = True
    max_secondary_matches: int = 2
