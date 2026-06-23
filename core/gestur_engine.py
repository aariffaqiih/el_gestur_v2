import cv2
import mediapipe as mp
import time
import math
import pyautogui
from collections import deque
from .config import *

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles

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
        self.stop_state = {
            "Left": {"stage": 0, "fist_time": 0},
            "Right": {"stage": 0, "fist_time": 0}
        }
        self.quit_intent_start = None
        self.quit_triggered = False
        self.laser_active = False
        self.laser_pose_intent_start = {"Left": None, "Right": None}
        self.laser_pose_toggled = {"Left": False, "Right": False}
        self.voice_start_intent_start = None
        self.voice_start_triggered = False
        self.last_voice_start_time = 0
        self.ily_intent_start = None
        self.ily_active = False
        self.ily_last_tab_time = 0
        self.circle_intent_start = None
        self.circle_triggered = False
        self.new_slide_intent_start = None
        self.new_slide_triggered = False
        self.cross_intent_start = None
        self.cross_triggered = False
        self.filter_x, self.filter_y = None, None
        self.last_cursor_x, self.last_cursor_y = None, None
        self.screen_w, self.screen_h = pyautogui.size()
        print("✅ GestureEngine v2.6 siap!")

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

    def _is_hand_open(self, landmarks, frame_w, frame_h):
        wrist, tips, pips = landmarks[0], [8, 12, 16, 20], [6, 10, 14, 18]
        open_count = sum(1 for t, p in zip(tips, pips) if self._calc_dist(wrist, landmarks[t], frame_w, frame_h) > self._calc_dist(wrist, landmarks[p], frame_w, frame_h) * 0.95)
        return open_count >= 2

    def _is_fist(self, landmarks):
        d = self._calc_dist
        wrist = landmarks[0]
        return all(d(wrist, landmarks[tip], 1, 1) < d(wrist, landmarks[pip], 1, 1) * 1.05 for tip, pip in zip([8, 12, 16, 20], [6, 10, 14, 18]))

    def _is_index_pointing(self, landmarks, w, h):
        # Use 3D Euclidean distance to prevent 2D perspective foreshortening errors when pointing at the camera
        d = lambda p1, p2: math.hypot(math.hypot(p1.x - p2.x, p1.y - p2.y), p1.z - p2.z)
        wrist = landmarks[0]
        return (d(wrist, landmarks[8]) > d(wrist, landmarks[6]) * 0.90 and
                d(wrist, landmarks[12]) < d(wrist, landmarks[10]) * 1.10 and
                d(wrist, landmarks[16]) < d(wrist, landmarks[14]) * 1.10 and
                d(wrist, landmarks[20]) < d(wrist, landmarks[18]) * 1.10)

    def _is_shaka_pose(self, landmarks, w, h):
        d, wrist = self._calc_dist, landmarks[0]
        thumb_open = d(wrist, landmarks[4], w, h) > d(wrist, landmarks[2], w, h) * 0.98
        pinky_open = d(wrist, landmarks[20], w, h) > d(wrist, landmarks[18], w, h) * 0.98
        index_curled = d(wrist, landmarks[8], w, h) < d(wrist, landmarks[6], w, h) * 1.05
        middle_curled = d(wrist, landmarks[12], w, h) < d(wrist, landmarks[10], w, h) * 1.05
        ring_curled = d(wrist, landmarks[16], w, h) < d(wrist, landmarks[14], w, h) * 1.05
        return thumb_open and pinky_open and index_curled and middle_curled and ring_curled

    def _is_ok_pose(self, landmarks, w, h):
        d, wrist = self._calc_dist, landmarks[0]
        thumb_tip = landmarks[4]
        ref_dist = max(d(wrist, landmarks[9], w, h), 1.0)
        index_close = d(thumb_tip, landmarks[8], w, h) < ref_dist * 0.45
        middle_open = d(wrist, landmarks[12], w, h) > d(wrist, landmarks[10], w, h) * 0.98
        ring_open = d(wrist, landmarks[16], w, h) > d(wrist, landmarks[14], w, h) * 0.98
        pinky_open = d(wrist, landmarks[20], w, h) > d(wrist, landmarks[18], w, h) * 0.98
        thumb_not_collapsed_to_wrist = d(wrist, thumb_tip, w, h) > ref_dist * 0.40
        return index_close and middle_open and ring_open and pinky_open and thumb_not_collapsed_to_wrist

    def _is_ily_pose(self, landmarks, w, h):
        d, wrist = self._calc_dist, landmarks[0]
        thumb_open = d(wrist, landmarks[4], w, h) > d(wrist, landmarks[2], w, h) * 0.95
        index_open = d(wrist, landmarks[8], w, h) > d(wrist, landmarks[6], w, h) * 0.95
        pinky_open = d(wrist, landmarks[20], w, h) > d(wrist, landmarks[18], w, h) * 0.95
        middle_curled = d(wrist, landmarks[12], w, h) < d(wrist, landmarks[10], w, h) * 1.05
        ring_curled = d(wrist, landmarks[16], w, h) < d(wrist, landmarks[14], w, h) * 1.05
        return thumb_open and index_open and pinky_open and middle_curled and ring_curled

    def _is_peace_pose(self, landmarks, w, h):
        d = self._calc_dist
        wrist = landmarks[0]
        index_open = d(wrist, landmarks[8], w, h) > d(wrist, landmarks[6], w, h) * 0.95
        middle_open = d(wrist, landmarks[12], w, h) > d(wrist, landmarks[10], w, h) * 0.95
        ring_curled = d(wrist, landmarks[16], w, h) < d(wrist, landmarks[14], w, h) * 1.05
        pinky_curled = d(wrist, landmarks[20], w, h) < d(wrist, landmarks[18], w, h) * 1.05
        return index_open and middle_open and ring_curled and pinky_curled

    @staticmethod
    def _get_two_hands(all_hands):
        if len(all_hands) < 2:
            return None
        return all_hands[0][1], all_hands[1][1]

    def _is_circle_pose(self, all_hands, w, h):
        two_hands = self._get_two_hands(all_hands)
        if not two_hands:
            return False
        left_lm, right_lm = two_hands
        d = self._calc_dist
        ref_dist = max(d(left_lm[0], left_lm[9], w, h), 1.0)
        thumb_dist = math.hypot((left_lm[4].x - right_lm[4].x) * w, (left_lm[4].y - right_lm[4].y) * h)
        index_dist = math.hypot((left_lm[8].x - right_lm[8].x) * w, (left_lm[8].y - right_lm[8].y) * h)
        return thumb_dist < ref_dist * 0.50 and index_dist < ref_dist * 0.50

    def _is_prayer_quit_pose(self, all_hands, w, h):
        two_hands = self._get_two_hands(all_hands)
        if not two_hands:
            return False
        left_lm, right_lm = two_hands
        if not self._is_hand_open(left_lm, w, h) or not self._is_hand_open(right_lm, w, h):
            return False
        d = self._calc_dist
        tip_pairs = [(8, 8), (12, 12), (16, 16), (20, 20)]
        ref_dist = max(d(left_lm[0], left_lm[9], w, h), 1.0)
        close_count = 0
        for lt, rt in tip_pairs:
            tip_dist = math.hypot(
                (left_lm[lt].x - right_lm[rt].x) * w,
                (left_lm[lt].y - right_lm[rt].y) * h
            )
            if tip_dist < ref_dist * 0.60:
                close_count += 1
        return close_count >= 3

    def _is_cross_pose(self, all_hands, w, h):
        if len(all_hands) < 2:
            return False
        left_lm = None
        right_lm = None
        for label, lm in all_hands:
            if label == "Left":
                left_lm = lm
            elif label == "Right":
                right_lm = lm
        if not left_lm or not right_lm:
            return False
        d = self._calc_dist
        ref_dist = max(d(left_lm[0], left_lm[9], w, h), 1.0)
        is_crossed = left_lm[0].x < right_lm[0].x and left_lm[9].x < right_lm[9].x
        y_dist = abs(left_lm[0].y - right_lm[0].y) * h
        return is_crossed and y_dist < ref_dist * 3.0

    def _process_quit_state(self, all_hands, w, h):
        prayer = self._is_prayer_quit_pose(all_hands, w, h)
        if prayer:
            self.start_state["Left"]["stage"] = 0
            self.start_state["Right"]["stage"] = 0
            if self.quit_intent_start is None:
                self.quit_intent_start = time.time()
                self.quit_triggered = False
            elif (not self.quit_triggered and
                  time.time() - self.quit_intent_start >= INTENT_QUIT_SEC):
                if not self._in_cooldown():
                    self.quit_triggered = True
                    self._trigger_action("quit", COOLDOWN_QUIT_MS)
        else:
            self.quit_intent_start = None
            self.quit_triggered = False

    def _process_circle_state(self, all_hands, w, h):
        if self._is_circle_pose(all_hands, w, h):
            if self.circle_intent_start is None:
                self.circle_intent_start = time.time()
                self.circle_triggered = False
            elif (not self.circle_triggered and 
                  time.time() - self.circle_intent_start >= INTENT_POWERPOINT_SEC):
                if not self._in_cooldown():
                    self.circle_triggered = True
                    self._trigger_action("open_powerpoint", COOLDOWN_POWERPOINT_MS)
        else:
            self.circle_intent_start = None
            self.circle_triggered = False

    def _process_cross_state(self, all_hands, w, h):
        if self._is_cross_pose(all_hands, w, h):
            if self.cross_intent_start is None:
                self.cross_intent_start = time.time()
                self.cross_triggered = False
            elif (not self.cross_triggered and 
                  time.time() - self.cross_intent_start >= INTENT_CROSS_SEC):
                if not self._in_cooldown():
                    self.cross_triggered = True
                    self._trigger_action("delete_slide", COOLDOWN_DELETE_MS)
        else:
            self.cross_intent_start = None
            self.cross_triggered = False

    def _detect_start_presentation(self, hand_label, landmarks, frame_w, frame_h):
        state = self.start_state[hand_label]
        if self._is_peace_pose(landmarks, frame_w, frame_h):
            if state["stage"] == 0:
                state.update({"stage": 1, "peace_time": time.time()})
            elif state["stage"] == 1:
                if time.time() - state.get("peace_time", time.time()) >= INTENT_FIST_SEC:
                    self._trigger_action("start", COOLDOWN_START_MS)
                    self.start_state["Left"]["stage"] = self.start_state["Right"]["stage"] = 0
        else:
            state["stage"] = 0

    def _detect_stop_presentation(self, hand_label, landmarks):
        state = self.stop_state[hand_label]
        if self._is_fist(landmarks):
            if state["stage"] == 0:
                state.update({"stage": 1, "fist_time": time.time()})
            elif state["stage"] == 1:
                if time.time() - state.get("fist_time", time.time()) >= INTENT_FIST_SEC:
                    self._trigger_action("quit", COOLDOWN_QUIT_MS)
                    self.stop_state["Left"]["stage"] = self.stop_state["Right"]["stage"] = 0
        else:
            state["stage"] = 0

    def _detect_laser_toggle(self, hand_label, landmarks, area_w, area_h):
        if self._is_shaka_pose(landmarks, area_w, area_h):
            if self.laser_pose_intent_start[hand_label] is None:
                self.laser_pose_intent_start[hand_label] = time.time()
            elif (not self.laser_pose_toggled[hand_label] and
                  time.time() - self.laser_pose_intent_start[hand_label] >= INTENT_LASER_SEC):
                self.laser_active = not self.laser_active
                self.laser_pose_toggled[hand_label] = True
                self.filter_x = self.filter_y = self.last_cursor_x = self.last_cursor_y = None
                self._trigger_action("laser_on" if self.laser_active else "laser_off", COOLDOWN_LASER_TOGGLE_MS)
        else:
            self.laser_pose_intent_start[hand_label] = None
            self.laser_pose_toggled[hand_label] = False
    def _track_index_finger(self, landmarks, area_w, area_h):
        if not self.cursor_callback: return
        # Blend fingertip (65%) and knuckle (35%) to filter out high-frequency joint tremors at the source
        raw_x = landmarks[8].x * 0.65 + landmarks[5].x * 0.35
        raw_y = landmarks[8].y * 0.65 + landmarks[5].y * 0.35
        box_w = LASER_BOX_X_MAX - LASER_BOX_X_MIN
        box_h = LASER_BOX_Y_MAX - LASER_BOX_Y_MIN
        norm_x = max(0.0, min(1.0, (raw_x - LASER_BOX_X_MIN) / box_w))
        norm_y = max(0.0, min(1.0, (raw_y - LASER_BOX_Y_MIN) / box_h))
        screen_w, screen_h = pyautogui.size()
        screen_x, screen_y = norm_x * screen_w, norm_y * screen_h
        now = time.time()
        if self.filter_x is None:
            self.filter_x = OneEuroFilter(now, screen_x, LASER_MIN_CUTOFF, LASER_BETA, LASER_D_CUTOFF)
            self.filter_y = OneEuroFilter(now, screen_y, LASER_MIN_CUTOFF, LASER_BETA, LASER_D_CUTOFF)
            self.last_cursor_x, self.last_cursor_y = screen_x, screen_y
        filtered_x = self.filter_x(now, screen_x)
        filtered_y = self.filter_y(now, screen_y)
        if abs(filtered_x - self.last_cursor_x) < LASER_DEADZONE_PX and abs(filtered_y - self.last_cursor_y) < LASER_DEADZONE_PX: return
        self.last_cursor_x, self.last_cursor_y = filtered_x, filtered_y
        self.cursor_callback(int(filtered_x), int(filtered_y))

    def _process_voice_start_state(self, voice_start_detected):
        if voice_start_detected:
            if self.voice_start_intent_start is None:
                self.voice_start_intent_start = time.time()
                self.voice_start_triggered = False
            elif (not self.voice_start_triggered and
                  time.time() - self.voice_start_intent_start >= INTENT_VOICE_START_SEC):
                now_ms = time.time() * 1000
                cooldown_ms = COOLDOWN_VOICE_START_MS
                if now_ms - self.last_voice_start_time >= cooldown_ms:
                    self.last_voice_start_time = now_ms
                    self.voice_start_triggered = True
                    self.last_action_name = "voice_start"
                    self.callback("voice_start")
        else:
            self.voice_start_intent_start = None
            self.voice_start_triggered = False

    def _process_new_slide_state(self, ok_detected):
        if ok_detected:
            if self.new_slide_intent_start is None:
                self.new_slide_intent_start = time.time()
                self.new_slide_triggered = False
            elif (not self.new_slide_triggered and
                  time.time() - self.new_slide_intent_start >= INTENT_NEW_SLIDE_SEC):
                if not self._in_cooldown():
                    self.new_slide_triggered = True
                    self._trigger_action("new_slide", COOLDOWN_NEW_SLIDE_MS)
        else:
            self.new_slide_intent_start = None
            self.new_slide_triggered = False

    def _reset_hand_state(self, hand_label):
        pass

    def _reset_inactive_hand_states(self, active_hand_labels):
        for hand_label in ("Left", "Right"):
            if hand_label not in active_hand_labels:
                self._reset_hand_state(hand_label)

    def _process_ily_state(self, ily_detected, w, h):
        if ily_detected:
            if self.ily_intent_start is None:
                self.ily_intent_start = time.time()
            elif not self.ily_active and time.time() - self.ily_intent_start >= INTENT_ILY_SEC:
                self.ily_active = True
                self.ily_last_tab_time = time.time() * 1000
                self.last_action_name = "alt_tab_start"
                self.callback("alt_tab_start")
            elif self.ily_active:
                now_ms = time.time() * 1000
                if now_ms - self.ily_last_tab_time >= ILY_TAB_REPEAT_MS:
                    self.ily_last_tab_time = now_ms
                    self.last_action_name = "alt_tab_next"
                    self.callback("alt_tab_next")
        else:
            if self.ily_active:
                self.ily_active = False
                self.last_action_name = "alt_tab_end"
                self.callback("alt_tab_end")
            self.ily_intent_start = None

    def _detect_swipe(self, hand_label, landmarks, frame_w, frame_h):
        if not self._is_hand_open(landmarks, frame_w, frame_h) or not (0.15 <= landmarks[9].y <= 0.90):
            self.position_buffer[hand_label].clear(); return
        buf = self.position_buffer[hand_label]
        buf.append((landmarks[9].x * frame_w, landmarks[9].y * frame_h, time.time() * 1000))
        if len(buf) < 4: return
        recent = list(buf)[-4:]
        velocities_x = [(recent[i][0] - recent[i-1][0]) / ((recent[i][2] - recent[i-1][2]) / 1000.0)
                        for i in range(1, len(recent)) if recent[i][2] > recent[i-1][2]]
        if not velocities_x: return
        peak_velocity = max(velocities_x, key=abs)
        delta_x_total = buf[-1][0] - buf[-4][0]
        delta_y_total = abs(buf[-1][1] - buf[-4][1])

        # Enforce horizontal swipe: ignore if vertical movement is significant
        if delta_y_total > abs(delta_x_total) * 0.7:
            return

        if abs(peak_velocity) < (frame_w * 0.3) or abs(delta_x_total) < (frame_w * 0.12): return
        arah = "kanan" if delta_x_total > 0 else "kiri"
        if arah != ("kanan" if peak_velocity > 0 else "kiri"): return

        # Natural swipe mapping: wave left (kiri) for next slide, wave right (kanan) for prev slide
        self._trigger_action("next" if arah == "kiri" else "prev", COOLDOWN_SWIPE_MS)
        buf.clear()

    def process_frame(self, frame, roi=None):
        h, w = frame.shape[:2]
        results = self.hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        all_hands = []
        valid_hands = []
        ily_detected = False
        voice_start_detected = False
        ok_detected = False
        two_hand_utility_pose = False
        if results.multi_hand_landmarks:
            for hand_landmarks, hand_info in zip(results.multi_hand_landmarks, results.multi_handedness):
                hand_label = "Left" if hand_info.classification[0].label == "Right" else "Right"
                all_hands.append((hand_label, hand_landmarks.landmark))
            for hand_landmarks, hand_info in zip(results.multi_hand_landmarks, results.multi_handedness):
                hand_label = "Left" if hand_info.classification[0].label == "Right" else "Right"
                lm = hand_landmarks.landmark
                if roi:
                    rx1, ry1, rx2, ry2 = roi
                    wrist = hand_landmarks.landmark[0]
                    wx, wy = int(wrist.x * w), int(wrist.y * h)
                    pad = 30
                    if not (rx1 - pad <= wx <= rx2 + pad and ry1 - pad <= wy <= ry2 + pad):
                        continue
                mp_draw.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                    mp_styles.get_default_hand_landmarks_style(),
                    mp_styles.get_default_hand_connections_style()
                )
                valid_hands.append((hand_label, lm))
                self._detect_laser_toggle(hand_label, lm, w, h)
                if self._is_ily_pose(lm, w, h):
                    ily_detected = True
                if self._is_ok_pose(lm, w, h):
                    ok_detected = True
                if voice_start_detected:
                    self.position_buffer[hand_label].clear()
                    self.start_state[hand_label]["stage"] = 0
                elif self.laser_active:
                    if self._is_index_pointing(lm, w, h): self._track_index_finger(lm, w, h)
                    else: self.filter_x = self.filter_y = self.last_cursor_x = self.last_cursor_y = None
                else:
                    if not self._in_cooldown():
                        if len(all_hands) < 2:
                            self._detect_swipe(hand_label, lm, w, h)
                            self._detect_start_presentation(hand_label, lm, w, h)
                            self._detect_stop_presentation(hand_label, lm)
                        else:
                            self.position_buffer[hand_label].clear()
                    else:
                        self.position_buffer[hand_label].clear()
                        self.start_state[hand_label]["stage"] = 0
                        self.stop_state[hand_label]["stage"] = 0
        active_hand_labels = {hand_label for hand_label, _ in valid_hands}
        self._reset_inactive_hand_states(active_hand_labels)
        self._process_voice_start_state(voice_start_detected)
        self._process_quit_state(all_hands, w, h)
        self._process_ily_state(ily_detected, w, h)
        self._process_circle_state(all_hands, w, h)
        self._process_cross_state(all_hands, w, h)
        self._process_new_slide_state(ok_detected)
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
    while True:
        ret, frame = cap.read()
        if not ret: break
        frame = engine.process_frame(cv2.flip(frame, 1))
        cv2.imshow("Mandor AI v2.4", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break
    cap.release()
    cv2.destroyAllWindows()
