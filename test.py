import os
import uuid
import openai
from validators import validate_email
from file_storage import append_patient_record
from speech_services import synthesize_speech, transcribe_audio  # assumes this exists


def generate_voice_file(output_path: str) -> str:
    # Generate speech and move it to the desired output path
    tmp_path = synthesize_speech("My email address is rachel dot taskale at gmail dot com")
    os.rename(tmp_path, output_path)
    return output_path

def main():
    audio_file = "./test_wavs/email_input.wav"
    generate_voice_file(audio_file)

    text = transcribe_audio(audio_file)
    print("Transcript:", text)

    valid, error = validate_email(text)
    if valid:
        print("✅ Valid email:", text)
        append_patient_record({"email": text})
    else:
        print("❌ Invalid:", error)

if __name__ == "__main__":
    main()
