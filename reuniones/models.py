from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

# --- CLASE MODIFICADA ---
class EstadoReunion(models.TextChoices):
    PROGRAMADA = 'PROGRAMADA', 'Programada'
    EN_CURSO   = 'EN_CURSO',   'En Curso'
    REALIZADA  = 'REALIZADA',  'Realizada'
    CANCELADA  = 'CANCELADA',  'Cancelada' # <-- NUEVO ESTADO
    
class Reunion(models.Model):
    TIPO_REUNION = [
        ("Ordinaria", "Ordinaria"),
        ("Extraordinaria", "Extraordinaria"),
    ]

    fecha = models.DateTimeField(verbose_name="Fecha y Hora")
    tipo = models.CharField(max_length=20, choices=TIPO_REUNION, default="Ordinaria")
    titulo = models.CharField(max_length=200, verbose_name="Título")
    tabla = models.TextField(verbose_name="Tabla de contenidos")
    creada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="reuniones_creadas")
    creada_el = models.DateTimeField(auto_now_add=True)

    # Este campo ya lo tenías, está perfecto
    estado = models.CharField(
        max_length=20,
        choices=EstadoReunion.choices,
        default=EstadoReunion.PROGRAMADA,
        verbose_name="Estado"
    )

    def __str__(self):
        return f"{self.titulo} - {self.fecha.strftime('%d/%m/%Y')}"

class Acta(models.Model):
     # --- AÑADIR ESTOS ESTADOS DE TRANSCRIPCIÓN ---
    ESTADO_NO_SUBIDO = "NO_SUBIDO"
    ESTADO_PENDIENTE = "PENDIENTE"
    ESTADO_PROCESANDO = "PROCESANDO"
    ESTADO_COMPLETADO = "COMPLETADO"
    ESTADO_ERROR = "ERROR"
    
    ESTADO_TRANSCRIPCION_CHOICES = [
        (ESTADO_NO_SUBIDO, "No Subido"),
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_PROCESANDO, "Procesando"),
        (ESTADO_COMPLETADO, "Completado"),
        (ESTADO_ERROR, "Error"),
    ]
    # -----------------------------------------------

    reunion = models.OneToOneField(
        Reunion,
        on_delete=models.CASCADE,
        related_name="acta",
        primary_key=True  # <-- ¡AÑADE ESTA LÍNEA!
    )
    contenido = models.TextField(blank=True, default="Borrador del acta...")
    
    aprobada = models.BooleanField(default=False)
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="actas_aprobadas"
    )
    aprobado_en = models.DateTimeField(null=True, blank=True)

    # --- CAMPOS NUEVOS Y ACTUALIZADOS ---
    # (Asegúrate de que los campos 'transcripcion_borrador' y 
    # 'transcripcion_actualizado' ya NO estén aquí)

    archivo_audio = models.FileField(
        upload_to="audios_reuniones/",  # Esto se guardará en Cellar/S3
        null=True,
        blank=True,
        help_text="Archivo de audio (.webm, .ogg) subido por la directiva."
    )
    estado_transcripcion = models.CharField(
        max_length=20,
        choices=ESTADO_TRANSCRIPCION_CHOICES, # Usamos la nueva lista
        default=ESTADO_NO_SUBIDO # Usamos el nuevo default
    )
    # --- FIN DE CAMPOS NUEVOS ---

    def __str__(self):
        return f"Acta de {self.reunion.titulo}"

class Asistencia(models.Model):
    reunion = models.ForeignKey(Reunion, on_delete=models.CASCADE, related_name="asistentes")
    # (Aquí asumí que 'vecino' debe ser un Perfil, no un User, pero sigo tu modelo original)
    vecino = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="asistencias")
    presente = models.BooleanField(default=False)

    class Meta:
        unique_together = ('reunion', 'vecino') 

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