"""Pure unit tests for the editorial_flow feature extraction and segmentation.

No database involved: everything runs on synthetic MediaInput lists.
"""

from django.test import SimpleTestCase

from editorial_flow.channel_discovery import discover_channel_candidates
from editorial_flow.configs import ChannelDiscoveryConfig, SegmentationConfig
from editorial_flow.outputs import ProgrammableSegment
from editorial_flow.features import (
    FeatureExtractor,
    LegacyFeatureExtractor,
    age_bucket,
    anime_bucket,
    decade_bucket,
    duration_bucket,
)
from editorial_flow.inputs import MediaInput
from editorial_flow.segmentation import run_segmentation


def make_media(media_id: str, categories: list[str], **kwargs) -> MediaInput:
    return MediaInput(id=media_id, title=media_id, categories=categories, **kwargs)


class BucketTests(SimpleTestCase):
    def test_buckets_handle_missing_values(self):
        self.assertEqual(duration_bucket(None), "unknown")
        self.assertEqual(decade_bucket(None), "unknown")
        self.assertEqual(age_bucket(None), "unknown")
        self.assertEqual(anime_bucket(None), "unknown")

    def test_buckets_are_absolute(self):
        self.assertEqual(duration_bucket(20 * 60), "tv_short")
        self.assertEqual(duration_bucket(110 * 60), "film_length")
        self.assertEqual(decade_bucket(1994), "1990s")
        self.assertEqual(age_bucket(16), "16_plus")
        self.assertEqual(anime_bucket(True), "anime")
        self.assertEqual(anime_bucket(False), "non_anime")


class FeatureExtractorTests(SimpleTestCase):
    def build_corpus(self) -> list[MediaInput]:
        media = []
        for index in range(10):
            media.append(
                make_media(
                    f"m{index}",
                    categories=["action", "everywhere"] if index < 5 else ["romance", "everywhere"],
                    release_year_min=1990 + index,
                    min_age=10,
                    is_anime=index % 2 == 0,
                )
            )
        # A value carried by a single media: no grouping power
        media[0].categories = media[0].categories + ["once-only"]
        return media

    def test_df_filter_drops_rare_and_ubiquitous_values(self):
        fe = FeatureExtractor(min_df_count=2, max_df_ratio=0.9)
        fe.fit(self.build_corpus())
        categories = fe.vocabularies["categories"]
        self.assertIn("action", categories)
        self.assertIn("romance", categories)
        self.assertNotIn("once-only", categories)  # df=1 < min_df_count
        self.assertNotIn("everywhere", categories)  # df=100% > max_df_ratio

    def test_empty_block_disappears(self):
        fe = FeatureExtractor(min_df_count=2, max_df_ratio=0.9)
        fe.fit(self.build_corpus())
        # No media has countries or studios: blocks are empty
        self.assertEqual(fe.vocabularies["countries"], [])
        self.assertEqual(fe.vocabularies["studios"], [])

    def test_transform_is_unit_norm(self):
        corpus = self.build_corpus()
        fe = FeatureExtractor()
        fe.fit(corpus)
        vector = fe.transform(corpus[0])
        self.assertTrue(vector)
        norm = sum(value * value for value in vector) ** 0.5
        self.assertAlmostEqual(norm, 1.0, places=6)

    def test_state_round_trip_produces_identical_vectors(self):
        corpus = self.build_corpus()
        fe = FeatureExtractor()
        fe.fit(corpus)
        restored = FeatureExtractor.from_state(fe.to_state())
        self.assertIsInstance(restored, FeatureExtractor)
        for media in corpus:
            self.assertEqual(fe.transform(media), restored.transform(media))

    def test_legacy_state_is_restored_as_legacy_extractor(self):
        legacy_state = {
            "max_features": 1000,
            "natures": ["fiction"],
            "container_kinds": ["series"],
            "categories": ["action", "romance"],
            "languages": ["fr"],
            "countries": [],
            "duration_min": 0.0,
            "duration_max": 3600.0,
            "rating_min": 0.0,
            "rating_max": 10.0,
        }
        restored = FeatureExtractor.from_state(legacy_state)
        self.assertIsInstance(restored, LegacyFeatureExtractor)
        media = make_media("m1", categories=["action"], nature="fiction", audio_languages=["fr"])
        vector = restored.transform(media)
        # nature one-hot, container one-hot, 2 categories, 1 language, 0 countries, duration, rating
        self.assertEqual(len(vector), 1 + 1 + 2 + 1 + 0 + 2)
        self.assertEqual(vector[0], 1.0)  # fiction
        self.assertEqual(vector[1], 0.0)  # series
        self.assertEqual(vector[2], 1.0)  # action
        self.assertEqual(vector[3], 0.0)  # romance

    def test_unknown_buckets_are_encoded_when_frequent(self):
        media = [
            make_media(f"a{i}", categories=["action", "guns"] if i % 2 else ["action", "cars"])
            for i in range(6)
        ]
        fe = FeatureExtractor(min_df_count=2, max_df_ratio=1.1)
        fe.fit(media)
        # All durations unknown -> single "unknown" value in the block
        self.assertEqual(fe.vocabularies["duration_bucket"], ["unknown"])


