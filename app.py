from livekit.agents import Agent, AgentSession, RoomInputOptions, WorkerOptions, cli
from livekit.plugins import assemblyai, openai
from dotenv import load_dotenv
import os, asyncio
from helpers import get_next_agent_response
from speech_services import on_transcript 

load_dotenv()

class PhoneAgent(Agent):
    def __init__(self):
        super().__init__(instructions="You are a helpful assistant for patients. Extract info like insurance or appointment scheduling.")
        self.session_state = {"state": "name", "retries": {}}

    async def on_user_speech_committed(self, user_msg, ctx):
        text = user_msg.content
        print(f"📞 User said: {text}")
        
        try:
            result, updated_state = await on_transcript(text, self.session_state)
            self.session_state = updated_state
        except Exception as e:
            print(f"❌ Error in on_transcript: {e}")
            result = {"retry": True, "response_text": "Sorry, I didn't catch that. Could you repeat?"}

        if result.get("end_call"):
            print("📞 Call ending...")
            if result.get("confirmed"):
                return "Thank you! Your information has been recorded. Goodbye!"
            else:
                return "I apologize, but we couldn't complete the process. Please call back when you're ready."

        response_text = result.get("response_text", "Thank you. Got it.")
        print(f"📞 Agent will speak: {response_text}")
        return response_text

    async def on_connected(self, ctx):
        """Called when the agent connects to the room - send welcome message"""
        
        try:
            welcome_prompt = get_next_agent_response(self.session_state["state"])
            print(f"📞 Agent will speak welcome: {welcome_prompt}")
            return welcome_prompt
        except Exception as e:
            print(f"❌ Error getting welcome prompt: {e}")
            return "Hello! I'm here to help you with your healthcare needs. Let's get started."

async def entrypoint(ctx):
    await ctx.connect()

    session = AgentSession(
        stt=assemblyai.STT(),  
        llm=None,              
        tts=openai.TTS()       
    )

    await session.start(
        agent=PhoneAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions()
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name="ai-telephony-agent"))