import asyncio
import json
import base64
from speech_services import audio_generator, stream_audio_to_assemblyai, on_transcript


CALL_SESSIONS = {}

def setup_routes(app, sock):
    @sock.route("/media")
    def media_stream(ws):
        sid = None
        audio_queue = asyncio.Queue()       
        audio_generator()

        while True:
            msg = ws.receive()
            if not msg:
                break

            try:
                data = json.loads(msg)
                event = data.get("event")

                if event == "start":
                    sid = data["start"]["callSid"]
                    print(f"[{sid}] Call started")
                    CALL_SESSIONS[sid] = {
                        "state": "email",
                        "phone": data["start"]["from"], 
                    }
                    asyncio.create_task(stream_audio_to_assemblyai(audio_generator(),lambda text: on_transcript(text, CALL_SESSIONS[sid])))

                elif event == "media":
                    audio_b64 = data["media"]["payload"]
                    audio_bytes = base64.b64decode(audio_b64)
                    audio_queue.put_nowait(audio_bytes)

                elif event == "stop":
                    print(f"[{sid}] Call ended")
                    audio_queue.put_nowait(None)
                    break

            except Exception as e:
                print("Error:", e)

