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
            },
        )
