"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Mapeo de URLs para la aplicación Usuarios.
               - Gestión de usuarios (CRUD)
               - API endpoints (Login, Reset Password, Health Check)
               - Flujos de seguridad web (Cambio de pass, recuperación)
--------------------------------------------------------------------------------
"""
from django.urls import path
from . import views
from .views import health
from usuarios import views as u

urlpatterns = [
    # --- GESTIÓN DE USUARIOS (WEB) ---
    path("", views.lista_usuarios, name="lista_usuarios"), # Listado con paginación
    path("crear/", views.crear_usuario, name="crear_usuario"), # Formulario de creación
    path("<int:pk>/editar/", views.editar_usuario, name="editar_usuario"), # Edición
    path("<int:pk>/eliminar/", views.eliminar_usuario, name="eliminar_usuario"), # Eliminación
    path("usuarios/<int:pk>/deshabilitar/", u.deshabilitar_usuario, name="deshabilitar"), # Bloqueo lógico
    path("usuarios/<int:pk>/restaurar/", u.restaurar_usuario, name="restaurar"), # Desbloqueo
    path('alerta-movil/', views.alerta_movil, name='alerta_movil'), # Vista de bloqueo móvil

    # --- API (MOVIL) ---
    path('api/login/', views.login_api, name='login_api'), # Endpoint de autenticación
    path('api/cambiar-password-inicial/', views.cambiar_password_inicial, name='cambiar_password_inicial'), # Cambio pass obligatorio
    path('api/health/', health, name='health'), # Health check del backend
    path("api/test/", views.ping, name="api_test"), # Ping test simple
    path("api/usuarios/by-role/", views.api_usuarios_by_role, name="api_usuarios_by_role"), # Selector dinámico

    # --- FLUJOS DE SEGURIDAD WEB ---
    # 1. Cambio de contraseña obligatorio (Primera vez)
    path('cambiar-password-obligatorio/', views.cambiar_password_obligatorio, name='cambiar_password_obligatorio'),
    
    # 2. Nueva Recuperación con Código (Reemplaza a la lógica vieja)
    path('recuperar-cuenta/', views.web_recuperar_paso1, name='web_recuperar_paso1'), # Paso 1: Pedir código
    path('recuperar-cuenta/verificar/', views.web_recuperar_paso2, name='web_recuperar_paso2'), # Paso 2: Verificar código
]