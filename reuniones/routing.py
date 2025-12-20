"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Definición de rutas URL para WebSockets, mapeando la URL de 
               transcripción al consumidor correspondiente.
--------------------------------------------------------------------------------
"""
# reuniones/routing.py
from django.urls import path
from .consumers import STTConsumer

websocket_urlpatterns = [
    path("ws/transcribir/<int:reunion_id>/", STTConsumer.as_asgi()), # Ruta WS para transcripción
]