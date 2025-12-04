# datamart/admin.py (Versión actualizada para tus nuevos modelos)
from django.contrib import admin
from .models import FactMetricasDiarias, DimVecino, DimActa

@admin.register(FactMetricasDiarias)
class FactMetricasDiariasAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'disponibilidad_sistema', 'tiempo_respuesta_ms', 'fallos_votacion')

@admin.register(DimVecino)
class DimVecinoAdmin(admin.ModelAdmin):
    # Elimina 'usa_app_movil' de aquí:
    list_display = ('nombre_completo', 'vecino_id_oltp') 
    # Elimina 'list_filter' si solo tenías ese campo, o quítalo de la lista:
    search_fields = ('nombre_completo',)

@admin.register(DimActa)
class DimActaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'precision_transcripcion')