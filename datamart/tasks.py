# datamart/tasks.py
from celery import shared_task
from django.core.management import call_command
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

@shared_task
def tarea_actualizar_bi_async():
    """
    Ejecuta el ETL en segundo plano.
    Se llama automáticamente cuando un usuario visita el panel BI.
    """
    logger.info("Iniciando ETL BI disparado por usuario...")
    try:
        # Ejecutamos el comando existente
        call_command("procesar_etl")
        
        # Guardamos la marca de tiempo de cuándo terminó
        # Esto nos sirve para saber cuándo fue la última actualización real
        cache.set('ultima_actualizacion_bi_timestamp', True, timeout=None)
        
        logger.info(" ETL BI finalizado correctamente.")
        return "ETL OK"
    except Exception as e:
        logger.error(f" Error en ETL BI: {e}")
        return f"Error: {e}"