import cv2
import os
import threading
import pyautogui
import time
from flask import Flask, jsonify, Response, request
from flask_cors import CORS

from object_lock import ObjectLocker
from gestur_engine import GestureEngine
from voice_typer import VoiceTyper
from config import *
from app_launcher import open_powerpoint_application
from document_api import create_document_blueprint
from document_commands import DocumentCommandService
from document_finder import DocumentFinder, resolve_search_roots
from command_router import CommandRouter

app = Flask(__name__)
CORS(app)

global_frame = None
current_software = "ppt"


def handle_gesture(action):
    global current_software

    if action == "alt_tab_start":
        pyautogui.keyDown("alt")
        pyautogui.press("tab")
        return
    if action == "alt_tab_next":
        pyautogui.press("tab")
        return
    if action == "alt_tab_end":
        pyautogui.keyUp("alt")
        return
    if action == "voice_start":
        if voice_typer.is_running():
            print("Voice Typer sudah aktif. OK sign diabaikan.")
        else:
            success = voice_typer.start()
            print("Voice Typer dimulai lewat OK sign." if success else "Gagal memulai Voice Typer lewat OK sign.")
        return
    if action == "open_powerpoint":
        success, message = open_powerpoint_application()
        print(("OK " if success else "ERROR ") + message)
        return

    if current_software == "ppt":
        if action == "next":
            pyautogui.press("right")
        elif action == "prev":
            pyautogui.press("left")
        elif action == "laser_on":
            pyautogui.keyDown("ctrl")
            pyautogui.press("l")
            pyautogui.keyUp("ctrl")
        elif action == "laser_off":
            pyautogui.keyDown("ctrl")
            pyautogui.press("a")
            pyautogui.keyUp("ctrl")
        elif action == "start":
            pyautogui.press("f5")
        elif action == "quit":
            pyautogui.press("esc")
        elif action == "new_slide":
            pyautogui.hotkey("ctrl", "m")
            time.sleep(0.5)
            pyautogui.press("tab")
            pyautogui.press("tab")
            pyautogui.press("enter")
            if not voice_typer.is_running():
                success = voice_typer.start()
                print("Voice Typer otomatis dimulai setelah new_slide." if success else "Gagal otomatis memulai Voice Typer.")

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
            pyautogui.hotkey("ctrl", "alt", "p")
        elif action == "quit":
            pyautogui.press("esc")

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
            pyautogui.hotkey("ctrl", "alt", "enter")
        elif action == "quit":
            pyautogui.press("esc")

    elif current_software == "notion":
        if action == "next":
            pyautogui.press("pagedown")
        elif action == "prev":
            pyautogui.press("pageup")
        elif action == "start":
            pyautogui.hotkey("ctrl", "\\")
        elif action == "quit":
            pyautogui.hotkey("ctrl", "\\")
        elif action == "laser_on":
            pass
        elif action == "laser_off":
            pass


def handle_cursor_move(x, y):
    print(f"KURSOR DITEKAN KE: ({x}, {y})")
    pyautogui.moveTo(x, y, _pause=False)


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
    document_commands.handle_text,
])
voice_typer = VoiceTyper(command_handler=command_router.handle_text)
app.register_blueprint(create_document_blueprint(document_commands))
pyautogui.FAILSAFE = True


def camera_loop():
    global global_frame
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    print("Pipeline Kamera berjalan...")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)

        frame_annotated, presenter_roi = locker.process_frame(frame)
        if locker.is_active and locker.locked_id and presenter_roi:
            frame_annotated = engine.process_frame(frame_annotated, roi=presenter_roi)

        ret, buffer = cv2.imencode(".jpg", frame_annotated)
        if ret:
            global_frame = buffer.tobytes()
        cv2.imshow("Backend Server - El Presentasi", frame_annotated)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
    cap.release()
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
    while True:
        if global_frame is not None:
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + global_frame + b"\r\n")
        else:
            time.sleep(0.1)


@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False),
        daemon=True,
    )
    flask_thread.start()

    camera_loop()
