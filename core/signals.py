"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Define señales (triggers) del sistema.
                       1. Elimina archivos físicos cuando se borra un adjunto del Foro.
                       2. Valida que el email sea único al guardar un Usuario (pre-save).
--------------------------------------------------------------------------------
"""

# Importa señal post-eliminación.
from django.db.models.signals import post_delete
# Importa decorador receptor.
from django.dispatch import receiver
# Importa modelo ArchivoAdjunto (de app foro).
from foro.models import ArchivoAdjunto
# Importa módulo os para operaciones de sistema de archivos.
import os
# Importa señal pre-guardado.
from django.db.models.signals import pre_save
# Importa modelo User.
from django.contrib.auth.models import User
# Importa excepción de validación.
from django.core.exceptions import ValidationError

# Señal: Al borrar un registro de ArchivoAdjunto...
@receiver(post_delete, sender=ArchivoAdjunto)
def eliminar_archivo_adjunto(sender, instance, **kwargs):
    """
    Elimina el archivo físico del disco (media/archivos/...)
    cuando se elimina un objeto ArchivoAdjunto de la base de datos.
    """
    # 'instance' es el objeto ArchivoAdjunto que se acaba de borrar.
    if instance.archivo:
        # Comprueba si el archivo físico existe en la ruta.
        if os.path.isfile(instance.archivo.path):
            # Lo elimina del disco para ahorrar espacio.
            os.remove(instance.archivo.path)

# Señal: Antes de guardar un usuario...
@receiver(pre_save, sender=User)
def asegurar_email_unico(sender, instance, **kwargs):
    # Verificar si el email viene en la instancia y no está vacío.
    if instance.email:
        # Normalizar a minúsculas para evitar duplicados por mayúsculas (Correo vs correo).
        instance.email = instance.email.lower()
        
        # Busca si existe otro usuario con ese email (excluyendo al usuario actual si se está editando).
        if User.objects.filter(email=instance.email).exclude(pk=instance.pk).exists():
            # Impide el guardado lanzando un error.
            raise ValidationError(f"El correo {instance.email} ya está asociado a otra cuenta.")