from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


COMPARISON_AXIS = "comparisons"
OPERATORS = frozenset({"gt", "gte", "lt", "lte", "eq", "neq"})


@dataclass(frozen=True)
class NumericFieldSpec:
    integer: bool
    minimum: float
    maximum: float


NUMERIC_FIELDS = {
    "min_age": NumericFieldSpec(True, 0, 100),
    "max_age": NumericFieldSpec(True, 0, 100),
    "release_year": NumericFieldSpec(True, 1800, 3000),
    "overall_rating_score": NumericFieldSpec(False, 0, 10),
    "community_rating_score": NumericFieldSpec(False, 0, 10),
    "critic_rating_score": NumericFieldSpec(False, 0, 100),
    "star_rating": NumericFieldSpec(False, 0, 5),
    "item_count": NumericFieldSpec(True, 0, 1_000_000),
    "duration_min_seconds": NumericFieldSpec(True, 0, 100_000_000),
    "duration_max_seconds": NumericFieldSpec(True, 0, 100_000_000),
    "total_duration_seconds": NumericFieldSpec(True, 0, 1_000_000_000),
    "min_video_width": NumericFieldSpec(True, 0, 100_000),
    "min_video_height": NumericFieldSpec(True, 0, 100_000),
}


def normalize_comparison(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Each comparison must be an object.")
    if set(value) != {"field", "operator", "value"}:
        raise ValueError("A comparison must contain exactly field, operator and value.")

    field = value.get("field")
    operator = value.get("operator")
    number = value.get("value")
    if field not in NUMERIC_FIELDS:
        raise ValueError(f"Unknown numeric field: {field}.")
    if operator not in OPERATORS:
        raise ValueError(f"Unknown numeric operator: {operator}.")
    if isinstance(number, bool) or not isinstance(number, (int, float)) or not isfinite(number):
        raise ValueError("Comparison value must be a finite number.")

    spec = NUMERIC_FIELDS[field]
    if spec.integer and (not isinstance(number, int) or isinstance(number, bool)):
        raise ValueError(f"{field} requires an integer value.")
    if not spec.minimum <= number <= spec.maximum:
        raise ValueError(f"{field} must be between {spec.minimum:g} and {spec.maximum:g}.")
    return {"field": field, "operator": operator, "value": number}


def comparison_key(comparison: dict) -> tuple:
    return comparison["field"], comparison["operator"], comparison["value"]


def matches(container, comparison: dict) -> bool:
    field = comparison["field"]
    operator = comparison["operator"]
    expected = comparison["value"]

    if field == "release_year":
        return _matches_release_year(container, operator, expected)
    actual = _resolve_value(container, field)
    if actual is None:
        return False
    return _compare(actual, operator, expected)


def preferred_bonus(container, comparisons: list[dict]) -> float:
    return float(sum(1 for comparison in comparisons if matches(container, comparison)))


def _resolve_value(container, field: str):
    if field == "star_rating":
        rating = container.overall_rating_score
        if rating is None:
            rating = container.community_rating_score
        return rating / 2 if rating is not None else None
    return getattr(container, field, None)


def _matches_release_year(container, operator: str, expected: int) -> bool:
    start = container.release_year_min
    end = container.release_year_max
    if operator in {"gt", "gte"}:
        return start is not None and _compare(start, operator, expected)
    if operator in {"lt", "lte"}:
        return end is not None and _compare(end, operator, expected)
    if start is None or end is None:
        return False
    is_exact_year = start == expected and end == expected
    return is_exact_year if operator == "eq" else not is_exact_year


def _compare(actual: float, operator: str, expected: float) -> bool:
    if operator == "gt":
        return actual > expected
    if operator == "gte":
        return actual >= expected
    if operator == "lt":
        return actual < expected
    if operator == "lte":
        return actual <= expected
    if operator == "eq":
        return actual == expected
    return actual != expected
