# datamart/models.py
from django.db import models

class DimVecino(models.Model):
    vecino_id_oltp = models.IntegerField(unique=True, help_text="ID original del modelo User de Django")
    nombre_completo = models.CharField(max_length=255)
    rango_etario = models.CharField(max_length=50, blank=True, null=True)
    direccion_sector = models.CharField(max_length=255, blank=True, null=True)
    tiene_niños = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre_completo

class DimTaller(models.Model):
    taller_id_oltp = models.IntegerField(unique=True, help_text="ID original de la app 'talleres'")
    nombre = models.CharField(max_length=255)
    cupos_totales = models.IntegerField(default=0)

    def __str__(self):
        return self.nombre

class DimActa(models.Model):
    acta_id_oltp = models.IntegerField(unique=True, help_text="ID original de la app 'reuniones.Acta'")
    titulo = models.CharField(max_length=255)
    fecha_reunion = models.DateField()

    def __str__(self):
        return self.titulo

class DimVotacion(models.Model):
    votacion_id_oltp = models.IntegerField(unique=True, help_text="ID original de la app 'votaciones'")
    pregunta = models.CharField(max_length=255)
    fecha_inicio = models.DateTimeField()

    def __str__(self):
        return self.pregunta

# --- HECHOS ---

class FactInscripcionTaller(models.Model):
    vecino = models.ForeignKey(DimVecino, on_delete=models.CASCADE, related_name="inscripciones")
    taller = models.ForeignKey(DimTaller, on_delete=models.CASCADE)
    fecha_inscripcion = models.DateTimeField()

class FactConsultaActa(models.Model):
    vecino = models.ForeignKey(DimVecino, on_delete=models.CASCADE)
    acta = models.ForeignKey(DimActa, on_delete=models.CASCADE)
    fecha_consulta = models.DateTimeField()

class FactParticipacionVotacion(models.Model):
    vecino = models.ForeignKey(DimVecino, on_delete=models.CASCADE)
    votacion = models.ForeignKey(DimVotacion, on_delete=models.CASCADE)
    fecha_voto = models.DateTimeField()