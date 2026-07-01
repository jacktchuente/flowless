"""
Definitions of output dataclasses produced by the TV programming algorithm.

All result types returned by the public functions live in this module. The
dataclasses are designed to be easily serialisable (e.g. via
``dataclasses.asdict``) so that callers can persist the algorithm's state
or forward results to other services. None of these classes depend on
Django or any database abstraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any


@dataclass
class ProgrammableSegment:
    """Represents a stable editorial block derived from clustering media.

    A programmable segment is more than a raw cluster: it encapsulates
    editorial identity (name, description, profile), scores describing
    its quality and cohesion, and the list of media items that belong to
    it. The reference vector and acceptance threshold are used by the
    matching process to evaluate new media against this segment.
    """

    segment_id: str
    name: str
    description: str
    profile: Dict[str, Any]
    reference_vector: List[float]
    reference_profile: Dict[str, Any]
    observed_profile: Dict[str, Any]
    programmable_score: float
    cohesion_score: float
    separation_score: float
    format_consistency_score: float
    volume_score: float
    labelability_score: float
    acceptance_threshold: float
    media_ids: List[str]


@dataclass
class SegmentMembership:
    """Associates a media item with a segment produced by segmentation.

    Each membership records the media and segment IDs together with a
    membership score. The score expresses how well the media fits the
    segment's reference profile (1.0 is a perfect fit). The ``is_primary``
    flag indicates whether this media is considered a primary member of
    the segment or a secondary/auxiliary member.
    """

    media_id: str
    segment_id: str
    score: float
    is_primary: bool = True


@dataclass
class SegmentationModelState:
    """Stores the state required to vectorise new media and evaluate segments.

    The model state is produced by ``run_segmentation`` and must be
    persisted by the caller. It contains everything needed to vectorise
    future media items consistently (feature configuration, encoders,
    scalers) as well as the reference vectors and acceptance thresholds
    for existing segments.
    """

    feature_state: Dict[str, Any]
    cluster_centroids: Dict[str, List[float]]
    acceptance_thresholds: Dict[str, float]
    algorithm: str
    version: str = "1.0"


@dataclass
class SegmentationResult:
    """Result returned by the segmentation process.

    It contains all the segments discovered, the membership assignments
    between media items and segments, lists of media considered outliers
    or belonging to weak clusters, the persistable model state, and any
    diagnostics information useful for debugging or analysis.
    """

    segments: List[ProgrammableSegment]
    memberships: List[SegmentMembership]
    outliers: List[str]
    weak_clusters: List[str]
    model_state: SegmentationModelState
    diagnostics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SegmentInChannel:
    """Represents the participation of a segment in a channel candidate.

    ``role`` can be ``anchor``, ``support`` or ``secondary`` and denotes
    the editorial weight of the segment inside the channel. The ``weight``
    field is a normalised numeric value summing up to 1 within a channel.
    """

    segment_id: str
    role: str
    weight: float


@dataclass
class ChannelCandidate:
    """Represents a candidate TV channel composed of multiple segments.

    A channel candidate aggregates compatible segments together and
    contains high level metadata such as a human friendly name,
    description, viability score and status. The ``profile`` field
    provides aggregated editorial characteristics of the channel.
    """

    channel_id: str
    name: str
    description: str
    segments: List[SegmentInChannel]
    viability_score: float
    status: str
    profile: Dict[str, Any]
    diagnostics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChannelDiscoveryResult:
    """Result produced by the channel discovery process.

    It bundles together all channel candidates, the intermediate
    communities discovered among segments, a list of segment links used to
    compute communities, and any diagnostic information. Each entry in
    ``segment_links`` is a tuple ``(segment_id_a, segment_id_b, score)``
    representing the compatibility score between two segments.
    """

    channel_candidates: List[ChannelCandidate]
    communities: List[List[str]]
    segment_links: List[Tuple[str, str, float]]
    diagnostics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SegmentPathElement:
    """Single element in a generated segment path.

    ``reason`` records the rationale for placing this segment at this
    position (e.g. "anchor start", "best transition from previous").
    ``transition_from_previous_score`` expresses the quality of the
    transition from the previous element; it is 0.0 for the first
    element.
    """

    position: int
    segment_id: str
    segment_name: str
    role: str
    reason: str
    transition_from_previous_score: float


@dataclass
class SegmentPathResult:
    """Result returned by ``generate_segment_path``.

    ``main_path`` contains the recommended ordering of segments for the
    channel. Additional alternative paths can be included in
    ``alternative_paths`` when the configuration requests multiple
    variants. ``transition_scores`` is a matrix mapping segment IDs to
    transition scores used to derive the path. ``is_loop`` indicates
    whether the path should be considered circular.
    """

    channel_id: str
    main_path: List[SegmentPathElement]
    is_loop: bool
    global_score: float
    alternative_paths: List[List[SegmentPathElement]]
    transition_scores: Dict[str, Dict[str, float]]
    diagnostics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MediaMatch:
    """Represents the assignment of a new media item to existing segments.

    ``status`` can be one of ``accepted``, ``secondary``, ``ambiguous``,
    ``rejected`` or ``pending``. ``primary_segment_id`` is the segment
    chosen as the best fit for the media, with associated score. The
    ``secondary_matches`` list contains tuples of other segments and their
    scores when secondary matches are permitted. ``decision_reason``
    explains why the media received its status.
    """

    media_id: str
    status: str
    primary_segment_id: Optional[str]
    primary_score: Optional[float]
    secondary_matches: List[Tuple[str, float]]
    decision_reason: str


@dataclass
class MediaSegmentMatchingResult:
    """Result returned by ``match_media_to_segments``.

    It aggregates match information for multiple media items, along with
    lists of unmatched and ambiguous items, plus any diagnostics.
    """

    matches: List[MediaMatch]
    unmatched: List[str]
    ambiguous: List[str]
    diagnostics: Dict[str, Any] = field(default_factory=dict)
