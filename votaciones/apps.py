# votaciones/apps.py
from django.apps import AppConfig

class VotacionesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'votaciones'

    def ready(self):
        import votaciones.signals # <--- AGREGAR ESTA LÍNEA