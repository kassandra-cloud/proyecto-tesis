from django.db import models
from django.conf import settings

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

    def __str__(self):
        return f"{self.titulo} - {self.fecha.strftime('%d/%m/%Y')}"

class Acta(models.Model):
    reunion = models.OneToOneField(Reunion, on_delete=models.CASCADE, primary_key=True)
    contenido = models.TextField(blank=True, default='')
    aprobada = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Acta de la reunión: {self.reunion.titulo}"
    transcripcion_borrador    = models.TextField(blank=True, default='')
    transcripcion_estado      = models.CharField(
        max_length=20,
        choices=[('BORRADOR','Borrador'), ('APROBADA','Aprobada')],
        default='BORRADOR'
    )
    transcripcion_actualizado = models.DateTimeField(auto_now=True)
    aprobado_por              = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='actas_aprobadas'
    )
    aprobado_en               = models.DateTimeField(null=True, blank=True)

class Asistencia(models.Model):
    reunion = models.ForeignKey(Reunion, on_delete=models.CASCADE, related_name="asistentes")
    vecino = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="asistencias")
    presente = models.BooleanField(default=False)

    class Meta:
        unique_together = ('reunion', 'vecino') # Para que un vecino no pueda registrarse dos veces en la misma reunión

    def __str__(self):
        estado = "Presente" if self.presente else "Ausente"
        return f"{self.vecino.username} - {self.reunion.titulo} ({estado})"
    
class ActaEmailLog(models.Model):
    acta = models.ForeignKey("Acta", on_delete=models.CASCADE, related_name="emails_enviados")
    destinatarios = models.TextField()  # guarda la lista como string
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    fecha_envio = models.DateTimeField(auto_now_add=True)
    ok = models.BooleanField(default=True)
    error = models.TextField(blank=True) 