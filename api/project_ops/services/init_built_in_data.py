import json
import logging
from datetime import time

from django.conf import settings
from django.db import IntegrityError, transaction

from grid_layout_preset.models import FillerPolicyPreset, GridBlockPreset, GridLayoutPreset
from media_source.constants import MediaNature
from rule_engine.models import Category, CategoryNature, CategoryRule

logger = logging.getLogger(__name__)


class Initializer:

    @staticmethod
    def init_categories():
        # Garde-fou tout-ou-rien : la BDD est la source de verite du vocabulaire,
        # le seed ne doit jamais ecraser ou completer des categories editees.
        if Category.objects.exists():
            logger.info("Categories already present, skipping built-in category seed.")
            return

        file_path = settings.BASE_DIR / "project_ops" / "built_in_data" / "categories.json"
        entries = Initializer._load_category_seed(file_path)

        with transaction.atomic():
            categories = Category.objects.bulk_create(
                [Category(category=entry["name"]) for entry in entries]
            )
            category_by_name = {category.category: category for category in categories}
            CategoryNature.objects.bulk_create([
                CategoryNature(category=category_by_name[entry["name"]], nature=nature)
                for entry in entries
                for nature in entry["natures"]
            ])
            CategoryRule.objects.bulk_create([
                CategoryRule(category=category_by_name[entry["name"]], rules=entry["rules"])
                for entry in entries
            ])

    @staticmethod
    def _load_category_seed(file_path) -> list[dict]:
        # Contrairement aux presets de grille, ce fichier definit le vocabulaire
        # canonique : toute anomalie doit faire echouer l'init, pas etre ignoree.
        with file_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        if not isinstance(payload, dict):
            raise ValueError(f"{file_path.name}: top-level payload must be an object.")

        nature_by_label = {choice.label: choice.value for choice in MediaNature}
        declared_natures = payload.get("natures")
        if not isinstance(declared_natures, list) or set(declared_natures) != set(nature_by_label):
            raise ValueError(
                f"{file_path.name}: 'natures' must list every MediaNature label: "
                f"{sorted(nature_by_label)}."
            )

        raw_entries = payload.get("categories")
        if not isinstance(raw_entries, list):
            raise ValueError(f"{file_path.name}: 'categories' must be a list.")

        entries = []
        seen_names = set()
        for raw_entry in raw_entries:
            if not isinstance(raw_entry, dict):
                raise ValueError(f"{file_path.name}: each category entry must be an object.")
            name = raw_entry.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"{file_path.name}: category entry without a valid name.")
            name = name.strip().lower()
            if name in seen_names:
                raise ValueError(f"{file_path.name}: duplicate category name: {name}.")
            seen_names.add(name)

            natures = raw_entry.get("natures", [])
            if not isinstance(natures, list):
                raise ValueError(f"{file_path.name}: 'natures' of {name} must be a list.")
            unknown = [label for label in natures if label not in nature_by_label]
            if unknown:
                raise ValueError(f"{file_path.name}: unknown natures for {name}: {unknown}.")

            rules = raw_entry.get("rules", [])
            if not isinstance(rules, list):
                raise ValueError(f"{file_path.name}: 'rules' of {name} must be a list.")

            entries.append({
                "name": name,
                # natures vides = valable pour toutes les natures (aucun lien cree).
                "natures": [nature_by_label[label] for label in natures],
                "rules": rules,
            })
        return entries

    @staticmethod
    def init_grid_layout_presets():
        directory = settings.BASE_DIR / "project_ops" / "built_in_data" / "grid_presets"
        if not directory.exists():
            logger.warning("Grid preset directory does not exist: %s", directory)
            return

        for file_path in sorted(directory.glob("*.json")):
            Initializer._load_grid_layout_presets_from_file(file_path)

    @staticmethod
    def _load_grid_layout_presets_from_file(file_path):
        with file_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        if not isinstance(payload, list):
            logger.warning("Skipping invalid grid preset file %s: top-level payload must be a list", file_path.name)
            return

        for preset_payload in payload:
            Initializer._create_grid_layout_preset_from_payload(file_path.name, preset_payload)

    @staticmethod
    def _create_grid_layout_preset_from_payload(file_name: str, payload: dict):
        if not isinstance(payload, dict):
            logger.warning("Skipping invalid grid preset entry in %s: entry must be an object", file_name)
            return

        preset_name = payload.get("name")
        if not isinstance(preset_name, str) or not preset_name.strip():
            logger.warning("Skipping invalid grid preset entry in %s: missing preset name", file_name)
            return

        try:
            preset = GridLayoutPreset.objects.create(
                name=preset_name,
                description=payload.get("description", "") or "",
            )
        except IntegrityError:
            logger.warning(
                "Skipping grid preset in %s because of a database uniqueness conflict: %s",
                file_name,
                preset_name,
            )
            return

        blocks = payload.get("blocks", [])
        if not isinstance(blocks, list):
            logger.warning("Skipping invalid blocks payload in %s for preset %s", file_name, preset_name)
            return

        for block_payload in blocks:
            Initializer._create_grid_block_preset_from_payload(file_name, preset, block_payload)

    @staticmethod
    def _create_grid_block_preset_from_payload(file_name: str, preset: GridLayoutPreset, payload: dict):
        if not isinstance(payload, dict):
            logger.warning("Skipping invalid block entry in %s for preset %s", file_name, preset.name)
            return

        filler_policy = Initializer._get_or_create_filler_policy_preset(
            file_name=file_name,
            payload=payload.get("post_filler_policy"),
        )

        GridBlockPreset.objects.create(
            grid_layout=preset,
            starts_at=Initializer._parse_time(payload.get("starts_at")),
            ends_at=Initializer._parse_time(payload.get("ends_at")),
            priority=payload.get("priority", 50),
            min_items=payload.get("min_items", 1),
            max_items=payload.get("max_items", 1),
            min_duration_seconds_per_item=payload.get("min_duration_seconds_per_item"),
            max_duration_seconds_per_item=payload.get("max_duration_seconds_per_item"),
            allowed=payload.get("allowed", {}),
            preferred=payload.get("preferred", {}),
            forbidden=payload.get("forbidden", {}),
            post_filler_policy=filler_policy
        )

    @staticmethod
    def _get_or_create_filler_policy_preset(file_name: str, payload: dict | None):
        if not payload:
            return None
        if not isinstance(payload, dict):
            logger.warning("Skipping invalid filler policy in %s: payload must be an object", file_name)
            return None

        policy_name = payload.get("name")
        if not isinstance(policy_name, str) or not policy_name.strip():
            logger.warning("Skipping invalid filler policy in %s: missing name", file_name)
            return None

        return FillerPolicyPreset.objects.create(
            name=policy_name,
            duration_seconds=payload.get("duration_seconds", 180),
        )

    @staticmethod
    def _parse_time(value: str) -> time:
        if not isinstance(value, str):
            raise ValueError("Invalid time value in built-in grid preset data.")
        hour, minute, second = value.split(":")
        return time(hour=int(hour), minute=int(minute), second=int(second))
