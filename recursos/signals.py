"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Configuración de Señales (Signals) para detectar cambios en el 
               estado de las solicitudes y gatillar notificaciones asíncronas.
--------------------------------------------------------------------------------
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import SolicitudReserva, Recurso
from .tasks import notificar_actualizacion_solicitud, notificar_nuevo_recurso

@receiver(pre_save, sender=SolicitudReserva)
def detectar_cambio_estado(sender, instance, **kwargs):
    """
    Antes de guardar, verificamos si el estado está cambiando respecto al valor en BD.
    Se guarda una bandera temporal `_estado_cambio` en la instancia.
    """
    if instance.pk: # Si es una edición
        try:
            old_instance = SolicitudReserva.objects.get(pk=instance.pk)
            instance._estado_cambio = old_instance.estado != instance.estado
        except SolicitudReserva.DoesNotExist:
            instance._estado_cambio = False
    else:
        instance._estado_cambio = False

@receiver(post_save, sender=SolicitudReserva)
def trigger_notificacion_recurso(sender, instance, created, **kwargs):
    """
    Después de guardar, si hubo cambio de estado relevante (Aprobada/Rechazada), 
    se dispara la tarea de notificación.
    """
    if hasattr(instance, '_estado_cambio') and instance._estado_cambio:
        if instance.estado in ['APROBADA', 'RECHAZADA']:
            notificar_actualizacion_solicitud.delay(instance.id)

@receiver(post_save, sender=Recurso)
def trigger_notificacion_nuevo_recurso(sender, instance, created, **kwargs):
    """
    Notifica a todos cuando se crea un nuevo recurso en el sistema.
    """
    if created:
        notificar_nuevo_recurso.delay(instance.id)