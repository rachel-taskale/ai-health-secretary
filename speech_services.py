import asyncio
import base64
import json
import time
import openai

import assemblyai as aai
import os
import uuid

from quart import websocket

from config import config
import websockets
from helpers import data_extraction, get_next_prompt, handle_appointment_scheduling, next_prompt_type, synthesize_speech
from file_storage import add_doctors_appointment, write_patient_record
from validators import validate_full_address
from email_service import send_confirmation_email_html

# Configure clients
aai.settings.api_key = config.assemblyai.api_key
transcriber = aai.Transcriber()



# Main function to handle all of our cases for receiving data from the user
async def on_transcript(text, session_state):
    print("made it to on transcript")
    current_state = session_state["state"]
    # Ternary function handle all the
    # send the data to the openai and extract the data from it
    if current_state == "address": 
        data, valid, error = validate_full_address(text)
    elif current_state == "schedule_appointment":
        data, valid, error = handle_appointment_scheduling(text)
        add_doctors_appointment(data, session_state["name"], session_state["topicOfCall"])
    else: 
        data, valid, error = data_extraction(text, current_state)
    if not valid or not data:
        print(f"an error occured: {error}")
        retry_audio = synthesize_speech(error)
        return {"retry": True, "audio_path": retry_audio}

    # For now we arent going to confirm with the user, just do extraction & store
   
    session_state[current_state] = data
    session_state["state"] = next_prompt_type(current_state)

    # prompt the user for the next input
    next_prompt = get_next_prompt(session_state["state"])
    next_audio = synthesize_speech(next_prompt)
    # if we reach the end then we should save all the information
    if next_prompt == 'done':
        print(f"current state: {session_state}")
        # Save it to our text file
        write_patient_record(session_state)
    
        send_confirmation_email_html(session_state)

    return {"retry": False, "audio_path": next_audio}, session_state



async def audio_generator(audio_queue):
    while True:
        chunk = await audio_queue.get()
        if chunk is None:
            break
        yield chunk     