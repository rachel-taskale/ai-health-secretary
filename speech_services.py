import asyncio
import base64
import json
import time
import openai

import assemblyai as aai
import tempfile
import os
import uuid
import config

from config import config
import websockets
from call_flow_state import get_next_prompt
from file_storage import append_patient_record
from validators import validate_dob, validate_email, validate_insurance_id, validate_regex

# Configure clients
openai.api_key =config.openai.api_key
aai.settings.api_key = config.assemblyai.api_key
transcriber = aai.Transcriber()



AUDIO_OUTPUT_DIR = "./audio_output"


def transcribe_audio(audio_path: str) -> str:
    print(f"audio path: {audio_path}")
    transcript = transcriber.transcribe(audio_path)
    return transcript

async def stream_audio_to_assemblyai(audio_generator, on_transcript):
    """
    Streams audio to AssemblyAI and calls `on_transcript` callback with final transcripts.
    """
    uri = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=8000"
    async with websockets.connect(uri,
        extra_headers={"Authorization": AssemblyAIConfig},
        ping_interval=5,
        ping_timeout=20) as ws:

        async def send_audio():
            async for chunk in audio_generator:
                await ws.send(json.dumps({"audio_data": base64.b64encode(chunk).decode("utf-8")}))
            await ws.send(json.dumps({"terminate_session": True}))

        async def receive_transcripts():
            async for msg in ws:
                data = json.loads(msg)
                if data.get("message_type") == "FinalTranscript":
                    text = data.get("text", "").strip()
                    if text:
                        await on_transcript(text)

        await asyncio.gather(send_audio(), receive_transcripts())


# # use OpenAI to generate a voice to stream back to the user with our pre-written response
# def synthesize_speech(text: str, voice: str = "echo", audio_path: str = AUDIO_OUTPUT_DIR ) -> str:
#     response = openai.audio.speech.create(
#         model="tts-1",
#         voice=voice,
#         input=text,
#     )

#     if not os.path.exists(AUDIO_OUTPUT_DIR):
#         os.makedirs(AUDIO_OUTPUT_DIR)

#     filename = f"{uuid.uuid4()}.mp3"
#     file_path = os.path.join(AUDIO_OUTPUT_DIR, filename)
#     with open(file_path, "wb") as f:
#         f.write(response.content)

#     return filename 


def synthesize_speech(text: str, voice: str = "echo", output_dir: str = AUDIO_OUTPUT_DIR) -> str:
    response = openai.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text,
    )

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    filename = f"{uuid.uuid4()}.mp3"
    file_path = os.path.join(output_dir, filename)

    with open(file_path, "wb") as f:
        f.write(response.content)

    return file_path  # ✅ full path


def invalid_speech_output(current_state):
    match current_state:
        case "email":
            return synthesize_speech("That didn't sound like a valid email. Please try again.")
        case "dob":
            return synthesize_speech("That doesn't seem like a valid birthdate. Say it like 1990 dash 12 dash 01.")
        case "insurance":
            return synthesize_speech("That doesn't seem like a valid birthdate. Say it like 1990 dash 12 dash 01.")

def next_prompt(current_state):
    match current_state:
        case "email":
            return "dob"
        case "dob":
            return "insurance"
        case "insurance":
            return "done"

# Function to handle all of our cases for receiving data from the user
async def on_transcript(text, session_state):
    current_state = session_state["state"]
    if current_state != "done":
            valid, error = validate_regex(text, current_state)
            if not valid:
                print(f"an error occured: {error}")
                retry_audio = synthesize_speech(invalid_speech_output(current_state))
                return {"retry": True, "audio_path": retry_audio}
            
            session_state[current_state] = text
            session_state["state"] = next_prompt(current_state)
    else:
        print(f"current state: {current_state}")
        session_data = {
                    "phone": session_state["phone"],
                    "email": session_state["email"],
                    "dob": session_state["dob"],
                    "insurance": session_state["insurance"],
                    "timestamp": int(time.time()),
                }
        append_patient_record(session_data)
        final_audio = synthesize_speech("Thanks. Your appointment has been submitted. Please check your email for the appointment confirmation. Goodbye.")
        return {"retry": False, "audio_path": final_audio}
    
     # Otherwise, prompt the user for the next input
    next_prompt = get_next_prompt(session_state["state"])
    next_audio = synthesize_speech(next_prompt)
    return {"retry": False, "audio_path": next_audio}
   


async def audio_generator(audio_queue):
    while True:
        chunk = await audio_queue.get()
        if chunk is None:
            break
        yield chunk     