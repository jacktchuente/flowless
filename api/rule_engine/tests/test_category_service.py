from django.test import TestCase

from media_source.constants import MediaNature
from rule_engine.models import Category, CategoryNature
from rule_engine.services import category_service


class CategoryServiceTests(TestCase):

    def setUp(self):
        self.rock = Category.objects.create(category="rock")
        self.pop = Category.objects.create(category="pop")
        self.action = Category.objects.create(category="action")
        self.biopic = Category.objects.create(category="biopic")
        self.universal = Category.objects.create(category="archive")

        CategoryNature.objects.create(category=self.rock, nature=MediaNature.MUSIC)
        CategoryNature.objects.create(category=self.pop, nature=MediaNature.MUSIC)
        CategoryNature.objects.create(category=self.action, nature=MediaNature.FICTION)
        CategoryNature.objects.create(category=self.biopic, nature=MediaNature.FICTION)
        CategoryNature.objects.create(category=self.biopic, nature=MediaNature.DOCUMENTARY)
        # self.universal : aucun lien -> valable pour toutes les natures.

    def test_get_all_category_names_sorted(self):
        self.assertEqual(
            category_service.get_all_category_names(),
            ["action", "archive", "biopic", "pop", "rock"],
        )

    def test_get_category_names_for_nature_includes_unlinked(self):
        self.assertEqual(
            category_service.get_category_names_for_nature(MediaNature.FICTION),
            ["action", "archive", "biopic"],
        )

    def test_get_category_names_for_nature_multi_nature_not_duplicated(self):
        names = category_service.get_category_names_for_nature(MediaNature.DOCUMENTARY)
        self.assertEqual(names, ["archive", "biopic"])
        self.assertEqual(len(names), len(set(names)))

    def test_get_category_names_for_nature_without_categories(self):
        self.assertEqual(
            category_service.get_category_names_for_nature(MediaNature.SPORT),
            ["archive"],
        )

    def test_get_music_category_names_strict_link_only(self):
        self.assertEqual(category_service.get_music_category_names(), {"pop", "rock"})

    def test_get_general_category_names_excludes_music(self):
        self.assertEqual(
            category_service.get_general_category_names(),
            ["action", "archive", "biopic"],
        )
