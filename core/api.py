# proyecto-tesis/core/api.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
# Importamos el modelo Perfil para acceder y actualizar el token
from core.models import Perfil, DispositivoFCM

from django.db import IntegrityError # Importamos para un manejo de errores más robusto
class RegistrarFCMTokenView(APIView):
    """
    Endpoint para que la app móvil registre su token FCM asociado al usuario.
    Requiere autenticación (Token DRF).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        from django.db import IntegrityError

        token = request.data.get("fcm_token") or request.data.get("token")
        nombre = request.data.get("nombre_dispositivo")
        plataforma = request.data.get("plataforma")

        if not token:
            return Response(
                {"error": "El campo 'fcm_token' es obligatorio."},
                status=400,
            )

        user = request.user

        try:
            # 1) Registrar/actualizar dispositivo FCM
            DispositivoFCM.objects.update_or_create(
                token=token,
                defaults={
                    "usuario": user,
                    "nombre_dispositivo": nombre,
                    "plataforma": plataforma,
                },
            )

            # 2) Compatibilidad con Perfil.fcm_token
            try:
                perfil = user.perfil
                perfil.fcm_token = token
                perfil.save(update_fields=["fcm_token"])
            except Perfil.DoesNotExist:
                pass

            return Response(
                {"status": "Token FCM registrado exitosamente."},
                status=200,
            )

        except IntegrityError:
            return Response(
                {"error": "Error al guardar el token (integridad de datos)."},
                status=500,
            )