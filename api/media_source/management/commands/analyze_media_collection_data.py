from django.core.management.base import BaseCommand

from media_source.tasks import analyze_media_collection_data


class Command(BaseCommand):
    help = "Execute media_source.tasks.analyze_media_collection_data synchronously."

    def add_arguments(self, parser):
        parser.add_argument("media_collection_id", type=int)

    def handle(self, *args, **options):
        analyze_media_collection_data(options["media_collection_id"])

