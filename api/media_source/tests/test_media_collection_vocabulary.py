from django.test import TestCase

from media_source.models import MediaCollection, MediaContainer, MediaSource
from media_source.services.media_collection_service import MediaCollectionService
from project_ops.constants import AnalyzeStatus
from rule_engine.services import vocabulary_service


class MediaCollectionVocabularyTests(TestCase):

    def setUp(self):
        self.media_source = MediaSource.objects.create(name="jellyfin", credentials={})
        self.media_collection = MediaCollection.objects.create(
            name="films",
            external_id="col-1",
            media_source=self.media_source,
            is_active=True,
            hash_data="x",
        )
        self.service = MediaCollectionService(self.media_collection)

    def test_manage_media_containers_populates_vocabulary(self):
        medias = [
            {
                "external_id": "m-1",
                "title": "Movie",
                "actors": ["Tom Hanks"],
                "directors": ["Tom Hooper"],
                "writers": ["Nora Ephron"],
                "creators": [],
                "studios": ["Warner Bros."],
                "countries": ["France"],
                "audio_languages": ["fre"],
                "subtitle_languages": ["eng"],
                # Champs non-axes : ne doivent pas fuiter dans le vocab.
                "people": [{"name": "Tom Hanks", "type": "Actor"}],
                "audio_languages_any": ["fre", "eng"],
            },
        ]

        self.service.manage_media_containers(medias, self.media_source)

        self.assertEqual(MediaContainer.objects.count(), 1)
        self.assertEqual(vocabulary_service.get_values("actors"), ["Tom Hanks"])
        self.assertEqual(vocabulary_service.get_values("directors"), ["Tom Hooper"])
        self.assertEqual(vocabulary_service.get_values("writers"), ["Nora Ephron"])
        self.assertEqual(vocabulary_service.get_values("creators"), [])
        self.assertEqual(vocabulary_service.get_values("studios"), ["Warner Bros."])
        self.assertEqual(vocabulary_service.get_values("countries"), ["France"])
        self.assertEqual(vocabulary_service.get_values("audio_languages"), ["fre"])
        self.assertEqual(vocabulary_service.get_values("subtitle_languages"), ["eng"])

    def test_manage_media_containers_upserts_without_duplicates(self):
        medias = [
            {
                "external_id": "m-1",
                "title": "Movie",
                "actors": ["Tom Hanks"],
            },
        ]

        self.service.manage_media_containers(medias, self.media_source)
        self.service.manage_media_containers(medias, self.media_source)

        self.assertEqual(vocabulary_service.get_values("actors"), ["Tom Hanks"])

    def test_new_container_starts_without_source_categories(self):
        self.service.manage_media_containers(
            [{
                "external_id": "m-1",
                "title": "Movie",
                "categories": ["Jellyfin category"],
                "genres": ["Horror"],
                "tags": ["Late night"],
            }],
            self.media_source,
        )

        container = MediaContainer.objects.get(external_id="m-1")
        self.assertEqual(container.categories, [])
        self.assertEqual(container.genres, ["Horror"])
        self.assertEqual(container.tags, ["Late night"])
        self.assertEqual(container.analyze_status, AnalyzeStatus.IDLE)

    def test_changed_container_is_queued_for_category_normalization(self):
        media = {"external_id": "m-1", "title": "Movie", "genres": ["Horror"]}
        self.service.manage_media_containers([media], self.media_source)
        container = MediaContainer.objects.get(external_id="m-1")
        container.categories = ["horror"]
        container.analyze_status = AnalyzeStatus.COMPLETE
        container.save(update_fields=["categories", "analyze_status"])

        changed = {**media, "title": "Movie remastered"}
        self.service.manage_media_containers([changed], self.media_source)

        container.refresh_from_db()
        self.assertEqual(container.categories, [])
        self.assertEqual(container.analyze_status, AnalyzeStatus.IDLE)
        self.assertIsNone(container.analyzed_at)

    def test_unchanged_container_keeps_normalized_categories(self):
        media = {"external_id": "m-1", "title": "Movie", "genres": ["Horror"]}
        self.service.manage_media_containers([media], self.media_source)
        container = MediaContainer.objects.get(external_id="m-1")
        container.categories = ["horror"]
        container.analyze_status = AnalyzeStatus.COMPLETE
        container.save(update_fields=["categories", "analyze_status"])

        self.service.manage_media_containers([media], self.media_source)

        container.refresh_from_db()
        self.assertEqual(container.categories, ["horror"])
        self.assertEqual(container.analyze_status, AnalyzeStatus.COMPLETE)
