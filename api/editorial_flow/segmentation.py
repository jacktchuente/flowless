"""
Implementation of the segmentation process for TV programming.

The ``run_segmentation`` function takes a list of ``MediaInput`` objects
and optionally a ``SegmentationConfig``. It normalises and vectorises
the media, performs clustering to group similar items into candidate
segments, scores each cluster, and returns only those clusters that
qualify as programmable segments. The function also produces a model
state that can be used later for matching new media to the segments.
"""

from __future__ import annotations

import math
import uuid
from typing import List, Dict, Optional, Tuple, Any

import numpy as np
from sklearn.cluster import KMeans

from .inputs import MediaInput
from .outputs import (
    ProgrammableSegment,
    SegmentMembership,
    SegmentationModelState,
    SegmentationResult,
)
from .configs import SegmentationConfig
from .features import FeatureExtractor
from .scoring import (
    compute_silhouette_scores,
    compute_cluster_silhouette,
    format_consistency_score,
    volume_score,
    labelability_score,
    programmable_score,
    similarity,
)


def _duration_bucket(seconds: Optional[float]) -> str:
    """Converts a duration in seconds to a human friendly bucket name."""
    if seconds is None:
        return "unknown"
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


def _generate_segment_name(dominant_nature: Optional[str], dominant_categories: List[str], duration_bucket: str) -> str:
    """Generates a human friendly name for a segment based on its profile."""
    parts: List[str] = []
    if dominant_nature:
        parts.append(dominant_nature.capitalize())
    if dominant_categories:
        # Use up to two categories in the name
        parts.append(" / ".join([c.capitalize() for c in dominant_categories[:2]]))
    if duration_bucket and duration_bucket != "unknown":
        # Map buckets to readable terms
        bucket_map = {
            "very_short": "courts",
            "short": "courts",
            "tv_short": "30 min",
            "medium_episode": "45 min",
            "long_episode": "1h",
            "film_length": "film",
            "very_long": "longs",
        }
        parts.append(bucket_map.get(duration_bucket, duration_bucket))
    if not parts:
        return "Segment"
    return " ".join(parts)


