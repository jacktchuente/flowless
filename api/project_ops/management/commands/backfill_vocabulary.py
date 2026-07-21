from django.core.management.base import BaseCommand

from rule_engine.models import VocabularyEntry
from rule_engine.services import vocabulary_service


class Command(BaseCommand):
    help = "Rebuild the editorial-rule vocabulary from active media containers."

    def handle(self, *args, **options):
        vocabulary_service.rebuild()

        for axis in vocabulary_service.VOCABULARY_AXES:
            count = VocabularyEntry.objects.filter(axis=axis).count()
            self.stdout.write(f"{axis}: {count} entries")

        self.stdout.write(self.style.SUCCESS("Vocabulary backfill done."))
