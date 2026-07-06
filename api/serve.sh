#!/usr/bin/env sh
set -e
cd "$(dirname "$0")"
poetry run uvicorn api_core.asgi:application --host 0.0.0.0 --port 8000
