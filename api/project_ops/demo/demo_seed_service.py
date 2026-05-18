from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

from django.core.files import File
from django.db import transaction
from django.utils import timezone

from grid_schedule.constants import ScheduledContainerStatus
from grid_schedule.models import BlockContainerSelection, ScheduleMediaItem, TvPlayout
from media_source.constants import MediaContainerKind, MediaNature, MediaProgrammingRole, MediaSourceType
from media_source.models import MediaCollection, MediaContainer, MediaItem, MediaSource
from project_ops.constants import AnalyzeStatus
from project_ops.demo.demo_reset_service import DemoDataResetService
from tv_channel.models import Catalog, EditorialLine, FillerPolicy, GridBlock, GridLayout, TvChannel


@dataclass(frozen=True)
class DemoContainerSpec:
    title: str
    description: str
    categories: list[str]
    item_count: int
    duration_seconds: int
    kind: int
    release_year: int


class DemoDataSeedService:
    IMAGE_EXTENSIONS = ("png", "jpg", "jpeg", "webp", "svg")

    @classmethod
    @transaction.atomic
    def run(cls):
        DemoDataResetService.run()

        media_source = cls._create_media_source()
        collections = cls._create_collections(media_source)
        containers = cls._create_containers(media_source, collections)

        catalog = cls._create_catalog()
        filler_policies = cls._create_filler_policies()
        cls._create_channels(catalog, containers, filler_policies)

    @classmethod
    def _create_media_source(cls) -> MediaSource:
        now = timezone.now()
        return MediaSource.objects.create(
            name=DemoDataResetService.DEMO_MEDIA_SOURCE_NAME,
            credentials={
                "application_url": "http://demo-jellyfin.local",
                "username": "demo_operator",
                "password": "demo_password",
            },
            source_type=MediaSourceType.jellyfin,
            analyzed_at=now,
            analyze_status=AnalyzeStatus.COMPLETE,
            is_active=True,
        )

    @classmethod
    def _create_collections(cls, media_source: MediaSource) -> dict[str, MediaCollection]:
        now = timezone.now()
        collection_specs = [
            {
                "key": "prestige_crime",
                "name": "Prestige Crime",
                "external_id": "demo-collection-prestige-crime",
                "programming_role": MediaProgrammingRole.MAIN,
                "nature": MediaNature.FICTION,
                "container_kind": MediaContainerKind.SERIES,
            },
            {
                "key": "action_features",
                "name": "Action Features",
                "external_id": "demo-collection-action-features",
                "programming_role": MediaProgrammingRole.MAIN,
                "nature": MediaNature.FICTION,
                "container_kind": MediaContainerKind.STANDALONE_VIDEO,
            },
            {
                "key": "current_affairs",
                "name": "Current Affairs",
                "external_id": "demo-collection-current-affairs",
                "programming_role": MediaProgrammingRole.MAIN,
                "nature": MediaNature.DOCUMENTARY,
                "container_kind": MediaContainerKind.SERIES,
            },
            {
                "key": "comedy_evenings",
                "name": "Comedy Evenings",
                "external_id": "demo-collection-comedy-evenings",
                "programming_role": MediaProgrammingRole.MAIN,
                "nature": MediaNature.SHOW,
                "container_kind": MediaContainerKind.SERIES,
            },
            {
                "key": "live_sessions",
                "name": "Live Sessions",
                "external_id": "demo-collection-live-sessions",
                "programming_role": MediaProgrammingRole.MAIN,
                "nature": MediaNature.MUSIC,
                "container_kind": MediaContainerKind.MUSIC_VIDEO_RELEASE,
            },
        ]

        data: dict[str, MediaCollection] = {}
        for spec in collection_specs:
            data[spec["key"]] = MediaCollection.objects.create(
                name=spec["name"],
                external_id=spec["external_id"],
                media_source=media_source,
                is_active=True,
                analyzed_at=now,
                analyze_status=AnalyzeStatus.COMPLETE,
                programming_role=spec["programming_role"],
                nature=spec["nature"],
                container_kind=spec["container_kind"],
                hash_data=f"demo-hash-{spec['external_id']}",
            )
        return data

    @classmethod
    def _create_containers(
        cls,
        media_source: MediaSource,
        collections: dict[str, MediaCollection],
    ) -> dict[str, MediaContainer]:
        container_specs: dict[str, tuple[str, DemoContainerSpec]] = {
            "harbor_homicide": (
                "prestige_crime",
                DemoContainerSpec(
                    title="Harbor Homicide",
                    description="A moody port-city investigation drama built around long-form cases and sharp ensemble writing.",
                    categories=["crime", "drama", "investigation"],
                    item_count=6,
                    duration_seconds=48 * 60,
                    kind=MediaContainerKind.SERIES,
                    release_year=2021,
                ),
            ),
            "cold_ledger": (
                "prestige_crime",
                DemoContainerSpec(
                    title="Cold Ledger",
                    description="A financial crimes unit tracks vanishings, shell companies and buried political debts.",
                    categories=["crime", "thriller", "neo-noir"],
                    item_count=4,
                    duration_seconds=52 * 60,
                    kind=MediaContainerKind.SERIES,
                    release_year=2020,
                ),
            ),
            "south_precinct": (
                "prestige_crime",
                DemoContainerSpec(
                    title="South Precinct",
                    description="Character-led police procedural anchored in a busy waterfront district.",
                    categories=["crime", "procedural", "urban"],
                    item_count=4,
                    duration_seconds=44 * 60,
                    kind=MediaContainerKind.SERIES,
                    release_year=2019,
                ),
            ),
            "midnight_run_89": (
                "action_features",
                DemoContainerSpec(
                    title="Midnight Run '89",
                    description="A slick overnight pursuit movie with synth-heavy scoring and relentless momentum.",
                    categories=["action", "thriller", "night"],
                    item_count=1,
                    duration_seconds=108 * 60,
                    kind=MediaContainerKind.STANDALONE_VIDEO,
                    release_year=1989,
                ),
            ),
            "neon_pursuit": (
                "action_features",
                DemoContainerSpec(
                    title="Neon Pursuit",
                    description="A metropolitan chase picture packed with practical stunts and glowing downtown skylines.",
                    categories=["action", "heist", "retro"],
                    item_count=1,
                    duration_seconds=102 * 60,
                    kind=MediaContainerKind.STANDALONE_VIDEO,
                    release_year=1992,
                ),
            ),
            "steel_frontier": (
                "action_features",
                DemoContainerSpec(
                    title="Steel Frontier",
                    description="Road action set across industrial border towns and abandoned rail corridors.",
                    categories=["action", "road", "cult"],
                    item_count=1,
                    duration_seconds=96 * 60,
                    kind=MediaContainerKind.STANDALONE_VIDEO,
                    release_year=1987,
                ),
            ),
            "pulse_report_weekly": (
                "current_affairs",
                DemoContainerSpec(
                    title="Pulse Report Weekly",
                    description="Weekly current-affairs magazine focused on institutions, policy and social shifts.",
                    categories=["current-affairs", "news", "magazine"],
                    item_count=5,
                    duration_seconds=42 * 60,
                    kind=MediaContainerKind.SERIES,
                    release_year=2024,
                ),
            ),
            "atlas_of_conflict": (
                "current_affairs",
                DemoContainerSpec(
                    title="Atlas of Conflict",
                    description="Documentary series unpacking modern crises through maps, eyewitness reporting and archival context.",
                    categories=["documentary", "geopolitics", "analysis"],
                    item_count=3,
                    duration_seconds=55 * 60,
                    kind=MediaContainerKind.SERIES,
                    release_year=2023,
                ),
            ),
            "deep_current": (
                "current_affairs",
                DemoContainerSpec(
                    title="Deep Current",
                    description="Feature documentary examining supply chains, labor and the quiet systems behind daily life.",
                    categories=["documentary", "society", "economy"],
                    item_count=1,
                    duration_seconds=84 * 60,
                    kind=MediaContainerKind.STANDALONE_VIDEO,
                    release_year=2022,
                ),
            ),
            "velvet_rewind_show": (
                "comedy_evenings",
                DemoContainerSpec(
                    title="Velvet Rewind",
                    description="Studio sitcom with warm banter, recurring neighborhood chaos and quick twenty-minute episodes.",
                    categories=["comedy", "sitcom", "comfort"],
                    item_count=8,
                    duration_seconds=24 * 60,
                    kind=MediaContainerKind.SERIES,
                    release_year=2018,
                ),
            ),
            "second_balcony_live": (
                "comedy_evenings",
                DemoContainerSpec(
                    title="Second Balcony Live",
                    description="Stand-up and sketch showcase recorded in a small theater with a sharp late-night rhythm.",
                    categories=["comedy", "stand-up", "late-night"],
                    item_count=5,
                    duration_seconds=28 * 60,
                    kind=MediaContainerKind.SERIES,
                    release_year=2021,
                ),
            ),
            "backstage_sessions_paris": (
                "live_sessions",
                DemoContainerSpec(
                    title="Backstage Sessions Paris",
                    description="Intimate performance recordings with stripped-back arrangements and short artist interviews.",
                    categories=["music", "live", "session"],
                    item_count=4,
                    duration_seconds=14 * 60,
                    kind=MediaContainerKind.MUSIC_VIDEO_RELEASE,
                    release_year=2024,
                ),
            ),
            "city_lights_live": (
                "live_sessions",
                DemoContainerSpec(
                    title="City Lights Live",
                    description="Urban rooftop concert series mixing soul, indie pop and soft electronic sets.",
                    categories=["music", "concert", "indie"],
                    item_count=4,
                    duration_seconds=16 * 60,
                    kind=MediaContainerKind.MUSIC_VIDEO_RELEASE,
                    release_year=2023,
                ),
            ),
        }

        data: dict[str, MediaContainer] = {}
        for key, (collection_key, spec) in container_specs.items():
            collection = collections[collection_key]
            container = MediaContainer.objects.create(
                original_data_hash=f"demo-container-hash-{key}",
                external_id=f"demo-container-{key}",
                title=spec.title,
                description=spec.description,
                media_source=media_source,
                media_collection=collection,
                analyzed_at=timezone.now(),
                analyze_status=AnalyzeStatus.COMPLETE,
                categories=spec.categories,
                item_count=spec.item_count,
                duration_min_seconds=spec.duration_seconds,
                duration_max_seconds=spec.duration_seconds,
                total_duration_seconds=spec.duration_seconds * spec.item_count,
                min_video_width=1920,
                min_video_height=1080,
                min_age=12,
                max_age=16,
                release_date=date(spec.release_year, 9, 1),
                countries=["US"],
                audio_languages=["en"],
                subtitle_languages=["en"],
                audio_languages_any=["en"],
                subtitle_languages_any=["en"],
                overall_rating_score=7.8,
                tags=spec.categories[:2],
                genres=spec.categories,
                raw_data={"demo": True, "title": spec.title},
                is_missing=False,
            )
            cls._create_items_for_container(media_source, container, spec)
            data[key] = container
        return data

    @classmethod
    def _create_items_for_container(
        cls,
        media_source: MediaSource,
        container: MediaContainer,
        spec: DemoContainerSpec,
    ):
        for index in range(1, spec.item_count + 1):
            item_title = container.title if spec.item_count == 1 else f"{container.title} Ep. {index}"
            MediaItem.objects.create(
                original_data_hash=f"demo-item-hash-{container.external_id}-{index}",
                container=container,
                title=item_title,
                description=f"Demo item {index} for {container.title}.",
                duration_seconds=spec.duration_seconds,
                sequence_number=index,
                season_number=1 if spec.kind == MediaContainerKind.SERIES else None,
                episode_number=index if spec.kind == MediaContainerKind.SERIES else None,
                min_age=12,
                max_age=16,
                release_date=date(spec.release_year, 9, min(index, 28)),
                release_year=spec.release_year,
                countries=["US"],
                audio_languages=["en"],
                subtitle_languages=["en"],
                video_width=1920,
                video_height=1080,
                overall_rating_score=7.6 + (index * 0.05),
                is_active=True,
                media_source=media_source,
                analyzed_at=timezone.now(),
                analyze_status=AnalyzeStatus.COMPLETE,
                external_id=f"{container.external_id}-item-{index}",
                is_missing=False,
                raw_data={"demo": True, "container": container.title, "index": index},
            )

    @classmethod
    def _create_catalog(cls) -> Catalog:
        return Catalog.objects.create(
            name=DemoDataResetService.DEMO_CATALOG_NAME,
            description="A polished one-catalog demo lineup showing crime, action, documentary, comedy and live music channels.",
            analyze_status=AnalyzeStatus.COMPLETE,
            number_of_channels=5,
        )

    @classmethod
    def _create_filler_policies(cls) -> dict[str, FillerPolicy]:
        return {
            "short_id": FillerPolicy.objects.create(name="Short Channel ID", duration_seconds=30),
            "late_bridge": FillerPolicy.objects.create(name="Late Night Bridge", duration_seconds=180),
        }

    @classmethod
    def _create_channels(
        cls,
        catalog: Catalog,
        containers: dict[str, MediaContainer],
        filler_policies: dict[str, FillerPolicy],
    ):
        now = timezone.localtime()
        day = now.date()
        channel_specs = [
            {
                "name": "Harbor Stories",
                "description": "Crime dramas and procedural investigations with a premium, character-first tone.",
                "specification": "A nightly crime drama lane mixing serialized investigations, police procedurals and urban thrillers.",
                "analyze_status": AnalyzeStatus.COMPLETE,
                "external_playout_id": "etv-demo-harbor-stories",
                "editorial": {
                    "allowed_categories": ["crime", "drama", "investigation"],
                    "preferred_categories": ["crime", "thriller"],
                    "allowed_natures": [MediaNature.FICTION],
                    "allowed_container_kinds": [MediaContainerKind.SERIES],
                    "start_at": time(0, 0),
                    "end_at": time(23, 59),
                    "allow_filler": True,
                },
                "blocks": [
                    {"starts_at": time(0, 0), "ends_at": time(1, 0), "container_key": "harbor_homicide", "item_index": 1},
                    {"starts_at": time(1, 0), "ends_at": time(2, 0), "container_key": "cold_ledger", "item_index": 1},
                    {"starts_at": time(2, 0), "ends_at": time(3, 0), "container_key": "south_precinct", "item_index": 1},
                    {"starts_at": time(3, 0), "ends_at": time(4, 0), "container_key": "harbor_homicide", "item_index": 2},
                    {"starts_at": time(4, 0), "ends_at": time(5, 0), "container_key": "cold_ledger", "item_index": 2},
                    {"starts_at": time(5, 0), "ends_at": time(6, 0), "container_key": "south_precinct", "item_index": 2},
                    {"starts_at": time(6, 0), "ends_at": time(7, 0), "container_key": "harbor_homicide", "item_index": 3},
                    {"starts_at": time(7, 0), "ends_at": time(8, 0), "container_key": "cold_ledger", "item_index": 3},
                    {"starts_at": time(8, 0), "ends_at": time(9, 0), "container_key": "south_precinct", "item_index": 3},
                    {"starts_at": time(9, 0), "ends_at": time(10, 0), "container_key": "harbor_homicide", "item_index": 4},
                    {"starts_at": time(10, 0), "ends_at": time(11, 0), "container_key": "cold_ledger", "item_index": 4},
                    {"starts_at": time(11, 0), "ends_at": time(12, 0), "container_key": "south_precinct", "item_index": 4},
                    {"starts_at": time(12, 0), "ends_at": time(13, 0), "container_key": "harbor_homicide", "item_index": 5},
                    {"starts_at": time(13, 0), "ends_at": time(14, 0), "container_key": "harbor_homicide", "item_index": 6},
                    {"starts_at": time(14, 0), "ends_at": time(15, 0), "container_key": "cold_ledger", "item_index": 1},
                    {"starts_at": time(15, 0), "ends_at": time(16, 0), "container_key": "south_precinct", "item_index": 1},
                    {"starts_at": time(16, 0), "ends_at": time(17, 0), "container_key": "harbor_homicide", "item_index": 1},
                    {"starts_at": time(17, 0), "ends_at": time(18, 0), "container_key": "cold_ledger", "item_index": 2},
                    {"starts_at": time(18, 0), "ends_at": time(19, 0), "container_key": "harbor_homicide", "item_index": 1},
                    {"starts_at": time(19, 0), "ends_at": time(20, 0), "container_key": "cold_ledger", "item_index": 1},
                    {"starts_at": time(20, 0), "ends_at": time(21, 0), "container_key": "harbor_homicide", "item_index": 2},
                    {"starts_at": time(21, 0), "ends_at": time(22, 0), "container_key": "south_precinct", "item_index": 1},
                    {"starts_at": time(22, 0), "ends_at": time(23, 0), "container_key": "cold_ledger", "item_index": 2},
                    {"starts_at": time(23, 0), "ends_at": time(0, 0), "container_key": "south_precinct", "item_index": 2},
                ],
            },
            {
                "name": "Night Shift Action",
                "description": "Late-night action cinema with practical stunts, neon thrillers and cult road movies.",
                "specification": "Feature-driven action channel designed for prime evening and post-midnight reruns.",
                "analyze_status": AnalyzeStatus.COMPLETE,
                "external_playout_id": "etv-demo-night-shift-action",
                "editorial": {
                    "allowed_categories": ["action", "thriller", "cult"],
                    "preferred_categories": ["action", "night"],
                    "allowed_natures": [MediaNature.FICTION],
                    "allowed_container_kinds": [MediaContainerKind.STANDALONE_VIDEO],
                    "start_at": time(20, 0),
                    "end_at": time(2, 0),
                    "allow_filler": True,
                },
                "blocks": [
                    {"starts_at": time(20, 0), "ends_at": time(22, 0), "container_key": "midnight_run_89", "item_index": 1},
                    {"starts_at": time(22, 15), "ends_at": time(0, 0), "container_key": "neon_pursuit", "item_index": 1},
                    {"starts_at": time(0, 0), "ends_at": time(1, 45), "container_key": "steel_frontier", "item_index": 1},
                ],
            },
            {
                "name": "Pulse Report",
                "description": "Current-affairs reporting, geopolitical documentaries and sober long-form analysis.",
                "specification": "A factual channel built around public affairs magazines, documentary strands and issue breakdowns.",
                "analyze_status": AnalyzeStatus.COMPLETE,
                "external_playout_id": None,
                "editorial": {
                    "allowed_categories": ["current-affairs", "documentary", "analysis"],
                    "preferred_categories": ["news", "documentary"],
                    "allowed_natures": [MediaNature.DOCUMENTARY, MediaNature.NEWS],
                    "allowed_container_kinds": [MediaContainerKind.SERIES, MediaContainerKind.STANDALONE_VIDEO],
                    "start_at": time(0, 0),
                    "end_at": time(23, 59),
                    "allow_filler": False,
                },
                "blocks": [
                    {"starts_at": time(0, 0), "ends_at": time(1, 0), "container_key": "pulse_report_weekly", "item_index": 1},
                    {"starts_at": time(1, 0), "ends_at": time(2, 0), "container_key": "atlas_of_conflict", "item_index": 1},
                    {"starts_at": time(2, 0), "ends_at": time(3, 30), "container_key": "deep_current", "item_index": 1},
                    {"starts_at": time(3, 30), "ends_at": time(4, 30), "container_key": "pulse_report_weekly", "item_index": 2},
                    {"starts_at": time(4, 30), "ends_at": time(5, 30), "container_key": "atlas_of_conflict", "item_index": 2},
                    {"starts_at": time(5, 30), "ends_at": time(6, 30), "container_key": "pulse_report_weekly", "item_index": 3},
                    {"starts_at": time(6, 30), "ends_at": time(7, 30), "container_key": "atlas_of_conflict", "item_index": 3},
                    {"starts_at": time(7, 30), "ends_at": time(8, 30), "container_key": "pulse_report_weekly", "item_index": 4},
                    {"starts_at": time(8, 30), "ends_at": time(10, 0), "container_key": "deep_current", "item_index": 1},
                    {"starts_at": time(10, 0), "ends_at": time(11, 0), "container_key": "pulse_report_weekly", "item_index": 5},
                    {"starts_at": time(11, 0), "ends_at": time(12, 0), "container_key": "atlas_of_conflict", "item_index": 1},
                    {"starts_at": time(12, 0), "ends_at": time(13, 0), "container_key": "pulse_report_weekly", "item_index": 1},
                    {"starts_at": time(13, 0), "ends_at": time(14, 0), "container_key": "atlas_of_conflict", "item_index": 2},
                    {"starts_at": time(14, 0), "ends_at": time(15, 30), "container_key": "deep_current", "item_index": 1},
                    {"starts_at": time(15, 30), "ends_at": time(16, 30), "container_key": "pulse_report_weekly", "item_index": 2},
                    {"starts_at": time(16, 30), "ends_at": time(17, 0), "container_key": "pulse_report_weekly", "item_index": 3},
                    {"starts_at": time(17, 0), "ends_at": time(18, 0), "container_key": "pulse_report_weekly", "item_index": 1},
                    {"starts_at": time(18, 0), "ends_at": time(19, 0), "container_key": "pulse_report_weekly", "item_index": 2},
                    {"starts_at": time(19, 0), "ends_at": time(20, 0), "container_key": "atlas_of_conflict", "item_index": 1},
                    {"starts_at": time(20, 0), "ends_at": time(21, 0), "container_key": "atlas_of_conflict", "item_index": 2},
                    {"starts_at": time(21, 15), "ends_at": time(22, 45), "container_key": "deep_current", "item_index": 1},
                    {"starts_at": time(22, 45), "ends_at": time(23, 30), "container_key": "pulse_report_weekly", "item_index": 3},
                    {"starts_at": time(23, 30), "ends_at": time(0, 0), "container_key": "pulse_report_weekly", "item_index": 4},
                ],
            },
            {
                "name": "Velvet Rewind",
                "description": "Comfort sitcoms, dry stage banter and relaxed late-evening comedy.",
                "specification": "A comedy lane for repeatable half-hours, stand-up showcases and easywatching evening sessions.",
                "analyze_status": AnalyzeStatus.COMPLETE,
                "external_playout_id": None,
                "editorial": {
                    "allowed_categories": ["comedy", "sitcom", "late-night"],
                    "preferred_categories": ["comedy", "comfort"],
                    "allowed_natures": [MediaNature.SHOW],
                    "allowed_container_kinds": [MediaContainerKind.SERIES],
                    "start_at": time(18, 30),
                    "end_at": time(23, 30),
                    "allow_filler": True,
                },
                "blocks": [
                    {"starts_at": time(18, 30), "ends_at": time(19, 0), "container_key": "velvet_rewind_show", "item_index": 1},
                    {"starts_at": time(19, 15), "ends_at": time(19, 45), "container_key": "second_balcony_live", "item_index": 1},
                    {"starts_at": time(20, 0), "ends_at": time(20, 30), "container_key": "velvet_rewind_show", "item_index": 2},
                    {"starts_at": time(20, 45), "ends_at": time(21, 15), "container_key": "second_balcony_live", "item_index": 2},
                    {"starts_at": time(21, 30), "ends_at": time(22, 0), "container_key": "velvet_rewind_show", "item_index": 3},
                    {"starts_at": time(22, 0), "ends_at": time(22, 30), "container_key": "velvet_rewind_show", "item_index": 4},
                    {"starts_at": time(22, 45), "ends_at": time(23, 15), "container_key": "second_balcony_live", "item_index": 3},
                ],
            },
            {
                "name": "Backstage Sessions",
                "description": "Live performance recordings, intimate sets and after-dark music sessions.",
                "specification": "Music channel centered on short live sessions, acoustic cuts and rooftop concert blocks.",
                "analyze_status": AnalyzeStatus.COMPLETE,
                "external_playout_id": None,
                "editorial": {
                    "allowed_categories": ["music", "live", "concert"],
                    "preferred_categories": ["music", "session"],
                    "allowed_natures": [MediaNature.MUSIC],
                    "allowed_container_kinds": [MediaContainerKind.MUSIC_VIDEO_RELEASE],
                    "start_at": time(19, 0),
                    "end_at": time(1, 0),
                    "allow_filler": True,
                },
                "blocks": [
                    {"starts_at": time(19, 0), "ends_at": time(19, 30), "container_key": "backstage_sessions_paris", "item_index": 1},
                    {"starts_at": time(19, 45), "ends_at": time(20, 15), "container_key": "city_lights_live", "item_index": 1},
                    {"starts_at": time(21, 0), "ends_at": time(21, 30), "container_key": "city_lights_live", "item_index": 1},
                    {"starts_at": time(21, 45), "ends_at": time(22, 15), "container_key": "backstage_sessions_paris", "item_index": 2},
                    {"starts_at": time(23, 0), "ends_at": time(23, 30), "container_key": "backstage_sessions_paris", "item_index": 2},
                    {"starts_at": time(23, 40), "ends_at": time(0, 10), "container_key": "city_lights_live", "item_index": 2},
                ],
            },
        ]

        for channel_spec in channel_specs:
            channel = TvChannel.objects.create(
                name=channel_spec["name"],
                description=channel_spec["description"],
                specification=channel_spec["specification"],
                catalog=catalog,
                is_enabled=True,
                analyze_status=channel_spec["analyze_status"],
                external_playout_id=channel_spec["external_playout_id"],
            )
            cls._attach_logo_if_available(channel)
            editorial_data = channel_spec["editorial"]
            EditorialLine.objects.create(
                tv_channel=channel,
                allowed_categories=editorial_data.get("allowed_categories", []),
                forbidden_categories=editorial_data.get("forbidden_categories", []),
                preferred_categories=editorial_data.get("preferred_categories", []),
                allowed_natures=editorial_data.get("allowed_natures", []),
                forbidden_natures=editorial_data.get("forbidden_natures", []),
                preferred_natures=editorial_data.get("preferred_natures", []),
                allowed_container_kinds=editorial_data.get("allowed_container_kinds", []),
                forbidden_container_kinds=editorial_data.get("forbidden_container_kinds", []),
                preferred_container_kinds=editorial_data.get("preferred_container_kinds", []),
                start_at=editorial_data["start_at"],
                end_at=editorial_data["end_at"],
                allow_filler=editorial_data["allow_filler"],
            )
            grid = GridLayout.objects.create(tv_channel=channel, is_active=True)
            playout = TvPlayout.objects.create(tv_channel=channel, is_active=True, grid=grid)
            cls._create_blocks_and_schedule(
                day=day,
                grid=grid,
                playout=playout,
                block_specs=channel_spec["blocks"],
                containers=containers,
                default_filler_policy=filler_policies["late_bridge"],
            )

    @classmethod
    def _create_blocks_and_schedule(
        cls,
        *,
        day: date,
        grid: GridLayout,
        playout: TvPlayout,
        block_specs: list[dict],
        containers: dict[str, MediaContainer],
        default_filler_policy: FillerPolicy,
    ):
        for order, block_spec in enumerate(block_specs):
            block = GridBlock.objects.create(
                grid_layout=grid,
                starts_at=block_spec["starts_at"],
                ends_at=block_spec["ends_at"],
                priority=50 + order,
                min_items=1,
                max_items=1,
                min_duration_seconds_per_item=None,
                max_duration_seconds_per_item=None,
                allowed_categories=[],
                forbidden_categories=[],
                preferred_categories=[],
                allowed_natures=[],
                forbidden_natures=[],
                preferred_natures=[],
                allowed_container_kinds=[],
                forbidden_container_kinds=[],
                preferred_container_kinds=[],
                post_filler_policy=default_filler_policy,
            )
            container = containers[block_spec["container_key"]]
            item = cls._get_container_item(container, block_spec["item_index"])
            selection = BlockContainerSelection.objects.create(
                order=order,
                planned_item_count=1,
                status=ScheduledContainerStatus.COMPLETED,
                media_container=container,
                block=block,
                tv_playout=playout,
                last_scheduled_item=item,
            )
            start_at = cls._aware_datetime(day, block_spec["starts_at"])
            block_end_at = cls._block_end_datetime(day, block_spec["starts_at"], block_spec["ends_at"])
            item_end_at = start_at + timedelta(seconds=item.duration_seconds or 0)
            end_at = min(item_end_at, block_end_at)
            ScheduleMediaItem.objects.create(
                added_to_playout=True,
                starts_at=start_at,
                ends_at=end_at,
                item=item,
                block_container_selection=selection,
            )

    @classmethod
    def _get_container_item(cls, container: MediaContainer, item_index: int) -> MediaItem:
        return container.items.order_by("episode_number", "sequence_number", "id")[item_index - 1]

    @classmethod
    def _aware_datetime(cls, day: date, value: time) -> datetime:
        return timezone.make_aware(datetime.combine(day, value), timezone.get_current_timezone())

    @classmethod
    def _block_end_datetime(cls, day: date, starts_at: time, ends_at: time) -> datetime:
        start = cls._aware_datetime(day, starts_at)
        end = cls._aware_datetime(day, ends_at)
        if end <= start:
            end += timedelta(days=1)
        return end

    @classmethod
    def _attach_logo_if_available(cls, channel: TvChannel):
        image_directory = Path(__file__).resolve().parent / "data" / "images"
        if not image_directory.exists():
            return
        for extension in cls.IMAGE_EXTENSIONS:
            file_path = image_directory / f"{channel.name}.{extension}"
            if not file_path.exists():
                continue
            with file_path.open("rb") as image_file:
                channel.logo.save(file_path.name, File(image_file), save=True)
            return
