from django.contrib import admin
from .models import Anuncio 

@admin.register(Anuncio)
class AnuncioAdmin(admin.ModelAdmin):
    # Campos que se mostrarán en la lista de anuncios en el admin
    list_display = ('titulo', 'autor', 'fecha_creacion')
    
    # Campos por los que se puede buscar
    search_fields = ('titulo', 'contenido')
    
    # Campos por los que se puede filtrar
    list_filter = ('autor', 'fecha_creacion')
    
    # Asegura que la fecha de creación se muestre pero no se edite
    readonly_fields = ('fecha_creacion',)
    
    # Este método se asegura de que el usuario que está creando el anuncio 
    # en el admin sea asignado automáticamente como el autor.
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.autor = request.user
        super().save_model(request, obj, form, change)

    # Optimiza el queryset para evitar consultas N+1
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('autor')