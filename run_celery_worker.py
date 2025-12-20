"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Script de arranque personalizado para el worker de Celery. 
               Es necesario específicamente para entornos Windows, donde se requiere 
               el uso de 'eventlet' y un parcheo (monkey_patch) para la concurrencia.
--------------------------------------------------------------------------------
"""
# run_celery_worker.py
# Este script es la nueva forma de iniciar el worker de Celery en Windows

import eventlet  # Importa la librería de concurrencia eventlet
eventlet.monkey_patch()  # ¡El parche se aplica SÓLO AQUÍ! Modifica librerías estándar para ser no bloqueantes

import os  # Importa módulo del sistema operativo
import sys  # Importa módulo para interactuar con el intérprete de Python
from celery.bin.celery import main as celery_main  # Importa la función principal de ejecución de Celery

if __name__ == "__main__":
    # Apunta a tu app de celery estableciendo la variable de entorno de configuración
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_tesis.settings')

    # Estos son los argumentos que antes poníamos en la terminal
    args = [
        'celery',           # Nombre del comando
        '-A',               # Flag para definir la aplicación
        'proyecto_tesis',   # Nombre de la aplicación Celery
        'worker',           # Modo de ejecución (worker)
        '--loglevel=info',  # Nivel de detalle de los logs
        '-P', 'eventlet',   # Pool de ejecución (eventlet para compatibilidad Windows)
        '-c', '2'           # Concurrencia (número de workers hijos)
    ]

    # Pasa los argumentos a la función principal de Celery simulando la línea de comandos
    sys.argv = args
    celery_main()  # Ejecuta Celery