"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Definición de las rutas URL para la aplicación 'foro', separadas 
               en secciones para vistas Web (HTML) y API REST (JSON).
--------------------------------------------------------------------------------
"""
from django.urls import path
from . import views
from .views import enviar_mensaje
app_name = 'foro' 

urlpatterns = [
    # ---------------- WEB ----------------
    path("lista/", views.lista_publicaciones, name="lista_publicaciones"),
    path("crear/", views.crear_publicacion, name="crear_publicacion"),
    
    # --- URL NUEVA Y MODIFICADAS ---
    path("publicacion/<int:pk>/", views.detalle_publicacion, name="detalle_publicacion"),
    path("publicacion/<int:pk>/alternar/", views.alternar_publicacion_web, name="alternar_publicacion_web"),
    path("publicacion/<int:pk>/eliminar/", views.eliminar_publicacion_web, name="eliminar_publicacion_web"),
    path("comentario/<int:pk>/eliminar/", views.eliminar_comentario_web, name="eliminar_comentario_web"),
    path("comentario/<int:pk>/restaurar/", views.restaurar_comentario_web, name="restaurar_comentario_web"),

    # ---------------- API (COINCIDE CON ANDROID) ----------------
    # GET /foro/api/v1/publicaciones/
    path("api/v1/publicaciones/", views.api_publicaciones_list, name="api_publicaciones_list"),

    # GET  /foro/api/v1/publicaciones/<id>/comentarios/
    # POST /foro/api/v1/publicaciones/<id>/comentarios/
    path("api/v1/publicaciones/<int:pk>/comentarios/", views.api_publicacion_comentarios, name="api_publicacion_comentarios"),
    path(
            "api/v1/publicaciones/<int:pk>/adjuntos/",
            views.api_subir_adjunto,
            name="api_subir_adjunto",
        ),
    path("foro/mensaje/", views.crear_mensaje, name="api_foro_mensaje"),
    path("api/publicaciones/<int:publicacion_id>/mensaje/",enviar_mensaje,name="foro_enviar_mensaje"),
    path("api/v1/comentarios/<int:pk>/", views.api_eliminar_comentario, name="api_eliminar_comentario"),
    path("api/v1/comentarios/<int:pk>/like/", views.api_toggle_like_comentario, name="api_toggle_like_comentario"),
    path("comentario/<int:pk>/reaccionar/", views.reaccionar_comentario_web, name="reaccionar_comentario_web"),
    path('api/v1/adjuntos/<int:pk>/', views.api_eliminar_adjunto, name='api_eliminar_adjunto'),
    path('api/v1/adjuntos/<int:pk>/like/', views.api_toggle_like_adjunto, name='api_toggle_like_adjunto'),
    path("adjunto/<int:pk>/reaccionar/", views.reaccionar_adjunto_web, name="reaccionar_adjunto_web"),
    path("adjunto/<int:pk>/eliminar/", views.eliminar_adjunto_web, name="eliminar_adjunto_web"),

]