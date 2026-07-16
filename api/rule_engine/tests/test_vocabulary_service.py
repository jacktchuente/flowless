from django.test import TestCase

from media_source.constants import MediaContainerKind
from media_source.models import MediaCollection, MediaContainer, MediaSource
from project_ops.constants import AnalyzeStatus
from rule_engine.models import Category, VocabularyEntry
from rule_engine.services import vocabulary_service


class VocabularyServiceTests(TestCase):

    def test_get_values_routes_categories_to_category_table(self):
        Category.objects.create(category="action")
        VocabularyEntry.objects.create(axis="actors", value="Tom Hanks")

        self.assertEqual(vocabulary_service.get_values("categories"), ["action"])
        self.assertEqual(vocabulary_service.get_values("actors"), ["Tom Hanks"])

    def test_get_values_unknown_axis_raises(self):
        with self.assertRaises(ValueError):
            vocabulary_service.get_values("people")

    def test_upsert_values_is_idempotent_and_ignores_unknown_axes(self):
        mapping = {
            "actors": ["Tom Hanks", "Meg Ryan"],
            "studios": ["Warner Bros."],
            "people": ["should be ignored"],
            "countries": [None, "", 42, "France"],
        }
        vocabulary_service.upsert_values(mapping)
        vocabulary_service.upsert_values(mapping)

        self.assertEqual(
            vocabulary_service.get_values("actors"),
            ["Meg Ryan", "Tom Hanks"],
        )
        self.assertEqual(vocabulary_service.get_values("studios"), ["Warner Bros."])
        self.assertEqual(vocabulary_service.get_values("countries"), ["France"])
        self.assertFalse(VocabularyEntry.objects.filter(axis="people").exists())

    def test_search_is_multiplexed_and_limited(self):
        vocabulary_service.upsert_values({
            "actors": ["Tom Hanks", "Tommy Lee Jones"],
            "directors": ["Tom Hooper"],
            "studios": ["Warner Bros."],
        })

        results = vocabulary_service.search("tom")
        self.assertEqual(
            results,
            [
                {"axis": "actors", "value": "Tom Hanks"},
                {"axis": "actors", "value": "Tommy Lee Jones"},
                {"axis": "directors", "value": "Tom Hooper"},
            ],
        )

        self.assertEqual(len(vocabulary_service.search("tom", limit=2)), 2)
        self.assertEqual(vocabulary_service.search("zzz"), [])

    def test_rebuild_adds_missing_and_removes_orphans(self):
        media_source = MediaSource.objects.create(name="jellyfin", credentials={})
        active_collection = MediaCollection.objects.create(
            name="films",
            external_id="col-1",
            media_source=media_source,
            is_active=True,
            hash_data="x",
            container_kind=MediaContainerKind.STANDALONE_VIDEO,
        )
        inactive_collection = MediaCollection.objects.create(
            name="archives",
            external_id="col-2",
            media_source=media_source,
            is_active=False,
            hash_data="x",
        )

        MediaContainer.objects.create(
            original_data_hash="h1",
            external_id="m-1",
            title="Movie",
            media_source=media_source,
            media_collection=active_collection,
            analyze_status=AnalyzeStatus.COMPLETE,
            actors=["Tom Hanks"],
            studios=["Warner Bros."],
            countries=["France"],
            audio_languages=["fre"],
        )
        # Container d'une collection inactive : ne doit pas alimenter le vocab.
        MediaContainer.objects.create(
            original_data_hash="h2",
            external_id="m-2",
            title="Old",
            media_source=media_source,
            media_collection=inactive_collection,
            analyze_status=AnalyzeStatus.COMPLETE,
            actors=["Forgotten Actor"],
        )
        # Orphelin d'une sync precedente : doit etre purge.
        VocabularyEntry.objects.create(axis="actors", value="Removed Actor")

        vocabulary_service.rebuild()

        self.assertEqual(vocabulary_service.get_values("actors"), ["Tom Hanks"])
        self.assertEqual(vocabulary_service.get_values("studios"), ["Warner Bros."])
        self.assertEqual(vocabulary_service.get_values("countries"), ["France"])
        self.assertEqual(vocabulary_service.get_values("audio_languages"), ["fre"])
        self.assertEqual(vocabulary_service.get_values("subtitle_languages"), [])

    def test_rebuild_is_idempotent(self):
        media_source = MediaSource.objects.create(name="jellyfin", credentials={})
        collection = MediaCollection.objects.create(
            name="films",
            external_id="col-1",
            media_source=media_source,
            is_active=True,
            hash_data="x",
        )
        MediaContainer.objects.create(
            original_data_hash="h1",
            external_id="m-1",
            title="Movie",
            media_source=media_source,
            media_collection=collection,
            analyze_status=AnalyzeStatus.COMPLETE,
            directors=["Tom Hooper"],
        )

        vocabulary_service.rebuild()
        first = list(VocabularyEntry.objects.order_by("axis", "value").values_list("axis", "value"))
        vocabulary_service.rebuild()
        second = list(VocabularyEntry.objects.order_by("axis", "value").values_list("axis", "value"))

        self.assertEqual(first, second)
        self.assertEqual(first, [("directors", "Tom Hooper")])
