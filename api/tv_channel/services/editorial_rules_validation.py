"""Shared validation for manually edited editorial rules.

The rule-engine generators still contain private equivalents. Keeping this module
independent avoids changing generation behaviour while giving API writes and LLM
suggestions one validation source of truth.
"""

from django.core.exceptions import ValidationError

from media_source.constants import MediaContainerKind, MediaNature
from media_source.data import categories


RULE_AXES = ("categories", "natures", "container_kinds")
RULE_LEVELS = ("allowed", "forbidden", "preferred")
RULE_FIELDS = tuple(f"{level}_{axis}" for axis in RULE_AXES for level in RULE_LEVELS)


def _deduplicate(values):
    return list(dict.fromkeys(values))


def validate_categories(values: list) -> list[str]:
    if not isinstance(values, list):
        raise ValidationError("Must be a list.")
    invalid = [value for value in values if not isinstance(value, str) or value not in categories]
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


def validate_editorial_rules_payload(data: dict) -> dict:
    normalized = dict(data)
    errors = {}
    validators = {
        "categories": validate_categories,
        "natures": validate_natures,
        "container_kinds": validate_container_kinds,
    }
    for axis, validator in validators.items():
        for level in RULE_LEVELS:
            field = f"{level}_{axis}"
            if field not in normalized:
                continue
            try:
                normalized[field] = validator(normalized[field])
            except ValidationError as exc:
                errors[field] = exc.messages
    if errors:
        raise ValidationError(errors)

    for axis in RULE_AXES:
        forbidden_field = f"forbidden_{axis}"
        forbidden = normalized.get(forbidden_field, [])
        for level in ("allowed", "preferred"):
            field = f"{level}_{axis}"
            ensure_no_overlap(normalized.get(field, []), forbidden, field, forbidden_field)
    return normalized
