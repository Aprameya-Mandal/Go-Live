import os
import sys
import asyncio
from typing import cast
import numpy as np
from openwakeword import utils
from openwakeword.model import Model
from google import genai
from google.genai import types

from PyQt6.QtWidgets import QApplication
import qasync

from gui import FloatingBubbleWindow, SystemTrayManager
from audio_handler import AudioHandler
from vision import ScreenCaptureManager
import tools

MODEL_NAME = os.getenv(
    "GEMINI_LIVE_MODEL", "gemini-2.5-flash-native-audio-latest"
)
WAKE_WORD_MODEL = "hey_jarvis"
WAKE_THRESHOLD = 0.55


class DesktopAssistantApp:
    def __init__(self, qapp):
        self.qapp = qapp
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")

        self.client = genai.Client(api_key=api_key)
        self.audio = AudioHandler()
        self.vision = ScreenCaptureManager(target_fps=1.0)

        # Setup wake word model
        utils.download_models()
        self.oww = Model(wakeword_models=[WAKE_WORD_MODEL], inference_framework="onnx")

        # Setup GUI & Tray
        self.bubble = FloatingBubbleWindow()
        self.tray = SystemTrayManager(self.qapp)

        # Connect Tray & GUI Signals
        self.tray.show_requested.connect(self.trigger_manual_activation)
        self.tray.hide_requested.connect(self.dismiss_live_session)
        self.tray.quit_requested.connect(self.quit)
        self.bubble.dismiss_requested.connect(self.dismiss_live_session)

        # Set dismiss callback in tools.py
        tools.set_dismiss_callback(self.dismiss_live_session)

        self.is_live = False
        self.session_stop_event = None

    def trigger_manual_activation(self):
        """Called when user selects 'Show' from tray."""
        if not self.is_live:
            asyncio.create_task(self._activate_session_flow())

    def dismiss_live_session(self):
        """Dismisses the floating bubble and returns to passive listening."""
        if self.session_stop_event and not self.session_stop_event.is_set():
            self.session_stop_event.set()
        self.bubble.hide_bubble()
        self.is_live = False

    def quit(self):
        self.dismiss_live_session()
        self.audio.close()
        self.qapp.quit()

    async def run_wake_word_loop(self):
        """Passively listens in background with low CPU consumption."""
        self.audio.start_mic()
        loop = asyncio.get_event_loop()

        while True:
            if not self.is_live:
                raw_chunk = await loop.run_in_executor(None, self.audio.read_mic_chunk)
                if raw_chunk:
                    audio_data = np.frombuffer(raw_chunk, dtype=np.int16)
                    prediction = cast(dict[str, float], self.oww.predict(audio_data))
                    score = prediction.get(WAKE_WORD_MODEL, 0.0)

                    if score >= WAKE_THRESHOLD:
                        self.oww.reset()
                        await self._activate_session_flow()

            await asyncio.sleep(0.01)

    async def _activate_session_flow(self):
        """Wakes up the assistant, displays the floating bubble, and starts Gemini Live."""
        self.is_live = True
        self.audio.play_chime()
        self.bubble.show_bubble()
        self.bubble.set_state("LISTENING")

        try:
            while self.is_live:
                await self.start_gemini_live_session()

                # Keep the assistant active if Live closes unexpectedly.
                if self.is_live:
                    self.bubble.show_bubble()
                    self.bubble.set_state("LISTENING")
                    await asyncio.sleep(0.5)
        finally:
            if not self.is_live:
                self.bubble.set_state("IDLE")
                self.bubble.hide_bubble()

    async def start_gemini_live_session(self):
        self.audio.start_speaker()
        stop_event = asyncio.Event()
        self.session_stop_event = stop_event

        config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            system_instruction=types.Content(
                parts=[
                    types.Part(
                        text=(
                            "You are a helpful Windows voice assistant with real-time screen vision. "
                            "When the user says 'hide', 'go to sleep', or 'dismiss', call the dismiss_assistant tool immediately. "
                            "Keep your spoken answers concise, direct, and conversational."
                        )
                    )
                ]
            ),
            tools=tools.SYSTEM_TOOLS,
        )

        try:
            async with self.client.aio.live.connect(model=MODEL_NAME, config=config) as session:
                mic_task = asyncio.create_task(self._stream_mic(session))
                screen_task = asyncio.create_task(self.vision.stream_screen_loop(session))
                recv_task = asyncio.create_task(self._handle_server_stream(session))

                await stop_event.wait()

                self.vision.stop()
                mic_task.cancel()
                screen_task.cancel()
                recv_task.cancel()
                await asyncio.gather(mic_task, screen_task, recv_task, return_exceptions=True)

        except Exception as e:
            print(f"[Gemini Live Session Exception] {e}")
        finally:
            self.vision.stop()
            self.audio.stop_speaker()

    async def _stream_mic(self, session):
        loop = asyncio.get_event_loop()
        stop_event = self.session_stop_event
        if stop_event is None:
            return
        try:
            while not stop_event.is_set():
                raw_chunk = await loop.run_in_executor(None, self.audio.read_mic_chunk)
                if raw_chunk:
                    await session.send_realtime_input(
                        audio=types.Blob(data=raw_chunk, mime_type="audio/pcm;rate=16000")
                    )
                await asyncio.sleep(0.001)
        except asyncio.CancelledError:
            pass

    async def _handle_server_stream(self, session):
        try:
            async for response in session.receive():
                # Server sent content / audio
                server_content = response.server_content
                if server_content is not None and server_content.model_turn is not None:
                    self.bubble.set_state("SPEAKING")
                    for part in server_content.model_turn.parts:
                        if part.inline_data:
                            self.audio.play_audio(part.inline_data.data)

                    # Return to listening once turn is complete
                    if server_content.turn_complete:
                        self.bubble.set_state("LISTENING")

                # Server requested tool execution
                if response.tool_call is not None:
                    self.bubble.set_state("PROCESSING")
                    responses = []
                    for fc in response.tool_call.function_calls:
                        res = await tools.execute_tool(fc.name, fc.args)
                        responses.append(
                            types.FunctionResponse(name=fc.name, id=fc.id, response=res)
                        )

                    if hasattr(session, "send_tool_response"):
                        await session.send_tool_response(function_responses=responses)
                    else:
                        await session.send(
                            input=types.LiveClientToolResponse(function_responses=responses)
                        )

                    self.bubble.set_state("LISTENING")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[Receive Stream Error] {e}")
        finally:
            stop_event = self.session_stop_event
            if stop_event is not None and not stop_event.is_set():
                stop_event.set()


def main():
    qapp = QApplication(sys.argv)
    qapp.setQuitOnLastWindowClosed(False)  # Allows running in system tray when bubble hides

    loop = qasync.QEventLoop(qapp)
    asyncio.set_event_loop(loop)

    assistant = DesktopAssistantApp(qapp)

    with loop:
        loop.create_task(assistant.run_wake_word_loop())
        loop.run_forever()


if __name__ == "__main__":
    main()