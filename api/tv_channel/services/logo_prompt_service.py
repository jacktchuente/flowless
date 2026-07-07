from __future__ import annotations

from django.conf import settings

from tv_channel.models import TvChannel
from utils.format_with_jinja import format_with_jinja


class LogoPromptService:
    TEMPLATE_PATH = (
        settings.BASE_DIR
        / "templates"
        / "tv_channel"
        / "prompts"
        / "logo_prompt.j2"
    )

    def __init__(self, tv_channel: TvChannel):
        self.tv_channel = tv_channel

    def generate_prompt(self) -> str:
        return format_with_jinja(
            self.TEMPLATE_PATH,
            {
                "channel_name": self.tv_channel.name,
                "channel_description": self.tv_channel.description or "",
                "channel_specification": self.tv_channel.specification or "",
                "catalog_name": self.tv_channel.catalog.name if self.tv_channel.catalog_id else "",
                "editorial_summary": self._build_editorial_summary(),
            },
        )

    def _build_editorial_summary(self) -> str:
        editorial_line = getattr(self.tv_channel, "editorialline", None)
        if editorial_line is None:
            return ""
        parts = []
        preferred = [value for value in (editorial_line.preferred_categories or []) if isinstance(value, str)]
        allowed = [value for value in (editorial_line.allowed_categories or []) if isinstance(value, str)]
        categories = preferred or allowed
        if categories:
            parts.append(f"Main themes: {', '.join(categories[:8])}.")
        parts.append(
            f"Broadcasting day: {editorial_line.start_at.strftime('%H:%M')}"
            f" to {editorial_line.end_at.strftime('%H:%M')}."
        )
        return " ".join(parts)
