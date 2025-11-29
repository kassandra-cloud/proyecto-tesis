# proyecto-tesis/foro/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Publicacion, Comentario
# from .tasks import notificar_nueva_publicacion, notificar_nuevo_comentario  <-- COMENTA ESTA IMPORTACIÓN SI DA ERROR LUEGO

@receiver(post_save, sender=Publicacion)
def trigger_notificacion_publicacion(sender, instance, created, **kwargs):
    """
    Señal desactivada temporalmente para evitar spam de notificaciones.
    """
    if created:
        pass 
        # COMENTA LAS LÍNEAS DE ABAJO:
        # print(f" Nueva publicación creada: {instance.id}. Encolando notificación...")
        # notificar_nueva_publicacion.delay(instance.id)

@receiver(post_save, sender=Comentario)
def trigger_notificacion_comentario(sender, instance, created, **kwargs):
    """
    Señal desactivada para comentarios.
    """
    if created:
        pass
        # COMENTA LAS LÍNEAS DE ABAJO:
        # print(f" Nuevo comentario en post {instance.publicacion.id}. Encolando notificación...")
        # notificar_nuevo_comentario.delay(instance.id)