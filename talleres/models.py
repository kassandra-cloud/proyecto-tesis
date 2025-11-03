from django.db import models
from django.contrib.auth.models import User

# --- 1. CLASE TALLER (Debe ir primero) ---
class Taller(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()
    cupos_totales = models.PositiveIntegerField(default=20)
    
    def __str__(self):
        return self.nombre
    
    @property
    def inscritos_count(self):
        """Cuenta cuántos usuarios se han inscrito."""
        return self.inscripcion_set.count()

    @property
    def cupos_disponibles(self):
        """Calcula los cupos restantes."""
        return self.cupos_totales - self.inscritos_count

# --- 2. CLASE INSCRIPCION (Debe ir después de Taller) ---
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