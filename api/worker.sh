#!/usr/bin/env sh
set -e
cd "$(dirname "$0")"
poetry run celery -A celery_tasks worker -l info -P solo
