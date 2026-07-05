from django.test import TestCase

from editorial_planning.models import EditorialSegmentMembership, EditorialSegmentMembershipStatus
from editorial_planning.services.generation_service import EditorialPlanningGenerationService
from editorial_planning.services.matching_service import EditorialPlanningMatchingService
from media_source.constants import MediaContainerKind, MediaNature
from media_source.models import MediaCollection, MediaContainer, MediaSource
from project_ops.constants import AnalyzeStatus
from tv_channel.models import Catalog


class EditorialPlanningMatchingServiceTests(TestCase):
    def setUp(self):
        self.catalog = Catalog.objects.create(name="Test catalog")
        self.media_source = MediaSource.objects.create(name="jellyfin", is_active=True)
        self.collection = MediaCollection.objects.create(
            name="Cartoons",
            external_id="col-1",
            media_source=self.media_source,
            is_active=True,
            nature=MediaNature.FICTION,
            container_kind=MediaContainerKind.SERIES,
            hash_data="x",
        )

    def _create_container(self, index: int, categories: list[str], nature_suffix: str) -> MediaContainer:
        return MediaContainer.objects.create(
            original_data_hash=f"hash-{nature_suffix}-{index}",
            external_id=f"ext-{nature_suffix}-{index}",
            title=f"{nature_suffix} show {index}",
            media_source=self.media_source,
            media_collection=self.collection,
            analyze_status=AnalyzeStatus.COMPLETE,
            categories=categories,
            item_count=10,
            total_duration_seconds=10 * 1500,
            audio_languages=["fr"],
            countries=["FR"],
            overall_rating_score=7.0,
        )

    def _generate_run(self):
        for index in range(6):
            self._create_container(index, ["animation", "kids"], "cartoon")
        for index in range(6):
            self._create_container(index, ["crime", "thriller"], "crime")

        return EditorialPlanningGenerationService(
            catalog=self.catalog,
            media_collection_ids=[self.collection.id],
        ).generate()

    def test_match_new_media_attaches_new_containers_to_existing_segments(self):
        run = self._generate_run()
        self.assertGreater(run.segments.count(), 0)
        baseline_membership_count = EditorialSegmentMembership.objects.count()

        new_container = self._create_container(99, ["animation", "kids"], "cartoon")

        result = EditorialPlanningMatchingService(run=run).match_new_media()

        self.assertEqual(result.evaluated_count, 1)
        self.assertGreater(EditorialSegmentMembership.objects.count(), baseline_membership_count)
        membership = EditorialSegmentMembership.objects.get(media_container=new_container, is_primary=True)
        self.assertEqual(membership.segment.run_id, run.id)
        self.assertIn(
            membership.status,
            (
                EditorialSegmentMembershipStatus.ACCEPTED,
                EditorialSegmentMembershipStatus.SECONDARY,
                EditorialSegmentMembershipStatus.AMBIGUOUS,
            ),
        )

        run.refresh_from_db()
        history = run.diagnostics.get("incremental_matching")
        self.assertTrue(history)
        self.assertEqual(history[-1]["evaluated_count"], 1)

    def test_match_new_media_ignores_already_matched_containers(self):
        run = self._generate_run()
        result = EditorialPlanningMatchingService(run=run).match_new_media()
        self.assertEqual(result.evaluated_count, 0)
        self.assertEqual(result.created_membership_count, 0)
