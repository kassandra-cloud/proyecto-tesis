# talleres/tasks.py
from celery import shared_task
from django.conf import settings
import firebase_admin
from firebase_admin import messaging, credentials
from .models import Taller
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
            logger.error(f"Error inicializando Firebase en Talleres: {e}")

@shared_task
def notificar_nuevo_taller(taller_id):
    """Notifica creación de taller"""
    inicializar_firebase()
    try:
        taller = Taller.objects.get(pk=taller_id)
        fecha_str = taller.fecha_inicio.strftime("%d/%m %H:%M")

        message = messaging.Message(
            notification=messaging.Notification(
                title="¡Nuevo Taller Disponible!",
                body=f"{taller.nombre}\nInicio: {fecha_str}"
            ),
            topic="talleres_generales",
            data={
                "tipo": "nuevo_taller",
                "taller_id": str(taller.id)
            }
        )
        messaging.send(message)
        return f"Notificación Nuevo Taller enviada."
    except Exception as e:
        return f"Error enviando notif taller: {e}"

# 👇 NUEVA TAREA AGREGADA
@shared_task
def notificar_cancelacion_taller(taller_id):
    """Notifica cancelación de taller"""
    inicializar_firebase()
    try:
        taller = Taller.objects.get(pk=taller_id)
        
        motivo = taller.motivo_cancelacion if taller.motivo_cancelacion else "Sin motivo especificado."

        message = messaging.Message(
            notification=messaging.Notification(
                title="Taller Cancelado ",
                body=f"El taller '{taller.nombre}' ha sido suspendido.\nMotivo: {motivo}"
            ),
            topic="talleres_generales", # Usamos el mismo canal general
            data={
                "tipo": "cancelacion_taller",
                "taller_id": str(taller.id)
            }
        )
        messaging.send(message)
        return f"Notificación Cancelación Taller enviada."
    except Exception as e:
        return f"Error enviando notif cancelacion: {e}"