# proyecto-tesis/core/api.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
# Importamos el modelo Perfil para acceder y actualizar el token
from core.models import Perfil 
from django.db import IntegrityError # Importamos para un manejo de errores más robusto

class RegistrarFCMTokenView(APIView):
    """
    Endpoint para que la app movil registre su token FCM asociado al usuario.
    Requiere autenticación (Bearer Token / JWT)
    """
    # Solo usuarios autenticados pueden usar esta vista
    permission_classes = [IsAuthenticated] 

    def post(self, request, *args, **kwargs):
        # El token FCM se espera en el cuerpo de la petición con la clave 'fcm_token'
        token = request.data.get("fcm_token") 

        if not token:
            return Response({"error": "El campo 'fcm_token' es requerido."}, status=400)
        
        try:
            # Accedemos al perfil del usuario autenticado
            perfil = request.user.perfil 
            
            # Almacena el token
            perfil.fcm_token = token
            perfil.save(update_fields=['fcm_token'])
            
            return Response({"status": "Token FCM registrado exitosamente."}, status=200)
        
        except AttributeError:
            # Si el usuario no tiene perfil (OneToOneField falla)
            return Response({"error": "Usuario autenticado no tiene un perfil asociado."}, status=400)
        except Perfil.DoesNotExist:
            # Si la consulta al perfil falla (aunque con request.user.perfil es poco probable)
            return Response({"error": "Perfil de usuario no encontrado."}, status=400)
        except IntegrityError:
            # Si hay un problema de base de datos (ej. token demasiado largo, aunque max_length=255 debería cubrirlo)
            return Response({"error": "Error al guardar el token debido a un problema de integridad de datos."}, status=500)