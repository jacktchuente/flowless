from datetime import datetime, time, timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from grid_schedule.models import (
    BlockContainerSelection,
    FlexiblePlayoutSelection,
    ScheduleMediaItem,
    TvPlayout,
)
from grid_schedule.services.etv_scheduler_service import ETVSchedulerService
from grid_schedule.services.post_roll_filler_service import PostRollFillerService
from grid_schedule.services.tv_schedule_service import TvPlayoutGenerationService
from media_source.constants import MediaProgrammingRole
from media_source.models import MediaCollection, MediaContainer, MediaItem, MediaSource
from project_ops.constants import AnalyzeStatus
from tv_channel.models import (
    Catalog,
    EditorialLine,
    FillerPolicy,
    GridBlock,
    GridLayout,
    GridLayoutMode,
    TvChannel,
)


class PostRollFillerFixtureMixin:
    def build_fixtures(self, *, grid_mode=GridLayoutMode.FIXED):
        self.catalog = Catalog.objects.create(name="Test catalog")
        self.tv_channel = TvChannel.objects.create(name="Test channel", catalog=self.catalog)
        self.editorial_line = EditorialLine.objects.create(
            tv_channel=self.tv_channel,
            start_at=time(6, 0),
            end_at=time(22, 0),
            allow_filler=True,
        )
        self.filler_policy = FillerPolicy.objects.create(name="post-roll", duration_seconds=180)
        self.grid_layout = GridLayout.objects.create(
            tv_channel=self.tv_channel,
            is_active=True,
            mode=grid_mode,
            post_filler_policy=self.filler_policy if grid_mode == GridLayoutMode.FLEXIBLE else None,
        )
        self.block = GridBlock.objects.create(
            grid_layout=self.grid_layout,
            starts_at=time(6, 0),
            ends_at=time(12, 0),
            min_items=1,
            max_items=4,
            post_filler_policy=self.filler_policy,
        )
        self.tv_playout = TvPlayout.objects.create(
            tv_channel=self.tv_channel,
            is_active=True,
            grid=self.grid_layout,
        )

        self.media_source = MediaSource.objects.create(name="jellyfin", is_active=True)
        self.main_collection = self._create_collection("Movies", role=None)
        self.window_start = timezone.make_aware(datetime(2026, 1, 1, 6, 0))
        self.window_end = self.window_start + timedelta(days=1)

    def _create_collection(self, name, *, role):
        return MediaCollection.objects.create(
            name=name[:20],
            external_id=f"col-{name}",
            media_source=self.media_source,
            is_active=True,
            programming_role=role,
            hash_data="x",
        )

    def _create_container(self, collection, external_id, *, title=None, provider_ids=None):
        return MediaContainer.objects.create(
            original_data_hash=f"hash-{external_id}",
            external_id=external_id,
            title=title or external_id,
            provider_ids=provider_ids or {},
            media_source=self.media_source,
            media_collection=collection,
            analyze_status=AnalyzeStatus.COMPLETE,
        )

    def _create_item(self, container, external_id, *, duration_seconds=3000):
        return MediaItem.objects.create(
            original_data_hash=f"hash-{external_id}",
            container=container,
            title=f"item {external_id}",
            duration_seconds=duration_seconds,
            media_source=self.media_source,
            external_id=external_id,
        )

    def _next_selection_order(self):
        self._selection_order = getattr(self, "_selection_order", -1) + 1
        return self._selection_order

    def _create_selection(self, container):
        return BlockContainerSelection.objects.create(
            media_container=container,
            block=self.block,
            tv_playout=self.tv_playout,
            order=self._next_selection_order(),
        )

    def _create_main_scheduled_item(self, container, item, *, starts_at, filler_seconds=180):
        selection = self._create_selection(container)
        ends_at = starts_at + timedelta(seconds=item.duration_seconds)
        return ScheduleMediaItem.objects.create(
            starts_at=starts_at,
            ends_at=ends_at,
            post_roll_filler_ends_at=ends_at + timedelta(seconds=filler_seconds),
            item=item,
            block_container_selection=selection,
        )

    def _fill(self):
        return PostRollFillerService(
            tv_playout=self.tv_playout,
            window_start=self.window_start,
            window_end=self.window_end,
        ).fill()


