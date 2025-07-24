import json
import os
from datetime import datetime
import uuid


PATIENT_RECORDS_FILE = os.path.join("data", "patient_records.txt")
DOCTORS_APPOINTMENTS_FILE = os.path.join("data", "doctors_appointments.txt")
# Patient Record Data
# "firstname#lastname" : {
#   "insurance_payer": string,
#   "insurance_ID": string,
#   "topic_of_call": string,
#   "phone": string,
#   "email":string,
#   "appointments": [
#       {
#               id: Foreign key - referenceID to the appointment
#               doctor_name:str
#       }
#   ]


# Appointment Data
# {doctor's name}.json: 
# {
#   "date": {
#       uniqueId: {
    #       "available": boolean,
    #       "start": str,
    #       "end": str,
    #       "patient": str,
    #       "reason": str
    #      }    
#   }



# Appends a new patient record to the doctors_appointments file 
# in a pseudo-JSON format with a composite key "First#Last".
def write_patient_record(data: dict):
    key = f'"{data["lastName"]}#{data["firstName"]}"'

    value = {
        "insurance_payer": data["insurance_payer"],
        "insurance_ID": data["insurance_ID"],
        "topic_of_call": data["topic_of_call"],
        "phone": data["phone"],
        "email": data["email"],
        "appointments": data["appointments"]
    }

    entry = f'{key} : {json.dumps(value, indent=2)},\n'

    # Create file if it doesn't exist
    if not os.path.exists(PATIENT_RECORDS_FILE):
        with open(PATIENT_RECORDS_FILE, "w") as f:
            f.write("# Patient Record Data\n")

    # Check if patient already exists
    with open(PATIENT_RECORDS_FILE, "r") as f:
        lines = f.readlines()
        if any(key in line for line in lines):
            
            return False

    # Append new patient record
    with open(PATIENT_RECORDS_FILE, "a") as f:
        f.write(entry)

    print(f"✅ Patient {key} written to file.")
    return True





def get_all_doctor_files():
    directory_path = "./data/schedule"
    file_list = []
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            file_list.append(os.path.join(root, file))
    return file_list


def get_doctors_appointments():
    files = get_all_doctor_files()
    # Need to aggregate all the data
    all_doctors_appointments = {}
    for file_name in files:
        with open(file_name, "r") as f:
            data =  [line.strip() for line in f if line.strip()]        
            json_parsed_data = json.parse(data)
            all_doctors_appointments[file_name] = json_parsed_data

    print(f"all_doctors_appointments: {all_doctors_appointments}")
    return all_doctors_appointments

def get_doctors_appointments_by_day_and_doctor(input:dict):
    filename = f"./data/schedule/{input['doctor_name']}.json"
    with open(filename, "r") as f:
        data = json.loads(f)
        return data[input["start"].date()]


def add_doctors_appointment(data: dict, patient_name: str, reason:str):
    doctor_name = data['doctor_name']
    start = data["start"]  # assumed format: "HH:MM"
    end = data["end"]      # assumed format: "HH:MM"

    # Convert time to a date string for use as dict key
    date_str = datetime.strptime(start, "%H:%M").date().isoformat() 
    new_uuid = str(uuid.uuid4())

    url_path = f"data/schedule/{doctor_name}.json"
    if not os.path.exists(url_path):
        raise FileNotFoundError(f"No schedule found for {doctor_name}")
    
    with open(url_path, "r") as f:
        schedule = json.load(f)

    slots = schedule.get(date_str, {})
    slots[new_uuid] = {
        "available": False,
        "start": start,
        "end": end,
        "patient": patient_name,
        "reason": reason
    }
    schedule[date_str] = slots

    with open(url_path, "w") as f:
        json.dump(schedule, f, indent=2)

    return True, new_uuid



SESSIONS_FILE = "./data/call_sessions.json"
# Saving call sessions here
def load_sessions():
    if not os.path.exists(SESSIONS_FILE):
        return {}
    with os.F_LOCK, open(SESSIONS_FILE, "r") as f:
        return json.load(f)

def save_sessions(sessions):
    with os.F_LOCK, open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f, indent=2)

def get_session(call_sid):
    sessions = load_sessions()
    return sessions.get(call_sid)

def update_session(call_sid, data):
    sessions = load_sessions()
    sessions[call_sid] = data
    save_sessions(sessions)



def on_transcript(text, session):
    sid = session.get("sid")
    if sid:
        with open(f"./{sid}_transcript.txt", "a") as f:
            f.write(text + "\n")
    return text