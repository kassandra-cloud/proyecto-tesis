from django import forms
from django.utils import timezone  
from .models import Reunion, Acta

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

    # --- 2. NUEVA VALIDACIÓN ---
    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        
        # Si existe una fecha y es menor a "ahora mismo"
        if fecha and fecha < timezone.now():
            raise forms.ValidationError("La fecha de la reunión no puede ser anterior al momento actual.")
        
        return fecha
    # ---------------------------

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha'].input_formats = ('%Y-%m-%dT%H:%M',)
        
        # Opcional: Esto ayuda visualmente bloqueando días pasados en el calendario HTML
        # (Aunque la validación real la hace el método clean_fecha de arriba)
        self.fields['fecha'].widget.attrs['min'] = timezone.now().strftime('%Y-%m-%dT%H:%M')

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