from django.db.models.signals import post_delete
from django.dispatch import receiver
from foro.models import ArchivoAdjunto
import os
from django.db.models.signals import pre_save
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

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

@receiver(pre_save, sender=User)
def asegurar_email_unico(sender, instance, **kwargs):
    # Verificar si el email viene en la instancia y no está vacío
    if instance.email:
        # Normalizar a minúsculas para evitar 'Correo@test.com' vs 'correo@test.com'
        instance.email = instance.email.lower()
        
        # Buscar si existe otro usuario (excluyendo al actual si es una edición)
        if User.objects.filter(email=instance.email).exclude(pk=instance.pk).exists():
            raise ValidationError(f"El correo {instance.email} ya está asociado a otra cuenta.")