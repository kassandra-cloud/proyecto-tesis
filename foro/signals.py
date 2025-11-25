# foro/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Publicacion, Comentario
from .tasks import notificar_nueva_publicacion, notificar_nuevo_comentario

@receiver(post_save, sender=Publicacion)
def trigger_notificacion_publicacion(sender, instance, created, **kwargs):
    if created and instance.visible: # Solo si es nueva y visible
        notificar_nueva_publicacion.delay(instance.id)

@receiver(post_save, sender=Comentario)
def trigger_notificacion_comentario(sender, instance, created, **kwargs):
    if created and instance.visible:
        notificar_nuevo_comentario.delay(instance.id)