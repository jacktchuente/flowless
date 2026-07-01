"""
Public API surface for the TV programming algorithm.

This package exposes four primary functions corresponding to the four
processes described in the specification: segmentation, channel
discovery, segment path generation and media matching. Callers should
construct appropriate input dataclasses and configuration objects and
invoke these functions directly. The implementation details are
encapsulated in submodules.
"""

from .segmentation import run_segmentation
from .channel_discovery import discover_channel_candidates
from .segment_path import generate_segment_path
from .matching import match_media_to_segments

__all__ = [
    "run_segmentation",
    "discover_channel_candidates",
    "generate_segment_path",
    "match_media_to_segments",
]
