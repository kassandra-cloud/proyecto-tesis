"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Configuración de la aplicación 'usuarios'. Define el tipo de 
               campo automático por defecto y el nombre de la app.
--------------------------------------------------------------------------------
"""
from django.apps import AppConfig  # Importa la clase base para configuración de aplicaciones

class UsuariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"  # Define BigAutoField para claves primarias
    name = "usuarios"  # Nombre de la aplicación