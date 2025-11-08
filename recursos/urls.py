from django.urls import path
from . import views

app_name = 'recursos'

urlpatterns = [
    # CRUD para la Directiva
    path('', views.lista_recursos, name='lista_recursos'),
    path('crear/', views.crear_recurso, name='crear_recurso'),
    path('<int:pk>/editar/', views.editar_recurso, name='editar_recurso'),
    
    # --- URLs MODIFICADAS ---
    path('<int:pk>/deshabilitar/', views.deshabilitar_recurso, name='deshabilitar_recurso'),
    path('<int:pk>/restaurar/', views.restaurar_recurso, name='restaurar_recurso'),
    
    # (Aquí pondremos las vistas para los vecinos más adelante)
]