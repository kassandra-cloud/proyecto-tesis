from django import forms
from .models import Votacion
from django.utils import timezone

class VotacionForm(forms.ModelForm):
    fecha_cierre_date = forms.DateField(
        label="Fecha de Cierre",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    fecha_cierre_time = forms.TimeField(
        label="Hora de Cierre",
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
    )
    
    
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
        

        opciones_list = [
            value.strip() for key, value in self.data.items() 
            if key.startswith('opcion_dinamica_') and value.strip()
        ]

        if len(opciones_list) < 2:
            self.add_error(None, "Debes proporcionar al menos dos opciones de voto válidas.")
        
        cleaned_data['opciones'] = opciones_list
        return cleaned_data
    
class VotacionEditForm(forms.ModelForm):
    # Campos separados para fecha y hora, igual que en la creación
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
        fields = [] # No tomamos campos directos del modelo aquí

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