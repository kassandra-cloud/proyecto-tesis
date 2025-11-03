from django import forms
from .models import Taller

class TallerForm(forms.ModelForm):
    class Meta:
        model = Taller
        # Campos que la Directiva puede llenar
        fields = ['nombre', 'descripcion', 'cupos_totales']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'cupos_totales': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'nombre': 'Nombre del Taller',
            'descripcion': 'Descripción',
            'cupos_totales': 'Cupos Totales',
        }