class SegmentationMultiMembershipTests(SimpleTestCase):
    def build_corpus(self) -> list[MediaInput]:
        media = []
        # Cluster A: action content with internal variance
        for index in range(6):
            extra = "guns" if index % 2 else "cars"
            media.append(make_media(f"a{index}", categories=["action", "war", extra]))
        # Cluster B: romance content with internal variance
        for index in range(6):
            extra = "tears" if index % 2 else "flowers"
            media.append(make_media(f"b{index}", categories=["romance", "drama", extra]))
        # Bridge media sharing both worlds
        media.append(make_media("x0", categories=["action", "war", "romance", "drama"]))
        media.append(make_media("x1", categories=["action", "war", "romance", "drama"]))
        return media

    def base_config(self, **kwargs) -> SegmentationConfig:
        return SegmentationConfig(
            candidate_cluster_counts=[2],
            min_programmable_score=0.0,
            min_df_count=2,
            **kwargs,
        )

    def test_strict_partition_without_multi_segment(self):
        result = run_segmentation(self.build_corpus(), self.base_config(allow_multi_segment=False))
        self.assertEqual(len(result.segments), 2)
        media_ids = [m.media_id for m in result.memberships]
        self.assertEqual(len(media_ids), len(set(media_ids)))
        self.assertTrue(all(m.is_primary for m in result.memberships))

    def test_multi_segment_creates_secondary_memberships(self):
        result = run_segmentation(self.build_corpus(), self.base_config(allow_multi_segment=True))
        self.assertEqual(len(result.segments), 2)
        secondary = [m for m in result.memberships if not m.is_primary]
        self.assertGreater(len(secondary), 0)
        # A secondary membership duplicates a media into another segment
        primary_by_media = {m.media_id: m.segment_id for m in result.memberships if m.is_primary}
        for membership in secondary:
            self.assertNotEqual(membership.segment_id, primary_by_media[membership.media_id])
        self.assertEqual(result.diagnostics.get("secondary_membership_count"), len(secondary))

    def test_segment_profile_contains_generic_axes(self):
        media = self.build_corpus()
        for index, item in enumerate(media):
            item.release_year_min = 1990 + (index % 3) * 10
            item.min_age = 10
            item.is_anime = True
        result = run_segmentation(media, self.base_config())
        profile = result.segments[0].profile
        self.assertIn("dominant_decade", profile)
        self.assertIn("dominant_age_bucket", profile)
        self.assertEqual(profile["dominant_anime"], "anime")

    def test_model_state_version_2(self):
        result = run_segmentation(self.build_corpus(), self.base_config())
        self.assertEqual(result.model_state.version, "2.0")
        self.assertEqual(result.model_state.feature_state.get("version"), "2.0")


