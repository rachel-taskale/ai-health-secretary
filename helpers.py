import json
import openai
from file_storage import get_doctors_appointments
from speech_services import synthesize_speech
from validators import validate_appointment_time

def get_next_prompt(state):
    appointments_natural_language = ""
    if state == "schedule_appointment":
        # Need to get all potential appointment times
        doctors_appointments = get_doctors_appointments()
        # Now need to prompt OpenAI to turn into natural language
        appointments_natural_language = convert_appointments_to_natural_language(doctors_appointments)

    prompts = {
        "insurance_payer": "Please provide the member name on your insurance card",
        "insurance": "Please provide your insurance ID.",
        "topic_of_call": "Why are you scheduling an appointment today?",
        "phone": "What is your phone number?",
        "email": "What is your email address?",
        "schedule_appointment": f"Great thanks for all that information, the next available appointments are: {appointments_natural_language}",
        "done": "Thanks. Your appointment has been scheduled. Please check your email for the appointment confirmation. Goodbye."
    }
    return prompts.get(state, None)


def convert_appointments_to_natural_language(raw_input: str) -> dict:
    prompt = f"""
    You are a secretary for a doctor's office communicate all open time slots to schedule appointments to your patient
    based on the slots currently filled. If a date doesn't exist in the list then the doctor is free all working hours. 
    
    Working hours are 9:00am - 5:00pm EST
    Only communicate open time ranges for the next two weeks

    "{raw_input}"
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    appointments = response.choices[0].message.content.strip()
    return appointments



def data_extraction (text: str, type: str):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": f"Extract {type} from the transcript"
            },
            {
                "role": "user",
                "content": f"Transcript: {text}\n\n Return the user's name, date of birth, and reason for calling as JSON."
            }
        ]
    )
    # One more round of validation on our regex to confirm the output from OpenAI was correct
    return validate_regex(response.choices[0].message["content"], type )



# sequence of events
def next_prompt(current_state):
    match current_state:
        case "insurance_payer":
            return "insurance"
        case "insurance":
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
        response = openai.ChatCompletion.create(
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
        return data, True, None
    except json.JSONDecodeError as e:
        return None, False, f"Failed to parse response: {e}"
    except Exception as e:
        return None, False, f"OpenAI error: {e}"