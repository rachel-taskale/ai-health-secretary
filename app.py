import base64
import json
import logging
import os
import threading
from assemblyai_client import AssemblyAIClient
from config import config
from flask import Flask
from flask_sockets import Sockets
from openai_client import OpenAIClient

from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler

from twilio_media_streams import TwilioMediaStreamHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
sockets = Sockets(app)


    
 

@sockets.route('/media')
def media_stream(ws):
    """Handle WebSocket media stream"""
    logger.info("Media stream connection established")
    assembly_client = AssemblyAIClient(config.assemblyai.api_key)
    openai_client = OpenAIClient(config.openai.api_key)
    handler = TwilioMediaStreamHandler(assembly_client, openai_client, "./static/audio", os.getenv("HOST_URL"), ws)
    
    message_count = 0
    
    while not ws.closed:
        message = ws.receive()
        if message is None:
            logger.info("No message received...")
            continue
        
        message_count += 1
        
        try:
            # Parse JSON message
            data = json.loads(message)
            event = data.get('event')
            
            # Route to appropriate handler
            if event == 'connected':
                print(f"WebSocket connected: {data}")
                handler.handle_connected(data)
            elif event == 'start':
                print(f"Stream started: {data}")
                handler.handle_start(data)
            elif event == 'media':
                handler.handle_media(data)
            elif event == 'mark':
                handler.handle_mark(data)
            elif event == 'stop':
                handler.stop_stream_ws({"streamSid": handler.stream_sid})

                break
            # Note: Removed DTMF handler since we're voice-only
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    logger.info(f"Media stream closed. Processed {message_count} messages")

if __name__ == '__main__':
    app.logger.setLevel(logging.DEBUG)
    
    HTTP_SERVER_PORT = 5002
    
    logger.info("Starting Twilio Voice-Only Media Stream server...")
    logger.info(f"Server will be available at: ws://localhost:{HTTP_SERVER_PORT}/media")
    logger.info("\nRequired audio files in 'audio_files/' directory:")
    logger.info("- welcome.mp3 (initial greeting)")
    logger.info("- ask_name.mp3 ('Please tell me your full name')")
    logger.info("- ask_member_id.mp3 ('Please tell me your insurance member ID')")
    logger.info("- ask_dob.mp3 ('Please tell me your date of birth')")
    logger.info("- confirm_info.mp3 ('Let me confirm your information...')")
    logger.info("- goodbye.mp3 ('Thank you, goodbye')")
    logger.info("\nSetup steps:")
    logger.info("1. Add your MP3 files to the 'audio_files/' directory")
    logger.info("2. Use ngrok to expose this server: ngrok http 5002")
    logger.info("3. Update your TwiML to use: wss://your-ngrok-url.ngrok.io/media")
    
    server = pywsgi.WSGIServer(('', HTTP_SERVER_PORT), app, handler_class=WebSocketHandler)
    server.serve_forever()