# reuniones/routing.py
from django.urls import path
from .consumers import STTConsumer

websocket_urlpatterns = [
    path("ws/transcribir/<int:reunion_id>/", STTConsumer.as_asgi()),
]