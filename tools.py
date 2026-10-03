import os
import subprocess
import webbrowser
import psutil
import pyautogui
from google.genai import types

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

# Global callback reference wired by main.py to hide the GUI
DISMISS_CALLBACK = None


def set_dismiss_callback(cb):
    global DISMISS_CALLBACK
    DISMISS_CALLBACK = cb


def open_application(app_name: str) -> str:
    known_apps = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "paint": "mspaint.exe",
        "task manager": "taskmgr.exe",
        "cmd": "cmd.exe",
        "terminal": "wt.exe",
        "explorer": "explorer.exe",
        "settings": "ms-settings:",
        "edge": "msedge.exe",
        "chrome": "chrome.exe",
    }
    target = known_apps.get(app_name.lower().strip(), app_name)
    try:
        if target.startswith("ms-") or target.startswith("http"):
            os.startfile(target)
        else:
            subprocess.Popen(target, shell=True)
        return f"Opened {app_name}."
    except Exception as e:
        return f"Failed to open {app_name}: {str(e)}"


def type_text(text: str) -> str:
    try:
        pyautogui.write(text, interval=0.01)
        return f"Typed text."
    except Exception as e:
        return f"Failed: {str(e)}"


def press_hotkey(keys: list[str]) -> str:
    try:
        pyautogui.hotkey(*keys)
        return f"Pressed: {', '.join(keys)}."
    except Exception as e:
        return f"Failed: {str(e)}"


def get_system_status() -> dict:
    try:
        battery = psutil.sensors_battery()
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "ram_used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
            "battery": f"{battery.percent}%" if battery else "AC Power",
        }
    except Exception as e:
        return {"error": str(e)}


def dismiss_assistant() -> str:
    """Hides the floating bubble and returns the assistant to passive listening mode."""
    if DISMISS_CALLBACK:
        DISMISS_CALLBACK()
    return "Going to sleep and hiding window."


# Tools registered with Gemini Multimodal Live API
SYSTEM_TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="open_application",
                description="Launch a desktop program (notepad, calculator, chrome, settings).",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={"app_name": types.Schema(type=types.Type.STRING)},
                    required=["app_name"],
                ),
            ),
            types.FunctionDeclaration(
                name="type_text",
                description="Type text into the currently active Windows window.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={"text": types.Schema(type=types.Type.STRING)},
                    required=["text"],
                ),
            ),
            types.FunctionDeclaration(
                name="press_hotkey",
                description="Trigger keyboard shortcuts (e.g. ['win', 'd'], ['ctrl', 'c']).",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "keys": types.Schema(
                            type=types.Type.ARRAY,
                            items=types.Schema(type=types.Type.STRING),
                        )
                    },
                    required=["keys"],
                ),
            ),
            types.FunctionDeclaration(
                name="get_system_status",
                description="Check Windows CPU, RAM, and battery metrics.",
                parameters=types.Schema(type=types.Type.OBJECT, properties={}),
            ),
            types.FunctionDeclaration(
                name="dismiss_assistant",
                description="Call this when the user asks to hide, go to sleep, close, or dismiss the assistant overlay.",
                parameters=types.Schema(type=types.Type.OBJECT, properties={}),
            ),
        ]
    )
]


async def execute_tool(name: str, args: dict) -> dict:
    if name == "open_application":
        result = open_application(args.get("app_name", ""))
    elif name == "type_text":
        result = type_text(args.get("text", ""))
    elif name == "press_hotkey":
        result = press_hotkey(args.get("keys", []))
    elif name == "get_system_status":
        result = get_system_status()
    elif name == "dismiss_assistant":
        result = dismiss_assistant()
    else:
        result = f"Unknown tool: {name}"
    return {"output": result}