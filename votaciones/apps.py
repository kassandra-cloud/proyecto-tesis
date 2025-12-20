"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Configuración de la aplicación 'votaciones'. Carga las señales 
               al iniciar la app para manejar notificaciones.
--------------------------------------------------------------------------------
"""
from django.apps import AppConfig  # Importa clase base de configuración

class VotacionesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'  # Tipo de clave primaria
    name = 'votaciones'  # Nombre de la aplicación

    def ready(self):
        # Importa señales al iniciar
        import votaciones.signals