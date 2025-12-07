import hashlib
from django.db import models
from django.conf import settings
from django.utils import timezone


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

    # Hash que permite verificar integridad y unicidad fuerte del voto
    hash_voto = models.CharField(
        max_length=64,
        blank=True,
        editable=False,
        verbose_name="Hash del voto"
    )

    class Meta:
        unique_together = [["opcion", "votante"]]
        verbose_name = "Voto"
        verbose_name_plural = "Votos"

    def save(self, *args, **kwargs):
        """
        Genera automáticamente un hash SHA-256 combinando:
        - ID del votante
        - ID de la opción
        - SECRET_KEY del proyecto

        Esto NO hace anónimo el voto, pero permite:
        - detectar alteraciones
        - justificar en la tesis un mecanismo básico de integridad.
        """
        data_string = f"{self.votante.id}-{self.opcion.id}-{settings.SECRET_KEY}"
        self.hash_voto = hashlib.sha256(data_string.encode()).hexdigest()
        super().save(*args, **kwargs)


class LogIntentoVoto(models.Model):
    """
    Registra cada intento de voto (especialmente desde la app móvil),
    para poder calcular el KPI de 'fallos en votaciones' en el módulo BI.
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