def run_segmentation(
    media: List[MediaInput],
    config: Optional[SegmentationConfig] = None,
) -> SegmentationResult:
    """Analyse media and produce stable programmable segments.

    This function clusters the provided media using k-means (with a search
    over candidate k values when ``candidate_cluster_counts`` is ``None``).
    It then scores each cluster and retains only those that meet the
    programmable criteria. Outliers and weak clusters are reported
    separately. The function returns a ``SegmentationResult`` containing
    the valid segments, membership assignments, outliers, weak clusters
    and a model state for later use.
    """
    if config is None:
        config = SegmentationConfig()
    # Edge case: no media provided
    if not media:
        fe = FeatureExtractor(max_features=config.max_features)
        fe.fit([])
        model_state = SegmentationModelState(
            feature_state=fe.to_state(),
            cluster_centroids={},
            acceptance_thresholds={},
            algorithm=config.algorithm,
        )
        return SegmentationResult(
            segments=[],
            memberships=[],
            outliers=[],
            weak_clusters=[],
            model_state=model_state,
            diagnostics={"message": "No media provided"},
        )
    # Normalise and vectorise media
    fe = FeatureExtractor(max_features=config.max_features)
    fe.fit(media)
    vectors = [fe.transform(m) for m in media]
    vectors_np = np.array(vectors, dtype=float)
    n_samples = len(media)
    # Determine candidate cluster counts
    if config.algorithm != "kmeans":
        raise ValueError(f"Unsupported algorithm: {config.algorithm}. Only 'kmeans' is available.")
    if config.candidate_cluster_counts:
        candidate_k = [k for k in config.candidate_cluster_counts if 1 < k < n_samples]
    else:
        # Reasonable range: 2 to min(sqrt(n) + 1, n-1) capped at 10
        max_k = max(2, min(int(math.sqrt(n_samples)) + 1, n_samples - 1, 10))
        candidate_k = list(range(2, max_k + 1))
    if not candidate_k:
        # Not enough samples to cluster meaningfully
        candidate_k = [1]
    best_k = 1
    best_score = -1.0
    best_labels: Optional[List[int]] = None
    silhouette_scores: Dict[int, float] = {}
    # Try each k and choose the one with the highest silhouette score
    for k in candidate_k:
        try:
            model = KMeans(n_clusters=k, random_state=config.random_state)
            labels = model.fit_predict(vectors_np)
            score = compute_silhouette_scores(vectors_np, labels)
            silhouette_scores[k] = score
            if score > best_score:
                best_score = score
                best_k = k
                best_labels = labels
        except Exception:
            continue
    if best_labels is None:
        # Fallback to single cluster
        best_k = 1
        best_labels = [0] * n_samples
    # Fit final model with best_k to obtain centroids and labels
    model = KMeans(n_clusters=best_k, random_state=config.random_state)
    final_labels = model.fit_predict(vectors_np)
    centroids = model.cluster_centers_.tolist()
    # Group media by cluster index
    clusters: Dict[int, List[int]] = {}
    for idx, cluster_id in enumerate(final_labels):
        clusters.setdefault(cluster_id, []).append(idx)
    segments: List[ProgrammableSegment] = []
    memberships: List[SegmentMembership] = []
    outliers: List[str] = []
    weak_clusters: List[str] = []
    acceptance_thresholds: Dict[str, float] = {}
    centroid_map: Dict[str, List[float]] = {}
    diagnostics: Dict[str, Any] = {
        "candidate_k": candidate_k,
        "silhouette_scores": silhouette_scores,
        "selected_k": best_k,
        "global_silhouette": best_score,
    }
    # Evaluate each cluster
    for cluster_id, indices in clusters.items():
        cluster_size = len(indices)
        # Compute durations and total duration
        durations: List[float] = []
        total_duration_seconds = 0.0
        for idx in indices:
            m = media[idx]
            avg = fe._average_duration(m)
            if avg is not None:
                durations.append(avg)
                # Approximate total duration as average times number of items (if available)
                count = m.item_count or 1
                total_duration_seconds += avg * count
            else:
                # If no duration, count as one item of zero length
                total_duration_seconds += 0.0
        # Compute category counts
        category_counts: Dict[str, int] = {}
        for idx in indices:
            for cat in media[idx].categories or []:
                key = cat.strip().lower()
                if key:
                    category_counts[key] = category_counts.get(key, 0) + 1
        # Compute cluster silhouette (cohesion + separation)
        cluster_vectors = vectors_np[indices]
        cluster_silhouette = compute_cluster_silhouette(vectors_np, list(final_labels), cluster_id)
        cohesion_score = cluster_silhouette
        separation_score = cluster_silhouette  # Approximate separation with silhouette
        fmt_score = format_consistency_score(durations)
        vol_score = volume_score(cluster_size, total_duration_seconds)
        lab_score = labelability_score(category_counts)
        prog_score = programmable_score(cohesion_score, separation_score, fmt_score, vol_score, lab_score)
        # Determine if this cluster qualifies as a segment
        if (
            cluster_size < config.min_cluster_size
            or cluster_size < config.min_items_per_segment
            or total_duration_seconds < config.min_total_duration_seconds
            or prog_score < config.min_programmable_score
        ):
            # Either too small or weak
            # If cluster has a single item and allow_outliers is True, treat as outlier
            if cluster_size <= 1 and config.allow_outliers:
                outliers.append(media[indices[0]].id)
            else:
                weak_clusters.extend([media[idx].id for idx in indices])
            continue
        # Create segment
        seg_id = str(uuid.uuid4())
        # Determine dominant attributes
        natures = [str(media[idx].nature).strip().lower() for idx in indices if media[idx].nature is not None]
        container_kinds = [str(media[idx].container_kind).strip().lower() for idx in indices if media[idx].container_kind is not None]
        cats = []
        for idx in indices:
            cats.extend([c.strip().lower() for c in media[idx].categories or [] if c])
        langs = []
        for idx in indices:
            langs.extend([l.strip().lower() for l in (media[idx].audio_languages or []) + (media[idx].subtitle_languages or []) + (media[idx].audio_languages_any or []) + (media[idx].subtitle_languages_any or []) if l])
        # Compute dominant values
        def _dominant(values: List[str]) -> Optional[str]:
            if not values:
                return None
            counts = {}
            for v in values:
                counts[v] = counts.get(v, 0) + 1
            return max(counts, key=counts.get)
        dominant_nature = _dominant(natures)
        dominant_container = _dominant(container_kinds)
        # Get top categories
        cat_counts = {}
        for c in cats:
            cat_counts[c] = cat_counts.get(c, 0) + 1
        dominant_categories = sorted(cat_counts, key=cat_counts.get, reverse=True)[:3]
        lang_counts = {}
        for l in langs:
            lang_counts[l] = lang_counts.get(l, 0) + 1
        dominant_languages = sorted(lang_counts, key=lang_counts.get, reverse=True)[:3]
        avg_duration = sum(durations) / len(durations) if durations else None
        bucket = _duration_bucket(avg_duration)
        name = _generate_segment_name(dominant_nature, dominant_categories, bucket)
        description = f"Segment {name} composé de {cluster_size} médias."
        profile = {
            "dominant_nature": dominant_nature,
            "dominant_container_kind": dominant_container,
            "dominant_categories": dominant_categories,
            "avg_duration_seconds": avg_duration,
            "duration_bucket": bucket,
            "dominant_languages": dominant_languages,
            "editorial_summary": description,
        }
        reference_vector = list(np.mean(cluster_vectors, axis=0))
        # Compute acceptance threshold: maximum distance inside cluster scaled
        distances = [np.linalg.norm(cv - np.array(reference_vector)) for cv in cluster_vectors]
        if distances:
            threshold = float(np.percentile(distances, 90) * 1.1)
        else:
            threshold = 0.0
        # Create ProgrammableSegment
        segment = ProgrammableSegment(
            segment_id=seg_id,
            name=name,
            description=description,
            profile=profile,
            reference_vector=reference_vector,
            reference_profile=profile,
            observed_profile=profile,
            programmable_score=prog_score,
            cohesion_score=cohesion_score,
            separation_score=separation_score,
            format_consistency_score=fmt_score,
            volume_score=vol_score,
            labelability_score=lab_score,
            acceptance_threshold=threshold,
            media_ids=[media[idx].id for idx in indices],
        )
        segments.append(segment)
        centroid_map[seg_id] = reference_vector
        acceptance_thresholds[seg_id] = threshold
        # Record memberships
        for idx in indices:
            m_id = media[idx].id
            # Membership score based on similarity
            score = similarity(vectors[idx], reference_vector)
            memberships.append(SegmentMembership(media_id=m_id, segment_id=seg_id, score=score, is_primary=True))
    # Build model state
    model_state = SegmentationModelState(
        feature_state=fe.to_state(),
        cluster_centroids=centroid_map,
        acceptance_thresholds=acceptance_thresholds,
        algorithm=config.algorithm,
        version="1.0",
    )
    return SegmentationResult(
        segments=segments,
        memberships=memberships,
        outliers=outliers,
        weak_clusters=weak_clusters,
        model_state=model_state,
        diagnostics=diagnostics,
    )
