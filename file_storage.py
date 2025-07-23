import json
import os
from datetime import datetime

PATIENT_RECORDS_FILE = os.path.join("data", "patient_records.txt")
DOCTORS_APPOINTMENTS_FILE = os.path.join("data", "doctors_appointments.txt")
# Patient Record Data
# "firstname#lastname" : {
#   "insurancePayer": string,
#   "insuranceID": string,
#   "topicOfCall": string,
#   "phone": string,
#   "email":string,
#   "schedule_appointment": referenceID to the appointment
# }


# Appointment Data
# uniqueId: {
#   "isBooked": boolean,
#   "doctor": firstname#lastname,
#   "doctorEmail": string,
#   "patient": firstname#lastname
#   "start": timestamp,
#   "end": timestamp
# }



# Appends a new patient record to the doctors_appointments file 
# in a pseudo-JSON format with a composite key "First#Last".
def write_patient_record(data: dict):
    key = f'"{data["lastName"]}#{data["firstName"]}"'
    value = {
        "insurancePayer": data["insurancePayer"],
        "insuranceID": data["insuranceID"],
        "topicOfCall": data["topicOfCall"],
        "phone": data["phone"],
        "email": data["email"],
        "schedule_appointment": data["appointmentID"]
    }

    entry = f'{key} : {json.dumps(value, indent=2)},\n'

    if not os.path.exists(DOCTORS_APPOINTMENTS_FILE):
        with open(DOCTORS_APPOINTMENTS_FILE, "w") as f:
            f.write("# Patient Record Data\n")

    with open(DOCTORS_APPOINTMENTS_FILE, "a") as f:
        f.write(entry)







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


def add_doctors_appointment(data:dict):
    doctor_name = data['doctor_name']
    start = data["start"]
    end = data["end"]
    date = data["date"]

    url_path = f"/data/schedule/{doctor_name}.json"
    if not os.path.exists(url_path):
        raise FileNotFoundError(f"No schedule found for {doctor_name}")
    
    with open(url_path, "r") as f:
        schedule = json.load(f)
    slots = schedule.get(date, [])

    for slot in slots:
        if slot["start"] == start and slot["end"] == end:
            if not slot.get("available", True):
                raise Exception("Slot is already booked")
            slot["available"] = False
            break
    else:
        raise Exception("No matching time slot found")

    with open(url_path, "w") as f:
        json.dump(schedule, f, indent=2)

    return True