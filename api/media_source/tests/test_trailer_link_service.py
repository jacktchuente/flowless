from django.test import TestCase

from media_source.constants import MediaProgrammingRole
from media_source.models import MediaCollection, MediaContainer, MediaItem, MediaSource
from media_source.services.trailer_link_service import TrailerLinkService
from project_ops.constants import AnalyzeStatus


class TrailerLinkServiceTests(TestCase):
    def setUp(self):
        self.media_source = MediaSource.objects.create(name="jellyfin", is_active=True)
        self.main_collection = MediaCollection.objects.create(
            name="Movies",
            external_id="col-main",
            media_source=self.media_source,
            is_active=True,
            hash_data="x",
        )
        self.trailer_collection = MediaCollection.objects.create(
            name="Trailers",
            external_id="col-trailers",
            media_source=self.media_source,
            is_active=True,
            programming_role=MediaProgrammingRole.TRAILER,
            hash_data="x",
        )
        self.target = self._create_container(
            collection=self.main_collection,
            external_id="jelly-guid-42",
            title="The Matrix",
            provider_ids={"tmdb": "603", "imdb": "tt0133093"},
        )

    def _create_container(self, *, collection, external_id, title, provider_ids=None):
        return MediaContainer.objects.create(
            original_data_hash=f"hash-{external_id}",
            external_id=external_id,
            title=title,
            provider_ids=provider_ids or {},
            media_source=self.media_source,
            media_collection=collection,
            analyze_status=AnalyzeStatus.COMPLETE,
        )

    def _create_item(self, container, *, external_id, duration_seconds=60):
        return MediaItem.objects.create(
            original_data_hash=f"hash-{external_id}",
            container=container,
            title=f"item {external_id}",
            duration_seconds=duration_seconds,
            media_source=self.media_source,
            external_id=external_id,
        )

    def test_matches_trailer_folder_named_with_jellyfin_guid(self):
        folder = self._create_container(
            collection=self.trailer_collection,
            external_id="trailer-folder-1",
            title="jelly-guid-42",
        )
        trailer = self._create_item(folder, external_id="trailer-1")

        found = list(TrailerLinkService().find_trailer_items(self.target))

        self.assertEqual([trailer.id], [item.id for item in found])

    def test_matches_trailer_folder_named_with_raw_provider_id(self):
        folder = self._create_container(
            collection=self.trailer_collection,
            external_id="trailer-folder-2",
            title="603",
        )
        trailer = self._create_item(folder, external_id="trailer-2")

        found = list(TrailerLinkService().find_trailer_items(self.target))

        self.assertIn(trailer.id, [item.id for item in found])

    def test_matches_trailer_folder_named_with_prefixed_provider_id_case_insensitive(self):
        folder = self._create_container(
            collection=self.trailer_collection,
            external_id="trailer-folder-3",
            title="Tmdb-603",
        )
        trailer = self._create_item(folder, external_id="trailer-3")

        found = list(TrailerLinkService().find_trailer_items(self.target))

        self.assertIn(trailer.id, [item.id for item in found])

    def test_no_match_returns_empty(self):
        folder = self._create_container(
            collection=self.trailer_collection,
            external_id="trailer-folder-4",
            title="unrelated-id",
        )
        self._create_item(folder, external_id="trailer-4")

        self.assertEqual(list(TrailerLinkService().find_trailer_items(self.target)), [])

    def test_items_without_duration_are_excluded(self):
        folder = self._create_container(
            collection=self.trailer_collection,
            external_id="trailer-folder-5",
            title="jelly-guid-42",
        )
        MediaItem.objects.create(
            original_data_hash="hash-no-duration",
            container=folder,
            title="broken trailer",
            duration_seconds=None,
            media_source=self.media_source,
            external_id="trailer-5",
        )

        self.assertEqual(list(TrailerLinkService().find_trailer_items(self.target)), [])

    def test_inactive_trailer_collection_is_ignored(self):
        self.trailer_collection.is_active = False
        self.trailer_collection.save(update_fields=["is_active"])
        folder = self._create_container(
            collection=self.trailer_collection,
            external_id="trailer-folder-6",
            title="jelly-guid-42",
        )
        self._create_item(folder, external_id="trailer-6")

        self.assertEqual(list(TrailerLinkService().find_trailer_items(self.target)), [])

    def test_find_target_for_trailer_container(self):
        folder = self._create_container(
            collection=self.trailer_collection,
            external_id="trailer-folder-7",
            title="tmdb-603",
        )

        found = TrailerLinkService().find_target_for_trailer_container(folder)

        self.assertIsNotNone(found)
        self.assertEqual(found.id, self.target.id)
