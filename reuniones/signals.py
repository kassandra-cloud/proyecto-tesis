"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Gestión de señales para disparar notificaciones asíncronas 
               basadas en cambios de estado de Reuniones y Actas.
--------------------------------------------------------------------------------
"""
from django.db import transaction
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Reunion, EstadoReunion, Acta
from .tasks import (
    enviar_notificacion_nueva_reunion, 
    enviar_notificacion_reunion_finalizada,
    enviar_notificacion_reunion_iniciada,
    enviar_notificacion_acta_aprobada
)

# --- REUNIONES ---

@receiver(pre_save, sender=Reunion) # Captura estado previo
def guardar_estado_anterior_reunion(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = Reunion.objects.get(pk=instance.pk)
            instance._estado_anterior = old.estado
        except Reunion.DoesNotExist:
            instance._estado_anterior = None
    else:
        instance._estado_anterior = None

@receiver(post_save, sender=Reunion) # Dispara notificaciones tras guardar
def gestionar_notificaciones_reunion(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(lambda: enviar_notificacion_nueva_reunion.delay(instance.pk))
    else:
        prev = getattr(instance, "_estado_anterior", None)
        curr = instance.estado

        if prev != EstadoReunion.REALIZADA and curr == EstadoReunion.REALIZADA:
            transaction.on_commit(lambda: enviar_notificacion_reunion_finalizada.delay(instance.pk))

        if prev != EstadoReunion.EN_CURSO and curr == EstadoReunion.EN_CURSO:
            transaction.on_commit(lambda: enviar_notificacion_reunion_iniciada.delay(instance.pk))

# --- ACTAS ---

@receiver(pre_save, sender=Acta) # Captura estado previo de aprobación
def guardar_estado_aprobacion_anterior(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = Acta.objects.get(pk=instance.pk)
            instance._aprobada_anterior = old.aprobada
        except Acta.DoesNotExist:
            instance._aprobada_anterior = False
    else:
        instance._aprobada_anterior = False

@receiver(post_save, sender=Acta) # Dispara notificación si se aprueba
def gestionar_notificaciones_acta(sender, instance, created, **kwargs):
    was_approved = getattr(instance, "_aprobada_anterior", False)
    is_approved = instance.aprobada

    # Notificar solo si pasa de No Aprobada -> Aprobada
    if not was_approved and is_approved:
        # Usamos .pk aquí, lo cual es seguro
        transaction.on_commit(lambda: enviar_notificacion_acta_aprobada.delay(instance.pk))