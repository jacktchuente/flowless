"""
Implementation of the segmentation process for TV programming.

The ``run_segmentation`` function takes a list of ``MediaInput`` objects
and optionally a ``SegmentationConfig``. It normalises and vectorises
the media, performs clustering to group similar items into candidate
segments, scores each cluster, and returns only those clusters that
qualify as programmable segments. The function also produces a model
state that can be used later for matching new media to the segments.

Vectors produced by the feature extractor are L2-normalised, so the
Euclidean geometry used by k-means and the acceptance thresholds is
consistent with the cosine similarity used for membership scores
(d² = 2 − 2·cos on the unit sphere).
"""

from __future__ import annotations

import math
import uuid
from typing import List, Dict, Optional, Any

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
from .features import (
    FeatureExtractor,
    age_bucket,
    anime_bucket,
    average_duration,
    decade_bucket,
    duration_bucket,
)
from .scoring import (
    compute_silhouette_scores,
    compute_cluster_silhouette,
    distinctiveness_score,
    format_consistency_score,
    volume_score,
    labelability_score,
    programmable_score,
    similarity,
)

DURATION_BUCKET_LABELS = {
    "very_short": "courts",
    "short": "courts",
    "tv_short": "30 min",
    "medium_episode": "45 min",
    "long_episode": "1h",
    "film_length": "film",
    "very_long": "longs",
}


def _generate_segment_name(dominant_nature: Optional[str], dominant_categories: List[str], bucket: str) -> str:
    """Generates a human friendly name for a segment based on its profile."""
    parts: List[str] = []
    if dominant_nature:
        parts.append(dominant_nature.capitalize())
    if dominant_categories:
        # Use up to two categories in the name
        parts.append(" / ".join([c.capitalize() for c in dominant_categories[:2]]))
    if bucket and bucket != "unknown":
        parts.append(DURATION_BUCKET_LABELS.get(bucket, bucket))
    if not parts:
        return "Segment"
    return " ".join(parts)


def _dominant(values: List[str]) -> Optional[str]:
    if not values:
        return None
    counts: Dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return max(counts, key=counts.get)


def _empty_result(config: SegmentationConfig, message: str, media: List[MediaInput], fe: FeatureExtractor) -> SegmentationResult:
    model_state = SegmentationModelState(
        feature_state=fe.to_state(),
        cluster_centroids={},
        acceptance_thresholds={},
        algorithm=config.algorithm,
        version="1.0",
    )
    return SegmentationResult(
        segments=[],
        memberships=[],
        outliers=[],
        weak_clusters=[m.id for m in media],
        model_state=model_state,
        diagnostics={"message": message},
    )


