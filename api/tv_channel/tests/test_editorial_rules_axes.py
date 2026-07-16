from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APITestCase

from rule_engine.models import Category, VocabularyEntry
from tv_channel.models import Catalog, EditorialLine, GridBlock, GridLayout, GridLayoutMode, TvChannel
from tv_channel.services.editorial_rules_validation import (
    RULE_AXES,
    validate_editorial_rules_payload,
    validate_rule_level,
)


def seed_vocabulary():
    Category.objects.create(category="horror")
    VocabularyEntry.objects.bulk_create([
        VocabularyEntry(axis="actors", value="Tom Hanks"),
        VocabularyEntry(axis="directors", value="Tom Hooper"),
        VocabularyEntry(axis="studios", value="Warner Bros."),
        VocabularyEntry(axis="countries", value="France"),
        VocabularyEntry(axis="audio_languages", value="fre"),
        VocabularyEntry(axis="subtitle_languages", value="eng"),
    ])


class EditorialRulesAxesValidationTests(TestCase):

    def setUp(self):
        seed_vocabulary()

    def test_rule_axes_include_vocabulary_axes(self):
        for axis in ("directors", "writers", "creators", "actors", "studios",
                     "countries", "audio_languages", "subtitle_languages"):
            self.assertIn(axis, RULE_AXES)

    def test_vocabulary_axis_accepts_known_value(self):
        normalized = validate_rule_level(
            {"actors": ["Tom Hanks", "Tom Hanks"], "audio_languages": ["fre"]},
            "allowed",
        )
        self.assertEqual(normalized["actors"], ["Tom Hanks"])
        self.assertEqual(normalized["audio_languages"], ["fre"])

    def test_vocabulary_axis_rejects_unknown_value_strict(self):
        with self.assertRaises(ValidationError):
            validate_rule_level({"actors": ["Unknown Actor"]}, "allowed")

    def test_vocabulary_axis_filters_unknown_value_lenient(self):
        normalized = validate_rule_level(
            {"actors": ["Tom Hanks", "Unknown Actor"]},
            "allowed",
            lenient=True,
        )
        self.assertEqual(normalized["actors"], ["Tom Hanks"])

    def test_overlap_between_allowed_and_forbidden_on_new_axis(self):
        with self.assertRaises(ValidationError):
            validate_editorial_rules_payload({
                "allowed": {"studios": ["Warner Bros."]},
                "forbidden": {"studios": ["Warner Bros."]},
            })


class EditorialLineApiAxesTests(APITestCase):

    def setUp(self):
        seed_vocabulary()
        catalog = Catalog.objects.create(name="Axes catalog")
        self.channel = TvChannel.objects.create(name="Axes channel", catalog=catalog)

    def test_put_editorial_line_with_new_axes(self):
        response = self.client.put(
            f"/api/tv-channel/{self.channel.id}/editorial-line/",
            {
                "start_at": "06:00",
                "end_at": "22:00",
                "allow_filler": True,
                "allowed": {"actors": ["Tom Hanks"], "countries": ["France"]},
                "preferred": {"directors": ["Tom Hooper"]},
                "forbidden": {"subtitle_languages": ["eng"]},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        line = EditorialLine.objects.get(tv_channel=self.channel)
        self.assertEqual(line.allowed["actors"], ["Tom Hanks"])
        self.assertEqual(line.preferred["directors"], ["Tom Hooper"])
        self.assertEqual(line.forbidden["subtitle_languages"], ["eng"])

    def test_put_editorial_line_rejects_unknown_actor(self):
        response = self.client.put(
            f"/api/tv-channel/{self.channel.id}/editorial-line/",
            {
                "start_at": "06:00",
                "end_at": "22:00",
                "allow_filler": True,
                "allowed": {"actors": ["Unknown Actor"]},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_reset_rules_clears_only_targeted_new_axis(self):
        EditorialLine.objects.create(
            tv_channel=self.channel,
            allowed={"actors": ["Tom Hanks"], "categories": ["horror"]},
            forbidden={"actors": ["Tom Hanks"]},
        )
        layout = GridLayout.objects.create(
            tv_channel=self.channel, is_active=True, mode=GridLayoutMode.FIXED
        )
        block = GridBlock.objects.create(
            grid_layout=layout,
            starts_at="12:00",
            ends_at="13:00",
            allowed={"actors": ["Tom Hanks"], "studios": ["Warner Bros."]},
        )

        response = self.client.post(
            f"/api/tv-channel/{self.channel.id}/reset-rules/",
            {"types": ["actor"], "levels": ["allowed", "forbidden"]},
            format="json",
        )
        self.assertEqual(response.status_code, 204)

        line = EditorialLine.objects.get(tv_channel=self.channel)
        self.assertEqual(line.allowed["actors"], [])
        self.assertEqual(line.allowed["categories"], ["horror"])
        self.assertEqual(line.forbidden["actors"], [])

        block.refresh_from_db()
        self.assertEqual(block.allowed["actors"], [])
        self.assertEqual(block.allowed["studios"], ["Warner Bros."])
