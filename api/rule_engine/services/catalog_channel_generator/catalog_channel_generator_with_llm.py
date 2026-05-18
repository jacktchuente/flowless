from __future__ import annotations

import json
import re
from typing import TypedDict

from django.conf import settings

from tv_channel.models import Catalog
from utils.format_with_jinja import format_with_jinja
from utils.llm_service import LLMService


class CatalogChannel(TypedDict):
    name: str
    description: str
    specification: str


class CatalogChannelGenerationError(ValueError):
    pass


class CatalogChannelGeneratorWithLlm:
    TEMPLATE_PATH = (
        settings.BASE_DIR
        / "templates"
        / "rule_engine"
        / "prompts"
        / "catalog_channel_generator_prompt.j2"
    )

    def __init__(self, catalog: Catalog):
        self.catalog = catalog

    def get_next_channel(
        self,
        *,
        forbidden_channel_names: list[str],
        existing_channels: list[CatalogChannel],
        target_channel_count: int,
    ) -> CatalogChannel:
        retry_errors: list[str] = []
        max_attempts = max(1, int(getattr(settings, "LLM_RETRY_CATALOG_CHANNEL_GENERATION", 3)))

        for attempt in range(1, max_attempts + 1):
            prompt = self.build_prompt(
                forbidden_channel_names=forbidden_channel_names,
                existing_channels=existing_channels,
                target_channel_count=target_channel_count,
                retry_errors=retry_errors,
            )
            response = LLMService().complete(prompt=prompt)
            try:
                channel = self._parse_llm_response(response.content)
            except CatalogChannelGenerationError as exc:
                retry_errors = [str(exc)]
                if attempt == max_attempts:
                    raise
                continue

            normalized_name = channel["name"].strip()
            if normalized_name in forbidden_channel_names:
                retry_errors = [f"Channel name is forbidden or already used: {normalized_name}."]
                if attempt == max_attempts:
                    raise CatalogChannelGenerationError(retry_errors[0])
                continue

            return channel

        raise CatalogChannelGenerationError("Catalog channel generation failed.")

    def build_prompt(
        self,
        *,
        forbidden_channel_names: list[str],
        existing_channels: list[CatalogChannel],
        target_channel_count: int,
        retry_errors: list[str] | None = None,
    ) -> str:
        retry_errors = retry_errors or []
        return format_with_jinja(
            self.TEMPLATE_PATH,
            {
                "catalog_name": self.catalog.name,
                "catalog_description": self.catalog.description or "",
                "target_channel_count": target_channel_count,
                "existing_channels": existing_channels,
                "existing_count": len(existing_channels),
                "forbidden_channel_names": forbidden_channel_names,
                "retry_errors": retry_errors,
            },
        )

    def _parse_llm_response(self, content: str) -> CatalogChannel:
        if not content or not content.strip():
            raise CatalogChannelGenerationError("LLM returned an empty response.")

        match = re.search(r"<catalog_output>\s*(\{.*?\})\s*</catalog_output>", content, re.DOTALL)
        candidate = match.group(1) if match else content.strip()

        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise CatalogChannelGenerationError("LLM returned an invalid catalog JSON payload.") from exc

        if not isinstance(payload, dict):
            raise CatalogChannelGenerationError("LLM returned an invalid top-level payload.")

        raw_channel = payload.get("channel")
        if not isinstance(raw_channel, dict):
            raise CatalogChannelGenerationError("LLM returned an invalid channel payload.")

        name = raw_channel.get("name")
        description = raw_channel.get("description")
        specification = raw_channel.get("specification")

        if not isinstance(name, str) or not name.strip():
            raise CatalogChannelGenerationError("LLM returned a channel without a valid name.")
        if not isinstance(description, str) or not description.strip():
            raise CatalogChannelGenerationError("LLM returned a channel without a valid description.")
        if not isinstance(specification, str) or not specification.strip():
            raise CatalogChannelGenerationError("LLM returned a channel without a valid specification.")

        return {
            "name": name.strip(),
            "description": description.strip(),
            "specification": specification.strip(),
        }
