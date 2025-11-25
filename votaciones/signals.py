# votaciones/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Votacion
from .tasks import notificar_nueva_votacion

@receiver(post_save, sender=Votacion)
def trigger_notificacion_votacion(sender, instance, created, **kwargs):
    # Solo notificamos si es una creación Y la votación está marcada como activa
    if created and instance.activa:
        notificar_nueva_votacion.delay(instance.id)