from celery import shared_task
import time

# --- IMPORTS EXISTENTES (VOSK/Audio) ---
import os
import json
import wave
import ffmpeg  # Para convertir .webm a .wav
import tempfile  # Para guardar archivos temporalmente
import traceback  # Para ver errores completos

from django.conf import settings

from .models import Acta, Reunion  # Modelos de esta app
from core.models import Perfil      # Para obtener fcm_token desde Perfil

# --- LIBRERÍAS DE VOSK ---
from vosk import Model, KaldiRecognizer

# --- IMPORTS FCM ---
import firebase_admin
from firebase_admin import messaging, credentials
from django.utils import timezone
import logging

# -----------------------------
# --- LOGGING / VOSK MODEL ---
logger = logging.getLogger(__name__)

VOSK_MODEL_PATH = os.path.join(settings.BASE_DIR, "vosk-model-small-es-0.42")
vosk_model = None

# -----------------------------
# --- CACHE PARA FIREBASE ---
firebase_app = None


def inicializar_firebase():
    """
    Inicializa Firebase Admin usando variables de settings (que vienen de .env).
    Si ya está inicializado, solo devuelve la app existente.
    """
    global firebase_app

    # 1) Si ya la tenemos cacheada, la usamos
    if firebase_app is not None:
        return firebase_app

    # 2) Si ya hay alguna app por defecto creada, la reutilizamos
    try:
        firebase_app = firebase_admin.get_app()
        return firebase_app
    except ValueError:
        # No había app, la creamos más abajo
        pass

    # 3) Leemos las variables desde settings (que tú cargarás desde .env)
    project_id = getattr(settings, "FIREBASE_PROJECT_ID", None)
    client_email = getattr(settings, "FIREBASE_CLIENT_EMAIL", None)
    private_key = getattr(settings, "FIREBASE_PRIVATE_KEY", None)
    private_key_id = getattr(settings, "FIREBASE_PRIVATE_KEY_ID", "dummy")

    if not project_id or not client_email or not private_key:
        logger.error(
            "Faltan credenciales de Firebase. "
            "Debes configurar FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL y FIREBASE_PRIVATE_KEY "
            "en settings/.env."
        )
        raise RuntimeError(
            "Faltan credenciales de Firebase (FIREBASE_*). Revisa tu .env y settings."
        )

    cred_info = {
        "type": "service_account",
        "project_id": project_id,
        "private_key_id": private_key_id,
        # En el .env suele ir con '\\n', aquí lo convertimos a saltos de línea reales
        "private_key": private_key.replace("\\n", "\n"),
        "client_email": client_email,
        "client_id": "dummy",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email}",
    }

    cred = credentials.Certificate(cred_info)
    firebase_app = firebase_admin.initialize_app(cred)
    logger.info("Firebase Admin SDK inicializado desde variables de entorno/.env.")
    return firebase_app


# -----------------------------------------------------------------
# NOTIFICACIONES FCM
# -----------------------------------------------------------------
@shared_task
def enviar_notificacion_nueva_reunion(reunion_id):
    """
    Envía una notificación FCM a todos los perfiles que tengan fcm_token,
    usando messaging.send() uno por uno (compatible con versiones antiguas).
    """
    # 0) Inicializar Firebase
    try:
        inicializar_firebase()
    except Exception as e:
        logger.error(f"ERROR al inicializar Firebase en Celery: {e}", exc_info=True)
        return

    # 1) Leer tokens FCM
    tokens = list(
        Perfil.objects
        .exclude(fcm_token__isnull=True)
        .exclude(fcm_token="")
        .values_list("fcm_token", flat=True)
    )

    if not tokens:
        logger.warning("No hay tokens de FCM registrados para enviar la notificación.")
        return

    # 2) Obtener la reunión
    try:
        reunion = Reunion.objects.get(pk=reunion_id)
    except Reunion.DoesNotExist:
        logger.error(f"Reunión con id={reunion_id} no existe. No se envía notificación.")
        return

    # 3) Enviar una notificación por token
    title = "Nueva reunión agendada"
    fecha_local = timezone.localtime(reunion.fecha)
    body = f"{reunion.titulo} el {fecha_local.strftime('%d/%m/%Y %H:%M')}"

    exito = 0
    fallo = 0

    for token in tokens:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=token,
            data={
                "tipo": "nueva_reunion",
                "reunion_id": str(reunion.id),
            },
        )
        try:
            messaging.send(message)
            exito += 1
        except Exception as e:
            fallo += 1
            logger.error(
                f"Error al enviar notificación a token {token}: {e}", exc_info=True
            )

    logger.info(f"Notificaciones enviadas. Éxito: {exito}, Fallos: {fallo}")


