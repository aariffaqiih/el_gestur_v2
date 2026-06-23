import cv2
import os
import sys
import threading
import pyautogui
import time
import re
from flask import Flask, jsonify, Response, request
from flask_cors import CORS

from core.object_lock import ObjectLocker
from core.gestur_engine import GestureEngine
from core.voice_typer import VoiceTyper
from core.config import *
from core.app_launcher import open_powerpoint_application, open_canva_application, open_figma_application, open_notion_application
from core.document_api import create_document_blueprint
from core.document_commands import DocumentCommandService
from core.document_finder import DocumentFinder, resolve_search_roots
from core.command_router import CommandRouter

app = Flask(__name__)
CORS(app)

global_frame = None
current_software = "ppt"


def handle_gesture(action):
    global current_software

    is_mac = sys.platform == "darwin"
    cmd_key = "command" if is_mac else "ctrl"
    alt_key = "option" if is_mac else "alt"
    switcher_key = "command" if is_mac else "alt"

    if action == "alt_tab_start":
        pyautogui.keyDown(switcher_key)
        pyautogui.press("tab")
        return
    if action == "alt_tab_next":
        pyautogui.press("tab")
        return
    if action == "alt_tab_end":
        pyautogui.keyUp(switcher_key)
        return
    if action == "voice_start":
        if voice_typer.is_running():
            print("Voice Typer sudah aktif. OK sign diabaikan.")
        else:
            success = voice_typer.start()
            print("Voice Typer dimulai lewat OK sign." if success else "Gagal memulai Voice Typer lewat OK sign.")
        return
    if action == "open_powerpoint":
        if current_software == "ppt":
            success, message = open_powerpoint_application()
        elif current_software == "canva":
            success, message = open_canva_application()
        elif current_software == "figma":
            success, message = open_figma_application()
        elif current_software == "notion":
            success, message = open_notion_application()
        else:
            success, message = False, f"Software {current_software} tidak didukung"
        print(("OK " if success else "ERROR ") + message)
        return

    if current_software == "ppt":
        if action == "next":
            pyautogui.press("right")
        elif action == "prev":
            pyautogui.press("left")
        elif action == "laser_on":
            # Send Ctrl + L (compatible on Windows and Mac PowerPoint versions)
            pyautogui.keyDown("ctrl")
            pyautogui.press("l")
            pyautogui.keyUp("ctrl")
            # Also send Cmd + L on macOS as fallback
            if is_mac:
                pyautogui.keyDown("command")
                pyautogui.press("l")
                pyautogui.keyUp("command")
        elif action == "laser_off":
            # Send Ctrl + A
            pyautogui.keyDown("ctrl")
            pyautogui.press("a")
            pyautogui.keyUp("ctrl")
            # Also send Cmd + A on macOS as fallback
            if is_mac:
                pyautogui.keyDown("command")
                pyautogui.press("a")
                pyautogui.keyUp("command")
        elif action == "start":
            if is_mac:
                pyautogui.hotkey("command", "shift", "return")
            else:
                pyautogui.press("f5")
        elif action == "quit":
            pyautogui.press("esc")
        elif action == "new_slide":
            if is_mac:
                pyautogui.hotkey("command", "shift", "n")
            else:
                pyautogui.hotkey("ctrl", "m")
                time.sleep(0.5)
                pyautogui.press("tab")
                pyautogui.press("tab")
                pyautogui.press("enter")
            if not voice_typer.is_running():
                success = voice_typer.start()
                print("Voice Typer otomatis dimulai setelah new_slide." if success else "Gagal otomatis memulai Voice Typer.")
        elif action == "delete_slide":
            pyautogui.press("delete")

    elif current_software == "canva":
        if action == "next":
            pyautogui.press("right")
        elif action == "prev":
            pyautogui.press("left")
        elif action == "laser_on":
            pyautogui.press("c")
        elif action == "laser_off":
            pyautogui.press("esc")
        elif action == "start":
            pyautogui.hotkey(cmd_key, alt_key, "p")
        elif action == "quit":
            pyautogui.press("esc")
        elif action == "new_slide":
            if is_mac:
                pyautogui.hotkey("command", "return")
            else:
                pyautogui.hotkey("ctrl", "enter")
            if not voice_typer.is_running():
                success = voice_typer.start()
                print("Voice Typer otomatis dimulai setelah new_slide." if success else "Gagal otomatis memulai Voice Typer.")
        elif action == "delete_slide":
            pyautogui.press("delete")

    elif current_software == "figma":
        if action == "next":
            pyautogui.press("right")
        elif action == "prev":
            pyautogui.press("left")
        elif action == "laser_on":
            pyautogui.press("c")
        elif action == "laser_off":
            pyautogui.press("v")
        elif action == "start":
            pyautogui.hotkey(cmd_key, alt_key, "enter")
        elif action == "quit":
            pyautogui.hotkey(cmd_key, "w")
        elif action == "new_slide":
            # Press Esc twice to clear text focus or selection and select parent Frame container
            pyautogui.press("esc")
            time.sleep(0.05)
            pyautogui.press("esc")
            time.sleep(0.05)
            if is_mac:
                pyautogui.hotkey("command", "d")
            else:
                pyautogui.hotkey("ctrl", "d")
            if not voice_typer.is_running():
                success = voice_typer.start()
                print("Voice Typer otomatis dimulai setelah new_slide." if success else "Gagal otomatis memulai Voice Typer.")
        elif action == "delete_slide":
            pyautogui.press("esc")
            time.sleep(0.05)
            pyautogui.press("esc")
            time.sleep(0.05)
            pyautogui.press("delete")

    elif current_software == "notion":
        if action == "next":
            pyautogui.press("pagedown")
        elif action == "prev":
            pyautogui.press("pageup")
        elif action == "start":
            pyautogui.hotkey(cmd_key, "\\")
        elif action == "quit":
            pyautogui.hotkey(cmd_key, "\\")
        elif action == "laser_on" or action == "laser_off":
            if is_mac:
                pyautogui.hotkey("command", "shift", "l")
            else:
                pyautogui.hotkey("ctrl", "shift", "l")
        elif action == "new_slide":
            if is_mac:
                pyautogui.hotkey("command", "n")
            else:
                pyautogui.hotkey("ctrl", "n")
            if not voice_typer.is_running():
                success = voice_typer.start()
                print("Voice Typer otomatis dimulai setelah new_slide." if success else "Gagal otomatis memulai Voice Typer.")
        elif action == "delete_slide":
            pyautogui.press("delete")


