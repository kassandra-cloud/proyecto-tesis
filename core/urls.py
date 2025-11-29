from django.urls import path
from .views import home,sin_permiso
from django.contrib.auth.views import LoginView
from .api import RegistrarFCMTokenView
from . import api_fcm
from . import views
from .views import RequestRecoveryCodeAPI, ResetPasswordWithCodeAPI
urlpatterns = [
    path("home/", views.home, name="home"),
    path("", LoginView.as_view(), name="login"),
    path("sin-permiso/", sin_permiso, name="sin_permiso"),
    path("api/v1/registrar-fcm-token/", RegistrarFCMTokenView.as_view(), name="api_registrar_fcm_token"),
    path("fcm/register/", api_fcm.registrar_fcm_token, name="registrar-fcm-token"),
    path('api/auth/request-code/', RequestRecoveryCodeAPI.as_view()),
    path('api/auth/reset-password-code/', ResetPasswordWithCodeAPI.as_view()),
]