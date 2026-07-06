#!/usr/bin/env sh
set -e
cd "$(dirname "$0")"
poetry run celery -A celery_tasks beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
