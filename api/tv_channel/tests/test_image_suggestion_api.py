from io import BytesIO
import shutil
import tempfile
from unittest.mock import patch

from django.test import override_settings
from PIL import Image
from rest_framework.test import APITestCase

from project_ops.constants import AnalyzeStatus
from tv_channel.models import (
    Catalog,
    ChannelImageKind,
    ChannelImageSuggestion,
    ChannelImageSuggestionRun,
    EditorialLine,
    TvChannel,
)
from tv_channel.services.image_suggestion.apply_service import ChannelImageApplyService
from tv_channel.services.image_suggestion.providers.base import ImageResult, ImageSearchProvider
from tv_channel.services.image_suggestion.suggestion_service import ChannelImageSuggestionService

PROVIDERS_PATCH = "tv_channel.services.image_suggestion.providers.PROVIDERS"


def png_bytes(width=1600, height=900, mode="RGB"):
    buffer = BytesIO()
    Image.new(mode, (width, height), (10, 20, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


class _StubProvider(ImageSearchProvider):
    name = "stub"
    result_count = 5
    downloaded: list[str] = []

    def is_available(self):
        return True

    def search(self, query, limit):
        return [
            ImageResult(
                provider=self.name,
                source_url=f"http://stub/full/{index}",
                thumbnail_url=f"http://stub/thumb/{index}",
                attribution=f"Item {index}",
            )
            for index in range(1, min(self.result_count, limit) + 1)
        ]

    def download(self, url):
        type(self).downloaded.append(url)
        return png_bytes(width=1600, height=900)


class ImageSuggestionFixtureMixin:
    def build_fixtures(self):
        _StubProvider.downloaded = []
        self.media_root = tempfile.mkdtemp(prefix="flowless-image-tests-")
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()
        self.addCleanup(self.override.disable)

        self.catalog = Catalog.objects.create(name="Images catalog")
        self.channel = TvChannel.objects.create(name="Images channel", catalog=self.catalog)
        EditorialLine.objects.create(
            tv_channel=self.channel,
            preferred={"studios": ["Studio Ghibli"]},
        )
        self.channel.refresh_from_db()


class ChannelImageSuggestionServiceTests(ImageSuggestionFixtureMixin, APITestCase):
    def setUp(self):
        self.build_fixtures()

    def test_run_records_query_and_stores_five_thumbnails(self):
        with patch(PROVIDERS_PATCH, (_StubProvider,)):
            result = ChannelImageSuggestionService(self.channel).run()

        run = result.run
        self.assertEqual(run.status, AnalyzeStatus.COMPLETE)
        self.assertEqual((run.entity_type, run.query, run.query_source), ("studio", "Studio Ghibli", "axes"))
        suggestions = list(run.suggestions.all())
        self.assertEqual([suggestion.position for suggestion in suggestions], [1, 2, 3, 4, 5])
        for suggestion in suggestions:
            self.assertTrue(suggestion.thumbnail.storage.exists(suggestion.thumbnail.name))
        self.assertEqual(len(_StubProvider.downloaded), 5)

    def test_run_with_failing_thumbnail_downgrades_status(self):
        class FlakyProvider(_StubProvider):
            def download(self, url):
                if url.endswith("/2"):
                    raise RuntimeError("boom")
                return png_bytes()

        with patch(PROVIDERS_PATCH, (FlakyProvider,)):
            result = ChannelImageSuggestionService(self.channel).run()

        self.assertEqual(result.run.status, AnalyzeStatus.COMPLETE_WITH_ERRORS)
        self.assertEqual(result.run.suggestions.count(), 4)
        self.assertTrue(any("Thumbnail download failed" in warning for warning in result.warnings))

    def test_old_runs_are_purged_with_their_files(self):
        with patch(PROVIDERS_PATCH, (_StubProvider,)), self.settings(CHANNEL_IMAGE_RUNS_KEPT=2):
            for _ in range(3):
                ChannelImageSuggestionService(self.channel).run()

        self.assertEqual(ChannelImageSuggestionRun.objects.count(), 2)
        remaining = {
            suggestion.thumbnail.name
            for suggestion in ChannelImageSuggestion.objects.all()
        }
        for name in remaining:
            self.assertTrue(ChannelImageSuggestion.objects.first().thumbnail.storage.exists(name))


class ChannelImageApplyServiceTests(ImageSuggestionFixtureMixin, APITestCase):
    def setUp(self):
        self.build_fixtures()
        with patch(PROVIDERS_PATCH, (_StubProvider,)):
            self.run = ChannelImageSuggestionService(self.channel).run().run
        self.suggestion = self.run.suggestions.first()

    def test_apply_normalizes_and_writes_channel_logo(self):
        with patch(PROVIDERS_PATCH, (_StubProvider,)), self.settings(
            CHANNEL_IMAGE_MAX_WIDTH=400, CHANNEL_IMAGE_MAX_HEIGHT=400
        ):
            channel = ChannelImageApplyService(self.suggestion).apply()

        self.assertTrue(channel.logo)
        with channel.logo.open("rb") as fh:
            image = Image.open(fh)
            image.load()
        self.assertLessEqual(image.width, 400)
        self.assertLessEqual(image.height, 400)
        self.suggestion.refresh_from_db()
        self.assertTrue(self.suggestion.is_chosen)

    def test_apply_marks_single_chosen_suggestion(self):
        other = self.run.suggestions.last()
        with patch(PROVIDERS_PATCH, (_StubProvider,)):
            ChannelImageApplyService(self.suggestion).apply()
            ChannelImageApplyService(other).apply()
        self.assertEqual(self.run.suggestions.filter(is_chosen=True).count(), 1)
        other.refresh_from_db()
        self.assertTrue(other.is_chosen)


class ChannelImageRunApiTests(ImageSuggestionFixtureMixin, APITestCase):
    def setUp(self):
        self.build_fixtures()

    def test_create_dispatches_task(self):
        with patch("tv_channel.views.channel_image_views.generate_channel_image_suggestions") as task_mock:
            response = self.client.post(
                "/api/channel-image-run/",
                {"tv_channel": self.channel.id, "query": "Akira", "entity_type": "theme"},
                format="json",
            )
        self.assertEqual(response.status_code, 202)
        task_mock.delay.assert_called_once_with(
            self.channel.id,
            kind=ChannelImageKind.LOGO,
            query="Akira",
            entity_type="theme",
        )

    def test_list_filters_by_channel_and_nests_suggestions(self):
        with patch(PROVIDERS_PATCH, (_StubProvider,)):
            ChannelImageSuggestionService(self.channel).run()
        other_channel = TvChannel.objects.create(name="Other", catalog=self.catalog)
        ChannelImageSuggestionRun.objects.create(tv_channel=other_channel)

        response = self.client.get(f"/api/channel-image-run/?tv_channel={self.channel.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(len(response.data[0]["suggestions"]), 5)
        self.assertEqual(response.data[0]["query"], "Studio Ghibli")

    def test_choose_applies_suggestion_and_returns_channel(self):
        with patch(PROVIDERS_PATCH, (_StubProvider,)):
            run = ChannelImageSuggestionService(self.channel).run().run
            suggestion = run.suggestions.first()
            response = self.client.post(
                f"/api/channel-image-run/{run.id}/choose/",
                {"suggestion_id": suggestion.id},
                format="json",
            )
        self.assertEqual(response.status_code, 200, response.data)
        self.channel.refresh_from_db()
        self.assertTrue(self.channel.logo)
        self.assertTrue(response.data["logo"])

    def test_choose_rejects_foreign_suggestion(self):
        with patch(PROVIDERS_PATCH, (_StubProvider,)):
            run_a = ChannelImageSuggestionService(self.channel).run().run
            run_b = ChannelImageSuggestionService(self.channel).run().run
        foreign = run_b.suggestions.first()
        response = self.client.post(
            f"/api/channel-image-run/{run_a.id}/choose/",
            {"suggestion_id": foreign.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_destroy_removes_thumbnail_files(self):
        with patch(PROVIDERS_PATCH, (_StubProvider,)):
            run = ChannelImageSuggestionService(self.channel).run().run
        names = [suggestion.thumbnail.name for suggestion in run.suggestions.all()]
        storage = run.suggestions.first().thumbnail.storage
        response = self.client.delete(f"/api/channel-image-run/{run.id}/")
        self.assertEqual(response.status_code, 204)
        for name in names:
            self.assertFalse(storage.exists(name))

    def test_image_query_preview_returns_axes_query(self):
        response = self.client.get(f"/api/tv-channel/{self.channel.id}/image-query-preview/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"entity_type": "studio", "query": "Studio Ghibli", "source": "axes"})

        line = self.channel.editorialline
        line.preferred = {}
        line.save(update_fields=["preferred"])
        response = self.client.get(f"/api/tv-channel/{self.channel.id}/image-query-preview/")
        self.assertEqual(response.data["query"], None)
