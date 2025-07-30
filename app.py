from livekit import agents
from livekit.agents import AgentSession, Agent, function_tool
from livekit.plugins import assemblyai, openai, deepgram
from livekit.agents import RoomInputOptions

import asyncio
from speech_services import on_transcript
from helpers import convert_appointments_to_natural_language, infer_address_with_llm, next_prompt_type
from file_storage import get_doctors_appointments


MAX_RETRIES = 10


class HealthcareAssistant(Agent):
    def __init__(self, tools) -> None:
        instructions = """
        You are a professional healthcare assistant. Follow this conversation flow, do not skip any steps
        
        1. Ask for patient's full name
        2. Ask for insurance member name
        3. Ask for insurance member id
        4. Ask why they are calling the medical office today
        5. Ask for home address - USE buffer_address_input tool for each user response
                - await validate_full_address(text)
        6. Ask for their phone number
        7. Ask for their email
        8. Help the caller schedule the appointment from the available times. In this step
            use the tool get_available_appointments to list all the available appointments
            in the next two weeks
        9. Conclude the call and communicate to the caller that their appointment has been scheduled and should
            check their email for a confirmation email

        IMPORTANT VALIDATION STEPS:
        1. After each user response, call check_can_proceed to see if the response was valid
        2. Periodically call check_current_state to ensure you're on the correct step
        3. If check_current_state returns "STEP_MISMATCH", follow its guidance to correct the flow

        TOOL USAGE:
        - check_can_proceed: Returns PROCEED/STOP based on validation
        - check_current_state: Validates you're on the correct step
        - buffer_address_input: Use for address collection only
        - If PROCEED, continue to next step
        - If STOP, repeat current question with helpful guidance

        SPECIAL ADDRESS HANDLING:
        When collecting the address (step 4):
        - Call buffer_address_input with each user response
        - If it returns "PARTIAL_ADDRESS", ask them to continue
        - If it returns "COMPLETE_ADDRESS", the address is ready - proceed normally
        - The user may give their address in multiple parts, so be patient

        Keep responses under 30 words unless providing examples. Be professional and empathetic.
        Ask one question at a time and wait for their response before continuing.
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
            # Add buffering for address
            "address_buffer": "",
            "address_buffer_timeout": None,
        }


async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    @function_tool
    async def buffer_address_input(user_input: str) -> str:
        """Buffer address input pieces and return the complete address when ready"""
        print(f"🏠 BUFFER FUNCTION CALLED with input: {user_input}")
        
        current_state = assistant.session_state.get("state", "name")
        
        if current_state != "address":
            return "Not currently collecting address information."
        
        # Add to buffer
        if assistant.session_state["address_buffer"]:
            assistant.session_state["address_buffer"] += " " + user_input
        else:
            assistant.session_state["address_buffer"] = user_input
        
        buffered_address = assistant.session_state["address_buffer"]
        print(f"🏠 Address buffer now contains: {buffered_address}")
        
        # Simple heuristic to detect if address seems complete
        has_number = any(char.isdigit() for char in buffered_address)
        has_street_words = any(word.lower() in buffered_address.lower() 
                              for word in ['street', 'st', 'avenue', 'ave', 'road', 'rd', 'lane', 'ln', 'drive', 'dr', 'way', 'court', 'ct'])
        word_count = len(buffered_address.split())
        
        if has_number and has_street_words and word_count >= 4:
            complete_address = assistant.session_state["address_buffer"]
            assistant.session_state["address_buffer"] = "" 

            cleaned_address = await infer_address_with_llm(complete_address)
            print(f"🏠 Address appears complete: {cleaned_address}")
            return f"COMPLETE_ADDRESS: {cleaned_address}"
        else:
            return f"PARTIAL_ADDRESS: I have '{buffered_address}' so far. Please continue with the rest of your address."

    @function_tool
    async def clear_address_buffer() -> str:
        """Clear the address buffer if needed"""
        assistant.session_state["address_buffer"] = ""
        print("🏠 Address buffer cleared")
        return "Address buffer cleared."


    # Define tools first, before creating the assistant
    @function_tool
    async def check_can_proceed() -> bool:
        """Check if the last response was valid and we can proceed to the next step"""
        print(f"assistant.session_state[\"last_response_valid\"]: {assistant.session_state["last_response_valid"]}")
        if assistant.session_state["last_response_valid"] == True: 
            return "PROCEED"
        return "STOP"

    @function_tool
    async def get_available_appointments() -> str:
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
    # Create assistant with the tools
    assistant = HealthcareAssistant([get_available_appointments, check_can_proceed,buffer_address_input, clear_address_buffer])
    # Add this before creating the session
    try:
        from livekit.plugins import silero
        vad_model = silero.VAD.load()
    except ImportError:
        vad_model = None
   
    session = AgentSession(
        stt=deepgram.STT(model="nova-2-phonecall", language="en"), 
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(model="tts-1", voice="nova", speed=1.0),
        vad=vad_model,  # Add this line
    )

    @session.on("conversation_item_added")
    def on_conversation_item(event):
        try:
            # Only process user messages (not agent messages)
            if event.item.role == "user" and event.item.text_content:
                user_input = event.item.text_content
                print(f"👤 User said: {user_input}")
                
                async def process_transcript():
                    try:
                        # Call our function that handles the logic extraction on the BE
                        previous_current_state = assistant.session_state["state"]
                        assistant.session_state["last_response_valid"] = False
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
                            current_state = assistant.session_state.get("state", "name")

                            # Check if the response was not valid, that would mean that we need to retry
                            if result.get("retry") == True:
                                assistant.session_state["last_response_valid"] = False

                                # Need to check if the number of times tried is beyond 3, if so then we need to close the session
                                # Can only try 3 times to get the right information
                                if assistant.session_state["retries"][current_state] >= MAX_RETRIES:
                                    print(f"❌ Max retries exceeded for {current_state}")
                                    assistant.session_state["last_response_valid"] = False
                                    await session.generate_reply(instructions="I'm having trouble understanding. Give us a call back later when you are in a better place to speak.")
                                    await session.aclose()
                                    return

                                retry_count = assistant.session_state["retries"][current_state] + 1
                                assistant.session_state["retries"][current_state] = retry_count
                                print(f"❌ Invalid info - Retry {retry_count} for {current_state}")
                            else: 
                                assistant.session_state["last_response_valid"] = True
                                assistant.session_state["retries"][current_state] = 0
                                print(assistant.session_state[assistant.session_state["state"]])
                                assistant.session_state["state"] = next_prompt_type(current_state)
                                print(f"✅ Valid info - Reset retries for {current_state}")
                    
                    # If we get an exception then we will just close the session for now
                    except Exception as transcript_error:
                        assistant.session_state["last_response_valid"] = False
                        print(f"❌ Error processing transcript: {transcript_error}")
                        await session.generate_reply(instructions="I'm experiencing technical difficulties. Let me transfer you to our staff for assistance.")
                        raise transcript_error

                asyncio.create_task(process_transcript())
                    
        except Exception as e:
            print(f"❌ Error: {e}")
    
    room_input_options = RoomInputOptions(
    close_on_disconnect=True,
)

    await session.start(
        room=ctx.room, 
        agent=assistant,
        room_input_options=room_input_options
    ) 
    # Initial greeting - let the LLM start based on instructions
    await session.generate_reply(
        instructions="Start the conversation by greeting the patient and start asking them questions to follow our steps")


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint, 
            agent_name="ai-telephony-agent"
        )
    )