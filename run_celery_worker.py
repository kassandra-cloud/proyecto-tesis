# run_celery_worker.py
# Este script es la nueva forma de iniciar el worker de Celery en Windows

import eventlet
eventlet.monkey_patch()  # ¡El parche se aplica SÓLO AQUÍ!

import os
import sys
from celery.bin.celery import main as celery_main

if __name__ == "__main__":
    # Apunta a tu app de celery
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_tesis.settings')

    # Estos son los argumentos que antes poníamos en la terminal
    args = [
        'celery',
        '-A',
        'proyecto_tesis',
        'worker',
        '--loglevel=info',
        '-P',
        'eventlet'
    ]

    # Pasa los argumentos a la función principal de Celery
    sys.argv = args
    celery_main()