# proyecto_tesis/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from reuniones.routing import websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proyecto_tesis.settings")

django_asgi = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi,
    "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
})
