"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Configuración del panel de administración de Django para la app 
               'talleres'. Permite gestionar los Talleres y visualizar las 
               Inscripciones de los vecinos.
--------------------------------------------------------------------------------
"""
from django.contrib import admin  # Importa el módulo de administración de Django
from .models import Taller, Inscripcion  # Importa los modelos Taller e Inscripcion

# 1. Personalización para el modelo Taller
class TallerAdmin(admin.ModelAdmin):
    # Campos que se mostrarán en la lista de talleres
    list_display = (
        'nombre', 
        'estado', 
        'fecha_inicio', 
        'fecha_termino', 
        'cupos_totales',
        'creado_por',
    )
    # Filtros laterales para búsqueda rápida
    list_filter = ('estado', 'fecha_inicio')
    # Campos por los que se puede buscar (nombre y descripción)
    search_fields = ('nombre', 'descripcion')
    # Orden por defecto: los más recientes primero (por fecha de inicio)
    ordering = ('-fecha_inicio',)

# 2. Personalización para el modelo Inscripcion
class InscripcionAdmin(admin.ModelAdmin):
    # Columnas visibles en la lista de inscripciones
    list_display = ('taller', 'vecino', 'fecha_inscripcion')
    # Filtros laterales por taller
    list_filter = ('taller',)
    # Búsqueda por nombre del taller o nombre de usuario del vecino
    search_fields = ('taller__nombre', 'vecino__username')
    # Habilita un widget de búsqueda/autocompletado para seleccionar taller y vecino (útil si hay muchos)
    autocomplete_fields = ('taller', 'vecino') 

# 3. Registrar los modelos en el admin con sus configuraciones personalizadas
admin.site.register(Taller, TallerAdmin)
admin.site.register(Inscripcion, InscripcionAdmin)