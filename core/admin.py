"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Configura el panel de administración para el modelo 
                       Perfil. Permite ver usuario, RUT y rol en la lista, 
                       y filtrar/buscar por esos campos.
--------------------------------------------------------------------------------
"""

# Importa módulo admin.
from django.contrib import admin
# Importa modelo Perfil.
from .models import Perfil

# Registra Perfil con configuración personalizada.
@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    # Columnas visibles en la lista.
    list_display = ('usuario', 'rut', 'rol')
    # Filtros laterales.
    list_filter = ('rol',)
    # Campos de búsqueda (usa __ para acceder a campos del usuario relacionado).
    search_fields = ('usuario__username', 'usuario__email', 'rut')