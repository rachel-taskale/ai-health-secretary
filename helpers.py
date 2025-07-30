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
                 "Extract the caller's first and last name from the transcript.\n"
                "If only one name is given, assume it is the first name and leave last name empty.\n"
                "Return the result as a JSON object with this format:\n\n"
                '{\n'
                '  "first_name": "string",\n'
                '  "last_name": "string"\n'
                '}\n\n'
                "Do not include any explanation — only return the JSON object."
            )
        case "insurance_id":
            return (
                   "The user is providing their insurance ID by spelling it out. "
                    "Convert this transcript to an insurance ID: "
                    "- 'one' = 1, 'two' = 2, 'three' = 3, 'four' = 4, 'five' = 5, 'six' = 6, 'seven' = 7, 'eight' = 8, 'nine' = 9, 'zero' = 0 "
                    "- Letter names become uppercase letters: 'a' = A, 'b' = B, 'c' = C, 'd' = D, etc. "
                    "Combine all characters into one string with no spaces. "
                    "For transcript 'one two three d', return '123D'. "
                    "Return only the converted ID or empty string if invalid."
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
async def data_extraction (text: str, v_type: str):
    base_prompt = openAIPrompts(v_type)
    final_prompt = f"{base_prompt}\n\nTranscript: {text}"
    response = openai_client.chat_response(final_prompt)
    print(f"open ai response: {response}")
    return await validate_regex(response, v_type)



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



async def handle_appointment_scheduling(text):
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

        is_valid_time, error_message = await validate_appointment_time(json_response)
        print(f"++++After: {error_message}")
        if not is_valid_time:
            return None, False, error_message

        return json_response, True, None

    except json.JSONDecodeError as e:
        return None, False, f"Failed to parse response: {e}"
    except Exception as e:
        return None, False, f"OpenAI error: {e}"





async def infer_address_with_llm(raw_address: str) -> str:
    """
    Uses OpenAI to infer the correct structured address from raw user input.
    """
    prompt = f"""
    You are an AI address normalizer. Your job is to take in a potentially incomplete or misspoken address and return the most likely full and correctly spelled address as a single line (like "123 Main Street, San Francisco, CA 94105").

    Based on your knowledge of common U.S. addresses and city/street formats, correct any typos and reorder parts as needed.

    Raw input: "{raw_address}"

    Respond ONLY with the inferred fixed address.
    """

    response = await openai.ChatCompletion.acreate(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt.strip()}],
    )
    
    return response.choices[0].message.content.strip()