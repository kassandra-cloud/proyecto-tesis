"""
URL configuration for proyecto_tesis project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings 
from django.conf.urls.static import static 

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("core.urls")),  
    path("api/core/", include("core.urls")),
    path("usuarios/", include("usuarios.urls")),  # módulo de gestión de usuarios
    path("accounts/", include("django.contrib.auth.urls")), 
    path("reuniones/", include("reuniones.urls")),
    path('talleres/', include('talleres.urls', namespace='talleres')),
    path("votaciones/", include("votaciones.urls")),
    path('foro/', include('foro.urls', namespace='foro')),
    path('anuncios/', include('anuncios.urls', namespace='anuncios')),
    path('recursos/', include('recursos.urls', namespace='recursos')),
    path('analitica/', include('datamart.urls')),
]

# esto es para que los archivos subidos (MEDIA) funcionen
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

