# reuniones/tasks.py
from celery import shared_task
import time

# --- ¡AÑADE TODOS ESTOS IMPORTS NUEVOS! ---
import os
import json
import wave
import ffmpeg # Para convertir .webm a .wav
import tempfile # Para guardar archivos temporalmente
import traceback # Para ver errores completos
from django.conf import settings
from .models import Acta

# --- LIBRERÍAS DE VOSK ---
from vosk import Model, KaldiRecognizer

# --- 1. CONFIGURA LA RUTA A TU MODELO VOSK ---
VOSK_MODEL_PATH = os.path.join(settings.BASE_DIR, "vosk-model-small-es-0.42")

# --- 2. ¡ARREGLO! NO CARGUES EL MODELO AQUÍ ---
vosk_model = None

# -----------------------------------------------------------------
# TAREA DE PRUEBA (ya la tenías)
# -----------------------------------------------------------------
@shared_task(name="test_celery_suma")
def test_celery_suma(x, y):
    # ... (tu tarea de suma) ...
    print(f"[TAREA RECIBIDA]: Sumando {x} + {y}...")
    time.sleep(3) 
    resultado = x + y
    print(f"[TAREA COMPLETADA]: Resultado = {resultado}")
    return resultado

# -----------------------------------------------------------------
# ¡TAREA DE TRANSCRIPCIÓN (CORREGIDA)!
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
                print(f"ERROR: No se pudo cargar el modelo VOSK. Ruta no encontrada: {VOSK_MODEL_PATH}")
                raise FileNotFoundError(f"Ruta de modelo VOSK no encontrada: {VOSK_MODEL_PATH}")
                
            vosk_model = Model(VOSK_MODEL_PATH)
            print(f"[Worker {acta_pk}]: Modelo VOSK cargado en memoria.")
            
        except Exception as e:
            print(f"ERROR CRÍTICO: No se pudo cargar el modelo VOSK desde {VOSK_MODEL_PATH}.")
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

    # --- MANEJO DE ARCHIVOS TEMPORALES (CORREGIDO PARA WINDOWS) ---
    input_webm_path = None
    output_wav_path = None

    try:
        # 2. Archivo de entrada (.webm)
        #    Creamos, escribimos, y CERRAMOS (para desbloquearlo)
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f_in:
            f_in.write(acta.archivo_audio.read())
            input_webm_path = f_in.name
        
        print(f"[Acta {acta_pk}]: Audio de S3 guardado en {input_webm_path}")

        # 3. Archivo de salida (.wav)
        #    Solo creamos un nombre de archivo temporal y lo cerramos.
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_out:
            output_wav_path = f_out.name
            
        print(f"[Acta {acta_pk}]: Archivo de salida temporal: {output_wav_path}")

        # 4. Convertir .webm a .wav (¡Archivos desbloqueados!)
        print(f"[Acta {acta_pk}]: Iniciando conversión de .webm a .wav...")
        (
            ffmpeg
            .input(input_webm_path) # Usamos la RUTA
            .output(output_wav_path, format='wav', acodec='pcm_s16le', ac=1, ar='16000') # Usamos la RUTA
            .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
        )
        print(f"[Acta {acta_pk}]: Conversión a .wav completada.")

        # 5. Abrir el .wav y transcribir con VOSK
        print(f"[Acta {acta_pk}]: Iniciando transcripción VOSK...")
        wf = wave.open(output_wav_path, "rb") # Leemos el WAV convertido
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            print(f"Error: El archivo WAV no está en formato mono 16-bit PCM.")
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
                full_text += result.get('text', '') + " "

        final_result = json.loads(recognizer.FinalResult())
        full_text += final_result.get('text', '')
        
        wf.close()
        print(f"[Acta {acta_pk}]: Transcripción VOSK finalizada.")

        # 6. Actualizar el acta en la Base de Datos
        acta.contenido = full_text
        acta.estado_transcripcion = Acta.ESTADO_COMPLETADO
        acta.save()
        
        print(f"[TAREA COMPLETADA]: Acta {acta_pk} actualizada con éxito.")
        return f"Acta {acta_pk} procesada con éxito."

    except Exception as e:
        # 7. Manejo de Errores
        print(f"!!! ERROR en Tarea {acta_pk}: {e} !!!")
        
        # Imprimir detalles si fue un error de FFMPEG
        if isinstance(e, ffmpeg.Error):
            print(f"STDOUT FFMPEG: {e.stdout.decode('utf8', errors='ignore')}")
            print(f"STDERR FFMPEG: {e.stderr.decode('utf8', errors='ignore')}")
        else:
            # Imprimir el error completo si fue de Python (ej. Vosk, DB)
            traceback.print_exc()

        acta.estado_transcripcion = Acta.ESTADO_ERROR
        acta.save()
        return f"Error procesando Acta {acta_pk}: {e}"
    
    finally:
        # 8. Limpieza de archivos temporales (¡MUY IMPORTANTE!)
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