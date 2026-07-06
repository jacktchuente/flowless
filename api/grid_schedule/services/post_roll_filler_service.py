import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from django.db.models import Q

from grid_schedule.models import ScheduleMediaItem, TvPlayout
from media_source.constants import MediaProgrammingRole
from media_source.models import MediaItem
from media_source.services.trailer_link_service import TrailerLinkService

logger = logging.getLogger(__name__)

ROLE_BY_LABEL = {choice.label: choice for choice in MediaProgrammingRole}
DEFAULT_ALLOWED_ROLES = (MediaProgrammingRole.TRAILER, MediaProgrammingRole.FILLER)
UPCOMING_CONTAINER_LOOKAHEAD = 5


@dataclass
class FillerFillResult:
    created_items: int = 0
    warnings: list[str] = field(default_factory=list)


class PostRollFillerService:
    """Fills the post-roll windows of a playout with real interstitial items.

    Runs as a second pass once the main items are persisted, so trailer
    selection can look at what is actually scheduled next. Every created
    item is attached to its parent main item (role != MAIN, no selection);
    whatever cannot be filled stays covered by the ErsatzTV pad fallback.
    """

    def __init__(
        self,
        *,
        tv_playout: TvPlayout,
        window_start: datetime,
        window_end: datetime,
    ):
        self.tv_playout = tv_playout
        self.window_start = window_start
        self.window_end = window_end
        self.trailer_link_service = TrailerLinkService()
        self._filler_pools: dict[tuple[int, ...], list[MediaItem]] = {}
        self._used_item_ids: set[int] = set()
        self._random = random.Random()

    def fill(self) -> FillerFillResult:
        result = FillerFillResult()
        main_items = self._load_main_items()
        if not main_items:
            return result

        to_create: list[ScheduleMediaItem] = []
        windows_without_trailer = 0
        windows_without_filler = 0

        for index, main_item in enumerate(main_items):
            if main_item.post_roll_filler_ends_at is None:
                continue
            if main_item.starts_at < self.window_start or main_item.has_post_roll_children:
                continue

            allowed_roles = self._resolve_allowed_roles(main_item)
            if not allowed_roles:
                continue

            cursor = main_item.ends_at
            window_end = main_item.post_roll_filler_ends_at

            if MediaProgrammingRole.TRAILER in allowed_roles:
                trailer_entry = self._pick_trailer(
                    main_items=main_items,
                    current_index=index,
                    remaining_seconds=int((window_end - cursor).total_seconds()),
                )
                if trailer_entry is None:
                    windows_without_trailer += 1
                else:
                    scheduled = self._build_child(
                        main_item=main_item,
                        media_item=trailer_entry,
                        role=MediaProgrammingRole.TRAILER,
                        cursor=cursor,
                    )
                    to_create.append(scheduled)
                    cursor = scheduled.ends_at

            filler_roles = tuple(
                role for role in allowed_roles if role != MediaProgrammingRole.TRAILER
            )
            placed_filler = False
            if filler_roles:
                while True:
                    remaining_seconds = int((window_end - cursor).total_seconds())
                    if remaining_seconds <= 0:
                        break
                    filler_item = self._pick_filler(filler_roles, remaining_seconds)
                    if filler_item is None:
                        break
                    scheduled = self._build_child(
                        main_item=main_item,
                        media_item=filler_item,
                        role=self._container_role(filler_item),
                        cursor=cursor,
                    )
                    to_create.append(scheduled)
                    cursor = scheduled.ends_at
                    placed_filler = True
                if not placed_filler and cursor == main_item.ends_at:
                    windows_without_filler += 1

        if to_create:
            ScheduleMediaItem.objects.bulk_create(to_create)
        result.created_items = len(to_create)

        if windows_without_trailer:
            result.warnings.append(
                f"no-trailer-for-upcoming: {windows_without_trailer} post-roll window(s) "
                "had no matching trailer for the upcoming programs."
            )
        if windows_without_filler:
            result.warnings.append(
                f"no-filler-available: {windows_without_filler} post-roll window(s) "
                "could not be filled with any interstitial content."
            )
        return result

    def _load_main_items(self) -> list[ScheduleMediaItem]:
        items = list(
            ScheduleMediaItem.objects
            .filter(
                Q(block_container_selection__tv_playout=self.tv_playout)
                | Q(flexible_selection__tv_playout=self.tv_playout),
                role=MediaProgrammingRole.MAIN,
                starts_at__lt=self.window_end,
            )
            .select_related(
                "item__container",
                "block_container_selection__block__post_filler_policy",
            )
            .order_by("starts_at", "id")
        )
        with_children = set(
            ScheduleMediaItem.objects
            .filter(parent_schedule_item__in=[item.id for item in items])
            .values_list("parent_schedule_item_id", flat=True)
        )
        for item in items:
            item.has_post_roll_children = item.id in with_children
        return items

    def _resolve_allowed_roles(self, main_item: ScheduleMediaItem) -> tuple[MediaProgrammingRole, ...]:
        policy = None
        if main_item.block_container_selection_id is not None:
            policy = main_item.block_container_selection.block.post_filler_policy
        elif main_item.flexible_selection_id is not None:
            policy = self.tv_playout.grid.post_filler_policy
        if policy is None:
            return ()
        labels = [label for label in (policy.allowed_roles or []) if label in ROLE_BY_LABEL]
        if not labels:
            return DEFAULT_ALLOWED_ROLES
        return tuple(ROLE_BY_LABEL[label] for label in labels)

    def _pick_trailer(
        self,
        *,
        main_items: list[ScheduleMediaItem],
        current_index: int,
        remaining_seconds: int,
    ) -> MediaItem | None:
        current_container_id = main_items[current_index].item.container_id
        seen_container_ids: set[int] = set()
        for upcoming in main_items[current_index + 1:]:
            container = upcoming.item.container
            if container.id == current_container_id or container.id in seen_container_ids:
                continue
            seen_container_ids.add(container.id)
            if len(seen_container_ids) > UPCOMING_CONTAINER_LOOKAHEAD:
                break
            candidates = [
                trailer
                for trailer in self.trailer_link_service.find_trailer_items(container)
                if (trailer.duration_seconds or 0) <= remaining_seconds
            ]
            fresh = [c for c in candidates if c.id not in self._used_item_ids]
            pool = fresh or candidates
            if pool:
                chosen = self._random.choice(pool)
                self._used_item_ids.add(chosen.id)
                return chosen
        return None

    def _pick_filler(
        self,
        roles: tuple[MediaProgrammingRole, ...],
        remaining_seconds: int,
    ) -> MediaItem | None:
        pool = self._get_filler_pool(roles)
        fitting = [item for item in pool if (item.duration_seconds or 0) <= remaining_seconds]
        if not fitting:
            return None
        fresh = [item for item in fitting if item.id not in self._used_item_ids]
        chosen = self._random.choice(fresh or fitting)
        self._used_item_ids.add(chosen.id)
        return chosen

    def _get_filler_pool(self, roles: tuple[MediaProgrammingRole, ...]) -> list[MediaItem]:
        key = tuple(sorted(role.value for role in roles))
        if key not in self._filler_pools:
            self._filler_pools[key] = list(
                MediaItem.objects
                .filter(
                    container__media_collection__programming_role__in=roles,
                    container__media_collection__is_active=True,
                    duration_seconds__gt=0,
                )
                .select_related("container__media_collection")
            )
        return self._filler_pools[key]

    @staticmethod
    def _container_role(media_item: MediaItem) -> MediaProgrammingRole:
        role = media_item.container.media_collection.programming_role
        if role is None:
            return MediaProgrammingRole.FILLER
        return MediaProgrammingRole(role)

    def _build_child(
        self,
        *,
        main_item: ScheduleMediaItem,
        media_item: MediaItem,
        role: MediaProgrammingRole,
        cursor: datetime,
    ) -> ScheduleMediaItem:
        return ScheduleMediaItem(
            added_to_playout=False,
            starts_at=cursor,
            ends_at=cursor + timedelta(seconds=media_item.duration_seconds or 0),
            item=media_item,
            role=role,
            parent_schedule_item=main_item,
            post_roll_filler_ends_at=None,
        )
