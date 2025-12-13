web: gunicorn proyecto_tesis.wsgi:application --log-file -
worker: celery -A proyecto_tesis worker --loglevel=info --pool=solo
