import logging

from rule_engine.services.catalog_channel_generator.catalog_channel_generator_with_llm import \
    CatalogChannel, CatalogChannelGenerationError, CatalogChannelGeneratorWithLlm
from django.conf import settings
from tv_channel.models import Catalog, TvChannel

logger = logging.getLogger(__name__)


class CatalogService:

    def __init__(self, catalog: Catalog):
        self.catalog = catalog

    def generate_channels(self, reboot: bool):
        if reboot:
            TvChannel.objects.filter(catalog=self.catalog).delete()

        target_channel_count = min(
            self.catalog.number_of_channels,
            getattr(settings, "CATALOG_GENERATOR_MAX_CHANNELS", self.catalog.number_of_channels),
        )
        if target_channel_count <= 0:
            return

        existing_catalog_channels = list(
            TvChannel.objects
            .filter(catalog=self.catalog)
            .values("name", "description", "specification")
        )
        global_channel_names = list(TvChannel.objects.values_list("name", flat=True))
        service = CatalogChannelGeneratorWithLlm(catalog=self.catalog)

        generated_channels: list[CatalogChannel] = []
        current_channels = [
            {
                "name": element["name"],
                "description": element["description"] or "",
                "specification": element["specification"] or "",
            }
            for element in existing_catalog_channels
        ]
        remaining = max(target_channel_count - len(current_channels), 0)

        for _ in range(remaining):
            try:
                channel_data = service.get_next_channel(
                    forbidden_channel_names=global_channel_names,
                    existing_channels=current_channels,
                    target_channel_count=target_channel_count,
                )
            except CatalogChannelGenerationError as exc:
                logger.warning(
                    "CatalogService.generate_channels stopped early catalog_id=%s generated=%s target=%s error=%s",
                    self.catalog.id,
                    len(current_channels),
                    target_channel_count,
                    exc,
                )
                break
            global_channel_names.append(channel_data["name"])
            current_channels.append(channel_data)
            generated_channels.append(channel_data)

        TvChannel.objects.bulk_create(
            [
                TvChannel(
                    name=element["name"],
                    description=element["description"],
                    specification=element["specification"],
                    catalog=self.catalog,
                )
                for element in generated_channels
            ]
        )
