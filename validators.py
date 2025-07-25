import json
import os
import re
from config import config

import requests
from openai import OpenAI

client = OpenAI()

from file_storage import get_doctors_appointments_by_day_and_doctor

PHONE_REGEX = re.compile(r"^\+1\d{10}$")
DOB_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")  # YYYY-MM-DD
INSURANCE_REGEX = re.compile(r"\b[A-Z0-9]{5,15}\b", re.IGNORECASE)
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_regex(text: str, type: str):
    match type:
        case "phone":
            found = re.search(PHONE_REGEX, text)
            if not found:
                return "", False, "Phone number must be country code, area code, and 7 digits"
        case "email":
            found = re.search(EMAIL_REGEX, text)
            if not found:
                return "", False, "Invalid email format"
        case "insurance_id":
            found = re.search(INSURANCE_REGEX, text)
            if not found:
                return "", False, "Insurance ID must be 5–15 alphanumeric characters"
        case "dob":
            found = re.search(DOB_REGEX, text)
            if not found:
                return "", False, "Invalid date of birth format. Use YYYY-MM-DD"
        case _:
            return "", False, f"Unknown validation type: {type}"

    return found.group(), True, ""


# Function to extract the address into json format
def extract_and_check_address_with_openai(raw_input: str) -> dict:
    prompt = f"""
        You are a medical office assistant extracting structured address information from patient speech.

        Your job is to extract only what the user explicitly says. Do not guess or make up address parts.
        If something is not clearly stated, leave it blank and include it in the "missingFields" list.

        Required fields:
        - "street": street number and name (e.g., "1245 Hayes Street")
        - "city": city name
        - "state": two-letter abbreviation (e.g., "CA")
        - "zip": 5-digit ZIP code
        - "status": "VALID" if all fields are present, "INCOMPLETE" otherwise
        - "missingFields": a list of any fields that are missing or unclear

        Only respond with a strict JSON object. Do not invent or assume any part of the address.
        Convert spelled-out numbers to digits (e.g., "twelve forty-five" → "1245").
        Transcript: "{raw_input}"
    """

    response = client.chat.completions.create(model="gpt-4",
    messages=[{"role": "user", "content": prompt}])

    json_text = response.choices[0].message.content.strip()
    return json_text


# Function to take extracted address and validate with external api to check that address actually exists
def validate_address_with_smarty(street, city, state, zip_code=None): 
    auth_id = config.smartystreets.auth_id
    auth_token = config.smartystreets.api_key

    params = {
        "street": street,
        "city": city,
        "state": state,
        "auth-id": auth_id,
        "auth-token": auth_token,
    }

    if zip_code:
        params["zipcode"] = zip_code

    response = requests.get("https://us-street.api.smartystreets.com/street-address", params=params)
    data = response.json()

    if response.status_code == 200 and len(data) > 0:
        return True, response
    else:
        return False, None




def validate_full_address(raw_input):
    result = extract_and_check_address_with_openai(raw_input)
    print(result)

    try:
        address = json.loads(result)
    except json.JSONDecodeError:
        return None, False, "Sorry, I couldn't understand the address. Please repeat it."

    is_valid, smarty_response = validate_address_with_smarty(
        address.get("street", ""),
        address.get("city", ""),
        address.get("state", ""),
        address.get("zip", "")
    )

    if not is_valid or not smarty_response.json():
        return None, False, "Address not found, please enter a valid address"

    components = smarty_response.json()[0]["components"]
    missing = address.get("missingFields", [])

    if "city" in missing:
        address["city"] = components.get("city_name", "")
    if "state" in missing:
        address["state"] = components.get("state_abbreviation", "")
    if "zip" in missing:
        address["zip"] = components.get("zipcode", "")
    if "street" in missing:
        address["street"] = " ".join(
            filter(None, [
                components.get("primary_number", ""),
                components.get("street_predirection", ""),
                components.get("street_name", ""),
                components.get("street_suffix", "")
            ])
        )

    return {
        "street": address["street"],
        "city": address["city"],
        "state": address["state"],
        "zip": address["zip"]
    }, True, ""




def validate_appointment_time(data: dict):
    # get the date from the start and end times:
    appointments_on_date = get_doctors_appointments_by_day_and_doctor(data)
    for i in appointments_on_date:
            start_time_in_between = i["start_date"] <=  input["start"] and i["start_date"] >=  input["end"]
            end_time_in_between = i["end_date"] <=  input["start"] and i["end_date"] >=  input["end"]
            exsiting_time_booked = i["start_date"] >=   input["start"] and i["end_date"] <=  input["end"]
            if start_time_in_between or end_time_in_between or exsiting_time_booked :
                return False
    return True

