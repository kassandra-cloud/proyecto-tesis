from django.contrib import admin
from .models import Taller, Inscripcion

# 1. Personalización para el modelo Taller
class TallerAdmin(admin.ModelAdmin):
    # Campos que se mostrarán en la lista
    list_display = (
        'nombre', 
        'estado', 
        'fecha_inicio', 
        'fecha_termino', 
        'cupos_totales',
        'creado_por',
    )
    # Filtros laterales
    list_filter = ('estado', 'fecha_inicio')
    # Campos por los que se puede buscar
    search_fields = ('nombre', 'descripcion')
    # Orden por defecto
    ordering = ('-fecha_inicio',)

# 2. Personalización para el modelo Inscripcion
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ('taller', 'vecino', 'fecha_inscripcion')
    list_filter = ('taller',)
    search_fields = ('taller__nombre', 'vecino__username')
    # Esto facilita buscar un taller o vecino específico
    autocomplete_fields = ('taller', 'vecino') 

# 3. Registrar los modelos en el admin
admin.site.register(Taller, TallerAdmin)
admin.site.register(Inscripcion, InscripcionAdmin)