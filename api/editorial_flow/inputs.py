"""
Definitions of input dataclasses used by the TV programming algorithm.

This module contains lightweight dataclasses describing the structure of
media objects consumed by the algorithm. These classes deliberately avoid
any dependency on Django or any other ORM. They simply describe the
fields available on input objects. Callers are responsible for mapping
from their own data layer into these dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Dict, Optional


@dataclass
class MediaInput:
    """A simplified representation of a media container.

    This class exposes the same fields that the algorithm expects from
    incoming media. Callers should populate these fields from their own
    models before invoking any of the algorithm's functions. All fields
    are optional except ``id`` and ``title``. None values are permitted
    and will be handled gracefully by the algorithm during normalisation
    and feature extraction.
    """

    # Identifiers
    id: str

    # Structural metadata
    container_kind: Optional[int | str] = None
    nature: Optional[int | str] = None

    # Editorial metadata
    title: str = ""
    description: Optional[str] = None

    # Thematic metadata
    categories: List[str] = field(default_factory=list)

    # Episode and duration metadata
    item_count: Optional[int] = None
    duration_min_seconds: Optional[int] = None
    duration_max_seconds: Optional[int] = None
    total_duration_seconds: Optional[int] = None

    # Video technical metadata
    min_video_width: Optional[int] = None
    min_video_height: Optional[int] = None

    # Age restrictions
    min_age: Optional[int] = None
    max_age: Optional[int] = None

    # Release dates
    release_date: Optional[date] = None
    release_date_start: Optional[date] = None
    release_date_end: Optional[date] = None
    release_year_min: Optional[int] = None
    release_year_max: Optional[int] = None

    # Origin metadata
    countries: List[str] = field(default_factory=list)

    # Language metadata
    audio_languages: List[str] = field(default_factory=list)
    subtitle_languages: List[str] = field(default_factory=list)
    audio_languages_any: List[str] = field(default_factory=list)
    subtitle_languages_any: List[str] = field(default_factory=list)

    # Ratings
    community_rating_score: Optional[float] = None
    critic_rating_score: Optional[float] = None
    overall_rating_score: Optional[float] = None

    # People metadata
    people: List[Dict[str, Optional[str]]] = field(default_factory=list)
    directors: List[str] = field(default_factory=list)
    writers: List[str] = field(default_factory=list)
    creators: List[str] = field(default_factory=list)
    actors: List[str] = field(default_factory=list)
    studios: List[str] = field(default_factory=list)
