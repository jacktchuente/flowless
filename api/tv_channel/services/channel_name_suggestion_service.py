from __future__ import annotations

import json
import re

from django.conf import settings

from tv_channel.models import GridLayout, GridLayoutMode, TvChannel
from utils.format_with_jinja import format_with_jinja
from utils.llm_service import LLMService


class ChannelNameSuggestionError(ValueError):
    pass


class ChannelNameSuggestionService:
    TEMPLATE_PATH = (
        settings.BASE_DIR
        / "templates"
        / "tv_channel"
        / "prompts"
        / "channel_name_suggestion_prompt.j2"
    )

    MAX_NAME_LENGTH = 50

    def __init__(self, tv_channel: TvChannel):
        self.tv_channel = tv_channel

    def suggest_name(self) -> str:
        forbidden_channel_names = list(
            TvChannel.objects
            .exclude(pk=self.tv_channel.pk)
            .values_list("name", flat=True)
        )

        retry_errors: list[str] = []
        max_attempts = max(1, int(getattr(settings, "LLM_RETRY_CHANNEL_NAME_SUGGESTION", 3)))

        for attempt in range(1, max_attempts + 1):
            prompt = self.build_prompt(
                forbidden_channel_names=forbidden_channel_names,
                retry_errors=retry_errors,
            )
            try:
                response = LLMService().complete(prompt=prompt)
                name = self._parse_llm_response(response.content)
            except Exception as exc:
                error = exc if isinstance(exc, ChannelNameSuggestionError) else ChannelNameSuggestionError(
                    f"LLM request failed: {exc}"
                )
                retry_errors = [str(error)]
                if attempt == max_attempts:
                    raise error from exc
                continue

            if name in forbidden_channel_names:
                retry_errors = [f"Channel name is forbidden or already used: {name}."]
                if attempt == max_attempts:
                    raise ChannelNameSuggestionError(retry_errors[0])
                continue

            return name

        raise ChannelNameSuggestionError("Channel name suggestion failed.")

    def build_prompt(
        self,
        *,
        forbidden_channel_names: list[str],
        retry_errors: list[str] | None = None,
    ) -> str:
        return format_with_jinja(
            self.TEMPLATE_PATH,
            {
                "channel_name": self.tv_channel.name,
                "channel_description": self.tv_channel.description or "",
                "channel_specification": self.tv_channel.specification or "",
                "catalog_name": self.tv_channel.catalog.name,
                "catalog_description": self.tv_channel.catalog.description or "",
                "scheduling_mode": self._get_scheduling_mode(),
                "editorial_line": self._build_editorial_line_context(),
                "editorial_candidate": self._build_editorial_candidate_context(),
                "forbidden_channel_names": forbidden_channel_names,
                "retry_errors": retry_errors or [],
            },
        )

    def _get_scheduling_mode(self) -> str:
        grid_layout = (
            GridLayout.objects
            .filter(tv_channel=self.tv_channel, is_active=True)
            .first()
        )
        if grid_layout is None:
            return "unknown"
        if grid_layout.mode == GridLayoutMode.FLEXIBLE:
            return "flexible"
        return "fixed"

    def _build_editorial_line_context(self) -> dict | None:
        editorial_line = getattr(self.tv_channel, "editorialline", None)
        if editorial_line is None:
            return None
        return {
            "allowed_categories": editorial_line.allowed_categories,
            "forbidden_categories": editorial_line.forbidden_categories,
            "preferred_categories": editorial_line.preferred_categories,
            "allowed_natures": editorial_line.allowed_natures,
            "preferred_natures": editorial_line.preferred_natures,
            "allowed_container_kinds": editorial_line.allowed_container_kinds,
            "preferred_container_kinds": editorial_line.preferred_container_kinds,
            "start_at": editorial_line.start_at.isoformat(),
            "end_at": editorial_line.end_at.isoformat(),
        }

    def _build_editorial_candidate_context(self) -> dict | None:
        candidate = (
            self.tv_channel.editorial_channel_candidates
            .order_by("-updated_at")
            .first()
        )
        if candidate is None:
            return None
        return {
            "name": candidate.name,
            "description": candidate.description,
            "segments": [
                {
                    "name": channel_segment.segment.name,
                    "description": channel_segment.segment.description,
                    "role": channel_segment.role,
                    "weight": channel_segment.weight,
                }
                for channel_segment in (
                    candidate.channel_segments
                    .select_related("segment")
                    .order_by("position", "-weight")
                )
            ],
        }

    def _parse_llm_response(self, content: str) -> str:
        if not content or not content.strip():
            raise ChannelNameSuggestionError("LLM returned an empty response.")

        match = re.search(r"<name_output>\s*(\{.*?\})\s*</name_output>", content, re.DOTALL)
        candidate = match.group(1) if match else content.strip()

        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise ChannelNameSuggestionError("LLM returned an invalid name JSON payload.") from exc

        if not isinstance(payload, dict):
            raise ChannelNameSuggestionError("LLM returned an invalid top-level payload.")

        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ChannelNameSuggestionError("LLM returned an empty channel name.")

        name = name.strip()
        if len(name) > self.MAX_NAME_LENGTH:
            raise ChannelNameSuggestionError(
                f"LLM returned a name longer than {self.MAX_NAME_LENGTH} characters: {name}."
            )

        return name
