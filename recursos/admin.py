"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Configuración del panel de administración de Django para la app 
               'recursos'. Permite gestionar los Recursos disponibles y visualizar 
               las Solicitudes de Reserva.
--------------------------------------------------------------------------------
"""
from django.contrib import admin
from .models import Recurso, SolicitudReserva

# Registro del modelo Recurso en el admin
@admin.register(Recurso)
class RecursoAdmin(admin.ModelAdmin):
    # Columnas visibles en la lista de recursos
    list_display = ("id", "nombre", "disponible")
    # Campos por los que se puede buscar
    search_fields = ("nombre", "descripcion")
    # Filtros laterales (por disponibilidad)
    list_filter = ("disponible",)

# Registro del modelo SolicitudReserva en el admin
@admin.register(SolicitudReserva)
class SolicitudReservaAdmin(admin.ModelAdmin):
    # Columnas visibles: ID, qué recurso, quién pide, fechas y estado
    list_display = ("id", "recurso", "solicitante", "fecha_inicio", "fecha_fin", "estado", "creado_el")
    # Filtros laterales por estado y recurso
    list_filter = ("estado", "recurso")
    # Búsqueda por nombre del recurso, usuario solicitante o motivo
    search_fields = ("recurso__nombre", "solicitante__username", "motivo")
    # Navegación jerárquica por fecha de inicio
    date_hierarchy = "fecha_inicio"