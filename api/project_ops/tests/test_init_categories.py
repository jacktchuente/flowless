import json
import tempfile
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.test import TestCase

from media_source.constants import MediaNature
from project_ops.services.init_built_in_data import Initializer
from rule_engine.models import Category, CategoryNature, CategoryRule


class InitCategoriesTests(TestCase):

    def test_seeds_categories_natures_and_rules_on_empty_database(self):
        Initializer.init_categories()

        self.assertEqual(Category.objects.count(), 31)
        self.assertEqual(CategoryRule.objects.count(), 31)
        self.assertEqual(CategoryNature.objects.count(), 31)
        self.assertEqual(
            CategoryNature.objects.filter(nature=MediaNature.FICTION).count(), 19
        )
        self.assertEqual(
            CategoryNature.objects.filter(nature=MediaNature.MUSIC).count(), 12
        )
        rock_rules = CategoryRule.objects.get(category__category="rock").rules
        self.assertTrue(rock_rules and rock_rules[0]["fields"] == ["tag", "genre"])

    def test_skips_when_categories_already_exist(self):
        category = Category.objects.create(category="ma-categorie")

        Initializer.init_categories()

        self.assertEqual(Category.objects.count(), 1)
        self.assertEqual(Category.objects.get().pk, category.pk)
        self.assertEqual(CategoryNature.objects.count(), 0)
        self.assertEqual(CategoryRule.objects.count(), 0)

    def test_running_twice_is_a_no_op(self):
        Initializer.init_categories()
        rule = CategoryRule.objects.get(category__category="rock")
        rule.rules = [{"fields": ["tag"], "values": ["edited"]}]
        rule.save()

        Initializer.init_categories()

        self.assertEqual(Category.objects.count(), 31)
        rule.refresh_from_db()
        self.assertEqual(rule.rules, [{"fields": ["tag"], "values": ["edited"]}])

    def test_multiple_top_level_rules_are_grouped_by_category(self):
        seed = {
            "natures": [
                {
                    "name": "fiction",
                    "value": MediaNature.FICTION.value,
                    "categories": ["action"],
                },
                {
                    "name": "documentary",
                    "value": MediaNature.DOCUMENTARY.value,
                    "categories": ["action"],
                },
            ],
            "rules": [
                {"category": "action", "fields": ["genre"], "values": ["action"]},
                {"category": "action", "fields": ["tag"], "values": ["combat"]},
            ],
        }
        with mock.patch.object(Initializer, "_load_category_seed", return_value=seed):
            Initializer.init_categories()

        self.assertEqual(
            CategoryRule.objects.get(category__category="action").rules,
            [
                {"fields": ["genre"], "values": ["action"]},
                {"fields": ["tag"], "values": ["combat"]},
            ],
        )
        self.assertEqual(Category.objects.filter(category="action").count(), 1)
        self.assertEqual(CategoryNature.objects.filter(category__category="action").count(), 2)


class CategorySeedValidationTests(TestCase):

    def _write_seed(self, payload) -> Path:
        file = tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(payload, file)
        file.close()
        self.addCleanup(Path(file.name).unlink)
        return Path(file.name)

    def _valid_payload(self):
        return {
            "natures": [
                {
                    "name": choice.label,
                    "categories": ["action"] if choice == MediaNature.FICTION else [],
                }
                for choice in MediaNature
            ],
            "rules": [
                {"category": "action", "fields": ["genre"], "values": ["action"]},
            ],
        }

    def test_valid_payload_loads(self):
        entries = Initializer._load_category_seed(self._write_seed(self._valid_payload()))
        self.assertEqual(
            entries,
            {
                "natures": [
                    {
                        "name": choice.label,
                        "value": choice.value,
                        "categories": ["action"] if choice == MediaNature.FICTION else [],
                    }
                    for choice in MediaNature
                ],
                "rules": [
                    {"category": "action", "fields": ["genre"], "values": ["action"]},
                ],
            },
        )

    def test_missing_nature_label_is_rejected(self):
        payload = self._valid_payload()
        payload["natures"] = [
            nature for nature in payload["natures"] if nature["name"] != "sport"
        ]
        with self.assertRaises(ValueError):
            Initializer._load_category_seed(self._write_seed(payload))

    def test_unknown_entry_nature_is_rejected(self):
        payload = self._valid_payload()
        payload["natures"][0]["name"] = "cartoon"
        with self.assertRaises(ValueError):
            Initializer._load_category_seed(self._write_seed(payload))

    def test_entry_without_name_is_rejected(self):
        payload = self._valid_payload()
        payload["natures"][0].pop("name")
        with self.assertRaises(ValueError):
            Initializer._load_category_seed(self._write_seed(payload))

    def test_duplicate_name_is_rejected(self):
        payload = self._valid_payload()
        payload["natures"].append({"name": "fiction", "categories": []})
        with self.assertRaises(ValueError):
            Initializer._load_category_seed(self._write_seed(payload))

    def test_extra_field_in_nature_is_rejected(self):
        payload = self._valid_payload()
        payload["natures"][0]["rules"] = []
        with self.assertRaises(ValueError):
            Initializer._load_category_seed(self._write_seed(payload))

    def test_duplicate_category_inside_nature_is_rejected(self):
        payload = self._valid_payload()
        fiction = next(nature for nature in payload["natures"] if nature["name"] == "fiction")
        fiction["categories"].append("Action")
        with self.assertRaises(ValueError):
            Initializer._load_category_seed(self._write_seed(payload))

    def test_rule_targeting_unknown_category_is_rejected(self):
        payload = self._valid_payload()
        payload["rules"][0]["category"] = "unknown"
        with self.assertRaises(ValueError):
            Initializer._load_category_seed(self._write_seed(payload))

    def test_multiple_rules_for_category_are_accepted(self):
        payload = self._valid_payload()
        payload["rules"].append({
            "category": "action",
            "fields": ["tag"],
            "values": ["combat"],
        })
        seed = Initializer._load_category_seed(self._write_seed(payload))
        self.assertEqual([rule["category"] for rule in seed["rules"]], ["action", "action"])

    def test_shipped_seed_file_natures_match_media_nature_labels(self):
        file_path = settings.BASE_DIR / "project_ops" / "built_in_data" / "categories.json"
        with file_path.open(encoding="utf-8") as file:
            payload = json.load(file)
        self.assertEqual(
            {nature["name"] for nature in payload["natures"]},
            {choice.label for choice in MediaNature},
        )
        self.assertEqual(set(payload), {"natures", "rules"})
