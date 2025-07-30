import requests
import json
import base64
import time
import os
import asyncio
import websockets

from validators import validate_address_with_smarty

# CONFIG
HOST = "http://localhost:5002"
WS_HOST = "ws://localhost:5002"
CALL_SID = "CA_TEST1234"
TEST_AUDIO_FILE = "test_audio.wav"  # small audio sample
EXPECTED_MP3 = f"./static/{CALL_SID}_response.mp3"
TRANSCRIPT_FILE = f"./transcript/{CALL_SID}_transcript.txt"


def create_audio_snippet():
    url = ""
    return url

def test_voice():
    print("➡️ Hitting /voice...")
    resp = requests.post(f"{HOST}/voice", data={"CallSid": CALL_SID, "From": "+1234567890"})
    assert resp.status_code == 200
    assert "<Start>" in resp.text
    print("✅ /voice responded with Start stream")

async def test_media_ws():
    print("➡️ Opening WebSocket to /media...")
    uri = f"{WS_HOST}/media?sid={CALL_SID}"

    async with websockets.connect(uri) as ws:
        # Start event
        await ws.send(json.dumps({
            "event": "start",
            "start": {
                "callSid": CALL_SID,
                "from": "+1234567890"
            }
        }))
        print("✅ Sent 'start'")

        # Simulate audio payload
        if not os.path.exists(TEST_AUDIO_FILE):
            raise FileNotFoundError(f"Missing {TEST_AUDIO_FILE}")

        with open(TEST_AUDIO_FILE, "rb") as f:
            audio_bytes = f.read()

        encoded_audio = base64.b64encode(audio_bytes).decode("utf-8")

        await ws.send(json.dumps({
            "event": "media",
            "media": {
                "payload": encoded_audio
            }
        }))
        print("✅ Sent 'media'")

        await ws.send(json.dumps({"event": "stop"}))
        print("✅ Sent 'stop'")

    print("⏳ Waiting for response mp3 and transcript...")

    for _ in range(10):
        if os.path.exists(EXPECTED_MP3) and os.path.exists(TRANSCRIPT_FILE):
            print("✅ MP3 + transcript file created")
            break
        time.sleep(1)
    else:
        raise AssertionError("❌ MP3 or transcript file was not created.")

    with open(TRANSCRIPT_FILE) as f:
        transcript = f.read().strip()
        assert len(transcript) > 0
        print("📄 Transcript content:")
        print(transcript)

def test_play():
    print("➡️ Hitting /play...")
    resp = requests.post(f"{HOST}/play", data={"CallSid": CALL_SID})
    assert resp.status_code == 200
    assert "<Play>" in resp.text
    assert "<Redirect>" in resp.text
    print("✅ /play returned TwiML with Play + Redirect")





if __name__ == "__main__":
    test_voice()
    asyncio.run(test_media_ws())
    test_play()
    print("\n🎉 All tests passed.")