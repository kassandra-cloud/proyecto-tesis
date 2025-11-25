# votaciones/tasks.py
from celery import shared_task
from django.conf import settings
import firebase_admin
from firebase_admin import messaging, credentials
from .models import Votacion
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
            logger.error(f"Error inicializando Firebase en Votaciones: {e}")

@shared_task
def notificar_nueva_votacion(votacion_id):
    """
    Avisa a todos los vecinos que hay una nueva votación disponible.
    """
    inicializar_firebase()
    try:
        votacion = Votacion.objects.get(pk=votacion_id)
        
        # Formateamos la fecha de cierre para que sea legible
        cierre_str = votacion.fecha_cierre.strftime("%d/%m %H:%M")

        # Mensaje al Tópico General
        message = messaging.Message(
            notification=messaging.Notification(
                title="¡Nueva Votación!",
                body=f"{votacion.pregunta}\nCierra el: {cierre_str}"
            ),
            topic="votaciones_generales", # <--- Tópico específico
            data={
                "tipo": "nueva_votacion",
                "votacion_id": str(votacion.id)
            }
        )
        
        response = messaging.send(message)
        return f"Notificación Votación enviada. ID: {response}"

    except Votacion.DoesNotExist:
        return f"Votación {votacion_id} no encontrada."
    except Exception as e:
        return f"Error enviando notif votación: {e}"