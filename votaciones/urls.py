"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Mapeo de URLs para el módulo de Votaciones. Incluye rutas web 
               para gestión y rutas de API para la app móvil.
--------------------------------------------------------------------------------
"""
from django.urls import path
from . import views
from . import api as api_views
from .api import ResultadosView

app_name = 'votaciones'

urlpatterns = [
    # Vistas Web (Django Templates)
    path('', views.lista_votaciones, name='lista_votaciones'),
    path('crear/', views.crear_votacion, name='crear_votacion'),
    path('<int:pk>/', views.detalle_votacion, name='detalle_votacion'),
    path('<int:pk>/votar/', views.emitir_voto, name='emitir_voto'),
    path('<int:pk>/cerrar/', views.cerrar_votacion, name='cerrar_votacion'),
    path('<int:pk>/editar/', views.editar_votacion, name='editar_votacion'),
    path('<int:pk>/eliminar/', views.eliminar_votacion, name='eliminar_votacion'),

    # API Endpoints (App Móvil)
    path('api/v1/abiertas/', api_views.abiertas, name='api_abiertas'),
    path('api/v1/solicitar-codigo/', api_views.solicitar_codigo_voto, name='solicitar_codigo_voto'),
    path('api/v1/<int:pk>/votar/', api_views.votar, name='api_votar'),
    path('api/v1/<int:pk>/resultados/', ResultadosView.as_view(), name='api_resultados'),
]