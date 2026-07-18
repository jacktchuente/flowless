from datetime import datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from grid_schedule.models import FlexiblePlayoutSelection, PlayoutGenerationReport, ScheduleMediaItem, TvPlayout
from grid_schedule.services.marathon_tv_schedule_service import MarathonPlayoutGenerationService
from media_source.constants import MediaContainerKind
from media_source.models import MediaCollection, MediaContainer, MediaItem, MediaSource
from project_ops.constants import AnalyzeStatus
from tv_channel.models import (
    Catalog,
    EditorialLine,
    GridLayout,
    GridLayoutMode,
    MarathonConfig,
    MarathonKindPolicy,
    TvChannel,
)
from tv_channel.tasks import generate_tv_channel_playout

NOW_PATCH = "grid_schedule.services.base_playout_generation_service.timezone.now"


class MarathonFixtureMixin:
    def build_fixtures(self):
        self.catalog = Catalog.objects.create(name="Marathon catalog")
        self.tv_channel = TvChannel.objects.create(name="Marathon channel", catalog=self.catalog)
        self.editorial_line = EditorialLine.objects.create(
            tv_channel=self.tv_channel,
            start_at=time(6, 0),
            end_at=time(22, 0),
            allow_filler=False,
        )
        self.grid_layout = GridLayout.objects.create(
            tv_channel=self.tv_channel,
            is_active=True,
            mode=GridLayoutMode.MARATHON,
        )
        self.config = MarathonConfig.objects.create(grid_layout=self.grid_layout)
        self.media_source = MediaSource.objects.create(name="jellyfin", is_active=True)
        self.now = timezone.make_aware(datetime(2026, 1, 1, 8, 0))

    def _add_policy(self, kind, *, min_run=1, max_run=1, quota=1):
        return MarathonKindPolicy.objects.create(
            config=self.config,
            container_kind=kind,
            min_run=min_run,
            max_run=max_run,
            quota=quota,
        )

    def _create_collection(self, name, *, kind):
        return MediaCollection.objects.create(
            name=name[:20],
            external_id=f"col-{name}",
            media_source=self.media_source,
            is_active=True,
            container_kind=kind,
            hash_data="x",
        )

    def _create_container(self, collection, external_id):
        return MediaContainer.objects.create(
            original_data_hash=f"hash-{external_id}",
            external_id=external_id,
            title=external_id,
            provider_ids={},
            media_source=self.media_source,
            media_collection=collection,
            analyze_status=AnalyzeStatus.COMPLETE,
        )

    def _create_episode(self, container, external_id, *, episode_number, duration_seconds):
        return MediaItem.objects.create(
            original_data_hash=f"hash-{external_id}",
            container=container,
            title=f"item {external_id}",
            duration_seconds=duration_seconds,
            season_number=1,
            episode_number=episode_number,
            media_source=self.media_source,
            external_id=external_id,
        )

    def _create_video(self, container, external_id, *, duration_seconds):
        return MediaItem.objects.create(
            original_data_hash=f"hash-{external_id}",
            container=container,
            title=f"item {external_id}",
            duration_seconds=duration_seconds,
            media_source=self.media_source,
            external_id=external_id,
        )

    def _create_series(self, name, *, episodes, duration_seconds=1800):
        collection = self._create_collection(name, kind=MediaContainerKind.SERIES)
        container = self._create_container(collection, name)
        items = [
            self._create_episode(
                container,
                f"{name}-e{index}",
                episode_number=index,
                duration_seconds=duration_seconds,
            )
            for index in range(1, episodes + 1)
        ]
        return container, items

    def _create_movie(self, name, *, duration_seconds=3600):
        collection = self._create_collection(name, kind=MediaContainerKind.STANDALONE_VIDEO)
        container = self._create_container(collection, name)
        item = self._create_video(container, f"{name}-video", duration_seconds=duration_seconds)
        return container, item

    def _generate(self, *, days=1, reset=True, extend=False, now=None):
        with patch(NOW_PATCH, return_value=now or self.now):
            return MarathonPlayoutGenerationService(
                tv_channel=self.tv_channel,
                days=days,
                reset=reset,
                extend=extend,
            ).generate()

    def _main_items(self):
        return list(
            ScheduleMediaItem.objects
            .filter(flexible_selection__tv_playout__tv_channel=self.tv_channel)
            .select_related("item", "item__container", "flexible_selection")
            .order_by("starts_at", "id")
        )

    def _selections(self):
        return list(
            FlexiblePlayoutSelection.objects
            .filter(tv_playout__tv_channel=self.tv_channel)
            .select_related("media_container")
            .order_by("order")
        )


