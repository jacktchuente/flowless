"""
Feature extraction utilities for the TV programming algorithm.

This module contains classes and helper functions to convert raw
``MediaInput`` instances into numerical feature vectors suitable for
clustering and similarity computation. The feature extractor learns
vocabularies of categorical values (e.g. categories, languages) from
the training data and stores them in a state object which can be used
later to vectorise new media consistently. No external dependencies
outside of the Python standard library and NumPy are required.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

import numpy as np

from .inputs import MediaInput


def _normalise_string(value: Optional[str]) -> str:
    """Lowercases and strips a string. Returns an empty string for None.

    Parameters
    ----------
    value: Optional[str]
        The string to normalise.

    Returns
    -------
    str
        The normalised string.
    """
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value.strip().lower())


@dataclass
class FeatureExtractor:
    """Learns and applies a feature mapping from ``MediaInput`` to vectors.

    The extractor builds vocabularies for categorical fields (nature,
    container_kind, categories, languages and countries) and stores
    normalisation ranges for numeric fields (duration and rating). It
    optionally limits the number of distinct features to ``max_features``
    when training. Each field is encoded as a one-hot or multi-hot
    vector. Numeric features are scaled to the [0, 1] range. The
    resulting feature vectors are dense lists of floats.
    """

    max_features: int = 1000

    # Learned vocabularies
    natures: List[str] = field(default_factory=list)
    container_kinds: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    countries: List[str] = field(default_factory=list)

    # Numeric ranges
    duration_min: float = 0.0
    duration_max: float = 1.0
    rating_min: float = 0.0
    rating_max: float = 1.0

    def fit(self, media_list: List[MediaInput]) -> None:
        """Learns the feature vocabularies and numeric ranges from media.

        Parameters
        ----------
        media_list: List[MediaInput]
            The media items to learn from.
        """
        # Reset vocabularies
        nature_set: set[str] = set()
        container_set: set[str] = set()
        category_counter: Counter[str] = Counter()
        language_counter: Counter[str] = Counter()
        country_counter: Counter[str] = Counter()
        durations: List[float] = []
        ratings: List[float] = []

        for m in media_list:
            # Collect categorical values
            if m.nature is not None:
                nature_set.add(str(m.nature).strip().lower())
            if m.container_kind is not None:
                container_set.add(str(m.container_kind).strip().lower())
            for cat in m.categories or []:
                if cat:
                    category_counter[_normalise_string(cat)] += 1
            # Combine all language lists
            for lang in (m.audio_languages or []) + (m.subtitle_languages or []) + (m.audio_languages_any or []) + (m.subtitle_languages_any or []):
                if lang:
                    language_counter[_normalise_string(lang)] += 1
            for c in m.countries or []:
                if c:
                    country_counter[_normalise_string(c)] += 1
            # Numeric values
            avg_dur = self._average_duration(m)
            if avg_dur is not None:
                durations.append(float(avg_dur))
            rating = m.overall_rating_score or m.community_rating_score or m.critic_rating_score
            if rating is not None:
                ratings.append(float(rating))
        # Truncate vocabularies based on frequency and max_features
        self.natures = sorted(nature_set)
        self.container_kinds = sorted(container_set)
        # Keep only the most frequent categories/languages/countries up to max_features
        def top_keys(counter: Counter[str]) -> List[str]:
            return [k for k, _ in counter.most_common(self.max_features)]
        self.categories = top_keys(category_counter)
        self.languages = top_keys(language_counter)
        self.countries = top_keys(country_counter)
        # Numeric ranges
        self.duration_min = min(durations) if durations else 0.0
        self.duration_max = max(durations) if durations else 1.0
        if self.duration_min == self.duration_max:
            self.duration_max += 1.0
        self.rating_min = min(ratings) if ratings else 0.0
        self.rating_max = max(ratings) if ratings else 10.0
        if self.rating_min == self.rating_max:
            self.rating_max += 1.0

    def _average_duration(self, media: MediaInput) -> Optional[float]:
        """Computes the average duration of a media item if possible.

        Duration is determined according to the guidelines: if both
        ``item_count`` and ``total_duration_seconds`` are provided the
        average is the division of the two; otherwise the mean of
        available duration_min_seconds, duration_max_seconds and
        total_duration_seconds is used. Returns ``None`` if no duration
        information is available.
        """
        durs: List[int] = []
        if media.item_count and media.total_duration_seconds:
            # Use total / count
            if media.item_count > 0:
                return media.total_duration_seconds / media.item_count
        # Fallback to available durations
        for d in [media.duration_min_seconds, media.duration_max_seconds, media.total_duration_seconds]:
            if d is not None:
                durs.append(d)
        if durs:
            return sum(durs) / len(durs)
        return None

    def transform(self, media: MediaInput) -> List[float]:
        """Converts a single ``MediaInput`` into a feature vector.

        This method encodes categorical fields using one-hot/multi-hot
        encoding and scales numeric fields. When a value is missing it
        contributes nothing to the vector. The order of features is
        deterministic: natures, container kinds, categories, languages,
        countries, followed by numeric features.

        Parameters
        ----------
        media: MediaInput
            The media item to vectorise.

        Returns
        -------
        List[float]
            A dense list of floats representing the media.
        """
        vector: List[float] = []
        # Nature one-hot
        nature_value = str(media.nature).strip().lower() if media.nature is not None else None
        for n in self.natures:
            vector.append(1.0 if nature_value == n else 0.0)
        # Container kind one-hot
        container_value = str(media.container_kind).strip().lower() if media.container_kind is not None else None
        for ck in self.container_kinds:
            vector.append(1.0 if container_value == ck else 0.0)
        # Categories multi-hot
        media_categories = {_normalise_string(c) for c in (media.categories or []) if c}
        for c in self.categories:
            vector.append(1.0 if c in media_categories else 0.0)
        # Languages multi-hot
        media_langs = {_normalise_string(l) for l in (media.audio_languages or []) + (media.subtitle_languages or []) + (media.audio_languages_any or []) + (media.subtitle_languages_any or []) if l}
        for l in self.languages:
            vector.append(1.0 if l in media_langs else 0.0)
        # Countries multi-hot
        media_countries = {_normalise_string(co) for co in (media.countries or []) if co}
        for co in self.countries:
            vector.append(1.0 if co in media_countries else 0.0)
        # Numeric features
        # Duration scaled to [0, 1]
        avg_dur = self._average_duration(media)
        if avg_dur is None:
            vector.append(0.0)
        else:
            vector.append((avg_dur - self.duration_min) / (self.duration_max - self.duration_min))
        # Rating scaled to [0, 1]
        rating = media.overall_rating_score or media.community_rating_score or media.critic_rating_score
        if rating is None:
            vector.append(0.0)
        else:
            vector.append((rating - self.rating_min) / (self.rating_max - self.rating_min))
        return vector

    def to_state(self) -> Dict[str, Any]:
        """Serialises the extractor to a plain Python dict.

        The returned dictionary contains only JSON compatible types so
        that it can easily be persisted. It can later be passed into
        ``FeatureExtractor.from_state`` to reconstruct the extractor.
        """
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
    def from_state(cls, state: Dict[str, Any]) -> "FeatureExtractor":
        """Reconstructs a ``FeatureExtractor`` from its serialised state."""
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
