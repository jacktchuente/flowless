from django.db import transaction

from media_source.models import MediaSource
from tv_channel.models import Catalog, FillerPolicy


class DemoDataResetService:
    DEMO_MEDIA_SOURCE_NAME = "Showcase Library"
    DEMO_CATALOG_NAME = "Prime Time Showcase"
    DEMO_FILLER_POLICIES = [
        "Short Channel ID",
        "Late Night Bridge",
    ]

    @classmethod
    def run(cls):
        Catalog.objects.filter(name=cls.DEMO_CATALOG_NAME).delete()
        MediaSource.objects.filter(name=cls.DEMO_MEDIA_SOURCE_NAME).delete()
        FillerPolicy.objects.filter(name__in=cls.DEMO_FILLER_POLICIES).delete()
