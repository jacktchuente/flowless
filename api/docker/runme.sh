#!/bin/bash
set -eu

python manage.py migrate
python manage.py create_admin
python manage.py init_built_in_data
python manage.py init_periodic_tasks

celery -A celery_tasks worker -l info -P solo &
celery -A celery_tasks beat -l INFO \
  --scheduler django_celery_beat.schedulers:DatabaseScheduler &
uvicorn api_core.asgi:application \
  --host 0.0.0.0 \
  --port 8000 \
  --proxy-headers \
  --forwarded-allow-ips "*" &

trap 'kill 0' TERM INT
# Le premier process qui meurt tue le conteneur ; compose le relance.
wait -n
exit 1
