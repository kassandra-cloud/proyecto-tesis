# core/api_fcm.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.models import Perfil, DispositivoFCM


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def registrar_fcm_token(request):
    """
    Registra o actualiza el token FCM del usuario autenticado.
    Espera JSON: { "fcm_token": "<TOKEN_FCM>", "nombre_dispositivo": "...", "plataforma": "android" }
    Los campos nombre_dispositivo y plataforma son opcionales.
    """
    fcm_token = request.data.get("fcm_token")
    nombre = request.data.get("nombre_dispositivo")
    plataforma = request.data.get("plataforma")

    if not fcm_token:
        return Response(
            {"detail": "El campo 'fcm_token' es obligatorio."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = request.user

    # 1) Registrar/actualizar el dispositivo
    dispositivo, created = DispositivoFCM.objects.update_or_create(
        token=fcm_token,
        defaults={
            "usuario": user,
            "nombre_dispositivo": nombre,
            "plataforma": plataforma,
        },
    )

    # 2) Mantener compatibilidad: seguir llenando Perfil.fcm_token
    try:
        perfil = user.perfil
        perfil.fcm_token = fcm_token
        perfil.save(update_fields=["fcm_token"])
    except Perfil.DoesNotExist:
        # Si el usuario aún no tiene perfil, solo ignoramos este paso.
        pass

    return Response(
        {
            "detail": "Token FCM registrado correctamente.",
            "created": created,
        },
        status=status.HTTP_200_OK,
    )
