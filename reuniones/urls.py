from django.urls import path
from . import views

app_name = "reuniones"

urlpatterns = [
    path("", views.reunion_list, name="lista_reuniones"),
    path("nueva/", views.reunion_create, name="crear_reunion"),
    path("<int:pk>/", views.reunion_detail, name="detalle_reunion"),
    path("<int:pk>/acta/", views.acta_edit, name="editar_acta"),
    path("<int:pk>/asistencia/", views.asistencia_list, name="lista_asistencia"),
    path("<int:pk>/acta/pdf/", views.acta_export_pdf, name="exportar_acta_pdf"),
]