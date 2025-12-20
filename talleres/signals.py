"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Gestión de señales (signals) para detectar creación o cancelación 
               de talleres y disparar las tareas de notificación correspondientes.
--------------------------------------------------------------------------------
"""
# talleres/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Taller
from .tasks import notificar_nuevo_taller, notificar_cancelacion_taller

@receiver(pre_save, sender=Taller)
def detectar_cambios_taller(sender, instance, **kwargs):
    """
    Antes de guardar, verificamos si se está cancelando.
    Compara el estado nuevo con el estado anterior en base de datos.
    """
    if instance.pk: # Es una edición
        try:
            old_instance = Taller.objects.get(pk=instance.pk)
            # Detectar si cambió de NO cancelado a CANCELADO
            instance._se_cancelo_ahora = (old_instance.estado != Taller.Estado.CANCELADO) and (instance.estado == Taller.Estado.CANCELADO)
        except Taller.DoesNotExist:
            instance._se_cancelo_ahora = False
    else:
        instance._se_cancelo_ahora = False

@receiver(post_save, sender=Taller)
def trigger_notificacion_taller(sender, instance, created, **kwargs):
    # 1. Caso Nuevo Taller: Si se crea y está programado, notificar.
    if created and instance.estado == Taller.Estado.PROGRAMADO:
        notificar_nuevo_taller.delay(instance.id)
    
    # 2. Caso Taller Cancelado: Si se detectó cancelación en pre_save, notificar.
    elif hasattr(instance, '_se_cancelo_ahora') and instance._se_cancelo_ahora:
        notificar_cancelacion_taller.delay(instance.id)