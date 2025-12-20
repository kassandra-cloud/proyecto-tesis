"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Define el formulario 'AnuncioForm' basado en el modelo 
                       Anuncio. Se utiliza en las vistas para validar y procesar 
                       la entrada de datos del usuario al crear o editar anuncios.
--------------------------------------------------------------------------------
"""

# Importa el módulo de formularios de Django.
from django import forms
# Importa el modelo Anuncio.
from .models import Anuncio

class AnuncioForm(forms.ModelForm):
    """Formulario para la gestión de anuncios."""
    class Meta:
        # Vincula el formulario al modelo Anuncio.
        model = Anuncio
        # Especifica qué campos deben aparecer en el formulario HTML.
        # Nota: 'autor' y 'fecha' se manejan automáticamente, no aquí.
        fields = ['titulo', 'contenido'] 
        
        # Define atributos HTML (widgets) para estilizar los campos con clases CSS (ej. Bootstrap).
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'contenido': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }