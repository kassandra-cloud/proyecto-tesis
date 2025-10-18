from django.urls import path
from . import views

app_name = 'votaciones'

urlpatterns = [
    path('', views.lista_votaciones, name='lista_votaciones'),
    path('crear/', views.crear_votacion, name='crear_votacion'),
    path('<int:pk>/', views.detalle_votacion, name='detalle_votacion'),
    path('<int:pk>/votar/', views.emitir_voto, name='emitir_voto'),
    path('<int:pk>/cerrar/', views.cerrar_votacion, name='cerrar_votacion'),
    path('<int:pk>/editar/', views.editar_votacion, name='editar_votacion'),
    path('<int:pk>/eliminar/', views.eliminar_votacion, name='eliminar_votacion'),
]