class SegmentationRefinementTests(SimpleTestCase):
    def build_corpus(self) -> list[MediaInput]:
        media = []
        for index in range(6):
            extra = "guns" if index % 2 else "cars"
            media.append(make_media(f"a{index}", categories=["action", "war", extra]))
        for index in range(6):
            extra = "tears" if index % 2 else "flowers"
            media.append(make_media(f"b{index}", categories=["romance", "drama", extra]))
        # Fuzzy media unrelated to both clusters
        media.append(make_media("junk0", categories=["zombie", "kraken"]))
        media.append(make_media("junk1", categories=["zombie", "kraken"]))
        return media

    def test_refinement_prunes_low_score_media_and_resegments(self):
        config = SegmentationConfig(
            candidate_cluster_counts=[2],
            min_programmable_score=0.0,
            min_df_count=2,
            allow_multi_segment=False,
            refine_membership_threshold=0.8,
        )
        result = run_segmentation(self.build_corpus(), config)
        refinement = result.diagnostics.get("refinement")
        self.assertIsNotNone(refinement)
        self.assertGreaterEqual(refinement["dropped_count"], 2)
        self.assertIn("junk0", result.weak_clusters)
        self.assertIn("junk1", result.weak_clusters)
        member_ids = {m.media_id for m in result.memberships}
        self.assertNotIn("junk0", member_ids)
        self.assertNotIn("junk1", member_ids)


class ChannelDiscoverySharingTests(SimpleTestCase):
    @staticmethod
    def make_segment(segment_id: str, vector: list[float], categories: list[str]) -> ProgrammableSegment:
        return ProgrammableSegment(
            segment_id=segment_id,
            name=segment_id,
            description="",
            profile={"dominant_categories": categories, "avg_duration_seconds": 1800.0},
            reference_vector=vector,
            reference_profile={},
            observed_profile={},
            programmable_score=0.5,
            cohesion_score=0.5,
            separation_score=0.5,
            format_consistency_score=0.5,
            volume_score=0.5,
            labelability_score=0.5,
            acceptance_threshold=0.5,
            media_ids=["m1", "m2"],
        )

    def chain_segments(self) -> list[ProgrammableSegment]:
        # s1-s2 and s2-s3 are compatible, s1-s3 are not: a chain topology
        return [
            self.make_segment("s1", [1.0, 0.0, 0.0], ["action"]),
            self.make_segment("s2", [0.7, 0.7, 0.0], ["action", "romance"]),
            self.make_segment("s3", [0.0, 1.0, 0.0], ["romance"]),
        ]

    def base_config(self, **kwargs) -> ChannelDiscoveryConfig:
        # Raw cosine scale: the s1-s2 and s2-s3 edges sit at ~0.7, the
        # s1-s3 pair at 0.0.
        return ChannelDiscoveryConfig(
            compatibility_threshold=0.6,
            min_segments_per_channel=1,
            min_channel_score=0.0,
            **kwargs,
        )

    def test_connected_components_yield_single_channel_on_chain(self):
        result = discover_channel_candidates(self.chain_segments(), self.base_config())
        self.assertEqual(len(result.channel_candidates), 1)

    def test_segment_sharing_yields_one_channel_per_anchor(self):
        result = discover_channel_candidates(
            self.chain_segments(),
            self.base_config(allow_segment_sharing=True),
        )
        self.assertEqual(len(result.channel_candidates), 3)
        segment_sets = {frozenset(s.segment_id for s in c.segments) for c in result.channel_candidates}
        self.assertEqual(len(segment_sets), 3)

    def test_segment_sharing_dedupes_identical_neighbourhoods(self):
        # Two quasi identical segments: their anchor neighbourhoods collapse
        segments = [
            self.make_segment("s1", [1.0, 0.0], ["action"]),
            self.make_segment("s2", [1.0, 0.0], ["action"]),
        ]
        result = discover_channel_candidates(
            segments,
            self.base_config(allow_segment_sharing=True),
        )
        self.assertEqual(len(result.channel_candidates), 1)
