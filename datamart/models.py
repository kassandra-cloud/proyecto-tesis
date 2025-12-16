from django.db import models

# --- DIMENSIONES ---

class DimVecino(models.Model):
    vecino_id_oltp = models.IntegerField(unique=True, help_text="ID original del modelo User")
    nombre_completo = models.CharField(max_length=255)
    rango_etario = models.CharField(max_length=50, blank=True, null=True)
    direccion_sector = models.CharField(max_length=255, blank=True, null=True)
    tiene_niños = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre_completo

class DimTaller(models.Model):
    taller_id_oltp = models.IntegerField(unique=True)
    nombre = models.CharField(max_length=255)
    cupos_totales = models.IntegerField(default=0)

    def __str__(self):
        return self.nombre

class DimActa(models.Model):
    acta_id_oltp = models.IntegerField(unique=True)
    titulo = models.CharField(max_length=255)
    fecha_reunion = models.DateField()
    precision_transcripcion = models.FloatField(default=0.0, help_text="Porcentaje 0-100")

    def __str__(self):
        return self.titulo

class DimVotacion(models.Model):
    votacion_id_oltp = models.IntegerField(unique=True)
    pregunta = models.CharField(max_length=255)
    fecha_inicio = models.DateTimeField()

    def __str__(self):
        return self.pregunta

class DimReunion(models.Model):
    reunion_id_oltp = models.IntegerField(unique=True)
    titulo = models.CharField(max_length=255)
    fecha = models.DateField()

    def __str__(self):
        return self.titulo

# --- HECHOS ---

class FactInscripcionTaller(models.Model):
    vecino = models.ForeignKey(DimVecino, on_delete=models.CASCADE)
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

class FactAsistenciaReunion(models.Model):
    vecino = models.ForeignKey(DimVecino, on_delete=models.CASCADE)
    reunion = models.ForeignKey(DimReunion, on_delete=models.CASCADE)

# --- ¡ESTAS SON LAS TABLAS QUE TE FALTABAN! ---

class FactCalidadTranscripcion(models.Model):
    fecha = models.DateField()
    total_palabras = models.IntegerField()
    palabras_correctas = models.IntegerField()
    precision_porcentaje = models.FloatField()
    origen = models.CharField(max_length=100, default="SIMULADO")

class FactMetricasDiarias(models.Model):
    fecha = models.DateField(auto_now_add=True)
    tiempo_respuesta_ms = models.IntegerField(help_text="Promedio en ms")
    disponibilidad_sistema = models.FloatField(help_text="Porcentaje 0-100")
    fallos_votacion = models.IntegerField(default=0)

# Agregamos esta también por si el ETL antiguo la llama, para evitar errores
class FactMetricasTecnicas(models.Model):
    fecha = models.DateField(auto_now_add=True)
    tiempo_respuesta_ms = models.IntegerField()
    disponibilidad = models.FloatField()
    fallos_votacion = models.IntegerField(default=0)

# 
class LogRendimiento(models.Model):
    usuario = models.CharField(max_length=150, null=True, blank=True)
    path = models.CharField(max_length=255, help_text="La página visitada")
    metodo = models.CharField(max_length=10) # GET o POST
    tiempo_ms = models.IntegerField(help_text="Milisegundos que tardó")
    fecha = models.DateTimeField(auto_now_add=True)
    #  NUEVO CAMPO: Para guardar el código (200, 404, 500)
    status_code = models.IntegerField(default=200) 
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.path} - {self.tiempo_ms}ms - {self.status_code}"