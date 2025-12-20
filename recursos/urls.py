"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Mapeo de URLs para la aplicación Recursos. Incluye rutas para:
               - Gestión Web de Recursos (Crear, Editar, Listar).
               - Gestión Web de Reservas (Aprobar, Rechazar).
               - Endpoints de API v1 (Recursos y Solicitudes).
--------------------------------------------------------------------------------
"""
from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from .api import SolicitudReservaViewSet, RecursoViewSet

app_name = 'recursos'

urlpatterns = [
    # --- Vistas WEB de Gestión de RECURSOS ---
    path('', views.lista_recursos, name='lista_recursos'),
    path('crear/', views.crear_recurso, name='crear_recurso'),
    path('<int:pk>/editar/', views.editar_recurso, name='editar_recurso'),
    path('<int:pk>/deshabilitar/', views.deshabilitar_recurso, name='deshabilitar_recurso'),
    path('<int:pk>/restaurar/', views.restaurar_recurso, name='restaurar_recurso'),
    
    # --- Vistas WEB de Gestión de RESERVAS ---
    path('solicitudes/', views.gestionar_reservas, name='gestionar_reservas'),
    path('solicitudes/<int:pk>/actualizar/', views.actualizar_estado_reserva, name='actualizar_estado_reserva'),
    
    # Redundancia de rutas para asegurar compatibilidad
    path('reservas/gestionar/', views.gestionar_reservas, name='gestionar_reservas'),
    path('reservas/<int:pk>/estado/', views.actualizar_estado_reserva, name='actualizar_estado_reserva'),
]

# --- Configuración de rutas de API v1 ---
router = DefaultRouter()
router.register(r'api/v1/recursos', RecursoViewSet, basename='api-recursos')
router.register(r'api/v1/solicitudes', SolicitudReservaViewSet, basename='api-solicitudes')

# Añadir rutas de API al patrón principal
urlpatterns += [
    path('', include(router.urls)),
]