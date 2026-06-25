CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30
SHOW_BACKEND_WINDOW = False

SWIPE_THRESHOLD_PX = 80

SWIPE_MAX_DURATION_MS = 1000
SWIPE_MIN_SPEED = 400

INTENT_FIST_SEC = 0.8        # Lebih aman untuk mulai presentasi
INTENT_LASER_SEC = 0.6       # Lebih aman untuk toggle laser pointer
INTENT_VOICE_START_SEC = 0.6 # Lebih aman untuk voice command start
INTENT_ILY_SEC = 0.6         # Lebih aman untuk alt-tab (App Switcher)
INTENT_POWERPOINT_SEC = 0.8  # Lebih aman untuk membuka PowerPoint (Circle)

INTENT_QUIT_SEC = 1.0        # Sangat aman untuk keluar presentasi (Prayer/Fist)
COOLDOWN_QUIT_MS = 1000

SNAP_DISTANCE_CLOSED = 20
SNAP_DISTANCE_OPEN = 80
SNAP_MAX_FRAMES = 3

COOLDOWN_SWIPE_MS = 400
COOLDOWN_START_MS = 1000
COOLDOWN_CLOSE_MS = 1000
COOLDOWN_SNAP_MS = 1
COOLDOWN_LASER_TOGGLE_MS = 800
COOLDOWN_VOICE_START_MS = 1500
COOLDOWN_ILY_MS = 300
ILY_TAB_REPEAT_MS = 400
COOLDOWN_POWERPOINT_MS = 2500
INTENT_NEW_SLIDE_SEC = 0.8   # Lebih aman untuk OK pose (Slide Baru)
COOLDOWN_NEW_SLIDE_MS = 1000
INTENT_CROSS_SEC = 1.0       # Sangat aman untuk L-pose (Hapus Slide - tindakan destruktif)
COOLDOWN_DELETE_MS = 1200    # Ditambah sedikit biar cooldown lebih aman
INTENT_UNDO_SEC = 0.8        # Lebih aman untuk Thumbs Down (Undo)
COOLDOWN_UNDO_MS = 1000

LASER_MIN_CUTOFF = 0.05
LASER_BETA = 0.05
LASER_D_CUTOFF = 1.0
LASER_BOX_X_MIN = 0.20
LASER_BOX_X_MAX = 0.80
LASER_BOX_Y_MIN = 0.15
LASER_BOX_Y_MAX = 0.85
LASER_DEADZONE_PX = 3

YOLO_CONFIDENCE = 0.5
LOCK_LOST_SEC = 3
YOLO_FRAME_SKIP = 3

MP_DETECTION_CONFIDENCE = 0.7
MP_TRACKING_CONFIDENCE = 0.7

DOCUMENT_SEARCH_PATHS = ["~/Documents", "~/Desktop", "~/Downloads"]
DOCUMENT_SEARCH_EXTENSIONS = [".docx", ".xlsx", ".pptx", ".pdf", ".txt", ".csv"]
DOCUMENT_SEARCH_MAX_RESULTS = 5
DOCUMENT_INDEX_TTL_SEC = 60
DOCUMENT_INDEX_MAX_FILES = 20_000
DOCUMENT_SEARCH_EXCLUDED_DIRS = [
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
]
