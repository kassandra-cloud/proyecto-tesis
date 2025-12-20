"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Definición de formularios de Django para la creación de 
               publicaciones y comentarios, incluyendo validaciones personalizadas.
--------------------------------------------------------------------------------
"""
# foro/forms.py
from django import forms
from .models import Publicacion
from .models import Publicacion, Comentario

# Formulario para crear una nueva publicación
class PublicacionForm(forms.ModelForm):
    class Meta:
        model = Publicacion

        fields = ["contenido"]
        widgets = {
            "contenido": forms.Textarea(attrs={
                "rows": 3,
                "class": "form-control",
                "placeholder": "Escribe aquí tu publicación…",
            })
        }
        labels = {"contenido": ""}

# Formulario para crear comentarios (incluye soporte para archivos)
class ComentarioCreateForm(forms.ModelForm):
    # 1. Campo oculto para respuestas (ID del comentario padre)
    parent_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    
    # 2. Campo para subir archivos (Opcional)
    archivo = forms.FileField(
        required=False, 
        widget=forms.FileInput(attrs={
            'class': 'form-control form-control-sm mt-2',
            'accept': 'image/*',  # ID AÑADIDO
        })
    )

    class Meta:
        model = Comentario
        fields = ["contenido", "archivo"]
        widgets = {
            "contenido": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Escribe un comentario..."
            }),
            "archivo": forms.ClearableFileInput(attrs={
                "id": "id_comentario_archivo",
                "class": "form-control form-control-sm"
            })
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 3. Hacemos que el texto NO sea obligatorio a nivel de campo
        self.fields['contenido'].required = False

    def clean(self):
        """Validación personalizada: Exigir Texto O Archivo."""
        cleaned_data = super().clean()
        contenido = cleaned_data.get("contenido")
        archivo = cleaned_data.get("archivo")

        # Si ambos están vacíos, lanzamos error
        if not contenido and not archivo:
            raise forms.ValidationError("Debes escribir un mensaje o subir un archivo.")
        
        return cleaned_data

    def save(self, publicacion, autor, commit=True):
        """
        Crea el comentario asignando publicacion, autor y (opcional) el parent.
        NOTA: Este método SOLO se usa para comentarios de texto. 
        Si hay archivo, la vista se encarga de crear el ArchivoAdjunto manualmente.
        """
        comentario = Comentario(
            publicacion=publicacion,
            autor=autor,
            contenido=self.cleaned_data.get("contenido", ""), # Usamos get por si viene vacío
        )

        pid = self.cleaned_data.get("parent_id")
        if pid:
            # Validamos que el padre pertenezca a la misma publicación
            try:
                comentario.parent = Comentario.objects.get(id=pid, publicacion=publicacion)
            except Comentario.DoesNotExist:
                pass

        if commit:
            comentario.save()
        return comentario