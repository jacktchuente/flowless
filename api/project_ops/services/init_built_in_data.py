import json
import logging
from datetime import time

from django.conf import settings
from django.db import IntegrityError

from grid_layout_preset.models import FillerPolicyPreset, GridBlockPreset, GridLayoutPreset
from project_ops.built_in_data.category_rule import CATEGORY_RULES
from rule_engine.models import Category, CategoryRule

logger = logging.getLogger(__name__)


class Initializer:

    @staticmethod
    def init_categories_and_category_rules():
        keys = set([element.lower() for element in CATEGORY_RULES.keys()])
        Category.objects.bulk_create([Category(category=element) for element in keys], ignore_conflicts=True)
        category_name_to_pk = {element[1]: element[0] for element in Category.objects.values_list("pk", "category")}
        for key in CATEGORY_RULES:
            pk = category_name_to_pk.get(key)
            if pk:
                # update_or_create: une regle modifiee dans le vocabulaire embarque
                # doit ecraser la version deja seedee en base.
                CategoryRule.objects.update_or_create(
                    category_id=pk,
                    defaults={"rules": CATEGORY_RULES.get(key)},
                )

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
            allowed_categories=payload.get("allowed_categories", []),
            forbidden_categories=payload.get("forbidden_categories", []),
            preferred_categories=payload.get("preferred_categories", []),
            allowed_natures=payload.get("allowed_natures", []),
            forbidden_natures=payload.get("forbidden_natures", []),
            preferred_natures=payload.get("preferred_natures", []),
            allowed_container_kinds=payload.get("allowed_container_kinds", []),
            forbidden_container_kinds=payload.get("forbidden_container_kinds", []),
            preferred_container_kinds=payload.get("preferred_container_kinds", []),
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
