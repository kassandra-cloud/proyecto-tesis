# en /talleres/urls.py

from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from .api import TallerViewSet

app_name = 'talleres'

urlpatterns = [
    path('', views.lista_talleres, name='lista_talleres'),
    
    # --- NUEVA RUTA ---
    path('archivados/', views.lista_talleres_archivados, name='lista_talleres_archivados'),
    
    path('crear/', views.crear_taller, name='crear_taller'),
    path('<int:pk>/', views.detalle_taller, name='detalle_taller'),
    path('<int:pk>/editar/', views.editar_taller, name='editar_taller'),
    path('<int:pk>/eliminar/', views.eliminar_taller, name='eliminar_taller'),
    
    # --- NUEVA RUTA ---
    path('<int:pk>/cancelar/', views.cancelar_taller, name='cancelar_taller'),
    
    path('<int:pk>/inscribir/', views.inscribir_taller, name='inscribir_taller'),
    path('mis-inscripciones/', views.mis_inscripciones, name='mis_inscripciones'),
]

# API (DRF)
router = DefaultRouter()
router.register(r"api/talleres", TallerViewSet, basename="api_talleres")
urlpatterns += router.urls