def handle_cursor_move(x, y):
    print(f"KURSOR DITEKAN KE: ({x}, {y})")
    pyautogui.moveTo(x, y, _pause=False)


def handle_software_commands(text):
    global current_software
    is_mac = sys.platform == "darwin"
    cmd_key = "command" if is_mac else "ctrl"
    
    lowered = text.lower().strip()
    
    if current_software == "ppt":
        if lowered in ["aktifkan pena", "pena"]:
            pyautogui.hotkey(cmd_key, "p")
            return {"status": "command", "command": "aktifkan pena"}
        elif lowered in ["aktifkan stabilo", "stabilo"]:
            pyautogui.hotkey(cmd_key, "i")
            return {"status": "command", "command": "aktifkan stabilo"}
        elif lowered in ["aktifkan pointer", "panah", "kursor"]:
            pyautogui.hotkey(cmd_key, "a")
            return {"status": "command", "command": "aktifkan pointer"}
        elif lowered in ["hapus coretan", "bersihkan coretan", "hapus semua"]:
            pyautogui.press("e")
            return {"status": "command", "command": "hapus coretan"}
        elif lowered == "layar hitam":
            pyautogui.press("b")
            return {"status": "command", "command": "layar hitam"}
        elif lowered == "layar putih":
            pyautogui.press("w")
            return {"status": "command", "command": "layar putih"}
        elif lowered in ["kembali normal", "tampilkan slide"]:
            pyautogui.press("space")
            return {"status": "command", "command": "kembali normal"}
            
    elif current_software == "canva":
        if lowered in ["tampilkan konfeti", "konfeti"]:
            pyautogui.press("c")
            return {"status": "command", "command": "tampilkan konfeti"}
        elif lowered in ["tampilkan gelembung", "gelembung"]:
            pyautogui.press("o")
            return {"status": "command", "command": "tampilkan gelembung"}
        elif lowered in ["blur layar", "samarkan layar"]:
            pyautogui.press("b")
            return {"status": "command", "command": "blur layar"}
        elif lowered in ["minta diam", "hening", "shh"]:
            pyautogui.press("q")
            return {"status": "command", "command": "hening"}
        elif lowered in ["suara drum", "drumroll"]:
            pyautogui.press("d")
            return {"status": "command", "command": "drumroll"}
        elif lowered in ["buka tirai", "tirai"]:
            pyautogui.press("u")
            return {"status": "command", "command": "buka tirai"}
        elif lowered == "mic drop":
            pyautogui.press("m")
            return {"status": "command", "command": "mic drop"}
        
        timer_match = re.match(r"^timer\s+(\d|satu|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan)\s+menit$", lowered)
        if timer_match:
            num_word = timer_match.group(1)
            num_map = {
                "1": "1", "satu": "1",
                "2": "2", "dua": "2",
                "3": "3", "tiga": "3",
                "4": "4", "empat": "4",
                "5": "5", "lima": "5",
                "6": "6", "enam": "6",
                "7": "7", "tujuh": "7",
                "8": "8", "delapan": "8",
                "9": "9", "sembilan": "9"
            }
            digit = num_map.get(num_word)
            if digit:
                pyautogui.press(digit)
                return {"status": "command", "command": f"timer {digit} menit"}
            
    elif current_software == "figma":
        if lowered in ["tampilkan komentar", "komentar"]:
            pyautogui.hotkey("shift", "c")
            return {"status": "command", "command": "tampilkan komentar"}
        elif lowered in ["zoom fit", "tampilkan semua"]:
            pyautogui.hotkey("shift", "1")
            return {"status": "command", "command": "zoom fit"}
        elif lowered in ["zoom seleksi", "fokus objek"]:
            pyautogui.hotkey("shift", "2")
            return {"status": "command", "command": "zoom seleksi"}
        elif lowered in ["toggle grid", "grid"]:
            pyautogui.hotkey("ctrl", "shift", "4")
            return {"status": "command", "command": "toggle grid"}
        elif lowered in ["sembunyikan ui", "tampilkan ui"]:
            pyautogui.hotkey(cmd_key, "\\")
            return {"status": "command", "command": "toggle ui"}
            
    elif current_software == "notion":
        if lowered in ["buat judul", "judul"]:
            pyautogui.typewrite("/h1", interval=0.01)
            time.sleep(0.1)
            pyautogui.press("enter")
            return {"status": "command", "command": "buat judul"}
        elif lowered in ["buat daftar", "daftar tugas"]:
            pyautogui.typewrite("/todo", interval=0.01)
            time.sleep(0.1)
            pyautogui.press("enter")
            return {"status": "command", "command": "buat daftar tugas"}
        elif lowered in ["tutup sidebar", "buka sidebar"]:
            pyautogui.hotkey(cmd_key, "\\")
            return {"status": "command", "command": "toggle sidebar"}
        elif lowered in ["buat kutipan", "kutipan"]:
            pyautogui.typewrite("/quote", interval=0.01)
            time.sleep(0.1)
            pyautogui.press("enter")
            return {"status": "command", "command": "buat kutipan"}
        elif lowered in ["buat poin", "poin"]:
            pyautogui.typewrite("/bullet", interval=0.01)
            time.sleep(0.1)
            pyautogui.press("enter")
            return {"status": "command", "command": "buat poin"}
        elif lowered in ["buat nomor", "daftar nomor"]:
            pyautogui.typewrite("/numbered", interval=0.01)
            time.sleep(0.1)
            pyautogui.press("enter")
            return {"status": "command", "command": "buat daftar nomor"}
        elif lowered in ["buat callout", "callout"]:
            pyautogui.typewrite("/callout", interval=0.01)
            time.sleep(0.1)
            pyautogui.press("enter")
            return {"status": "command", "command": "buat callout"}
        elif lowered in ["buat tabel", "tabel"]:
            pyautogui.typewrite("/table", interval=0.01)
            time.sleep(0.1)
            pyautogui.press("enter")
            return {"status": "command", "command": "buat tabel"}
            
    return None


