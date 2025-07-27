# phone_agent/twilio_handler.py
import asyncio
from asyncio.log import logger
import base64
import os
import json
import threading
import uuid
from io import BytesIO
import audio_processor
from speech_services import on_transcript
import numpy as np


class TwilioMediaStreamHandler:
    def __init__(self, assembly_client, openai_client, audio_dir, host_url, ws):
        print("TwilioMediaStreamHandler initialized")
        self.assembly_client = assembly_client
        self.openai_client = openai_client
        self.audio_dir = audio_dir
        self.host_url = host_url
        self.stream_sid = None
        self.sessions = {}
        self.call_sid = None
        self.ws = ws
        


    # This function handles the start event of the media stream
    def handle_start(self, data):
        """Handle stream start"""
        start_data = data.get('start', {})
        self.stream_sid = start_data.get('streamSid')
        self.call_sid = start_data.get('callSid')
        
        logger.info(f"Stream started - SID: {self.stream_sid}")
        logger.info(f"Call SID: {self.call_sid}")
        logger.info(f"Tracks: {start_data.get('tracks')}")
        self.sessions[self.stream_sid] = {
            "state": "listening",
            "retries": {},
            "call_sid": self.call_sid
        }
        
        try:
            print("🎤 Starting AssemblyAI client...")
            self.assembly_client.start(
                on_transcript=lambda text: asyncio.create_task(
                    self.handle_transcript(text, self.stream_sid)
                )
            )
            print(f"✅ Stream started successfully: {self.stream_sid}")
        except Exception as e:
            print(f"❌ Error starting AssemblyAI client: {e}")
            import traceback
            traceback.print_exc()
        
        # Start the conversation flow
        # self.start_conversation()


    def handle_connected(self, data):
        """Handle WebSocket connection"""
        logger.info("WebSocket connected")
        logger.info(f"Protocol: {data.get('protocol')}, Version: {data.get('version')}")


    def is_audio_active(self, audio_bytes: bytes, threshold: float = 500) -> bool:
        """
        Uses RMS energy via numpy to detect if audio contains active speech.
        Works with 16-bit PCM mono audio (from Twilio).
        """
        if not audio_bytes:
            return False

        # Convert bytes to numpy array of int16
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
        rms = np.sqrt(np.mean(audio_np.astype(np.float32) ** 2))

        return rms > threshold
                

    def handle_media(self, data):
        """
        Handle incoming base64-encoded audio from Twilio Media Stream.
        Detects speech activity, sends clear message to interrupt playback,
        and streams audio to AssemblyAI if speaking.
        """
        if not self.assembly_client:
            print("❌ AssemblyAI client not initialized")
            return

        try:
            payload = data.get("media", {}).get("payload")
            if not payload:
                print("⚠️ No media payload found")
                return

            audio_data = base64.b64decode(payload)

            # Check for speech activity
            if self.is_audio_active(audio_data):
                if not self.is_speaking:
                    print("🎙️ User started speaking")
                    self.is_speaking = True
                    self.send_clear_message()

                    # Cancel any silence timer if it was previously set
                    if self.silence_timer:
                        self.silence_timer.cancel()

                self.speech_buffer.append(audio_data)
                self.assembly_client.send_audio(audio_data)
            else:
                # Start silence timer only if we were speaking before
                if self.is_speaking and not self.silence_timer:
                    print("🤫 Detected silence — starting timer")
                    self.silence_timer = threading.Timer(1.0, self.process_speech_end)
                    self.silence_timer.start()

        except Exception as e:
            print(f"❌ Error in handle_media: {e}")


    # This function handles the mark event which indicates that an audio playback has completed
    # it logs the completion and prepares for the next user input
    def handle_mark(self, data):
        """Handle mark events (audio playback completion)"""
        mark = data.get('mark', {})
        name = mark.get('name')
        logger.info(f"Audio playback completed: {name}")
        
        # After any prompt finishes playing, we're ready to listen
        if name.endswith('_complete'):
            logger.info("Ready to listen for user response...")



    # this function plays audio files stored in the audio_files directory
    # it uses the audio_processor to get the base64 encoded audio data
    # and sends it to Twilio for playback
    def play_audio(self, audio_name: str):
        """
        Sends a static .ulaw audio file over the Twilio media WebSocket.
        """
        if not self.stream_sid or not self.ws:
            logger.error("Missing stream SID or WebSocket connection")
            return

        file_path = os.path.join("audio_files", f"{audio_name}.ulaw")
        if not os.path.isfile(file_path):
            logger.error(f"Audio file not found: {file_path}")
            return

        try:
            with open(file_path, "rb") as f:
                audio_data = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.exception(f"Failed to read audio file: {e}")
            return

        # Create Twilio media and mark messages
        media_msg = {
            "event": "media",
            "streamSid": self.stream_sid,
            "media": {
                "payload": audio_data
            }
        }

        mark_msg = {
            "event": "mark",
            "streamSid": self.stream_sid,
            "mark": {
                "name": f"{audio_name}_complete"
            }
        }

        try:
            self.ws.send(json.dumps(media_msg))
            self.ws.send(json.dumps(mark_msg))
            logger.info(f"✅ Sent audio: {audio_name}")
        except Exception as e:
            logger.exception(f"❌ Failed to send audio: {e}")


    # This function stops the current media stream and cleans up the session
    # it sends a stop message to AssemblyAI and clears the session state
    # it also handles any cleanup required for the WebSocket connection
    async def stop_stream_ws(self, data):
        """Handle WebSocket stream stop event"""
        print(f"Stopping WebSocket stream: {self.stream_sid}")
        
        try:
            # Stop AssemblyAI transcription
            if hasattr(self.assembly_client, 'send_audio'):
                await self.assembly_client.send_audio(None)
            if hasattr(self.assembly_client, 'stop'):
                self.assembly_client.stop()
                
            # Clean up session
            if self.stream_sid and self.stream_sid in self.sessions:
                del self.sessions[self.stream_sid]
                
        except Exception as e:
            print(f"Error stopping stream: {e}")
        finally:
            self.stream_sid = None
            self.call_sid = None

        
    def send_clear_message(self):
        """Clear audio buffer (interrupt current playback)"""
        if not self.stream_sid:
            return
            
        clear_message = {
            "event": "clear",
            "streamSid": self.stream_sid
        }
    
        try:
            self.ws.send(json.dumps(clear_message))
            logger.info("Sent clear message - interrupted current audio")
        except Exception as e:
            logger.error(f"Error sending clear message: {e}")

    

    async def handle_transcript(self, text, stream_sid):
        """Handle transcribed text from AssemblyAI"""
        print(f"📝 User said: {text}")
        
        session_state = self.sessions.get(stream_sid)
        if not session_state:
            print(f"No session found for {stream_sid}")
            return

        try:
            # Process the transcript using your speech_services
            result, updated_session_state = await on_transcript(text, session_state)
            
            # Update session state
            self.sessions[stream_sid] = updated_session_state
            
            if result.get("end_call"):
                print("Call ending requested")
                # Handle call ending - you might want to send a final message
                # or perform cleanup here
                return
                
            # Handle audio response
            audio_path = result.get("audio_path")
            if audio_path:
                print(f"Audio response generated: {audio_path}")
                # You might want to implement logic here to play the audio
                # back through Twilio's media stream or use TwiML
                self.play_audio(audio_path)
                
        except Exception as e:
            print(f"Error handling transcript: {e}")