class PostRollFillerServiceTests(PostRollFillerFixtureMixin, TestCase):
    def setUp(self):
        self.build_fixtures()

    def test_trailer_of_upcoming_program_fills_window(self):
        container_a = self._create_container(self.main_collection, "main-a")
        container_b = self._create_container(
            self.main_collection, "main-b", provider_ids={"tmdb": "603"}
        )
        item_a = self._create_item(container_a, "item-a")
        item_b = self._create_item(container_b, "item-b")
        main_a = self._create_main_scheduled_item(container_a, item_a, starts_at=self.window_start)
        self._create_main_scheduled_item(
            container_b, item_b, starts_at=main_a.post_roll_filler_ends_at
        )

        trailer_collection = self._create_collection("Trailers", role=MediaProgrammingRole.TRAILER)
        trailer_folder = self._create_container(trailer_collection, "trailer-folder", title="tmdb-603")
        trailer_item = self._create_item(trailer_folder, "trailer-1", duration_seconds=60)

        result = self._fill()

        children = list(ScheduleMediaItem.objects.filter(parent_schedule_item=main_a))
        self.assertEqual(len(children), 1)
        child = children[0]
        self.assertEqual(child.role, MediaProgrammingRole.TRAILER)
        self.assertEqual(child.item_id, trailer_item.id)
        self.assertEqual(child.starts_at, main_a.ends_at)
        self.assertLessEqual(child.ends_at, main_a.post_roll_filler_ends_at)
        self.assertIsNone(child.block_container_selection_id)
        self.assertIsNone(child.flexible_selection_id)
        self.assertGreaterEqual(result.created_items, 1)

    def test_filler_fallback_when_no_trailer_matches(self):
        container_a = self._create_container(self.main_collection, "main-a")
        item_a = self._create_item(container_a, "item-a")
        main_a = self._create_main_scheduled_item(container_a, item_a, starts_at=self.window_start)

        filler_collection = self._create_collection("Fillers", role=MediaProgrammingRole.FILLER)
        filler_container = self._create_container(filler_collection, "filler-folder")
        for index in range(4):
            self._create_item(filler_container, f"filler-{index}", duration_seconds=60)

        result = self._fill()

        children = list(
            ScheduleMediaItem.objects.filter(parent_schedule_item=main_a).order_by("starts_at")
        )
        self.assertEqual(len(children), 3)  # 3 x 60s dans la fenetre de 180s
        for child in children:
            self.assertEqual(child.role, MediaProgrammingRole.FILLER)
            self.assertGreaterEqual(child.starts_at, main_a.ends_at)
            self.assertLessEqual(child.ends_at, main_a.post_roll_filler_ends_at)
        self.assertTrue(any("no-trailer-for-upcoming" in warning for warning in result.warnings))

    def test_warnings_when_no_interstitial_content_exists(self):
        container_a = self._create_container(self.main_collection, "main-a")
        item_a = self._create_item(container_a, "item-a")
        self._create_main_scheduled_item(container_a, item_a, starts_at=self.window_start)

        result = self._fill()

        self.assertEqual(result.created_items, 0)
        self.assertTrue(any("no-trailer-for-upcoming" in warning for warning in result.warnings))
        self.assertTrue(any("no-filler-available" in warning for warning in result.warnings))

    def test_fill_is_idempotent_on_windows_already_filled(self):
        container_a = self._create_container(self.main_collection, "main-a")
        item_a = self._create_item(container_a, "item-a")
        self._create_main_scheduled_item(container_a, item_a, starts_at=self.window_start)

        filler_collection = self._create_collection("Fillers", role=MediaProgrammingRole.FILLER)
        filler_container = self._create_container(filler_collection, "filler-folder")
        self._create_item(filler_container, "filler-0", duration_seconds=180)

        first = self._fill()
        second = self._fill()

        self.assertEqual(first.created_items, 1)
        self.assertEqual(second.created_items, 0)

    def test_allowed_roles_restricts_the_pool(self):
        self.filler_policy.allowed_roles = ["bumper"]
        self.filler_policy.save(update_fields=["allowed_roles"])

        container_a = self._create_container(self.main_collection, "main-a")
        item_a = self._create_item(container_a, "item-a")
        main_a = self._create_main_scheduled_item(container_a, item_a, starts_at=self.window_start)

        filler_collection = self._create_collection("Fillers", role=MediaProgrammingRole.FILLER)
        filler_container = self._create_container(filler_collection, "filler-folder")
        self._create_item(filler_container, "filler-0", duration_seconds=60)
        bumper_collection = self._create_collection("Bumpers", role=MediaProgrammingRole.BUMPER)
        bumper_container = self._create_container(bumper_collection, "bumper-folder")
        bumper_item = self._create_item(bumper_container, "bumper-0", duration_seconds=60)

        self._fill()

        children = list(ScheduleMediaItem.objects.filter(parent_schedule_item=main_a))
        self.assertTrue(children)
        for child in children:
            self.assertEqual(child.role, MediaProgrammingRole.BUMPER)
            self.assertEqual(child.item_id, bumper_item.id)


