from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from grid_schedule.models import (
    BlockContainerSelection,
    PlayoutGenerationReport,
    ScheduleMediaItem,
    TvPlayout,
)
from media_source.models import MediaCollection, MediaContainer, MediaItem, MediaSource
from tv_channel.models import Catalog, GridBlock, GridLayout, TvChannel
from datetime import timedelta, time


class DashboardOverviewTests(TestCase):
    def create_playout(self):
        catalog = Catalog.objects.create(name="Schedule")
        channel = TvChannel.objects.create(name="On air", catalog=catalog)
        grid = GridLayout.objects.create(tv_channel=channel, is_active=True)
        block = GridBlock.objects.create(
            grid_layout=grid, starts_at=time(10), ends_at=time(11)
        )
        source = MediaSource.objects.create(name="Source", credentials={})
        collection = MediaCollection.objects.create(
            name="Collection",
            external_id="collection",
            media_source=source,
            hash_data="hash",
        )
        container = MediaContainer.objects.create(
            original_data_hash="container-hash",
            external_id="container",
            title="Series",
            media_source=source,
            media_collection=collection,
        )
        item = MediaItem.objects.create(
            original_data_hash="item-hash",
            external_id="item",
            title="Episode",
            container=container,
            media_source=source,
        )
        playout = TvPlayout.objects.create(
            tv_channel=channel, grid=grid, is_active=True
        )
        selection = BlockContainerSelection.objects.create(
            media_container=container, block=block, tv_playout=playout
        )
        return channel, grid, block, item, playout, selection

    def test_empty_overview_contract(self):
        response = APIClient().get("/api/dashboard/overview/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["stats"]["channels_total"], 0)
        self.assertEqual(response.data["alerts"], [])
        self.assertEqual(response.data["on_air"], [])

    def test_counts_enabled_channels_and_stale_sources(self):
        catalog = Catalog.objects.create(name="Test")
        TvChannel.objects.create(name="Active", catalog=catalog, is_enabled=True)
        TvChannel.objects.create(name="Disabled", catalog=catalog, is_enabled=False)
        MediaSource.objects.create(name="Jellyfin", credentials={})
        data = APIClient().get("/api/dashboard/overview/").data
        self.assertEqual(data["stats"]["channels_total"], 2)
        self.assertEqual(data["stats"]["channels_enabled"], 1)
        self.assertEqual(data["stats"]["sources_stale"], 1)
        self.assertEqual(data["alerts"][0]["kind"], "stale_source")

    def test_returns_current_and_next_fixed_schedule_items(self):
        channel, _, _, item, _, selection = self.create_playout()
        now = timezone.now()
        ScheduleMediaItem.objects.create(
            item=item,
            block_container_selection=selection,
            starts_at=now - timedelta(minutes=10),
            ends_at=now + timedelta(minutes=10),
        )
        next_item = MediaItem.objects.create(
            original_data_hash="next-hash",
            external_id="next",
            title="Next episode",
            container=item.container,
            media_source=item.media_source,
        )
        ScheduleMediaItem.objects.create(
            item=next_item,
            block_container_selection=selection,
            starts_at=now + timedelta(minutes=10),
            ends_at=now + timedelta(minutes=20),
        )

        data = APIClient().get("/api/dashboard/overview/").data

        self.assertEqual(data["stats"]["channels_on_air"], 1)
        self.assertEqual(data["on_air"][0]["tv_channel_id"], channel.id)
        self.assertEqual(data["on_air"][0]["current"]["title"], "Episode")
        self.assertEqual(data["on_air"][0]["next"]["title"], "Next episode")

    def test_prioritizes_playout_errors_before_grid_warnings(self):
        channel, grid, _, _, playout, _ = self.create_playout()
        GridBlock.objects.create(grid_layout=grid, starts_at=time(12), ends_at=time(13))
        PlayoutGenerationReport.objects.create(
            tv_playout=playout,
            issues=[
                {
                    "severity": "error",
                    "code": "gap",
                    "message": "Missing media",
                }
            ],
        )

        data = APIClient().get("/api/dashboard/overview/").data

        self.assertEqual(data["alerts"][0]["kind"], "playout_issue")
        self.assertEqual(data["alerts"][0]["object_id"], channel.id)
        self.assertTrue(
            any(alert["kind"] == "grid_warning" for alert in data["alerts"])
        )
