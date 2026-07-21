#!/bin/bash
# Backfill initial du vocabulaire des axes de regles editoriales.
#
# Reconstruit VocabularyEntry depuis les MediaContainer deja en base
# (collections actives, analyse complete) : ajoute les valeurs manquantes,
# purge les orphelins. Idempotent — peut etre relance sans risque.
#
# A lancer une fois apres le deploiement (migration comprise). Inutile
# d'attendre une nouvelle sync : les donnees existantes suffisent, et les
# syncs suivantes alimentent le vocabulaire d'elles-memes.
#
# Usage : ./scripts/backfill_vocabulary.sh
set -eu

cd "$(dirname "$0")/.."

docker compose exec api python manage.py backfill_vocabulary
