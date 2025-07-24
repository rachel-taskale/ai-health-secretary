# phone_agent/twilio_handler.py
import base64
import os
import json
import uuid
from flask import Response
from io import BytesIO

from speech_services import on_transcript

class TwilioMediaStreamHandler:
    def __init__(self, assembly_client, openai_client, audio_dir, host_url, session_store):
        self.assembly_client = assembly_client
        self.openai_client = openai_client
        self.audio_dir = audio_dir
        self.host_url = host_url
        self.stream_sid = None
        self.sessions = session_store

    def start_stream(self, request):
        data = request.json
        self.stream_sid = data["streamSid"]
        self.sessions[self.stream_sid] = {
                "state": "address",  # or whatever your initial state is
            }
        # Start Assembly in background
        self.assembly_client.start(
            on_transcript=lambda text: self.handle_transcript(text, self.stream_sid)
        )

        print(f"🔗 Started stream: {self.stream_sid}")
        return Response(status=200)

    def receive_audio(self, request):
        if not self.stream_sid:
            return Response("No stream", status=400)

        payload = request.json
        event = payload.get("event")

        if event == "media":
            audio_b64 = payload["media"]["payload"]
            audio_bytes = BytesIO(base64.b64decode(audio_b64)).getvalue()
            self.assembly_client.send_audio(audio_bytes)

        return Response(status=200)

    #  End our function
    def stop_stream(self, request):
        print(f"Stopping stream: {self.stream_sid}")
        self.assembly_client.send_audio(None)
        self.assembly_client.stop()
        self.stream_sid = None
        return Response(status=200)
    


    async def handle_transcript(self, text):
        print(f"📝 User said: {text}")
        session_state = self.sessions.get(self.stream_sid)
        if not session_state:
            print(f"No session found for {self.stream_sid}")
            return

        result = await on_transcript(text, session_state)  # ✅ your function

        audio_url = result["audio_path"]
        print(f"Streaming audio back: {audio_url}")

        
    
        # filename = f"{uuid.uuid4()}.mp3"
        # filepath = os.path.join(self.audio_dir, filename)
        # with open(filepath, "wb") as f:
        #     f.write(speech.content)

        # Send <Play> TwiML redirect to Twilio (optional step: needs call SID)
        # For now, serve via <Play> in your app logic
        # print(f"🔊 MP3 ready: {self.host_url}/static/audio/{filename}")
