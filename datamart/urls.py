"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Definición de rutas URL para las vistas del panel de inteligencia 
               de negocios, ejecución de ETL y descarga de reportes.
--------------------------------------------------------------------------------
"""
from django.urls import path  # Importa función para definir rutas
from . import views  # Importa las vistas de la app actual

urlpatterns = [
    # Ruta para ver el dashboard principal
    path('panel-bi/', views.panel_bi_view, name='panel_bi'),
    # Ruta para gatillar el proceso ETL manualmente
    path('ejecutar-etl/', views.ejecutar_etl_view, name='ejecutar_etl'),
    # Ruta para descargar el reporte en PDF
    path('descargar-informe/', views.generar_pdf_view, name='descargar_pdf'),
]