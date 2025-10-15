# core/admin.py
from django.contrib import admin
from .models import Perfil

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rut', 'rol')
    list_filter = ('rol',)
    search_fields = ('usuario__username', 'usuario__email', 'rut')
