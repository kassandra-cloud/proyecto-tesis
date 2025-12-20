"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Clase de configuración de la app 'core'. Define el tipo 
                       de campo auto-incremental y carga las señales (signals) 
                       al iniciar la aplicación.
--------------------------------------------------------------------------------
"""

# Importa AppConfig.
from django.apps import AppConfig

class CoreConfig(AppConfig):
    # Define BigAutoField como tipo por defecto para IDs.
    default_auto_field = "django.db.models.BigAutoField"
    # Nombre de la aplicación.
    name = "core"

    def ready(self):
        """Se ejecuta al iniciar Django. Importa signals para activarlas."""
        from . import signals