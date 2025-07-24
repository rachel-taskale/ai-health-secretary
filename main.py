import asyncio
import logging
import atexit
import signal
import threading
from app import app
from config import config
import assemblyai as aai
from typing import Type

from assemblyai.streaming.v3 import (
    BeginEvent,
    StreamingClient,
    StreamingClientOptions,
    StreamingError,
    StreamingEvents,
    StreamingParameters,
    StreamingSessionParameters,
    TerminationEvent,
    TurnEvent,
)

# Optional cleanup
try:
    import multiprocessing.resource_tracker
    atexit.register(lambda: multiprocessing.resource_tracker._resource_tracker._cleanup())
except Exception:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def on_begin(self: Type[StreamingClient], event: BeginEvent):
    print(f"Session started: {event.id}")


def on_turn(self: Type[StreamingClient], event: TurnEvent):
    print(f"{event.transcript} ({event.end_of_turn})")
    if event.end_of_turn and not event.turn_is_formatted:
        self.set_params(StreamingSessionParameters(format_turns=True))


def on_terminated(self: Type[StreamingClient], event: TerminationEvent):
    print(f"Session terminated: {event.audio_duration_seconds} seconds")


def on_error(self: Type[StreamingClient], error: StreamingError):
    print(f"Error occurred: {error}")


def run_streaming_agent():
    client = StreamingClient(
        StreamingClientOptions(
            api_key=config.assemblyai.api_key,
            api_host="streaming.assemblyai.com",
        )
    )

    client.on(StreamingEvents.Begin, on_begin)
    client.on(StreamingEvents.Turn, on_turn)
    client.on(StreamingEvents.Termination, on_terminated)
    client.on(StreamingEvents.Error, on_error)

    client.connect(
        StreamingParameters(sample_rate=16000, format_turns=True)
    )

    try:
        stream = aai.extras.MicrophoneStream(sample_rate=16000)
        client.stream(stream)
    except KeyboardInterrupt:
        print("Streaming agent interrupted.")
    finally:
        client.disconnect(terminate=True)


async def main():
    loop = asyncio.get_running_loop()

    # Graceful shutdown hook
    def shutdown():
        print("Shutting down...")

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)

    # Run agent in a thread
    agent_thread = threading.Thread(target=run_streaming_agent, daemon=True)
    agent_thread.start()

    try:
        await app.run_task(port=5002)
    finally:
        shutdown()
        agent_thread.join(timeout=3)


if __name__ == "__main__":
    asyncio.run(main())
