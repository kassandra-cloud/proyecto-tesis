"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Utilidad de línea de comandos de Django para tareas administrativas.
               Se usa para ejecutar el servidor, realizar migraciones, crear 
               superusuarios y gestionar el proyecto en general.
--------------------------------------------------------------------------------
"""
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os  # Importa módulo del sistema operativo
import sys  # Importa módulo del sistema


def main():
    """Run administrative tasks."""
    # Establece el archivo de configuración predeterminado para el proyecto
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_tesis.settings')
    try:
        # Intenta importar la función para ejecutar comandos de Django
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # Si falla la importación, lanza un error explicativo (falta entorno virtual o Django no instalado)
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    # Ejecuta el comando pasado por argumentos en la terminal
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()  # Llama a la función principal si se ejecuta el script directamente