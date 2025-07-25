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



# Appends a new patient record to the doctors_appointments file 
# in a pseudo-JSON format with a composite key "First#Last".
def write_patient_record(data: dict):
    print("write_patient_record")
    key = f'"{data["last_name"]}#{data["first_name"]}"'
    new_appointment = data["appointments"]

    new_value = {
        "insurance_payer": data["insurance_payer"],
        "insurance_id": data["insurance_id"],
        "topic_of_call": data["topic_of_call"],
        "phone": data["phone"],
        "email": data["email"],
        "last_name": data["last_name"],
        "first_name":data["first_name"],
        "appointments": [new_appointment]
    }

    # Create file if it doesn't exist
    if not os.path.exists(DOCTORS_APPOINTMENTS_FILE):
        with open(DOCTORS_APPOINTMENTS_FILE, "w") as f:
            f.write("# Patient Record Data\n")

    updated = False
    new_lines = []

    with open(DOCTORS_APPOINTMENTS_FILE, "r") as f:
        for line in f:
            if line.strip().startswith(key):
                try:
                    existing_json_str = line.split(":", 1)[1].rstrip(",\n")
                    existing_data = json.loads(existing_json_str)

                    # Update fields if changed
                    for field in ["insurance_payer", "insurance_id", "topic_of_call", "phone", "email"]:
                        existing_data[field] = new_value[field]

                    # Append appointment if it's new
                    if new_appointment not in existing_data.get("appointments", []):
                        existing_data["appointments"].append(new_appointment)

                    # Reconstruct line
                    updated_line = f"{key} : {json.dumps(existing_data, indent=2)},\n"
                    new_lines.append(updated_line)
                    updated = True
                except Exception as e:
                    print(f"Failed to parse line for {key}: {e}")
                    new_lines.append(line)
            else:
                new_lines.append(line)

    if not updated:
        new_line = f'{key} : {json.dumps(new_value, indent=2)},\n'
        new_lines.append(new_line)

    with open(DOCTORS_APPOINTMENTS_FILE, "w") as f:
        f.writelines(new_lines)

    print(f"{'Updated' if updated else 'Created'} patient record for {key}")
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
            all_doctors_appointments[file_name] = data

    print(f"all_doctors_appointments: {all_doctors_appointments}")
    return all_doctors_appointments

def get_doctors_appointments_by_day_and_doctor(input:dict):
    filename = f"./data/schedule/{input['doctor_name']}.json"
    with open(filename, "r") as f:
        data = json.load(f) 
        return data


def add_doctors_appointment(data: dict, patient_name: str, reason:str):
    print("add_doctors_appointment")
    doctor_name = data['doctor_name']
    start = data["start"]  
    end = data["end"]      

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



# SESSIONS_FILE = "./data/call_sessions.json"
# # Saving call sessions here
# def load_sessions():
#     if not os.path.exists(SESSIONS_FILE):
#         return {}
#     with os.F_LOCK, open(SESSIONS_FILE, "r") as f:
#         return json.load(f)

# def save_sessions(sessions):
#     with os.F_LOCK, open(SESSIONS_FILE, "w") as f:
#         json.dump(sessions, f, indent=2)

# def get_session(call_sid):
#     sessions = load_sessions()
#     return sessions.get(call_sid)

# def update_session(call_sid, data):
#     sessions = load_sessions()
#     sessions[call_sid] = data
#     save_sessions(sessions)



# def on_write_transcript(text, session):
#     sid = session.get("sid")
#     if sid:
#         with open(f"./{sid}_transcript.txt", "a") as f:
#             f.write(text + "\n")
#     return text