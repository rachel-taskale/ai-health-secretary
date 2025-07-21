import json
import os
from datetime import datetime

PATIENT_CALLS_FILE = os.path.join("data", "patient_calls.txt")
FAKE_PROVIDERS_FILE = os.path.join("data", "fake_providers.txt")

def append_patient_record(data: dict):
    with open(PATIENT_CALLS_FILE, "a") as f:
        f.write(json.dumps(data) + "\n")

def load_patient_records():
    if not os.path.exists(PATIENT_CALLS_FILE):
        return []
    with open(PATIENT_CALLS_FILE, "r") as f:
        return [json.loads(line) for line in f if line.strip()]

def load_fake_providers():
    if not os.path.exists(FAKE_PROVIDERS_FILE):
        return []
    with open(FAKE_PROVIDERS_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]
# 