locker = ObjectLocker()
locker.is_active = True
engine = GestureEngine(callback=handle_gesture, cursor_callback=handle_cursor_move)
document_finder = DocumentFinder(
    roots=resolve_search_roots(
        DOCUMENT_SEARCH_PATHS,
        environment_override=os.environ.get("EL_DOCUMENT_SEARCH_PATHS"),
    ),
    extensions=DOCUMENT_SEARCH_EXTENSIONS,
    max_results=DOCUMENT_SEARCH_MAX_RESULTS,
    index_ttl_seconds=DOCUMENT_INDEX_TTL_SEC,
    excluded_directory_names=DOCUMENT_SEARCH_EXCLUDED_DIRS,
    max_index_files=DOCUMENT_INDEX_MAX_FILES,
)
document_commands = DocumentCommandService(document_finder)
command_router = CommandRouter([
    handle_software_commands,
    document_commands.handle_text,
])
voice_typer = VoiceTyper(command_handler=command_router.handle_text)
app.register_blueprint(create_document_blueprint(document_commands))
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.005


def camera_loop():
    global global_frame
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    print("Pipeline Kamera berjalan...")
    while True:
        # Sleep when engine is STANDBY to save power and computation
        if not locker.is_active:
            time.sleep(0.5)

        start_time = time.time()
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)

        frame_annotated, presenter_roi = locker.process_frame(frame)
        if locker.is_active and locker.locked_id and presenter_roi:
            frame_annotated = engine.process_frame(frame_annotated, roi=presenter_roi)

        global_frame = frame_annotated

        # Frame rate controller
        elapsed = time.time() - start_time
        delay = (1.0 / CAMERA_FPS) - elapsed

        if SHOW_BACKEND_WINDOW:
            cv2.imshow("Backend Server - El Presentasi", frame_annotated)
            wait_ms = max(1, int(delay * 1000)) if delay > 0 else 1
            key = cv2.waitKey(wait_ms) & 0xFF
            if key == ord("q"):
                break
        else:
            if delay > 0:
                time.sleep(delay)
    cap.release()
    if SHOW_BACKEND_WINDOW:
        cv2.destroyAllWindows()


