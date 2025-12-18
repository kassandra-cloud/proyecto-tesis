from django.urls import path
from . import views
from .views import health
from usuarios import views as u

urlpatterns = [
    # --- GESTIÓN DE USUARIOS ---
    path("", views.lista_usuarios, name="lista_usuarios"),
    path("crear/", views.crear_usuario, name="crear_usuario"),
    path("<int:pk>/editar/", views.editar_usuario, name="editar_usuario"),
    path("<int:pk>/eliminar/", views.eliminar_usuario, name="eliminar_usuario"),
    path("usuarios/<int:pk>/deshabilitar/", u.deshabilitar_usuario, name="deshabilitar"),
    path("usuarios/<int:pk>/restaurar/", u.restaurar_usuario, name="restaurar"),
    path('alerta-movil/', views.alerta_movil, name='alerta_movil'),

    # --- API (MOVIL) ---
    path('api/login/', views.login_api, name='login_api'),
    path('api/cambiar-password-inicial/', views.cambiar_password_inicial, name='cambiar_password_inicial'),
    path('api/health/', health, name='health'),
    path("api/test/", views.ping, name="api_test"),
    path("api/usuarios/by-role/", views.api_usuarios_by_role, name="api_usuarios_by_role"),

    # --- FLUJOS DE SEGURIDAD WEB ---
    # 1. Cambio de contraseña obligatorio (Primera vez)
    path('cambiar-password-obligatorio/', views.cambiar_password_obligatorio, name='cambiar_password_obligatorio'),
    
    # 2. Nueva Recuperación con Código (Reemplaza a la lógica vieja)
    path('recuperar-cuenta/', views.web_recuperar_paso1, name='web_recuperar_paso1'),
    path('recuperar-cuenta/verificar/', views.web_recuperar_paso2, name='web_recuperar_paso2'),
]