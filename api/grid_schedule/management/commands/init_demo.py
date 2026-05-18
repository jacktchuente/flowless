from datetime import time

from django.core.management.base import BaseCommand
from django.db import transaction

from media_source.constants import MediaContainerKind, MediaNature
from tv_channel.constants import DayPart, BlockType, CutStrategy
from tv_channel.models import (
    Catalog,
    EditorialLine,
    Grid,
    GridBlock,
    TvChannel,
)


class Command(BaseCommand):
    help = "Initialise des données de démonstration pour la partie TV."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-blocks",
            action="store_true",
            help="Supprime puis recrée les blocs de la grille.",
        )
        parser.add_argument(
            "--deactivate-other-playouts",
            action="store_true",
            help="Désactive les autres playouts actifs de la chaîne avant de créer le playout démo.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        reset_blocks = options["reset_blocks"]
        deactivate_other_playouts = options["deactivate_other_playouts"]

        catalog, _ = Catalog.objects.update_or_create(
            name="demo",
            defaults={
                "description": "Catalogue de démonstration pour la génération de chaînes.",
            },
        )

        editorial_line, _ = EditorialLine.objects.update_or_create(
            name="police_family",
            defaults={
                "description": "Chaîne thématique policière accessible au grand public.",
                "positioning": "thematic",
                "target_audience": "family",
                "tone": "accessible",

                # Contraintes dures
                "allowed_categories": ["policier", "enquete", "thriller", "documentaire"],
                "forbidden_categories": ["horreur", "gore", "violent_extreme"],
                "allowed_natures": [
                    MediaNature.FICTION,
                    MediaNature.DOCUMENTARY,
                ],
                "allowed_container_kinds": [
                    MediaContainerKind.MOVIE,
                    MediaContainerKind.SERIES,
                ],
                "min_age": 0,
                "max_age": 12,
                "min_duration_seconds": 10 * 60,
                "max_duration_seconds": 180 * 60,
                "countries": ["FR", "US"],
                "audio_languages": ["fr"],
                "subtitle_languages": ["fr"],
                "min_rating_score": 50.0,

                # Préférences souples / scoring
                "preferred_categories": ["policier", "enquete"],
                "preferred_natures": [MediaNature.FICTION],
                "preferred_container_kinds": [
                    MediaContainerKind.SERIES,
                    MediaContainerKind.MOVIE,
                ],
                "category_weights": {
                    "policier": 1.0,
                    "enquete": 0.9,
                    "thriller": 0.5,
                    "documentaire": 0.3,
                },
                "nature_weights": {
                    str(MediaNature.FICTION.value): 1.0,
                    str(MediaNature.DOCUMENTARY.value): 0.4,
                },
                "container_kind_weights": {
                    str(MediaContainerKind.SERIES.value): 1.0,
                    str(MediaContainerKind.MOVIE.value): 0.7,
                },

                # Priorité des dayparts
                "daypart_priorities": {
                    DayPart.EARLY_MORNING.value: 10,
                    DayPart.MORNING.value: 20,
                    DayPart.DAYTIME.value: 40,
                    DayPart.ACCESS.value: 75,
                    DayPart.PRIME_TIME.value: 100,
                    DayPart.LATE_NIGHT.value: 25,
                    DayPart.OVERNIGHT.value: 10,
                },
                "daypart_preferences": {
                    DayPart.DAYTIME.value: {
                        "preferred_categories": ["policier", "enquete"],
                        "preferred_container_kinds": [MediaContainerKind.SERIES],
                        "min_rating_score": 45,
                    },
                    DayPart.PRIME_TIME.value: {
                        "preferred_categories": ["policier", "thriller"],
                        "preferred_container_kinds": [
                            MediaContainerKind.MOVIE,
                            MediaContainerKind.SERIES,
                        ],
                        "min_rating_score": 65,
                    },
                    DayPart.LATE_NIGHT.value: {
                        "preferred_categories": ["thriller", "enquete"],
                        "preferred_container_kinds": [MediaContainerKind.SERIES],
                        "min_rating_score": 50,
                    },
                },
            },
        )

        channel, _ = TvChannel.objects.update_or_create(
            name="PolarTV",
            defaults={
                "catalog": catalog,
                "is_enabled": True,
            },
        )

        grid, _ = Grid.objects.update_or_create(
            name="demo_weekday",
            defaults={
                "description": "Grille de démonstration simple pour une chaîne thématique.",
                "starts_at": time(6, 0),
                "stops_at": time(2, 0),
            },
        )

        # Compatibilité si ton modèle TvChannel a encore des champs éditoriaux / grille
        channel_updates = {}
        if hasattr(channel, "editorial_line_id"):
            channel_updates["editorial_line"] = editorial_line
        if hasattr(channel, "grid_id"):
            channel_updates["grid"] = grid
        if channel_updates:
            for field_name, value in channel_updates.items():
                setattr(channel, field_name, value)
            channel.save()

        if reset_blocks:
            grid.blocks.all().delete()

        block_definitions = [
            {
                "name": "Early Morning",
                "order": 1,
                "daypart": DayPart.EARLY_MORNING,
                "block_type": BlockType.EDITORIAL,
                "starts_at": time(6, 0),
                "ends_at": time(9, 0),
                "priority": 20,
                "min_items": 2,
                "max_items": 6,
                "min_item_duration_seconds": 15 * 60,
                "max_item_duration_seconds": 60 * 60,
                "live_allowed": False,
                "replay_allowed": True,
                "mandatory": True,
                "can_start_late": False,
                "can_end_late": False,
                "max_delay_minutes": 0,
                "cut_strategy": CutStrategy.REDUCE_FILLERS,
            },
            {
                "name": "Daytime",
                "order": 2,
                "daypart": DayPart.DAYTIME,
                "block_type": BlockType.EDITORIAL,
                "starts_at": time(9, 0),
                "ends_at": time(18, 0),
                "priority": 40,
                "min_items": 4,
                "max_items": 12,
                "min_item_duration_seconds": 20 * 60,
                "max_item_duration_seconds": 90 * 60,
                "live_allowed": False,
                "replay_allowed": True,
                "mandatory": True,
                "can_start_late": True,
                "can_end_late": False,
                "max_delay_minutes": 10,
                "cut_strategy": CutStrategy.REDUCE_FILLERS,
            },
            {
                "name": "Access",
                "order": 3,
                "daypart": DayPart.ACCESS,
                "block_type": BlockType.PROTECTED,
                "starts_at": time(18, 0),
                "ends_at": time(20, 30),
                "priority": 80,
                "min_items": 2,
                "max_items": 4,
                "min_item_duration_seconds": 20 * 60,
                "max_item_duration_seconds": 75 * 60,
                "live_allowed": False,
                "replay_allowed": False,
                "mandatory": True,
                "can_start_late": True,
                "can_end_late": False,
                "max_delay_minutes": 5,
                "cut_strategy": CutStrategy.DROP_LOW_PRIORITY_ITEMS,
            },
            {
                "name": "Prime Time",
                "order": 4,
                "daypart": DayPart.PRIME_TIME,
                "block_type": BlockType.PROTECTED,
                "starts_at": time(20, 30),
                "ends_at": time(23, 0),
                "priority": 100,
                "min_items": 1,
                "max_items": 2,
                "min_item_duration_seconds": 75 * 60,
                "max_item_duration_seconds": 150 * 60,
                "live_allowed": False,
                "replay_allowed": False,
                "mandatory": True,
                "can_start_late": True,
                "can_end_late": True,
                "max_delay_minutes": 15,
                "cut_strategy": CutStrategy.PROTECT_BLOCK,
            },
            {
                "name": "Late Night",
                "order": 5,
                "daypart": DayPart.LATE_NIGHT,
                "block_type": BlockType.EDITORIAL,
                "starts_at": time(23, 0),
                "ends_at": time(2, 0),
                "priority": 25,
                "min_items": 1,
                "max_items": 6,
                "min_item_duration_seconds": 20 * 60,
                "max_item_duration_seconds": 120 * 60,
                "live_allowed": False,
                "replay_allowed": True,
                "mandatory": False,
                "can_start_late": True,
                "can_end_late": True,
                "max_delay_minutes": 30,
                "cut_strategy": CutStrategy.DROP_ENTIRE_BLOCK_TAIL,
            },
        ]

        for block_data in block_definitions:
            defaults = {
                key: value
                for key, value in block_data.items()
                if key in {
                    "order",
                    "daypart",
                    "starts_at",
                    "ends_at",
                    "priority",
                    "min_items",
                    "max_items",
                    "min_item_duration_seconds",
                    "max_item_duration_seconds",
                    "post_roll_filler_policy",
                    "mandatory",
                }
            }
            defaults.setdefault("post_roll_filler_policy", "rounded_5mn")
            GridBlock.objects.update_or_create(
                grid=grid,
                name=block_data["name"],
                defaults=defaults,
            )



        self.stdout.write(self.style.SUCCESS("Démo TV initialisée."))
        self.stdout.write(f"Catalog: {catalog.name}")
        self.stdout.write(f"EditorialLine: {editorial_line.name}")
        self.stdout.write(f"TvChannel: {channel.name}")
        self.stdout.write(f"Grid: {grid.name}")
        self.stdout.write(f"Blocks: {grid.blocks.count()}")
