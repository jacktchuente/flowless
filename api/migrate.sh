#!/usr/bin/env sh
set -e
cd "$(dirname "$0")"
poetry run python manage.py makemigrations
poetry run python manage.py migrate
