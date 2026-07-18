from __future__ import annotations

from dataclasses import dataclass

from tv_channel.services.image_suggestion.query_service import ImageQuery


@dataclass
class ImageResult:
    provider: str
    source_url: str        # pleine resolution, sans credentials
    thumbnail_url: str     # petite taille, sans credentials
    width: int | None = None
    height: int | None = None
    attribution: str = ""


class ImageSearchProvider:
    name: str

    def __init__(self, tv_channel):
        self.tv_channel = tv_channel

    def is_available(self) -> bool:
        raise NotImplementedError

    def search(self, query: ImageQuery, limit: int) -> list[ImageResult]:
        raise NotImplementedError

    def download(self, url: str) -> bytes:
        """Downloads a source/thumbnail URL, adding provider credentials
        (auth stays inside the provider, never in stored URLs)."""
        raise NotImplementedError
