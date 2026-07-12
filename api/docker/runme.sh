cp docker/nginx.conf /etc/nginx/conf.d/django_app.conf
python manage.py migrate
python manage.py create_admin
python manage.py init_built_in_data
python manage.py init_periodic_tasks
uvicorn api_core.asgi:application --port 8000 & nginx -g "daemon off;" & celery -A celery_tasks worker -l info -P solo & celery -A celery_tasks beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
