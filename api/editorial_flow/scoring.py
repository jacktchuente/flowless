"""
Scoring utilities for the TV programming algorithm.

This module defines functions to assess the quality of clusters and
communities, as well as compute pairwise similarity and transition
scores. While the scoring functions implemented here are simple,
they encapsulate the heuristics described in the specification and
provide a single place to adjust weights and formulas.
"""

from __future__ import annotations

from typing import List, Dict, Any, Iterable

import numpy as np
from sklearn.metrics import silhouette_samples, silhouette_score


def compute_silhouette_scores(vectors: np.ndarray, labels: List[int]) -> float:
    """Computes the overall silhouette score for a clustering assignment.

    Returns a value in [-1, 1] where higher values indicate more
    separated and cohesive clusters. If only a single cluster exists or
    less than 2 clusters are present the score falls back to 0.0.
    """
    # If only one cluster or trivial assignment, silhouette_score raises
    unique_labels = set(labels)
    if len(unique_labels) < 2:
        return 0.0
    try:
        return float(silhouette_score(vectors, labels))
    except Exception:
        return 0.0


def compute_cluster_silhouette(vectors: np.ndarray, labels: List[int], cluster_id: int) -> float:
    """Computes the mean silhouette score for a single cluster.

    If fewer than 2 clusters exist returns 0.0.
    """
    unique_labels = set(labels)
    if len(unique_labels) < 2:
        return 0.0
    try:
        sil_samples = silhouette_samples(vectors, labels)
        mask = np.array(labels) == cluster_id
        if mask.sum() == 0:
            return 0.0
        return float(sil_samples[mask].mean())
    except Exception:
        return 0.0


def format_consistency_score(durations: List[float]) -> float:
    """Scores how consistent the durations are within a cluster.

    Lower standard deviation yields higher score. If no durations are
    provided the function returns 0.5 as a neutral score.
    """
    if not durations:
        return 0.5
    arr = np.array(durations, dtype=float)
    # Normalise by max duration to avoid scaling issues
    max_dur = arr.max() if arr.max() > 0 else 1.0
    std = arr.std() / max_dur
    # Map std to score: high std -> low score, low std -> high score
    score = 1.0 / (1.0 + std * 10.0)
    return float(max(0.0, min(1.0, score)))


def volume_score(num_items: int, total_duration: float) -> float:
    """Scores a cluster based on its size and total duration.

    Uses a logistic-like function favouring clusters with more than 2
    items or more than two hours of content. The score is capped
    between 0 and 1.
    """
    # Convert duration to hours
    hours = total_duration / 3600.0
    items_component = 1 - np.exp(-num_items / 3.0)
    duration_component = 1 - np.exp(-hours / 2.0)
    return float(max(0.0, min(1.0, 0.5 * items_component + 0.5 * duration_component)))


def labelability_score(category_counts: Dict[str, int]) -> float:
    """Scores how easily a cluster can be described by a small number of categories.

    The score increases when a few categories dominate the distribution.
    It is computed as the sum of the relative frequencies of the top
    three categories. If no categories are present the function
    returns 0.0.
    """
    total = sum(category_counts.values())
    if total == 0:
        return 0.0
    top_counts = sorted(category_counts.values(), reverse=True)[:3]
    return float(sum(top_counts) / total)


# A silhouette of 0.5 is already excellent on sparse multi-tag data, so the
# cohesion input is normalised against this realistic ceiling instead of the
# theoretical 1.0 (which no real corpus ever reaches).
COHESION_REFERENCE_SILHOUETTE = 0.5


def normalised_cohesion(silhouette_value: float) -> float:
    """Maps a raw silhouette onto [0, 1] against a realistic ceiling."""
    return float(max(0.0, min(1.0, silhouette_value / COHESION_REFERENCE_SILHOUETTE)))


def programmable_score(cohesion: float, separation: float, format_consistency: float, volume: float, labelability: float) -> float:
    """Combines various cluster scores into a single programmability score.

    The weights reflect the importance of each criterion. Cohesion and
    separation are emphasised, as well as consistency of duration and
    sufficient volume. Labelability contributes modestly. The result
    is clamped between 0 and 1. Callers are expected to pass a cohesion
    already normalised onto [0, 1] (see ``normalised_cohesion``) so that
    a good cluster lands around 0.7-0.8 instead of plateauing at ~0.6.
    """
    score = (
        0.3 * cohesion
        + 0.2 * separation
        + 0.2 * format_consistency
        + 0.2 * volume
        + 0.1 * labelability
    )
    return float(max(0.0, min(1.0, score)))


def similarity(a: Iterable[float], b: Iterable[float]) -> float:
    """Cosine similarity remapped from [-1, 1] to [0, 1].

    Frozen legacy scale: model states persisted with version "1.0" were
    scored and thresholded on this mapping, so it must keep producing
    identical values for those runs. New (v2) code paths use
    ``cosine_similarity`` instead, whose scale is meaningful for
    non-negative feature vectors (0 = unrelated, 1 = identical).
    """
    a_arr = np.array(list(a), dtype=float)
    b_arr = np.array(list(b), dtype=float)
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    cos = float(np.dot(a_arr, b_arr) / (norm_a * norm_b))
    # Map from [-1,1] to [0,1]
    return max(0.0, min(1.0, (cos + 1.0) / 2.0))


def cosine_similarity(a: Iterable[float], b: Iterable[float]) -> float:
    """Raw cosine similarity clipped to [0, 1].

    With the non-negative v2 feature vectors the cosine already lives in
    [0, 1], so no remapping is needed: 0 means unrelated and 1 identical,
    which keeps membership scores and thresholds interpretable.
    """
    a_arr = np.array(list(a), dtype=float)
    b_arr = np.array(list(b), dtype=float)
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    cos = float(np.dot(a_arr, b_arr) / (norm_a * norm_b))
    return max(0.0, min(1.0, cos))


def diversity_score(category_sets: List[List[str]]) -> float:
    """Scores the diversity of categories across segments.

    The score is highest when the average per-segment category diversity
    sits around 0.5 of the total unique categories. Too little or too
    much diversity reduces the score. If there are no categories
    available the score is neutral (0.5).
    """
    all_cats = set(cat for cats in category_sets for cat in cats)
    total_unique = len(all_cats)
    if total_unique == 0:
        return 0.5
    # Compute diversity ratio per segment and average
    ratios = []
    for cats in category_sets:
        unique = len(set(cats)) if cats else 0
        ratios.append(unique / total_unique)
    avg_ratio = sum(ratios) / len(ratios) if ratios else 0.0
    # Optimal ratio at 0.5
    return float(max(0.0, 1.0 - abs(avg_ratio - 0.5) * 2.0))


def distinctiveness_score(
    community_centroid: Iterable[float],
    other_centroids: List[Iterable[float]],
    similarity_fn=cosine_similarity,
) -> float:
    """Computes how distinct a community is from other communities.

    The score decreases if the centroid of this community is very
    similar to any other centroid. It uses the raw cosine similarity by
    default; legacy callers may pass the mapped ``similarity``. If there
    are no other centroids the score is 1.0.
    """
    if not other_centroids:
        return 1.0
    scores = [similarity_fn(community_centroid, centroid) for centroid in other_centroids]
    max_sim = max(scores) if scores else 0.0
    return float(1.0 - max_sim)
