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
        seed = Initializer._load_category_seed(file_path)
        category_names = list(dict.fromkeys(
            category
            for nature in seed["natures"]
            for category in nature["categories"]
        ))
        rules_by_category = {name: [] for name in category_names}
        for rule in seed["rules"]:
            rules_by_category[rule["category"]].append({
                "fields": rule["fields"],
                "values": rule["values"],
            })

        with transaction.atomic():
            categories = Category.objects.bulk_create(
                [Category(category=name) for name in category_names]
            )
            category_by_name = {category.category: category for category in categories}
            CategoryNature.objects.bulk_create([
                CategoryNature(category=category_by_name[category], nature=nature["value"])
                for nature in seed["natures"]
                for category in nature["categories"]
            ])
            CategoryRule.objects.bulk_create([
                CategoryRule(
                    category=category_by_name[name],
                    rules=rules_by_category[name],
                )
                for name in category_names
            ])

    @staticmethod
    def _load_category_seed(file_path) -> list[dict]:
        # Contrairement aux presets de grille, ce fichier definit le vocabulaire
        # canonique : toute anomalie doit faire echouer l'init, pas etre ignoree.
        with file_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        if not isinstance(payload, dict):
            raise ValueError(f"{file_path.name}: top-level payload must be an object.")
        if set(payload) != {"natures", "rules"}:
            raise ValueError(
                f"{file_path.name}: top-level payload must contain exactly natures and rules."
            )

        nature_by_label = {choice.label: choice.value for choice in MediaNature}
        raw_natures = payload.get("natures")
        if not isinstance(raw_natures, list):
            raise ValueError(f"{file_path.name}: 'natures' must be a list.")

        natures = []
        seen_natures = set()
        seen_categories = set()
        for raw_nature in raw_natures:
            if not isinstance(raw_nature, dict) or set(raw_nature) != {"name", "categories"}:
                raise ValueError(
                    f"{file_path.name}: each nature must contain exactly name and categories."
                )
            name = raw_nature.get("name")
            if not isinstance(name, str) or name not in nature_by_label:
                raise ValueError(f"{file_path.name}: unknown nature: {name}.")
            if name in seen_natures:
                raise ValueError(f"{file_path.name}: duplicate nature: {name}.")
            seen_natures.add(name)

            raw_categories = raw_nature.get("categories")
            if not isinstance(raw_categories, list) or not all(
                isinstance(category, str) and category.strip() for category in raw_categories
            ):
                raise ValueError(
                    f"{file_path.name}: categories of {name} must be a list of strings."
                )
            categories = [category.strip().lower() for category in raw_categories]
            if len(categories) != len(set(categories)):
                raise ValueError(f"{file_path.name}: duplicate category in nature {name}.")
            seen_categories.update(categories)
            natures.append({
                "name": name,
                "value": nature_by_label[name],
                "categories": categories,
            })

        if seen_natures != set(nature_by_label):
            raise ValueError(
                f"{file_path.name}: 'natures' must contain every MediaNature label: "
                f"{sorted(nature_by_label)}."
            )

        raw_rules = payload.get("rules")
        if not isinstance(raw_rules, list):
            raise ValueError(f"{file_path.name}: top-level 'rules' must be a list.")

        rules = []
        for raw_rule in raw_rules:
            if not isinstance(raw_rule, dict):
                raise ValueError(f"{file_path.name}: each rule must be an object.")
            category = raw_rule.get("category")
            if not isinstance(category, str) or category.strip().lower() not in seen_categories:
                raise ValueError(f"{file_path.name}: rule targets unknown category: {category}.")
            fields = raw_rule.get("fields")
            values = raw_rule.get("values")
            if not isinstance(fields, list) or not all(
                isinstance(field, str) and field.strip() for field in fields
            ):
                raise ValueError(f"{file_path.name}: rule fields must be a list of strings.")
            if not isinstance(values, list) or not all(
                isinstance(value, str) and value.strip() for value in values
            ):
                raise ValueError(f"{file_path.name}: rule values must be a list of strings.")
            rules.append({
                "category": category.strip().lower(),
                "fields": fields,
                "values": values,
            })

        return {"natures": natures, "rules": rules}

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