class FlexiblePostRollFillerTests(PostRollFillerFixtureMixin, TestCase):
    def setUp(self):
        self.build_fixtures(grid_mode=GridLayoutMode.FLEXIBLE)

    def test_flexible_items_use_grid_level_policy(self):
        container_a = self._create_container(self.main_collection, "main-a")
        item_a = self._create_item(container_a, "item-a")
        selection = FlexiblePlayoutSelection.objects.create(
            tv_playout=self.tv_playout,
            path_position=0,
            media_container=container_a,
        )
        ends_at = self.window_start + timedelta(seconds=item_a.duration_seconds)
        main_a = ScheduleMediaItem.objects.create(
            starts_at=self.window_start,
            ends_at=ends_at,
            post_roll_filler_ends_at=ends_at + timedelta(seconds=180),
            item=item_a,
            flexible_selection=selection,
        )

        filler_collection = self._create_collection("Fillers", role=MediaProgrammingRole.FILLER)
        filler_container = self._create_container(filler_collection, "filler-folder")
        self._create_item(filler_container, "filler-0", duration_seconds=120)

        result = self._fill()

        children = list(ScheduleMediaItem.objects.filter(parent_schedule_item=main_a))
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0].role, MediaProgrammingRole.FILLER)
        self.assertEqual(result.created_items, 1)


class ScheduleMediaItemConstraintTests(PostRollFillerFixtureMixin, TestCase):
    def setUp(self):
        self.build_fixtures()
        self.container = self._create_container(self.main_collection, "main-a")
        self.item = self._create_item(self.container, "item-a")
        self.main = self._create_main_scheduled_item(
            self.container, self.item, starts_at=self.window_start
        )

    def test_non_main_item_with_selection_is_rejected(self):
        selection = self._create_selection(self.container)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ScheduleMediaItem.objects.create(
                starts_at=self.main.ends_at,
                ends_at=self.main.ends_at + timedelta(seconds=60),
                item=self.item,
                role=MediaProgrammingRole.FILLER,
                parent_schedule_item=self.main,
                block_container_selection=selection,
            )

    def test_non_main_item_without_parent_is_rejected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ScheduleMediaItem.objects.create(
                starts_at=self.main.ends_at,
                ends_at=self.main.ends_at + timedelta(seconds=60),
                item=self.item,
                role=MediaProgrammingRole.FILLER,
            )

    def test_main_item_with_parent_is_rejected(self):
        selection = self._create_selection(self.container)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ScheduleMediaItem.objects.create(
                starts_at=self.main.ends_at,
                ends_at=self.main.ends_at + timedelta(seconds=60),
                item=self.item,
                role=MediaProgrammingRole.MAIN,
                parent_schedule_item=self.main,
                block_container_selection=selection,
            )


class StandardGenerationInterstitialTests(PostRollFillerFixtureMixin, TestCase):
    def setUp(self):
        self.build_fixtures()

    def test_generation_excludes_interstitial_collections_and_fills_post_roll(self):
        container_a = self._create_container(self.main_collection, "main-a")
        container_b = self._create_container(self.main_collection, "main-b")
        for index in range(3):
            self._create_item(container_a, f"item-a-{index}", duration_seconds=3000)
            self._create_item(container_b, f"item-b-{index}", duration_seconds=3000)

        filler_collection = self._create_collection("Fillers", role=MediaProgrammingRole.FILLER)
        filler_container = self._create_container(filler_collection, "filler-folder")
        for index in range(4):
            self._create_item(filler_container, f"filler-{index}", duration_seconds=60)

        result = TvPlayoutGenerationService(
            tv_channel=self.tv_channel,
            days=1,
            reset=True,
        ).generate()

        main_items = ScheduleMediaItem.objects.filter(
            block_container_selection__tv_playout=result.tv_playout,
        )
        self.assertGreater(main_items.count(), 0)
        for scheduled in main_items.select_related("item__container__media_collection"):
            self.assertIsNone(scheduled.item.container.media_collection.programming_role)

        children = ScheduleMediaItem.objects.filter(
            parent_schedule_item__block_container_selection__tv_playout=result.tv_playout,
        )
        self.assertEqual(children.count(), result.filled_items)
        self.assertGreater(result.filled_items, 0)
        for child in children.select_related("parent_schedule_item"):
            self.assertNotEqual(child.role, MediaProgrammingRole.MAIN)
            self.assertGreaterEqual(child.starts_at, child.parent_schedule_item.ends_at)
            self.assertLessEqual(
                child.ends_at, child.parent_schedule_item.post_roll_filler_ends_at
            )


class EtvSchedulerQueryTests(TestCase):
    def test_interstitial_query_targets_the_exact_episode(self):
        query = ETVSchedulerService._get_query(
            {
                "media_container_kind": None,
                "media_container_title": "tmdb-603",
                "media_item_title": "Trailer 1",
                "role": MediaProgrammingRole.TRAILER,
            }
        )
        self.assertEqual(
            query,
            'show_title:"tmdb-603" AND type:episode AND title:"Trailer 1"',
        )

    def test_main_item_query_is_unchanged(self):
        query = ETVSchedulerService._get_query(
            {
                "media_container_kind": None,
                "media_container_title": "Some Show",
                "media_item_title": "Episode 1",
                "role": MediaProgrammingRole.MAIN,
            }
        )
        self.assertEqual(query, 'title:"Some Show"')
