from __future__ import annotations

from editorial_flow.inputs import MediaInput
from media_source.constants import MediaContainerKind, MediaNature
from media_source.models import MediaContainer


def _choice_label(choices, value) -> str | None:
    if value is None:
        return None
    try:
        return choices(value).label
    except ValueError:
        return str(value)


def build_media_input(container: MediaContainer) -> MediaInput:
    collection = container.media_collection
    return MediaInput(
        id=str(container.id),
        container_kind=_choice_label(MediaContainerKind, collection.container_kind),
        nature=_choice_label(MediaNature, collection.nature),
        is_anime=collection.is_anime,
        title=container.title,
        description=container.description,
        categories=container.categories or [],
        item_count=container.item_count,
        duration_min_seconds=container.duration_min_seconds,
        duration_max_seconds=container.duration_max_seconds,
        total_duration_seconds=container.total_duration_seconds,
        min_video_width=container.min_video_width,
        min_video_height=container.min_video_height,
        min_age=container.min_age,
        max_age=container.max_age,
        release_date=container.release_date,
        release_date_start=container.release_date_start,
        release_date_end=container.release_date_end,
        release_year_min=container.release_year_min,
        release_year_max=container.release_year_max,
        countries=container.countries or [],
        audio_languages=container.audio_languages or [],
        subtitle_languages=container.subtitle_languages or [],
        audio_languages_any=container.audio_languages_any or [],
        subtitle_languages_any=container.subtitle_languages_any or [],
        community_rating_score=container.community_rating_score,
        critic_rating_score=container.critic_rating_score,
        overall_rating_score=container.overall_rating_score,
        people=container.people or [],
        directors=container.directors or [],
        writers=container.writers or [],
        creators=container.creators or [],
        actors=container.actors or [],
        studios=container.studios or [],
    )
