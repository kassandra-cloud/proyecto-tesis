from django.contrib import admin
from .models import Recurso, SolicitudReserva
# Register your models here.
@admin.register(Recurso)
class RecursoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "disponible")
    search_fields = ("nombre", "descripcion")
    list_filter = ("disponible",)

@admin.register(SolicitudReserva)
class SolicitudReservaAdmin(admin.ModelAdmin):
    list_display = ("id", "recurso", "solicitante", "fecha_inicio", "fecha_fin", "estado", "creado_el")
    list_filter = ("estado", "recurso")
    search_fields = ("recurso__nombre", "solicitante__username", "motivo")
    date_hierarchy = "fecha_inicio"