import asyncio
from speech_services import on_transcript

cases = {
    "name" :"Hi, my... my... my name is rachel taskale",
    "insurance_payer": "john smith",
    "insurance_id": "the member id is 123456723d",
    "address":"my address is twelve fourty five hayes street california 94117",
    "topic": "I am calling for an annual check up",
    "phone":"my phone number is 19177012642",
    "email" : "my email is rachel taskale at gmail dot com",
    "schedule_appointment": "august 15th at 1:30pm works"
}

async def test_on_transcript():
    session_state = {"state":"name"}
    while session_state["state"]!= "done":
        
        print(f"\n🧪 Testing state: '{session_state["state"]}' with input: \"{cases[session_state["state"]]}\"")

        result, session_state = await on_transcript(cases[session_state["state"]], session_state)
        print("🔁 Result:", result)
        print("📦 Session State:", session_state)

if __name__ == "__main__":
    asyncio.run(test_on_transcript())
