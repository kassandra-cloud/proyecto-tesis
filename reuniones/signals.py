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

@receiver(pre_save, sender=Reunion)
def guardar_estado_anterior_reunion(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = Reunion.objects.get(pk=instance.pk)
            instance._estado_anterior = old.estado
        except Reunion.DoesNotExist:
            instance._estado_anterior = None
    else:
        instance._estado_anterior = None

@receiver(post_save, sender=Reunion)
def gestionar_notificaciones_reunion(sender, instance, created, **kwargs):
    # 1. Nueva Reunión
    if created:
        transaction.on_commit(lambda: enviar_notificacion_nueva_reunion.delay(instance.id))
    else:
        prev = getattr(instance, "_estado_anterior", None)
        curr = instance.estado

        # 2. Reunión Finalizada
        if prev != EstadoReunion.REALIZADA and curr == EstadoReunion.REALIZADA:
            transaction.on_commit(lambda: enviar_notificacion_reunion_finalizada.delay(instance.id))

        # 3. Reunión Iniciada
        if prev != EstadoReunion.EN_CURSO and curr == EstadoReunion.EN_CURSO:
            transaction.on_commit(lambda: enviar_notificacion_reunion_iniciada.delay(instance.id))

# --- ACTAS ---

@receiver(pre_save, sender=Acta)
def guardar_estado_aprobacion_anterior(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = Acta.objects.get(pk=instance.pk)
            instance._aprobada_anterior = old.aprobada
        except Acta.DoesNotExist:
            instance._aprobada_anterior = False
    else:
        instance._aprobada_anterior = False

@receiver(post_save, sender=Acta)
def gestionar_notificaciones_acta(sender, instance, created, **kwargs):
    was_approved = getattr(instance, "_aprobada_anterior", False)
    is_approved = instance.aprobada

    # Notificar solo si pasa de No Aprobada -> Aprobada
    if not was_approved and is_approved:
        transaction.on_commit(lambda: enviar_notificacion_acta_aprobada.delay(instance.pk))