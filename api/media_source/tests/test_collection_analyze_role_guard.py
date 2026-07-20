from unittest.mock import patch

from rest_framework.test import APITestCase

from media_source.constants import MediaProgrammingRole
from media_source.models import MediaCollection, MediaContainer, MediaSource
from media_source.services.media_collection_service import MediaCollectionService


class CollectionAnalyzeRoleGuardTests(APITestCase):
    def setUp(self):
        self.media_source = MediaSource.objects.create(name="jellyfin", is_active=True)

    def _collection(self, *, role):
        return MediaCollection.objects.create(
            name="col",
            external_id=f"col-{role}",
            media_source=self.media_source,
            is_active=True,
            programming_role=role,
            hash_data="x",
        )

    def test_analyze_endpoint_rejects_non_main_roles(self):
        for role in (None, MediaProgrammingRole.TRAILER, MediaProgrammingRole.FILLER):
            collection = self._collection(role=role)
            with patch("media_source.views.media_collection_views.analyze_media_collection_data") as task_mock:
                response = self.client.post(f"/api/media-collection/{collection.id}/analyze/", {}, format="json")
            self.assertEqual(response.status_code, 400, role)
            task_mock.delay.assert_not_called()

    def test_analyze_endpoint_accepts_main_role(self):
        collection = self._collection(role=MediaProgrammingRole.MAIN)
        with patch("media_source.views.media_collection_views.analyze_media_collection_data") as task_mock:
            response = self.client.post(f"/api/media-collection/{collection.id}/analyze/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        task_mock.delay.assert_called_once()

    def _container(self, collection):
        return MediaContainer.objects.create(
            original_data_hash="h1",
            external_id=f"cont-{collection.id}",
            title="t",
            media_source=self.media_source,
            media_collection=collection,
        )

    def test_pipeline_disables_llm_for_non_main_collections(self):
        collection = self._collection(role=MediaProgrammingRole.TRAILER)
        self._container(collection)
        with patch(
            "media_source.services.media_collection_service.MediaContainerService.normalize_data"
        ) as normalize_mock:
            normalize_mock.side_effect = lambda use_llm: MediaContainer.objects.get(
                media_collection=collection
            )
            MediaCollectionService(collection).analyze_collection_data(use_llm=True)
        normalize_mock.assert_called_once_with(use_llm=False)

    def test_pipeline_keeps_llm_for_main_collections(self):
        collection = self._collection(role=MediaProgrammingRole.MAIN)
        self._container(collection)
        with patch(
            "media_source.services.media_collection_service.MediaContainerService.normalize_data"
        ) as normalize_mock:
            normalize_mock.side_effect = lambda use_llm: MediaContainer.objects.get(
                media_collection=collection
            )
            MediaCollectionService(collection).analyze_collection_data(use_llm=True)
        normalize_mock.assert_called_once_with(use_llm=True)
