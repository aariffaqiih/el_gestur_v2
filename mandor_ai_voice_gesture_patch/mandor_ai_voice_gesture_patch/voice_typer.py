# ============================================================
# MANDOR AI — VOICE TYPER MODULE
# Fitur: Mengetik teks dengan suara (Bahasa Indonesia)
# Engine: Google Web Speech API (gratis, tanpa API key)
# ============================================================

import speech_recognition as sr
import pyautogui
import threading
import time
import re
import sys

# Fix Windows console encoding agar emoji tidak crash
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

def _safe_print(*args, **kwargs):
    """Print yang aman untuk Windows (fallback jika emoji gagal)."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        text = " ".join(str(a) for a in args)
        print(text.encode('ascii', 'replace').decode('ascii'), **kwargs)

class VoiceTyper:
    """
    Modul Voice-to-Text yang berjalan di background thread.
    Mendengarkan suara dari mikrofon, mengenali ucapan dalam
    Bahasa Indonesia, lalu mengetikkan hasilnya ke aplikasi aktif.
    """

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self._thread = None
        self._stop_event = threading.Event()
        self._is_running = False

        # --- Konfigurasi Recognizer ---
        # Sesuaikan sensitivitas untuk lingkungan yang agak berisik
        self.recognizer.energy_threshold = 300        # Batas minimum energi suara
        self.recognizer.dynamic_energy_threshold = True  # Auto-adjust ke lingkungan
        self.recognizer.pause_threshold = 0.8         # Detik diam sebelum dianggap selesai bicara
        self.recognizer.phrase_threshold = 0.3        # Minimum durasi frasa

        # --- State publik (bisa dibaca oleh server/frontend) ---
        self.last_text = ""
        self.status = "idle"   # idle | listening | processing | error
        self.error_msg = ""

        # --- Command keywords (vokal → aksi keyboard) ---
        # Pengguna bisa bilang ini kapan saja saat voice typer aktif
        self.VOICE_COMMANDS = {
            "tekan enter":      lambda: pyautogui.press('enter'),
            "baris baru":       lambda: pyautogui.press('enter'),
            "enter":            lambda: pyautogui.press('enter'),
            "hapus":            lambda: pyautogui.hotkey('ctrl', 'backspace'),
            "hapus semua":      lambda: (pyautogui.hotkey('ctrl', 'a'), pyautogui.press('delete')),
            "spasi":            lambda: pyautogui.press('space'),
            "tab":              lambda: pyautogui.press('tab'),
            "titik":            lambda: pyautogui.typewrite('.', interval=0),
            "koma":             lambda: pyautogui.typewrite(',', interval=0),
            "tanda tanya":      lambda: pyautogui.typewrite('?', interval=0),
            "tanda seru":       lambda: pyautogui.typewrite('!', interval=0),
        }

        _safe_print("🎙️  VoiceTyper modul dimuat. Siap digunakan.")

    # ========================================================
    # INTERNAL: Loop Utama (berjalan di thread terpisah)
    # ========================================================
    def _listen_loop(self):
        """Loop utama yang terus mendengarkan mikrofon."""
        _safe_print("🎙️  VoiceTyper: Mulai mendengarkan...")

        # Kalibrasi noise ambient sekali saat mulai
        try:
            with self.microphone as source:
                self.status = "calibrating"
                _safe_print("🔇 Kalibrasi noise ambient (1 detik)...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                _safe_print("✅ Kalibrasi selesai. Mulai mendengarkan.")
        except Exception as e:
            self.status = "error"
            self.error_msg = f"Gagal akses mikrofon: {e}"
            _safe_print(f"❌ {self.error_msg}")
            self._is_running = False
            return

        while not self._stop_event.is_set():
            try:
                self.status = "listening"
                self.error_msg = ""

                with self.microphone as source:
                    # Dengarkan audio (timeout 5 detik, phrase_time_limit 15 detik)
                    audio = self.recognizer.listen(
                        source,
                        timeout=5,
                        phrase_time_limit=15
                    )

                # Proses audio → teks
                self.status = "processing"
                text = self.recognizer.recognize_google(audio, language="id-ID")
                text = text.strip()

                if not text:
                    continue

                _safe_print(f"🗣️  Terdengar: \"{text}\"")
                self.last_text = text

                # Cek apakah ini voice command
                if not self._try_execute_command(text):
                    # Bukan command → ketik teksnya
                    self._type_text(text)

            except sr.WaitTimeoutError:
                # Tidak ada suara selama 5 detik — lanjut loop
                continue
            except sr.UnknownValueError:
                # Audio terdengar tapi tidak bisa dikenali
                _safe_print("🔇 Suara tidak dikenali, ulangi...")
                continue
            except sr.RequestError as e:
                # Masalah jaringan / API
                self.status = "error"
                self.error_msg = f"Error API: {e}"
                _safe_print(f"⚠️  {self.error_msg}. Retry dalam 2 detik...")
                time.sleep(2)
                continue
            except Exception as e:
                # Error tak terduga
                self.status = "error"
                self.error_msg = str(e)
                _safe_print(f"❌ Error: {e}")
                time.sleep(1)
                continue

        self.status = "idle"
        self._is_running = False
        _safe_print("🎙️  VoiceTyper: Berhenti mendengarkan.")

    # ========================================================
    # INTERNAL: Eksekusi Voice Command
    # ========================================================
    def _try_execute_command(self, text):
        """
        Cek apakah teks yang dikenali adalah voice command.
        Return True jika command ditemukan dan dieksekusi.
        """
        lowered = text.lower().strip()
        for keyword, action in self.VOICE_COMMANDS.items():
            if lowered == keyword:
                _safe_print(f"⚡ Voice Command: \"{keyword}\"")
                action()
                return True
        return False

    # ========================================================
    # INTERNAL: Ketik Teks ke Aplikasi Aktif
    # ========================================================
    def _type_text(self, text):
        """
        Mengetik teks menggunakan pyperclip + pyautogui hotkey paste.
        Ini JAUH lebih andal daripada pyautogui.typewrite() karena:
        1. Mendukung karakter Unicode / non-ASCII (huruf Indonesia, emoji)
        2. Lebih cepat (satu operasi paste vs karakter per karakter)
        """
        try:
            import pyperclip
            pyperclip.copy(text + " ")
            pyautogui.hotkey('ctrl', 'v')
            _safe_print(f"✍️  Diketik: \"{text}\"")
        except ImportError:
            # Fallback: pakai pyautogui.write (terbatas ASCII)
            # Untuk karakter non-ASCII, kita pakai Windows clipboard API
            self._clipboard_type(text + " ")

    def _clipboard_type(self, text):
        """Fallback: tulis ke clipboard Windows dan paste."""
        try:
            import subprocess
            process = subprocess.Popen(
                ['clip'], stdin=subprocess.PIPE, shell=True
            )
            process.communicate(text.encode('utf-16-le'))
            time.sleep(0.05)
            pyautogui.hotkey('ctrl', 'v')
            _safe_print(f"✍️  Diketik (via clip): \"{text.strip()}\"")
        except Exception as e:
            # Ultimate fallback: pakai pyautogui.write
            safe_text = text.encode('ascii', 'replace').decode('ascii')
            pyautogui.write(safe_text, interval=0.02)
            _safe_print(f"✍️  Diketik (fallback): \"{safe_text.strip()}\"")

    # ========================================================
    # PUBLIC API: Start / Stop / Status
    # ========================================================
    def start(self):
        """Mulai mendengarkan suara di background thread."""
        if self._is_running:
            _safe_print("⚠️  VoiceTyper sudah berjalan!")
            return False

        self._stop_event.clear()
        self._is_running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        """Hentikan voice typer."""
        if not self._is_running:
            _safe_print("⚠️  VoiceTyper tidak sedang berjalan.")
            return False

        self._stop_event.set()
        self._is_running = False
        self.status = "idle"
        _safe_print("🛑 VoiceTyper: Perintah stop dikirim.")
        return True

    def is_running(self):
        """Apakah voice typer sedang aktif?"""
        return self._is_running

    def get_status(self):
        """Kembalikan dict status untuk endpoint API."""
        return {
            "is_running": self._is_running,
            "status": self.status,
            "last_text": self.last_text,
            "error": self.error_msg
        }


# ============================================================
# TEST MANDIRI
# ============================================================
if __name__ == "__main__":
    _safe_print("=" * 60)
    _safe_print("🎙️  TEST VOICE TYPER — Bahasa Indonesia")
    _safe_print("Bicara ke mikrofon, teks akan diketikkan otomatis.")
    _safe_print("Tekan Ctrl+C untuk berhenti.")
    _safe_print("=" * 60)

    vt = VoiceTyper()
    vt.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        vt.stop()
        _safe_print("\n👋 Selesai.")
