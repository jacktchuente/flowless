import tempfile
import time
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase, TestCase, override_settings

from project_ops.services import heartbeat


class HeartbeatServiceTests(SimpleTestCase):
    def test_alive_when_recent(self):
        with mock.patch.object(heartbeat, "_client") as client:
            client.return_value.get.return_value = str(time.time()).encode()
            alive, age = heartbeat.scheduler_is_alive()
        self.assertTrue(alive)
        self.assertLess(age, 5)

    def test_dead_when_stale(self):
        with mock.patch.object(heartbeat, "_client") as client:
            client.return_value.get.return_value = str(time.time() - 3600).encode()
            alive, _ = heartbeat.scheduler_is_alive()
        self.assertFalse(alive)

    def test_dead_when_missing(self):
        with mock.patch.object(heartbeat, "_client") as client:
            client.return_value.get.return_value = None
            alive, age = heartbeat.scheduler_is_alive()
        self.assertFalse(alive)
        self.assertIsNone(age)


class HealthEndpointTests(TestCase):
    @mock.patch(
        "project_ops.views.health_views.scheduler_is_alive",
        return_value=(True, 12.0),
    )
    def test_healthy(self, _):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertTrue(body["database"])
        self.assertTrue(body["scheduler"])

    @mock.patch(
        "project_ops.views.health_views.scheduler_is_alive",
        return_value=(False, None),
    )
    def test_degraded_when_scheduler_dead(self, _):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(body["status"], "degraded")
        self.assertFalse(body["scheduler"])


class MediaServeTests(SimpleTestCase):
    def test_serves_media_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "logo.txt").write_text("hello")
            with override_settings(MEDIA_ROOT=tmp):
                response = self.client.get("/medias/logo.txt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"hello")
        self.assertIn("max-age=3600", response.headers["Cache-Control"])

    def test_missing_media_file_returns_404(self):
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp):
                response = self.client.get("/medias/nope.png")
        self.assertEqual(response.status_code, 404)
