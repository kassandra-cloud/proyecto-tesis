"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Script del proceso ETL (Extract, Transform, Load) que extrae datos 
               del sistema transaccional (OLTP), los transforma y carga en el 
               esquema OLAP del Datamart para análisis.
--------------------------------------------------------------------------------
"""
import random  # Para generar datos aleatorios de prueba si faltan valores reales
from django.core.management.base import BaseCommand  # Base para comandos de consola
from django.db import transaction  # Para manejo de transacciones atómicas
from django.contrib.auth.models import User  # Modelo de usuario de Django
from django.utils import timezone  # Utilidades de fecha y hora
from django.db import models  # Modelos base de Django
from django.db.models import Avg  # Función de agregación Promedio

from datamart.models import LogRendimiento  # Modelo de logs para métricas técnicas

# Importación de modelos OLTP (Sistema Transaccional - Fuente de Datos)
from core.models import Perfil
from reuniones.models import Acta, LogConsultaActa, Reunion, Asistencia
from talleres.models import Taller, Inscripcion

# Manejo de importación condicional para Votaciones por si el módulo no existe
try:
    from votaciones.models import Votacion, Voto, LogIntentoVoto
except ImportError:
    class Votacion: objects = None
    class Voto: objects = None
    class LogIntentoVoto: objects = None

# Importación de modelos OLAP (Datamart - Destino de Datos)
from datamart.models import (
    DimVecino, DimTaller, DimActa, DimVotacion, DimReunion,
    FactInscripcionTaller, FactConsultaActa, FactParticipacionVotacion,
    FactAsistenciaReunion, FactMetricasDiarias, FactCalidadTranscripcion,
    FactMetricasTecnicas,
)

class Command(BaseCommand):
    help = "ETL para BI (Solo Usuarios Activos + Precisión Manual)"

    # Método auxiliar para determinar rango etario (simulado por ahora)
    def get_rango_etario(self, user):
        return "Adulto"

    # Ejecuta todo el proceso dentro de una transacción atómica (todo o nada)
    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Iniciando ETL...")

        # ---------------------------------------------------------
        # 1. LIMPIEZA DE DATOS (Vaciar Datamart previo)
        # ---------------------------------------------------------
        # Borrado de tablas de Hechos
        FactInscripcionTaller.objects.all().delete()
        FactConsultaActa.objects.all().delete()
        FactParticipacionVotacion.objects.all().delete()
        FactAsistenciaReunion.objects.all().delete()
        FactMetricasDiarias.objects.all().delete()
        FactCalidadTranscripcion.objects.all().delete()
        FactMetricasTecnicas.objects.all().delete()

        # Borrado de tablas de Dimensiones
        DimVecino.objects.all().delete()
        DimTaller.objects.all().delete()
        DimActa.objects.all().delete()
        DimVotacion.objects.all().delete()
        DimReunion.objects.all().delete()

        # ---------------------------------------------------------
        # 2. CARGA DE DIMENSIONES (Tablas maestras)
        # ---------------------------------------------------------

        # Carga Dimensión Vecinos (Solo usuarios activos)
        usuarios_activos = User.objects.filter(is_active=True)
        vecinos_creados = []
        for user in usuarios_activos:
            sector = "Sin Dirección"
            ninos = False
            try:
                # Intenta obtener datos extra del perfil
                if hasattr(user, "perfil"):
                    perfil = user.perfil
                    if perfil.direccion:
                        sector = perfil.direccion.strip()
                    ninos = perfil.total_ninos > 0
            except Exception:
                pass

            # Prepara el objeto DimVecino
            vecinos_creados.append(
                DimVecino(
                    vecino_id_oltp=user.id,
                    nombre_completo=user.username,
                    rango_etario=self.get_rango_etario(user),
                    direccion_sector=sector,
                    tiene_niños=ninos,
                )
            )
        # Inserta masivamente en la base de datos
        DimVecino.objects.bulk_create(vecinos_creados)

        # Carga Dimensión Talleres
        for t in Taller.objects.all():
            DimTaller.objects.create(
                taller_id_oltp=t.id,
                nombre=t.nombre,
                cupos_totales=t.cupos_totales,
            )

        # Carga Dimensión Actas
        for a in Acta.objects.all():
            # Obtiene la calificación de precisión del admin o simula una si es 0
            precision_real = float(getattr(a, "calificacion_precision", 0))
            if precision_real == 0:
                precision_real = round(random.uniform(90.0, 99.0), 1)

            DimActa.objects.create(
                acta_id_oltp=a.reunion.id,
                titulo=a.reunion.titulo,
                fecha_reunion=a.reunion.fecha.date(),
                precision_transcripcion=precision_real,
            )

        # Carga Dimensión Votaciones
        if Votacion.objects:
            for v in Votacion.objects.all():
                DimVotacion.objects.create(
                    votacion_id_oltp=v.id,
                    pregunta=v.pregunta,
                    fecha_inicio=v.fecha_cierre,
                )

        # Carga Dimensión Reuniones
        for r in Reunion.objects.all():
            DimReunion.objects.create(
                reunion_id_oltp=r.id,
                titulo=r.titulo,
                fecha=r.fecha.date(),
            )

        # ---------------------------------------------------------
        # 3. CARGA DE HECHOS (Tablas transaccionales del BI)
        # ---------------------------------------------------------
        
        # Mapeos en memoria para agilizar búsquedas de claves foráneas
        vecinos_map = {v.vecino_id_oltp: v for v in DimVecino.objects.all()}
        talleres_map = {t.taller_id_oltp: t for t in DimTaller.objects.all()}
        actas_map = {a.acta_id_oltp: a for a in DimActa.objects.all()}
        votaciones_map = {v.votacion_id_oltp: v for v in DimVotacion.objects.all()}
        reuniones_map = {r.reunion_id_oltp: r for r in DimReunion.objects.all()}

        # Hecho: Inscripciones a Talleres
        objs_ins = []
        for i in Inscripcion.objects.all():
            if i.vecino_id in vecinos_map and i.taller_id in talleres_map:
                objs_ins.append(
                    FactInscripcionTaller(
                        vecino=vecinos_map[i.vecino_id],
                        taller=talleres_map[i.taller_id],
                        fecha_inscripcion=i.fecha_inscripcion,
                    )
                )
        FactInscripcionTaller.objects.bulk_create(objs_ins)

        # Hecho: Consultas de Actas (Logs de lectura)
        objs_con = []
        for l in LogConsultaActa.objects.all():
            if l.vecino_id in vecinos_map and l.acta_id in actas_map:
                objs_con.append(
                    FactConsultaActa(
                        vecino=vecinos_map[l.vecino_id],
                        acta=actas_map[l.acta_id],
                        fecha_consulta=l.fecha_consulta,
                    )
                )
        FactConsultaActa.objects.bulk_create(objs_con)

        # Hecho: Participación en Votaciones
        if Voto.objects:
            objs_voto = []
            # Agrupa votos únicos por votante y votación
            votos_unicos = (
                Voto.objects.values(
                    "votante_id",
                    "opcion__votacion_id",
                    "opcion__votacion__fecha_cierre",
                )
                .distinct()
            )
            for vo in votos_unicos:
                vid = vo["votante_id"]
                votid = vo["opcion__votacion_id"]
                if vid in vecinos_map and votid in votaciones_map:
                    objs_voto.append(
                        FactParticipacionVotacion(
                            vecino=vecinos_map[vid],
                            votacion=votaciones_map[votid],
                            fecha_voto=vo["opcion__votacion__fecha_cierre"],
                        )
                    )
            FactParticipacionVotacion.objects.bulk_create(objs_voto)

        # Hecho: Asistencia a Reuniones
        objs_asis = []
        for asis in Asistencia.objects.filter(presente=True):
            if asis.vecino_id in vecinos_map and asis.reunion_id in reuniones_map:
                objs_asis.append(
                    FactAsistenciaReunion(
                        vecino=vecinos_map[asis.vecino_id],
                        reunion=reuniones_map[asis.reunion_id],
                    )
                )
        FactAsistenciaReunion.objects.bulk_create(objs_asis)

        # ---------------------------------------------------------
        # 4. CÁLCULO DE MÉTRICAS TÉCNICAS
        # ---------------------------------------------------------

        # Cálculo de tiempo promedio de respuesta desde logs
        promedio_tiempo = (
            LogRendimiento.objects.aggregate(prom=Avg("tiempo_ms"))["prom"] or 0
        )

        # Cálculo de disponibilidad del sistema (Uptime)
        total_peticiones = LogRendimiento.objects.count()
        errores = LogRendimiento.objects.filter(status_code__gte=500).count()
        if total_peticiones > 0:
            uptime_real = ((total_peticiones - errores) / total_peticiones) * 100
        else:
            uptime_real = 100.0

        # Conteo de fallos en votación móvil
        fallos_voto = 0
        if LogIntentoVoto.objects:
            fallos_voto = LogIntentoVoto.objects.filter(
                fue_exitoso=False,
                origen="APP_MOVIL",
            ).count()

        # Guarda las métricas diarias
        try:
            FactMetricasDiarias.objects.create(
                tiempo_respuesta_ms=int(promedio_tiempo),
                disponibilidad_sistema=round(uptime_real, 2),
                fallos_votacion=fallos_voto,
            )
        except Exception:
            pass

        # Datos simulados para calidad de transcripción si no existen
        if not FactCalidadTranscripcion.objects.exists():
            FactCalidadTranscripcion.objects.create(
                fecha=timezone.now(),
                total_palabras=100,
                palabras_correctas=95,
                precision_porcentaje=95.0,
                origen="SIMULADO",
            )

        # Mensaje final de éxito
        self.stdout.write(
            self.style.SUCCESS(
                f"ETL completado. Usuarios activos cargados: {len(vecinos_creados)}"
            )
        )