from django.urls import path
from . import views
from .views import health
urlpatterns = [
    path("", views.lista_usuarios, name="lista_usuarios"),
    path("crear/", views.crear_usuario, name="crear_usuario"),
    path("<int:pk>/editar/", views.editar_usuario, name="editar_usuario"),
    path("<int:pk>/eliminar/", views.eliminar_usuario, name="eliminar_usuario"),
    path('api/login/', views.login_api, name='login_api'),
    path('api/health/', health, name='health'),   # ← nuevo
    path("api/test/", views.ping, name="api_test"),
]
