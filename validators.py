import re

PHONE_REGEX = re.compile(r"^\+1\d{10}$")  # e.g., +14155552671
DOB_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")  # YYYY-MM-DD
INSURANCE_REGEX = re.compile(r"^[A-Z0-9]{5,15}$", re.IGNORECASE)
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def validate_phone(phone: str):
    if not PHONE_REGEX.match(phone):
        return False, "Invalid phone format. Use +1XXXXXXXXXX"
    return True, ""

def validate_dob(dob: str):
    if not DOB_REGEX.match(dob):
        return False, "Invalid date of birth format. Use YYYY-MM-DD"
    return True, ""

def validate_insurance_id(insurance_id: str):
    if not INSURANCE_REGEX.match(insurance_id):
        return False, "Insurance ID must be 5-15 alphanumeric characters"
    return True, ""

def validate_email(email: str):
    if not EMAIL_REGEX.match(email):
        return False, "Invalid email format"
    return True, ""

def validate_regex(text: str, type: str):
    match type:
        case "phone":
            if not PHONE_REGEX.match(text):
                return False, "Invalid phone format. Use +1XXXXXXXXXX"
        case "email":
            if not EMAIL_REGEX.match(text):
                return False, "Invalid email format"
        case "insurance":
            if not INSURANCE_REGEX.match(text):
                return False, "Insurance ID must be 5-15 alphanumeric characters"
        case "dob":
            if not DOB_REGEX.match(text):
                return False, "Invalid date of birth format. Use YYYY-MM-DD"
    return True, ""
