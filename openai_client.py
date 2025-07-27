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
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful and accurate medical secretary with expertise in health insurance"},
                {"role": "user", "content": user_text}
            ]
        )
        return response.choices[0].message.content.strip()
