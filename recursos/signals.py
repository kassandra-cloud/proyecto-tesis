# recursos/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import SolicitudReserva, Recurso
from .tasks import notificar_actualizacion_solicitud, notificar_nuevo_recurso

@receiver(pre_save, sender=SolicitudReserva)
def detectar_cambio_estado(sender, instance, **kwargs):
    """
    Antes de guardar, verificamos si el estado está cambiando.
    """
    if instance.pk: # Si es una edición (no una creación nueva)
        try:
            old_instance = SolicitudReserva.objects.get(pk=instance.pk)
            # Comparamos el estado anterior con el nuevo
            instance._estado_cambio = old_instance.estado != instance.estado
        except SolicitudReserva.DoesNotExist:
            instance._estado_cambio = False
    else:
        instance._estado_cambio = False

@receiver(post_save, sender=SolicitudReserva)
def trigger_notificacion_recurso(sender, instance, created, **kwargs):
    """
    Después de guardar, si hubo cambio de estado a APROBADA o RECHAZADA, notificamos.
    """
    # Verificamos la bandera que pusimos en pre_save
    if hasattr(instance, '_estado_cambio') and instance._estado_cambio:
        
        # 🔹 FILTRO: Solo notificar si la directiva tomó una decisión
        if instance.estado in ['APROBADA', 'RECHAZADA']:
            notificar_actualizacion_solicitud.delay(instance.id)

@receiver(post_save, sender=Recurso)
def trigger_notificacion_nuevo_recurso(sender, instance, created, **kwargs):
    # Solo si es un recurso nuevo
    if created:
        notificar_nuevo_recurso.delay(instance.id)