import assemblyai as aai
from config import config
from helpers import data_extraction, handle_appointment_scheduling
from file_storage import add_doctors_appointment, write_patient_record
from validators import validate_full_address
from email_service import send_confirmation_email_html

MAX_RETRIES = 3

async def on_transcript(text, session_state):
    print(f"ON_TRANSCRIPT: {text}")
    current_state = session_state["state"]
    # Validate based on current state
    match current_state:
        case "address":
            data, valid, error = await validate_full_address(text)
        case "schedule_appointment":
            data, valid, error = await handle_appointment_scheduling(text)
            if valid and data:
                await add_doctors_appointment(data, session_state["name"], session_state["topic_of_call"])
        case "done":
            return {
                "end_call": True,
                "retry": False,
            }, session_state
        case _:
            print(f"Current state: {current_state}, text: {text}")
            data, valid, error = await data_extraction(text, current_state)

    if not valid or not data:
        print(f"why am i here: valid: {valid}, data: {data}")
        return {
                "end_call": False,
                "retry": True,
            }, session_state

    if current_state == "schedule_appointment":
        session_state["appointments"] = data
    else:
        session_state[current_state] = data
    print(f"current state: {current_state}")
    print(f"new session state: {session_state["state"]}")
    
    if session_state["state"] == "done":
        write_patient_record(session_state)
        send_confirmation_email_html(session_state)
        return {
            "end_call": True,
            "retry": False,
        }, session_state
    
    print("made it hereeeeeeeeeee")

    return {
        "end_call": False,
        "retry": False
    }, session_state

async def audio_generator(audio_queue):
    while True:
        chunk = await audio_queue.get()
        if chunk is None:
            break
        yield chunk