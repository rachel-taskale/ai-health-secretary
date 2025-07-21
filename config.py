from dataclasses import dataclass, field
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class TwilioConfig:
    sid: str
    api_key: str
    phone_number: str

@dataclass
class AssemblyAIConfig:
    api_key: str

@dataclass
class OpenAIConfig:
    api_key: str

@dataclass
class AppConfig:
    twilio: TwilioConfig = field(default_factory=lambda: TwilioConfig(
        sid=os.getenv("TWILIO_ACCOUNT_SID"),
        api_key=os.getenv("TWILIO_AUTH_TOKEN"),
        phone_number=os.getenv("TWILIO_PHONE_NUMBER")
    ))
    openai: OpenAIConfig = field(default_factory=lambda: OpenAIConfig(
        api_key=os.getenv("OPENAI_API_KEY")
    ))
    assemblyai: AssemblyAIConfig = field(default_factory=lambda: AssemblyAIConfig(
        api_key=os.getenv("ASSEMBLYAI_API_KEY")
    ))

config = AppConfig()