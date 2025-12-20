"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Este archivo define el modelo de datos 'Anuncio'. 
                       Representa los comunicados oficiales que la directiva 
                       envía a los vecinos, almacenando título, contenido, 
                       autor y fecha.
--------------------------------------------------------------------------------
"""

# Importa el módulo models de Django para definir estructuras de base de datos.
from django.db import models
# Importa settings para hacer referencia segura al modelo de Usuario configurado.
from django.conf import settings

class Anuncio(models.Model):
    """Modelo que representa una noticia o comunicado para la comunidad."""
    
    # Campo de texto corto para el título del anuncio (máx 200 caracteres).
    titulo = models.CharField(max_length=200, verbose_name="Título del Anuncio")
    
    # Campo de texto largo para el cuerpo del mensaje.
    contenido = models.TextField(verbose_name="Contenido del Mensaje")
    
    # Relación Clave Foránea con el usuario (autor). 
    # Si el usuario se borra, el autor queda como NULL (SET_NULL) para no borrar el anuncio.
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name="anuncios_creados" # Permite acceder a los anuncios desde el objeto usuario.
    )
    
    # Fecha y hora de creación automática al momento de guardar el registro por primera vez.
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Devuelve el título del anuncio al representarlo como texto."""
        return self.titulo

    class Meta:
        # Configuración del modelo: ordena los resultados por fecha de creación descendente (nuevo primero).
        ordering = ['-fecha_creacion'] 
        # Nombre singular para el panel de administración.
        verbose_name = "Anuncio"
        # Nombre plural para el panel de administración.
        verbose_name_plural = "Anuncios"