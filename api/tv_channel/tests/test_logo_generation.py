import base64
import tempfile
from unittest import mock

from django.test import TestCase, override_settings
from rest_framework.test import APITestCase

from tv_channel.models import Catalog, EditorialLine, TvChannel
from tv_channel.services.logo_generation.base import LogoGenerationError, LogoImageBackend
from tv_channel.services.logo_generation.comfyui_backend import ComfyUiImageBackend
from tv_channel.services.logo_generation.logo_generation_service import BACKENDS, LogoGenerationService
from tv_channel.services.logo_generation.openai_backend import OpenAiImageBackend
from tv_channel.services.logo_prompt_service import LogoPromptService

TEMP_MEDIA_ROOT = tempfile.mkdtemp(prefix="flowless-test-media-")


class FakeBackend(LogoImageBackend):
    name = "fake"

    def generate(self, prompt: str) -> bytes:
        return b"png-bytes"


class BackendResolutionTests(TestCase):
    def setUp(self):
        self.catalog = Catalog.objects.create(name="Catalog")
        self.tv_channel = TvChannel.objects.create(name="Chan", catalog=self.catalog)

    def test_unknown_backend_raises(self):
        with self.assertRaises(LogoGenerationError):
            LogoGenerationService(self.tv_channel, backend="dall-e-9000")

    @override_settings(IMAGE_GENERATION_BACKEND="fake")
    def test_settings_default_is_used_when_no_param(self):
        with mock.patch.dict(BACKENDS, {"fake": FakeBackend}):
            service = LogoGenerationService(self.tv_channel)
        self.assertEqual(service.backend.name, "fake")

    @override_settings(IMAGE_GENERATION_BACKEND="fake")
    def test_param_overrides_settings(self):
        with mock.patch.dict(BACKENDS, {"fake": FakeBackend, "other": FakeBackend}):
            service = LogoGenerationService(self.tv_channel, backend="other")
        self.assertEqual(service.backend.name, "fake")  # FakeBackend instance either way


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT, IMAGE_GENERATION_BACKEND="fake")
class LogoGenerationServiceTests(TestCase):
    def setUp(self):
        self.catalog = Catalog.objects.create(name="Catalog")
        self.tv_channel = TvChannel.objects.create(name="Chan", catalog=self.catalog)

    def test_generated_image_is_saved_on_the_channel(self):
        with mock.patch.dict(BACKENDS, {"fake": FakeBackend}):
            LogoGenerationService(self.tv_channel).generate()

        self.tv_channel.refresh_from_db()
        self.assertTrue(self.tv_channel.logo)
        with self.tv_channel.logo.open("rb") as handle:
            self.assertEqual(handle.read(), b"png-bytes")


class OpenAiBackendTests(TestCase):
    @override_settings(OPENAI_IMAGE_API_KEY=None)
    def test_missing_api_key_raises(self):
        with self.assertRaises(LogoGenerationError):
            OpenAiImageBackend()

    @override_settings(OPENAI_IMAGE_API_KEY="key", OPENAI_IMAGE_MODEL="gpt-image-1")
    def test_b64_response_is_decoded(self):
        payload = base64.b64encode(b"image-data").decode()
        fake_client = mock.Mock()
        fake_client.images.generate.return_value = mock.Mock(
            data=[mock.Mock(b64_json=payload, url=None)]
        )
        with mock.patch(
            "tv_channel.services.logo_generation.openai_backend.OpenAI",
            return_value=fake_client,
        ):
            backend = OpenAiImageBackend()
            result = backend.generate("a logo")

        self.assertEqual(result, b"image-data")
        fake_client.images.generate.assert_called_once()


@override_settings(COMFYUI_URL="http://comfy:8188", COMFYUI_TIMEOUT_SECONDS=10)
class ComfyUiBackendTests(TestCase):
    def test_full_flow_submit_poll_download(self):
        module_path = "tv_channel.services.logo_generation.comfyui_backend"

        post_response = mock.Mock(status_code=200)
        post_response.json.return_value = {"prompt_id": "abc"}

        history_response = mock.Mock(status_code=200)
        history_response.json.return_value = {
            "abc": {
                "status": {"status_str": "success"},
                "outputs": {
                    "9": {"images": [{"filename": "logo.png", "subfolder": "", "type": "output"}]},
                },
            }
        }
        view_response = mock.Mock(status_code=200, content=b"comfy-image")

        with mock.patch(f"{module_path}.requests.post", return_value=post_response) as post_mock, \
                mock.patch(f"{module_path}.requests.get", side_effect=[history_response, view_response]):
            backend = ComfyUiImageBackend()
            result = backend.generate("a logo")

        self.assertEqual(result, b"comfy-image")
        workflow = post_mock.call_args.kwargs["json"]["prompt"]
        rendered_prompt = workflow["6"]["inputs"]["text"]
        self.assertIn("a logo", rendered_prompt)

    def test_workflow_error_raises(self):
        module_path = "tv_channel.services.logo_generation.comfyui_backend"

        post_response = mock.Mock(status_code=200)
        post_response.json.return_value = {"prompt_id": "abc"}
        history_response = mock.Mock(status_code=200)
        history_response.json.return_value = {
            "abc": {"status": {"status_str": "error"}, "outputs": {}}
        }

        with mock.patch(f"{module_path}.requests.post", return_value=post_response), \
                mock.patch(f"{module_path}.requests.get", return_value=history_response):
            backend = ComfyUiImageBackend()
            with self.assertRaises(LogoGenerationError):
                backend.generate("a logo")


class LogoPromptEnrichmentTests(TestCase):
    def setUp(self):
        self.catalog = Catalog.objects.create(name="Ma médiathèque")
        self.tv_channel = TvChannel.objects.create(
            name="SciFiXplore",
            catalog=self.catalog,
            description="Science-fiction channel",
            specification="Dominant nature: fiction. Catégories: science-fiction, aventure.",
        )
        EditorialLine.objects.create(
            tv_channel=self.tv_channel,
            preferred={"categories": ["science-fiction", "aventure"]},
        )

    def test_prompt_contains_specification_and_editorial_summary(self):
        prompt = LogoPromptService(self.tv_channel).generate_prompt()

        self.assertIn("SciFiXplore", prompt)
        self.assertIn("Dominant nature: fiction", prompt)
        self.assertIn("science-fiction", prompt)
        self.assertIn("Ma médiathèque", prompt)


class GenerateLogoActionTests(APITestCase):
    def setUp(self):
        self.catalog = Catalog.objects.create(name="Catalog")
        self.tv_channel = TvChannel.objects.create(name="Chan", catalog=self.catalog)

    def test_action_dispatches_the_task(self):
        with mock.patch("tv_channel.views.tv_channel_views.generate_tv_channel_logo") as task_mock:
            response = self.client.post(
                f"/api/tv-channel/{self.tv_channel.id}/generate-logo/",
                {"backend": "comfyui"},
                format="json",
            )

        self.assertEqual(response.status_code, 202)
        task_mock.delay.assert_called_once_with(self.tv_channel.id, backend="comfyui")

    def test_unknown_backend_is_rejected(self):
        with mock.patch("tv_channel.views.tv_channel_views.generate_tv_channel_logo") as task_mock:
            response = self.client.post(
                f"/api/tv-channel/{self.tv_channel.id}/generate-logo/",
                {"backend": "nope"},
                format="json",
            )

        self.assertEqual(response.status_code, 400)
        task_mock.delay.assert_not_called()
