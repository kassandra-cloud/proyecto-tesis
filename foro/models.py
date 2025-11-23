from django.db import models
from django.contrib.auth.models import User
import os
from django.conf import settings


class Publicacion(models.Model):
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    contenido = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    visible = models.BooleanField(default=True, db_index=True)
    eliminado = models.BooleanField(default=False)
    def __str__(self):
        return f'Publicación de {self.autor.username}'

class ArchivoAdjunto(models.Model):
    publicacion = models.ForeignKey(
        Publicacion,
        on_delete=models.CASCADE,
        related_name='adjuntos'
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='adjuntos_foro'
    )
    archivo = models.FileField(upload_to='archivos/')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # 🔹 NUEVO: para saber si debe mostrarse como "mensaje" (app) o adjunto normal (web)
    es_mensaje = models.BooleanField(
        default=False,
        help_text="Si está marcado, se mostrará en la sección de comentarios."
    )

    def __str__(self):
        return self.archivo.name

    @property
    def tipo_archivo(self):
        ext = os.path.splitext(self.archivo.name)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif']:
            return 'imagen'
        elif ext in ['.mp3', '.wav', '.ogg', '.webm', '.m4a']:
            return 'audio'
        elif ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
            return 'video'
        else:
            return 'otro'

class Comentario(models.Model):
    publicacion = models.ForeignKey("Publicacion", on_delete=models.CASCADE, related_name="comentarios")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    contenido = models.TextField()
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="respuestas")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    visible = models.BooleanField(default=True, db_index=True)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='comentarios_liked', blank=True)
    class Meta:
        ordering = ["fecha_creacion"]