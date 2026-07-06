"""
Feature extraction utilities for the TV programming algorithm.

This module converts raw ``MediaInput`` instances into numerical feature
vectors suitable for clustering and similarity computation.

The current extractor (state version "2.0") encodes each editorial axis
as a weighted block of multi-hot / one-hot dimensions:

- categorical vocabularies are learned from the corpus and filtered by
  document frequency: values carried by too few media (no grouping
  power) or by almost the whole corpus (no separating power) are dropped
  automatically, whatever the library looks like;
- multi-hot values are weighted by IDF so ubiquitous values weigh less
  than discriminative ones;
- numeric fields are encoded through absolute, data-independent buckets
  (duration bucket, release decade, age bracket) with an explicit
  ``unknown`` bucket instead of a biased zero;
- each block is L2-normalised then scaled by a configurable weight, and
  the final vector is L2-normalised. On the unit sphere the Euclidean
  distance used by k-means is a monotone function of the cosine
  similarity used for scoring, so a single geometry serves both.

The previous extractor (state version "1.0") is kept as
``LegacyFeatureExtractor`` so that model states persisted by older runs
keep vectorising new media identically during incremental matching.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List, Any, Optional

import numpy as np

from .inputs import MediaInput

FEATURE_STATE_VERSION = "2.0"

# Relative editorial importance of each block. Categories carry the main
# thematic signal; format, nature and anime are first-order channel axes;
# languages and origins are secondary context.
DEFAULT_BLOCK_WEIGHTS: Dict[str, float] = {
    "nature": 0.8,
    "container_kind": 0.6,
    "is_anime": 0.8,
    "categories": 1.0,
    "audio_languages": 0.3,
    "subtitle_languages": 0.1,
    "countries": 0.3,
    "studios": 0.3,
    "directors": 0.2,
    "duration_bucket": 0.8,
    "decade": 0.5,
    "age_bucket": 0.5,
}

UNKNOWN_BUCKET = "unknown"


def _normalise_string(value: Optional[str]) -> str:
    """Lowercases and strips a string. Returns an empty string for None."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value.strip().lower())


def duration_bucket(seconds: Optional[float]) -> str:
    """Converts a duration in seconds to an absolute bucket name."""
    if seconds is None:
        return UNKNOWN_BUCKET
    minutes = seconds / 60.0
    if minutes < 5:
        return "very_short"
    if minutes < 15:
        return "short"
    if minutes < 30:
        return "tv_short"
    if minutes < 45:
        return "medium_episode"
    if minutes < 65:
        return "long_episode"
    if minutes < 130:
        return "film_length"
    return "very_long"


def decade_bucket(year: Optional[int]) -> str:
    """Converts a release year to an absolute decade bucket ("1990s")."""
    if year is None or year <= 0:
        return UNKNOWN_BUCKET
    return f"{(int(year) // 10) * 10}s"


def age_bucket(min_age: Optional[int]) -> str:
    """Converts a minimum age to an absolute audience bracket."""
    if min_age is None:
        return UNKNOWN_BUCKET
    if min_age < 10:
        return "all_audiences"
    if min_age < 13:
        return "10_plus"
    if min_age < 16:
        return "13_plus"
    if min_age < 18:
        return "16_plus"
    return "18_plus"


def anime_bucket(is_anime: Optional[bool]) -> str:
    """Tri-state encoding of the anime flag."""
    if is_anime is None:
        return UNKNOWN_BUCKET
    return "anime" if is_anime else "non_anime"


def average_duration(media: MediaInput) -> Optional[float]:
    """Computes the average duration of a media item if possible.

    If both ``item_count`` and ``total_duration_seconds`` are provided
    the average is the division of the two; otherwise the mean of the
    available duration fields is used. Returns ``None`` when no duration
    information is available.
    """
    if media.item_count and media.total_duration_seconds:
        if media.item_count > 0:
            return media.total_duration_seconds / media.item_count
    durs = [
        d
        for d in [media.duration_min_seconds, media.duration_max_seconds, media.total_duration_seconds]
        if d is not None
    ]
    if durs:
        return sum(durs) / len(durs)
    return None


