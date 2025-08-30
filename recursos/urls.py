from django.urls import path
from . import views

app_name = "recursos"

urlpatterns = [
    path("", views.recurso_list, name="lista_recursos"),
    path("nuevo/", views.recurso_create, name="crear_recurso"),
]