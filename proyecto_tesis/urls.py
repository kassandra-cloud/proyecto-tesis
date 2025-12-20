"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Archivo principal de enrutamiento URL del proyecto. Define las rutas 
               maestras que delegan a las URLs específicas de cada aplicación 
               (core, usuarios, reuniones, etc.).
--------------------------------------------------------------------------------
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings 
from django.conf.urls.static import static 
from anuncios.api import lista_anuncios_api

# Lista de patrones de URL
urlpatterns = [
    path('admin/', admin.site.urls), # Panel de administración de Django
    path("", include("core.urls")),  # Rutas de la aplicación Core (Home, etc.)
    path("api/core/", include("core.urls")), # Rutas API de Core
    path("usuarios/", include("usuarios.urls")),  # Rutas para gestión de usuarios
    path("accounts/", include("django.contrib.auth.urls")), # Rutas de autenticación estándar
    path("reuniones/", include("reuniones.urls")), # Rutas del módulo de reuniones
    path('talleres/', include('talleres.urls', namespace='talleres')), # Rutas del módulo de talleres
    path("votaciones/", include("votaciones.urls")), # Rutas del módulo de votaciones
    path('foro/', include('foro.urls', namespace='foro')), # Rutas del foro
    path('anuncios/', include('anuncios.urls', namespace='anuncios')), # Rutas de anuncios web
    path('api/anuncios/', lista_anuncios_api, name='api_lista_anuncios'), # Endpoint específico de API anuncios
    path('recursos/', include('recursos.urls', namespace='recursos')), # Rutas de gestión de recursos
    path('analitica/', include('datamart.urls')), # Rutas del panel BI (Datamart)
]

# Configuración para servir archivos multimedia en modo DEBUG (Desarrollo)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)