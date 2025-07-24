import os
import re
from config import config

import requests
from openai import OpenAI

client = OpenAI()

from file_storage import get_doctors_appointments_by_day_and_doctor

PHONE_REGEX = re.compile(r"^\+1\d{10}$")  # e.g., +14155552671
DOB_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")  # YYYY-MM-DD
INSURANCE_REGEX = re.compile(r"^[A-Z0-9]{5,15}$", re.IGNORECASE)
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_regex(text: str, type: str):
    found = text
    match type:
        case "phone":
            found = re.search(PHONE_REGEX, text)
            if not found or found == "":
                return "", False, "Invalid phone format. Use XXXXXXXXXX"
        case "email":
            found = re.search(EMAIL_REGEX, text)
            if not found or found == "":
                return "", False, "Invalid email format"
        case "insurance_id":
            found = re.search(INSURANCE_REGEX, text)
            if not found or found == "":
                return "", False, "Insurance ID must be 5-15 alphanumeric characters"
        case "dob":
            found = re.search(DOB_REGEX, text)
            if not found or found == "":
                return "", False, "Invalid date of birth format. Use YYYY-MM-DD"
            
    print(f"found: {found}")
    return found, True, ""


# Function to extract the address into json format
def extract_and_check_address_with_openai(raw_input: str) -> dict:
    prompt = f"""
    You're an address parser. Extract a structured US mailing address from this input:

    "{raw_input}"

    Respond in JSON like:
    {{
    "street": "123 Main St",
    "city": "San Francisco",
    "state": "CA",
    "zip": "94105",
    "status": "VALID",  # or "INCOMPLETE" or "INVALID"
    "missingFields": ["street", "city"]  # only if status is INCOMPLETE
    }}

    Only respond with valid JSON. And convert all spelled out numbers to number format
    """

    response = client.chat.completions.create(model="gpt-4",
    messages=[{"role": "user", "content": prompt}])

    json_text = response.choices[0].message.content.strip()
    return eval(json_text) 



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
        return True
    else:
        return False



def validate_full_address(raw_input):
    result = extract_and_check_address_with_openai(raw_input)
    print(result)

    if result.get("status") != "VALID":
        missing_fields = ", ".join(str(f) for f in result.get("missingFields", []))
        return None, False, f"Address is incomplete, please repeat address with {missing_fields}"

    is_valid = validate_address_with_smarty(
        result["street"], result["city"], result["state"], result.get("zip")
    )
    if not is_valid:
        return None, False, "Address not found, please enter a valid address"
    ans = {
        "street": result["street"],
        "city": result["city"],
        "state": result["state"],
        "zip": result["zip"]
    }
    return ans, True, ""




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