@app.route("/set_software", methods=["POST"])
def set_software():
    global current_software
    data = request.json
    selected = data.get("software")
    if selected in ["ppt", "canva", "figma", "notion"]:
        current_software = selected
        print(f"TARGET SOFTWARE DIUBAH KE: {current_software.upper()}")
        return jsonify({"status": "success", "software": current_software})
    return jsonify({"status": "error", "message": "Software tidak dikenali"}), 400


@app.route("/open_ppt", methods=["POST"])
def open_ppt():
    success, message = open_powerpoint_application()
    if success:
        return jsonify({"status": "success", "message": message})
    return jsonify({"status": "error", "message": message}), 500


@app.route("/open_canva", methods=["POST"])
def open_canva():
    success, message = open_canva_application()
    if success:
        return jsonify({"status": "success", "message": message})
    return jsonify({"status": "error", "message": message}), 500


@app.route("/open_figma", methods=["POST"])
def open_figma():
    success, message = open_figma_application()
    if success:
        return jsonify({"status": "success", "message": message})
    return jsonify({"status": "error", "message": message}), 500


@app.route("/open_notion", methods=["POST"])
def open_notion():
    success, message = open_notion_application()
    if success:
        return jsonify({"status": "success", "message": message})
    return jsonify({"status": "error", "message": message}), 500


