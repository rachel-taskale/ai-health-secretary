import asyncio
import base64
import json
import time
import openai

import assemblyai as aai
import os
import uuid
import config

from config import config
import websockets
from helpers import data_extraction, get_next_prompt, handle_appointment_scheduling, synthesize_speech
from file_storage import write_patient_record
from validators import validate_full_address

# Configure clients
openai.api_key =config.openai.api_key
aai.settings.api_key = config.assemblyai.api_key
transcriber = aai.Transcriber()



# Use assembly AI to transcribe the audio
def transcribe_audio(audio_path: str) -> str:
    print(f"audio path: {audio_path}")
    transcript = transcriber.transcribe(audio_path)
    transcript_text = transcript.text
    return transcript_text

async def stream_audio_to_assemblyai(audio_generator, on_transcript):
    """
    Streams audio to AssemblyAI and calls `on_transcript` callback with final transcripts.
    """
    uri = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"
    async with websockets.connect(uri,
        extra_headers={"Authorization": config.assemblyai.api_key},
        ping_interval=5,
        ping_timeout=20) as ws:

        async def send_audio():
            async for chunk in audio_generator:
                await ws.send(json.dumps({"audio_data": base64.b64encode(chunk).decode("utf-8")}))
            await ws.send(json.dumps({"terminate_session": True}))

        async def receive_transcripts():
            async for msg in ws:
                data = json.loads(msg)
                print(f"data: {data}")
                if data.get("message_type") == "FinalTranscript":
                    text = data.get("text", "").strip()
                    if text:
                        await on_transcript(text)

        return await asyncio.gather(send_audio(), receive_transcripts())




# Function to handle all of our cases for receiving data from the user
async def on_transcript(text, session_state):
    current_state = session_state["state"]
    # Ternary function handle all the
    # send the data to the openai and extract the data from it
    if current_state == "address": 
        data, valid, error = validate_full_address(text)
    elif current_state == "schedule_appointment":
        data, valid, error = handle_appointment_scheduling(text)
    else: 
        data, valid, error = data_extraction(text, current_state)
    if not valid or not data:
        print(f"an error occured: {error}")
        retry_audio = synthesize_speech(error)
        return {"retry": True, "audio_path": retry_audio}
        
    # For now we arent going to confirm with the user, just do extraction & store
    session_state[current_state] = data
    session_state["state"] = next_prompt(current_state)

    # prompt the user for the next input
    next_prompt = get_next_prompt(session_state["state"])
    next_audio = synthesize_speech(next_prompt)
    # if we reach the end then we should save all the information
    if next_prompt == 'done':
        print(f"current state: {session_state}")
        # Save it to our text file
        write_patient_record(session_state)
    return {"retry": False, "audio_path": next_audio}

   

async def audio_generator(audio_queue):
    while True:
        chunk = await audio_queue.get()
        if chunk is None:
            break
        yield chunk     