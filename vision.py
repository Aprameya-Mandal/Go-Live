import io
import asyncio
import mss
from PIL import Image
from google.genai import types


class ScreenCaptureManager:
    def __init__(self, target_fps: float = 1.0, quality: int = 70, scale: float = 0.75):
        self.interval = 1.0 / target_fps
        self.quality = quality
        self.scale = scale
        self.running = False

    def grab_frame_jpeg(self, sct: mss.MSS) -> bytes:
        monitor = sct.monitors[1]  # Primary display
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        if self.scale != 1.0:
            new_size = (int(img.width * self.scale), int(img.height * self.scale))
            img = img.resize(new_size, Image.Resampling.BILINEAR)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=self.quality)
        return buf.getvalue()

    async def stream_screen_loop(self, session):
        self.running = True
        with mss.mss() as sct:
            while self.running:
                start_time = asyncio.get_event_loop().time()
                try:
                    frame_bytes = self.grab_frame_jpeg(sct)
                    await session.send_realtime_input(
                        video=types.Blob(data=frame_bytes, mime_type="image/jpeg")
                    )
                except Exception as e:
                    print(f"[Vision Error] {e}")

                elapsed = asyncio.get_event_loop().time() - start_time
                await asyncio.sleep(max(0.0, self.interval - elapsed))

    def stop(self):
        self.running = False