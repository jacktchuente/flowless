from datetime import datetime
from unittest.mock import patch

from django.utils import timezone
from rest_framework.test import APITestCase

from grid_schedule.models import ScheduleMediaItem
from grid_schedule.services.tv_schedule_matching_service import TvScheduleMatchingService
from grid_schedule.services.tv_schedule_service import TvPlayoutGenerationService
from grid_schedule.tests.test_post_roll_filler_service import PostRollFillerFixtureMixin


class NumericSchedulingIntegrationTests(PostRollFillerFixtureMixin, APITestCase):
    def setUp(self):
        self.build_fixtures()
        self.block.post_filler_policy = None
        self.block.save(update_fields=["post_filler_policy"])

        self.matching_container = self._create_container(self.main_collection, "matching")
        self.matching_container.min_age = 12
        self.matching_container.release_year_min = 2015
        self.matching_container.release_year_max = 2020
        self.matching_container.overall_rating_score = 8.0
        self.matching_container.save(update_fields=[
            "min_age",
            "release_year_min",
            "release_year_max",
            "overall_rating_score",
        ])
        self._create_item(self.matching_container, "matching-item", duration_seconds=3600)

        self.young_container = self._create_container(self.main_collection, "young")
        self.young_container.min_age = 7
        self.young_container.release_year_min = 2015
        self.young_container.release_year_max = 2015
        self.young_container.overall_rating_score = 9.0
        self.young_container.save(update_fields=[
            "min_age",
            "release_year_min",
            "release_year_max",
            "overall_rating_score",
        ])
        self._create_item(self.young_container, "young-item", duration_seconds=3600)

    def test_saved_numeric_rules_drive_schedule_generation(self):
        response = self.client.put(
            f"/api/tv-channel/{self.tv_channel.id}/editorial-line/",
            {
                "start_at": "06:00",
                "end_at": "22:00",
                "allow_filler": False,
                "allowed": {
                    "comparisons": [
                        {"field": "min_age", "operator": "gt", "value": 10},
                        {"field": "release_year", "operator": "gte", "value": 2010},
                        {"field": "star_rating", "operator": "gte", "value": 4},
                    ],
                },
                "preferred": {},
                "forbidden": {},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data["allowed"]["comparisons"]), 3)
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
