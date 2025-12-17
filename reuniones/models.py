# reuniones/models.py
from django.db import models
from django.conf import settings


class EstadoReunion(models.TextChoices):
    PROGRAMADA = 'PROGRAMADA', 'Programada'
    EN_CURSO   = 'EN_CURSO',   'En Curso'
    REALIZADA  = 'REALIZADA',  'Realizada'
    CANCELADA  = 'CANCELADA',  'Cancelada'


class Reunion(models.Model):
    TIPO_REUNION = [
        ("Ordinaria", "Ordinaria"),
        ("Extraordinaria", "Extraordinaria"),
    ]

    fecha = models.DateTimeField(verbose_name="Fecha y Hora", db_index=True)
    tipo = models.CharField(max_length=20, choices=TIPO_REUNION, default="Ordinaria", db_index=True)
    titulo = models.CharField(max_length=200, verbose_name="Título")
    tabla = models.TextField(verbose_name="Tabla de contenidos")

    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reuniones_creadas"
    )
    creada_el = models.DateTimeField(auto_now_add=True)

    estado = models.CharField(
        max_length=20,
        choices=EstadoReunion.choices,
        default=EstadoReunion.PROGRAMADA,
        db_index=True,
        verbose_name="Estado"
    )

    class Meta:
        indexes = [
            models.Index(fields=["estado", "fecha"]),
            models.Index(fields=["fecha"]),
        ]

    def __str__(self):
        return f"{self.titulo} - {self.fecha.strftime('%d/%m/%Y')}"


class Acta(models.Model):
    ESTADO_NO_SUBIDO   = "NO_SUBIDO"
    ESTADO_PENDIENTE   = "PENDIENTE"
    ESTADO_PROCESANDO  = "PROCESANDO"
    ESTADO_COMPLETADO  = "COMPLETADO"
    ESTADO_ERROR       = "ERROR"

    ESTADO_TRANSCRIPCION_CHOICES = [
        (ESTADO_NO_SUBIDO, "No Subido"),
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_PROCESANDO, "Procesando"),
        (ESTADO_COMPLETADO, "Completado"),
        (ESTADO_ERROR, "Error"),
    ]

    reunion = models.OneToOneField(
        Reunion,
        on_delete=models.CASCADE,
        related_name="acta",
        primary_key=True
    )

    contenido = models.TextField(blank=True, default="Borrador del acta...")

    aprobada = models.BooleanField(default=False, db_index=True)
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="actas_aprobadas"
    )
    aprobado_en = models.DateTimeField(null=True, blank=True)

    archivo_audio = models.FileField(
        upload_to="audios_reuniones/",
        null=True,
        blank=True
    )

    estado_transcripcion = models.CharField(
        max_length=20,
        choices=ESTADO_TRANSCRIPCION_CHOICES,
        default=ESTADO_NO_SUBIDO,
        db_index=True
    )

    calificacion_precision = models.IntegerField(default=0)

    def __str__(self):
        return f"Acta de {self.reunion.titulo}"


class Asistencia(models.Model):
    reunion = models.ForeignKey(Reunion, on_delete=models.CASCADE, related_name="asistentes", db_index=True)
    vecino = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="asistencias", db_index=True)
    presente = models.BooleanField(default=False, db_index=True)

    class Meta:
        unique_together = ('reunion', 'vecino')
        indexes = [
            models.Index(fields=["reunion", "presente"]),
            models.Index(fields=["vecino", "presente"]),
        ]

    def __str__(self):
        estado = "Presente" if self.presente else "Ausente"
        return f"{self.vecino.username} - {self.reunion.titulo} ({estado})"


class ActaEmailLog(models.Model):
    acta = models.ForeignKey("Acta", on_delete=models.CASCADE, related_name="emails_enviados")
    destinatarios = models.TextField()
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    fecha_envio = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Email de acta {self.acta_id} enviado a {self.destinatarios[:50]}..."


class LogConsultaActa(models.Model):
    acta = models.ForeignKey(Acta, on_delete=models.CASCADE, related_name="consultas", db_index=True)
    vecino = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="consultas_de_actas", db_index=True)
    fecha_consulta = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Log de Consulta de Acta"
        verbose_name_plural = "Logs de Consultas de Actas"
        indexes = [
            models.Index(fields=["acta", "fecha_consulta"]),
            models.Index(fields=["vecino", "fecha_consulta"]),
        ]

    def __str__(self):
        return f"{self.vecino.username} consultó {self.acta.reunion.titulo}"
