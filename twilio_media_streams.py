# phone_agent/twilio_handler.py
import base64
import os
import json
import uuid
from flask import Response
from io import BytesIO

from helpers import twiml_response_with_hangup
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
                "state": "name",
                "retries":{}  # or whatever your initial state is
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
    

def twiml_response_with_hangup(message: str) -> Response:
    return Response(f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Say voice="alice">{message}</Say>
        <Hangup/>
    </Response>""", mimetype="text/xml")


async def handle_transcript(self, text):
    print(f"📝 User said: {text}")
    session_state = self.sessions.get(self.stream_sid)
    if not session_state:
        print(f"No session found for {self.stream_sid}")
        return twiml_response_with_hangup("Session ended due to a system error.")

    result, updated_session_state = await on_transcript(text, session_state)

    if result.get("end_call"):
        if result.get("confirmed"):
            return (Response(f"""<?xml version="1.0" encoding="UTF-8"?>
                        <Response>
                            <Hangup/>
                        </Response>""", mimetype="text/xml"))
        return twiml_response_with_hangup(result["message"])

    # Update session state
    self.sessions[self.stream_sid] = updated_session_state

    audio_url = result.get("audio_path")
    print(f"Streaming audio back: {audio_url}")

    return Response(f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Play>{audio_url}</Play>
    </Response>""", mimetype="text/xml")