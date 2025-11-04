# foro/forms.py
from django import forms
<<<<<<< HEAD
from .models import Publicacion
=======
from .models import Publicacion, Comentario

>>>>>>> 75e549b (api de taller y foro)

class PublicacionForm(forms.ModelForm):
    class Meta:
        model = Publicacion
<<<<<<< HEAD
        fields = ['contenido']
        widgets = {
            'contenido': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Escribe tu publicación aquí...'}),
        }
=======
        fields = ["contenido"]
        widgets = {
            "contenido": forms.Textarea(attrs={
                "rows": 3,
                "class": "form-control",
                "placeholder": "Escribe aquí tu publicación…",
            })
        }
        labels = {"contenido": ""}


class ComentarioCreateForm(forms.ModelForm):
    # Campo oculto para soportar “Responder”. Guardamos el ID del comentario padre.
    parent_id = forms.IntegerField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Comentario
        fields = ["contenido"]  # parent se asigna en save() usando parent_id
        widgets = {
            "contenido": forms.Textarea(attrs={
                "rows": 2,
                "class": "form-control",
                "placeholder": "Escribe un comentario…",
            })
        }
        labels = {"contenido": ""}

    def save(self, publicacion, autor, commit=True):
        """
        Crea el comentario asignando publicacion, autor y (opcional) el parent.
        Se llama desde la vista con: form.save(publicacion, request.user)
        """
        comentario = Comentario(
            publicacion=publicacion,
            autor=autor,
            contenido=self.cleaned_data["contenido"],
        )

        pid = self.cleaned_data.get("parent_id")
        if pid:
            # Validamos que el padre pertenezca a la misma publicación
            try:
                comentario.parent = Comentario.objects.get(id=pid, publicacion=publicacion)
            except Comentario.DoesNotExist:
                pass  # si no existe o no corresponde, lo ignoramos

        if commit:
            comentario.save()
        return comentario
>>>>>>> 75e549b (api de taller y foro)
