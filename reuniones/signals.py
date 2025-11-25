from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Reunion, EstadoReunion
from .tasks import (
    enviar_notificacion_nueva_reunion, 
    enviar_notificacion_reunion_finalizada,
    enviar_notificacion_reunion_iniciada  # <--- Importar nueva tarea
)

@receiver(pre_save, sender=Reunion)
def guardar_estado_anterior(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = Reunion.objects.get(pk=instance.pk)
            instance._estado_anterior = old_instance.estado
        except Reunion.DoesNotExist:
            instance._estado_anterior = None
    else:
        instance._estado_anterior = None

@receiver(post_save, sender=Reunion)
def gestionar_notificaciones_reunion(sender, instance, created, **kwargs):
    # 1. Nueva Reunión
    if created:
        print(f"[Signal] Nueva Reunión creada: {instance.id}")
        enviar_notificacion_nueva_reunion.delay(instance.id)
    
    else:
        estado_anterior = getattr(instance, "_estado_anterior", None)
        
        # 2. Reunión Finalizada (Cambio a REALIZADA)
        if estado_anterior != EstadoReunion.REALIZADA and instance.estado == EstadoReunion.REALIZADA:
            print(f"[Signal] Reunión finalizada: {instance.id}")
            enviar_notificacion_reunion_finalizada.delay(instance.id)

        # 3. Reunión Iniciada (Cambio a EN_CURSO)
        if estado_anterior != EstadoReunion.EN_CURSO and instance.estado == EstadoReunion.EN_CURSO:
            print(f"[Signal] Reunión iniciada: {instance.id}")
            enviar_notificacion_reunion_iniciada.delay(instance.id)