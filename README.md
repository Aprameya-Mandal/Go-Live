# Gemini Desktop Assistant

A Windows desktop voice assistant built with Python, PyQt6, Gemini Live, and wake-word detection. It listens for a custom wake phrase (`Hey Jarvis`), opens a floating AI bubble UI, streams microphone input to Gemini Live, captures the screen for context, and exposes a few Windows automation tools.

## Features

- Wake word detection using `openwakeword`
- Gemini Live conversation over realtime audio
- Floating glass-style desktop bubble UI with tray support
- Screen capture for live visual context
- Windows automation tools such as dismissing the assistant or other app actions
- Startup registration for Windows auto-launch

## Tech Stack

- Python 3.14
- PyQt6
- qasync
- PyAudioWPatch
- openwakeword
- google-genai
- NumPy
- MSS / Pillow
- ONNX Runtime

## Project Structure

```text
.
├── main.py                 # Main app loop and Gemini Live orchestration
├── gui.py                  # Floating UI and system tray logic
├── audio_handler.py        # Microphone/speaker management
├── vision.py               # Screen capture loop
├── tools.py                # Tool callbacks and system actions
├── startup_manager.py      # Windows startup registration helper
├── requirements.txt        # Python dependencies
├── Arcitecture Overview.txt
└── README.md
```

## Requirements

- Windows 10/11
- A valid Google Gemini API key
- Microphone and speaker access
- Project dependencies installed in a Python virtual environment

## Setup

1. Open PowerShell in the project folder.
2. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Upgrade pip and install dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

4. Set your environment variables:

```powershell
$env:GEMINI_API_KEY="your_google_gemini_api_key_here"
$env:GEMINI_LIVE_MODEL="gemini-2.5-flash-native-audio-latest"
```

> The app checks `GEMINI_API_KEY` at launch. If it is missing, the app will exit with an error.

## Run the App

```powershell
python main.py
```

Or directly using the project venv interpreter:

```powershell
.\.venv\Scripts\python.exe .\main.py
```

## Startup Registration

This project includes a helper to add itself to Windows startup:

```powershell
python startup_manager.py --enable
```

To remove the startup entry:

```powershell
python startup_manager.py --disable
```

This writes a Run key into the Windows registry for the currently active Python executable.

## Important Note

This project expects its dependencies to be installed in the same virtual environment that runs the app. Using the global Python interpreter may fail because the app imports `pyaudiowpatch`, which is not the same as the standard `PyAudio` package and must match the Windows audio stack setup in the project environment.

## Typical Usage

- Launch the app.
- Wait for the floating bubble to appear in standby mode.
- Say `Hey Jarvis`.
- The assistant starts listening and streams audio to Gemini Live.
- The app can also capture your screen while the live session is active.

## Notes

- The app uses realtime audio and screen streaming, so it may consume CPU and audio resources while active.
- The assistant is designed for desktop use and is Windows-focused.
- If `GEMINI_API_KEY` is not configured, the app will not start.

## License

This project is provided as-is for personal use. Add your own license if you plan to distribute it.
