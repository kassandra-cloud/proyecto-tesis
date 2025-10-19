from django.urls import path
from . import views
from . import api as api_views
app_name = 'votaciones'

urlpatterns = [
    path('', views.lista_votaciones, name='lista_votaciones'),
    path('crear/', views.crear_votacion, name='crear_votacion'),
    path('<int:pk>/', views.detalle_votacion, name='detalle_votacion'),
    path('<int:pk>/votar/', views.emitir_voto, name='emitir_voto'),
    path('<int:pk>/cerrar/', views.cerrar_votacion, name='cerrar_votacion'),
    path('<int:pk>/editar/', views.editar_votacion, name='editar_votacion'),
    path('<int:pk>/eliminar/', views.eliminar_votacion, name='eliminar_votacion'),
    path('api/v1/abiertas/', api_views.abiertas, name='api_abiertas'),
    path('api/v1/<int:pk>/votar/', api_views.votar, name='api_votar'),
    path('api/v1/<int:pk>/resultados/', api_views.resultados, name='api_resultados'),
]