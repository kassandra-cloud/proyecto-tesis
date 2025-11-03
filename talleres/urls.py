from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_talleres, name='lista_talleres'),
    path('crear/', views.crear_taller, name='crear_taller'),
    path('<int:taller_id>/', views.detalle_taller, name='detalle_taller'),
    path('<int:taller_id>/editar/', views.editar_taller, name='editar_taller'),
    path('<int:taller_id>/eliminar/', views.eliminar_taller, name='eliminar_taller'),
]