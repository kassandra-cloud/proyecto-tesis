"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Definición de tareas asíncronas utilizando Celery para ejecutar 
               el proceso ETL en segundo plano sin bloquear al usuario.
--------------------------------------------------------------------------------
"""
from celery import shared_task  # Decorador para crear tareas compartidas de Celery
from django.core.management import call_command  # Permite ejecutar comandos de management
from django.core.cache import cache  # Para interactuar con la caché
import logging

logger = logging.getLogger(__name__)  # Configuración del logger

@shared_task
def tarea_actualizar_bi_async():
    """
    Ejecuta el ETL en segundo plano.
    Se llama automáticamente cuando un usuario visita el panel BI o solicita actualización.
    """
    logger.info("Iniciando ETL BI disparado por usuario...")
    try:
        # Ejecuta el comando 'procesar_etl' definido en management/commands
        call_command("procesar_etl")
        
        # Guarda la marca de tiempo de finalización en caché
        # Esto permite saber cuándo fue la última actualización exitosa
        cache.set('ultima_actualizacion_bi_timestamp', True, timeout=None)
        
        logger.info(" ETL BI finalizado correctamente.")
        return "ETL OK"
    except Exception as e:
        logger.error(f" Error en ETL BI: {e}")
        return f"Error: {e}"