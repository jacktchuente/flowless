from datetime import datetime
from unittest.mock import patch

from django.utils import timezone
from rest_framework.test import APITestCase

from grid_schedule.models import ScheduleMediaItem
from grid_schedule.services.tv_schedule_matching_service import TvScheduleMatchingService
from grid_schedule.services.tv_schedule_service import TvPlayoutGenerationService
from grid_schedule.tests.test_post_roll_filler_service import PostRollFillerFixtureMixin
from rule_engine.models import VocabularyEntry


class GenreTagSchedulingIntegrationTests(PostRollFillerFixtureMixin, APITestCase):
    def setUp(self):
        self.build_fixtures()
        self.block.post_filler_policy = None
        self.block.save(update_fields=["post_filler_policy"])
        VocabularyEntry.objects.bulk_create([
            VocabularyEntry(axis="genres", value="Horror"),
            VocabularyEntry(axis="tags", value="Late night"),
        ])

        self.matching_container = self._create_container(
            self.main_collection,
            "matching",
        )
        self.matching_container.categories = ["Horror"]
        self.matching_container.genres = ["hORRoR"]
        self.matching_container.tags = ["Late night"]
        self.matching_container.save(update_fields=["categories", "genres", "tags"])
        self._create_item(self.matching_container, "matching-item", duration_seconds=3600)

        self.category_only_container = self._create_container(
            self.main_collection,
            "category-only",
        )
        self.category_only_container.categories = ["Horror"]
        self.category_only_container.genres = ["Drama"]
        self.category_only_container.tags = ["Late night"]
        self.category_only_container.save(update_fields=["categories", "genres", "tags"])
        self._create_item(self.category_only_container, "category-item", duration_seconds=3600)

    def test_saved_genre_and_tag_rules_drive_schedule_generation(self):
        response = self.client.put(
            f"/api/tv-channel/{self.tv_channel.id}/editorial-line/",
            {
                "start_at": "06:00",
                "end_at": "22:00",
                "allow_filler": False,
                "allowed": {
                    "genres": ["  horror "],
                    "tags": ["late NIGHT"],
                },
                "preferred": {},
                "forbidden": {},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["allowed"]["genres"], ["Horror"])
        self.assertEqual(response.data["allowed"]["tags"], ["Late night"])
        self.tv_channel.refresh_from_db()
        self.assertEqual(
            TvScheduleMatchingService(tv_channel=self.tv_channel)
            .get_block_match_stats(self.block)["matching_media_container_count"],
            1,
        )

        now = timezone.make_aware(datetime(2026, 1, 1, 6, 0))
        with patch("grid_schedule.services.tv_schedule_service.timezone.now", return_value=now):
            result = TvPlayoutGenerationService(
                tv_channel=self.tv_channel,
                days=1,
                reset=True,
            ).generate()

        scheduled_container_ids = set(
            ScheduleMediaItem.objects
            .filter(block_container_selection__tv_playout=result.tv_playout)
            .values_list("item__container_id", flat=True)
        )
        self.assertEqual(scheduled_container_ids, {self.matching_container.id})
