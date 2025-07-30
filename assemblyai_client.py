import asyncio
import base64
import json
import websockets
from config import config



class AssemblyAIClient:
    def __init__(self, api_key):
        self.api_key = config.assemblyai.api_key
        self.uri = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"
        self.ws = None
        self.transcript_callback = None

    def set_callback(self, callback):
        self.transcript_callback = callback

    async def connect(self, on_transcript):
        self.on_transcript = on_transcript

        self.ws = await websockets.connect(
            self.uri,
            additional_headers={"Authorization": self.api_key},
            ping_interval=5,
            ping_timeout=20
        )
        asyncio.create_task(self._receive_loop())

    async def send_audio(self, audio_chunk):
        print("made it to send audio")
        if self.ws:
            payload = json.dumps({
                "audio_data": base64.b64encode(audio_chunk).decode("utf-8")
            })
            await self.ws.send(payload)

    async def _receive_loop(self):
        async for message in self.ws:
            msg = json.loads(message)
            if msg.get("message_type") == "FinalTranscript":
                text = msg.get("text", "").strip()
                if text and self.transcript_callback:
                    await self.transcript_callback(text)

    async def terminate(self):
        if self.ws:
            await self.ws.send(json.dumps({"terminate_session": True}))
            await self.ws.close()
            self.ws = None
    

 