from rest_framework.test import APITestCase

from media_source.models import MediaSource


class MediaSourceSetActiveTests(APITestCase):
    def setUp(self):
        self.source = MediaSource.objects.create(
            name="jellyfin",
            is_active=False,
            credentials={"application_url": "http://jf", "username": "u", "password": "p"},
        )

    def test_set_active_toggles_flag_without_credentials_check(self):
        response = self.client.post(
            f"/api/media-source/{self.source.id}/set-active/",
            {"is_active": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_active"])
        self.source.refresh_from_db()
        self.assertTrue(self.source.is_active)

        response = self.client.post(
            f"/api/media-source/{self.source.id}/set-active/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.source.refresh_from_db()
        self.assertFalse(self.source.is_active)
