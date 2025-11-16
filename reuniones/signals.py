# proyecto-tesis/reuniones/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Reunion # Solo necesitamos importar el modelo
from .tasks import enviar_notificacion_nueva_reunion # Importamos la tarea Celery

@receiver(post_save, sender=Reunion)
def notificar_nueva_reunion(sender, instance, created, **kwargs):
    """
    Dispara la tarea Celery para enviar notificaciones de FCM 
    cuando se crea una nueva Reunion.
    """
    # Solo si el objeto Reunion se acaba de crear (importante: `created=True`)
    if created:
        print(f"[Signal] Nueva Reunión creada: {instance.id}. Disparando notificación FCM.")
        # Llamamos a la tarea asíncrona de Celery
        enviar_notificacion_nueva_reunion.delay(instance.id)