import os
import sys
import winreg

APP_NAME = "GeminiDesktopAssistant"


def get_paths():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pythonw_path = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pythonw_path):
        pythonw_path = sys.executable
    main_py = os.path.join(current_dir, "main.py")
    return pythonw_path, main_py, current_dir


def register_startup():
    pythonw, main_py, working_dir = get_paths()
    command = f'"{pythonw}" "{main_py}"'

    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    )
    with key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
    print(f"[Success] Registered '{APP_NAME}' in Windows Startup:\n  {command}")


def unregister_startup():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        with key:
            winreg.DeleteValue(key, APP_NAME)
        print(f"[Success] Removed '{APP_NAME}' from Windows Startup.")
    except FileNotFoundError:
        print(f"[Notice] '{APP_NAME}' is not registered.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--enable", action="store_true", help="Enable Windows startup")
    parser.add_argument("--disable", action="store_true", help="Disable Windows startup")
    args = parser.parse_args()

    if args.disable:
        unregister_startup()
    else:
        register_startup()