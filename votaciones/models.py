"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Definición de modelos para el sistema de Votaciones. Incluye lógica 
               de integridad de voto mediante hash SHA-256 y logs de auditoría.
--------------------------------------------------------------------------------
"""
import hashlib  # Para hashing criptográfico
from django.db import models
from django.conf import settings
from django.utils import timezone


# 1. Modelo Votación
class Votacion(models.Model):
    pregunta = models.CharField(max_length=255, verbose_name="Pregunta")
    fecha_cierre = models.DateTimeField(verbose_name="Fecha de cierre", db_index=True)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Creada por"
    )
    activa = models.BooleanField(default=True, db_index=True)

    def esta_abierta(self) -> bool:
        """True si está activa y aún no llega la fecha de cierre."""
        return self.activa and self.fecha_cierre > timezone.now()

    def __str__(self) -> str:
        return self.pregunta

    class Meta:
        ordering = ["-fecha_cierre", "-id"]
        indexes = [
            models.Index(fields=["activa", "fecha_cierre"]),
        ]
        verbose_name = "Votación"
        verbose_name_plural = "Votaciones"


# 2. Modelo Opción
class Opcion(models.Model):
    votacion = models.ForeignKey(
        Votacion,
        related_name="opciones",
        on_delete=models.CASCADE,
        verbose_name="Votación"
    )
    texto = models.CharField(max_length=150, verbose_name="Texto de la opción")

    def __str__(self):
        return self.texto

    class Meta:
        verbose_name = "Opción"
        verbose_name_plural = "Opciones"


# 3. Modelo Voto (con integridad)
class Voto(models.Model):
    opcion = models.ForeignKey(
        Opcion,
        related_name="votos",
        on_delete=models.CASCADE,
        verbose_name="Opción"
    )
    votante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="Vecino"
    )

    # Hash que permite verificar integridad del voto
    hash_voto = models.CharField(
        max_length=64,
        blank=True,
        editable=False,
        verbose_name="Hash del voto"
    )

    class Meta:
        unique_together = [["opcion", "votante"]]  # Evita duplicados a nivel de BD
        verbose_name = "Voto"
        verbose_name_plural = "Votos"

    def save(self, *args, **kwargs):
        """
        Genera automáticamente un hash SHA-256 combinando:
        - ID del votante
        - ID de la opción
        - SECRET_KEY del proyecto
        Esto permite detectar alteraciones post-voto.
        """
        data_string = f"{self.votante.id}-{self.opcion.id}-{settings.SECRET_KEY}"
        self.hash_voto = hashlib.sha256(data_string.encode()).hexdigest()
        super().save(*args, **kwargs)


# 4. Modelo Log de Intentos (Auditoría / BI)
class LogIntentoVoto(models.Model):
    """
    Registra cada intento de voto (exitoso o fallido) para métricas de seguridad y uso.
    """
    ORIGENES = (
        ("APP_MOVIL", "App móvil"),
        ("WEB", "Sitio web"),
    )

    votacion = models.ForeignKey(
        Votacion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs_intentos",
        verbose_name="Votación"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs_intentos_voto",
        verbose_name="Vecino"
    )
    fue_exitoso = models.BooleanField(default=False, verbose_name="¿Fue exitoso?")
    motivo_fallo = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Motivo del fallo"
    )
    origen = models.CharField(
        max_length=20,
        choices=ORIGENES,
        default="APP_MOVIL",
        verbose_name="Origen"
    )
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "Log de intento de voto"
        verbose_name_plural = "Logs de intentos de voto"

    def __str__(self):
        estado = "OK" if self.fue_exitoso else "FALLO"
        return f"[{estado}] {self.usuario} en votación {self.votacion_id} - {self.motivo_fallo}"