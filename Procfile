web: daphne -b 0.0.0.0 -p $PORT config.asgi:application
worker: celery -A config worker --loglevel=info --concurrency=2
release: python manage.py migrate --noinput && python manage.py populate_data