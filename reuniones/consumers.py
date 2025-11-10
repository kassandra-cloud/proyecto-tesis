# reuniones/consumers.py
import asyncio, json, logging
from channels.generic.websocket import AsyncWebsocketConsumer
from concurrent.futures import ThreadPoolExecutor
from django.conf import settings

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
EXECUTOR = ThreadPoolExecutor(max_workers=2)
_VOSK_MODEL = None  # carga perezosa y compartida

class STTConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.reunion_id = self.scope["url_route"]["kwargs"]["reunion_id"]
        self.group_name  = f"reunion-{self.reunion_id}"
        self.last_final  = None
        self.rec         = None

        # Cargar Vosk con manejo de errores
        try:
            global _VOSK_MODEL
            if _VOSK_MODEL is None:
                from vosk import Model
                logger.info("Cargando modelo Vosk: %s", settings.VOSK_MODEL_PATH)
                _VOSK_MODEL = Model(str(settings.VOSK_MODEL_PATH))
            from vosk import KaldiRecognizer
            self.rec = KaldiRecognizer(_VOSK_MODEL, SAMPLE_RATE)
            self.rec.SetWords(True)
        except Exception as e:
            await self.accept()
            await self.send(json.dumps({"type":"status","msg":f"Error Vosk: {e}"}))
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(json.dumps({"type":"status","msg":"WS conectado"}))

    async def receive(self, text_data=None, bytes_data=None):
        if not self.rec or not bytes_data:
            return
        loop = asyncio.get_running_loop()
        accepted = await loop.run_in_executor(EXECUTOR, self.rec.AcceptWaveform, bytes_data)
        if accepted:
            data = json.loads(self.rec.Result())
            txt  = (data.get("text") or "").strip()
            if txt and txt != self.last_final:        # anti-duplicado
                self.last_final = txt
                await self.channel_layer.group_send(
                    self.group_name,
                    {"type":"stt_broadcast", "payload":{"type":"final","text":txt}}
                )
        else:
            parc = json.loads(self.rec.PartialResult()).get("partial","").strip()
            if parc:
                await self.send(json.dumps({"type":"partial","text":parc}))

    async def disconnect(self, code):
        # No vuelvas a enviar FinalResult aquí; solo cierra
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def stt_broadcast(self, event):
        await self.send(json.dumps(event["payload"]))
