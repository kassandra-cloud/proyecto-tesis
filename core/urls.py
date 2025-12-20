"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Define el mapeo de URLs para la aplicación core.
                       Incluye rutas para el home, login, página de error, 
                       y endpoints de la API (registro FCM y recuperación de clave).
--------------------------------------------------------------------------------
"""

# Importa función path para rutas.
from django.urls import path
# Importa vistas desde el archivo local.
from .views import home, sin_permiso
# Importa vista genérica de Login de Django.
from django.contrib.auth.views import LoginView
# Importa vista API basada en clases.
from .api import RegistrarFCMTokenView
# Importa módulo de API FCM (aunque no lo tenemos documentado, se importa aquí).
from . import api_fcm
from . import views
# Importa vistas API específicas.
from .views import RequestRecoveryCodeAPI, ResetPasswordWithCodeAPI

urlpatterns = [
    # Ruta para el dashboard principal.
    path("home/", views.home, name="home"),
    # Ruta raíz (/) que carga el Login.
    path("", LoginView.as_view(), name="login"),
    # Ruta para página de error de permisos.
    path("sin-permiso/", sin_permiso, name="sin_permiso"),
    # Endpoint API (versión clase) para registrar token FCM.
    path("api/v1/registrar-fcm-token/", RegistrarFCMTokenView.as_view(), name="api_registrar_fcm_token"),
    # Endpoint API (versión función) para registrar token FCM (parece duplicado o legado).
    path("fcm/register/", api_fcm.registrar_fcm_token, name="registrar-fcm-token"),
    # Endpoint API para solicitar código de recuperación de contraseña.
    path('api/auth/request-code/', RequestRecoveryCodeAPI.as_view()),
    # Endpoint API para resetear contraseña con código.
    path('api/auth/reset-password-code/', ResetPasswordWithCodeAPI.as_view()),
]