# ============================================================
# MANDOR AI v2.0 — KONFIGURASI PUSAT
# Ubah nilai di sini untuk tuning tanpa menyentuh logika utama
# ============================================================

# --- KAMERA ---
CAMERA_INDEX = 0          # 0 = kamera utama/webcam bawaan
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30

# --- GESTUR: KIBASAN (Next /Prev Slide) ---
SWIPE_THRESHOLD_PX = 80      # Min delta X untuk dianggap kibasan

SWIPE_MAX_DURATION_MS = 1000  # Max durasi kibasan (ms), lebih lambat = bukan kibas
SWIPE_MIN_SPEED = 400  # Kecepatan minimum kibasan (pixel per detik)

# --- GESTUR: ANCANG-ANCANG (durasi dalam detik) ---
INTENT_FIST_SEC = 0.8     # Kepalan untuk Start Presentation
INTENT_CROSS_SEC = 1.0    # Kedua tangan di dada untuk Close
INTENT_SHAKA_SEC = 0.8    # Pose Shaka (🤙) untuk toggle Laser Pointer

# --- GESTUR: QUIT (T-Pose / Time Out) ---
INTENT_QUIT_SEC = 1.0       # Harus ditahan 1 detik agar tidak tereksekusi tanpa sengaja
COOLDOWN_QUIT_MS = 2000     # Cooldown super panjang (2 detik) karena ini aksi destruktif

# --- GESTUR: FINGER SNAP (Blackout/Whiteout) ---
SNAP_DISTANCE_CLOSED = 20  # Jarak jempol-jari tengah saat menempel (px)
SNAP_DISTANCE_OPEN = 80    # Jarak jempol-jari tengah setelah snap (px)
SNAP_MAX_FRAMES = 3        # Max frame untuk transisi snap

# --- COOLDOWN (dalam milidetik) ---
COOLDOWN_SWIPE_MS = 1000
COOLDOWN_START_MS = 2000
COOLDOWN_CLOSE_MS = 2000
COOLDOWN_SNAP_MS = 1
COOLDOWN_LASER_TOGGLE_MS = 1500  # Cooldown antar toggle laser

# --- LASER POINTER & CURSOR TRACKING ---
LASER_MIN_CUTOFF = 0.4       # One Euro Filter: makin kecil = makin tenang saat diam
LASER_BETA = 0.007           # One Euro Filter: makin besar = makin responsif saat gerak
LASER_D_CUTOFF = 1.0         # One Euro Filter: derivative cutoff
LASER_BOX_X_MIN = 0.20       # Batas kiri zona interaksi (% dari frame)
LASER_BOX_X_MAX = 0.80       # Batas kanan zona interaksi
LASER_BOX_Y_MIN = 0.15       # Batas atas zona interaksi
LASER_BOX_Y_MAX = 0.85       # Batas bawah zona interaksi
LASER_DEADZONE_PX = 2        # Deadzone kursor (pixel layar)

# --- OBJECT LOCKING ---
YOLO_CONFIDENCE = 0.5
LOCK_LOST_SEC = 3          # Toleransi presenter hilang dari frame

# --- MEDIAPIPE ---
MP_DETECTION_CONFIDENCE = 0.7
MP_TRACKING_CONFIDENCE = 0.7