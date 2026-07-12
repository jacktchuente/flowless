from django.test import SimpleTestCase

from media_source.services.media_server_services.jellyfin_service import (
    JellyfinService,
)


class BuildItemPayloadTests(SimpleTestCase):
    def _episode(self, **overrides):
        payload = {
            "Id": "ep-1",
            "Name": "Episode 1",
            "Type": "Episode",
            "IndexNumber": 1,
            "ParentIndexNumber": 1,
        }
        payload.update(overrides)
        return payload

    def test_builds_payload_for_regular_episode(self):
        payload = JellyfinService._build_item_payload(self._episode())
        self.assertIsNotNone(payload)
        self.assertEqual(payload["external_id"], "ep-1")

    def test_skips_virtual_episode_by_location_type(self):
        item = self._episode(LocationType="Virtual")
        self.assertIsNone(JellyfinService._build_item_payload(item))

    def test_skips_virtual_episode_by_flag(self):
        item = self._episode(IsVirtualItem=True)
        self.assertIsNone(JellyfinService._build_item_payload(item))
