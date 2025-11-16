from django.urls import path
from .views import home,sin_permiso
from django.contrib.auth.views import LoginView
from .api import RegistrarFCMTokenView
urlpatterns = [
    path("home", home, name="home"),
    path("", LoginView.as_view(), name="login"),
    path("sin-permiso/", sin_permiso, name="sin_permiso"),
    path("api/v1/registrar-fcm-token/", RegistrarFCMTokenView.as_view(), name="api_registrar_fcm_token"),
]