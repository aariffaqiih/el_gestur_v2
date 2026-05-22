# ============================================================
# EL PRESENTASI v2.0 — MAIN SERVER (Universal Version)
# ============================================================

import cv2
import threading
import pyautogui
import time
from flask import Flask, jsonify, Response, request
from flask_cors import CORS

from object_lock import ObjectLocker
from gestur_engine import GestureEngine
from config import *

app = Flask(__name__)
CORS(app)

global_frame = None

# 🚨 STATE BARU: Nyimpen software apa yang lagi dipake (Default: PPT)
current_software = "ppt"

def handle_gesture(action):
    global current_software
    
    # --- AKSI UNIVERSAL (berlaku di semua software) ---
    if action == "left_click":
        pyautogui.click()
        return
    elif action == "copy":
        pyautogui.hotkey('ctrl', 'c')
        return
    elif action == "paste":
        pyautogui.hotkey('ctrl', 'v')
        return
    elif action == "select_all":
        pyautogui.hotkey('ctrl', 'a')
        return
    elif action == "alt_tab_start":
        pyautogui.keyDown('alt')
        pyautogui.press('tab')
        return
    elif action == "alt_tab_next":
        pyautogui.press('tab')
        return
    elif action == "alt_tab_end":
        pyautogui.keyUp('alt')
        return

    # --- PROFIL POWERPOINT (PPT) ---
    if current_software == "ppt":
        if action == "next": pyautogui.press('right')
        elif action == "prev": pyautogui.press('left')
        elif action == "laser_on": 
            pyautogui.keyDown('ctrl')
            pyautogui.press('l')
            pyautogui.keyUp('ctrl')
        elif action == "laser_off": 
            pyautogui.keyDown('ctrl')
            pyautogui.press('a')
            pyautogui.keyUp('ctrl')
        elif action == "start": pyautogui.press('f5')
        elif action == "quit": pyautogui.press('esc')

    # --- PROFIL CANVA ---
    elif current_software == "canva":
        if action == "next": pyautogui.press('right')
        elif action == "prev": pyautogui.press('left')
        elif action == "laser_on": pyautogui.press('c') # Canva punya efek 'Confetti/Magic' pakai C
        elif action == "laser_off": pyautogui.press('esc')
        elif action == "start": pyautogui.hotkey('ctrl', 'alt', 'p') # Shortcut Present Canva
        elif action == "quit": pyautogui.press('esc')

    # --- PROFIL FIGMA (Prototype / Slides) ---
    elif current_software == "figma":
        if action == "next": pyautogui.press('right')
        elif action == "prev": pyautogui.press('left')
        elif action == "laser_on": pyautogui.press('c') # Komen figma
        elif action == "laser_off": pyautogui.press('v') # Move tool
        elif action == "start": pyautogui.hotkey('ctrl', 'alt', 'enter') # Play figma
        elif action == "quit": pyautogui.press('esc')

    # --- PROFIL NOTION ---
    elif current_software == "notion":
        if action == "next": pyautogui.press('pagedown') # Notion sifatnya di-scroll ke bawah
        elif action == "prev": pyautogui.press('pageup')
        elif action == "start": pyautogui.hotkey('ctrl', '\\') # Toggle sidebar biar full
        elif action == "quit": pyautogui.hotkey('ctrl', '\\')
        # Notion gak punya laser, biarin aja kosong
        elif action == "laser_on": pass
        elif action == "laser_off": pass

def handle_cursor_move(x, y):
    print(f"👉 KURSOR DITEKAN KE: ({x}, {y})")
    pyautogui.moveTo(x, y, _pause=False)

locker = ObjectLocker()
locker.is_active = True # Aktifkan langsung secara default tanpa harus menunggu web!
engine = GestureEngine(callback=handle_gesture, cursor_callback=handle_cursor_move)
pyautogui.FAILSAFE = False

def camera_loop():
    global global_frame
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    
    print("🎥 Pipeline Kamera berjalan...")
    while True:
        ret, frame = cap.read()
        if not ret: break
        frame = cv2.flip(frame, 1)
        
        frame_annotated, presenter_roi = locker.process_frame(frame)
        if locker.is_active and locker.locked_id and presenter_roi:
            frame_annotated = engine.process_frame(frame_annotated, roi=presenter_roi)
            
        ret, buffer = cv2.imencode('.jpg', frame_annotated)
        if ret: global_frame = buffer.tobytes()
        cv2.imshow("Backend Server - El Presentasi", frame_annotated)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'): break
    cap.release()
    cv2.destroyAllWindows()

# ==========================================
# HTTP ENDPOINTS
# ==========================================

# 🚨 ENDPOINT BARU BUAT NERIMA PILIHAN SOFTWARE DARI WEB
@app.route('/set_software', methods=['POST'])
def set_software():
    global current_software
    data = request.json
    selected = data.get('software')
    if selected in ["ppt", "canva", "figma", "notion"]:
        current_software = selected
        print(f"🔄 TARGET SOFTWARE DIUBAH KE: {current_software.upper()}")
        return jsonify({"status": "success", "software": current_software})
    return jsonify({"status": "error", "message": "Software tidak dikenali"}), 400

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify({
        "is_active": locker.is_active,
        "locked_id": locker.locked_id,
        "gesture_status": engine.get_status() if locker.is_active else "Sistem Offline",
        "current_software": current_software
    })

@app.route('/start', methods=['POST'])
def start_engine():
    locker.is_active = True
    return jsonify({"status": "success"})

@app.route('/stop', methods=['POST'])
def stop_engine():
    locker.is_active = False
    locker.unlock()
    return jsonify({"status": "success"})

@app.route('/lock', methods=['POST'])
def force_lock():
    if locker.is_active:
        locker.wants_to_lock = True
        return jsonify({"message": "Sinyal kunci dikirim"})
    return jsonify({"message": "Gagal. Nyalakan engine!"}), 400

@app.route('/unlock', methods=['POST'])
def force_unlock():
    locker.unlock()
    return jsonify({"message": "Presenter dilepas."})

def generate_frames():
    global global_frame
    while True:
        if global_frame is not None:
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + global_frame + b'\r\n')
        else:
            time.sleep(0.1)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    cam_thread = threading.Thread(target=camera_loop, daemon=True)
    cam_thread.start()
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)