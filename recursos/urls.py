from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from .api import SolicitudReservaViewSet
from .api import RecursoViewSet, SolicitudReservaViewSet
app_name = 'recursos'


urlpatterns = [
    # --- Vistas de Gestión de RECURSOS ---
    path('', views.lista_recursos, name='lista_recursos'), # <--- ESTA ES LA RAÍZ
    path('crear/', views.crear_recurso, name='crear_recurso'),
    path('<int:pk>/editar/', views.editar_recurso, name='editar_recurso'),
    path('<int:pk>/deshabilitar/', views.deshabilitar_recurso, name='deshabilitar_recurso'),
    path('<int:pk>/restaurar/', views.restaurar_recurso, name='restaurar_recurso'),
    
    # --- Vistas de Gestión de RESERVAS ---
    path('solicitudes/', views.gestionar_reservas, name='gestionar_reservas'),
    path('solicitudes/<int:pk>/actualizar/', views.actualizar_estado_reserva, name='actualizar_estado_reserva'),

]

# --- API v1 ---
from rest_framework.routers import DefaultRouter
from .api import RecursoViewSet

router = DefaultRouter()
router.register(r'api/v1/recursos', RecursoViewSet, basename='api-recursos')
router.register(r'api/v1/solicitudes', SolicitudReservaViewSet, basename='api-solicitudes')


urlpatterns += [
    path('', include(router.urls)),
]