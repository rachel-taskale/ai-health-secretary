import json
import os
import uuid
from flask import Response
from openai import OpenAI
import openai

client = OpenAI()
from file_storage import get_doctors_appointments
from validators import validate_appointment_time, validate_regex

AUDIO_OUTPUT_DIR = "./audio_output"

# def play_audio(response_text: str):
#     audio_url = synthesize_speech(response_text)  # returns hosted mp3 URL
#     return f"""
#         <Response>
#             <Play>{audio_url}</Play>
#         </Response>
#     """


def get_next_agent_response(state):
    appointments_natural_language = ""
    if state == "schedule_appointment":
        # Need to get all potential appointment times
        doctors_appointments = get_doctors_appointments()
        # Now need to prompt OpenAI to turn into natural language
        appointments_natural_language = convert_appointments_to_natural_language(doctors_appointments)

    prompts = {
        "name": "Welcome, please state your name so we can identify your patient account",
        "insurance_payer": "Please provide the member name on your insurance card",
        "insurance_id": "Please provide your insurance ID.",
        "address": "Please provide your address in the format: street address, city, state, and zip code.",
        "topic_of_call": "Why are you scheduling an appointment today?",
        "phone": "What is your phone number?",
        "email": "What is your email address?",
        "schedule_appointment": f"Great thanks for all that information, the next available appointments are: {appointments_natural_language}",
        "done": "Thanks. Your appointment has been scheduled. Please check your email for the appointment confirmation. Goodbye."
    }
    return prompts.get(state, None)

def openAIPrompts(type):
    match type:
        case "name":
            return "Extract the first and last name of the caller from the transcript. If it is just a name then that is the caller name"
        case "insurance_payer":
            return (
                "Extract the insurance payer’s full name from the transcript. "
                "If only one name is provided, treat it as the insurance payer."
            )
        case "insurance_id":
            return (
                "Extract the insurance ID from the transcript. "
                "It may be mentioned as 'Group Name', 'Member ID', or any similar label found on a health insurance card."
            )
        case "topic_of_call":
            return "Summarize the main topic of scheduling an appointment with the doctor from the transcript"
        case "phone":
           return (
                "Extract the phone number from the transcript. The user may say the number with spaces, dashes, or the word 'dash' in between digits. "
                "They may also include the U.S. country code like '+1' or say 'one' at the beginning. "
                "Return the phone number in E.164 format (e.g., +19177012642). "
                "Only return the number — do not include any explanation, labels, or extra text."
            )
        case "email":
           return (
                "Extract the email address from the transcript. The user may say 'at' instead of '@' and 'dot' instead of '.'. "
                "Convert those into the correct characters and return the email address in standard format (e.g., user@domain.com). "
                "Only return the email address — do not include any explanation, labels, or extra text."
            )
    return None



def openai_prompt_handler(prompt: str, system_prompt: str = "You are a helpful and accurate medical secretary with expertise in health insurance."):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()




def convert_appointments_to_natural_language(raw_input: str) -> dict:
    prompt = f"""
    Communicate all open time slots to schedule appointments to your patient based on the 
    slots currently filled. If a date doesn't exist in the list then the doctor is free all working hours. 
    
    Working hours are 9:00am - 5:00pm EST
    Only communicate open time ranges for the next two weeks

    "{raw_input}"
    """
    return openai_prompt_handler(prompt)



# Main openai prompt 
def data_extraction (text: str, type: str):
    base_prompt = openAIPrompts(type)
    final_prompt = f"{base_prompt}\n\nTranscript: {text}"
    response = openai_prompt_handler(final_prompt)
    # One more round of validation on our regex to confirm the output from OpenAI was correct
    return validate_regex(response, type)



# sequence of events
def next_prompt_type(current_state):
    match current_state:
        case "name":
            return "insurance_payer"
        case "insurance_payer":
            return "insurance_id"
        case "insurance_id":
            return "topic_of_call"
        case "topic_of_call":
            return "address"
        case "address":
            return "phone"
        case "phone":
            return "email"
        case "email":
            return "schedule_appointment"
        case "schedule_appointment":
            return "done"



def handle_appointment_scheduling(text):
    # extract the data
    prompt = f"""
        You are a secretary for a doctor's office. Extract all relevant scheduling information from the patient's message.

        Given this input: "{text}"

        Return a JSON object in this format (no explanations):
        {{
            "doctors_name": "string, e.g. 'john'",
            "start": "ISO 8601 timestamp for the start time, e.g. '2025-07-22T15:00:00'",
            "end": "ISO 8601 timestamp for the end time"
        }}
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        raw_content = response.choices[0].message.content.strip()
        data = json.loads(raw_content)

        # Validate that the appointment is available
        isValidTime = validate_appointment_time(data)
        if not isValidTime:
            return None, False, f"Appointment is already booked, please choose a different time"
        
        # If it is a valid time then we will need write to our doctors appointments file
        return data, True, None
    except json.JSONDecodeError as e:
        return None, False, f"Failed to parse response: {e}"
    except Exception as e:
        return None, False, f"OpenAI error: {e}"

# function to write create audio file in static
def synthesize_speech(text: str, voice: str = "nova", output_dir: str = AUDIO_OUTPUT_DIR) -> str:
    print(f"[TTS] Text input: {repr(text)}")  # <-- See what's being passed
    if not isinstance(text, str) or not text.strip():
        raise ValueError("synthesize_speech: 'text' must be a non-empty string")

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

    return file_path




