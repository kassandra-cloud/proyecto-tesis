from django.urls import path
from . import views
<<<<<<< HEAD

=======
from rest_framework.routers import DefaultRouter
from .api import TallerViewSet
>>>>>>> 75e549b (api de taller y foro)
urlpatterns = [
    path('', views.lista_talleres, name='lista_talleres'),
    path('crear/', views.crear_taller, name='crear_taller'),
    path('<int:taller_id>/', views.detalle_taller, name='detalle_taller'),
    path('<int:taller_id>/editar/', views.editar_taller, name='editar_taller'),
    path('<int:taller_id>/eliminar/', views.eliminar_taller, name='eliminar_taller'),
<<<<<<< HEAD
]
=======
]

router = DefaultRouter()
router.register(r"api/talleres", TallerViewSet, basename="api_talleres")
urlpatterns += router.urls
>>>>>>> 75e549b (api de taller y foro)
