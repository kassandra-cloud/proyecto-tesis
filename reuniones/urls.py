from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter
from .api import ReunionViewSet, ActaViewSet,AsistenciaViewSet

app_name = "reuniones"

urlpatterns = [
    path("", views.reunion_list, name="lista_reuniones"),
    path("nueva/", views.reunion_create, name="crear_reunion"),
    path("<int:pk>/", views.reunion_detail, name="detalle_reunion"),
    path("<int:pk>/acta/", views.acta_edit, name="editar_acta"),
    path("<int:pk>/asistencia/", views.asistencia_list, name="lista_asistencia"),
    path("<int:pk>/acta/pdf/", views.acta_export_pdf, name="exportar_acta_pdf"),
    
    # path("<int:pk>/acta/aprobar/", views.aprobar_acta, name="aprobar_acta"), <-- ESTA LÍNEA SE BORRÓ (era la del error)
    
    path("<int:pk>/acta/rechazar/", views.rechazar_acta, name="rechazar_acta"),
    path("actas/<int:pk>/enviar-pdf/", views.enviar_acta_pdf_por_correo, name="enviar_acta_pdf_por_correo"),
    path("<int:pk>/borrador/guardar/", views.guardar_borrador_acta, name="guardar_borrador_acta"),
    path("<int:pk>/borrador/aprobar/", views.aprobar_borrador_acta, name="aprobar_borrador_acta"),

    # --- NUEVAS RUTAS DE ESTADO AÑADIDAS ---
    path('<int:pk>/iniciar/', views.iniciar_reunion, name='iniciar_reunion'),
    path('<int:pk>/finalizar/', views.finalizar_reunion, name='finalizar_reunion'),
    path('<int:pk>/cancelar/', views.cancelar_reunion, name='cancelar_reunion'),
    path('api/feed/', views.reuniones_json_feed, name='reuniones_feed'),
]

# API (esto lo dejamos tal cual)
router = DefaultRouter()
router.register(r"reuniones", ReunionViewSet, basename="reunion_api")
router.register(r"actas", ActaViewSet, basename="acta_api")
router.register(r"asistencias", AsistenciaViewSet, basename="asistencia_api")

urlpatterns += router.urls