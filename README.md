## Summary
An AI phone agent that will prompt and listen to the caller's responses in order to collect information such as full name, insurance information, contact information and schedule an appointment for the caller. I wanted this to be the most barebones MVP version I could make while still meeting all the requirements so use text files as my mock database where I have multiple "doctors" taht you can schedule appointments with

## Tech Stack
For calling and audio extraction:
- Phone number hosted on Twilio
- Redirect SIP to Livekit meeting room with agent
- Stream and transcribe audio using AssemblyAI 

For extracting information from the transcript:
- Pipe data into OpenAI then validate the formatting using regex

For address verification
- Extract and infer address in OpenAI
- Validate address exists with SmartyStreets
