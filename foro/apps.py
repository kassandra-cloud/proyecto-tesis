"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Configuración de la aplicación 'foro'. Incluye la carga de señales 
               (signals) al iniciar la app.
--------------------------------------------------------------------------------
"""
from django.apps import AppConfig

class ForoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'foro'

    def ready(self):
        # Importa las señales cuando la aplicación está lista
        import foro.signals