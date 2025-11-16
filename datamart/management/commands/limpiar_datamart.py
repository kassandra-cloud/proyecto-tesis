# datamart/management/commands/limpiar_datamart.py
from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Borra forzadamente todas las tablas y migraciones de la app datamart'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            "ADVERTENCIA: Se borrarán todas las tablas de 'datamart' y su historial de migración."
        ))
        
        tables_to_drop = [
            'datamart_factconsultaacta',
            'datamart_factinscripciontaller',
            'datamart_factparticipacionvotacion',
            'datamart_dimacta',
            'datamart_dimtaller',
            'datamart_dimvotacion',
            'datamart_dimvecino',
        ]

        with connection.cursor() as cursor:
            # Desactivar chequeo de claves foráneas para permitir borrado
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            
            self.stdout.write("Borrando tablas de datamart...")
            for table_name in tables_to_drop:
                try:
                    cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
                    self.stdout.write(f" - Tabla '{table_name}' borrada.")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error borrando {table_name}: {e}"))
            
            self.stdout.write("Borrando historial de migración de datamart...")
            try:
                cursor.execute("DELETE FROM django_migrations WHERE app = 'datamart';")
                self.stdout.write(f" - Historial de 'datamart' borrado de django_migrations.")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error borrando historial: {e}"))

            # Reactivar chequeo de claves foráneas
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

        self.stdout.write(self.style.SUCCESS("¡Limpieza de 'datamart' completada!"))