# anuncios/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Anuncio
from .tasks import enviar_notificacion_nuevo_anuncio # Importamos la tarea nueva

@receiver(post_save, sender=Anuncio)
def notificar_nuevo_anuncio(sender, instance, created, **kwargs):
    if created:
        print(f"[Signal] Nuevo Anuncio creado: {instance.titulo}. Enviando a Celery...")
        # Llamada asíncrona a Celery
        enviar_notificacion_nuevo_anuncio.delay(instance.id)