"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Configuración de la aplicación 'talleres'. Carga las señales 
               (signals) al iniciar la app para notificaciones automáticas.
--------------------------------------------------------------------------------
"""
# talleres/apps.py
from django.apps import AppConfig  # Importa clase base de configuración

class TalleresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'  # Tipo de PK por defecto
    name = 'talleres'  # Nombre de la app

    def ready(self):
        # Importa las señales cuando la aplicación está lista
        import talleres.signals