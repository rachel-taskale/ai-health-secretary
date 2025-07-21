def get_next_prompt(state):
    prompts = {
        "email": "What is your email address?",
        "dob": "What is your date of birth?",
        "insurance": "Please provide your insurance ID.",
        "done": "Thanks. You will receive a confirmation shortly."
    }
    return prompts.get(state, "")
