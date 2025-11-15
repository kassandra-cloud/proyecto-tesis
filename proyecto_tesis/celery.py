# proyecto_tesis/celery.py
import os
from celery import Celery

# Establece la variable de entorno para que Celery sepa dónde están tus settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_tesis.settings')

# Crea la instancia de la aplicación Celery
app = Celery('proyecto_tesis')

# Carga la configuración desde tu settings.py (ej. CELERY_BROKER_URL)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Carga automáticamente las tareas (ej. tasks.py) de todas las apps
app.autodiscover_tasks()