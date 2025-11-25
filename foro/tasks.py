# foro/tasks.py
from celery import shared_task
from django.conf import settings
import firebase_admin
from firebase_admin import messaging, credentials
from django.contrib.auth import get_user_model
from .models import Publicacion, Comentario
import logging

logger = logging.getLogger(__name__)

def inicializar_firebase():
    """Inicializa Firebase solo si no está activo ya"""
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
            logger.error(f"Error inicializando Firebase: {e}")

@shared_task
def notificar_nueva_publicacion(publicacion_id):
    """Avisa a TODOS (Topic) que hay un nuevo tema"""
    inicializar_firebase()
    try:
        pub = Publicacion.objects.get(pk=publicacion_id)
        
        # Enviar al Topic 'foro_general' (Todos los vecinos suscritos)
        message = messaging.Message(
            notification=messaging.Notification(
                title="Nuevo tema en el Foro",
                body=f"{pub.autor.username}: {pub.contenido[:80]}..."
            ),
            topic="foro_general",
            data={
                "tipo": "nueva_publicacion",
                "id": str(pub.id)
            }
        )
        messaging.send(message)
        return "Notificación de Publicación enviada."
    except Exception as e:
        return f"Error enviando notif publicación: {e}"

@shared_task
def notificar_nuevo_comentario(comentario_id):
    """Avisa solo al DUEÑO del post que alguien le comentó"""
    inicializar_firebase()
    try:
        comentario = Comentario.objects.select_related('publicacion__autor__perfil').get(pk=comentario_id)
        autor_post = comentario.publicacion.autor
        
        # No notificar si uno se comenta a sí mismo
        if comentario.autor == autor_post:
            return "Auto-comentario, omitido."

        # Obtener token del dueño del post
        token = getattr(autor_post.perfil, 'fcm_token', None)
        if not token:
            return "Autor del post no tiene token FCM."

        message = messaging.Message(
            notification=messaging.Notification(
                title="Nuevo comentario en tu publicación",
                body=f"{comentario.autor.username} respondió: {comentario.contenido[:80]}..."
            ),
            token=token, #  Envío directo solo a este usuario
            data={
                "tipo": "nuevo_comentario",
                "publicacion_id": str(comentario.publicacion.id)
            }
        )
        messaging.send(message)
        return "Notificación de Comentario enviada."
    except Exception as e:
        return f"Error enviando notif comentario: {e}"