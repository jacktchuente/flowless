from datetime import time

from django.test import TestCase

from editorial_planning.models import (
    EditorialChannelCandidate,
    EditorialFlowRun,
    EditorialSegmentPath,
)
from editorial_planning.services.channel_creation_service import (
    EditorialFlexibleChannelCreationService,
)
from tv_channel.models import (
    Catalog,
    FillerPolicy,
    GridBlock,
    GridLayout,
    GridLayoutMode,
    TvChannel,
)
from tv_channel.services.tv_channel_service import TvChannelService


class FillerPolicyManagerTests(TestCase):
    def test_creates_policy_with_deterministic_name(self):
        policy = FillerPolicy.objects.get_or_create_for_params()

        self.assertEqual(policy.name, "Post-roll 180s (default roles)")
        self.assertEqual(policy.duration_seconds, 180)
        self.assertEqual(policy.allowed_roles, [])

    def test_reuses_policy_with_same_params(self):
        first = FillerPolicy.objects.get_or_create_for_params(
            duration_seconds=60, allowed_roles=["trailer"]
        )
        second = FillerPolicy.objects.get_or_create_for_params(
            duration_seconds=60, allowed_roles=["trailer"]
        )

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(FillerPolicy.objects.count(), 1)

    def test_different_params_create_distinct_policies(self):
        base = FillerPolicy.objects.get_or_create_for_params()
        longer = FillerPolicy.objects.get_or_create_for_params(duration_seconds=300)
        roles = FillerPolicy.objects.get_or_create_for_params(allowed_roles=["filler"])

        self.assertEqual(len({base.pk, longer.pk, roles.pk}), 3)
        self.assertEqual(roles.name, "Post-roll 180s (filler)")

    def test_role_order_does_not_create_duplicates(self):
        first = FillerPolicy.objects.get_or_create_for_params(
            allowed_roles=["trailer", "filler"]
        )
        second = FillerPolicy.objects.get_or_create_for_params(
            allowed_roles=["filler", "trailer"]
        )

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.allowed_roles, ["filler", "trailer"])

    def test_returns_oldest_match_when_legacy_duplicates_exist(self):
        oldest = FillerPolicy.objects.create(name="legacy - block#1")
        FillerPolicy.objects.create(name="legacy - block#2")

        policy = FillerPolicy.objects.get_or_create_for_params()

        self.assertEqual(policy.pk, oldest.pk)
        self.assertEqual(FillerPolicy.objects.count(), 2)


class FillerPolicyBlockModeReuseTests(TestCase):
    def setUp(self):
        self.catalog = Catalog.objects.create(name="Reuse catalog")

    def _channel_with_blocks(self, name):
        channel = TvChannel.objects.create(name=name, catalog=self.catalog)
        layout = GridLayout.objects.create(
            tv_channel=channel, is_active=True, mode=GridLayoutMode.FIXED
        )
        blocks = [
            GridBlock.objects.create(
                grid_layout=layout, starts_at=time(12), ends_at=time(13)
            ),
            GridBlock.objects.create(
                grid_layout=layout, starts_at=time(13), ends_at=time(14)
            ),
        ]
        return channel, blocks

    def test_blocks_share_one_policy_across_channels(self):
        first_channel, first_blocks = self._channel_with_blocks("First channel")
        second_channel, second_blocks = self._channel_with_blocks("Second channel")

        TvChannelService(first_channel)._attach_default_post_filler_policies(
            first_blocks
        )
        TvChannelService(second_channel)._attach_default_post_filler_policies(
            second_blocks
        )

        self.assertEqual(FillerPolicy.objects.count(), 1)
        policy_id = FillerPolicy.objects.get().pk
        for block in first_blocks + second_blocks:
            block.refresh_from_db()
            self.assertEqual(block.post_filler_policy_id, policy_id)


class FillerPolicyFlexibleModeReuseTests(TestCase):
    def setUp(self):
        self.catalog = Catalog.objects.create(name="Flexible catalog")
        self.run = EditorialFlowRun.objects.create(catalog=self.catalog)

    def _candidate(self, key, name):
        candidate = EditorialChannelCandidate.objects.create(
            run=self.run, channel_key=key, name=name
        )
        EditorialSegmentPath.objects.create(channel_candidate=candidate)
        return candidate

    def test_flexible_channels_reuse_the_shared_policy(self):
        existing = FillerPolicy.objects.get_or_create_for_params()
        candidate = self._candidate("chan-1", "Flexible one")

        channel = EditorialFlexibleChannelCreationService(
            channel_candidate=candidate
        ).create_channel()

        grid = GridLayout.objects.get(tv_channel=channel)
        self.assertEqual(grid.mode, GridLayoutMode.FLEXIBLE)
        self.assertEqual(grid.post_filler_policy_id, existing.pk)
        self.assertEqual(FillerPolicy.objects.count(), 1)

    def test_flexible_creation_without_existing_policy_creates_one(self):
        candidate = self._candidate("chan-2", "Flexible two")

        channel = EditorialFlexibleChannelCreationService(
            channel_candidate=candidate
        ).create_channel()

        grid = GridLayout.objects.get(tv_channel=channel)
        self.assertIsNotNone(grid.post_filler_policy)
        self.assertEqual(grid.post_filler_policy.duration_seconds, 180)
        self.assertEqual(FillerPolicy.objects.count(), 1)
