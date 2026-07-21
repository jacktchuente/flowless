from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from media_source.models import MediaCollection, MediaContainer, MediaSource
from project_ops.constants import AnalyzeStatus
from rule_engine.models import VocabularyEntry


class BackfillVocabularyCommandTests(TestCase):
    def test_command_rebuilds_vocabulary_and_reports_counts(self):
        media_source = MediaSource.objects.create(name="jellyfin", credentials={})
        collection = MediaCollection.objects.create(
            name="films",
            external_id="col-1",
            media_source=media_source,
            is_active=True,
            hash_data="x",
        )
        MediaContainer.objects.create(
            original_data_hash="hash-1",
            external_id="movie-1",
            title="Movie",
            media_source=media_source,
            media_collection=collection,
            analyze_status=AnalyzeStatus.COMPLETE,
            genres=["Film noir"],
            tags=["Late night"],
            actors=["Tom Hanks"],
        )
        VocabularyEntry.objects.create(axis="genres", value="Orphan genre")
        stdout = StringIO()

        call_command("backfill_vocabulary", stdout=stdout)

        self.assertEqual(
            list(VocabularyEntry.objects.filter(axis="genres").values_list("value", flat=True)),
            ["Film noir"],
        )
        self.assertTrue(VocabularyEntry.objects.filter(axis="tags", value="Late night").exists())
        self.assertTrue(VocabularyEntry.objects.filter(axis="actors", value="Tom Hanks").exists())
        output = stdout.getvalue()
        self.assertIn("genres: 1 entries", output)
        self.assertIn("tags: 1 entries", output)
        self.assertIn("Vocabulary backfill done.", output)
