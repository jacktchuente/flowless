import base64
import logging

import requests
from django.conf import settings
from openai import OpenAI

from tv_channel.services.logo_generation.base import LogoGenerationError, LogoImageBackend

logger = logging.getLogger(__name__)


class OpenAiImageBackend(LogoImageBackend):
    """API d'images compatible OpenAI (officielle ou serveur compatible)."""

    name = "openai"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or settings.OPENAI_IMAGE_API_KEY
        self.base_url = base_url or settings.OPENAI_IMAGE_URL or None
        self.model = model or settings.OPENAI_IMAGE_MODEL

        if not self.api_key:
            raise LogoGenerationError("OPENAI_IMAGE_API_KEY is not configured.")
        if not self.model:
            raise LogoGenerationError("OPENAI_IMAGE_MODEL is not configured.")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def generate(self, prompt: str) -> bytes:
        try:
            response = self.client.images.generate(
                model=self.model,
                prompt=prompt,
                size="1024x1024",
                n=1,
            )
        except Exception as exc:
            raise LogoGenerationError(f"Image generation failed: {exc}") from exc

        if not response.data:
            raise LogoGenerationError("Image API returned no image.")
        image = response.data[0]

        b64_payload = getattr(image, "b64_json", None)
        if b64_payload:
            return base64.b64decode(b64_payload)

        url = getattr(image, "url", None)
        if url:
            download = requests.get(url, timeout=60)
            if download.status_code != 200:
                raise LogoGenerationError(f"Could not download generated image (HTTP {download.status_code}).")
            return download.content

        raise LogoGenerationError("Image API returned neither b64_json nor url.")
