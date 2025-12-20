"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Configuración del panel de administración de Django para visualizar 
               y gestionar los modelos del Datamart (Dimensiones y Hechos).
--------------------------------------------------------------------------------
"""
from django.contrib import admin  # Importa el módulo de administración de Django
from .models import FactMetricasDiarias, DimVecino, DimActa  # Importa los modelos del Datamart a registrar

# Registra el modelo de hechos de métricas diarias en el admin
@admin.register(FactMetricasDiarias)
class FactMetricasDiariasAdmin(admin.ModelAdmin):
    # Define las columnas que se mostrarán en la lista de registros
    list_display = ('fecha', 'disponibilidad_sistema', 'tiempo_respuesta_ms', 'fallos_votacion')

# Registra la dimensión de vecinos en el admin
@admin.register(DimVecino)
class DimVecinoAdmin(admin.ModelAdmin):
    # Define las columnas visibles: nombre y el ID original del sistema transaccional
    list_display = ('nombre_completo', 'vecino_id_oltp') 
    # Habilita una barra de búsqueda que filtra por nombre completo
    search_fields = ('nombre_completo',)

# Registra la dimensión de actas en el admin
@admin.register(DimActa)
class DimActaAdmin(admin.ModelAdmin):
    # Muestra el título del acta y su precisión de transcripción en la lista
    list_display = ('titulo', 'precision_transcripcion')