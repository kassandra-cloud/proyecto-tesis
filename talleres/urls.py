from django.urls import path
from . import views

app_name = "talleres"

urlpatterns = [
    path("", views.taller_list, name="lista_talleres"),
    path("nuevo/", views.taller_create, name="crear_taller"),
    path("<int:pk>/inscripciones/", views.inscripcion_list, name="lista_inscripciones"),
]