def _block_values(media: MediaInput, block: str) -> List[str]:
    """Returns the normalised raw values of a media for a given block."""
    if block == "nature":
        return [_normalise_string(str(media.nature))] if media.nature is not None else []
    if block == "container_kind":
        return [_normalise_string(str(media.container_kind))] if media.container_kind is not None else []
    if block == "is_anime":
        return [anime_bucket(media.is_anime)]
    if block == "categories":
        return [_normalise_string(c) for c in (media.categories or []) if c]
    if block == "audio_languages":
        return [
            _normalise_string(lang)
            for lang in (media.audio_languages or []) + (media.audio_languages_any or [])
            if lang
        ]
    if block == "subtitle_languages":
        return [
            _normalise_string(lang)
            for lang in (media.subtitle_languages or []) + (media.subtitle_languages_any or [])
            if lang
        ]
    if block == "countries":
        return [_normalise_string(c) for c in (media.countries or []) if c]
    if block == "studios":
        return [_normalise_string(s) for s in (media.studios or []) if s]
    if block == "directors":
        return [_normalise_string(d) for d in (media.directors or []) if d]
    if block == "duration_bucket":
        return [duration_bucket(average_duration(media))]
    if block == "decade":
        return [decade_bucket(media.release_year_min or media.release_year_max)]
    if block == "age_bucket":
        return [age_bucket(media.min_age)]
    raise KeyError(f"Unknown feature block: {block}")


class FeatureExtractor:
    """Learns and applies the block-based feature mapping (state v2).

    See the module docstring for the encoding principles. The public
    surface (``fit`` / ``transform`` / ``to_state`` / ``from_state``) is
    shared with ``LegacyFeatureExtractor``; ``from_state`` dispatches on
    the persisted state version.
    """

    BLOCKS = list(DEFAULT_BLOCK_WEIGHTS.keys())

    def __init__(
        self,
        max_features: int = 1000,
        min_df_count: int = 2,
        max_df_ratio: float = 0.9,
        block_weights: Optional[Dict[str, float]] = None,
    ):
        self.max_features = max_features
        self.min_df_count = min_df_count
        self.max_df_ratio = max_df_ratio
        self.block_weights = {**DEFAULT_BLOCK_WEIGHTS, **(block_weights or {})}
        # Learned per block: ordered vocabulary and per-value IDF weight
        self.vocabularies: Dict[str, List[str]] = {}
        self.idf_weights: Dict[str, List[float]] = {}

    def fit(self, media_list: List[MediaInput]) -> None:
        """Learns filtered vocabularies and IDF weights from the corpus."""
        n = len(media_list)
        self.vocabularies = {}
        self.idf_weights = {}
        if n == 0:
            return

        for block in self.BLOCKS:
            df: Counter[str] = Counter()
            for media in media_list:
                for value in set(_block_values(media, block)):
                    df[value] += 1

            kept: List[str] = []
            for value, count in df.most_common():
                if count < self.min_df_count:
                    continue
                if n > 1 and count / n > self.max_df_ratio:
                    continue
                kept.append(value)
                if len(kept) >= self.max_features:
                    break

            # Deterministic order: most frequent first, then alphabetical
            kept.sort(key=lambda value: (-df[value], value))
            self.vocabularies[block] = kept
            self.idf_weights[block] = [
                math.log((1 + n) / (1 + df[value])) + 1.0
                for value in kept
            ]

    def transform(self, media: MediaInput) -> List[float]:
        """Converts a single ``MediaInput`` into a weighted unit vector."""
        parts: List[np.ndarray] = []
        for block in self.BLOCKS:
            vocab = self.vocabularies.get(block, [])
            if not vocab:
                continue
            idf = self.idf_weights.get(block) or [1.0] * len(vocab)
            values = set(_block_values(media, block))
            sub = np.array(
                [idf[i] if vocab[i] in values else 0.0 for i in range(len(vocab))],
                dtype=float,
            )
            norm = np.linalg.norm(sub)
            if norm > 0:
                sub = sub / norm
            parts.append(sub * self.block_weights.get(block, 1.0))

        if not parts:
            return []
        vector = np.concatenate(parts)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector.tolist()

    def to_state(self) -> Dict[str, Any]:
        """Serialises the extractor to a JSON-compatible dict."""
        return {
            "version": FEATURE_STATE_VERSION,
            "max_features": self.max_features,
            "min_df_count": self.min_df_count,
            "max_df_ratio": self.max_df_ratio,
            "block_weights": self.block_weights,
            "vocabularies": self.vocabularies,
            "idf_weights": self.idf_weights,
        }

    @classmethod
    def from_state(cls, state: Dict[str, Any]) -> "FeatureExtractor | LegacyFeatureExtractor":
        """Reconstructs an extractor, dispatching on the state version.

        States persisted before the block-based encoding (no ``version``
        key) are restored as ``LegacyFeatureExtractor`` so incremental
        matching against old runs keeps producing identical vectors.
        """
        if state.get("version") != FEATURE_STATE_VERSION:
            return LegacyFeatureExtractor.from_state(state)
        fe = cls(
            max_features=state.get("max_features", 1000),
            min_df_count=state.get("min_df_count", 2),
            max_df_ratio=state.get("max_df_ratio", 0.9),
            block_weights=state.get("block_weights"),
        )
        fe.vocabularies = {block: list(values) for block, values in (state.get("vocabularies") or {}).items()}
        fe.idf_weights = {block: list(values) for block, values in (state.get("idf_weights") or {}).items()}
        return fe

    # Kept for callers that used the private helper on the v1 extractor.
    def _average_duration(self, media: MediaInput) -> Optional[float]:
        return average_duration(media)


