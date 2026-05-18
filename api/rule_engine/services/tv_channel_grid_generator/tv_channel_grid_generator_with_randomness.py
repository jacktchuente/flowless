from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import TypedDict

from media_source.constants import MediaNature


SLOTS_STANDARD_BY_NATURE = {
    MediaNature.FICTION: [(18, 30), (38, 58), (75, 115), (115, 160)],
    MediaNature.DOCUMENTARY: [(20, 30), (40, 60), (75, 100), (100, 140)],
    MediaNature.SHOW: [(20, 35), (40, 65), (75, 110), (110, 180)],
}


class TvChannelGridGeneratorPayload(TypedDict, total=False):
    name: str
    description: str
    specification: str
    start_at: time
    end_at: time
    preferred_categories: list[str]
    forbidden_categories: list[str]
    allowed_categories: list[str]
    preferred_natures: list[int]
    forbidden_natures: list[int]
    allowed_natures: list[int]
    preferred_container_kinds: list[int]
    forbidden_container_kinds: list[int]
    allowed_container_kinds: list[int]
    allow_filler: bool


@dataclass(frozen=True)
class PreparedGridBlock:
    starts_at: time
    ends_at: time
    priority: int
    min_items: int
    max_items: int
    min_duration_seconds_per_item: int | None
    max_duration_seconds_per_item: int | None
    allowed_categories: list[str]
    forbidden_categories: list[str]
    preferred_categories: list[str]
    allowed_natures: list[int]
    forbidden_natures: list[int]
    preferred_natures: list[int]
    allowed_container_kinds: list[int]
    forbidden_container_kinds: list[int]
    preferred_container_kinds: list[int]


