web: gunicorn config.wsgi:application --log-file=-
worker: celery -A tramper_backend worker -l info
release: python manage.py migrate --noinput