class LegacyFeatureExtractor:
    """Feature extractor matching the persisted state version "1.0".

    Frozen implementation: only used to vectorise new media against model
    states produced before the block-based encoding, so those runs keep
    matching consistently. Do not extend it.
    """

    def __init__(self, max_features: int = 1000):
        self.max_features = max_features
        self.natures: List[str] = []
        self.container_kinds: List[str] = []
        self.categories: List[str] = []
        self.languages: List[str] = []
        self.countries: List[str] = []
        self.duration_min: float = 0.0
        self.duration_max: float = 1.0
        self.rating_min: float = 0.0
        self.rating_max: float = 1.0

    def _average_duration(self, media: MediaInput) -> Optional[float]:
        return average_duration(media)

    def transform(self, media: MediaInput) -> List[float]:
        vector: List[float] = []
        nature_value = str(media.nature).strip().lower() if media.nature is not None else None
        for n in self.natures:
            vector.append(1.0 if nature_value == n else 0.0)
        container_value = str(media.container_kind).strip().lower() if media.container_kind is not None else None
        for ck in self.container_kinds:
            vector.append(1.0 if container_value == ck else 0.0)
        media_categories = {_normalise_string(c) for c in (media.categories or []) if c}
        for c in self.categories:
            vector.append(1.0 if c in media_categories else 0.0)
        media_langs = {
            _normalise_string(lang)
            for lang in (media.audio_languages or [])
            + (media.subtitle_languages or [])
            + (media.audio_languages_any or [])
            + (media.subtitle_languages_any or [])
            if lang
        }
        for lang in self.languages:
            vector.append(1.0 if lang in media_langs else 0.0)
        media_countries = {_normalise_string(co) for co in (media.countries or []) if co}
        for co in self.countries:
            vector.append(1.0 if co in media_countries else 0.0)
        avg_dur = average_duration(media)
        if avg_dur is None:
            vector.append(0.0)
        else:
            vector.append((avg_dur - self.duration_min) / (self.duration_max - self.duration_min))
        rating = media.overall_rating_score or media.community_rating_score or media.critic_rating_score
        if rating is None:
            vector.append(0.0)
        else:
            vector.append((rating - self.rating_min) / (self.rating_max - self.rating_min))
        return vector

    def to_state(self) -> Dict[str, Any]:
        return {
            "max_features": self.max_features,
            "natures": self.natures,
            "container_kinds": self.container_kinds,
            "categories": self.categories,
            "languages": self.languages,
            "countries": self.countries,
            "duration_min": self.duration_min,
            "duration_max": self.duration_max,
            "rating_min": self.rating_min,
            "rating_max": self.rating_max,
        }

    @classmethod
    def from_state(cls, state: Dict[str, Any]) -> "LegacyFeatureExtractor":
        fe = cls(max_features=state.get("max_features", 1000))
        fe.natures = state.get("natures", [])
        fe.container_kinds = state.get("container_kinds", [])
        fe.categories = state.get("categories", [])
        fe.languages = state.get("languages", [])
        fe.countries = state.get("countries", [])
        fe.duration_min = state.get("duration_min", 0.0)
        fe.duration_max = state.get("duration_max", 1.0)
        fe.rating_min = state.get("rating_min", 0.0)
        fe.rating_max = state.get("rating_max", 1.0)
        return fe
