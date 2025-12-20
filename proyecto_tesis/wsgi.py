"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Configuración WSGI para el proyecto. Es el punto de entrada estándar 
               para servidores web compatibles con Python (como Gunicorn) en producción.
--------------------------------------------------------------------------------
"""

import os  # Importa módulo del sistema operativo

from django.core.wsgi import get_wsgi_application  # Importa la aplicación WSGI de Django

# Establece la variable de entorno que apunta a la configuración del proyecto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_tesis.settings')

# Crea la aplicación WSGI invocable
application = get_wsgi_application()