"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:   Consumer de WebSockets para transcripción en tiempo real (STT) 
               usando el modelo Vosk. Maneja la recepción de audio y envío de texto.
--------------------------------------------------------------------------------
"""
# reuniones/consumers.py
import asyncio, json, logging # Importa librerías estándar
from channels.generic.websocket import AsyncWebsocketConsumer # Importa consumidor asíncrono
from concurrent.futures import ThreadPoolExecutor # Importa ejecutor de hilos
from django.conf import settings # Importa configuraciones de Django

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000 # Frecuencia de muestreo para el audio
EXECUTOR = ThreadPoolExecutor(max_workers=2) # Ejecutor para tareas pesadas
_VOSK_MODEL = None  # carga perezosa y compartida del modelo

class STTConsumer(AsyncWebsocketConsumer):
    async def connect(self): # Maneja la conexión WS
        self.reunion_id = self.scope["url_route"]["kwargs"]["reunion_id"] # Obtiene ID de reunión
        self.group_name  = f"reunion-{self.reunion_id}" # Define nombre de grupo
        self.last_final  = None
        self.rec         = None

        # Cargar Vosk con manejo de errores
        try:
            global _VOSK_MODEL
            if _VOSK_MODEL is None:
                from vosk import Model
                logger.info("Cargando modelo Vosk: %s", settings.MODEL_PATH_RELATIVO)
                _VOSK_MODEL = Model(str(settings.MODEL_PATH_RELATIVO)) # Carga el modelo globalmente
            from vosk import KaldiRecognizer
            self.rec = KaldiRecognizer(_VOSK_MODEL, SAMPLE_RATE) # Inicializa reconocedor
            self.rec.SetWords(True)
        except Exception as e:
            await self.accept()
            await self.send(json.dumps({"type":"status","msg":f"Error Vosk: {e}"}))
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name) # Une al grupo
        await self.accept() # Acepta conexión
        await self.send(json.dumps({"type":"status","msg":"WS conectado"}))

    async def receive(self, text_data=None, bytes_data=None): # Recibe datos (audio)
        if not self.rec or not bytes_data:
            return
        loop = asyncio.get_running_loop()
        # Procesa el audio en un hilo separado para no bloquear
        accepted = await loop.run_in_executor(EXECUTOR, self.rec.AcceptWaveform, bytes_data)
        if accepted:
            data = json.loads(self.rec.Result())
            txt  = (data.get("text") or "").strip()
            if txt and txt != self.last_final:        # anti-duplicado
                self.last_final = txt
                await self.channel_layer.group_send( # Envía resultado final al grupo
                    self.group_name,
                    {"type":"stt_broadcast", "payload":{"type":"final","text":txt}}
                )
        else:
            parc = json.loads(self.rec.PartialResult()).get("partial","").strip()
            if parc:
                await self.send(json.dumps({"type":"partial","text":parc})) # Envía parcial al cliente

    async def disconnect(self, code): # Desconexión
        # No vuelvas a enviar FinalResult aquí; solo cierra
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def stt_broadcast(self, event): # Envía mensaje a clientes
        await self.send(json.dumps(event["payload"]))