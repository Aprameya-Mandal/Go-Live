import pyaudiowpatch as pyaudio
import numpy as np

MIC_FORMAT = pyaudio.paInt16
MIC_CHANNELS = 1
MIC_RATE = 16000
MIC_CHUNK = 1280

SPEAKER_FORMAT = pyaudio.paInt16
SPEAKER_CHANNELS = 1
SPEAKER_RATE = 24000


class AudioHandler:
    def __init__(self):
        self.p: pyaudio.PyAudio | None = None
        self.mic_stream: pyaudio.Stream | None = None
        self.speaker_stream: pyaudio.Stream | None = None
        self.last_error: str | None = None

        try:
            self.p = pyaudio.PyAudio()
        except Exception as exc:  # pragma: no cover - environment-dependent
            self.last_error = str(exc)

    def _require_audio_engine(self) -> pyaudio.PyAudio:
        if self.p is None:
            raise RuntimeError(
                f"Audio engine failed to initialize: {self.last_error or 'unknown error'}"
            )
        return self.p

    def start_mic(self):
        audio_engine = self._require_audio_engine()
        if self.mic_stream is not None and self.mic_stream.is_active():
            return
        try:
            self.mic_stream = audio_engine.open(
                format=MIC_FORMAT,
                channels=MIC_CHANNELS,
                rate=MIC_RATE,
                input=True,
                frames_per_buffer=MIC_CHUNK,
            )
        except Exception as exc:
            raise RuntimeError(f"Could not open microphone: {exc}") from exc

    def read_mic_chunk(self) -> bytes:
        if self.mic_stream and self.mic_stream.is_active():
            return self.mic_stream.read(MIC_CHUNK, exception_on_overflow=False)
        return b""

    def stop_mic(self):
        if self.mic_stream:
            try:
                self.mic_stream.stop_stream()
            except Exception:
                pass
            try:
                self.mic_stream.close()
            except Exception:
                pass
            self.mic_stream = None

    def start_speaker(self):
        audio_engine = self._require_audio_engine()
        if self.speaker_stream is not None and self.speaker_stream.is_active():
            return
        try:
            self.speaker_stream = audio_engine.open(
                format=SPEAKER_FORMAT,
                channels=SPEAKER_CHANNELS,
                rate=SPEAKER_RATE,
                output=True,
            )
        except Exception as exc:
            raise RuntimeError(f"Could not open speaker: {exc}") from exc

    def play_audio(self, pcm_bytes: bytes):
        if self.speaker_stream and self.speaker_stream.is_active():
            self.speaker_stream.write(pcm_bytes)

    def stop_speaker(self):
        if self.speaker_stream:
            try:
                self.speaker_stream.stop_stream()
            except Exception:
                pass
            try:
                self.speaker_stream.close()
            except Exception:
                pass
            self.speaker_stream = None

    def play_chime(self, freq=880.0, duration=0.15):
        self.start_speaker()
        speaker_stream = self.speaker_stream
        if speaker_stream is None:
            raise RuntimeError("Speaker stream failed to initialize")
        samples = int(SPEAKER_RATE * duration)
        t = np.linspace(0, duration, samples, False)
        tone = np.sin(2 * np.pi * freq * t) * np.linspace(0.8, 0.0, samples)
        audio = (tone * 32767).astype(np.int16).tobytes()
        speaker_stream.write(audio)

    def close(self):
        self.stop_mic()
        self.stop_speaker()
        if self.p is not None:
            try:
                self.p.terminate()
            except Exception:
                pass
            self.p = None