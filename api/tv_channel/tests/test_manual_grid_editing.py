from datetime import time
from unittest import mock

from django.test import override_settings
from rest_framework.test import APITestCase

from tv_channel.models import (
    Catalog,
    EditorialLine,
    FillerPolicy,
    GridBlock,
    GridLayout,
    GridLayoutMode,
    TvChannel,
)
from utils.llm_service import LLMResponse


class ManualGridApiTests(APITestCase):
    def setUp(self):
        self.catalog = Catalog.objects.create(name="Manual catalog")
        self.channel = TvChannel.objects.create(
            name="Manual channel", catalog=self.catalog
        )
        self.layout = GridLayout.objects.create(
            tv_channel=self.channel, is_active=True, mode=GridLayoutMode.FIXED
        )
        self.policy = FillerPolicy.objects.create(
            name="Short ident", duration_seconds=30
        )

    def block_payload(self, **overrides):
        payload = {
            "grid_layout": self.layout.id,
            "starts_at": "12:00",
            "ends_at": "13:00",
            "priority": 50,
            "min_items": 1,
            "max_items": 2,
            "min_duration_seconds_per_item": 60,
            "max_duration_seconds_per_item": 3600,
            "allowed_categories": ["horror"],
            "forbidden_categories": [],
            "preferred_categories": [],
            "allowed_natures": ["fiction"],
            "forbidden_natures": [],
            "preferred_natures": [],
            "allowed_container_kinds": ["standalone_video"],
            "forbidden_container_kinds": [],
            "preferred_container_kinds": [],
            "post_filler_policy": self.policy.id,
        }
        payload.update(overrides)
        return payload

    def test_form_options_and_editorial_line_create(self):
        options = self.client.get("/api/tv-channel/form-options/")
        self.assertEqual(options.status_code, 200)
        self.assertIn({"value": 1, "label": "fiction"}, options.data["natures"])
        self.assertEqual(options.data["filler_policies"][0]["name"], "Short ident")

        response = self.client.patch(
            f"/api/tv-channel/{self.channel.id}/editorial-line/",
            {
                "allowed_natures": ["fiction", 1],
                "forbidden_categories": ["kids"],
                "start_at": "06:00",
                "end_at": "23:00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["allowed_natures"], [1])
        self.assertEqual(
            self.client.get(f"/api/tv-channel/{self.channel.id}/").data[
                "editorial_line_data"
            ]["forbidden_categories"],
            ["kids"],
        )

    def test_editorial_validation_rejects_overlap_and_bad_window(self):
        response = self.client.patch(
            f"/api/tv-channel/{self.channel.id}/editorial-line/",
            {"allowed_natures": [1], "forbidden_natures": ["fiction"]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.patch(
            f"/api/tv-channel/{self.channel.id}/editorial-line/",
            {"start_at": "22:00", "end_at": "06:00"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_block_crud_bounds_and_inactive_guard(self):
        created = self.client.post(
            "/api/grid-block/", self.block_payload(), format="json"
        )
        self.assertEqual(created.status_code, 201, created.data)
        block_id = created.data["id"]
        updated = self.client.patch(
            f"/api/grid-block/{block_id}/", {"priority": 70}, format="json"
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(updated.data["priority"], 70)
        self.assertEqual(
            self.client.patch(
                f"/api/grid-block/{block_id}/", {"max_items": 4}, format="json"
            ).status_code,
            400,
        )
        other = GridLayout.objects.create(
            tv_channel=self.channel, is_active=False, mode=GridLayoutMode.FIXED
        )
        self.assertEqual(
            self.client.patch(
                f"/api/grid-block/{block_id}/", {"grid_layout": other.id}, format="json"
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.delete(f"/api/grid-block/{block_id}/").status_code, 204
        )

    @mock.patch("tv_channel.views.grid_block_views.GridBlockService")
    def test_available_media_count_previews_unsaved_rules(self, service_class):
        service_class.return_value.get_available_media_count.return_value = 12
        block = GridBlock.objects.create(
            grid_layout=self.layout,
            starts_at=time(12),
            ends_at=time(13),
            allowed_categories=["drama"],
        )

        response = self.client.post(
            f"/api/grid-block/{block.id}/available-media-count/",
            {"allowed_categories": ["comedy"], "min_duration_seconds_per_item": 600},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data, {"count": 12})
        preview = service_class.call_args.kwargs["grid_block"]
        self.assertEqual(preview.allowed_categories, ["comedy"])
        self.assertEqual(preview.min_duration_seconds_per_item, 600)
        block.refresh_from_db()
        self.assertEqual(block.allowed_categories, ["drama"])

    def test_flexible_grid_writes_are_rejected(self):
        self.layout.mode = GridLayoutMode.FLEXIBLE
        self.layout.save(update_fields=["mode"])
        self.assertEqual(
            self.client.patch(
                f"/api/tv-channel/{self.channel.id}/grid/",
                {"post_filler_policy": None},
                format="json",
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post(
                "/api/grid-block/", self.block_payload(), format="json"
            ).status_code,
            400,
        )

    def test_grid_update_version_and_warnings(self):
        EditorialLine.objects.create(
            tv_channel=self.channel, start_at=time(12), end_at=time(14)
        )
        first = GridBlock.objects.create(
            grid_layout=self.layout, starts_at=time(12), ends_at=time(13)
        )
        GridBlock.objects.create(
            grid_layout=self.layout, starts_at=time(13, 30), ends_at=time(14)
        )
        warnings = self.client.get(
            f"/api/tv-channel/{self.channel.id}/grid-warnings/"
        ).data["warnings"]
        self.assertTrue(any("Gap" in item for item in warnings))
        patched = self.client.patch(
            f"/api/tv-channel/{self.channel.id}/grid/",
            {"post_filler_policy": self.policy.id},
            format="json",
        )
        self.assertEqual(patched.status_code, 200, patched.data)
        copied = self.client.post(
            f"/api/tv-channel/{self.channel.id}/grid/new-version/", {}, format="json"
        )
        self.assertEqual(copied.status_code, 201, copied.data)
        self.layout.refresh_from_db()
        self.assertFalse(self.layout.is_active)
        self.assertEqual(len(copied.data["blocks"]), 2)
        self.assertNotEqual(copied.data["blocks"][0]["id"], first.id)


@override_settings(LLM_RETRY_FORM_SUGGESTION=2)
class FormSuggestionApiTests(APITestCase):
    def setUp(self):
        catalog = Catalog.objects.create(name="Suggestion catalog")
        self.channel = TvChannel.objects.create(
            name="Suggestion channel", catalog=catalog
        )
        GridLayout.objects.create(
            tv_channel=self.channel, is_active=True, mode=GridLayoutMode.FIXED
        )

    @mock.patch("tv_channel.services.form_suggestion_service.LLMService.complete")
    def test_suggestion_retries_and_normalizes(self, complete):
        complete.side_effect = [
            LLMResponse(content="bad", raw_response=None),
            LLMResponse(
                content='<suggestion_output>{"allowed_natures":["fiction"],"start_at":"06:00","end_at":"22:00"}</suggestion_output>',
                raw_response=None,
            ),
        ]
        response = self.client.post(
            f"/api/tv-channel/{self.channel.id}/suggest-form/",
            {
                "form_kind": "editorial_line",
                "user_context": "fiction",
                "current_values": {},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["values"]["allowed_natures"], [1])
        self.assertEqual(complete.call_count, 2)

    @mock.patch("tv_channel.services.form_suggestion_service.LLMService.complete")
    def test_persistent_invalid_value_returns_502(self, complete):
        complete.return_value = LLMResponse(
            content='<suggestion_output>{"allowed_natures":["alien"]}</suggestion_output>',
            raw_response=None,
        )
        response = self.client.post(
            f"/api/tv-channel/{self.channel.id}/suggest-form/",
            {"form_kind": "editorial_line"},
            format="json",
        )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(complete.call_count, 2)

    @mock.patch("tv_channel.services.form_suggestion_service.LLMService.complete")
    def test_network_failure_returns_502_after_retries(self, complete):
        complete.side_effect = ConnectionError("LLM unavailable")
        response = self.client.post(
            f"/api/tv-channel/{self.channel.id}/suggest-form/",
            {"form_kind": "editorial_line"},
            format="json",
        )
        self.assertEqual(response.status_code, 502)
        self.assertIn("LLM request failed", response.data["detail"])
        self.assertEqual(complete.call_count, 2)
