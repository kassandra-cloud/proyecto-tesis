"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Clase de configuración de la aplicación 'anuncios'.
                       Se utiliza para configurar el tipo de campo automático 
                       y cargar las señales (signals) al iniciar la app.
--------------------------------------------------------------------------------
"""

# Importa la clase base AppConfig.
from django.apps import AppConfig

class AnunciosConfig(AppConfig):
    # Define el tipo de campo predeterminado para claves primarias (BigInt).
    default_auto_field = 'django.db.models.BigAutoField'
    # Nombre técnico de la aplicación.
    name = 'anuncios'

    def ready(self):
        """Método que se ejecuta cuando Django termina de cargar la configuración."""
        # Importar las señales aquí asegura que se registren correctamente
        # y evita problemas de importación circular.
        import anuncios.signals