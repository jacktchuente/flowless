from __future__ import annotations

from dataclasses import dataclass
import json
import re

from django.conf import settings

from tv_channel.models import ChannelImageEntityType, ChannelImageQuerySource, TvChannel
from utils.format_with_jinja import format_with_jinja
from utils.llm_service import LLMService


class ImageQueryError(ValueError):
    pass


@dataclass
class ImageQuery:
    entity_type: str
    query: str
    source: str


class ChannelImageQueryService:
    """
    Resolves the search query for a channel image, most deterministic source
    first: user override, then editorial line axes (studios/actors), then an
    LLM fallback returning a structured {entity_type, query} payload.
    """

    TEMPLATE_PATH = (
        settings.BASE_DIR
        / "templates"
        / "tv_channel"
        / "prompts"
        / "image_query_prompt.j2"
    )
    # (axe de la ligne edito, entity_type produit)
    AXIS_ENTITY_TYPES = (
        ("studios", ChannelImageEntityType.STUDIO),
        ("actors", ChannelImageEntityType.PERSON),
    )

    def __init__(self, tv_channel: TvChannel):
        self.tv_channel = tv_channel

    def resolve(self, *, query: str | None = None, entity_type: str | None = None) -> ImageQuery:
        override = self._from_user(query=query, entity_type=entity_type)
        if override is not None:
            return override
        from_axes = self.resolve_from_axes()
        if from_axes is not None:
            return from_axes
        return self._from_llm()

    def resolve_from_axes(self) -> ImageQuery | None:
        editorial_line = getattr(self.tv_channel, "editorialline", None)
        if editorial_line is None:
            return None
        for axis, entity_type in self.AXIS_ENTITY_TYPES:
            for level in (editorial_line.preferred, editorial_line.allowed):
                values = [value for value in level.get(axis, []) if isinstance(value, str) and value.strip()]
                if values:
                    return ImageQuery(
                        entity_type=entity_type,
                        query=values[0].strip(),
                        source=ChannelImageQuerySource.AXES,
                    )
        return None

    @staticmethod
    def _from_user(*, query: str | None, entity_type: str | None) -> ImageQuery | None:
        if not query or not query.strip():
            return None
        entity_type = (entity_type or "").strip().lower()
        if entity_type not in ChannelImageEntityType.values:
            entity_type = ChannelImageEntityType.THEME
        return ImageQuery(
            entity_type=entity_type,
            query=query.strip(),
            source=ChannelImageQuerySource.USER,
        )

    def _from_llm(self) -> ImageQuery:
        retry_errors: list[str] = []
        attempts = max(1, int(getattr(settings, "LLM_RETRY_IMAGE_QUERY", 3)))
        last_error = "Image query generation failed."
        for _ in range(attempts):
            try:
                response = LLMService().complete(prompt=self._build_prompt(retry_errors))
                payload = self._parse(response.content)
                return ImageQuery(
                    entity_type=payload["entity_type"],
                    query=payload["query"],
                    source=ChannelImageQuerySource.LLM,
                )
            except ImageQueryError as exc:
                last_error = str(exc)
                retry_errors = [last_error]
            except Exception as exc:
                last_error = f"LLM request failed: {exc}"
                retry_errors = [last_error]
        raise ImageQueryError(last_error)

    def _build_prompt(self, retry_errors: list[str]) -> str:
        return format_with_jinja(
            self.TEMPLATE_PATH,
            {
                "channel_name": self.tv_channel.name,
                "channel_description": self.tv_channel.description or "",
                "channel_specification": self.tv_channel.specification or "",
                "catalog_name": self.tv_channel.catalog.name if self.tv_channel.catalog_id else "",
                "editorial_summary": self._build_editorial_summary(),
                "retry_errors": retry_errors,
            },
        )

    def _build_editorial_summary(self) -> str:
        editorial_line = getattr(self.tv_channel, "editorialline", None)
        if editorial_line is None:
            return ""
        parts = []
        for axis, label in (
            ("categories", "Main themes"),
            ("studios", "Studios"),
            ("actors", "Actors"),
            ("directors", "Directors"),
        ):
            preferred = [value for value in editorial_line.preferred.get(axis, []) if isinstance(value, str)]
            allowed = [value for value in editorial_line.allowed.get(axis, []) if isinstance(value, str)]
            values = preferred or allowed
            if values:
                parts.append(f"{label}: {', '.join(values[:8])}.")
        return " ".join(parts)

    @staticmethod
    def _parse(content: str) -> dict:
        if not content or not content.strip():
            raise ImageQueryError("LLM returned an empty response.")
        match = re.search(r"<image_query>\s*(\{.*?\})\s*</image_query>", content, re.DOTALL)
        if not match:
            raise ImageQueryError("LLM response is missing image_query tags.")
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            raise ImageQueryError("LLM returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise ImageQueryError("LLM returned an invalid top-level payload.")
        entity_type = str(payload.get("entity_type", "")).strip().lower()
        query = str(payload.get("query", "")).strip()
        if entity_type not in ChannelImageEntityType.values:
            raise ImageQueryError(f"Unknown entity_type: {entity_type!r}.")
        if not query:
            raise ImageQueryError("LLM returned an empty query.")
        return {"entity_type": entity_type, "query": query[:255]}
