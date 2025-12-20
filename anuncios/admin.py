"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Configura la interfaz administrativa de Django para el 
                       modelo Anuncio. Permite buscar, filtrar y asignar 
                       automáticamente el autor al crear un anuncio desde el admin.
--------------------------------------------------------------------------------
"""

# Importa el módulo admin de Django.
from django.contrib import admin
# Importa el modelo Anuncio definido en el archivo local models.py.
from .models import Anuncio 

# Registra la clase AnuncioAdmin asociada al modelo Anuncio usando el decorador.
@admin.register(Anuncio)
class AnuncioAdmin(admin.ModelAdmin):
    # Define las columnas que se mostrarán en la lista de registros del admin.
    list_display = ('titulo', 'autor', 'fecha_creacion')
    
    # Define los campos por los cuales el administrador puede buscar texto.
    search_fields = ('titulo', 'contenido')
    
    # Añade filtros laterales para filtrar por autor o fecha.
    list_filter = ('autor', 'fecha_creacion')
    
    # Establece que la fecha de creación es de solo lectura (no modificable).
    readonly_fields = ('fecha_creacion',)
    
    # Sobrescribe el método save_model para inyectar lógica personalizada al guardar.
    def save_model(self, request, obj, form, change):
        # Si el objeto no tiene clave primaria (es nuevo, no una edición).
        if not obj.pk:
            # Asigna el usuario actual (request.user) como autor del anuncio.
            obj.autor = request.user
        # Llama al método original para guardar en la base de datos.
        super().save_model(request, obj, form, change)

    # Sobrescribe get_queryset para optimizar las consultas a la base de datos.
    def get_queryset(self, request):
        # Usa select_related para traer los datos del autor en la misma consulta SQL (evita N+1).
        return super().get_queryset(request).select_related('autor')