"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Configuración principal de la aplicación 'datamart' dentro del 
               proyecto Django.
--------------------------------------------------------------------------------
"""
from django.apps import AppConfig  # Importa la clase base para configuración de aplicaciones

class DatamartConfig(AppConfig):
    # Define el tipo de campo autoincremental por defecto para los modelos
    default_auto_field = 'django.db.models.BigAutoField'
    # Establece el nombre de la aplicación
    name = 'datamart'