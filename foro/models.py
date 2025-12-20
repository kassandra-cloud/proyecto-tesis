"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Este archivo define la estructura de datos para la aplicación 'foro'.
               Incluye las entidades principales como Publicacion, Comentario y 
               ArchivoAdjunto. Soporta eliminación lógica, likes y clasificación 
               automática de tipos de archivo.
--------------------------------------------------------------------------------
"""
from django.db import models
from django.contrib.auth.models import User
import os
from django.conf import settings
from django.contrib import admin 


# 1. MODELO PUBLICACION (Post Principal del Foro)
class Publicacion(models.Model):
    # Relación con el usuario que creó la publicación (CASCADE: si el usuario se borra, se borran sus posts)
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    # Contenido principal del post
    contenido = models.TextField()
    # Fecha y hora de creación (se establece automáticamente al crear)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    # Campo para eliminación lógica o moderación (True=visible, False=oculto)
    visible = models.BooleanField(default=True, db_index=True)
    # Campo para indicar si la publicación fue marcada para eliminación
    eliminado = models.BooleanField(default=False)
    def __str__(self):
        # Representación legible del objeto
        return f'Publicación de {self.autor.username}'


# 2. MODELO ARCHIVOADJUNTO (Archivos multimedia o documentos)
class ArchivoAdjunto(models.Model):
    # Relación con la Publicacion a la que pertenece el adjunto
    publicacion = models.ForeignKey(
        Publicacion,
        on_delete=models.CASCADE,
        related_name='adjuntos' # Permite acceder a los adjuntos desde una Publicacion: `publicacion.adjuntos.all()`
    )
    # Relación con el usuario que subió el archivo
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='adjuntos_foro'
    )
    # Campo para el archivo: se guarda en 'archivos/' dentro del MEDIA_ROOT
    archivo = models.ImageField(upload_to='archivos/') 
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # Indicador de contexto: si es True, se considera parte de la conversación/chat (usado en las Vistas Web y API)
    es_mensaje = models.BooleanField(
        default=False,
        help_text="Si está marcado, se mostrará en la sección de comentarios."
    )
    # Descripción opcional del archivo (ej: el texto que acompaña a una imagen en un chat)
    descripcion = models.TextField(null=True, blank=True)
    # Relación Many-to-Many para el sistema de Likes (quién ha dado like a este adjunto)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='adjuntos_liked', blank=True)
    
    def __str__(self):
        return self.archivo.name

    # Propiedad calculada: determina el tipo de archivo (imagen, audio, video, etc.) basado en su extensión
    @property
    def tipo_archivo(self):
        ext = os.path.splitext(self.archivo.name)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif']:
            return 'imagen'
        elif ext in ['.mp3', '.wav', '.ogg', '.webm', '.m4a']:
            return 'audio'
        elif ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
            return 'video'
        elif ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']:
            return 'documento'
        else:
            return 'otro'

    # Propiedad para mostrar el tipo de archivo de forma amigable en el Admin de Django
    @admin.display(description="Tipo de archivo")
    def tipo_archivo_admin(self):
        return self.tipo_archivo
        
# 3. MODELO COMENTARIO (Respuestas a Publicaciones y a otros Comentarios)
class Comentario(models.Model):
    publicacion = models.ForeignKey("Publicacion", on_delete=models.CASCADE, related_name="comentarios")
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    contenido = models.TextField()
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="respuestas")
    visible = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    reply_to_adjunto = models.ForeignKey(
        "ArchivoAdjunto",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="respuestas",
    )

    # Agregado soporte de likes para comentarios
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="comentarios_liked",
        blank=True
    )