import subprocess
import sys
import os

def get_latest_powerpoint_file():
    try:
        import winreg
        base_path = r"Software\Microsoft\Office\16.0\PowerPoint\User MRU"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, base_path)
        sub_key_name = winreg.EnumKey(key, 0)
        file_mru_path = base_path + "\\" + sub_key_name + r"\File MRU"
        mru_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, file_mru_path)
        val, _ = winreg.QueryValueEx(mru_key, "Item 1")
        file_path = val.split('*')[-1]
        if os.path.exists(file_path):
            return file_path
    except Exception:
        pass
    return None

def force_foreground():
    try:
        import win32gui
        import win32con
        import ctypes
        import time
        import pyautogui
        
        user32 = ctypes.windll.user32
        hwnd = 0
        for _ in range(50):
            hwnd = win32gui.FindWindow("PPTFrameClass", None)
            if hwnd:
                break
            time.sleep(0.1)
            
        if hwnd:
            fg_hwnd = user32.GetForegroundWindow()
            fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None)
            window_thread = user32.GetWindowThreadProcessId(hwnd, None)
            
            if fg_thread != window_thread:
                user32.AttachThreadInput(fg_thread, window_thread, True)
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                win32gui.SetForegroundWindow(hwnd)
                user32.AttachThreadInput(fg_thread, window_thread, False)
            else:
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                win32gui.SetForegroundWindow(hwnd)
            pyautogui.press('alt')
    except Exception:
        pass

def open_powerpoint_application():
    if sys.platform == "darwin":
        try:
            subprocess.Popen(["open", "-a", "Microsoft PowerPoint"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, "Success on macOS"
        except Exception as mac_error:
            return False, f"Failed to open PowerPoint on macOS: {str(mac_error)}"

    if sys.platform != "win32":
        return False, "Unsupported platform"

    try:
        import win32com.client
        powerpoint = win32com.client.Dispatch("PowerPoint.Application")
        powerpoint.Visible = True
        latest_file = get_latest_powerpoint_file()
        if latest_file:
            powerpoint.Presentations.Open(latest_file)
        else:
            powerpoint.Presentations.Add()
        try:
            powerpoint.Activate()
        except Exception:
            pass
        force_foreground()
        return True, "Success via COM"
    except Exception as com_error:
        com_error_msg = str(com_error)

    try:
        latest_file = get_latest_powerpoint_file()
        if latest_file:
            subprocess.Popen(["cmd", "/c", "start", "", latest_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
        else:
            subprocess.Popen(["cmd", "/c", "start", "", "powerpnt.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
        force_foreground()
        return True, "Success via fallback"
    except Exception as start_error:
        return False, "Failed to open PowerPoint"


def open_canva_application():
    if sys.platform == "darwin":
        try:
            # Try to open native Mac app
            subprocess.Popen(["open", "-a", "Canva"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, "Success opening Canva App on macOS"
        except Exception:
            pass
    elif sys.platform == "win32":
        try:
            # Try to open using protocol handler
            subprocess.Popen(["cmd", "/c", "start", "", "canva://"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
            return True, "Success opening Canva via protocol on Windows"
        except Exception:
            pass
            
    # Fallback to opening default web browser
    try:
        import webbrowser
        webbrowser.open("https://www.canva.com")
        return True, "Success opening Canva in web browser"
    except Exception as e:
        return False, f"Failed to open Canva: {e}"


def open_figma_application():
    if sys.platform == "darwin":
        try:
            subprocess.Popen(["open", "-a", "Figma"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, "Success opening Figma App on macOS"
        except Exception:
            pass
    elif sys.platform == "win32":
        try:
            subprocess.Popen(["cmd", "/c", "start", "", "figma://"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
            return True, "Success opening Figma via protocol on Windows"
        except Exception:
            pass
            
    try:
        import webbrowser
        webbrowser.open("https://www.figma.com")
        return True, "Success opening Figma in web browser"
    except Exception as e:
        return False, f"Failed to open Figma: {e}"


def open_notion_application():
    if sys.platform == "darwin":
        try:
            subprocess.Popen(["open", "-a", "Notion"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, "Success opening Notion App on macOS"
        except Exception:
            pass
    elif sys.platform == "win32":
        try:
            subprocess.Popen(["cmd", "/c", "start", "", "notion://"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
            return True, "Success opening Notion via protocol on Windows"
        except Exception:
            pass
            
    try:
        import webbrowser
        webbrowser.open("https://www.notion.so")
        return True, "Success opening Notion in web browser"
    except Exception as e:
        return False, f"Failed to open Notion: {e}"

