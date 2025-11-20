from django.contrib import admin
from reuniones.models import Acta, Reunion, Asistencia
@admin.register(Acta)
class ActaAdmin(admin.ModelAdmin):
    list_display = ('reunion', 'estado_transcripcion', 'aprobada')
    list_filter = ('estado_transcripcion', 'aprobada')
# FIN DEL BLOQUE NUEVO

class ActaInline(admin.StackedInline):
    model = Acta
    can_delete = False
    verbose_name_plural = 'Acta'
class AsistenciaInline(admin.TabularInline):
    model = Asistencia
    extra = 0
    can_delete = True

@admin.register(Reunion)
class ReunionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'fecha', 'estado', 'tipo')
    list_filter = ('estado', 'tipo', 'fecha')
    search_fields = ('titulo',)
    inlines = [ActaInline, AsistenciaInline]