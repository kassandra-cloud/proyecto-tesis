"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Formularios para la gestión web de votaciones. Incluye validaciones 
               de fechas y procesamiento dinámico de opciones de respuesta.
--------------------------------------------------------------------------------
"""
from django import forms
from .models import Votacion
from django.utils import timezone

# Formulario para Crear Votación
class VotacionForm(forms.ModelForm):
    # Campos de fecha y hora separados para mejor UX
    fecha_cierre_date = forms.DateField(
        label="Fecha de Cierre",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    fecha_cierre_time = forms.TimeField(
        label="Hora de Cierre",
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
    )
    
    # Campo oculto para recibir las opciones generadas dinámicamente en el frontend
    opciones = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Votacion
        fields = ['pregunta']
        widgets = {
            'pregunta': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'pregunta': 'Pregunta de la Votación',
        }

    # Validación: La fecha no puede ser pasada
    def clean_fecha_cierre_date(self):
        fecha = self.cleaned_data.get('fecha_cierre_date')
        if fecha and fecha < timezone.now().date():
            raise forms.ValidationError("La fecha de cierre no puede ser anterior a la fecha actual.")
        return fecha

    def clean(self):
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha_cierre_date')
        hora = cleaned_data.get('fecha_cierre_time')

        # Combina fecha y hora para crear datetime aware
        if fecha and hora:
            fecha_cierre_completa = timezone.make_aware(
                timezone.datetime.combine(fecha, hora)
            )
            if fecha_cierre_completa < timezone.now():
                self.add_error('fecha_cierre_time', "La hora de cierre no puede ser anterior a la hora actual.")
            cleaned_data['fecha_cierre'] = fecha_cierre_completa
        
        # Procesa opciones dinámicas enviadas desde el frontend (inputs 'opcion_dinamica_X')
        opciones_list = [
            value.strip() for key, value in self.data.items() 
            if key.startswith('opcion_dinamica_') and value.strip()
        ]

        if len(opciones_list) < 2:
            self.add_error(None, "Debes proporcionar al menos dos opciones de voto válidas.")
        
        cleaned_data['opciones'] = opciones_list
        return cleaned_data
    
# Formulario para Editar Votación (solo fecha de cierre)
class VotacionEditForm(forms.ModelForm):
    # Campos separados para fecha y hora
    fecha_cierre_date = forms.DateField(
        label="Nueva Fecha de Cierre",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    fecha_cierre_time = forms.TimeField(
        label="Nueva Hora de Cierre",
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
    )

    class Meta:
        model = Votacion
        fields = [] # No edita pregunta ni opciones directamente

    def clean_fecha_cierre_date(self):
        fecha = self.cleaned_data.get('fecha_cierre_date')
        if fecha and fecha < timezone.now().date():
            raise forms.ValidationError("La fecha de cierre no puede ser anterior a la fecha actual.")
        return fecha

    def clean(self):
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha_cierre_date')
        hora = cleaned_data.get('fecha_cierre_time')

        if fecha and hora:
            fecha_cierre_completa = timezone.make_aware(
                timezone.datetime.combine(fecha, hora)
            )
            if fecha_cierre_completa < timezone.now():
                self.add_error('fecha_cierre_time', "La hora de cierre no puede ser anterior a la hora actual.")
            
            cleaned_data['fecha_cierre'] = fecha_cierre_completa
        
        return cleaned_data