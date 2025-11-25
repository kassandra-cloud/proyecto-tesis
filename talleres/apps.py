# talleres/apps.py
from django.apps import AppConfig

class TalleresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'talleres'

    def ready(self):
        import talleres.signals  