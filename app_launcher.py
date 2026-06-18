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

