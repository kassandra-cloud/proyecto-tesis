"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Definición de los modelos de datos para el Datamart, estructurados 
               en un esquema de estrella con Dimensiones (Dim) y Hechos (Fact).
--------------------------------------------------------------------------------
"""
from django.db import models  # Importa la clase base de modelos de Django

# =========================
# DIMENSIONES (Tablas Maestras)
# =========================

class DimVecino(models.Model):
    # ID original del vecino en el sistema transaccional
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
    # Precisión de la transcripción automática del acta
    precision_transcripcion = models.FloatField(default=0.0, help_text="Porcentaje 0-100")

    class Meta:
        indexes = [
            models.Index(fields=["fecha_reunion"]),  # Índice para acelerar filtrado por fecha
        ]

    def __str__(self):
        return self.titulo

class DimVotacion(models.Model):
    votacion_id_oltp = models.IntegerField(unique=True)
    pregunta = models.CharField(max_length=255)
    fecha_inicio = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["fecha_inicio"]),
        ]

    def __str__(self):
        return self.pregunta

class DimReunion(models.Model):
    reunion_id_oltp = models.IntegerField(unique=True)
    titulo = models.CharField(max_length=255)
    fecha = models.DateField()

    class Meta:
        indexes = [
            models.Index(fields=["fecha"]),
        ]

    def __str__(self):
        return self.titulo


# =========================
# HECHOS (Tablas Transaccionales / Eventos)
# =========================

class FactInscripcionTaller(models.Model):
    # Relación con dimensión Vecino
    vecino = models.ForeignKey(DimVecino, on_delete=models.CASCADE)
    # Relación con dimensión Taller
    taller = models.ForeignKey(DimTaller, on_delete=models.CASCADE)
    fecha_inscripcion = models.DateTimeField()

    class Meta:
        # Índices compuestos para optimizar consultas de cruce
        indexes = [
            models.Index(fields=["fecha_inscripcion"]),
            models.Index(fields=["taller", "fecha_inscripcion"]),
            models.Index(fields=["vecino", "fecha_inscripcion"]),
        ]

class FactConsultaActa(models.Model):
    vecino = models.ForeignKey(DimVecino, on_delete=models.CASCADE)
    acta = models.ForeignKey(DimActa, on_delete=models.CASCADE)
    fecha_consulta = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["fecha_consulta"]),
            models.Index(fields=["acta", "fecha_consulta"]),
            models.Index(fields=["vecino", "fecha_consulta"]),
        ]

class FactParticipacionVotacion(models.Model):
    vecino = models.ForeignKey(DimVecino, on_delete=models.CASCADE)
    votacion = models.ForeignKey(DimVotacion, on_delete=models.CASCADE)
    fecha_voto = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["fecha_voto"]),
            models.Index(fields=["votacion", "fecha_voto"]),
            models.Index(fields=["vecino", "fecha_voto"]),
        ]

class FactAsistenciaReunion(models.Model):
    vecino = models.ForeignKey(DimVecino, on_delete=models.CASCADE)
    reunion = models.ForeignKey(DimReunion, on_delete=models.CASCADE)

    class Meta:
        indexes = [
            models.Index(fields=["reunion"]),
            models.Index(fields=["vecino"]),
        ]

# =========================
# EXTRA: MÉTRICAS Y CALIDAD
# =========================

class FactCalidadTranscripcion(models.Model):
    fecha = models.DateField()
    total_palabras = models.IntegerField()
    palabras_correctas = models.IntegerField()
    precision_porcentaje = models.FloatField()
    origen = models.CharField(max_length=100, default="SIMULADO")

    class Meta:
        indexes = [
            models.Index(fields=["fecha"]),
            models.Index(fields=["origen", "fecha"]),
        ]

class FactMetricasDiarias(models.Model):
    fecha = models.DateField(auto_now_add=True)
    tiempo_respuesta_ms = models.IntegerField(help_text="Promedio en ms")
    disponibilidad_sistema = models.FloatField(help_text="Porcentaje 0-100")
    fallos_votacion = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["fecha"]),
        ]

class FactMetricasTecnicas(models.Model):
    fecha = models.DateField(auto_now_add=True)
    tiempo_respuesta_ms = models.IntegerField()
    disponibilidad = models.FloatField()
    fallos_votacion = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["fecha"]),
        ]

# =========================
# LOGS DE RENDIMIENTO (Fuente para KPIs técnicos)
# =========================

class LogRendimiento(models.Model):
    usuario = models.CharField(max_length=150, null=True, blank=True)
    path = models.CharField(max_length=255, help_text="La página visitada")
    metodo = models.CharField(max_length=10)  # Ejemplo: GET o POST
    tiempo_ms = models.IntegerField(help_text="Milisegundos que tardó")
    status_code = models.IntegerField(default=200)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["fecha"]),
            models.Index(fields=["fecha", "path"]),
            models.Index(fields=["fecha", "status_code"]),
            models.Index(fields=["path"]),
        ]

    def __str__(self):
        return f"{self.path} - {self.tiempo_ms}ms - {self.status_code}"