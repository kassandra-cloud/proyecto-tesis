from django.db import models
from django.conf import settings

class Anuncio(models.Model):
    titulo = models.CharField(max_length=200, verbose_name="Título del Anuncio")
    contenido = models.TextField(verbose_name="Contenido del Mensaje")
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name="anuncios_creados"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo

    class Meta:
        ordering = ['-fecha_creacion'] # Ordena del más nuevo al más viejo
        verbose_name = "Anuncio"
        verbose_name_plural = "Anuncios"