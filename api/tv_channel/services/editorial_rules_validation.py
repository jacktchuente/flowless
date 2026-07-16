"""Shared validation for manually edited editorial rules.

The rule-engine generators still contain private equivalents. Keeping this module
independent avoids changing generation behaviour while giving API writes and LLM
suggestions one validation source of truth.
"""

from django.core.exceptions import ValidationError

from media_source.constants import MediaContainerKind, MediaNature
from rule_engine.services import category_service


RULE_AXES = ("categories", "natures", "container_kinds")
RULE_LEVELS = ("allowed", "forbidden", "preferred")


def _deduplicate(values):
    return list(dict.fromkeys(values))


def validate_categories(values: list) -> list[str]:
    if not isinstance(values, list):
        raise ValidationError("Must be a list.")
    known_categories = set(category_service.get_all_category_names())
    invalid = [value for value in values if not isinstance(value, str) or value not in known_categories]
    if invalid:
        raise ValidationError(f"Unknown categories: {invalid}.")
    return _deduplicate(values)


def _validate_choices(values: list, choices, label: str) -> list[int]:
    if not isinstance(values, list):
        raise ValidationError("Must be a list.")
    by_label = {choice.label: choice.value for choice in choices}
    valid_values = set(by_label.values())
    normalized = []
    invalid = []
    for value in values:
        if isinstance(value, bool):
            invalid.append(value)
        elif isinstance(value, int) and value in valid_values:
            normalized.append(value)
        elif isinstance(value, str) and value in by_label:
            normalized.append(by_label[value])
        else:
            invalid.append(value)
    if invalid:
        raise ValidationError(f"Unknown {label}: {invalid}.")
    return _deduplicate(normalized)


def validate_natures(values: list) -> list[int]:
    return _validate_choices(values, MediaNature, "natures")


def validate_container_kinds(values: list) -> list[int]:
    return _validate_choices(values, MediaContainerKind, "container kinds")


def ensure_no_overlap(a: list, b: list, field_a: str, field_b: str) -> None:
    overlap = set(a).intersection(b)
    if overlap:
        raise ValidationError({field_a: f"Must not overlap with {field_b}: {sorted(overlap)}."})


AXIS_VALIDATORS = {
    "categories": validate_categories,
    "natures": validate_natures,
    "container_kinds": validate_container_kinds,
}


def validate_rule_level(value, level_name: str, *, lenient: bool = False) -> dict:
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise ValidationError({level_name: "Must be a dict keyed by rule axis."})
    unknown_axes = [axis for axis in value if axis not in RULE_AXES]
    if unknown_axes and not lenient:
        raise ValidationError({level_name: f"Unknown rule axes: {sorted(unknown_axes)}."})

    normalized = {}
    errors = []
    for axis in RULE_AXES:
        axis_values = value.get(axis, [])
        try:
            normalized[axis] = AXIS_VALIDATORS[axis](axis_values)
        except ValidationError as exc:
            if lenient and isinstance(axis_values, list):
                normalized[axis] = _lenient_filter(axis_values, axis)
            else:
                errors.extend(f"{axis}: {message}" for message in exc.messages)
    if errors:
        raise ValidationError({level_name: errors})
    return normalized


def _lenient_filter(values: list, axis: str) -> list:
    kept = []
    for value in values:
        try:
            kept.extend(AXIS_VALIDATORS[axis]([value]))
        except ValidationError:
            continue
    return _deduplicate(kept)


def validate_editorial_rules_payload(data: dict, *, lenient: bool = False) -> dict:
    normalized = dict(data)
    errors = {}
    for level in RULE_LEVELS:
        if level not in normalized:
            continue
        try:
            normalized[level] = validate_rule_level(normalized[level], level, lenient=lenient)
        except ValidationError as exc:
            errors.update(exc.message_dict)
    if errors:
        raise ValidationError(errors)

    forbidden = normalized.get("forbidden", {})
    for axis in RULE_AXES:
        for level in ("allowed", "preferred"):
            ensure_no_overlap(
                normalized.get(level, {}).get(axis, []),
                forbidden.get(axis, []),
                level,
                f"forbidden {axis}",
            )
    return normalized
