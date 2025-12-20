"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Configuración de Celery, el gestor de tareas asíncronas. 
               Permite ejecutar procesos pesados (como envío de correos o notificaciones)
               en segundo plano sin bloquear la respuesta al usuario.
--------------------------------------------------------------------------------
"""
import os  # Importa módulo del sistema operativo
from celery import Celery  # Importa la clase base de Celery

# Establece la variable de entorno para que Celery sepa dónde están tus settings de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_tesis.settings')

# Crea la instancia de la aplicación Celery con el nombre del proyecto
app = Celery('proyecto_tesis')

# Carga la configuración desde tu settings.py
# El namespace='CELERY' significa que buscará variables que empiecen con CELERY_ en settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Busca y carga automáticamente las tareas (tasks.py) definidas en cada aplicación instalada
app.autodiscover_tasks()