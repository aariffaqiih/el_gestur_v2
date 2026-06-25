import cv2
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
import time
import numpy as np
from .config import CAMERA_FPS, YOLO_CONFIDENCE, LOCK_LOST_SEC, CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT, YOLO_FRAME_SKIP
class ObjectLocker:
    def __init__(self):
        print("⏳ Loading YOLOv8 model...")
        
        # Resolve path to yolov8n.pt when running as frozen app
        import sys, os
        model_name = 'yolov8n.pt'
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
            model_path = os.path.join(base_path, model_name)
            if not os.path.exists(model_path):
                # Fallback to Resources folder on macOS BUNDLE
                resources_path = os.path.join(os.path.dirname(base_path), 'Resources')
                model_path = os.path.join(resources_path, model_name)
        else:
            model_path = model_name
            
        self.model = YOLO(model_path)
        
        # Auto-detect best device (CUDA for Windows with NVIDIA, MPS for macOS, CPU fallback)
        import torch
        self.device = 'cpu'
        if torch.cuda.is_available():
            self.device = 'cuda'
        elif torch.backends.mps.is_available():
            self.device = 'mps'
        print(f"✅ YOLOv8 device set to: {self.device}")

        print("⏳ Setup DeepSORT...")
        self.tracker = DeepSort(max_age=int(CAMERA_FPS * 5), embedder=None)

        self.locked_id = None
        self.lock_lost_time = 0
        self.center_timers = {}

        self.is_active = False
        self.wants_to_lock = False

        # Performance optimization attributes
        self.frame_count = 0
        self.last_tracks = []

        print("✅ ObjectLocker siap dalam mode STANDBY!")

    def set_locked_id(self, track_id):
        self.locked_id = str(track_id)
        self.center_timers.clear()
        self.wants_to_lock = False
        print(f"🔒 PRESENTER TERKUNCI: ID {self.locked_id}")

    def unlock(self):
        self.locked_id = None
        self.center_timers.clear()
        self.wants_to_lock = False
        print("🔓 PRESENTER DILEPAS")

    def process_frame(self, frame):
        h, w = frame.shape[:2]

        if not self.is_active:
            cv2.putText(frame, "EL PRESENTASI - ENGINE STANDBY", (30, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, "Nyalakan engine melalui kontrol aplikasi web.", (30, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
            return frame, None

        center_x_min = int(w * 0.35)
        center_x_max = int(w * 0.65)

        self.frame_count += 1

        if self.frame_count % YOLO_FRAME_SKIP == 0 or self.wants_to_lock or not self.last_tracks:
            results = self.model(frame, classes=[0], conf=YOLO_CONFIDENCE, verbose=False, imgsz=320, device=self.device)
            detections = []
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = box.conf[0].item()
                    box_w, box_h = x2 - x1, y2 - y1
                    detections.append(([int(x1), int(y1), int(box_w), int(box_h)], conf, 'person'))

            embeds = [np.ones(128, dtype=np.float32) for _ in range(len(detections))]
            tracks = self.tracker.update_tracks(detections, embeds=embeds)
            self.last_tracks = tracks
        else:
            tracks = self.last_tracks

        presenter_roi = None
        locked_person_found = False

        if not self.locked_id:
            cv2.line(frame, (center_x_min, 0), (center_x_min, h), (0, 255, 255), 1, cv2.LINE_AA)
            cv2.line(frame, (center_x_max, 0), (center_x_max, h), (0, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(frame, "ZONA SETUP - DIAM 3 DETIK UNTUK KUNCI", (center_x_min - 50, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        for track in tracks:
            if not track.is_confirmed():
                continue

            track_id = str(track.track_id)
            ltrb = track.to_ltrb()

            tx1 = max(0, int(ltrb[0]))
            ty1 = max(0, int(ltrb[1]))
            tx2 = min(w, int(ltrb[2]))
            ty2 = min(h, int(ltrb[3]))

            if self.locked_id and track_id == self.locked_id:
                locked_person_found = True
                presenter_roi = (tx1, ty1, tx2, ty2)
                cv2.rectangle(frame, (tx1, ty1), (tx2, ty2), (0, 255, 0), 2)
                cv2.putText(frame, f"PRESENTER ID:{track_id}", (tx1, ty1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            elif not self.locked_id:
                if self.wants_to_lock:
                    self.set_locked_id(track_id)
                    break

                cx = (tx1 + tx2) // 2
                if center_x_min < cx < center_x_max:
                    if track_id not in self.center_timers:
                        self.center_timers[track_id] = time.time()
                    else:
                        elapsed = time.time() - self.center_timers[track_id]
                        cv2.putText(frame, f"Locking... {int(elapsed)}s", (tx1, ty1 - 25),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

                        if elapsed >= 3.0:
                            self.set_locked_id(track_id)
                            break
                else:
                    if track_id in self.center_timers:
                        del self.center_timers[track_id]

                cv2.rectangle(frame, (tx1, ty1), (tx2, ty2), (200, 200, 200), 1)
                cv2.putText(frame, f"ID:{track_id}", (tx1, ty1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            elif self.locked_id and track_id != self.locked_id:
                cv2.rectangle(frame, (tx1, ty1), (tx2, ty2), (0, 0, 255), 1)
                cv2.putText(frame, f"ID:{track_id}", (tx1, ty1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        if self.locked_id and not locked_person_found:
            if self.lock_lost_time == 0:
                self.lock_lost_time = time.time()
            elif time.time() - self.lock_lost_time >= LOCK_LOST_SEC:
                print(f"⏰ PRESENTER HILANG > {LOCK_LOST_SEC} DETIK. MELEPAS KUNCI OTOMATIS.")
                self.unlock()

            if self.locked_id:
                cv2.putText(frame, f"DI LUAR FRAME! (MENUNGGU ID: {self.locked_id})", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
        else:
            self.lock_lost_time = 0

        return frame, presenter_roi

if __name__ == "__main__":
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    locker = ObjectLocker()
    locker.is_active = True

    while True:
        ret, frame = cap.read()
        if not ret: break

        frame = cv2.flip(frame, 1)
        frame, roi = locker.process_frame(frame)

        cv2.imshow("Mandor AI v2 - Multi-Locker", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'): break
        elif key == ord('u'): locker.unlock()
        elif ord('1') <= key <= ord('9'): locker.set_locked_id(str(chr(key)))

    cap.release()
    cv2.destroyAllWindows()