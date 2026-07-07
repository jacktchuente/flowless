import logging

from django.conf import settings
from django.core.files.base import ContentFile

from tv_channel.models import TvChannel
from tv_channel.services.logo_generation.base import LogoGenerationError, LogoImageBackend
from tv_channel.services.logo_generation.comfyui_backend import ComfyUiImageBackend
from tv_channel.services.logo_generation.openai_backend import OpenAiImageBackend
from tv_channel.services.logo_prompt_service import LogoPromptService

logger = logging.getLogger(__name__)

BACKENDS: dict[str, type[LogoImageBackend]] = {
    ComfyUiImageBackend.name: ComfyUiImageBackend,
    OpenAiImageBackend.name: OpenAiImageBackend,
}


class LogoGenerationService:
    def __init__(self, tv_channel: TvChannel, *, backend: str | None = None):
        self.tv_channel = tv_channel
        self.backend = self._resolve_backend(backend)

    @staticmethod
    def _resolve_backend(backend: str | None) -> LogoImageBackend:
        name = (backend or settings.IMAGE_GENERATION_BACKEND or "").strip().lower()
        backend_class = BACKENDS.get(name)
        if backend_class is None:
            raise LogoGenerationError(
                f"Unknown image generation backend '{name}'. Available: {', '.join(sorted(BACKENDS))}."
            )
        return backend_class()

    def generate(self) -> TvChannel:
        prompt = LogoPromptService(self.tv_channel).generate_prompt()
        logger.info(
            "LogoGenerationService.generate channel_id=%s backend=%s prompt_length=%s",
            self.tv_channel.id,
            self.backend.name,
            len(prompt),
        )
        image_bytes = self.backend.generate(prompt)
        if not image_bytes:
            raise LogoGenerationError("Image backend returned an empty payload.")
        self.tv_channel.logo.save(
            f"channel_{self.tv_channel.id}_logo.png",
            ContentFile(image_bytes),
            save=True,
        )
        return self.tv_channel
