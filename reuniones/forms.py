from django import forms
from .models import Reunion, Acta # <--- AÑADE Acta A LA IMPORTACIÓN

class ReunionForm(forms.ModelForm):
    class Meta:
        model = Reunion
        fields = ['titulo', 'tipo', 'fecha', 'tabla']
        widgets = {
            'fecha': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'tabla': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }
        labels = {
            'titulo': 'Título de la Reunión',
            'tipo': 'Tipo de Reunión',
            'fecha': 'Fecha y Hora',
            'tabla': 'Tabla de Contenidos (Temas a tratar)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha'].input_formats = ('%Y-%m-%dT%H:%M',)


class ActaForm(forms.ModelForm):
    class Meta:
        model = Acta
        fields = ['contenido']
        widgets = {
            'contenido': forms.Textarea(attrs={'class': 'form-control', 'rows': 15}),
        }
        labels = {
            'contenido': 'Contenido del Acta'
        }