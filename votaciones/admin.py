from django.contrib import admin
from .models import Votacion, Opcion, Voto

admin.site.register(Votacion)
admin.site.register(Opcion)
admin.site.register(Voto)