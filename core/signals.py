from django.db.models.signals import post_delete
from django.dispatch import receiver
from foro.models import ArchivoAdjunto
import os

@receiver(post_delete, sender=ArchivoAdjunto)
def eliminar_archivo_adjunto(sender, instance, **kwargs):
    """
    Elimina el archivo físico del disco (media/archivos/...)
    cuando se elimina un objeto ArchivoAdjunto de la base de datos.
    """
    # 'instance' es el objeto ArchivoAdjunto que se acaba de borrar
    if instance.archivo:
        # Comprueba si el archivo existe y lo borra
        if os.path.isfile(instance.archivo.path):
            os.remove(instance.archivo.path)