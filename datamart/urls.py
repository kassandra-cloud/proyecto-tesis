# datamart/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('panel-bi/', views.panel_bi_view, name='panel_bi'),
    path('ejecutar-etl/', views.ejecutar_etl_view, name='ejecutar_etl'),
]