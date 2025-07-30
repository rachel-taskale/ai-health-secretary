from asyncio import subprocess
import json
import os
import uuid
from flask import Response
from openai import OpenAI
import openai
from config import config

from openai_client import OpenAIClient

from file_storage import get_doctors_appointments
from validators import validate_appointment_time, validate_regex


openai_client = OpenAIClient(config.openai.api_key, config.audiodir, config.openai.api_key)

AUDIO_OUTPUT_DIR = "./audio_output"


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
            return (
                "Extract the caller's first and last name from the transcript.\n"
                "If only one name is given, assume it is the first name and leave last name empty.\n"
                "Return the result as a JSON object with this format:\n\n"
                '{\n'
                '  "first_name": "string",\n'
                '  "last_name": "string"\n'
                '}\n\n'
                "Do not include any explanation — only return the JSON object."
            )
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


def convert_appointments_to_natural_language(raw_input: str) -> dict:
    prompt = f"""
    Communicate all open time slots to schedule appointments to your patient based on the 
    slots currently filled. If a date doesn't exist in the list then the doctor is free all working hours. 
    
    Working hours are 9:00am - 5:00pm EST
    Only communicate open time ranges for the next two weeks

    "{raw_input}"
    """

    return openai_client.chat_response(prompt)



# Main openai prompt 
def data_extraction (text: str, type: str):
    base_prompt = openAIPrompts(type)
    final_prompt = f"{base_prompt}\n\nTranscript: {text}"
    response = openai_client.chat_response(final_prompt)
    print(f"open ai response: {response}")
    return validate_regex(response, type)



# sequence of events
def next_prompt_type(current_state):
    match current_state:
        case "name":
            print("returning insurance payer")
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
    prompt = f"""
    Extract the scheduling information from the patient's message.

    Input:
    "{text}"

    Return a valid JSON object with the following fields:
    {{
      "doctor_name": "string, e.g. 'john'",
      "start": "start time in ISO 8601 format, e.g. '2025-07-22T15:00:00'",
      "end": "end time in ISO 8601 format",
      "missing_fields": ["list of any missing fields, e.g. 'doctor_name', 'start', 'end'"]
    }}

    Do not include any explanation — only return the JSON object.
    If all fields are present, return an empty list for "missing_fields".
    """

    try:
        response = openai_client.chat_response(prompt)
        print(response)
        json_response = json.loads(response)
        print(f"After response: {response}")
        missing_fields = json_response.get("missing_fields", None)
        print(f"missing fields: {missing_fields}")

        if missing_fields == None:
            return None, False, (
                f"We need more information. Please repeat your appointment preference with "
                f"these missing fields: {json_response['missing_fields']}"
            )

        is_valid_time, error_message = validate_appointment_time(json_response)
        print(f"++++After: {error_message}")
        if not is_valid_time:
            return None, False, error_message

        return json_response, True, None

    except json.JSONDecodeError as e:
        return None, False, f"Failed to parse response: {e}"
    except Exception as e:
        return None, False, f"OpenAI error: {e}"



