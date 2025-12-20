"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Configuración ASGI para el proyecto. Permite manejar tanto 
               peticiones HTTP tradicionales (Django) como conexiones WebSocket 
               (Channels) para funcionalidades en tiempo real.
--------------------------------------------------------------------------------
"""
import os  # Importa el módulo para interactuar con el sistema operativo
from django.core.asgi import get_asgi_application  # Importa la aplicación ASGI estándar de Django
from channels.routing import ProtocolTypeRouter, URLRouter  # Importa enrutadores para manejar diferentes protocolos
from channels.auth import AuthMiddlewareStack  # Middleware para gestionar autenticación en WebSockets
from reuniones.routing import websocket_urlpatterns  # Importa las rutas de WebSockets definidas en la app 'reuniones'

# Establece la variable de entorno que apunta al archivo de configuración de Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proyecto_tesis.settings")

# Inicializa la aplicación ASGI para manejar peticiones HTTP
django_asgi = get_asgi_application()

# Define el enrutador principal de protocolos
application = ProtocolTypeRouter({
    "http": django_asgi,  # Si el protocolo es HTTP, usa la aplicación Django estándar
    "websocket": AuthMiddlewareStack(  # Si es WebSocket, envuelve en autenticación...
        URLRouter(websocket_urlpatterns)  # ...y enruta según las URLs definidas
    ),
})