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
    path("<int:pk>/acta/aprobar/", views.aprobar_acta, name="aprobar_acta"),
    path("<int:pk>/acta/rechazar/", views.rechazar_acta, name="rechazar_acta"),
    path("<int:pk>/borrador/guardar/", views.guardar_borrador_acta, name="guardar_borrador_acta"),
    path("<int:pk>/borrador/aprobar/", views.aprobar_borrador_acta, name="aprobar_borrador_acta"),
]
router = DefaultRouter()
router.register(r"api/reuniones", ReunionViewSet, basename="api_reuniones")
router.register(r"api/actas", ActaViewSet, basename="api_actas")
router.register(r"api/asistencias", AsistenciaViewSet,basename="api_asistencias") 
urlpatterns += router.urls