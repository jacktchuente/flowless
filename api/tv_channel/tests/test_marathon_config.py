from datetime import time

from rest_framework.test import APITestCase

from media_source.constants import MediaContainerKind
from tv_channel.models import (
    Catalog,
    ChannelProgrammingMode,
    EditorialLine,
    GridLayout,
    GridLayoutMode,
    MarathonConfig,
    MarathonKindPolicy,
    TvChannel,
)
from tv_channel.services.tv_channel_service import TvChannelService


class MarathonBlueprintTests(APITestCase):
    def setUp(self):
        self.catalog = Catalog.objects.create(name="Marathon catalog")
        self.channel = TvChannel.objects.create(
            name="Marathon channel",
            catalog=self.catalog,
            programming_mode=ChannelProgrammingMode.MARATHON,
        )
        self.editorial_line = EditorialLine.objects.create(
            tv_channel=self.channel,
            start_at=time(6, 0),
            end_at=time(22, 0),
            allow_filler=True,
        )

    def test_blueprint_creates_marathon_grid_with_default_config(self):
        result = TvChannelService(tv_channel=self.channel).generate_editorial_line_and_grid()

        grid_layout = result["grid_layout"]
        self.assertEqual(grid_layout.mode, GridLayoutMode.MARATHON)
        self.assertTrue(grid_layout.is_active)
        self.assertEqual(result["blocks"], [])
        self.assertEqual(grid_layout.gridblock_set.count(), 0)
        self.assertIsNotNone(grid_layout.post_filler_policy)

        policies = {
            policy.container_kind: policy
            for policy in grid_layout.marathon_config.kind_policies.all()
        }
        self.assertEqual(
            set(policies),
            {MediaContainerKind.SERIES, MediaContainerKind.STANDALONE_VIDEO},
        )
        self.assertEqual(policies[MediaContainerKind.SERIES].max_run, 2)
        self.assertEqual(policies[MediaContainerKind.STANDALONE_VIDEO].max_run, 1)

    def test_blueprint_reboot_replaces_active_grid(self):
        first = TvChannelService(tv_channel=self.channel).generate_editorial_line_and_grid()
        second = TvChannelService(tv_channel=self.channel).generate_editorial_line_and_grid(reboot=True)

        first["grid_layout"].refresh_from_db()
        self.assertFalse(first["grid_layout"].is_active)
        self.assertTrue(second["grid_layout"].is_active)
        self.assertEqual(second["grid_layout"].marathon_config.kind_policies.count(), 2)

    def test_blueprint_without_filler_skips_grid_policy(self):
        self.editorial_line.allow_filler = False
        self.editorial_line.save(update_fields=["allow_filler"])

        result = TvChannelService(tv_channel=self.channel).generate_editorial_line_and_grid()

        self.assertIsNone(result["grid_layout"].post_filler_policy)


class MarathonChannelApiTests(APITestCase):
    def setUp(self):
        self.catalog = Catalog.objects.create(name="Marathon catalog")

    def test_create_accepts_programming_mode_and_update_ignores_it(self):
        created = self.client.post(
            "/api/tv-channel/",
            {
                "name": "Marathon channel",
                "description": "desc",
                "catalog": self.catalog.id,
                "programming_mode": ChannelProgrammingMode.MARATHON,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        channel = TvChannel.objects.get(name="Marathon channel")
        self.assertEqual(channel.programming_mode, ChannelProgrammingMode.MARATHON)
        self.assertEqual(created.data["programming_mode"], ChannelProgrammingMode.MARATHON)

        updated = self.client.patch(
            f"/api/tv-channel/{channel.id}/",
            {"programming_mode": ChannelProgrammingMode.CLASSIC},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        channel.refresh_from_db()
        self.assertEqual(channel.programming_mode, ChannelProgrammingMode.MARATHON)


class MarathonConfigApiTests(APITestCase):
    def setUp(self):
        self.catalog = Catalog.objects.create(name="Marathon catalog")
        self.channel = TvChannel.objects.create(
            name="Marathon channel",
            catalog=self.catalog,
            programming_mode=ChannelProgrammingMode.MARATHON,
        )
        self.layout = GridLayout.objects.create(
            tv_channel=self.channel,
            is_active=True,
            mode=GridLayoutMode.MARATHON,
        )
        self.config = MarathonConfig.objects.create(grid_layout=self.layout)
        MarathonKindPolicy.objects.create(
            config=self.config,
            container_kind=MediaContainerKind.SERIES,
            min_run=2,
            max_run=2,
            quota=1,
        )
        self.url = f"/api/tv-channel/{self.channel.id}/marathon-config/"

    def test_get_returns_policies(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["kind_policies"]), 1)
        policy = response.data["kind_policies"][0]
        self.assertEqual(policy["container_kind"], MediaContainerKind.SERIES)
        self.assertEqual(policy["container_kind_label"], "series")

    def test_put_replaces_all_policies(self):
        response = self.client.put(
            self.url,
            {
                "kind_policies": [
                    {
                        "container_kind": MediaContainerKind.STANDALONE_VIDEO,
                        "min_run": 1,
                        "max_run": 1,
                        "quota": 3,
                    },
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        policies = list(self.config.kind_policies.all())
        self.assertEqual(len(policies), 1)
        self.assertEqual(policies[0].container_kind, MediaContainerKind.STANDALONE_VIDEO)
        self.assertEqual(policies[0].quota, 3)

    def test_put_rejects_duplicate_kind(self):
        response = self.client.put(
            self.url,
            {
                "kind_policies": [
                    {"container_kind": MediaContainerKind.SERIES, "min_run": 1, "max_run": 1, "quota": 1},
                    {"container_kind": MediaContainerKind.SERIES, "min_run": 2, "max_run": 2, "quota": 1},
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.config.kind_policies.count(), 1)

    def test_put_rejects_min_run_above_max_run(self):
        response = self.client.put(
            self.url,
            {
                "kind_policies": [
                    {"container_kind": MediaContainerKind.SERIES, "min_run": 3, "max_run": 2, "quota": 1},
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_rejects_channel_without_marathon_grid(self):
        self.layout.mode = GridLayoutMode.FIXED
        self.layout.save(update_fields=["mode"])
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)

    def test_grid_data_exposes_marathon_config(self):
        response = self.client.get(f"/api/tv-channel/{self.channel.id}/")
        self.assertEqual(response.status_code, 200)
        grid_data = response.data["grid_data"]
        self.assertEqual(grid_data["mode"], GridLayoutMode.MARATHON)
        self.assertEqual(len(grid_data["marathon_config"]["kind_policies"]), 1)

    def test_new_grid_version_clones_marathon_config(self):
        response = self.client.post(f"/api/tv-channel/{self.channel.id}/grid/new-version/")
        self.assertEqual(response.status_code, 201, response.data)

        self.layout.refresh_from_db()
        self.assertFalse(self.layout.is_active)
        copy = GridLayout.objects.get(tv_channel=self.channel, is_active=True)
        self.assertEqual(copy.mode, GridLayoutMode.MARATHON)
        cloned = list(copy.marathon_config.kind_policies.all())
        self.assertEqual(len(cloned), 1)
        self.assertEqual(cloned[0].container_kind, MediaContainerKind.SERIES)
        self.assertEqual(cloned[0].min_run, 2)
