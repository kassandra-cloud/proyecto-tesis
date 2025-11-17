# en /talleres/forms.py

from django import forms
from .models import Taller, Inscripcion
from django.utils import timezone

class TallerForm(forms.ModelForm):
    class Meta:
        model = Taller
        fields = [
            'nombre', 
            'descripcion', 
            'cupos_totales', # Nombre corregido
            'fecha_inicio', 
            'fecha_termino'
        ]
        
        # Estos widgets se mantienen
        widgets = {
            'fecha_inicio': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, 
                format='%Y-%m-%dT%H:%M'
            ),
            'fecha_termino': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, 
                format='%Y-%m-%dT%H:%M'
            ),
            'descripcion': forms.Textarea(attrs={'rows': 4}),
        }

    # --- ESTE ES EL MÉTODO __init__ CORREGIDO ---
    def __init__(self, *args, **kwargs):
        """
        Agrega la clase 'form-control' de Bootstrap a todos los campos,
        preservando los atributos existentes (como 'type').
        """
        super().__init__(*args, **kwargs)
        
        for field_name, field in self.fields.items():
            # Obtenemos los atributos existentes (ej. {'type': 'datetime-local'})
            existing_attrs = field.widget.attrs
            
            # Obtenemos la clase CSS existente, si hay alguna
            existing_class = existing_attrs.get('class', '')
            
            # Añadimos 'form-control' a la lista de clases
            field.widget.attrs['class'] = f'{existing_class} form-control'.strip()
    # --- FIN DEL MÉTODO __init__ CORREGIDO ---

    # --- VALIDACIÓN (Se mantiene igual) ---
    def clean(self):
        cleaned_data = super().clean()
        inicio = cleaned_data.get("fecha_inicio")
        fin = cleaned_data.get("fecha_termino")
        instancia = self.instance

        if inicio and fin:
            if fin <= inicio:
                raise forms.ValidationError(
                    "La fecha y hora de término debe ser posterior a la de inicio."
                )
            if not instancia.pk and inicio < timezone.now():
                 raise forms.ValidationError(
                    "No se puede programar un taller en una fecha/hora pasada."
                 )
        return cleaned_data


# --- FORMULARIO DE CANCELACIÓN (Añadimos 'form-control' también) ---
class CancelacionTallerForm(forms.ModelForm):
    class Meta:
        model = Taller
        fields = ['motivo_cancelacion']
        widgets = {
            'motivo_cancelacion': forms.Textarea(
                attrs={'rows': 4, 'placeholder': 'Explique brevemente por qué se cancela el taller...'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['motivo_cancelacion'].required = True
        self.fields['motivo_cancelacion'].label = "Motivo de la Cancelación"
        # Agregamos la clase aquí
        self.fields['motivo_cancelacion'].widget.attrs['class'] = 'form-control'


# --- FORMULARIO DE INSCRIPCIÓN (Se mantiene igual) ---
class InscripcionForm(forms.ModelForm):
    class Meta:
        model = Inscripcion
        fields = []