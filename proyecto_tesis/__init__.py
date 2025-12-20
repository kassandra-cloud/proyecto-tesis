"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Inicializador del paquete del proyecto. Configura PyMySQL como 
               driver de MySQL para compatibilidad y carga la aplicación Celery 
               para asegurar que las tareas asíncronas se registren al arrancar Django.
--------------------------------------------------------------------------------
"""
import pymysql  # Importa la librería PyMySQL para interactuar con bases de datos MySQL
pymysql.install_as_MySQLdb()  # Instala PyMySQL como reemplazo de MySQLdb (necesario para Django en algunos entornos)
from .celery import app as celery_app  # Importa la instancia de la aplicación Celery definida en celery.py

# Define lo que se exportará cuando se haga "from proyecto_tesis import *"
__all__ = ('celery_app',)