@shared_task
def enviar_notificacion_reunion_finalizada(reunion_id):
    """
    Notifica a los usuarios cuando una reunión cambia a estado REALIZADA.
    """
    try:
        # Aseguramos inicialización de Firebase
        inicializar_firebase()
        
        reunion = Reunion.objects.get(id=reunion_id)
        
        # Obtenemos los tokens de todos los usuarios que tengan uno registrado
        tokens = list(Perfil.objects.exclude(fcm_token__isnull=True)
                                    .exclude(fcm_token="")
                                    .values_list("fcm_token", flat=True))

        if not tokens:
            print("No hay tokens FCM registrados para enviar notificación.")
            return

        # Creamos el mensaje Multicast
        mensaje = messaging.MulticastMessage(
            notification=messaging.Notification(
                title="Reunión Finalizada",
                body=f"La reunión '{reunion.titulo}' ha finalizado. Revisa los detalles en la app."
            ),
            data={
                "tipo": "reunion_finalizada",
                "reunion_id": str(reunion.id),
                "click_action": "FLUTTER_NOTIFICATION_CLICK"
            },
            tokens=tokens
        )

        response = messaging.send_each_for_multicast(mensaje)
        print(f"[FCM] Notificación de finalización enviada. Éxitos: {response.success_count}")

    except Reunion.DoesNotExist:
        print(f"Reunión {reunion_id} no encontrada.")
    except Exception as e:
        print(f"Error enviando notificación FCM: {e}")


@shared_task  # <--- ESTA ES LA NUEVA TAREA QUE NECESITAS
def enviar_notificacion_reunion_iniciada(reunion_id):
    """
    Notifica a los usuarios cuando una reunión cambia a estado EN_CURSO.
    """
    try:
        # Aseguramos inicialización de Firebase
        inicializar_firebase()
        
        reunion = Reunion.objects.get(id=reunion_id)
        
        # Obtenemos los tokens de todos los usuarios que tengan uno registrado
        tokens = list(Perfil.objects.exclude(fcm_token__isnull=True)
                                    .exclude(fcm_token="")
                                    .values_list("fcm_token", flat=True))

        if not tokens:
            print("No hay tokens FCM registrados para enviar notificación.")
            return

        # Creamos el mensaje Multicast
        mensaje = messaging.MulticastMessage(
            notification=messaging.Notification(
                title="¡Reunión Iniciada!",
                body=f"La reunión '{reunion.titulo}' ha comenzado. ¡Únete ahora!"
            ),
            data={
                "tipo": "reunion_iniciada",  # Clave para identificar el tipo en Android
                "reunion_id": str(reunion.id),
                "click_action": "FLUTTER_NOTIFICATION_CLICK"
            },
            tokens=tokens
        )

        response = messaging.send_each_for_multicast(mensaje)
        print(f"[FCM] Notificación de inicio enviada. Éxitos: {response.success_count}")

    except Reunion.DoesNotExist:
        print(f"Reunión {reunion_id} no encontrada.")
    except Exception as e:
        print(f"Error enviando notificación FCM: {e}")


# -----------------------------------------------------------------
# TAREA DE PRUEBA (Suma)
# -----------------------------------------------------------------
@shared_task(name="test_celery_suma")
def test_celery_suma(x, y):
    """
    Tarea de prueba para verificar que Celery está funcionando.
    """
    print(f"[TAREA RECIBIDA]: Sumando {x} + {y}...")
    time.sleep(3)
    resultado = x + y
    print(f"[TAREA COMPLETADA]: Resultado = {resultado}")
    return resultado


