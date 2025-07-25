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
from helpers import data_extraction, get_next_agent_response, handle_appointment_scheduling, next_prompt_type, synthesize_speech
from file_storage import add_doctors_appointment, write_patient_record
from validators import validate_full_address
from email_service import send_confirmation_email_html

# Configure clients
aai.settings.api_key = config.assemblyai.api_key
transcriber = aai.Transcriber()



MAX_RETRIES = 3
async def on_transcript(text, session_state):
    current_state = session_state["state"]
    retries = session_state.get("retries", {}).get(current_state, 0)
    print(retries)

    # Validate based on current state
    match current_state:
        case "done":
              return {
                    "end_call": True,
                    "confirmed": True
            }
        case "address":
            data, valid, error = validate_full_address(text)
        case "schedule_appointment":
            data, valid, error = handle_appointment_scheduling(text)
        case _:
            data, valid, error = data_extraction(text, current_state)

    if not valid or not data:
        retries += 1
        # Update retries in session state
        session_state.setdefault("retries", {})[current_state] = retries

        if retries >= MAX_RETRIES:
            return {
                    "end_call": True,
                    "confirmed":False,
                    "audio_path": synthesize_speech(f"I'm having trouble understanding. We can't move on until I receive this information. Please give me a call back when you have the rest of the details")
            }, session_state

        return {
            "retry": True,
            "audio_path": synthesize_speech(error)
        }, session_state

    # ✅ Valid input — store it and reset retry counter
    session_state[current_state] = data
    session_state["retries"][current_state] = 0  # reset retries
    

    # Advance to next state
    session_state["state"] = next_prompt_type(current_state)
    if session_state["state"] == "done":
        write_patient_record(session_state)
        send_confirmation_email_html(session_state)

    return {"retry": False, "audio_path": None}, session_state



# Main function to handle all of our cases for receiving data from the user
# async def on_transcript(text, session_state):
#     print(session_state)
#     current_state = session_state["state"]
#     # Ternary function handle all the
#     # send the data to the openai and extract the data from it
#     if current_state == "address": 
#         data, valid, error = validate_full_address(text)
#     elif current_state == "schedule_appointment":
#         data, valid, error = handle_appointment_scheduling(text)
#         add_doctors_appointment(data, session_state["name"], session_state["topic_of_call"])
#     else: 
#         data, valid, error = data_extraction(text, current_state)
#     if not valid or not data:
#         print(f"an error occured: {error}")
#         retry_audio = synthesize_speech(error)
#         return {"retry": True, "audio_path": retry_audio}, session_state

#     # For now we arent going to confirm with the user, just do extraction & store
   
#     session_state[current_state] = data
#     session_state["state"] = next_prompt_type(current_state)

#     # prompt the user for the next input
#     next_prompt = get_next_agent_response(session_state["state"])
#     next_audio = synthesize_speech(next_prompt)
#     # if we reach the end then we should save all the information
#     if next_prompt == 'done':
#         print(f"current state: {session_state}")
#         # Save it to our text file
#         write_patient_record(session_state)
    
#         send_confirmation_email_html(session_state)

#     return {"retry": False, "audio_path": next_audio}, session_state



async def audio_generator(audio_queue):
    while True:
        chunk = await audio_queue.get()
        if chunk is None:
            break
        yield chunk     