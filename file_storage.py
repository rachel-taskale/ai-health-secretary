import json
import os
from datetime import datetime
import uuid


PATIENT_RECORDS_FILE = os.path.join("data", "patient_records.json")
DOCTORS_APPOINTMENTS_FILE = os.path.join("data", "doctors_appointments.json")
# Patient Record Data
# "firstname#lastname" : {
#   "insurance_payer": string,
#   "insurance_ID": string,
#   "topic_of_call": string,
#   "phone": string,
#   
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

def write_patient_record(data: dict):
    print("write_patient_record")
    key = f"{data['name']['last_name']}#{data['name']['first_name']}"
    new_appointment = data["appointments"]

    new_value = {
        "insurance_payer": data["insurance_payer"],
        "insurance_id": data["insurance_id"],
        "topic_of_call": data["topic_of_call"],
        "phone": data["phone"],
        "email": data["email"],
        "last_name": data['name']["last_name"],
        "first_name": data['name']["first_name"],
        "appointments": [new_appointment]
    }

    # Load existing records or initialize
    if os.path.exists(PATIENT_RECORDS_FILE):
        with open(PATIENT_RECORDS_FILE, "r") as f:
            try:
                records = json.load(f)
            except json.JSONDecodeError:
                print("Warning: Corrupt JSON file, reinitializing.")
                records = {}
    else:
        records = {}

    if key in records:
        patient = records[key]
        for field in ["insurance_payer", "insurance_id", "topic_of_call", "phone", "email"]:
            patient[field] = new_value[field]

        # Avoid duplicate appointments
        if new_appointment not in patient.get("appointments", []):
            patient["appointments"].append(new_appointment)
        print(f"Updated patient record for {key}")
    else:
        records[key] = new_value
        print(f"Created new patient record for {key}")

    with open(PATIENT_RECORDS_FILE, "w") as f:
        json.dump(records, f, indent=2)

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
    all_doctors_appointments = {}
    for file_name in files:
        try:
            with open(file_name, "r") as f:
                data = json.load(f)  
                all_doctors_appointments[file_name] = data
        except Exception as e:
            print(f"Failed to load {file_name}: {e}")

    print(f"all_doctors_appointments: {all_doctors_appointments}")
    return all_doctors_appointments

def get_doctors_appointments_by_day_and_doctor(input:dict):
    print("get_doctors_appointments_by_day_and_doctor")
    filename = f"./data/schedule/{input['doctor_name']}.json"
    with open(filename, "r") as f:
        return json.load(f) 

def add_doctors_appointment(data: dict, patient_name: str, reason: str):
    print(f"add_doctors_appointment: {data}")

    doctor_name = data["doctor_name"]
    start_ts = data["start"] 
    end_ts = data["end"]     

    start_dt = datetime.fromisoformat(start_ts)
    end_dt = datetime.fromisoformat(end_ts)

    date_str = start_dt.date().isoformat()          
    start_time = start_dt.strftime("%H:%M")         
    end_time = end_dt.strftime("%H:%M")             

    new_uuid = str(uuid.uuid4())

    url_path = f"data/schedule/{doctor_name}.json"
    if not os.path.exists(url_path):
        raise FileNotFoundError(f"No schedule found for {doctor_name}")

    with open(url_path, "r") as f:
        schedule = json.load(f)

    slots = schedule.get(date_str, {})
    slots[new_uuid] = {
        "available": False,
        "start": start_time,
        "end": end_time,
        "patient": patient_name,
        "reason": reason
    }
    schedule[date_str] = slots

    with open(url_path, "w") as f:
        json.dump(schedule, f, indent=2)

    return True, new_uuid

def on_write_transcript(text, session):
    sid = session.get("sid")
    if sid:
        with open(f"./{sid}_transcript.txt", "a") as f:
            f.write(text + "\n")
    return text