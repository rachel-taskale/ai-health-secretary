from livekit import agents
from livekit.agents import AgentSession, Agent, function_tool
from livekit.plugins import assemblyai, openai
import asyncio
from speech_services import on_transcript
from helpers import convert_appointments_to_natural_language
from file_storage import get_doctors_appointments
MAX_RETRIES = 3


class HealthcareAssistant(Agent):
    def __init__(self, tools) -> None:
        instructions = """
        You are a professional healthcare assistant. Follow this conversation flow:
        
        1. Ask for the patient's full name
        2. Ask for their insurance member name
        3. Ask for their insurance member id
        4. Ask for their home address
        5. Ask them why they are calling the medical office today
        6. Ask them for their phone number
        7. Ask them for their email
        8. Help the caller schedule the appointment from the available times. In this step
            use the tool get_available_appointments to list all the available appointments
            in the next two weeks
        9. Conclude the call and communicate to the caller that their appointment has been scheduled and should
            check their email for a confirmation email
        
        Keep responses under 25 words. Be professional and empathetic.
        Ask one question at a time and wait for their response before continuing.
        Before continuing onto the next prompt, check the response of the tool check_can_proceed, if returns false then must retry the last prompt
        Only respond when explicitly instructed to do so.
        """
        
        super().__init__(
            instructions=instructions,
            tools=tools
        )
        
        self.session_state = {
            "state": "name", 
            "last_response_valid": True,
            "retries": {"name": 0, "insurance_payer": 0, "insurance_id": 0, "address": 0, "topic_of_call": 0, "phone": 0, "email": 0, "schedule_appointment": 0},
            "patient_name": None,
            "insurance_payer": None,
            "insurance_id": None,
            "address": None,
            "topic_of_call": None,
            "phone": None,
            "email": None,
            "appointment_data": None,
        }



async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()
    session = AgentSession(
        stt=assemblyai.STT(),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(model="tts-1", voice="nova", speed=1.0),
    )

    @function_tool
    async def check_can_proceed():
        return assistant.session_state["last_response_valid"]

    # Tool function to get available appointments
    @function_tool
    async def get_available_appointments():
        """Get all available appointment slots for the next two weeks"""
        try:
            print("📅 Fetching available appointments...")
            doctors_appointments = get_doctors_appointments()
            appointments_text = convert_appointments_to_natural_language(doctors_appointments)
            print(f"📋 Available appointments: {appointments_text}")
            return f"Here are the available appointment times for the next two weeks: {appointments_text}. Which time works best for you?"
        except Exception as e:
            print(f"❌ Error getting appointments: {e}")
            return "I'm having trouble accessing our appointment system. Let me transfer you to our scheduling team."

    assistant = HealthcareAssistant([get_available_appointments, check_can_proceed])



    @session.on("user_input_transcribed")
    def on_conversation_item(event):
        try:
            if event.is_final and event.transcript:
                user_input = event.transcript
                print(f"👤 User said: {user_input}")
                async def process_transcript():
                    try:
                        # Call our function that handles the logic extraction on the BE
                        result, updated_session_state = await on_transcript(user_input, assistant.session_state)
                        assistant.session_state = updated_session_state            
                        print(f"🔍 Result: {result}")
                        print(f"📊 State: {assistant.session_state}")
                        
                        # If we are ending the call then close the session
                        if result.get("end_call", False):
                            print("🔚 Call ending")
                            await session.generate_reply(
                                    instructions="Thank the patient and confirm their appointment has been scheduled. Tell them to check their email for confirmation. End the call politely."
                                )
                            await session.aclose()

                        else:
                            # Check if the response was not valid, that would mean that we need to retry
                            if result.get("retry") == True:
                                # Need ot check if the number of times tried is beyond 3, if so then we need to close the session
                                # Can only try 3 times to get the right information
                                current_state = assistant.session_state.get("state", "name")

                                if assistant.session_state["retries"][current_state] > MAX_RETRIES:
                                      raise transcript_error

                                retry_count = assistant.session_state["retries"][current_state] + 1
                                assistant.session_state["retries"][current_state] = retry_count
                                assistant.session_state["last_response_valid"] = False
                                print(f"❌ Invalid info - Retry {retry_count} for {current_state}")
                            else: 
                                assistant.session_state["last_response_valid"] = True
                                assistant.session_state["retries"][current_state] = 0
                    
                    # If we get an exception then we will just close the session for now
                    except Exception as transcript_error:
                        session.generate_reply(transcript_error)
                        print(f"❌ Error processing transcript: {transcript_error}")
                        await session.aclose()

                asyncio.create_task(process_transcript())
                    
        except Exception as e:
            print(f"❌ Error: {e}")

    await session.start(room=ctx.room, agent=assistant)
    
    # Initial greeting - let the LLM start based on instructions
    await session.generate_reply(
        instructions="Start the conversation by greeting the patient and asking for their full name as specified in step 1."
    )


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint, 
            agent_name="ai-telephony-agent"
        )
    )