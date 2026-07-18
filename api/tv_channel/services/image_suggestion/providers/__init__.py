from tv_channel.services.image_suggestion.providers.jellyfin_provider import JellyfinImageProvider
from tv_channel.services.image_suggestion.providers.tmdb_provider import TmdbImageProvider

# Ordre = priorite: Jellyfin d'abord, TMDB complete jusqu'a la limite.
PROVIDERS = (JellyfinImageProvider, TmdbImageProvider)