class TvChannelGridGeneratorWithRandomness:
    BASE_DATE = date(2000, 1, 1)
    MIN_BLOCK_DURATION_MINUTES = 30
    MAX_BLOCK_ITEMS = 3

    def __init__(self, tv_channel_data: TvChannelGridGeneratorPayload, *, seed: int | str | None = None):
        self.tv_channel_data = tv_channel_data
        self.start_at = tv_channel_data["start_at"]
        self.end_at = tv_channel_data["end_at"]

        self.preferred_categories = self._clean_strings(tv_channel_data.get("preferred_categories", []))
        self.forbidden_categories = self._clean_strings(tv_channel_data.get("forbidden_categories", []))
        self.allowed_categories = self._clean_strings(tv_channel_data.get("allowed_categories", []))
        self.preferred_natures = self._clean_ints(tv_channel_data.get("preferred_natures", []))
        self.forbidden_natures = self._clean_ints(tv_channel_data.get("forbidden_natures", []))
        self.allowed_natures = self._clean_ints(tv_channel_data.get("allowed_natures", []))
        self.preferred_container_kinds = self._clean_ints(tv_channel_data.get("preferred_container_kinds", []))
        self.forbidden_container_kinds = self._clean_ints(tv_channel_data.get("forbidden_container_kinds", []))
        self.allowed_container_kinds = self._clean_ints(tv_channel_data.get("allowed_container_kinds", []))
        self.allow_filler = bool(tv_channel_data.get("allow_filler", True))
        self.random = random.Random(seed)

    def get_blocks(self) -> list[PreparedGridBlock]:
        window_start, window_end = self._build_window()
        blocks: list[PreparedGridBlock] = []
        cursor = window_start

        while cursor < window_end:
            remaining_minutes = int((window_end - cursor).total_seconds() / 60)
            if remaining_minutes < self.MIN_BLOCK_DURATION_MINUTES:
                if blocks:
                    previous = blocks[-1]
                    blocks[-1] = PreparedGridBlock(**{**previous.__dict__, "ends_at": window_end.time()})
                break

            selected_natures = self._select_natures()
            min_minutes, max_minutes = self._get_duration_standard_for_natures(selected_natures)
            max_items = self._select_max_items(
                remaining_minutes=remaining_minutes,
                min_minutes_per_item=min_minutes,
            )
            block_duration_minutes = self._select_block_duration_minutes(
                min_minutes_per_item=min_minutes,
                max_minutes_per_item=max_minutes,
                max_items=max_items,
                remaining_minutes=remaining_minutes,
            )
            block_end = min(cursor + timedelta(minutes=block_duration_minutes), window_end)

            blocks.append(
                PreparedGridBlock(
                    starts_at=cursor.time(),
                    ends_at=block_end.time(),
                    priority=self._compute_priority(cursor.time()),
                    min_items=1,
                    max_items=max_items,
                    min_duration_seconds_per_item=min_minutes * 60,
                    max_duration_seconds_per_item=max_minutes * 60,
                    allowed_categories=self._select_allowed_categories(),
                    forbidden_categories=self.forbidden_categories,
                    preferred_categories=self._select_preferred_categories(),
                    allowed_natures=selected_natures,
                    forbidden_natures=self.forbidden_natures,
                    preferred_natures=self._select_preferred_natures(selected_natures),
                    allowed_container_kinds=self._select_allowed_container_kinds(),
                    forbidden_container_kinds=self.forbidden_container_kinds,
                    preferred_container_kinds=self._select_preferred_container_kinds(),
                )
            )
            cursor = block_end

        return blocks

    def _build_window(self) -> tuple[datetime, datetime]:
        start = datetime.combine(self.BASE_DATE, self.start_at)
        end = datetime.combine(self.BASE_DATE, self.end_at)
        if end <= start:
            end += timedelta(days=1)
        return start, end

    def _select_natures(self) -> list[int]:
        available_natures = [nature for nature in SLOTS_STANDARD_BY_NATURE.keys() if nature not in self.forbidden_natures]
        if self.allowed_natures:
            pool = [nature for nature in self.allowed_natures if nature in available_natures]
        elif self.preferred_natures:
            pool = [nature for nature in self.preferred_natures if nature in available_natures]
        else:
            pool = available_natures
        if not pool:
            pool = available_natures
        if not pool:
            return []
        max_count = min(2, len(pool))
        count = self.random.choice([1, 1, 1, max_count])
        return self.random.sample(pool, k=count)

    def _get_duration_standard_for_natures(self, natures: list[int]) -> tuple[int, int]:
        ranges = [self.random.choice(SLOTS_STANDARD_BY_NATURE.get(nature) or []) for nature in natures if SLOTS_STANDARD_BY_NATURE.get(nature)]
        if not ranges:
            ranges = [(40, 90)]
        return min(item[0] for item in ranges), max(item[1] for item in ranges)

    def _select_max_items(self, *, remaining_minutes: int, min_minutes_per_item: int) -> int:
        theoretical_max = max(1, remaining_minutes // min_minutes_per_item)
        max_possible = min(self.MAX_BLOCK_ITEMS, theoretical_max)
        if max_possible <= 1:
            return 1
        if max_possible == 2:
            return self.random.choice([1, 2, 2])
        return self.random.choice([1, 2, 2, 3])

    def _select_block_duration_minutes(
        self,
        *,
        min_minutes_per_item: int,
        max_minutes_per_item: int,
        max_items: int,
        remaining_minutes: int,
    ) -> int:
        min_duration = min_minutes_per_item * max_items
        max_duration = min(max_minutes_per_item * max_items, remaining_minutes)
        if max_duration < self.MIN_BLOCK_DURATION_MINUTES:
            return remaining_minutes
        min_duration = max(self.MIN_BLOCK_DURATION_MINUTES, min(min_duration, max_duration))
        return self._round_to_nearest_15_minutes(self.random.randint(min_duration, max_duration))

    @staticmethod
    def _round_to_nearest_15_minutes(minutes: int) -> int:
        return max(15, round(minutes / 15) * 15)

    def _select_allowed_categories(self) -> list[str]:
        forbidden = set(self.forbidden_categories)
        allowed = [category for category in self.allowed_categories if category not in forbidden]
        preferred = [category for category in self.preferred_categories if category not in forbidden and category not in allowed]
        if allowed:
            allowed_count = self.random.randint(1, min(3, len(allowed)))
            selected = self.random.sample(allowed, k=allowed_count)
            if preferred and self.random.random() < 0.4:
                selected.append(self.random.choice(preferred))
            return self._unique_strings(selected)
        if preferred:
            preferred_count = self.random.randint(1, min(2, len(preferred)))
            return self._unique_strings(self.random.sample(preferred, k=preferred_count))
        return []

    def _select_preferred_categories(self) -> list[str]:
        pool = [category for category in self.preferred_categories if category not in self.forbidden_categories]
        if not pool:
            return []
        count = self.random.randint(1, min(3, len(pool)))
        return self._unique_strings(self.random.sample(pool, k=count))

    def _select_preferred_natures(self, selected_natures: list[int]) -> list[int]:
        pool = [nature for nature in self.preferred_natures if nature in selected_natures] or selected_natures[:]
        if not pool:
            return []
        count = self.random.randint(1, min(len(pool), 2))
        return self._clean_ints(self.random.sample(pool, k=count))

    def _select_allowed_container_kinds(self) -> list[int]:
        forbidden = set(self.forbidden_container_kinds)
        allowed = [kind for kind in self.allowed_container_kinds if kind not in forbidden]
        preferred = [kind for kind in self.preferred_container_kinds if kind not in forbidden and kind not in allowed]
        if allowed:
            count = self.random.randint(1, min(2, len(allowed)))
            selected = self.random.sample(allowed, k=count)
            if preferred and self.random.random() < 0.4:
                selected.append(self.random.choice(preferred))
            return self._clean_ints(selected)
        if preferred:
            count = self.random.randint(1, min(2, len(preferred)))
            return self._clean_ints(self.random.sample(preferred, k=count))
        return []

    def _select_preferred_container_kinds(self) -> list[int]:
        pool = [kind for kind in self.preferred_container_kinds if kind not in self.forbidden_container_kinds]
        if not pool:
            return []
        count = self.random.randint(1, min(2, len(pool)))
        return self._clean_ints(self.random.sample(pool, k=count))

    @staticmethod
    def _compute_priority(starts_at: time) -> int:
        if time(19, 0) <= starts_at <= time(23, 0):
            return 90
        if time(6, 0) <= starts_at <= time(10, 0):
            return 70
        if time(23, 0) <= starts_at or starts_at <= time(2, 0):
            return 50
        return 60

    @staticmethod
    def _unique_strings(values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            if isinstance(value, str) and value and value not in cleaned:
                cleaned.append(value)
        return cleaned

    @staticmethod
    def _clean_strings(values: list[str]) -> list[str]:
        return TvChannelGridGeneratorWithRandomness._unique_strings(values)

    @staticmethod
    def _clean_ints(values: list[int]) -> list[int]:
        cleaned: list[int] = []
        for value in values:
            if isinstance(value, int) and value not in cleaned:
                cleaned.append(value)
        return cleaned
