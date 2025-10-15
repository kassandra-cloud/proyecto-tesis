from django.urls import path
from .views import home,sin_permiso

urlpatterns = [
    path("", home, name="home"),
    path("sin-permiso/", sin_permiso, name="sin_permiso"),
]