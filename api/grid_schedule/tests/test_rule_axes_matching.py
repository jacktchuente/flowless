from datetime import time

from django.test import TestCase

from grid_schedule.services.tv_schedule_matching_service import TvScheduleMatchingService
from grid_schedule.services.tv_schedule_service import TvPlayoutGenerationService
from media_source.models import MediaCollection, MediaContainer, MediaItem, MediaSource
from project_ops.constants import AnalyzeStatus
from tv_channel.models import Catalog, EditorialLine, GridBlock, GridLayout, GridLayoutMode, TvChannel


class RuleAxesFixtureMixin:
    def build_fixtures(self):
        self.catalog = Catalog.objects.create(name="Axes catalog")
        self.tv_channel = TvChannel.objects.create(name="Axes channel", catalog=self.catalog)
        self.editorial_line = EditorialLine.objects.create(tv_channel=self.tv_channel)
        self.grid_layout = GridLayout.objects.create(
            tv_channel=self.tv_channel, is_active=True, mode=GridLayoutMode.FIXED
        )
        self.block = GridBlock.objects.create(
            grid_layout=self.grid_layout,
            starts_at=time(6, 0),
            ends_at=time(12, 0),
        )
        self.media_source = MediaSource.objects.create(name="jellyfin", is_active=True)
        self.collection = MediaCollection.objects.create(
            name="Movies",
            external_id="col-movies",
            media_source=self.media_source,
            is_active=True,
            hash_data="x",
        )

    def create_container(self, external_id, **fields):
        container = MediaContainer.objects.create(
            original_data_hash=f"hash-{external_id}",
            external_id=external_id,
            title=external_id,
            media_source=self.media_source,
            media_collection=self.collection,
            analyze_status=AnalyzeStatus.COMPLETE,
            **fields,
        )
        MediaItem.objects.create(
            original_data_hash=f"hash-item-{external_id}",
            container=container,
            title=f"{external_id} item",
            duration_seconds=1800,
            media_source=self.media_source,
            external_id=f"item-{external_id}",
        )
        return container


class MatchingServiceRuleAxesTests(RuleAxesFixtureMixin, TestCase):

    def setUp(self):
        self.build_fixtures()
        self.hanks_movie = self.create_container(
            "hanks-movie",
            actors=["Tom Hanks"],
            studios=["Warner Bros."],
            audio_languages=["fre"],
        )
        self.other_movie = self.create_container(
            "other-movie",
            actors=["Someone Else"],
            studios=["Indie"],
            audio_languages=["eng"],
        )

    def stats(self):
        service = TvScheduleMatchingService(tv_channel=self.tv_channel)
        return service.get_block_match_stats(self.block)

    def test_allowed_on_new_axis_filters_containers(self):
        self.block.allowed = {"actors": ["Tom Hanks"]}
        self.block.save()
        self.assertEqual(self.stats()["matching_media_container_count"], 1)

    def test_forbidden_on_new_axis_excludes_container(self):
        self.editorial_line.forbidden = {"studios": ["Warner Bros."]}
        self.editorial_line.save()
        self.assertEqual(self.stats()["matching_media_container_count"], 1)

    def test_editorial_line_allowed_combines_with_block(self):
        self.editorial_line.allowed = {"audio_languages": ["fre"]}
        self.editorial_line.save()
        self.block.allowed = {"actors": ["Someone Else"]}
        self.block.save()
        # Ligne edito exige fre (hanks-movie), block exige Someone Else
        # (other-movie) : aucun container ne satisfait les deux.
        self.assertEqual(self.stats()["matching_media_container_count"], 0)

    def test_empty_rules_match_everything(self):
        self.assertEqual(self.stats()["matching_media_container_count"], 2)


class GenerationServiceRuleAxesTests(RuleAxesFixtureMixin, TestCase):

    def setUp(self):
        self.build_fixtures()
        self.container = self.create_container(
            "hanks-movie",
            actors=["Tom Hanks"],
            directors=["Tom Hooper"],
            countries=["France"],
        )
        self.service = TvPlayoutGenerationService(tv_channel=self.tv_channel, days=1)

    def test_strict_filters_respect_new_axes(self):
        self.block.forbidden = {"countries": ["France"]}
        self.assertFalse(
            self.service._passes_strict_filters(self.tv_channel, self.block, self.container)
        )
        self.block.forbidden = {}
        self.block.allowed = {"actors": ["Tom Hanks"]}
        self.assertTrue(
            self.service._passes_strict_filters(self.tv_channel, self.block, self.container)
        )

    def test_preferred_new_axes_add_score_bonus(self):
        history = {"container_counts": {}, "last_block_id_by_container": {}}

        self.block.preferred = {}
        baseline = self.service._score_container(
            tv_channel=self.tv_channel, block=self.block, container=self.container, history=history
        )

        self.block.preferred = {"actors": ["Tom Hanks"], "directors": ["Tom Hooper"]}
        boosted = self.service._score_container(
            tv_channel=self.tv_channel, block=self.block, container=self.container, history=history
        )

        self.assertEqual(boosted.score - baseline.score, 2.0)
        self.assertEqual(boosted.reasons["preferred_actors"], 1.0)
        self.assertEqual(boosted.reasons["preferred_directors"], 1.0)
        self.assertEqual(boosted.reasons["preferred_countries"], 0.0)
