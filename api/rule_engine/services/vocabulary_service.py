"""Acces au vocabulaire des axes de regles editoriales.

La base de donnees est la source de verite : pas de cache module, chaque
appel relit les tables. Les categories restent portees par le modele
Category (structure nature/rules dediee) ; les autres axes vivent dans
VocabularyEntry.
"""

from collections.abc import Iterable

from django.db import transaction

from media_source.models import MediaContainer
from project_ops.constants import AnalyzeStatus
from rule_engine.models import VocabularyEntry
from rule_engine.services import category_service


# Axes a valeurs ouvertes stockes dans VocabularyEntry. Chaque axe porte le
# nom du champ homonyme de MediaContainer.
VOCABULARY_AXES = (
    "genres",
    "tags",
    "directors",
    "writers",
    "creators",
    "actors",
    "studios",
    "countries",
    "audio_languages",
    "subtitle_languages",
)

VALUE_MAX_LENGTH = 255


def get_values(axis: str) -> list[str]:
    if axis == "categories":
        return category_service.get_all_category_names()
    if axis not in VOCABULARY_AXES:
        raise ValueError(f"Unknown vocabulary axis: {axis}.")
    return list(
        VocabularyEntry.objects
        .filter(axis=axis)
        .order_by("value")
        .values_list("value", flat=True)
    )


def search(query: str, limit: int = 20) -> list[dict[str, str]]:
    return [
        {"axis": entry.axis, "value": entry.value}
        for entry in (
            VocabularyEntry.objects
            .filter(value__icontains=query)
            .order_by("axis", "value")[:limit]
        )
    ]


def upsert_values(mapping: dict[str, Iterable[str]]) -> None:
    entries = [
        VocabularyEntry(axis=axis, value=value)
        for axis, values in mapping.items()
        if axis in VOCABULARY_AXES
        for value in _normalized(values)
    ]
    if entries:
        VocabularyEntry.objects.bulk_create(entries, ignore_conflicts=True)


def rebuild() -> None:
    """Recale le vocabulaire sur les containers actifs (ajouts + orphelins).

    Idempotent : sert aussi de backfill initial. Agregation en Python pour
    rester portable entre SQLite (dev) et PostgreSQL (prod).
    """
    expected: dict[str, set[str]] = {axis: set() for axis in VOCABULARY_AXES}

    containers = (
        MediaContainer.objects
        .filter(
            analyze_status=AnalyzeStatus.COMPLETE,
            media_collection__is_active=True,
            is_missing=False,
        )
        .values_list(*VOCABULARY_AXES)
    )
    for row in containers.iterator():
        for axis, values in zip(VOCABULARY_AXES, row):
            expected[axis].update(_normalized(values))

    with transaction.atomic():
        for axis in VOCABULARY_AXES:
            existing = set(
                VocabularyEntry.objects
                .filter(axis=axis)
                .values_list("value", flat=True)
            )
            orphans = existing - expected[axis]
            if orphans:
                VocabularyEntry.objects.filter(axis=axis, value__in=orphans).delete()
            missing = expected[axis] - existing
            if missing:
                VocabularyEntry.objects.bulk_create(
                    [VocabularyEntry(axis=axis, value=value) for value in sorted(missing)],
                    ignore_conflicts=True,
                )


def _normalized(values) -> set[str]:
    if not isinstance(values, (list, tuple, set)):
        return set()
    return {
        value
        for value in values
        if isinstance(value, str) and value and len(value) <= VALUE_MAX_LENGTH
    }
