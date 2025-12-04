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
    votacion = models.ForeignKey(Votacion, related_name='opciones', on_delete=models.CASCADE)
    texto = models.CharField(max_length=150)

    def __str__(self):
        return self.texto

class Voto(models.Model):
    opcion = models.ForeignKey(Opcion, related_name='votos', on_delete=models.CASCADE)
    votante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # 2. Agrega este campo nuevo
    hash_voto = models.CharField(max_length=64, blank=True, editable=False) 

    class Meta:
        unique_together = [['opcion', 'votante']]

    # 3. Agrega este método para generar el Hash automático
    def save(self, *args, **kwargs):
        # Si ya tiene ID (es edición) o es nuevo, calculamos el hash
        # Usamos: ID Usuario + ID Opcion + LLAVE SECRETA DEL PROYECTO
        data_string = f"{self.votante.id}-{self.opcion.id}-{settings.SECRET_KEY}"
        
        # Generamos el hash SHA-256
        self.hash_voto = hashlib.sha256(data_string.encode()).hexdigest()
        
        super().save(*args, **kwargs)