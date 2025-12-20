"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Configura las señales (triggers) de Django. Escucha el 
                       evento 'post_save' del modelo Anuncio para disparar 
                       automáticamente una tarea asíncrona de notificación 
                       vía Celery/Firebase.
--------------------------------------------------------------------------------
"""

# Importa la señal post_save (se ejecuta después de guardar un registro).
from django.db.models.signals import post_save
# Importa el receptor para conectar funciones a señales.
from django.dispatch import receiver
# Importa el modelo Anuncio.
from .models import Anuncio
# Importa la tarea de Celery para enviar notificaciones.
from .tasks import enviar_notificacion_nuevo_anuncio 

# Decorador que conecta la función 'notificar_nuevo_anuncio' a la señal 'post_save' de 'Anuncio'.
@receiver(post_save, sender=Anuncio)
def notificar_nuevo_anuncio(sender, instance, created, **kwargs):
    """Función que se ejecuta cada vez que se guarda un Anuncio."""
    # Verifica si es una creación (True) y no una edición.
    if created:
        print(f"[Signal] Nuevo Anuncio creado: {instance.titulo}. Enviando a Celery...")
        # Llama a la tarea de Celery de forma asíncrona (.delay) pasando solo el ID.
        # Se pasa el ID y no el objeto completo porque los objetos DB no son serializables para Celery.
        enviar_notificacion_nuevo_anuncio.delay(instance.id)