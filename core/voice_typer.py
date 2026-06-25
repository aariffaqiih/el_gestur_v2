import speech_recognition as sr
import pyautogui
import threading
import time
import sys
import re

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

def _safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        text = " ".join(str(a) for a in args)
        print(text.encode('ascii', 'replace').decode('ascii'), **kwargs)

class VoiceTyper:

    def __init__(self, command_handler=None, device_index=None):
        self.recognizer = sr.Recognizer()
        self.device_index = device_index
        self.microphone = sr.Microphone(device_index=self.device_index)
        self._command_handler = command_handler
        self._thread = None
        self._stop_event = threading.Event()
        self._is_running = False

        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.recognizer.phrase_threshold = 0.3

        self.last_text = ""
        self.status = "idle"
        self.error_msg = ""
        self.capitalize_next = True
        self.is_muted = False

        # Platform-specific hotkey shortcuts
        is_mac = sys.platform == "darwin"
        cmd_key = "command" if is_mac else "ctrl"
        word_delete_key = "option" if is_mac else "ctrl"

        self.VOICE_COMMANDS = {
            "tekan enter":      lambda: pyautogui.press('enter'),
            "baris baru":       lambda: pyautogui.press('enter'),
            "enter":            lambda: pyautogui.press('enter'),
            "hapus":            lambda: pyautogui.hotkey(word_delete_key, 'backspace'),
            "hapus semua":      lambda: (pyautogui.hotkey(cmd_key, 'a'), pyautogui.press('delete')),
            "spasi":            lambda: pyautogui.press('space'),
            "tab":              lambda: pyautogui.press('tab'),
            "titik":            lambda: pyautogui.typewrite('.', interval=0),
            "koma":             lambda: pyautogui.typewrite(',', interval=0),
            "tanda tanya":      lambda: pyautogui.typewrite('?', interval=0),
            "tanda seru":       lambda: pyautogui.typewrite('!', interval=0),
        }

        _safe_print("🎙️  VoiceTyper modul dimuat. Siap digunakan.")

    def _listen_loop(self):
        _safe_print("🎙️  VoiceTyper: Mulai mendengarkan...")

        try:
            with self.microphone as source:
                self.status = "calibrating"
                _safe_print("🔇 Kalibrasi noise ambient (1 detik)...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                _safe_print("✅ Kalibrasi selesai. Mulai mendengarkan.")

                self.status = "listening"
                while not self._stop_event.is_set():
                    try:
                        self.status = "listening"
                        self.error_msg = ""
                        audio = self.recognizer.listen(
                            source,
                            timeout=5,
                            phrase_time_limit=15
                        )

                        self.status = "processing"
                        text = self.recognizer.recognize_google(audio, language="id-ID")
                        text = text.strip()

                        if not text:
                            continue

                        _safe_print(f"🗣️  Terdengar: \"{text}\"")
                        self.process_text(text)

                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
                        _safe_print("🔇 Suara tidak dikenali, ulangi...")
                        continue
                    except sr.RequestError as e:
                        self.status = "error"
                        self.error_msg = f"Error API: {e}"
                        _safe_print(f"⚠️  {self.error_msg}. Retry dalam 2 detik...")
                        time.sleep(2)
                        continue
                    except Exception as e:
                        self.status = "error"
                        self.error_msg = str(e)
                        _safe_print(f"❌ Error: {e}")
                        time.sleep(1)
                        continue
        except Exception as e:
            self.status = "error"
            self.error_msg = f"Gagal akses mikrofon: {e}"
            _safe_print(f"❌ {self.error_msg}")
            self._is_running = False
            return

        self.status = "idle"
        self._is_running = False
        _safe_print("🎙️  VoiceTyper: Berhenti mendengarkan.")

    def _try_execute_command(self, text):
        lowered = text.lower().strip()
        for keyword, action in self.VOICE_COMMANDS.items():
            if lowered == keyword:
                _safe_print(f"⚡ Voice Command: \"{keyword}\"")
                action()
                return True
        return False

    def _try_execute_dynamic_command(self, text):
        if self._command_handler is None:
            return None
        try:
            result = self._command_handler(text)
        except Exception as error:
            _safe_print(f"❌ Dynamic command gagal: {error}")
            return {
                "status": "error",
                "message": f"Perintah gagal dijalankan: {error}",
            }
        if result is not None:
            _safe_print(f"⚡ Dynamic Voice Command: \"{text}\"")
        return result

    def _type_text(self, text):
        is_mac = sys.platform == "darwin"
        cmd_key = "command" if is_mac else "ctrl"
        try:
            import pyperclip
            pyperclip.copy(text + " ")
            time.sleep(0.1)  # Tunggu agar clipboard sinkron di OS
            if is_mac:
                pyautogui.keyDown('command')
                time.sleep(0.02)
                pyautogui.press('v')
                time.sleep(0.02)
                pyautogui.keyUp('command')
            else:
                pyautogui.hotkey(cmd_key, 'v')
            _safe_print(f"✍️  Diketik: \"{text}\"")
        except Exception:
            self._clipboard_type(text + " ")

    def _clipboard_type(self, text):
        is_mac = sys.platform == "darwin"
        cmd_key = "command" if is_mac else "ctrl"
        try:
            import subprocess
            if is_mac:
                process = subprocess.Popen(
                    ['pbcopy'], stdin=subprocess.PIPE
                )
                process.communicate(text.encode('utf-8'))
            else:
                process = subprocess.Popen(
                    ['clip'], stdin=subprocess.PIPE, shell=True
                )
                process.communicate(text.encode('utf-16-le'))
            time.sleep(0.1)  # Tunggu agar clipboard sinkron di OS
            if is_mac:
                pyautogui.keyDown('command')
                time.sleep(0.02)
                pyautogui.press('v')
                time.sleep(0.02)
                pyautogui.keyUp('command')
            else:
                pyautogui.hotkey(cmd_key, 'v')
            _safe_print(f"✍️  Diketik (via clipboard): \"{text.strip()}\"")
        except Exception as e:
            safe_text = text.encode('ascii', 'replace').decode('ascii')
            pyautogui.write(safe_text, interval=0.02)
            _safe_print(f"✍️  Diketik (fallback): \"{safe_text.strip()}\"")

    def _clean_and_format_text(self, text):
        # 1. Smart Punctuation Replacement for Indonesian using regex word boundaries
        replacements = [
            (r"\s*\b(?:titik dua)\b", ":"),
            (r"\s*\b(?:titik koma)\b", ";"),
            (r"\s*\b(?:tanda tanya)\b", "?"),
            (r"\s*\b(?:tanda seru)\b", "!"),
            (r"\s*\b(?:buka kurung)\b", " ("),
            (r"\s*\b(?:tutup kurung)\b", ") "),
            (r"\s*\b(?:titik)\b", "."),
            (r"\s*\b(?:koma)\b", ","),
            (r"\s*\b(?:baris baru)\b", "\n"),
            (r"\s*\b(?:paragraf baru)\b", "\n\n")
        ]
        
        # Replace punctuation words case-insensitively using regex
        for pattern_str, punc in replacements:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            text = pattern.sub(punc, text)
            
        # Clean up double/multiple spaces around punctuation
        text = re.sub(r'\s+([.,;:?!])', r'\1', text)
        text = re.sub(r'\(\s+', '(', text)
        text = re.sub(r'\s+\)', ')', text)
        
        # 2. Auto-capitalization
        # Capitalize the first alphabetic character if capitalize_next is True
        if getattr(self, 'capitalize_next', True):
            match = re.search(r'[a-zA-Z]', text)
            if match:
                idx = match.start()
                text = text[:idx] + text[idx].upper() + text[idx+1:]
                self.capitalize_next = False
            
        # Capitalize letters following sentence endings (. ? !) inside the text
        def capitalize_sentences(match):
            return match.group(1) + match.group(2).upper()
            
        text = re.sub(r'([.!?]\s+)([a-z])', capitalize_sentences, text)
        
        # Capitalize letters following a newline character
        def capitalize_newlines(match):
            return match.group(1) + match.group(2).upper()
            
        text = re.sub(r'(\n\s*)([a-z])', capitalize_newlines, text)
        
        # Check if the overall phrase ends with sentence-ending punctuation or a newline
        trimmed = text.strip()
        if trimmed.endswith((".", "?", "!")) or "\n" in text:
            self.capitalize_next = True
            
        return text

    def process_text(self, text):
        if getattr(self, "is_muted", False):
            _safe_print("🔇 VoiceTyper dibisukan. Teks diabaikan.")
            return {"status": "muted", "message": "Voice Typer dibisukan"}

        stripped_text = str(text).strip()
        if not stripped_text:
            return {"status": "empty"}

        self.last_text = stripped_text
        dynamic_result = self._try_execute_dynamic_command(stripped_text)
        if dynamic_result is not None:
            self.last_text = f"[Command] {stripped_text}"
            return dynamic_result

        if self._try_execute_command(stripped_text):
            self.last_text = f"[Command] {stripped_text.lower()}"
            return {"status": "command", "command": stripped_text.lower()}

        formatted_text = self._clean_and_format_text(stripped_text)
        self._type_text(formatted_text)
        return {"status": "success", "typed": formatted_text}

    def mute(self):
        self.is_muted = True
        _safe_print("🔇 VoiceTyper: Dibisukan (Muted)")

    def unmute(self):
        self.is_muted = False
        _safe_print("🔊 VoiceTyper: Suara aktif (Unmuted)")

    def toggle_mute(self):
        self.is_muted = not getattr(self, "is_muted", False)
        _safe_print(f"🎙️ VoiceTyper: Mute status diubah ke {self.is_muted}")
        return self.is_muted

    def set_command_handler(self, command_handler):
        self._command_handler = command_handler

    def set_device_index(self, index):
        if index is None or index == "" or str(index).lower() == "default":
            self.device_index = None
        else:
            try:
                self.device_index = int(index)
            except ValueError:
                self.device_index = None
        
        self.microphone = sr.Microphone(device_index=self.device_index)
        _safe_print(f"🎙️ VoiceTyper: device_index diatur ke {self.device_index}")
        
        # If running, restart to apply new device immediately
        if self._is_running:
            _safe_print("🎙️ VoiceTyper: Merestart listener untuk menggunakan perangkat baru...")
            self.stop()
            # Wait for thread to terminate
            if self._thread:
                self._thread.join(timeout=1.0)
            self.start()

    def start(self):
        if self._is_running:
            _safe_print("⚠️  VoiceTyper sudah berjalan!")
            return False

        # Always recreate microphone instance to pick up latest device_index
        self.microphone = sr.Microphone(device_index=self.device_index)
        self._stop_event.clear()
        self._is_running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        if not self._is_running:
            _safe_print("⚠️  VoiceTyper tidak sedang berjalan.")
            return False

        self._stop_event.set()
        self._is_running = False
        self.status = "idle"
        _safe_print("🛑 VoiceTyper: Perintah stop dikirim.")
        return True

    def is_running(self):
        return self._is_running

    def get_status(self):
        return {
            "is_running": self._is_running,
            "status": self.status,
            "last_text": self.last_text,
            "error": self.error_msg,
            "device_index": self.device_index,
            "is_muted": getattr(self, "is_muted", False)
        }


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
