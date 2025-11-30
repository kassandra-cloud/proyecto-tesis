from django.urls import path
from . import views
from .views import health
from django.contrib.auth import views as auth_views
from usuarios import views as u
urlpatterns = [
    path("", views.lista_usuarios, name="lista_usuarios"),
    path("crear/", views.crear_usuario, name="crear_usuario"),
    path("<int:pk>/editar/", views.editar_usuario, name="editar_usuario"),
    path("<int:pk>/eliminar/", views.eliminar_usuario, name="eliminar_usuario"),
    path('api/login/', views.login_api, name='login_api'),
    path('api/cambiar-password-inicial/', views.cambiar_password_inicial, name='cambiar_password_inicial'),
    path('api/health/', health, name='health'),   # ← nuevo
    path("api/test/", views.ping, name="api_test"),
    path('cambiar-password-obligatorio/', views.cambiar_password_obligatorio, name='cambiar_password_obligatorio'),
    path('accounts/password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('accounts/password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path("usuarios/<int:pk>/deshabilitar/", u.deshabilitar_usuario, name="deshabilitar"),
    path("usuarios/<int:pk>/restaurar/", u.restaurar_usuario, name="restaurar"),
    path("api/usuarios/by-role/", views.api_usuarios_by_role, name="api_usuarios_by_role"),
]
