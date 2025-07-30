import assemblyai as aai
import os
import uuid

from config import config
from helpers import data_extraction, get_next_agent_response, handle_appointment_scheduling, next_prompt_type
from file_storage import add_doctors_appointment, write_patient_record
from validators import validate_full_address
from email_service import send_confirmation_email_html

# Configure clients
aai.settings.api_key = config.assemblyai.api_key
transcriber = aai.Transcriber()

MAX_RETRIES = 3

async def on_transcript(text, session_state):
    print(f"ON_TRANSCRIPT: {text}")
    current_state = session_state["state"]
    print(f"current state: {current_state}")
    retries = session_state.get("retries", {}).get(current_state, 0)
    print(f"Current retries: {retries}")

    # Validate based on current state
    match current_state:
        case "address":
            data, valid, error = validate_full_address(text)
        case "schedule_appointment":
            data, valid, error = handle_appointment_scheduling(text)
            if valid and data:
                add_doctors_appointment(data, session_state["name"], session_state["topic_of_call"])
        case "done":
            return {
                "end_call": True,
                "confirmed": True,
            }, session_state
        case _:
            print(f"Current state: {current_state}, text: {text}")
            data, valid, error = data_extraction(text, current_state)

    if not valid or not data:
        print(valid)
        print(data)
        retries += 1
        # Update retries in session state
        session_state.setdefault("retries", {})[current_state] = retries

        if retries >= MAX_RETRIES:
            return {
                "end_call": True,
                "confirmed": False,
            }, session_state
        
        return {
        "retry": True,
        "confirmed":False,
    }, session_state



    if current_state == "schedule_appointment":
        session_state["appointments"] = data
    else:
        session_state[current_state] = data
    

    if "retries" not in session_state:
        session_state["retries"] = {}
    session_state["retries"][current_state] = 0 

    session_state["state"] = next_prompt_type(current_state)
    print(f"current state: {current_state}")
    print(f"new session state: {session_state["state"]}")
    
    if session_state["state"] == "done":
        write_patient_record(session_state)
        send_confirmation_email_html(session_state)
        return {
            "end_call": True,
            "confirmed": True,
            "response_text": "Thanks. Your appointment has been scheduled. Please check your email for the appointment confirmation. Goodbye."
        }, session_state

    try:
        next_prompt = get_next_agent_response(session_state["state"])
        print(f"next prompt: {next_prompt}")
        return {
            "retry": False, 
            "confirmed": True
        }, session_state
    except Exception as e:
        print(f"Error getting next prompt: {e}")
        return {
            "retry": False, 
            "confirmed":False,
        }, session_state

async def audio_generator(audio_queue):
    while True:
        chunk = await audio_queue.get()
        if chunk is None:
            break
        yield chunk