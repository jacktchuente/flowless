from __future__ import annotations

from io import BytesIO
import logging

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.conf import settings
from PIL import Image

from tv_channel.models import ChannelImageSuggestion
from tv_channel.services.image_suggestion.search import get_provider
from utils.task_status_service import broadcast_refresh

logger = logging.getLogger(__name__)


class ChannelImageApplyService:
    """Downloads the chosen suggestion at full resolution, normalizes it
    (bounded size, web-friendly format) and writes it as the channel logo —
    the existing upload-logo/ErsatzTV push pipeline takes over from there."""

    def __init__(self, suggestion: ChannelImageSuggestion):
        self.suggestion = suggestion
        self.tv_channel = suggestion.run.tv_channel

    def apply(self):
        provider = get_provider(self.tv_channel, self.suggestion.provider)
        if provider is None:
            raise ValidationError(f"Unknown image provider {self.suggestion.provider}.")
        raw_bytes = provider.download(self.suggestion.source_url)
        normalized_bytes, extension = self._normalize(raw_bytes)

        self.tv_channel.logo.save(
            f"channel_{self.tv_channel.id}_suggestion_{self.suggestion.id}.{extension}",
            ContentFile(normalized_bytes),
            save=True,
        )
        self.suggestion.run.suggestions.update(is_chosen=False)
        self.suggestion.is_chosen = True
        self.suggestion.save(update_fields=["is_chosen"])
        broadcast_refresh("TvChannel", self.tv_channel.id)
        return self.tv_channel

    @staticmethod
    def _normalize(raw_bytes: bytes) -> tuple[bytes, str]:
        max_width = int(getattr(settings, "CHANNEL_IMAGE_MAX_WIDTH", 1000))
        max_height = int(getattr(settings, "CHANNEL_IMAGE_MAX_HEIGHT", 1000))
        try:
            image = Image.open(BytesIO(raw_bytes))
            image.load()
        except Exception as exc:
            raise ValidationError("Downloaded file is not a valid image.") from exc

        has_alpha = image.mode in ("RGBA", "LA", "P")
        image = image.convert("RGBA" if has_alpha else "RGB")
        image.thumbnail((max_width, max_height))

        buffer = BytesIO()
        if has_alpha:
            image.save(buffer, format="PNG")
            return buffer.getvalue(), "png"
        image.save(buffer, format="JPEG", quality=90)
        return buffer.getvalue(), "jpg"
