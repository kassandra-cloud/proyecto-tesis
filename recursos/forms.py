"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Definición de formularios Django para la gestión (creación/edición)
               de los objetos Recurso desde la interfaz web administrativa.
--------------------------------------------------------------------------------
"""
from django import forms
from .models import Recurso

class RecursoForm(forms.ModelForm):
    class Meta:
        model = Recurso
        fields = ['nombre', 'descripcion', 'disponible']
        # Estilos CSS (Bootstrap) para los campos del formulario
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        # Etiquetas personalizadas
        labels = {
            'nombre': 'Nombre del Recurso',
            'descripcion': 'Descripción (opcional)',
            'disponible': 'Disponible para reservar',
        }