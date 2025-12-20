"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Configuración del panel de administración de Django para la app 'foro'.
               Permite gestionar Publicaciones, Comentarios y Archivos Adjuntos,
               incluyendo inlines para ver elementos relacionados.
--------------------------------------------------------------------------------
"""
from django.contrib import admin
from .models import Publicacion, ArchivoAdjunto, Comentario

# Configuración para ver archivos adjuntos dentro de la edición de una publicación
class ArchivoAdjuntoInline(admin.TabularInline):
    model = ArchivoAdjunto
    extra = 0  # No mostrar filas vacías extra para agregar nuevos
    readonly_fields = ('tipo_archivo',) # Mostrar el tipo calculado (imagen, video, etc.) como solo lectura

# Configuración para ver comentarios dentro de la edición de una publicación
class ComentarioInline(admin.TabularInline):
    model = Comentario
    extra = 0
    fields = ('autor', 'contenido', 'visible', 'fecha_creacion')
    readonly_fields = ('fecha_creacion',) # La fecha no se debe editar manualmente
    can_delete = True

# Registro del modelo Publicacion
@admin.register(Publicacion)
class PublicacionAdmin(admin.ModelAdmin):
    # Columnas visibles en la lista
    list_display = ('id', 'autor', 'resumen_contenido', 'fecha_creacion', 'visible', 'total_adjuntos')
    # Filtros laterales
    list_filter = ('visible', 'fecha_creacion')
    # Campos de búsqueda
    search_fields = ('contenido', 'autor__username', 'autor__email')
    # Elementos relacionados a mostrar en la misma página
    inlines = [ArchivoAdjuntoInline, ComentarioInline]
    
    # Método auxiliar para mostrar un extracto del contenido
    def resumen_contenido(self, obj):
        return obj.contenido[:50] + "..." if len(obj.contenido) > 50 else obj.contenido
    resumen_contenido.short_description = "Contenido"

    # Método auxiliar para contar adjuntos
    def total_adjuntos(self, obj):
        return obj.adjuntos.count()
    total_adjuntos.short_description = "Adjuntos"

# Registro del modelo Comentario
@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('autor', 'publicacion_link', 'resumen_contenido', 'fecha_creacion', 'visible')
    list_filter = ('visible', 'fecha_creacion')
    search_fields = ('contenido', 'autor__username')
    
    def resumen_contenido(self, obj):
        return obj.contenido[:50] + "..." if len(obj.contenido) > 50 else obj.contenido
    
    # Enlace para ver a qué publicación pertenece
    def publicacion_link(self, obj):
        return obj.publicacion
    publicacion_link.short_description = "Publicación"

# Registro del modelo ArchivoAdjunto
@admin.register(ArchivoAdjunto)
class ArchivoAdjuntoAdmin(admin.ModelAdmin):
    list_display = ('archivo', 'tipo_archivo', 'publicacion', 'autor', 'es_mensaje')
    list_filter = ('es_mensaje', 'fecha_creacion')