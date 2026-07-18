from __future__ import annotations

import logging

from tv_channel.services.image_suggestion import providers as providers_module
from tv_channel.services.image_suggestion.providers.base import ImageResult, ImageSearchProvider
from tv_channel.services.image_suggestion.query_service import ImageQuery

logger = logging.getLogger(__name__)


def build_providers(tv_channel) -> list[ImageSearchProvider]:
    # Lu au moment de l'appel pour rester patchable (tests, verification).
    return [provider_class(tv_channel) for provider_class in providers_module.PROVIDERS]


def get_provider(tv_channel, name: str) -> ImageSearchProvider | None:
    for provider in build_providers(tv_channel):
        if provider.name == name:
            return provider
    return None


def collect_image_results(
    tv_channel,
    query: ImageQuery,
    limit: int,
) -> tuple[list[ImageResult], list[str]]:
    """Providers in priority order; each one tops results up to `limit`,
    deduplicated by source_url. A failing provider is skipped with a warning."""
    results: list[ImageResult] = []
    warnings: list[str] = []
    seen_urls: set[str] = set()

    for provider in build_providers(tv_channel):
        if len(results) >= limit:
            break
        if not provider.is_available():
            warnings.append(f"Image provider {provider.name} is not available.")
            continue
        try:
            # Limite pleine (pas le reste a combler): un doublon inter-provider
            # ne doit pas manger le budget du complement.
            provider_results = provider.search(query, limit)
        except Exception as exc:
            logger.exception("Image provider %s failed", provider.name)
            warnings.append(f"Image provider {provider.name} failed: {exc}")
            continue
        for result in provider_results:
            if len(results) >= limit:
                break
            if result.source_url in seen_urls:
                continue
            seen_urls.add(result.source_url)
            results.append(result)
    return results, warnings