@app.route("/voice_start", methods=["POST"])
def voice_start():
    if voice_typer.is_running():
        return jsonify({"status": "already_running", "message": "Voice Typer sudah aktif."})
    success = voice_typer.start()
    if success:
        return jsonify({"status": "success", "message": "Voice Typer dimulai."})
    return jsonify({"status": "error", "message": "Gagal memulai Voice Typer."}), 500


@app.route("/voice_stop", methods=["POST"])
def voice_stop():
    voice_typer.stop()
    return jsonify({"status": "success", "message": "Voice Typer dihentikan."})


@app.route("/voice_status", methods=["GET"])
def voice_status():
    return jsonify(voice_typer.get_status())


@app.route("/voice_mute", methods=["POST"])
def voice_mute():
    voice_typer.mute()
    return jsonify({"status": "success", "voice_typer": voice_typer.get_status()})


@app.route("/voice_unmute", methods=["POST"])
def voice_unmute():
    voice_typer.unmute()
    return jsonify({"status": "success", "voice_typer": voice_typer.get_status()})


@app.route("/voice_toggle_mute", methods=["POST"])
def voice_toggle_mute():
    is_muted = voice_typer.toggle_mute()
    return jsonify({"status": "success", "is_muted": is_muted, "voice_typer": voice_typer.get_status()})


@app.route("/toggle_laser", methods=["POST"])
def toggle_laser():
    engine.laser_active = not engine.laser_active
    action = "laser_on" if engine.laser_active else "laser_off"
    handle_gesture(action)
    engine.filter_x = engine.filter_y = engine.last_cursor_x = engine.last_cursor_y = None
    return jsonify({
        "status": "success", 
        "laser_active": engine.laser_active, 
        "gesture_status": engine.get_status()
    })


@app.route("/voice_devices", methods=["GET"])
def voice_devices():
    try:
        import speech_recognition as sr
        names = sr.Microphone.list_microphone_names()
        devices = [{"index": idx, "name": name} for idx, name in enumerate(names)]
        return jsonify({"status": "success", "devices": devices})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gagal mendapatkan daftar mikrofon: {e}"}), 500


@app.route("/set_voice_device", methods=["POST"])
def set_voice_device():
    data = request.json or {}
    device_index = data.get("device_index")
    try:
        voice_typer.set_device_index(device_index)
        return jsonify({
            "status": "success",
            "message": f"Mikrofon backend berhasil diatur ke index: {device_index}",
            "voice_typer": voice_typer.get_status()
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gagal mengatur mikrofon: {e}"}), 500


@app.route("/type", methods=["POST"])
def type_text():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    return jsonify(voice_typer.process_text(text))


@app.route("/status", methods=["GET"])
def get_status():
    return jsonify({
        "is_active": locker.is_active,
        "locked_id": locker.locked_id,
        "gesture_status": engine.get_status() if locker.is_active else "Sistem Offline",
        "current_software": current_software,
        "voice_typer": voice_typer.get_status(),
        "documents": document_commands.get_status(),
    })


@app.route("/start", methods=["POST"])
def start_engine():
    locker.is_active = True
    return jsonify({"status": "success"})


@app.route("/stop", methods=["POST"])
def stop_engine():
    locker.is_active = False
    locker.unlock()
    return jsonify({"status": "success"})


@app.route("/lock", methods=["POST"])
def force_lock():
    if locker.is_active:
        locker.wants_to_lock = True
        return jsonify({"message": "Sinyal kunci dikirim"})
    return jsonify({"message": "Gagal. Nyalakan engine!"}), 400


@app.route("/unlock", methods=["POST"])
def force_unlock():
    locker.unlock()
    return jsonify({"message": "Presenter dilepas."})


def generate_frames():
    global global_frame
    last_sent_frame = None
    while True:
        if global_frame is not None:
            if global_frame is not last_sent_frame:
                ret, buffer = cv2.imencode(".jpg", global_frame)
                if ret:
                    yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
                    last_sent_frame = global_frame
            time.sleep(0.033)  # limit stream to max ~30 FPS
        else:
            time.sleep(0.1)


@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=5005, debug=False, use_reloader=False),
        daemon=True,
    )
    flask_thread.start()

    camera_loop()
