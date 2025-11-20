from django.contrib import admin
from .models import Publicacion, ArchivoAdjunto, Comentario


class ArchivoAdjuntoInline(admin.TabularInline):
    model = ArchivoAdjunto
    extra = 0  # No mostrar filas vacías extra
    readonly_fields = ('tipo_archivo',) # Mostrar el tipo calculado


class ComentarioInline(admin.TabularInline):
    model = Comentario
    extra = 0
    fields = ('autor', 'contenido', 'visible', 'fecha_creacion')
    readonly_fields = ('fecha_creacion',)
    can_delete = True



@admin.register(Publicacion)
class PublicacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'autor', 'resumen_contenido', 'fecha_creacion', 'visible', 'total_adjuntos')
    list_filter = ('visible', 'fecha_creacion')
    search_fields = ('contenido', 'autor__username', 'autor__email')
    inlines = [ArchivoAdjuntoInline, ComentarioInline]
    

    def resumen_contenido(self, obj):
        return obj.contenido[:50] + "..." if len(obj.contenido) > 50 else obj.contenido
    resumen_contenido.short_description = "Contenido"

    def total_adjuntos(self, obj):
        return obj.adjuntos.count()
    total_adjuntos.short_description = "Adjuntos"

@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('autor', 'publicacion_link', 'resumen_contenido', 'fecha_creacion', 'visible')
    list_filter = ('visible', 'fecha_creacion')
    search_fields = ('contenido', 'autor__username')
    
    def resumen_contenido(self, obj):
        return obj.contenido[:50] + "..." if len(obj.contenido) > 50 else obj.contenido
    

    def publicacion_link(self, obj):
        return obj.publicacion
    publicacion_link.short_description = "Publicación"


@admin.register(ArchivoAdjunto)
class ArchivoAdjuntoAdmin(admin.ModelAdmin):
    list_display = ('archivo', 'tipo_archivo', 'publicacion', 'autor', 'es_mensaje')
    list_filter = ('es_mensaje', 'fecha_creacion')