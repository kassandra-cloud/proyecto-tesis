"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Configuración de la aplicación Reuniones. Importa las señales 
               (signals) al iniciar la aplicación.
--------------------------------------------------------------------------------
"""
from django.apps import AppConfig


class ReunionesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reuniones'
    def ready(self):
            import reuniones.signals  # Carga las señales