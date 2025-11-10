
# foro/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # ---------------- WEB ----------------
    path("lista/", views.lista_publicaciones, name="lista_publicaciones"),
    path("crear/", views.crear_publicacion, name="crear_publicacion"),
    path("foro-web/", views.foro_web, name="foro_web"),
    path("<int:publicacion_id>/comentar/", views.comentar, name="comentar"),
    path("<int:publicacion_id>/comentarios/partial/", views.comentarios_partial, name="comentarios_partial"),
    path("publicacion/<int:pk>/alternar/", views.alternar_publicacion, name="alternar_publicacion"),
    path("comentario/<int:pk>/eliminar/", views.eliminar_comentario, name="eliminar_comentario"),

    # ---------------- API (COINCIDE CON ANDROID) ----------------
    # GET /foro/api/v1/publicaciones/
    path("api/v1/publicaciones/", views.api_publicaciones_list, name="api_publicaciones_list"),

    # GET  /foro/api/v1/publicaciones/<id>/comentarios/
    # POST /foro/api/v1/publicaciones/<id>/comentarios/
    path("api/v1/publicaciones/<int:pk>/comentarios/", views.api_publicacion_comentarios, name="api_publicacion_comentarios"),
]
