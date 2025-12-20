"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Define tareas asíncronas de Celery para la aplicación.
                       Maneja la lógica de conexión con Firebase Admin SDK para
                       enviar notificaciones push a dispositivos móviles cuando
                       se crea un anuncio.
--------------------------------------------------------------------------------
"""

# Importa el decorador shared_task de Celery.
from celery import shared_task
# Importa la configuración de Django.
from django.conf import settings
# Importa las librerías de Firebase Admin.
import firebase_admin
from firebase_admin import messaging, credentials
# Importa el modelo Anuncio.
from .models import Anuncio
# Importa logging para registrar eventos del sistema.
import logging

# Obtiene una instancia del logger.
logger = logging.getLogger(__name__)

# --- Función auxiliar para inicializar Firebase de forma segura ---
def inicializar_firebase():
    """Verifica si la app de Firebase ya está inicializada, si no, la inicia."""
    if not firebase_admin._apps:
        try:
            # Obtiene credenciales desde settings.py (variables de entorno).
            project_id = getattr(settings, "FIREBASE_PROJECT_ID", None)
            client_email = getattr(settings, "FIREBASE_CLIENT_EMAIL", None)
            private_key = getattr(settings, "FIREBASE_PRIVATE_KEY", None)
            
            # Si existen todas las credenciales necesarias.
            if project_id and client_email and private_key:
                # Crea el objeto de certificado.
                cred = credentials.Certificate({
                    "type": "service_account",
                    "project_id": project_id,
                    "private_key_id": getattr(settings, "FIREBASE_PRIVATE_KEY_ID", "dummy"),
                    "private_key": private_key.replace("\\n", "\n"), # Corrige saltos de línea.
                    "client_email": client_email,
                    "client_id": "dummy",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email}",
                })
                # Inicializa la app con las credenciales.
                firebase_admin.initialize_app(cred)
                logger.info("Firebase inicializado en tarea de Anuncios.")
        except Exception as e:
            logger.error(f"Error inicializando Firebase: {e}")

# Tarea compartida de Celery para enviar la notificación.
@shared_task
def enviar_notificacion_nuevo_anuncio(anuncio_id):
    """
    Envía una notificación al TOPIC 'anuncios_generales' de Firebase Cloud Messaging.
    """
    try:
        # Asegura que Firebase esté listo.
        inicializar_firebase()
        
        # Intenta recuperar el anuncio de la base de datos usando el ID.
        try:
            anuncio = Anuncio.objects.get(pk=anuncio_id)
        except Anuncio.DoesNotExist:
            logger.warning(f"Anuncio {anuncio_id} no encontrado. Omitiendo notificación.")
            return

        # Construye el mensaje para FCM.
        message = messaging.Message(
            # Configura título y cuerpo visible de la notificación.
            notification=messaging.Notification(
                title=f"Nuevo Anuncio: {anuncio.titulo}",
                body=f"{anuncio.contenido[:100]}..." # Trunca el contenido a 100 caracteres.
            ),
            topic="anuncios_generales", # Define el tema al que se suscriben los móviles.
            # Datos adicionales invisibles para procesar en la app móvil.
            data={
                "tipo": "nuevo_anuncio",
                "anuncio_id": str(anuncio.id)
            }
        )

        # Envía el mensaje a través de Firebase.
        response = messaging.send(message)
        print(f"[Celery] Notificación de Anuncio enviada al Topic. ID: {response}")
        return response

    except Exception as e:
        print(f"[Celery] Error enviando anuncio: {e}")
        # En caso de error, se podría reintentar descomentando la línea siguiente:
        # self.retry(exc=e, countdown=60)