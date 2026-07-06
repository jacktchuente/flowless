from django.test import TestCase

from grid_schedule.models import ScheduleMediaItem
from grid_schedule.services.etv_scheduler_service import ETVSchedulerService
from grid_schedule.services.tv_schedule_service import TvPlayoutGenerationService
from media_source.constants import MediaContainerKind, MediaProgrammingRole
from media_source.models import MediaItem
from grid_schedule.tests.test_post_roll_filler_service import PostRollFillerFixtureMixin


class EtvMusicQueryTests(TestCase):
    def test_music_video_query_targets_the_clip(self):
        query = ETVSchedulerService._get_query(
            {
                "media_container_kind": MediaContainerKind.MUSIC_VIDEO_RELEASE,
                "media_container_title": "Artist - Song",
                "media_item_title": "Artist - Song",
                "role": MediaProgrammingRole.MAIN,
            }
        )
        self.assertEqual(query, 'title:"Artist - Song" AND type:music_video')

    def test_music_release_query_targets_the_song(self):
        query = ETVSchedulerService._get_query(
            {
                "media_container_kind": MediaContainerKind.MUSIC_RELEASE,
                "media_container_title": "Some Album",
                "media_item_title": "Track 2",
                "role": MediaProgrammingRole.MAIN,
            }
        )
        self.assertEqual(query, 'title:"Track 2" AND type:song')


class MusicBlockGenerationTests(PostRollFillerFixtureMixin, TestCase):
    def setUp(self):
        self.build_fixtures()
        # Bloc de clips type MTV: uniquement des music_video_release, items courts.
        self.block.min_items = 5
        self.block.max_items = 20
        self.block.min_duration_seconds_per_item = 60
        self.block.max_duration_seconds_per_item = 600
        self.block.allowed_container_kinds = [MediaContainerKind.MUSIC_VIDEO_RELEASE]
        self.block.save()

        self.clip_collection = self._create_collection("Clips", role=None)
        self.clip_collection.container_kind = MediaContainerKind.MUSIC_VIDEO_RELEASE
        self.clip_collection.save(update_fields=["container_kind"])

        self.series_collection = self._create_collection("Shows", role=None)
        self.series_collection.container_kind = MediaContainerKind.SERIES
        self.series_collection.save(update_fields=["container_kind"])

    def _create_clip(self, index):
        container = self._create_container(self.clip_collection, f"clip-{index}")
        container.duration_min_seconds = 240
        container.duration_max_seconds = 240
        container.total_duration_seconds = 240
        container.item_count = 1
        container.save()
        self._create_item(container, f"clip-item-{index}", duration_seconds=240)
        return container

    def test_music_block_chains_clips_and_excludes_series(self):
        for index in range(20):
            self._create_clip(index)
        series_container = self._create_container(self.series_collection, "series-1")
        self._create_item(series_container, "episode-1", duration_seconds=240)

        result = TvPlayoutGenerationService(
            tv_channel=self.tv_channel,
            days=1,
            reset=True,
        ).generate()

        scheduled = (
            ScheduleMediaItem.objects
            .filter(block_container_selection__tv_playout=result.tv_playout)
            .select_related("item__container__media_collection")
        )
        self.assertGreaterEqual(scheduled.count(), 5)
        for entry in scheduled:
            collection = entry.item.container.media_collection
            self.assertEqual(collection.container_kind, MediaContainerKind.MUSIC_VIDEO_RELEASE)
            duration = (entry.ends_at - entry.starts_at).total_seconds()
            self.assertGreaterEqual(duration, 60)
            self.assertLessEqual(duration, 600)
