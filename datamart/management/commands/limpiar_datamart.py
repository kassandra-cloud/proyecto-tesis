from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Borra forzadamente todas las tablas y migraciones de la app datamart'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            "ADVERTENCIA: Se borrarán todas las tablas de 'datamart' y su historial de migración."
        ))
        
        # LISTA COMPLETA DE TABLAS A BORRAR
        tables_to_drop = [
            'datamart_factmetricasdiarias',       # Nueva
            'datamart_factcalidadtranscripcion',  # Nueva
            'datamart_factmetricastecnicas',      # Nueva
            'datamart_factasistenciareunion',     # Nueva
            'datamart_factparticipacionvotacion',
            'datamart_factconsultaacta',
            'datamart_factinscripciontaller',
            'datamart_dimreunion',                # Nueva
            'datamart_dimacta',
            'datamart_dimtaller',
            'datamart_dimvotacion',
            'datamart_dimvecino',
        ]

        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            
            self.stdout.write("Borrando tablas de datamart...")
            for table_name in tables_to_drop:
                try:
                    cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
                    self.stdout.write(f" - Tabla '{table_name}' borrada.")
                except Exception as e:
                    pass # Ignoramos si no existe
            
            self.stdout.write("Borrando historial de migración...")
            try:
                cursor.execute("DELETE FROM django_migrations WHERE app = 'datamart';")
            except Exception as e:
                pass

            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

        self.stdout.write(self.style.SUCCESS("¡Limpieza completa! Listo para migrar de cero."))