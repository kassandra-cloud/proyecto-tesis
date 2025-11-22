# anuncios/apps.py
from django.apps import AppConfig

class AnunciosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'anuncios'

    def ready(self):
        # Importar las señales cuando la app esté lista
        import anuncios.signals