from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = "Limpia todas las tablas reales del datamart y su historial de migraciones."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            "Eliminando TODAS las tablas que comienzan con 'datamart_'..."
        ))

        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

            # Obtener TODAS las tablas que realmente existen
            cursor.execute("SHOW TABLES LIKE 'datamart%';")
            tablas = cursor.fetchall()

            for (tabla,) in tablas:
                try:
                    cursor.execute(f"DROP TABLE `{tabla}`;")
                    self.stdout.write(f" - Borrada: {tabla}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error al borrar {tabla}: {e}"))

            self.stdout.write("Limpiando migraciones de la app datamart...")
            cursor.execute("DELETE FROM django_migrations WHERE app = 'datamart';")

            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

        self.stdout.write(self.style.SUCCESS("¡Limpieza COMPLETA!"))
        self.stdout.write(self.style.SUCCESS("Ahora ejecuta:"))
        self.stdout.write(self.style.SUCCESS("  python manage.py migrate datamart"))
