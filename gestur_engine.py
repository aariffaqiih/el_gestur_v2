# ============================================================
# MANDOR AI v2.0 — GESTURE ENGINE (GOD MODE V2.4 - THE FOX)
# Pendekatan: Velocity Spike + Dynamic ROI Scaling + Euclidean
# Fitur: Swipe, Start, Laser, dan Quit (Kon / Fox Pose)
# ============================================================

import cv2
import mediapipe as mp
import time
import math
import pyautogui
import sys
from collections import deque
from config import *

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles

# ============================================================
# ONE EURO FILTER — Adaptive Low-Pass Filter untuk Cursor
# ============================================================
class OneEuroFilter:
    def __init__(self, t0, x0, min_cutoff=1.0, beta=0.01, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_prev = x0
        self.dx_prev = 0.0
        self.t_prev = t0

    def __call__(self, t, x):
        dt = t - self.t_prev
        if dt <= 0: return self.x_prev
        dx = (x - self.x_prev) / dt
        alpha_d = self._alpha(dt, self.d_cutoff)
        edx = alpha_d * dx + (1.0 - alpha_d) * self.dx_prev
        cutoff = self.min_cutoff + self.beta * abs(edx)
        alpha = self._alpha(dt, cutoff)
        rx = alpha * x + (1.0 - alpha) * self.x_prev
        self.t_prev, self.x_prev, self.dx_prev = t, rx, edx
        return rx

    def _alpha(self, dt, cutoff):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

# ============================================================
# GESTURE ENGINE — Mesin Utama Deteksi Gestur
# ============================================================
class GestureEngine:
    def __init__(self, callback, cursor_callback=None):
        self.callback = callback
        self.cursor_callback = cursor_callback
        self.hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=MP_DETECTION_CONFIDENCE,
            min_tracking_confidence=MP_TRACKING_CONFIDENCE
        )
        
        self.position_buffer = {"Left": deque(maxlen=20), "Right": deque(maxlen=20)}
        self.last_action_time = 0
        self.current_cooldown = 0
        self.last_action_name = ""
        
        self.start_state = {
            "Left": {"stage": 0, "fist_time": 0, "initial_y": 0, "raised": False},
            "Right": {"stage": 0, "fist_time": 0, "initial_y": 0, "raised": False}
        }
        
        # Tracker terpisah untuk tiap tangan agar stabil
        self.quit_intent_start = {"Left": None, "Right": None}

        self.laser_active = False
        self.shaka_intent_start = None
        self.shaka_toggled = False       
        self.filter_x, self.filter_y = None, None
        self.last_cursor_x, self.last_cursor_y = None, None
        self.screen_w, self.screen_h = pyautogui.size()

        print("✅ GestureEngine v2.4 (God Mode + Fox Summon) siap!")

    def _in_cooldown(self):
        return (time.time() * 1000 - self.last_action_time) < self.current_cooldown

    def _trigger_action(self, action, cooldown_ms):
        self.last_action_time = time.time() * 1000
        self.current_cooldown = cooldown_ms
        self.last_action_name = action
        print(f"🎯 AKSI DIEKSEKUSI: {action.upper()}")
        self.callback(action)

    @staticmethod
    def _calc_dist(p1, p2, w, h):
        return math.hypot((p1.x - p2.x) * w, (p1.y - p2.y) * h)

    # ========================================================
    # PENDETEKSI POSE TANGAN
    # ========================================================
    def _is_hand_open(self, landmarks, frame_w, frame_h):
        wrist, tips, pips = landmarks[0], [8, 12, 16, 20], [6, 10, 14, 18]
        open_count = sum(1 for t, p in zip(tips, pips) if self._calc_dist(wrist, landmarks[t], frame_w, frame_h) > self._calc_dist(wrist, landmarks[p], frame_w, frame_h))
        return open_count >= 3

    def _is_fist(self, landmarks):
        return all(landmarks[tip].y > landmarks[mcp].y for tip, mcp in zip([8, 12, 16, 20], [5, 9, 13, 17]))

    def _is_shaka_pose(self, landmarks, w, h):
        d, wrist = self._calc_dist, landmarks[0]
        return (d(wrist, landmarks[4], w, h) > d(wrist, landmarks[2], w, h) and
                d(wrist, landmarks[20], w, h) > d(wrist, landmarks[18], w, h) and
                d(wrist, landmarks[8], w, h) < d(wrist, landmarks[6], w, h) and
                d(wrist, landmarks[12], w, h) < d(wrist, landmarks[10], w, h) and
                d(wrist, landmarks[16], w, h) < d(wrist, landmarks[14], w, h))

    def _is_index_pointing(self, landmarks, w, h):
        d, wrist = self._calc_dist, landmarks[0]
        # Telunjuk terbuka, jari tengah, manis, dan kelingking mengepal.
        # Jempol bebas (tidak usah terlalu ketat karena tiap orang cara mengepalnya beda)
        return (d(wrist, landmarks[8], w, h) > d(wrist, landmarks[6], w, h) and
                d(wrist, landmarks[12], w, h) < d(wrist, landmarks[10], w, h) and
                d(wrist, landmarks[16], w, h) < d(wrist, landmarks[14], w, h) and
                d(wrist, landmarks[20], w, h) < d(wrist, landmarks[18], w, h))

    # --- THE FOX POSE (KON) UNTUK QUIT ---
    def _is_fox_pose(self, landmarks, w, h):
        d, wrist = self._calc_dist, landmarks[0]
        
        # Telinga Rubah: Telunjuk & Kelingking LURUS
        index_open = d(wrist, landmarks[8], w, h) > d(wrist, landmarks[6], w, h)
        pinky_open = d(wrist, landmarks[20], w, h) > d(wrist, landmarks[18], w, h)
        
        # Moncong Rubah: Tengah, Manis, Jempol MENEKUK ke dalam
        middle_curled = d(wrist, landmarks[12], w, h) < d(wrist, landmarks[10], w, h)
        ring_curled = d(wrist, landmarks[16], w, h) < d(wrist, landmarks[14], w, h)
        thumb_curled = d(wrist, landmarks[4], w, h) < d(wrist, landmarks[3], w, h) * 1.2
        
        return index_open and pinky_open and middle_curled and ring_curled and thumb_curled

    # ========================================================
    # LOGIKA GESTUR AKSI
    # ========================================================
    
    # --- LOGIKA QUIT (FOX POSE / KON) ---
    def _detect_quit_presentation(self, hand_label, landmarks, area_w, area_h):
        if self._is_fox_pose(landmarks, area_w, area_h):
            if self.quit_intent_start[hand_label] is None:
                self.quit_intent_start[hand_label] = time.time()
                print(f"🦊 [{hand_label}] Pose 'KON' Terdeteksi! Menahan 1 Detik untuk Quit...")
            elif time.time() - self.quit_intent_start[hand_label] >= getattr(sys.modules[__name__], 'INTENT_QUIT_SEC', 1.0):
                if not self._in_cooldown():
                    self._trigger_action("quit", getattr(sys.modules[__name__], 'COOLDOWN_QUIT_MS', 2000))
                    self.quit_intent_start[hand_label] = None
        else:
            self.quit_intent_start[hand_label] = None

    # --- LOGIKA START ---
    def _detect_start_presentation(self, hand_label, landmarks, frame_w, frame_h):
        state = self.start_state[hand_label]
        is_fist, current_y = self._is_fist(landmarks), landmarks[0].y  

        if state["stage"] == 0:
            if is_fist and current_y > 0.60:
                state.update({"stage": 1, "fist_time": time.time(), "initial_y": current_y, "raised": False})
                print(f"⚠️ [{hand_label}] Start Presentation: Ancang-ancang...")
        elif state["stage"] == 1:
            if is_fist:
                if time.time() - state["fist_time"] >= getattr(sys.modules[__name__], 'INTENT_FIST_SEC', 0.8): 
                    state["stage"] = 2
                    print(f"🔥 [{hand_label}] Start Presentation: Terkunci! Angkat tangan.")
            else: state["stage"] = 0
        elif state["stage"] == 2:
            if current_y < state["initial_y"] - 0.20: state["raised"] = True
            if self._is_hand_open(landmarks, frame_w, frame_h):
                if state["raised"]:
                    self._trigger_action("start", getattr(sys.modules[__name__], 'COOLDOWN_START_MS', 2000)) 
                    self.start_state["Left"]["stage"] = self.start_state["Right"]["stage"] = 0
                else: state["stage"] = 0

    # --- LOGIKA LASER ---
    def _detect_laser_toggle(self, landmarks, area_w, area_h):
        if self._is_shaka_pose(landmarks, area_w, area_h):
            if self.shaka_intent_start is None: self.shaka_intent_start = time.time()
            elif not self.shaka_toggled and (time.time() - self.shaka_intent_start >= getattr(sys.modules[__name__], 'INTENT_SHAKA_SEC', 0.8)):
                self.laser_active, self.shaka_toggled = not self.laser_active, True  
                self.filter_x = self.filter_y = self.last_cursor_x = self.last_cursor_y = None
                print("🔴 LASER AKTIF" if self.laser_active else "⚫ LASER NONAKTIF")
                self._trigger_action("laser_on" if self.laser_active else "laser_off", getattr(sys.modules[__name__], 'COOLDOWN_LASER_TOGGLE_MS', 1500))
        else:
            self.shaka_intent_start = None; self.shaka_toggled = False

    def _track_index_finger(self, landmarks, area_w, area_h):
        if not self.cursor_callback: return
        raw_x, raw_y = landmarks[8].x, landmarks[8].y
        box_w, box_h = LASER_BOX_X_MAX - LASER_BOX_X_MIN, LASER_BOX_Y_MAX - LASER_BOX_Y_MIN
        norm_x = max(0.0, min(1.0, (raw_x - LASER_BOX_X_MIN) / box_w))
        norm_y = max(0.0, min(1.0, (raw_y - LASER_BOX_Y_MIN) / box_h))
        screen_x, screen_y = norm_x * self.screen_w, norm_y * self.screen_h
        
        now = time.time()
        if self.filter_x is None:
            self.filter_x = OneEuroFilter(now, screen_x, LASER_MIN_CUTOFF, LASER_BETA, LASER_D_CUTOFF)
            self.filter_y = OneEuroFilter(now, screen_y, LASER_MIN_CUTOFF, LASER_BETA, LASER_D_CUTOFF)
            self.last_cursor_x, self.last_cursor_y = screen_x, screen_y

        filtered_x, filtered_y = self.filter_x(now, screen_x), self.filter_y(now, screen_y)
        if abs(filtered_x - self.last_cursor_x) < LASER_DEADZONE_PX and abs(filtered_y - self.last_cursor_y) < LASER_DEADZONE_PX: return
        self.last_cursor_x, self.last_cursor_y = filtered_x, filtered_y
        self.cursor_callback(int(filtered_x), int(filtered_y))

    # --- LOGIKA SWIPE ---
    def _detect_swipe(self, hand_label, landmarks, frame_w, frame_h):
        if not self._is_hand_open(landmarks, frame_w, frame_h) or not (0.15 <= landmarks[9].y <= 0.90):
            self.position_buffer[hand_label].clear(); return
        
        buf = self.position_buffer[hand_label]
        buf.append((landmarks[9].x * frame_w, landmarks[9].y * frame_h, time.time() * 1000))
        if len(buf) < 4: return

        recent = list(buf)[-4:]
        velocities_x = [ (recent[i][0] - recent[i-1][0]) / ((recent[i][2] - recent[i-1][2]) / 1000.0) 
                         for i in range(1, len(recent)) if recent[i][2] > recent[i-1][2] ]
        
        if not velocities_x: return
        peak_velocity, delta_total = max(velocities_x, key=abs), buf[-1][0] - buf[-4][0]

        if abs(peak_velocity) < (frame_w * 0.4) or abs(delta_total) < (frame_w * 0.15): return
        
        arah = "kanan" if delta_total > 0 else "kiri"
        if arah != ("kanan" if peak_velocity > 0 else "kiri"): return

        self._trigger_action("next" if (arah == "kanan" and hand_label == "Right") else "prev", getattr(sys.modules[__name__], 'COOLDOWN_SWIPE_MS', 1000))
        buf.clear()

    # ========================================================
    # PROCESS FRAME — Pipeline Utama & Routing
    # ========================================================
    def process_frame(self, frame, roi=None):
        h, w = frame.shape[:2]
        
        # Selalu proses full frame agar MediaPipe stabil (tidak terganggu getaran kotak YOLO)
        results = self.hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        if results.multi_hand_landmarks:
            for hand_landmarks, hand_info in zip(results.multi_hand_landmarks, results.multi_handedness):
                hand_label = "Left" if hand_info.classification[0].label == "Right" else "Right"
                
                # Jika ada ROI presenter, pastikan tangan berada di dalam kotak tersebut
                if roi:
                    rx1, ry1, rx2, ry2 = roi
                    # Patokan posisi pergelangan tangan (landmark 0)
                    wrist = hand_landmarks.landmark[0]
                    wx, wy = int(wrist.x * w), int(wrist.y * h)
                    # Beri padding toleransi sebesar 30px di sekeliling kotak YOLO
                    pad = 30
                    if not (rx1 - pad <= wx <= rx2 + pad and ry1 - pad <= wy <= ry2 + pad):
                        continue # Abaikan jika di luar kotak presenter
                
                # Gambar landmark secara utuh dan indah
                mp_draw.draw_landmarks(
                    frame, 
                    hand_landmarks, 
                    mp_hands.HAND_CONNECTIONS, 
                    mp_styles.get_default_hand_landmarks_style(), 
                    mp_styles.get_default_hand_connections_style()
                )

                lm = hand_landmarks.landmark
                
                # 1. Cek Gestur Toggle dan Kon (Quit) secara independen
                self._detect_laser_toggle(lm, w, h)
                self._detect_quit_presentation(hand_label, lm, w, h)

                # 2. Routing Aksi Inti (Berdasarkan Status Laser)
                if self.laser_active:
                    if self._is_index_pointing(lm, w, h): self._track_index_finger(lm, w, h)
                    else: self.filter_x = self.filter_y = self.last_cursor_x = self.last_cursor_y = None
                else:
                    if not self._in_cooldown():
                        self._detect_swipe(hand_label, lm, w, h)
                        self._detect_start_presentation(hand_label, lm, w, h)
                    else:
                        self.position_buffer[hand_label].clear()
                        self.start_state[hand_label]["stage"] = 0
        return frame

    def get_status(self):
        if self.laser_active: return "🔴 Laser Pointer Aktif"
        if self._in_cooldown(): return f"Cooldown... ({int(self.current_cooldown - (time.time()*1000 - self.last_action_time))}ms)"
        return "Siap"

if __name__ == "__main__":
    def on_gesture(action): print(f"👉 AKSI DITERIMA: {action}")
    engine = GestureEngine(callback=on_gesture)
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    print("=" * 60 + "\n🤖 TEST GESTURE ENGINE v2.4\nBuat pose 'Kon' (Metal Pose) untuk Quit Presentation!\n" + "=" * 60)

    while True:
        ret, frame = cap.read()
        if not ret: break
        frame = engine.process_frame(cv2.flip(frame, 1))
        cv2.imshow("Mandor AI v2.4", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break
    cap.release()
    cv2.destroyAllWindows()