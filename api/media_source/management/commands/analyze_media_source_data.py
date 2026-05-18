from django.core.management.base import BaseCommand

from media_source.tasks import analyze_media_source_data


class Command(BaseCommand):
    help = "Execute media_source.tasks.analyze_media_source_data synchronously."

    def add_arguments(self, parser):
        parser.add_argument("media_source_id", type=int)

    def handle(self, *args, **options):
        analyze_media_source_data(options["media_source_id"])

