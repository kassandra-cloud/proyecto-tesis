"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Este archivo define la vista de API 'registrar_fcm_token'.
                       Permite a los dispositivos móviles (Android/iOS) enviar 
                       su token de Firebase Cloud Messaging (FCM) al backend 
                       para recibir notificaciones push. Mantiene compatibilidad 
                       dual guardando el token tanto en la tabla de dispositivos 
                       como en el perfil del usuario.
--------------------------------------------------------------------------------
"""

# Importa decoradores de DRF para definir vistas basadas en funciones y permisos.
from rest_framework.decorators import api_view, permission_classes
# Importa la clase de permiso para asegurar que solo usuarios logueados accedan.
from rest_framework.permissions import IsAuthenticated
# Importa objetos para construir respuestas HTTP estandarizadas.
from rest_framework.response import Response
from rest_framework import status

# Importa los modelos necesarios de la aplicación core.
from core.models import Perfil, DispositivoFCM


# Define que esta vista solo acepta peticiones HTTP POST.
@api_view(["POST"])
# Exige autenticación (el usuario debe enviar un token válido en el header).
@permission_classes([IsAuthenticated])
def registrar_fcm_token(request):
    """
    Registra o actualiza el token FCM del usuario autenticado.
    Espera JSON: { "fcm_token": "<TOKEN_FCM>", "nombre_dispositivo": "...", "plataforma": "android" }
    Los campos nombre_dispositivo y plataforma son opcionales.
    """
    # Extrae el token del cuerpo de la petición (JSON).
    fcm_token = request.data.get("fcm_token")
    # Extrae datos opcionales del dispositivo.
    nombre = request.data.get("nombre_dispositivo")
    plataforma = request.data.get("plataforma")

    # Validación: El token es obligatorio para que esto funcione.
    if not fcm_token:
        return Response(
            {"detail": "El campo 'fcm_token' es obligatorio."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Obtiene el objeto usuario desde la request (ya autenticado).
    user = request.user

    # 1) Registrar/actualizar el dispositivo en la tabla dedicada 'DispositivoFCM'.
    # update_or_create busca un registro con ese token. 
    # Si existe, actualiza los campos en 'defaults'. Si no, lo crea.
    dispositivo, created = DispositivoFCM.objects.update_or_create(
        token=fcm_token,
        defaults={
            "usuario": user,
            "nombre_dispositivo": nombre,
            "plataforma": plataforma,
        },
    )

    # 2) Mantener compatibilidad: seguir llenando Perfil.fcm_token (Legacy).
    # Esto asegura que el código antiguo que busca el token en el Perfil siga funcionando.
    try:
        perfil = user.perfil
        perfil.fcm_token = fcm_token
        # Optimización: Solo guarda el campo 'fcm_token', no todo el perfil.
        perfil.save(update_fields=["fcm_token"])
    except Perfil.DoesNotExist:
        # Si el usuario es un administrador o superusuario sin perfil vecinal, 
        # ignoramos este paso sin romper la ejecución.
        pass

    # Retorna una respuesta exitosa (200 OK) confirmando la acción.
    return Response(
        {
            "detail": "Token FCM registrado correctamente.",
            "created": created, # Booleano: True si se creó nuevo, False si se actualizó.
        },
        status=status.HTTP_200_OK,
    )