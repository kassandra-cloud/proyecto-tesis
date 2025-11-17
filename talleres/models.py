# en /talleres/models.py

from django.db import models
from django.contrib.auth.models import User
from django.db import models
from django.conf import settings
from django.utils import timezone # <- Importar timezone

class Taller(models.Model):
    
    # --- NUEVA CLASE PARA ESTADOS ---
    class Estado(models.TextChoices):
        PROGRAMADO = "PROGRAMADO", "Programado"
        FINALIZADO = "FINALIZADO", "Finalizado"
        CANCELADO = "CANCELADO", "Cancelado"
    # --- FIN ---

    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField()
    cupos_totales = models.PositiveIntegerField()
    
    # --- CAMPOS MODIFICADOS ---
    # Cambiamos DateField a DateTimeField para incluir la hora
    fecha_inicio = models.DateTimeField(verbose_name="Fecha y Hora de Inicio")
    fecha_termino = models.DateTimeField(verbose_name="Fecha y Hora de Término")
    # --- FIN MODIFICACIÓN ---

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name="talleres_creados"
    )
    creado_el = models.DateTimeField(auto_now_add=True)

    # --- NUEVOS CAMPOS ---
    estado = models.CharField(
        max_length=20, 
        choices=Estado.choices, 
        default=Estado.PROGRAMADO,
        verbose_name="Estado"
    )
    motivo_cancelacion = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Motivo de Cancelación"
    )
    # --- FIN NUEVOS CAMPOS ---


    def __str__(self):
        return self.nombre

    class Meta:
        ordering = ['fecha_inicio']
        verbose_name = "Taller"
        verbose_name_plural = "Talleres"

    @property
    def es_cancelable(self):
        """
        Verifica si el taller se puede cancelar (solo si está programado)
        """
        return self.estado == self.Estado.PROGRAMADO
    
    @property
    def esta_activo(self):
        """
        Verifica si el taller está actualmente en curso.
        """
        ahora = timezone.now()
        return self.fecha_inicio <= ahora <= self.fecha_termino and self.estado == self.Estado.PROGRAMADO

    @property
    def cupos_disponibles(self):
        """
        Calcula los cupos restantes.
        Requiere que 'inscritos_count' sea anotado en la vista.
        """
        # Usamos getattr por seguridad, si 'inscritos_count' no existe
        # (aunque nuestras vistas ya lo añaden)
        inscritos = getattr(self, 'inscritos_count', 0)
        return self.cupos_totales - inscritos
# --- 2. CLASE INSCRIPCION  ---
class Inscripcion(models.Model):
    vecino = models.ForeignKey(User, on_delete=models.CASCADE)
    # Esta línea necesita que 'Taller' ya haya sido definido
    taller = models.ForeignKey(Taller, on_delete=models.CASCADE)
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Evita que un usuario se inscriba dos veces
        unique_together = ('vecino', 'taller')

    def __str__(self):
        return f'{self.vecino.username} inscrito en {self.taller.nombre}'