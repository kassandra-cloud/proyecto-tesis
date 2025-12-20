"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Configuración del panel de administración para Reuniones, Actas 
               y Asistencias. Define cómo se visualizan y filtran estos modelos 
               en el backend de Django.
--------------------------------------------------------------------------------
"""
from django.contrib import admin # Importa el módulo admin de Django
from reuniones.models import Acta, Reunion, Asistencia # Importa los modelos de la app

@admin.register(Acta) # Registra el modelo Acta en el admin
class ActaAdmin(admin.ModelAdmin):
    list_display = ('reunion', 'estado_transcripcion', 'aprobada') # Columnas visibles en la lista
    list_filter = ('estado_transcripcion', 'aprobada') # Filtros laterales

class ActaInline(admin.StackedInline): # Define una vista en línea para el Acta
    model = Acta # Modelo asociado
    can_delete = False # No permite borrar el acta desde la vista de reunión
    verbose_name_plural = 'Acta' # Nombre plural para la sección

class AsistenciaInline(admin.TabularInline): # Define vista en línea tipo tabla para Asistencia
    model = Asistencia # Modelo asociado
    extra = 0 # No muestra filas vacías extra
    can_delete = True # Permite borrar asistencias

@admin.register(Reunion) # Registra el modelo Reunion
class ReunionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'fecha', 'estado', 'tipo') # Columnas visibles
    list_filter = ('estado', 'tipo', 'fecha') # Filtros laterales
    search_fields = ('titulo',) # Campo de búsqueda
    inlines = [ActaInline, AsistenciaInline] # Agrega las vistas en línea de Acta y Asistencia