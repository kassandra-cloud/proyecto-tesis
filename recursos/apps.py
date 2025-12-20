"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Configuración de la aplicación 'recursos'. Carga las señales 
               (signals) al iniciar para activar notificaciones automáticas.
--------------------------------------------------------------------------------
"""
from django.apps import AppConfig

class RecursosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recursos'

    def ready(self):
        # Importa el módulo de señales cuando la app está lista
        import recursos.signals