# datamart/management/commands/procesar_etl.py
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User

# --- Modelos de Producción (OLTP) ---
from core.models import Perfil
from reuniones.models import Acta, LogConsultaActa
from talleres.models import Taller, Inscripcion
from votaciones.models import Votacion, Voto # ¡Usamos tus modelos reales!

# --- Modelos de Destino (OLAP) ---
from datamart.models import (
    DimVecino, DimTaller, DimActa, DimVotacion,
    FactInscripcionTaller, FactConsultaActa, FactParticipacionVotacion
)

class Command(BaseCommand):
    help = 'Procesa los datos de producción (OLTP) al Data Mart (OLAP) para BI.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Iniciando Proceso ETL..."))

        # --- 1. LIMPIAR Data Mart ---
        self.stdout.write("Limpiando tablas de Hechos...")
        FactInscripcionTaller.objects.all().delete()
        FactConsultaActa.objects.all().delete()
        FactParticipacionVotacion.objects.all().delete()
        
        self.stdout.write("Limpiando tablas de Dimensiones...")
        DimVecino.objects.all().delete()
        DimTaller.objects.all().delete()
        DimActa.objects.all().delete()
        DimVotacion.objects.all().delete()

        # --- 2. CARGAR Dimensiones ---
        self.stdout.write("Cargando Dimensión 'DimVecino'...")
        for user in User.objects.all():
            nombre = user.get_full_name() or user.username
            rango, sector, niños = None, None, False
            try:
                perfil = Perfil.objects.get(usuario=user) 
                sector = perfil.direccion
                niños = perfil.total_ninos > 0
            except Perfil.DoesNotExist:
                pass
            DimVecino.objects.create(
                vecino_id_oltp=user.id, nombre_completo=nombre,
                rango_etario=rango, direccion_sector=sector, tiene_niños=niños
            )
        
        self.stdout.write("Cargando Dimensión 'DimTaller'...")
        for taller_oltp in Taller.objects.all():
            DimTaller.objects.create(
                taller_id_oltp=taller_oltp.id,
                nombre=taller_oltp.nombre,
                cupos_totales=taller_oltp.cupos_totales
            )

        self.stdout.write("Cargando Dimensión 'DimActa'...")
        for acta_oltp in Acta.objects.all().select_related('reunion'):
            DimActa.objects.create(
                acta_id_oltp=acta_oltp.reunion.id,
                titulo=acta_oltp.reunion.titulo,
                fecha_reunion=acta_oltp.reunion.fecha.date()
            )

        self.stdout.write("Cargando Dimensión 'DimVotacion'...")
        if Votacion.objects:
            for votacion_oltp in Votacion.objects.all():
                DimVotacion.objects.create(
                    votacion_id_oltp=votacion_oltp.id,
                    pregunta=votacion_oltp.pregunta, 
                    # --- CORRECCIÓN 1 ---
                    # Usamos 'fecha_cierre' porque 'fecha_inicio' no existe
                    fecha_inicio=votacion_oltp.fecha_cierre 
                )

        # --- 3. CARGAR Hechos ---
        self.stdout.write("Cargando Hecho 'FactInscripcionTaller'...")
        for inscripcion_oltp in Inscripcion.objects.all():
            try:
                dim_vecino = DimVecino.objects.get(vecino_id_oltp=inscripcion_oltp.vecino.id)
                dim_taller = DimTaller.objects.get(taller_id_oltp=inscripcion_oltp.taller.id)
                FactInscripcionTaller.objects.create(
                    vecino=dim_vecino, taller=dim_taller,
                    fecha_inscripcion=inscripcion_oltp.fecha_inscripcion
                )
            except (DimVecino.DoesNotExist, DimTaller.DoesNotExist): pass

        self.stdout.write("Cargando Hecho 'FactConsultaActa'...")
        for log_oltp in LogConsultaActa.objects.all():
            try:
                dim_vecino = DimVecino.objects.get(vecino_id_oltp=log_oltp.vecino.id)
                dim_acta = DimActa.objects.get(acta_id_oltp=log_oltp.acta.reunion_id)
                FactConsultaActa.objects.create(
                    vecino=dim_vecino, acta=dim_acta,
                    fecha_consulta=log_oltp.fecha_consulta
                )
            except (DimVecino.DoesNotExist, DimActa.DoesNotExist): pass

        self.stdout.write("Cargando Hecho 'FactParticipacionVotacion'...")
        if Voto.objects:
            # Usamos select_related para optimizar la consulta
            for voto_oltp in Voto.objects.all().select_related('votante', 'opcion__votacion'):
                try:
                    # --- CORRECCIÓN 2 ---
                    # Usamos 'votante' en lugar de 'vecino'
                    dim_vecino = DimVecino.objects.get(vecino_id_oltp=voto_oltp.votante.id) 
                    
                    # --- CORRECCIÓN 3 ---
                    # Accedemos a la votacion a través de la 'opcion'
                    dim_votacion = DimVotacion.objects.get(votacion_id_oltp=voto_oltp.opcion.votacion.id)
                    
                    FactParticipacionVotacion.objects.create(
                        vecino=dim_vecino, 
                        votacion=dim_votacion,
                        # --- CORRECCIÓN 4 ---
                        # Usamos 'fecha_cierre' porque 'fecha_voto' no existe
                        fecha_voto=voto_oltp.opcion.votacion.fecha_cierre
                    )
                except (AttributeError, DimVecino.DoesNotExist, DimVotacion.DoesNotExist):
                    self.stdout.write(self.style.WARNING(f"Omitiendo voto para vecino/votación no encontrado."))

        self.stdout.write(self.style.SUCCESS("¡Proceso ETL completado con éxito!"))