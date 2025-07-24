# phone_agent/openai_client.py
import os
import uuid
from openai import OpenAI
from config import config

class OpenAIClient:
    def __init__(self, api_key, audio_dir, host_url):
        self.client = OpenAI(api_key=api_key)
        self.audio_dir = audio_dir
        self.host_url = host_url

    def chat_response(self, user_text: str) -> str:
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful receptionist at a medical clinic."},
                {"role": "user", "content": user_text}
            ]
        )
        return response.choices[0].message.content.strip()

    def synthesize_speech(self, text: str) -> str:
        response = self.client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text
        )

        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join(self.audio_dir, filename)
        with open(filepath, "wb") as f:
            f.write(response.content)

        return f"{self.host_url}/static/audio/{filename}"
