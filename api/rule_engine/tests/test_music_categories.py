from django.test import TestCase

from media_source.models import MediaCollection, MediaContainer, MediaSource
from project_ops.services.init_built_in_data import Initializer
from rule_engine.services.category_normalizer.category_normalizer_without_llm import (
    CategoryNormalizerWithoutLlm,
)


class MusicCategoryRulesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Initializer.init_categories_and_category_rules()
        cls.media_source = MediaSource.objects.create(name="jellyfin", is_active=True)
        cls.collection = MediaCollection.objects.create(
            name="Music videos",
            external_id="col-mv",
            media_source=cls.media_source,
            is_active=True,
            hash_data="x",
        )

    def _container(self, *, title, genres):
        return MediaContainer.objects.create(
            original_data_hash=f"hash-{title}",
            external_id=f"ext-{title}",
            title=title,
            media_source=self.media_source,
            media_collection=self.collection,
            genres=genres,
        )

    def test_synthpop_genre_maps_to_pop_and_music(self):
        container = self._container(title="Some clip", genres=["Synthpop"])

        categories = CategoryNormalizerWithoutLlm(container).get_categories()

        self.assertIn("pop", categories)

    def test_death_metal_genre_maps_to_metal(self):
        container = self._container(title="Loud clip", genres=["Death Metal"])

        categories = CategoryNormalizerWithoutLlm(container).get_categories()

        self.assertIn("metal", categories)

    def test_generic_music_category_still_matches(self):
        container = self._container(title="Live concert", genres=["Concert"])

        categories = CategoryNormalizerWithoutLlm(container).get_categories()

        self.assertIn("music", categories)

    def test_non_music_content_gets_no_music_genre(self):
        container = self._container(title="A war story", genres=["War"])

        categories = CategoryNormalizerWithoutLlm(container).get_categories()

        for genre in ("pop", "rock", "metal", "hip-hop", "electronic"):
            self.assertNotIn(genre, categories)
