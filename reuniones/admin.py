from django.contrib import admin

from reuniones.models import Acta

@admin.register(Acta)
class ActaAdmin(admin.ModelAdmin):
    list_display = ('reunion', 'estado_transcripcion', 'aprobada')
    list_filter = ('estado_transcripcion', 'aprobada')
# FIN DEL BLOQUE NUEVO

class ActaInline(admin.StackedInline): # <-- Esta línea ya la tenías
    model = Acta
    can_delete = False
    verbose_name_plural = 'Acta'
