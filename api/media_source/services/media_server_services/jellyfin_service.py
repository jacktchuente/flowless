from __future__ import annotations

from datetime import date, datetime
from statistics import mean
from typing import Any, Literal, TypedDict

import requests


ContainerKind = Literal[
    "movie",
    "series",
    "music_release",
    "music_video_release",
    "other",
]

ItemKind = Literal[
    "movie",
    "episode",
    "music_track",
    "music_video",
    "other",
]


class MediaItem(TypedDict, total=False):
    external_id: str
    title: str
    description: str | None

    item_kind: ItemKind | None

    duration_seconds: int | None
    sequence_number: int | None
    season_number: int | None
    episode_number: int | None

    min_age: int | None
    max_age: int | None
    release_date: date | None
    release_year: int | None
    countries: list[str]
    audio_languages: list[str]
    subtitle_languages: list[str]
    video_width: int | None
    video_height: int | None
    community_rating_score: float | None
    critic_rating_score: float | None
    overall_rating_score: float | None

    tags: list[str]
    genres: list[str]

    people: list[dict[str, str | None]]
    directors: list[str]
    writers: list[str]
    creators: list[str]
    actors: list[str]
    studios: list[str]

    raw_metadata: dict[str, Any]


class MediaServerMediaContainer(TypedDict, total=False):
    external_id: str
    provider_ids: dict[str, str]
    title: str
    description: str | None

    container_kind: ContainerKind | None

    categories: list[str]

    item_count: int
    duration_min_seconds: int | None
    duration_max_seconds: int | None
    total_duration_seconds: int | None
    min_video_width: int | None
    min_video_height: int | None

    min_age: int | None
    max_age: int | None
    release_date: date | None
    release_date_start: date | None
    release_date_end: date | None
    release_year_min: int | None
    release_year_max: int | None
    countries: list[str]
    audio_languages: list[str]
    subtitle_languages: list[str]
    audio_languages_any: list[str]
    subtitle_languages_any: list[str]
    community_rating_score: float | None
    critic_rating_score: float | None
    overall_rating_score: float | None

    people: list[dict[str, str | None]]
    directors: list[str]
    writers: list[str]
    creators: list[str]
    actors: list[str]
    studios: list[str]

    tags: list[str]
    genres: list[str]

    raw_metadata: dict[str, Any]
    items: list[MediaItem]


class Collection(TypedDict):
    name: str
    external_id: str
    container_kind: ContainerKind | None


class Credentials(TypedDict):
    application_url: str
    username: str
    password: str


