"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Comando de gestión (management command) para eliminar todas las 
               tablas y el historial de migraciones asociadas al Datamart.
--------------------------------------------------------------------------------
"""
from django.core.management.base import BaseCommand  # Clase base para crear comandos personalizados
from django.db import connection  # Permite ejecutar consultas SQL directas a la base de datos

class Command(BaseCommand):
    # Texto de ayuda que aparece al ejecutar python manage.py help limpiar_datamart
    help = "Limpia todas las tablas reales del datamart y su historial de migraciones."

    def handle(self, *args, **options):
        # Muestra un mensaje de advertencia en la consola
        self.stdout.write(self.style.WARNING(
            "Eliminando TODAS las tablas que comienzan con 'datamart_'..."
        ))

        # Abre un cursor para ejecutar SQL crudo
        with connection.cursor() as cursor:
            # Desactiva temporalmente el chequeo de claves foráneas para evitar errores al borrar
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

            # Busca todas las tablas que pertenezcan a la app datamart
            cursor.execute("SHOW TABLES LIKE 'datamart%';")
            tablas = cursor.fetchall()  # Obtiene la lista de tablas

            # Itera sobre cada tabla encontrada
            for (tabla,) in tablas:
                try:
                    # Ejecuta la sentencia DROP TABLE para borrar la tabla
                    cursor.execute(f"DROP TABLE `{tabla}`;")
                    self.stdout.write(f" - Borrada: {tabla}")
                except Exception as e:
                    # Si falla, muestra el error en rojo
                    self.stdout.write(self.style.ERROR(f"Error al borrar {tabla}: {e}"))

            # Informa que se limpiará el historial de migraciones de Django
            self.stdout.write("Limpiando migraciones de la app datamart...")
            # Borra los registros de migraciones aplicadas para esta app
            cursor.execute("DELETE FROM django_migrations WHERE app = 'datamart';")

            # Reactiva el chequeo de claves foráneas
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

        # Mensajes finales de éxito e instrucciones
        self.stdout.write(self.style.SUCCESS("¡Limpieza COMPLETA!"))
        self.stdout.write(self.style.SUCCESS("Ahora ejecuta:"))
        self.stdout.write(self.style.SUCCESS("  python manage.py migrate datamart"))