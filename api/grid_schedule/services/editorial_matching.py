"""
Editorial rule matching shared by the schedulers.

A "rules source" is any object carrying `allowed` / `preferred` / `forbidden`
dicts keyed by rule axis (EditorialLine, GridBlock): the fixed pipeline
stacks editorial line + block, the marathon pipeline uses the editorial line
alone.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from media_source.models import MediaContainer
from tv_channel.services.editorial_rules_validation import STRING_RULE_AXES
from tv_channel.services import numeric_rules


def container_categories(container: MediaContainer) -> set[str]:
    return {
        value
        for value in (container.categories or [])
        if isinstance(value, str) and value
    }


def container_axis_values(container: MediaContainer, axis: str) -> set[str]:
    if axis == "categories":
        return container_categories(container)
    return {
        value
        for value in (getattr(container, axis) or [])
        if isinstance(value, str) and value
    }


def container_nature(container: MediaContainer):
    return getattr(container.media_collection, "nature", None)


def container_kind(container: MediaContainer):
    return getattr(container.media_collection, "container_kind", None)


def choice_values(values: Iterable) -> set[str]:
    normalized: set[str] = set()
    for value in values:
        if value is None:
            continue
        normalized.add(str(value))
        enum_value = getattr(value, "value", None)
        if enum_value is not None:
            normalized.add(str(enum_value))
        enum_name = getattr(value, "name", None)
        if enum_name is not None:
            normalized.add(str(enum_name))
    return normalized


def passes_allowed_values(container_values: set[str], allowed_values: list[str]) -> bool:
    values = {_normalize_text(value) for value in container_values if isinstance(value, str)}
    allowed = {_normalize_text(value) for value in (allowed_values or []) if isinstance(value, str)}
    if not allowed:
        return True
    return bool(values.intersection(allowed))


def intersects(left: set[str], right: list[str]) -> bool:
    left_values = {_normalize_text(value) for value in left if isinstance(value, str)}
    right_values = {_normalize_text(value) for value in (right or []) if isinstance(value, str)}
    return bool(left_values.intersection(right_values))


def passes_allowed_choice(value, allowed_values: list) -> bool:
    allowed = choice_values(allowed_values or [])
    if not allowed:
        return True
    return bool(choice_values([value]).intersection(allowed))


def matches_forbidden_choice(value, forbidden_values: list) -> bool:
    forbidden = choice_values(forbidden_values or [])
    if not forbidden:
        return False
    return bool(choice_values([value]).intersection(forbidden))


def preferred_values_bonus(values: set[str], preferred_values: list[str]) -> float:
    normalized_values = {_normalize_text(value) for value in values if isinstance(value, str)}
    preferred = {_normalize_text(value) for value in preferred_values if isinstance(value, str)}
    return float(len(normalized_values.intersection(preferred)))


def _normalize_text(value: str) -> str:
    return value.strip().casefold()


def preferred_choice_bonus(value, preferred_values: list) -> float:
    preferred = choice_values(preferred_values or [])
    if not preferred:
        return 0.0
    return 1.0 if choice_values([value]).intersection(preferred) else 0.0


def container_passes_rules(container: MediaContainer, rules_sources: Sequence) -> bool:
    for axis in STRING_RULE_AXES:
        values = container_axis_values(container, axis)
        for source in rules_sources:
            if not passes_allowed_values(values, source.allowed.get(axis, [])):
                return False
            if intersects(values, source.forbidden.get(axis, [])):
                return False

    nature = container_nature(container)
    kind = container_kind(container)
    for source in rules_sources:
        allowed_comparisons = source.allowed.get(numeric_rules.COMPARISON_AXIS, [])
        if not all(numeric_rules.matches(container, comparison) for comparison in allowed_comparisons):
            return False
        forbidden_comparisons = source.forbidden.get(numeric_rules.COMPARISON_AXIS, [])
        if any(numeric_rules.matches(container, comparison) for comparison in forbidden_comparisons):
            return False
        if not passes_allowed_choice(nature, source.allowed.get("natures", [])):
            return False
        if matches_forbidden_choice(nature, source.forbidden.get("natures", [])):
            return False
        if not passes_allowed_choice(kind, source.allowed.get("container_kinds", [])):
            return False
        if matches_forbidden_choice(kind, source.forbidden.get("container_kinds", [])):
            return False
    return True


def preferred_bonus(container: MediaContainer, rules_sources: Sequence) -> float:
    total = 0.0
    for axis in STRING_RULE_AXES:
        preferred: list[str] = []
        for source in rules_sources:
            preferred += source.preferred.get(axis, [])
        total += preferred_values_bonus(container_axis_values(container, axis), preferred)

    natures_preferred: list = []
    kinds_preferred: list = []
    for source in rules_sources:
        total += numeric_rules.preferred_bonus(
            container,
            source.preferred.get(numeric_rules.COMPARISON_AXIS, []),
        )
        natures_preferred += source.preferred.get("natures", [])
        kinds_preferred += source.preferred.get("container_kinds", [])
    total += preferred_choice_bonus(container_nature(container), natures_preferred)
    total += preferred_choice_bonus(container_kind(container), kinds_preferred)
    return total