class JellyfinService:
    AUTH_HEADER = (
        'MediaBrowser Client="Flowless", Device="API", '
        'DeviceId="flowless-media-source", Version="1.0.0"'
    )

    COLLECTION_FIELDS = "PrimaryImageAspectRatio,CollectionType"

    COLLECTION_TYPE_KIND_MAP: dict[str, ContainerKind] = {
        "movies": "movie",
        "tvshows": "series",
        "music": "music_release",
        "musicvideos": "music_video_release",
    }

    CONTAINER_ITEM_TYPES = "Movie,Series,MusicAlbum,MusicVideo,Audio"

    COLLECTION_ITEM_FIELDS = (
        "Genres,Tags,Overview,RunTimeTicks,CommunityRating,CriticRating,ProductionYear,PremiereDate,"
        "OfficialRating,RecursiveItemCount,ChildCount,ProductionLocations,"
        "People,Studios,Taglines,MediaStreams,Path,ParentId,AlbumId,Album,IndexNumber,"
        "ParentIndexNumber,CollectionType,ProviderIds"
    )

    SERIES_EPISODE_FIELDS = (
        "Genres,Tags,Overview,RunTimeTicks,CommunityRating,CriticRating,ProductionYear,PremiereDate,"
        "OfficialRating,ProductionLocations,MediaStreams,IndexNumber,ParentIndexNumber,"
        "People,Studios"
    )

    ALBUM_TRACK_FIELDS = (
        "Genres,Tags,Overview,RunTimeTicks,CommunityRating,CriticRating,ProductionYear,PremiereDate,"
        "ProductionLocations,MediaStreams,IndexNumber,ParentIndexNumber,Album,AlbumId,"
        "People,Studios"
    )

    def __init__(self, credentials: Credentials):
        self.credentials = credentials

    @staticmethod
    def normalize_url(url: str) -> str:
        return url.rstrip("/")

    @classmethod
    def build_auth_headers(cls) -> dict[str, str]:
        return {
            "X-Emby-Authorization": cls.AUTH_HEADER,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    @classmethod
    def authenticate_credentials(cls, credentials: Credentials) -> dict[str, Any]:
        response = requests.post(
            f"{cls.normalize_url(credentials['application_url'])}/Users/AuthenticateByName",
            json={
                "Username": credentials["username"],
                "Pw": credentials["password"],
            },
            headers=cls.build_auth_headers(),
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def check_connexion(self) -> bool:
        try:
            self.authenticate_credentials(self.credentials)
        except requests.RequestException:
            return False
        return True

    def _authenticate(self) -> tuple[str, str]:
        payload = self.authenticate_credentials(self.credentials)
        token = payload.get("AccessToken")
        user_id = (payload.get("User") or {}).get("Id")

        if not token or not user_id:
            raise ValueError("Jellyfin authentication response is incomplete.")

        return token, user_id

    def _request(
            self,
            token: str,
            path: str,
            params: dict[str, Any],
            timeout: int = 30,
    ) -> dict[str, Any]:
        application_url = self.normalize_url(self.credentials["application_url"])
        response = requests.get(
            f"{application_url}{path}",
            params=params,
            headers={
                "X-Emby-Token": token,
                "Accept": "application/json",
            },
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    def _fetch_paginated_items(
            self,
            token: str,
            path: str,
            params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        start_index = 0
        limit = 200

        while True:
            payload = self._request(
                token=token,
                path=path,
                params={
                    **params,
                    "StartIndex": start_index,
                    "Limit": limit,
                },
            )

            page_items = payload.get("Items", [])
            if not isinstance(page_items, list):
                break

            items.extend(
                item for item in page_items if isinstance(item, dict)
            )

            if len(page_items) < limit:
                break

            start_index += limit

        return items

    def get_collections(self) -> list[Collection]:
        token, user_id = self._authenticate()

        views = self._fetch_paginated_items(
            token=token,
            path=f"/Users/{user_id}/Views",
            params={"Fields": self.COLLECTION_FIELDS},
        )

        collections: list[Collection] = []

        for view in views:
            external_id = view.get("Id")
            name = view.get("Name")

            if not isinstance(external_id, str) or not isinstance(name, str):
                continue

            collection_type = view.get("CollectionType")
            container_kind = (
                self.COLLECTION_TYPE_KIND_MAP.get(collection_type.strip().lower())
                if isinstance(collection_type, str)
                else None
            )

            collections.append(
                {
                    "name": name[:20],
                    "external_id": external_id,
                    "container_kind": container_kind,
                }
            )

        return collections

    def get_media(self, collection_id: str) -> list[MediaServerMediaContainer]:
        return [
            container
            for batch in self.iter_media_batches(collection_id)
            for container in batch
        ]

    def iter_media_batches(
            self,
            collection_id: str,
            batch_size: int = 100,
    ):
        token, user_id = self._authenticate()

        collection_items = self._fetch_collection_items(
            token=token,
            user_id=user_id,
            collection_id=collection_id,
        )

        for start_index in range(0, len(collection_items), batch_size):
            yield self._build_media_containers(
                token=token,
                user_id=user_id,
                collection_items=collection_items[start_index:start_index + batch_size],
            )

    def _fetch_collection_items(
            self,
            token: str,
            user_id: str,
            collection_id: str,
    ) -> list[dict[str, Any]]:
        return self._fetch_paginated_items(
            token=token,
            path=f"/Users/{user_id}/Items",
            params={
                "ParentId": collection_id,
                "Recursive": True,
                "IncludeItemTypes": self.CONTAINER_ITEM_TYPES,
                "Fields": self.COLLECTION_ITEM_FIELDS,
            },
        )

    def _fetch_series_episodes(
            self,
            token: str,
            user_id: str,
            series_id: str,
    ) -> list[dict[str, Any]]:
        return self._fetch_paginated_items(
            token=token,
            path=f"/Shows/{series_id}/Episodes",
            params={
                "UserId": user_id,
                "Fields": self.SERIES_EPISODE_FIELDS,
                # Exclut les épisodes virtuels (métadonnées sans fichier) que
                # Jellyfin renvoie quand « afficher les épisodes manquants »
                # est actif côté serveur.
                "IsMissing": False,
            },
        )

    def _fetch_album_tracks(
            self,
            token: str,
            user_id: str,
            album_id: str,
    ) -> list[dict[str, Any]]:
        return self._fetch_paginated_items(
            token=token,
            path=f"/Users/{user_id}/Items",
            params={
                "ParentId": album_id,
                "Recursive": True,
                "IncludeItemTypes": "Audio",
                "Fields": self.ALBUM_TRACK_FIELDS,
            },
        )

    @staticmethod
    def _ticks_to_seconds(value: Any) -> int | None:
        if not isinstance(value, int):
            return None
        return int(value / 10_000_000)

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if not isinstance(value, str) or not value:
            return None

        normalized = value.replace("Z", "+00:00")

        try:
            return datetime.fromisoformat(normalized).date()
        except ValueError:
            return None

    @staticmethod
    def _normalize_language(value: Any) -> str | None:
        if not isinstance(value, str):
            return None

        normalized = value.strip().lower().replace("_", "-")
        return normalized or None

    @staticmethod
    def _dedupe_sorted(values: list[str]) -> list[str]:
        return sorted({value for value in values if value})

    @staticmethod
    def _dedupe_people(values: list[dict[str, str | None]]) -> list[dict[str, str | None]]:
        seen: set[tuple[str | None, str | None, str | None, str | None]] = set()
        people: list[dict[str, str | None]] = []

        for value in values:
            key = (
                value.get("external_id"),
                value.get("name"),
                value.get("type"),
                value.get("role"),
            )

            if key in seen:
                continue

            seen.add(key)
            people.append(value)

        return people

    @classmethod
    def _extract_people(cls, item: dict[str, Any]) -> dict[str, Any]:
        people: list[dict[str, str | None]] = []

        for person in item.get("People") or []:
            if not isinstance(person, dict):
                continue

            name = person.get("Name")

            if not isinstance(name, str):
                continue

            external_id = person.get("Id")
            person_type = person.get("Type")
            role = person.get("Role")

            people.append(
                {
                    "external_id": external_id if isinstance(external_id, str) else None,
                    "name": name,
                    "type": person_type if isinstance(person_type, str) else None,
                    "role": role if isinstance(role, str) else None,
                }
            )

        people = cls._dedupe_people(people)

        return {
            "people": people,
            "directors": cls._dedupe_sorted(
                [
                    person["name"]
                    for person in people
                    if person.get("type") == "Director" and person.get("name")
                ]
            ),
            "writers": cls._dedupe_sorted(
                [
                    person["name"]
                    for person in people
                    if person.get("type") == "Writer" and person.get("name")
                ]
            ),
            "creators": cls._dedupe_sorted(
                [
                    person["name"]
                    for person in people
                    if person.get("type") == "Creator" and person.get("name")
                ]
            ),
            "actors": cls._dedupe_sorted(
                [
                    person["name"]
                    for person in people
                    if person.get("type") == "Actor" and person.get("name")
                ]
            ),
        }

    @classmethod
    def _extract_studios(cls, item: dict[str, Any]) -> list[str]:
        studios: list[str] = []

        for studio in item.get("Studios") or []:
            if isinstance(studio, str):
                studios.append(studio)
            elif isinstance(studio, dict) and isinstance(studio.get("Name"), str):
                studios.append(studio["Name"])

        return cls._dedupe_sorted(studios)

    @staticmethod
    def _extract_age_bounds(item: dict[str, Any]) -> tuple[int | None, int | None]:
        rating = item.get("OfficialRating")

        if not isinstance(rating, str):
            return None, None

        digits = "".join(char for char in rating if char.isdigit())

        if not digits:
            return None, None

        return int(digits), None

    @classmethod
    def _extract_media_streams(cls, item: dict[str, Any]) -> dict[str, Any]:
        audio_languages: list[str] = []
        subtitle_languages: list[str] = []
        video_widths: list[int] = []
        video_heights: list[int] = []

        for stream in item.get("MediaStreams") or []:
            if not isinstance(stream, dict):
                continue

            stream_type = stream.get("Type")

            if stream_type == "Audio":
                language = cls._normalize_language(stream.get("Language"))
                if language:
                    audio_languages.append(language)

            elif stream_type == "Subtitle":
                language = cls._normalize_language(stream.get("Language"))
                if language:
                    subtitle_languages.append(language)

            elif stream_type == "Video":
                width = stream.get("Width")
                height = stream.get("Height")

                if isinstance(width, int) and width > 0:
                    video_widths.append(width)

                if isinstance(height, int) and height > 0:
                    video_heights.append(height)

        return {
            "audio_languages": cls._dedupe_sorted(audio_languages),
            "subtitle_languages": cls._dedupe_sorted(subtitle_languages),
            "video_width": min(video_widths) if video_widths else None,
            "video_height": min(video_heights) if video_heights else None,
        }

    @classmethod
    def _extract_common_metadata(cls, item: dict[str, Any]) -> dict[str, Any]:
        stream_data = cls._extract_media_streams(item)
        min_age, max_age = cls._extract_age_bounds(item)

        countries = cls._dedupe_sorted(
            [
                value
                for value in item.get("ProductionLocations") or []
                if isinstance(value, str)
            ]
        )

        community_rating = item.get("CommunityRating")
        critic_rating = item.get("CriticRating")

        return {
            "description": item.get("Overview")
            if isinstance(item.get("Overview"), str)
            else None,
            "min_age": min_age,
            "max_age": max_age,
            "duration_seconds": cls._ticks_to_seconds(item.get("RunTimeTicks")),
            "release_date": cls._parse_date(item.get("PremiereDate")),
            "release_year": item.get("ProductionYear")
            if isinstance(item.get("ProductionYear"), int)
            else None,
            "countries": countries,
            "audio_languages": stream_data["audio_languages"],
            "subtitle_languages": stream_data["subtitle_languages"],
            "video_width": stream_data["video_width"],
            "video_height": stream_data["video_height"],
            "community_rating_score": float(community_rating)
            if isinstance(community_rating, int | float)
            else None,
            "critic_rating_score": float(critic_rating)
            if isinstance(critic_rating, int | float)
            else None,
            "overall_rating_score": float(community_rating)
            if isinstance(community_rating, int | float)
            else None,
        }

    @classmethod
    def _extract_categories(cls, item: dict[str, Any]) -> dict[str, list[str]]:
        genres = cls._dedupe_sorted(
            [
                value
                for value in item.get("Genres") or []
                if isinstance(value, str)
            ]
        )

        tags = cls._dedupe_sorted(
            [
                value
                for value in item.get("Tags") or []
                if isinstance(value, str)
            ]
        )

        return {
            "genres": genres,
            "tags": tags,
            "categories": cls._dedupe_sorted(genres + tags),
        }

    @staticmethod
    def _container_kind(item_type: Any) -> ContainerKind:
        if item_type == "Movie":
            return "movie"
        if item_type == "Series":
            return "series"
        if item_type == "MusicAlbum":
            return "music_release"
        if item_type == "MusicVideo":
            return "music_video_release"
        if item_type == "Audio":
            return "music_release"
        return "other"

    @staticmethod
    def _extract_provider_ids(item: dict[str, Any]) -> dict[str, str]:
        provider_ids = item.get("ProviderIds")
        if not isinstance(provider_ids, dict):
            return {}
        return {
            str(provider).lower(): str(value)
            for provider, value in provider_ids.items()
            if isinstance(provider, str) and value not in (None, "")
        }

    @staticmethod
    def _item_kind(item_type: Any) -> ItemKind:
        if item_type == "Movie":
            return "movie"
        if item_type == "Episode":
            return "episode"
        if item_type == "Audio":
            return "music_track"
        if item_type == "MusicVideo":
            return "music_video"
        return "other"

    @classmethod
    def _build_item_payload(cls, item: dict[str, Any]) -> MediaItem | None:
        external_id = item.get("Id")

        if not isinstance(external_id, str):
            return None

        # Garde-fou : ne jamais ingérer un item virtuel (aucun fichier).
        if item.get("LocationType") == "Virtual" or item.get("IsVirtualItem") is True:
            return None

        common = cls._extract_common_metadata(item)
        category_data = cls._extract_categories(item)
        people_data = cls._extract_people(item)
        studios = cls._extract_studios(item)

        index_number = item.get("IndexNumber")
        parent_index_number = item.get("ParentIndexNumber")

        return {
            "external_id": external_id,
            "title": item.get("Name") if isinstance(item.get("Name"), str) else external_id,
            "description": common["description"],
            "item_kind": cls._item_kind(item.get("Type")),
            "min_age": common["min_age"],
            "max_age": common["max_age"],
            "duration_seconds": common["duration_seconds"],
            "release_date": common["release_date"],
            "release_year": common["release_year"],
            "countries": common["countries"],
            "audio_languages": common["audio_languages"],
            "subtitle_languages": common["subtitle_languages"],
            "video_width": common["video_width"],
            "video_height": common["video_height"],
            "community_rating_score": common["community_rating_score"],
            "critic_rating_score": common["critic_rating_score"],
            "overall_rating_score": common["overall_rating_score"],
            "genres": category_data["genres"],
            "tags": category_data["tags"],
            "people": people_data["people"],
            "directors": people_data["directors"],
            "writers": people_data["writers"],
            "creators": people_data["creators"],
            "actors": people_data["actors"],
            "studios": studios,
            "sequence_number": index_number if isinstance(index_number, int) else None,
            "season_number": parent_index_number if isinstance(parent_index_number, int) else None,
            "episode_number": index_number if isinstance(index_number, int) else None,
            "raw_metadata": item,
        }

    @classmethod
    def _aggregate_container(
            cls,
            container_item: dict[str, Any],
            item_payloads: list[MediaItem],
    ) -> MediaServerMediaContainer | None:
        external_id = container_item.get("Id")

        if not isinstance(external_id, str):
            return None

        common = cls._extract_common_metadata(container_item)
        category_data = cls._extract_categories(container_item)
        container_people_data = cls._extract_people(container_item)
        container_studios = cls._extract_studios(container_item)

        min_ages = [
            item["min_age"]
            for item in item_payloads
            if item.get("min_age") is not None
        ]

        max_ages = [
            item["max_age"]
            for item in item_payloads
            if item.get("max_age") is not None
        ]

        durations = [
            item["duration_seconds"]
            for item in item_payloads
            if item.get("duration_seconds") is not None
        ]

        release_dates = [
            item["release_date"]
            for item in item_payloads
            if item.get("release_date") is not None
        ]

        release_years = [
            item["release_year"]
            for item in item_payloads
            if item.get("release_year") is not None
        ]

        community_ratings = [
            item["community_rating_score"]
            for item in item_payloads
            if item.get("community_rating_score") is not None
        ]

        critic_ratings = [
            item["critic_rating_score"]
            for item in item_payloads
            if item.get("critic_rating_score") is not None
        ]

        ratings = [
            item["overall_rating_score"]
            for item in item_payloads
            if item.get("overall_rating_score") is not None
        ]

        countries = sorted(
            {
                country
                for item in item_payloads
                for country in item.get("countries", [])
            }
        )

        audio_sets = [
            set(item.get("audio_languages", []))
            for item in item_payloads
            if item.get("audio_languages")
        ]

        subtitle_sets = [
            set(item.get("subtitle_languages", []))
            for item in item_payloads
            if item.get("subtitle_languages")
        ]

        audio_any = sorted(
            {
                language
                for item in item_payloads
                for language in item.get("audio_languages", [])
            }
        )

        subtitle_any = sorted(
            {
                language
                for item in item_payloads
                for language in item.get("subtitle_languages", [])
            }
        )

        widths = [
            item["video_width"]
            for item in item_payloads
            if item.get("video_width") is not None
        ]

        heights = [
            item["video_height"]
            for item in item_payloads
            if item.get("video_height") is not None
        ]

        people = cls._dedupe_people(
            container_people_data["people"]
            + [
                person
                for item in item_payloads
                for person in item.get("people", [])
            ]
        )

        directors = cls._dedupe_sorted(
            container_people_data["directors"]
            + [
                director
                for item in item_payloads
                for director in item.get("directors", [])
            ]
        )

        writers = cls._dedupe_sorted(
            container_people_data["writers"]
            + [
                writer
                for item in item_payloads
                for writer in item.get("writers", [])
            ]
        )

        creators = cls._dedupe_sorted(
            container_people_data["creators"]
            + [
                creator
                for item in item_payloads
                for creator in item.get("creators", [])
            ]
        )

        actors = cls._dedupe_sorted(
            container_people_data["actors"]
            + [
                actor
                for item in item_payloads
                for actor in item.get("actors", [])
            ]
        )

        studios = cls._dedupe_sorted(
            container_studios
            + [
                studio
                for item in item_payloads
                for studio in item.get("studios", [])
            ]
        )

        genres = cls._dedupe_sorted(
            category_data["genres"]
            + [
                genre
                for item in item_payloads
                for genre in item.get("genres", [])
            ]
        )

        tags = cls._dedupe_sorted(
            category_data["tags"]
            + [
                tag
                for item in item_payloads
                for tag in item.get("tags", [])
            ]
        )

        categories = cls._dedupe_sorted(genres + tags)

        return {
            "external_id": external_id,
            "provider_ids": cls._extract_provider_ids(container_item),
            "title": container_item.get("Name")
            if isinstance(container_item.get("Name"), str)
            else external_id,
            "description": common["description"],

            "container_kind": cls._container_kind(container_item.get("Type")),

            "categories": categories,
            "genres": genres,
            "tags": tags,

            "item_count": len(item_payloads),

            "duration_min_seconds": min(durations)
            if durations
            else common["duration_seconds"],
            "duration_max_seconds": max(durations)
            if durations
            else common["duration_seconds"],
            "total_duration_seconds": sum(durations)
            if durations
            else common["duration_seconds"],

            "min_video_width": min(widths) if widths else common["video_width"],
            "min_video_height": min(heights) if heights else common["video_height"],

            "min_age": max(min_ages) if min_ages else common["min_age"],
            "max_age": max(max_ages) if max_ages else common["max_age"],
            "release_date": min(release_dates) if release_dates else common["release_date"],
            "release_date_start": min(release_dates) if release_dates else common["release_date"],
            "release_date_end": max(release_dates) if release_dates else common["release_date"],
            "release_year_min": min(release_years) if release_years else common["release_year"],
            "release_year_max": max(release_years) if release_years else common["release_year"],

            "countries": countries or common["countries"],

            "audio_languages": sorted(set.intersection(*audio_sets))
            if audio_sets
            else common["audio_languages"],

            "subtitle_languages": sorted(set.intersection(*subtitle_sets))
            if subtitle_sets
            else common["subtitle_languages"],

            "audio_languages_any": audio_any or common["audio_languages"],
            "subtitle_languages_any": subtitle_any or common["subtitle_languages"],

            "community_rating_score": mean(community_ratings)
            if community_ratings
            else common["community_rating_score"],
            "critic_rating_score": mean(critic_ratings)
            if critic_ratings
            else common["critic_rating_score"],
            "overall_rating_score": mean(ratings)
            if ratings
            else common["overall_rating_score"],

            "people": people,
            "directors": directors,
            "writers": writers,
            "creators": creators,
            "actors": actors,
            "studios": studios,

            "raw_metadata": {
                "container": container_item,
                "items": [
                    item["raw_metadata"]
                    for item in item_payloads
                    if "raw_metadata" in item
                ],
            },

            "items": item_payloads,
        }

    def _build_media_containers(
            self,
            token: str,
            user_id: str,
            collection_items: list[dict[str, Any]],
    ) -> list[MediaServerMediaContainer]:
        containers: list[MediaServerMediaContainer] = []
        audio_by_album_id: dict[str, list[dict[str, Any]]] = {}

        for item in collection_items:
            if item.get("Type") == "Audio" and isinstance(item.get("AlbumId"), str):
                audio_by_album_id.setdefault(item["AlbumId"], []).append(item)

        for item in collection_items:
            item_type = item.get("Type")
            item_id = item.get("Id")

            if not isinstance(item_id, str):
                continue

            item_payloads: list[MediaItem] = []

            if item_type in {"Movie", "MusicVideo"}:
                item_payload = self._build_item_payload(item)
                if item_payload:
                    item_payloads = [item_payload]

            elif item_type == "Series":
                episodes = self._fetch_series_episodes(
                    token=token,
                    user_id=user_id,
                    series_id=item_id,
                )

                item_payloads = [
                    payload
                    for episode in episodes
                    if (payload := self._build_item_payload(episode)) is not None
                ]

            elif item_type == "MusicAlbum":
                tracks = self._fetch_album_tracks(
                    token=token,
                    user_id=user_id,
                    album_id=item_id,
                )

                if not tracks:
                    tracks = audio_by_album_id.get(item_id, [])

                item_payloads = [
                    payload
                    for track in tracks
                    if (payload := self._build_item_payload(track)) is not None
                ]

            elif item_type == "Audio" and not isinstance(item.get("AlbumId"), str):
                item_payload = self._build_item_payload(item)
                if item_payload:
                    item_payloads = [item_payload]

            else:
                continue

            container = self._aggregate_container(
                container_item=item,
                item_payloads=item_payloads,
            )

            if container:
                containers.append(container)

        return containers