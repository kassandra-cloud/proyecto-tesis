"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Define el mapeo de URLs para la aplicación de anuncios.
                       Conecta las rutas (ej. /crear/) con sus respectivas 
                       vistas (funciones en views.py).
--------------------------------------------------------------------------------
"""

# Importa la función path para definir rutas.
from django.urls import path
# Importa las vistas desde el archivo actual.
from . import views

# Define el nombre de espacio de la app para referenciar URLs como 'anuncios:nombre'.
app_name = 'anuncios'

urlpatterns = [
    # Ruta raíz de anuncios: lista todos los anuncios.
    path('', views.lista_anuncios, name='lista_anuncios'),
    # Ruta para crear un nuevo anuncio.
    path('crear/', views.crear_anuncio, name='crear_anuncio'),
    # Ruta para editar un anuncio específico (usa el ID como parámetro entero).
    path('<int:pk>/editar/', views.editar_anuncio, name='editar_anuncio'),
    # Ruta para eliminar un anuncio específico.
    path('<int:pk>/eliminar/', views.eliminar_anuncio, name='eliminar_anuncio'),
]