"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Define endpoints de la API REST para funcionalidades 
                       del núcleo, específicamente el registro de tokens FCM 
                       (Firebase Cloud Messaging) para notificaciones push.
--------------------------------------------------------------------------------
"""

# proyecto-tesis/core/api.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
# Importamos el modelo Perfil y DispositivoFCM para acceder y actualizar el token.
from core.models import Perfil, DispositivoFCM

# Importamos para un manejo de errores más robusto en base de datos.
from django.db import IntegrityError 

class RegistrarFCMTokenView(APIView):
    """
    Endpoint para que la app móvil registre su token FCM asociado al usuario.
    Requiere autenticación (Token DRF).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Importación local redundante pero inofensiva.
        from django.db import IntegrityError

        # Obtiene datos del cuerpo de la petición.
        token = request.data.get("fcm_token") or request.data.get("token")
        nombre = request.data.get("nombre_dispositivo")
        plataforma = request.data.get("plataforma")

        # Validación básica.
        if not token:
            return Response(
                {"error": "El campo 'fcm_token' es obligatorio."},
                status=400,
            )

        user = request.user

        try:
            # 1) Registrar/actualizar dispositivo FCM en la tabla dedicada (soporta múltiples dispositivos).
            DispositivoFCM.objects.update_or_create(
                token=token, # Busca por token.
                defaults={   # Si existe actualiza, si no crea con estos datos.
                    "usuario": user,
                    "nombre_dispositivo": nombre,
                    "plataforma": plataforma,
                },
            )

            # 2) Compatibilidad con Perfil.fcm_token (campo legacy/único dispositivo).
            # Se mantiene sincronizado el último token en el perfil principal.
            try:
                perfil = user.perfil
                perfil.fcm_token = token
                perfil.save(update_fields=["fcm_token"])
            except Perfil.DoesNotExist:
                pass # Si no hay perfil, ignora este paso (admin, etc.).

            return Response(
                {"status": "Token FCM registrado exitosamente."},
                status=200,
            )

        except IntegrityError:
            return Response(
                {"error": "Error al guardar el token (integridad de datos)."},
                status=500,
            )