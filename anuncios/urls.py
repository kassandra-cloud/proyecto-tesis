# anuncios/urls.py
from django.urls import path
from . import views

app_name = 'anuncios'

urlpatterns = [
    path('', views.lista_anuncios, name='lista_anuncios'),
    path('crear/', views.crear_anuncio, name='crear_anuncio'),
    path('<int:pk>/editar/', views.editar_anuncio, name='editar_anuncio'),
    path('<int:pk>/eliminar/', views.eliminar_anuncio, name='eliminar_anuncio'),
]