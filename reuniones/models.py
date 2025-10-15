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
    contenido = models.TextField(verbose_name="Contenido del Acta")
    aprobada = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Acta de la reunión: {self.reunion.titulo}"

class Asistencia(models.Model):
    reunion = models.ForeignKey(Reunion, on_delete=models.CASCADE, related_name="asistentes")
    vecino = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="asistencias")
    presente = models.BooleanField(default=False)

    class Meta:
        unique_together = ('reunion', 'vecino') # Para que un vecino no pueda registrarse dos veces en la misma reunión

    def __str__(self):
        estado = "Presente" if self.presente else "Ausente"
        return f"{self.vecino.username} - {self.reunion.titulo} ({estado})"