class MarathonRotationTests(MarathonFixtureMixin, TestCase):
    def setUp(self):
        self.build_fixtures()

    def test_rotation_alternates_series_runs_and_films(self):
        self._add_policy(MediaContainerKind.SERIES, min_run=2, max_run=2, quota=1)
        self._add_policy(MediaContainerKind.STANDALONE_VIDEO, min_run=1, max_run=1, quota=1)
        self._create_series("serie-a", episodes=4, duration_seconds=1800)
        self._create_movie("film-b", duration_seconds=3600)

        result = self._generate(days=1)

        items = self._main_items()
        # 16h window, cycle film(1h) + 2 episodes(2x30min) = 2h -> 8 full cycles
        self.assertEqual(result.generated_items, 24)
        titles = [scheduled.item.title for scheduled in items[:9]]
        self.assertEqual(
            titles,
            [
                "item film-b-video",
                "item serie-a-e1",
                "item serie-a-e2",
                "item film-b-video",
                "item serie-a-e3",
                "item serie-a-e4",
                "item film-b-video",
                # Episodes reboucles a S01E01 une fois la serie epuisee.
                "item serie-a-e1",
                "item serie-a-e2",
            ],
        )
        for scheduled, following in zip(items, items[1:]):
            self.assertEqual(scheduled.ends_at, following.starts_at)

        selections = self._selections()
        self.assertEqual(
            [selection.planned_item_count for selection in selections[:4]],
            [1, 2, 1, 2],
        )

    def test_lru_never_repeats_a_container_before_pool_exhaustion(self):
        self._add_policy(MediaContainerKind.SERIES, min_run=1, max_run=2, quota=1)
        self._create_series("serie-a", episodes=2)
        self._create_series("serie-b", episodes=2)
        self._create_series("serie-c", episodes=2)

        self._generate(days=1)

        run_containers = [selection.media_container.title for selection in self._selections()]
        self.assertGreaterEqual(len(run_containers), 6)
        self.assertEqual(run_containers[:3], ["serie-a", "serie-b", "serie-c"])
        for index in range(1, len(run_containers)):
            self.assertNotEqual(run_containers[index], run_containers[index - 1])

    def test_kind_quota_weights_run_frequency(self):
        self._add_policy(MediaContainerKind.SERIES, min_run=1, max_run=1, quota=2)
        self._add_policy(MediaContainerKind.STANDALONE_VIDEO, min_run=1, max_run=1, quota=1)
        self._create_series("serie-a", episodes=20, duration_seconds=600)
        self._create_movie("film-b", duration_seconds=600)

        self._generate(days=1)

        run_kinds = [
            selection.media_container.media_collection.container_kind
            for selection in self._selections()
        ]
        series, film = MediaContainerKind.SERIES, MediaContainerKind.STANDALONE_VIDEO
        self.assertEqual(run_kinds[:8], [series, film, series, series, film, series, series, film])

    def test_kind_without_policy_or_zeroed_is_excluded(self):
        self._add_policy(MediaContainerKind.SERIES, min_run=2, max_run=2, quota=1)
        self._add_policy(MediaContainerKind.STANDALONE_VIDEO, min_run=1, max_run=0, quota=1)
        self._create_series("serie-a", episodes=4)
        self._create_movie("film-b")
        clip_collection = self._create_collection("clips", kind=MediaContainerKind.MUSIC_VIDEO_RELEASE)
        clip_container = self._create_container(clip_collection, "clip-c")
        self._create_video(clip_container, "clip-c-video", duration_seconds=240)

        self._generate(days=1)

        scheduled_kinds = {
            scheduled.item.container.media_collection.container_kind
            for scheduled in self._main_items()
        }
        self.assertEqual(scheduled_kinds, {MediaContainerKind.SERIES})

    def test_min_run_skips_containers_with_too_few_items(self):
        self._add_policy(MediaContainerKind.SERIES, min_run=2, max_run=2, quota=1)
        self._create_series("serie-thin", episodes=1)
        self._create_series("serie-fat", episodes=4)

        self._generate(days=1)

        run_containers = {selection.media_container.title for selection in self._selections()}
        self.assertEqual(run_containers, {"serie-fat"})

    def test_started_run_resumes_next_morning_instead_of_truncating(self):
        self._add_policy(MediaContainerKind.SERIES, min_run=2, max_run=2, quota=1)
        self._create_series("serie-a", episodes=2, duration_seconds=5400)

        self._generate(days=2)

        selections = self._selections()
        # Runs de 3h depuis 06:00 -> le 6e run demarre a 21:00.
        boundary_run = selections[5]
        run_items = list(
            ScheduleMediaItem.objects.filter(flexible_selection=boundary_run).order_by("starts_at")
        )
        self.assertEqual(boundary_run.planned_item_count, 2)
        self.assertEqual(len(run_items), 2)
        self.assertEqual(run_items[0].starts_at, timezone.make_aware(datetime(2026, 1, 1, 21, 0)))
        self.assertEqual(run_items[1].starts_at, timezone.make_aware(datetime(2026, 1, 2, 6, 0)))

    def test_extend_continues_the_rotation_after_last_item(self):
        self._add_policy(MediaContainerKind.SERIES, min_run=2, max_run=2, quota=1)
        self._add_policy(MediaContainerKind.STANDALONE_VIDEO, min_run=1, max_run=1, quota=1)
        self._create_series("serie-a", episodes=4, duration_seconds=1800)
        self._create_movie("film-b", duration_seconds=3600)

        self._generate(days=1)
        first_pass_items = self._main_items()
        last_end = first_pass_items[-1].ends_at

        extend_now = self.now + timedelta(hours=4)
        result = self._generate(days=1, reset=False, extend=True, now=extend_now)

        self.assertGreater(result.generated_items, 0)
        new_items = [item for item in self._main_items() if item.starts_at >= last_end]
        self.assertEqual(new_items[0].starts_at, timezone.make_aware(datetime(2026, 1, 2, 6, 0)))
        # La rotation repart des compteurs du playout: le cycle suivant
        # recommence par un film comme les precedents.
        self.assertEqual(new_items[0].item.title, "item film-b-video")
        items = self._main_items()
        for scheduled, following in zip(items, items[1:]):
            self.assertGreaterEqual(following.starts_at, scheduled.ends_at)

    def test_generate_requires_marathon_config(self):
        self.config.delete()
        with self.assertRaises(ValidationError):
            self._generate(days=1)

    def test_generate_requires_at_least_one_enabled_kind(self):
        self._add_policy(MediaContainerKind.SERIES, min_run=1, max_run=0, quota=1)
        with self.assertRaises(ValidationError):
            self._generate(days=1)


class MarathonTaskDispatchTests(MarathonFixtureMixin, TestCase):
    def setUp(self):
        self.build_fixtures()

    @patch("tv_channel.tasks.save_status_and_broadcast")
    @patch("tv_channel.tasks.MarathonPlayoutGenerationService")
    def test_task_dispatches_marathon_grid_to_marathon_service(self, service_mock, _broadcast_mock):
        tv_playout = TvPlayout.objects.create(tv_channel=self.tv_channel, is_active=True, grid=self.grid_layout)
        service_mock.return_value.generate.return_value = SimpleNamespace(
            tv_playout=tv_playout,
            created=True,
            generated_items=3,
            warnings=[],
            issues=[],
            filled_items=0,
            repaired_gaps=0,
            trimmed_overlaps=0,
            window_start=self.now,
            window_end=self.now + timedelta(days=1),
        )

        generate_tv_channel_playout(self.tv_channel.id, days=1, reset=False)

        service_mock.assert_called_once_with(
            tv_channel=self.tv_channel,
            days=1,
            reset=False,
            extend=False,
        )
        report = PlayoutGenerationReport.objects.get(tv_playout=tv_playout)
        self.assertEqual(report.generated_items, 3)
