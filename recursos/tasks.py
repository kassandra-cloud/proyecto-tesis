# recursos/tasks.py
from celery import shared_task
from django.conf import settings
import firebase_admin
from firebase_admin import messaging, credentials
from .models import SolicitudReserva, Recurso
import logging

logger = logging.getLogger(__name__)

def inicializar_firebase():
    """Inicializa Firebase si no está activo ya"""
    if not firebase_admin._apps:
        try:
            project_id = getattr(settings, "FIREBASE_PROJECT_ID", None)
            client_email = getattr(settings, "FIREBASE_CLIENT_EMAIL", None)
            private_key = getattr(settings, "FIREBASE_PRIVATE_KEY", None)
            
            if project_id and client_email and private_key:
                cred = credentials.Certificate({
                    "type": "service_account",
                    "project_id": project_id,
                    "private_key_id": getattr(settings, "FIREBASE_PRIVATE_KEY_ID", "dummy"),
                    "private_key": private_key.replace("\\n", "\n"),
                    "client_email": client_email,
                    "client_id": "dummy",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email}",
                })
                firebase_admin.initialize_app(cred)
        except Exception as e:
            logger.error(f"Error inicializando Firebase en Recursos: {e}")

@shared_task
def notificar_actualizacion_solicitud(solicitud_id):
    """
    Notifica al solicitante que el estado de su solicitud ha cambiado (Aprobada/Rechazada).
    """
    inicializar_firebase()
    try:
        # 🔹 CORRECCIÓN: Usamos 'solicitante' en lugar de 'vecino'
        solicitud = SolicitudReserva.objects.select_related('solicitante__perfil', 'recurso').get(pk=solicitud_id)
        usuario = solicitud.solicitante
        
        # Obtener token del usuario
        token = getattr(usuario.perfil, 'fcm_token', None)
        if not token:
            return f"Usuario {usuario.username} no tiene token FCM registrado."

        # Texto del estado para mostrar (ej: APROBADA -> Aprobada)
        estado_legible = solicitud.get_estado_display()

        # Construcción del mensaje
        message = messaging.Message(
            notification=messaging.Notification(
                title="Solicitud Actualizada",
                body=f"Tu solicitud para '{solicitud.recurso.nombre}' ha sido {estado_legible}. Revisa los detalles en la app."
            ),
            token=token,
            data={
                "tipo": "actualizacion_solicitud",
                "solicitud_id": str(solicitud.id),
                "nuevo_estado": str(solicitud.estado)
            }
        )
        
        # Enviar
        response = messaging.send(message)
        return f"Notificación enviada a {usuario.username}. ID: {response}"

    except SolicitudReserva.DoesNotExist:
        return f"Solicitud {solicitud_id} no encontrada."
    except Exception as e:
        return f"Error enviando notificación de recurso: {e}"

@shared_task
def notificar_nuevo_recurso(recurso_id):
    """Avisa a TODOS que hay un nuevo recurso disponible"""
    inicializar_firebase()
    try:
        recurso = Recurso.objects.get(pk=recurso_id)
        
        message = messaging.Message(
            notification=messaging.Notification(
                title="¡Nuevo Recurso Disponible!",
                body=f"Ahora puedes reservar: {recurso.nombre}"
            ),
            topic="recursos_generales",
            data={
                "tipo": "nuevo_recurso",
                "recurso_id": str(recurso.id)
            }
        )
        messaging.send(message)
        return "Notificación de nuevo recurso enviada."
    except Exception as e:
        return f"Error enviando notif nuevo recurso: {e}"