# -----------------------------------------------------------------
# TAREA DE TRANSCRIPCIÓN CON VOSK
# -----------------------------------------------------------------
@shared_task(name="procesar_audio_vosk")
def procesar_audio_vosk(acta_pk):
    """
    Tarea de Celery para procesar un archivo de audio de un acta
    usando VOSK y actualizar el contenido del acta.
    """
    global vosk_model

    # --- CARGA PEREZOSA DEL MODELO ---
    if vosk_model is None:
        try:
            print(f"[Worker {acta_pk}]: Cargando modelo VOSK (solo esta vez)...")
            if not os.path.exists(VOSK_MODEL_PATH):
                print(
                    f"ERROR: No se pudo cargar el modelo VOSK. "
                    f"Ruta no encontrada: {VOSK_MODEL_PATH}"
                )
                raise FileNotFoundError(
                    f"Ruta de modelo VOSK no encontrada: {VOSK_MODEL_PATH}"
                )

            vosk_model = Model(VOSK_MODEL_PATH)
            print(f"[Worker {acta_pk}]: Modelo VOSK cargado en memoria.")

        except Exception as e:
            print(
                f"ERROR CRÍTICO: No se pudo cargar el modelo VOSK desde "
                f"{VOSK_MODEL_PATH}."
            )
            print(f"Error original: {e}")
            try:
                acta_error = Acta.objects.get(pk=acta_pk)
                acta_error.estado_transcripcion = Acta.ESTADO_ERROR
                acta_error.save()
            except Acta.DoesNotExist:
                pass
            return f"Error: Modelo VOSK no pudo ser cargado."

    # --- Búsqueda de Acta ---
    try:
        acta = Acta.objects.get(pk=acta_pk)
    except Acta.DoesNotExist:
        print(f"Error en tarea: No se encontró el Acta con pk={acta_pk}. Abortando.")
        return f"Error: Acta {acta_pk} no encontrada."

    # 1. Marcar el acta como "PROCESANDO"
    acta.estado_transcripcion = Acta.ESTADO_PROCESANDO
    acta.save()
    print(f"[TAREA INICIADA]: Procesando audio para Acta {acta_pk}...")

    # --- MANEJO DE ARCHIVOS TEMPORALES ---
    input_webm_path = None
    output_wav_path = None

    try:
        # 2. Archivo de entrada (.webm)
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f_in:
            f_in.write(acta.archivo_audio.read())
            input_webm_path = f_in.name

        print(f"[Acta {acta_pk}]: Audio guardado en {input_webm_path}")

        # 3. Archivo de salida (.wav)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_out:
            output_wav_path = f_out.name

        print(f"[Acta {acta_pk}]: Archivo de salida temporal: {output_wav_path}")

        # 4. Convertir .webm a .wav
        print(f"[Acta {acta_pk}]: Iniciando conversión de .webm a .wav...")
        (
            ffmpeg
            .input(input_webm_path)
            .output(
                output_wav_path,
                format="wav",
                acodec="pcm_s16le",
                ac=1,
                ar="16000",
            )
            .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
        )
        print(f"[Acta {acta_pk}]: Conversión a .wav completada.")

        # 5. Abrir el .wav y transcribir con VOSK
        print(f"[Acta {acta_pk}]: Iniciando transcripción VOSK...")
        wf = wave.open(output_wav_path, "rb")
        if (
            wf.getnchannels() != 1
            or wf.getsampwidth() != 2
            or wf.getcomptype() != "NONE"
        ):
            print("Error: El archivo WAV no está en formato mono 16-bit PCM.")
            raise Exception("Formato de audio incorrecto, se requiere mono 16-bit PCM.")

        recognizer = KaldiRecognizer(vosk_model, wf.getframerate())
        recognizer.SetWords(True)

        full_text = ""

        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                full_text += result.get("text", "") + " "

        final_result = json.loads(recognizer.FinalResult())
        full_text += final_result.get("text", "")

        wf.close()
        print(f"[Acta {acta_pk}]: Transcripción VOSK finalizada.")

        # 6. Actualizar el acta
        acta.contenido = full_text
        acta.estado_transcripcion = Acta.ESTADO_COMPLETADO
        acta.save()

        print(f"[TAREA COMPLETADA]: Acta {acta_pk} actualizada con éxito.")
        return f"Acta {acta_pk} procesada con éxito."

    except Exception as e:
        print(f"!!! ERROR en Tarea {acta_pk}: {e} !!!")

        if isinstance(e, ffmpeg.Error):
            print(f"STDOUT FFMPEG: {e.stdout.decode('utf8', errors='ignore')}")
            print(f"STDERR FFMPEG: {e.stderr.decode('utf8', errors='ignore')}")
        else:
            traceback.print_exc()

        acta.estado_transcripcion = Acta.ESTADO_ERROR
        acta.save()
        return f"Error procesando Acta {acta_pk}: {e}"

    finally:
        # 8. Limpieza
        print(f"[Acta {acta_pk}]: Limpiando archivos temporales...")
        try:
            if input_webm_path and os.path.exists(input_webm_path):
                os.remove(input_webm_path)
                print(f" - Borrado: {input_webm_path}")
            if output_wav_path and os.path.exists(output_wav_path):
                os.remove(output_wav_path)
                print(f" - Borrado: {output_wav_path}")
        except Exception as e:
            print(f"Error durante la limpieza de archivos: {e}")