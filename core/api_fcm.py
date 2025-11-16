# core/api_fcm.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.models import Perfil


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def registrar_fcm_token(request):
    """
    Registra o actualiza el token FCM del usuario autenticado.
    Espera JSON: { "fcm_token": "<TOKEN_FCM>" }
    """
    fcm_token = request.data.get("fcm_token")

    if not fcm_token:
        return Response(
            {"detail": "Falta 'fcm_token' en el cuerpo de la petición."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Aquí manejamos el caso "User has no perfil"
    try:
        perfil = request.user.perfil
    except Perfil.DoesNotExist:
        return Response(
            {"detail": "El usuario autenticado no tiene Perfil asociado."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    perfil.fcm_token = fcm_token
    perfil.save(update_fields=["fcm_token"])

    return Response(
        {"detail": "Token FCM registrado correctamente."},
        status=status.HTTP_200_OK,
    )
