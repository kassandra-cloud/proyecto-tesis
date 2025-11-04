from django.db import models
from django.contrib.auth.models import User
import os
<<<<<<< HEAD
=======
from django.conf import settings
>>>>>>> 75e549b (api de taller y foro)

class Publicacion(models.Model):
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    contenido = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Publicación de {self.autor.username}'

class ArchivoAdjunto(models.Model):
    publicacion = models.ForeignKey(Publicacion, on_delete=models.CASCADE, related_name='adjuntos')
    archivo = models.FileField(upload_to='archivos/')

    def __str__(self):
        return self.archivo.name

    # ------------------------------
    # Propiedad para detectar tipo de archivo
    # ------------------------------
    @property
    def tipo_archivo(self):
        ext = os.path.splitext(self.archivo.name)[1].lower()  # extensión en minúscula
        if ext in ['.jpg', '.jpeg', '.png', '.gif']:
            return 'imagen'
        elif ext in ['.mp3', '.wav', '.ogg', '.webm', '.m4a']:
            return 'audio'
        elif ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
            return 'video'
        else:
            return 'otro'
<<<<<<< HEAD
=======
class Comentario(models.Model):
    publicacion = models.ForeignKey("Publicacion", on_delete=models.CASCADE, related_name="comentarios")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    contenido = models.TextField()
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="respuestas")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha_creacion"]
>>>>>>> 75e549b (api de taller y foro)
