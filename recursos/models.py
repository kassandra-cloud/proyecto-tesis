from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q

class Recurso(models.Model):
    """
    Representa un recurso comunitario físico que se puede reservar.
    Ej: "Sede Comunitaria", "Proyector", "Parrilla"
    """
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre del Recurso")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    
    # Campo para que la directiva decida si el recurso está activo o no
    disponible = models.BooleanField(default=True, help_text="Marcar si el recurso está disponible para ser reservado.")

    def __str__(self):
        return self.nombre
        
    class Meta:
        verbose_name = "Recurso"
        verbose_name_plural = "Recursos"

class Reserva(models.Model):
    """
    Representa la solicitud de reserva de un Recurso por parte de un Vecino.
    """
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente de Aprobación"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"
        CANCELADA = "CANCELADA", "Cancelada por Vecino"

    recurso = models.ForeignKey(Recurso, on_delete=models.CASCADE, related_name="reservas")
    vecino = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservas_hechas")
    
    fecha_inicio = models.DateTimeField(verbose_name="Inicio de la reserva")
    fecha_fin = models.DateTimeField(verbose_name="Fin de la reserva")
    
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    
    motivo = models.TextField(verbose_name="Motivo de la reserva")
    
    # Opcional: un campo para que la directiva deje notas (ej. motivo del rechazo)
    # notas_directiva = models.TextField(blank=True, verbose_name="Notas de la Directiva")

    creada_el = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.recurso.nombre} - {self.vecino.username} ({self.get_estado_display()})"

    class Meta:
        ordering = ['fecha_inicio']
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"

    def clean(self):
        # 1. Validar que la fecha de fin sea posterior a la de inicio
        if self.fecha_fin <= self.fecha_inicio:
            raise ValidationError("La fecha de finalización debe ser posterior a la fecha de inicio.")
        
        # 2. Validar que la fecha de inicio no sea en el pasado (solo al crear)
        if not self.pk and self.fecha_inicio < timezone.now():
             raise ValidationError("No se pueden crear reservas en el pasado.")

        # 3. Validar superposición de reservas APROBADAS o PENDIENTES
        # (No queremos dos reservas pendientes para el mismo horario)
        reservas_en_conflicto = Reserva.objects.filter(
            recurso=self.recurso,
            estado__in=[self.Estado.APROBADA, self.Estado.PENDIENTE]
        ).filter(
            # (StartA < EndB) and (EndA > StartB)
            fecha_inicio__lt=self.fecha_fin,
            fecha_fin__gt=self.fecha_inicio
        ).exclude(pk=self.pk) # Excluirse a sí mismo si se está editando

        if reservas_en_conflicto.exists():
            raise ValidationError("El recurso ya tiene una solicitud aprobada o pendiente en este horario.")