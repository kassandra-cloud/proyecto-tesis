"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Configuración del panel de administración de Django para la app 
               'votaciones'. Registra los modelos Votacion, Opcion y Voto para 
               su gestión básica desde el backend.
--------------------------------------------------------------------------------
"""
from django.contrib import admin  # Importa el módulo de administración
from .models import Votacion, Opcion, Voto  # Importa los modelos a registrar

# Registra los modelos para que aparezcan en el panel de admin
admin.site.register(Votacion)
admin.site.register(Opcion)
admin.site.register(Voto)