def run_segmentation(
    media: List[MediaInput],
    config: Optional[SegmentationConfig] = None,
) -> SegmentationResult:
    """Analyse media and produce stable programmable segments.

    This function clusters the provided media using k-means (with a search
    over candidate k values when ``candidate_cluster_counts`` is ``None``).
    It then scores each cluster and retains only those that meet the
    programmable criteria. Outliers and weak clusters are reported
    separately. When ``config.allow_multi_segment`` is enabled, media that
    satisfy the acceptance threshold of other segments also receive
    secondary memberships there, so segments are unique by their full
    composition rather than a strict partition. The function returns a
    ``SegmentationResult`` containing the valid segments, membership
    assignments, outliers, weak clusters and a model state for later use.
    """
    if config is None:
        config = SegmentationConfig()

    fe = FeatureExtractor(
        max_features=config.max_features,
        min_df_count=config.min_df_count,
        max_df_ratio=config.max_df_ratio,
        block_weights=config.block_weights,
    )
    fe.fit(media)

    if not media:
        return _empty_result(config, "No media provided", media, fe)

    vectors = [fe.transform(m) for m in media]
    vectors_np = np.array(vectors, dtype=float)
    n_samples = len(media)
    if vectors_np.size == 0:
        return _empty_result(config, "No discriminative feature available", media, fe)

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
    best_score = -math.inf
    silhouette_scores: Dict[int, float] = {}
    selection_scores: Dict[int, float] = {}
    # Try each k; pick the best silhouette penalised by cluster imbalance
    # so a trivial "one giant cluster" split does not win by default.
    for k in candidate_k:
        try:
            model = KMeans(n_clusters=k, random_state=config.random_state)
            labels = model.fit_predict(vectors_np)
            silhouette = compute_silhouette_scores(vectors_np, labels)
            largest_share = max(np.bincount(labels)) / n_samples
            imbalance = max(0.0, largest_share - config.max_cluster_ratio)
            selection = silhouette - config.cluster_imbalance_penalty * imbalance
            silhouette_scores[k] = silhouette
            selection_scores[k] = selection
            if selection > best_score:
                best_score = selection
                best_k = k
        except Exception:
            continue

    # Fit final model with best_k to obtain centroids and labels
    if best_k <= 1:
        final_labels = np.zeros(n_samples, dtype=int)
    else:
        model = KMeans(n_clusters=best_k, random_state=config.random_state)
        final_labels = model.fit_predict(vectors_np)

    # Group media by cluster index
    clusters: Dict[int, List[int]] = {}
    for idx, cluster_id in enumerate(final_labels):
        clusters.setdefault(int(cluster_id), []).append(idx)

    # Mean vector per cluster, used both as reference vector and to
    # compute a real separation score against the other clusters.
    cluster_means: Dict[int, np.ndarray] = {
        cluster_id: vectors_np[indices].mean(axis=0)
        for cluster_id, indices in clusters.items()
    }

    segments: List[ProgrammableSegment] = []
    memberships: List[SegmentMembership] = []
    outliers: List[str] = []
    weak_clusters: List[str] = []
    acceptance_thresholds: Dict[str, float] = {}
    centroid_map: Dict[str, List[float]] = {}
    segment_primary_indices: Dict[str, set[int]] = {}
    diagnostics: Dict[str, Any] = {
        "candidate_k": candidate_k,
        "silhouette_scores": silhouette_scores,
        "selection_scores": selection_scores,
        "selected_k": best_k,
        "global_silhouette": silhouette_scores.get(best_k, 0.0),
        "allow_multi_segment": config.allow_multi_segment,
    }

    # Evaluate each cluster
    for cluster_id, indices in clusters.items():
        cluster_size = len(indices)
        durations: List[float] = []
        total_duration_seconds = 0.0
        for idx in indices:
            m = media[idx]
            avg = average_duration(m)
            if avg is not None:
                durations.append(avg)
                # Approximate total duration as average times number of items (if available)
                count = m.item_count or 1
                total_duration_seconds += avg * count

        category_counts: Dict[str, int] = {}
        for idx in indices:
            for cat in media[idx].categories or []:
                key = cat.strip().lower()
                if key:
                    category_counts[key] = category_counts.get(key, 0) + 1

        cluster_vectors = vectors_np[indices]
        cohesion_score = compute_cluster_silhouette(vectors_np, list(final_labels), cluster_id)
        other_means = [mean for other_id, mean in cluster_means.items() if other_id != cluster_id]
        separation_score = distinctiveness_score(cluster_means[cluster_id], other_means)
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
        natures = [str(media[idx].nature).strip().lower() for idx in indices if media[idx].nature is not None]
        container_kinds = [
            str(media[idx].container_kind).strip().lower()
            for idx in indices
            if media[idx].container_kind is not None
        ]
        cats: List[str] = []
        for idx in indices:
            cats.extend([c.strip().lower() for c in media[idx].categories or [] if c])
        langs: List[str] = []
        for idx in indices:
            langs.extend(
                [
                    lang.strip().lower()
                    for lang in (media[idx].audio_languages or []) + (media[idx].audio_languages_any or [])
                    if lang
                ]
            )
        decades = [
            decade_bucket(media[idx].release_year_min or media[idx].release_year_max)
            for idx in indices
        ]
        age_buckets = [age_bucket(media[idx].min_age) for idx in indices]
        anime_values = [anime_bucket(media[idx].is_anime) for idx in indices]

        dominant_nature = _dominant(natures)
        dominant_container = _dominant(container_kinds)
        cat_counts: Dict[str, int] = {}
        for c in cats:
            cat_counts[c] = cat_counts.get(c, 0) + 1
        dominant_categories = sorted(cat_counts, key=cat_counts.get, reverse=True)[:3]
        lang_counts: Dict[str, int] = {}
        for lang in langs:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
        dominant_languages = sorted(lang_counts, key=lang_counts.get, reverse=True)[:3]
        known_decades = sorted({d for d in decades if d != "unknown"})
        avg_duration_value = sum(durations) / len(durations) if durations else None
        bucket = duration_bucket(avg_duration_value)
        name = _generate_segment_name(dominant_nature, dominant_categories, bucket)
        description = f"Segment {name} composé de {cluster_size} médias."
        profile = {
            "dominant_nature": dominant_nature,
            "dominant_container_kind": dominant_container,
            "dominant_categories": dominant_categories,
            "avg_duration_seconds": avg_duration_value,
            "duration_bucket": bucket,
            "dominant_languages": dominant_languages,
            "decades": known_decades,
            "dominant_decade": _dominant([d for d in decades if d != "unknown"]),
            "dominant_age_bucket": _dominant([a for a in age_buckets if a != "unknown"]),
            "dominant_anime": _dominant([a for a in anime_values if a != "unknown"]),
            "editorial_summary": description,
        }
        reference_vector = cluster_means[cluster_id].tolist()
        # Compute acceptance threshold: maximum distance inside cluster scaled
        distances = [np.linalg.norm(cv - cluster_means[cluster_id]) for cv in cluster_vectors]
        if distances:
            threshold = float(np.percentile(distances, 90) * 1.1)
        else:
            threshold = 0.0

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
        segment_primary_indices[seg_id] = set(indices)
        # Record primary memberships
        for idx in indices:
            score = similarity(vectors[idx], reference_vector)
            memberships.append(
                SegmentMembership(media_id=media[idx].id, segment_id=seg_id, score=score, is_primary=True)
            )

    # Secondary memberships: a media may also belong to any other segment
    # whose acceptance threshold it satisfies, or that sits at most
    # ``multi_segment_distance_ratio`` times farther than its primary
    # segment (scale-free, so it works whatever the corpus geometry).
    # Segments then become unique by their full composition instead of
    # forming a strict partition.
    if config.allow_multi_segment and len(segments) > 1:
        primary_distance_by_index: Dict[int, float] = {}
        for segment in segments:
            reference = np.array(segment.reference_vector, dtype=float)
            for idx in segment_primary_indices[segment.segment_id]:
                primary_distance_by_index[idx] = float(np.linalg.norm(vectors_np[idx] - reference))

        secondary_count = 0
        for segment in segments:
            reference = np.array(segment.reference_vector, dtype=float)
            threshold = acceptance_thresholds[segment.segment_id]
            primary_indices = segment_primary_indices[segment.segment_id]
            for idx in range(n_samples):
                if idx in primary_indices:
                    continue
                distance = float(np.linalg.norm(vectors_np[idx] - reference))
                primary_distance = primary_distance_by_index.get(idx)
                within_threshold = distance <= threshold
                within_ratio = (
                    primary_distance is not None
                    and primary_distance > 0
                    and distance <= config.multi_segment_distance_ratio * primary_distance
                )
                if not within_threshold and not within_ratio:
                    continue
                memberships.append(
                    SegmentMembership(
                        media_id=media[idx].id,
                        segment_id=segment.segment_id,
                        score=similarity(vectors[idx], segment.reference_vector),
                        is_primary=False,
                    )
                )
                secondary_count += 1
        diagnostics["secondary_membership_count"] = secondary_count

    model_state = SegmentationModelState(
        feature_state=fe.to_state(),
        cluster_centroids=centroid_map,
        acceptance_thresholds=acceptance_thresholds,
        algorithm=config.algorithm,
        version="2.0",
    )
    return SegmentationResult(
        segments=segments,
        memberships=memberships,
        outliers=outliers,
        weak_clusters=weak_clusters,
        model_state=model_state,
        diagnostics=diagnostics,
    )
