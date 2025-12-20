"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Definición de la estructura de datos. 
               - Recurso: Elemento reservable (sala, proyector, etc.).
               - SolicitudReserva: Petición con flujo de estados (Pendiente, Aprobada...).
               - Reserva: Modelo histórico/espejo para compatibilidad.
--------------------------------------------------------------------------------
"""
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q, F, UniqueConstraint

# 1. MODELO RECURSO
class Recurso(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre del Recurso")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    
    # Control maestro de disponibilidad (activar/desactivar recurso globalmente)
    disponible = models.BooleanField(default=True, help_text="Marcar si el recurso está disponible para ser reservado.")

    def __str__(self):
        return self.nombre
        
    class Meta:
        verbose_name = "Recurso"
        verbose_name_plural = "Recursos"

# 2. MODELO RESERVA (Modelo Legacy/Espejo para compatibilidad lógica)
class Reserva(models.Model):
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
    creada_el = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.recurso.nombre} - {self.vecino.username} ({self.get_estado_display()})"

    class Meta:
        ordering = ['fecha_inicio']
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"

    def clean(self):
        # Validaciones de lógica de negocio para reservas directas
        if self.fecha_fin <= self.fecha_inicio:
            raise ValidationError("La fecha de finalización debe ser posterior a la fecha de inicio.")
        
        if not self.pk and self.fecha_inicio < timezone.now():
             raise ValidationError("No se pueden crear reservas en el pasado.")

        # Validación de superposición de horarios
        reservas_en_conflicto = Reserva.objects.filter(
            recurso=self.recurso,
            estado__in=[self.Estado.APROBADA, self.Estado.PENDIENTE]
        ).filter(
            fecha_inicio__lt=self.fecha_fin,
            fecha_fin__gt=self.fecha_inicio
        ).exclude(pk=self.pk)

        if reservas_en_conflicto.exists():
            raise ValidationError("El recurso ya tiene una solicitud aprobada o pendiente en este horario.")

# 3. MODELO SOLICITUD RESERVA (Modelo principal de gestión)
class SolicitudReserva(models.Model):
    ESTADOS = [
        ("PENDIENTE", "Pendiente"),
        ("APROBADA", "Aprobada"),
        ("RECHAZADA", "Rechazada"),
        ("CANCELADA", "Cancelada por Vecino"),
    ]

    recurso = models.ForeignKey("Recurso", on_delete=models.CASCADE, related_name="solicitudes")
    solicitante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="solicitudes_recursos")
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    motivo = models.TextField(blank=True)
    estado = models.CharField(max_length=10, choices=ESTADOS, default="PENDIENTE", db_index=True)
    creado_el = models.DateTimeField(auto_now_add=True)
    actualizado_el = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado_el"]
        indexes = [
            models.Index(fields=["recurso", "fecha_inicio", "fecha_fin"]),
            models.Index(fields=["estado"]),
            models.Index(fields=["solicitante", "recurso"]),
        ]
        constraints = [
            # Restricción SQL: fecha fin debe ser mayor o igual a inicio
            models.CheckConstraint(
                check=Q(fecha_fin__gte=F("fecha_inicio")),
                name="solicitud_fin_gte_inicio",
            ),
            # Restricción SQL: Solo una solicitud pendiente por usuario y recurso a la vez
            UniqueConstraint(
                fields=["solicitante", "recurso"],
                condition=Q(estado="PENDIENTE"),
                name="uniq_pendiente_por_usuario_y_recurso",
            ),
        ]

    def __str__(self):
        return f"{self.recurso} · {self.solicitante} · {self.estado} ({self.fecha_inicio}→{self.fecha_fin})"

    def clean(self):
        super().clean()

        # Validación 1: Rango de fechas lógico
        if self.fecha_fin and self.fecha_inicio and self.fecha_fin < self.fecha_inicio:
            raise ValidationError("La fecha de fin no puede ser menor a la fecha de inicio.")

        # Validación 2: Impedir solapamiento con reservas YA APROBADAS
        if self.estado == "APROBADA":
            solapadas = (
                SolicitudReserva.objects
                .filter(recurso=self.recurso, estado="APROBADA")
                .exclude(pk=self.pk)
                .filter(
                    fecha_inicio__lte=self.fecha_fin,
                    fecha_fin__gte=self.fecha_inicio,
                )
                .exists()
            )
            if solapadas:
                raise ValidationError("Ya existe una reserva APROBADA que se solapa en esas fechas para este recurso.")

        # Validación 3: Impedir que el mismo usuario tenga múltiples solicitudes solapadas activas
        activa_solapada = (
            SolicitudReserva.objects
            .filter(
                solicitante=self.solicitante,
                recurso=self.recurso,
                estado__in=["PENDIENTE", "APROBADA"],
            )
            .exclude(pk=self.pk)
            .filter(
                fecha_inicio__lt=self.fecha_fin,
                fecha_fin__gt=self.fecha_inicio
            )
            .exists()
        )

        if activa_solapada:
            raise ValidationError("Ya tienes una solicitud PENDIENTE o APROBADA que se solapa con estas fechas para este recurso.")

    def save(self, *args, **kwargs):
        self.full_clean()  # Ejecuta las validaciones clean() antes de guardar
        return super().save(*args, **kwargs)

    @property
    def rango(self) -> str:
        return f"{self.fecha_inicio} – {self.fecha_fin}"