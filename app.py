import os
from quart import Quart, request, send_from_directory
from dotenv import load_dotenv

from twilio_media_streams import TwilioMediaStreamHandler
from assemblyai_client import AssemblyAIClient
from openai_client import OpenAIClient
from config import config

load_dotenv()
app = Quart(__name__)
HOST_URL = os.getenv("HOST_URL")
AUDIO_DIR = "./static/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

openai_client = OpenAIClient(config.openai.api_key, AUDIO_DIR, HOST_URL)
assembly_client = AssemblyAIClient(config.assemblyai.api_key)
twilio_handler = TwilioMediaStreamHandler(assembly_client, openai_client, AUDIO_DIR, HOST_URL)

@app.route("/", methods=["POST"])
async def twilio_entry():
    print("twilio_entry")
    return (
        f"""
        <Response>
            <Start>
                <Stream url="{HOST_URL}/twilio-stream" />
            </Start>
            <Say>Hello! How can I help you today?</Say>
        </Response>
        """,
        200,
        {"Content-Type": "text/xml"},
    )

@app.route("/twilio-stream", methods=["POST"])
async def start_stream():
    return await twilio_handler.start_stream(request)

@app.route("/twilio-stream", methods=["PUT"])
async def receive_audio():
    return await twilio_handler.receive_audio(request)

@app.route("/twilio-stream", methods=["DELETE"])
async def stop_stream():
    return await twilio_handler.stop_stream(request)

@app.route("/static/audio/<filename>")
async def serve_audio(filename):
    return await send_from_directory(AUDIO_DIR, filename)

@app.route("/twilio-stream", methods=["GET"])
async def health_check():
    return "OK"

