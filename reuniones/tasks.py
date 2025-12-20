"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Tareas asíncronas de Celery para envío de notificaciones FCM y 
               procesamiento de audio con Vosk y FFmpeg.
--------------------------------------------------------------------------------
"""
from celery import shared_task
import time
import os
import json
import wave
import ffmpeg
import tempfile
import traceback
import logging
from django.conf import settings
from django.utils import timezone
from .models import Acta, Reunion
from core.models import Perfil, DispositivoFCM
from vosk import Model, KaldiRecognizer
import firebase_admin
from firebase_admin import messaging, credentials

logger = logging.getLogger(__name__)

VOSK_MODEL_PATH = os.path.join(settings.BASE_DIR, "vosk-model-small-es-0.42")
vosk_model = None
firebase_app = None


def inicializar_firebase(): # Inicializa Firebase SDK
    global firebase_app
    if firebase_app is not None:
        return firebase_app

    try:
        firebase_app = firebase_admin.get_app()
        return firebase_app
    except ValueError:
        pass

    project_id = getattr(settings, "FIREBASE_PROJECT_ID", None)
    client_email = getattr(settings, "FIREBASE_CLIENT_EMAIL", None)
    private_key = getattr(settings, "FIREBASE_PRIVATE_KEY", None)
    private_key_id = getattr(settings, "FIREBASE_PRIVATE_KEY_ID", "dummy")

    if not project_id or not client_email or not private_key:
        logger.error("Faltan credenciales de Firebase en settings/.env.")
        return None

    cred_info = {
        "type": "service_account",
        "project_id": project_id,
        "private_key_id": private_key_id,
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
    return firebase_app


#Tareas de notificacion
def _obtener_tokens_dispositivos():
    """
    Obtiene TODOS los tokens registrados en DispositivoFCM (multi-dispositivo).
    """
    return list(
        DispositivoFCM.objects
        .values_list("token", flat=True)
        .distinct()
    )


@shared_task
def enviar_notificacion_nueva_reunion(reunion_id): # Notif nueva reunión
    try:
        inicializar_firebase()
        reunion = Reunion.objects.get(pk=reunion_id)
        tokens = _obtener_tokens_dispositivos()
        if not tokens:
            return
        fecha_local = timezone.localtime(reunion.fecha)
        body = f"{reunion.titulo} el {fecha_local.strftime('%d/%m/%Y %H:%M')}"
        for token in tokens:
            try:
                msg = messaging.Message(
                    notification=messaging.Notification(
                        title="Nueva reunión agendada",
                        body=body
                    ),
                    token=token,
                    data={
                        "tipo": "nueva_reunion",
                        "reunion_id": str(reunion.id)
                    }
                )
                messaging.send(msg)
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error notif nueva reunion: {e}")


@shared_task
def enviar_notificacion_reunion_iniciada(reunion_id): # Notif inicio reunión
    try:
        inicializar_firebase()
        reunion = Reunion.objects.get(id=reunion_id)

        tokens = _obtener_tokens_dispositivos()
        if not tokens:
            return

        mensaje = messaging.MulticastMessage(
            notification=messaging.Notification(
                title="¡Reunión Iniciada!",
                body=f"La reunión '{reunion.titulo}' ha comenzado. ¡Únete ahora!"
            ),
            data={
                "tipo": "reunion_iniciada",
                "reunion_id": str(reunion.id),
                "click_action": "FLUTTER_NOTIFICATION_CLICK"
            },
            tokens=tokens
        )
        messaging.send_each_for_multicast(mensaje)
    except Exception as e:
        logger.error(f"Error notif inicio reunion: {e}")


@shared_task
def enviar_notificacion_reunion_finalizada(reunion_id): # Notif fin reunión
    try:
        inicializar_firebase()
        reunion = Reunion.objects.get(id=reunion_id)

        tokens = _obtener_tokens_dispositivos()
        if not tokens:
            return

        mensaje = messaging.MulticastMessage(
            notification=messaging.Notification(
                title="Reunión Finalizada",
                body=f"La reunión '{reunion.titulo}' ha finalizado."
            ),
            data={
                "tipo": "reunion_finalizada",
                "reunion_id": str(reunion.id)
            },
            tokens=tokens
        )
        messaging.send_each_for_multicast(mensaje)
    except Exception as e:
        logger.error(f"Error notif fin reunion: {e}")


@shared_task
def enviar_notificacion_acta_aprobada(acta_id): # Notif acta aprobada
    try:
        inicializar_firebase()
        acta = Acta.objects.get(pk=acta_id)
        reunion = acta.reunion

        tokens = _obtener_tokens_dispositivos()
        if not tokens:
            return

        mensaje = messaging.MulticastMessage(
            notification=messaging.Notification(
                title="Acta Disponible",
                body=f"El acta de '{reunion.titulo}' ha sido aprobada."
            ),
            data={
                "tipo": "acta_aprobada",
                "acta_id": str(acta.pk),
                "reunion_id": str(reunion.id)
            },
            tokens=tokens
        )
        messaging.send_each_for_multicast(mensaje)
    except Exception as e:
        logger.error(f"Error notif acta aprobada: {e}")


# Tarea de transcripcion con Vosk

@shared_task(name="procesar_audio_vosk")
def procesar_audio_vosk(acta_pk): # Procesamiento de audio
    global vosk_model
    try:
        if vosk_model is None:
            if not os.path.exists(VOSK_MODEL_PATH):
                raise FileNotFoundError(f"Modelo VOSK no encontrado en {VOSK_MODEL_PATH}")
            vosk_model = Model(VOSK_MODEL_PATH)

        acta = Acta.objects.get(pk=acta_pk)
        acta.estado_transcripcion = Acta.ESTADO_PROCESANDO
        acta.save()

        # Crear archivos temporales
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f_in:
            f_in.write(acta.archivo_audio.read())
            input_webm_path = f_in.name

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_out:
            output_wav_path = f_out.name

        # Convertir con FFMPEG
        (
            ffmpeg
            .input(input_webm_path)
            .output(
                output_wav_path, 
                format="wav", 
                acodec="pcm_s16le", 
                ac=1, 
                ar="16000",
                # Filtro de paso alto (quita ruidos graves) y compresión dinámica
                af="highpass=f=200, lowpass=f=3000, loudnorm" 
            )
            .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
        )

        # Transcribir
        wf = wave.open(output_wav_path, "rb")
        rec = KaldiRecognizer(vosk_model, wf.getframerate())
        rec.SetWords(True)

        full_text = ""
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                full_text += res.get("text", "") + " "

        final_res = json.loads(rec.FinalResult())
        full_text += final_res.get("text", "")
        wf.close()

        acta.contenido = full_text
        acta.estado_transcripcion = Acta.ESTADO_COMPLETADO
        acta.save()

        # Limpieza
        if os.path.exists(input_webm_path):
            os.remove(input_webm_path)
        if os.path.exists(output_wav_path):
            os.remove(output_wav_path)

        return f"Acta {acta_pk} procesada."

    except Exception as e:
        try:
            a = Acta.objects.get(pk=acta_pk)
            a.estado_transcripcion = Acta.ESTADO_ERROR
            a.save()
        except:
            pass
        return f"Error procesando: {e}"