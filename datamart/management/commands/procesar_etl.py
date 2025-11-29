import time
from datetime import date
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count, Q
from django.db import models # <-- CORRECCIÓN CRÍTICA: Se necesita para modelos.Min/Max, etc.
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

# Modelos del Data Mart (Destino)
from datamart.models import (
    DimVecino, DimTaller, DimActa, DimVotacion,
    FactInscripcionTaller, FactConsultaActa, FactParticipacionVotacion
)

# Modelos del Sistema Transaccional (Origen)
from core.models import Perfil          # Para DimVecino
from talleres.models import Taller, Inscripcion # Para DimTaller y FactInscripcionTaller
from reuniones.models import Acta, LogConsultaActa # Para DimActa y FactConsultaActa
from votaciones.models import Votacion, Voto # Para DimVotacion y FactParticipacionVotacion


User = get_user_model()


class Command(BaseCommand):
    help = "Ejecuta el proceso ETL (Extracción, Transformación y Carga) para actualizar el Data Mart."

    def get_rango_etario(self, user: User) -> str:
        """Función simplificada para rango etario."""
        return "No Disponible"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- INICIANDO PROCESO ETL ---"))
        start_time = time.time()

        # 1. CARGA DE DIMENSIONES
        self.stdout.write(self.style.HTTP_INFO("1. Cargando Dimensión Vecino..."))
        self.procesar_dim_vecino()

        self.stdout.write(self.style.HTTP_INFO("2. Cargando Dimensión Taller..."))
        self.procesar_dim_taller()

        self.stdout.write(self.style.HTTP_INFO("3. Cargando Dimensión Acta..."))
        self.procesar_dim_acta()

        self.stdout.write(self.style.HTTP_INFO("4. Cargando Dimensión Votación..."))
        self.procesar_dim_votacion()
        
        # 2. CARGA DE HECHOS
        self.stdout.write(self.style.HTTP_INFO("5. Cargando Hechos de Inscripción a Talleres..."))
        self.procesar_inscripciones_taller()

        self.stdout.write(self.style.HTTP_INFO("6. Cargando Hechos de Participación en Votaciones..."))
        self.procesar_participacion_votacion()

        self.stdout.write(self.style.HTTP_INFO("7. Cargando Hechos de Consulta de Actas..."))
        self.procesar_consultas_actas() 

        end_time = time.time()
        duration = end_time - start_time
        self.stdout.write(self.style.SUCCESS(f"--- PROCESO ETL FINALIZADO con éxito en {duration:.2f} segundos. ---"))

    # =========================================================================
    # DIMENSIONES
    # =========================================================================

    def procesar_dim_vecino(self):
        """Carga datos de Perfil/User a DimVecino."""
        DimVecino.objects.all().delete()
        
        perfiles = Perfil.objects.select_related('usuario').all()
        
        dim_vecinos = []
        for perfil in perfiles:
            user = perfil.usuario
            
            full_name = f"{user.first_name or ''} {user.last_name or ''} {perfil.apellido_paterno or ''} {perfil.apellido_materno or ''}".strip()
            
            sector = perfil.direccion.split(',')[0].strip() if perfil.direccion else None

            dim_vecinos.append(DimVecino(
                vecino_id_oltp=user.id,
                nombre_completo=full_name or user.username,
                rango_etario=self.get_rango_etario(user), 
                direccion_sector=sector,
                tiene_niños=(perfil.total_ninos > 0)
            ))
        
        DimVecino.objects.bulk_create(dim_vecinos)
        self.stdout.write(self.style.SUCCESS(f"DimVecino cargados: {len(dim_vecinos)}"))


    def procesar_dim_taller(self):
        """Carga datos de Taller a DimTaller."""
        DimTaller.objects.all().delete()
        
        talleres = Taller.objects.all()
        dim_talleres = [
            DimTaller(
                taller_id_oltp=t.id,
                nombre=t.nombre,
                cupos_totales=t.cupos_totales
            ) for t in talleres
        ]
        
        DimTaller.objects.bulk_create(dim_talleres)
        self.stdout.write(self.style.SUCCESS(f"DimTaller cargados: {len(dim_talleres)}"))


    def procesar_dim_acta(self):
        """Carga datos de Acta (OLTP) a DimActa."""
        DimActa.objects.all().delete()
        
        actas = Acta.objects.select_related('reunion').all()
        dim_actas = [
            DimActa(
                acta_id_oltp=a.pk, 
                titulo=a.reunion.titulo,
                fecha_reunion=a.reunion.fecha.date() 
            ) for a in actas
        ]
        
        DimActa.objects.bulk_create(dim_actas)
        self.stdout.write(self.style.SUCCESS(f"DimActa cargadas: {len(dim_actas)}"))

    def procesar_dim_votacion(self):
        """Carga datos de Votacion (OLTP) a DimVotacion."""
        DimVotacion.objects.all().delete()
        
        votaciones = Votacion.objects.all()
        dim_votaciones = [
            DimVotacion(
                votacion_id_oltp=v.id,
                pregunta=v.pregunta,
                fecha_inicio=v.fecha_cierre # Usando fecha_cierre como proxy para el evento
            ) for v in votaciones
        ]
        
        DimVotacion.objects.bulk_create(dim_votaciones)
        self.stdout.write(self.style.SUCCESS(f"DimVotacion cargadas: {len(dim_votaciones)}"))

    # =========================================================================
    # HECHOS
    # =========================================================================

    def procesar_inscripciones_taller(self):
        """Carga datos de Inscripcion a FactInscripcionTaller."""
        FactInscripcionTaller.objects.all().delete()
        
        inscripciones = Inscripcion.objects.select_related('vecino', 'taller').all()
        
        vecino_map = {d.vecino_id_oltp: d for d in DimVecino.objects.all()}
        taller_map = {d.taller_id_oltp: d for d in DimTaller.objects.all()}

        fact_inscripciones = []
        for i in inscripciones:
            dim_vecino = vecino_map.get(i.vecino_id)
            dim_taller = taller_map.get(i.taller_id)
            
            if dim_vecino and dim_taller:
                fact_inscripciones.append(FactInscripcionTaller(
                    vecino=dim_vecino,
                    taller=dim_taller,
                    fecha_inscripcion=i.fecha_inscripcion
                ))
        
        FactInscripcionTaller.objects.bulk_create(fact_inscripciones)
        self.stdout.write(self.style.SUCCESS(f"FactInscripcionTaller cargados: {len(fact_inscripciones)}"))


    def procesar_participacion_votacion(self):
        """Carga datos de Voto a FactParticipacionVotacion."""
        FactParticipacionVotacion.objects.all().delete()
        
        # Agrupación de votos únicos por votante y votación
        votos_agrupados = Voto.objects.select_related('opcion__votacion').values(
            'votante_id', 'opcion__votacion_id', 'opcion__votacion__fecha_cierre'
        ).annotate(
            fecha_voto_min=models.Min('id') # <--- Esto ahora funciona gracias a la importación
        ).order_by('votante_id', 'opcion__votacion_id')
        
        vecino_map = {d.vecino_id_oltp: d for d in DimVecino.objects.all()}
        votacion_map = {d.votacion_id_oltp: d for d in DimVotacion.objects.all()}

        fact_participaciones = []
        for v in votos_agrupados:
            dim_vecino = vecino_map.get(v['votante_id'])
            dim_votacion = votacion_map.get(v['opcion__votacion_id'])
            
            if dim_vecino and dim_votacion:
                fact_participaciones.append(FactParticipacionVotacion(
                    vecino=dim_vecino,
                    votacion=dim_votacion,
                    fecha_voto=v['opcion__votacion__fecha_cierre'] 
                ))
        
        FactParticipacionVotacion.objects.bulk_create(fact_participaciones)
        self.stdout.write(self.style.SUCCESS(f"FactParticipacionVotacion cargados: {len(fact_participaciones)}"))


    def procesar_consultas_actas(self):
        """
        Extrae logs de consultas de actas (transaccional) y carga la FactConsultaActa.
        """
        FactConsultaActa.objects.all().delete()

        logs = LogConsultaActa.objects.all().select_related('acta', 'vecino')

        vecino_map = {d.vecino_id_oltp: d for d in DimVecino.objects.all()}
        acta_map = {d.acta_id_oltp: d for d in DimActa.objects.all()}

        fact_consultas = []
        for log in logs:
            dim_vecino = vecino_map.get(log.vecino_id) 
            dim_acta = acta_map.get(log.acta_id)

            if dim_vecino and dim_acta:
                fact_consultas.append(FactConsultaActa(
                    vecino=dim_vecino,
                    acta=dim_acta,
                    fecha_consulta=log.fecha_consulta
                ))
            else:
                self.stderr.write(self.style.WARNING(f"Advertencia: No se encontró DimVecino o DimActa para LogConsultaActa ID {log.id}. Salto de registro."))


        FactConsultaActa.objects.bulk_create(fact_consultas)
        self.stdout.write(self.style.SUCCESS(f"FactConsultaActa cargados: {len(fact_consultas)}"))