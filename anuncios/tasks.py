# anuncios/tasks.py
from celery import shared_task
from django.conf import settings
import firebase_admin
from firebase_admin import messaging, credentials
from .models import Anuncio
import logging

logger = logging.getLogger(__name__)

# --- Reutilizamos la lógica de inicialización segura ---
def inicializar_firebase():
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
                logger.info("✅ Firebase inicializado en tarea de Anuncios.")
        except Exception as e:
            logger.error(f"Error inicializando Firebase: {e}")

@shared_task
def enviar_notificacion_nuevo_anuncio(anuncio_id):
    """
    Envía una notificación al TOPIC 'anuncios_generales' cuando se crea un anuncio.
    """
    try:
        inicializar_firebase()
        
        # Recuperamos el objeto anuncio de la BD
        try:
            anuncio = Anuncio.objects.get(pk=anuncio_id)
        except Anuncio.DoesNotExist:
            logger.warning(f"Anuncio {anuncio_id} no encontrado. Omitiendo notificación.")
            return

        # Preparamos el mensaje al TEMA (Topic)
        message = messaging.Message(
            notification=messaging.Notification(
                title=f"Nuevo Anuncio: {anuncio.titulo}",
                body=f"{anuncio.contenido[:100]}..." # Primeros 100 caracteres
            ),
            topic="anuncios_generales", # <--- ¡Importante! Coincide con Android
            data={
                "tipo": "nuevo_anuncio",
                "anuncio_id": str(anuncio.id)
            }
        )

        # Enviamos
        response = messaging.send(message)
        print(f"✅ [Celery] Notificación de Anuncio enviada al Topic. ID: {response}")
        return response

    except Exception as e:
        print(f"❌ [Celery] Error enviando anuncio: {e}")
        # Opcional: self.retry(exc=e, countdown=60)