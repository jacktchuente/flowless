"""Acces au vocabulaire de categories.

La base de donnees est la source de verite : pas de cache module, chaque
appel relit les tables pour voir les editions utilisateur immediatement.
"""

from django.db.models import Q

from media_source.constants import MediaNature
from rule_engine.models import Category


def get_all_category_names() -> list[str]:
    return list(Category.objects.order_by("category").values_list("category", flat=True))


def get_category_names_for_nature(nature: int) -> list[str]:
    # Convention : une categorie sans aucun lien CategoryNature est valable
    # pour toutes les natures.
    return list(
        Category.objects
        .filter(Q(nature_links__isnull=True) | Q(nature_links__nature=nature))
        .distinct()
        .order_by("category")
        .values_list("category", flat=True)
    )


def get_music_category_names() -> set[str]:
    # Lien strict uniquement (pas de repli "0 lien = toutes") : seules les
    # categories explicitement musicales forment le vocabulaire musical.
    return set(
        Category.objects
        .filter(nature_links__nature=MediaNature.MUSIC)
        .values_list("category", flat=True)
    )


def get_general_category_names() -> list[str]:
    music = get_music_category_names()
    return [name for name in get_all_category_names() if name not in music]
