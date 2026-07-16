from unittest import mock

from django.test import TestCase

from media_source.constants import MediaContainerKind
from media_source.models import MediaCollection, MediaContainer, MediaSource
from project_ops.services.init_built_in_data import Initializer
from rule_engine.services.category_normalizer.category_normalizer_with_llm import (
    CategoryNormalizerWithLlm,
)
from rule_engine.services.category_normalizer.category_normalizer_without_llm import (
    CategoryNormalizerWithoutLlm,
)


class MusicCategoryFixtureMixin:
    @classmethod
    def setUpTestData(cls):
        Initializer.init_categories()
        cls.media_source = MediaSource.objects.create(name="jellyfin", is_active=True)
        cls.music_collection = MediaCollection.objects.create(
            name="Music videos",
            external_id="col-mv",
            media_source=cls.media_source,
            is_active=True,
            container_kind=MediaContainerKind.MUSIC_VIDEO_RELEASE,
            hash_data="x",
        )
        cls.series_collection = MediaCollection.objects.create(
            name="Shows",
            external_id="col-shows",
            media_source=cls.media_source,
            is_active=True,
            container_kind=MediaContainerKind.SERIES,
            hash_data="x",
        )

    def _container(self, *, collection, title, genres=None, description=None):
        return MediaContainer.objects.create(
            original_data_hash=f"hash-{title}",
            external_id=f"ext-{title}",
            title=title,
            description=description,
            media_source=self.media_source,
            media_collection=collection,
            genres=genres or [],
        )


class MusicCategoryRulesTests(MusicCategoryFixtureMixin, TestCase):
    def test_synthpop_genre_maps_to_pop_on_a_music_container(self):
        container = self._container(
            collection=self.music_collection, title="Some clip", genres=["Synthpop"]
        )

        categories = CategoryNormalizerWithoutLlm(container).get_categories()

        self.assertIn("pop", categories)

    def test_death_metal_genre_maps_to_metal(self):
        container = self._container(
            collection=self.music_collection, title="Loud clip", genres=["Death Metal"]
        )

        categories = CategoryNormalizerWithoutLlm(container).get_categories()

        self.assertIn("metal", categories)

    def test_generic_music_category_stays_for_non_music_containers(self):
        # Un film-concert dans une bibliotheque non musicale garde "music".
        container = self._container(
            collection=self.series_collection, title="Live concert", genres=["Concert"]
        )

        categories = CategoryNormalizerWithoutLlm(container).get_categories()

        self.assertIn("music", categories)

    def test_music_container_gets_genres_only(self):
        container = self._container(
            collection=self.music_collection,
            title="Thriller",
            genres=["Pop", "Concert"],
            description="A scary horror story with zombies in space.",
        )

        categories = CategoryNormalizerWithoutLlm(container).get_categories()

        self.assertIn("pop", categories)
        # "music" est redondant avec le kind du container: jamais assignee ici.
        self.assertNotIn("music", categories)
        for excluded in ("horror", "science-fiction", "suspense"):
            self.assertNotIn(excluded, categories)

    def test_series_never_gets_music_genres_even_from_genre_field(self):
        container = self._container(
            collection=self.series_collection,
            title="A rock band story",
            genres=["Rock", "Drama"],
        )

        categories = CategoryNormalizerWithoutLlm(container).get_categories()

        self.assertNotIn("rock", categories)

    def test_common_words_in_series_description_do_not_match_genres(self):
        container = self._container(
            collection=self.series_collection,
            title="Farm life",
            description="A family drama set in the country, in an old house full of pop culture and heavy metal doors.",
        )

        categories = CategoryNormalizerWithoutLlm(container).get_categories()

        for genre in ("country", "pop", "metal", "electronic"):
            self.assertNotIn(genre, categories)


class LlmNormalizerVocabularySplitTests(MusicCategoryFixtureMixin, TestCase):
    def _mock_llm(self, response_text):
        fake_service = mock.Mock()
        fake_service.complete.return_value = mock.Mock(
            content=f"###response###\n{response_text}"
        )
        return mock.patch(
            "rule_engine.services.category_normalizer.category_normalizer_with_llm.LLMService",
            return_value=fake_service,
        ), fake_service

    def test_music_container_uses_the_music_prompt_and_restricted_vocabulary(self):
        container = self._container(
            collection=self.music_collection,
            title="Daft Punk - Around the World",
            genres=["House"],
        )
        patcher, fake_service = self._mock_llm("music, electronic")

        with patcher:
            categories = CategoryNormalizerWithLlm(container).get_categories()

        prompt = fake_service.complete.call_args.kwargs["prompt"]
        self.assertIn("music categorization engine", prompt)
        self.assertIn('"Daft Punk"', prompt)
        self.assertIn('"Around the World"', prompt)
        self.assertNotIn("western", prompt)
        # "music" hors vocabulaire des containers musicaux: seuls les genres restent.
        self.assertEqual(categories, ["electronic"])

    def test_music_response_outside_vocabulary_is_filtered(self):
        container = self._container(
            collection=self.music_collection, title="Some clip", genres=["Pop"]
        )
        patcher, _ = self._mock_llm("pop, romance, action")

        with patcher:
            categories = CategoryNormalizerWithLlm(container).get_categories()

        self.assertEqual(categories, ["pop"])

    def test_series_prompt_does_not_expose_music_genres(self):
        container = self._container(
            collection=self.series_collection,
            title="A rock band story",
            genres=["Drama"],
        )
        patcher, fake_service = self._mock_llm("emotion")

        with patcher:
            categories = CategoryNormalizerWithLlm(container).get_categories()

        prompt = fake_service.complete.call_args.kwargs["prompt"]
        self.assertIn("media categorization engine", prompt)
        self.assertNotIn("hip-hop", prompt)
        self.assertNotIn("variete-francaise", prompt)
        self.assertIn("music", prompt)  # la categorie generique reste disponible
        self.assertEqual(categories, ["emotion"])
