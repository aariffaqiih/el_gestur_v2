import os
import sys

# Redirect output to log file or dummy writer when frozen to prevent print() crashes
if getattr(sys, 'frozen', False):
    class DummyWriter:
        def write(self, data): pass
        def flush(self): pass
    try:
        log_path = "/tmp/el_presentasi_debug.log"
        sys.stdout = open(log_path, "w", buffering=1)
        sys.stderr = sys.stdout
    except Exception:
        sys.stdout = DummyWriter()
        sys.stderr = DummyWriter()
elif sys.stdout is None:
    class DummyWriter:
        def write(self, data): pass
        def flush(self): pass
    sys.stdout = DummyWriter()
    sys.stderr = DummyWriter()

# Set environment variable to 0 so OpenCV doesn't skip permission prompts on macOS,
# though we also request it explicitly on the main thread to be safe.
os.environ["OPENCV_AVFOUNDATION_SKIP_AUTH"] = "0"

import threading
import time
import webview
from server import app, camera_loop

def request_mac_camera_permission():
    if sys.platform == "darwin":
        try:
            import objc
            # Register metadata for requestAccessForMediaType:completionHandler:
            objc.registerMetaDataForSelector(
                b"AVCaptureDevice",
                b"requestAccessForMediaType:completionHandler:",
                {
                    "arguments": {
                        3: {
                            "type": objc._C_ID,
                            "block": True,
                            "callable": {
                                "retval": {"type": b"v"},
                                "arguments": {
                                    0: {"type": b"^v"},  # Context
                                    1: {"type": objc._C_NSBOOL}  # BOOL granted
                                }
                            }
                        }
                    }
                }
            )
            
            av_globals = {}
            objc.loadBundle('AVFoundation', bundle_path='/System/Library/Frameworks/AVFoundation.framework', module_globals=av_globals)
            AVCaptureDevice = av_globals.get('AVCaptureDevice')
            
            # 0: NotDetermined, 1: Restricted, 2: Denied, 3: Authorized
            status = AVCaptureDevice.authorizationStatusForMediaType_('vide')
            print(f"[macOS Camera] Status otorisasi kamera: {status}")
            
            if status == 0:  # AVAuthorizationStatusNotDetermined
                print("[macOS Camera] Meminta izin akses kamera...")
                def handler(granted):
                    print(f"[macOS Camera] Hasil request izin: {granted}")
                AVCaptureDevice.requestAccessForMediaType_completionHandler_('vide', handler)
            elif status == 2:  # Denied
                print("[macOS Camera] PERINGATAN: Akses kamera ditolak! Harap izinkan aplikasi di Pengaturan Sistem > Privasi & Keamanan > Kamera.")
        except Exception as e:
            print(f"[macOS Camera] Gagal memproses izin kamera macOS: {e}")

def request_mac_accessibility_permission():
    if sys.platform == "darwin":
        try:
            import objc
            # Load the ApplicationServices framework dynamically
            AS = objc.loadBundle('ApplicationServices', bundle_path='/System/Library/Frameworks/ApplicationServices.framework', module_globals=globals())
            objc.loadBundleFunctions(AS, globals(), [('AXIsProcessTrustedWithOptions', b'Z@')])
            
            # This option triggers the macOS system dialog if not trusted
            options = {'AXTrustedCheckOptionPrompt': True}
            trusted = AXIsProcessTrustedWithOptions(options)
            print(f"[macOS Accessibility] Trusted status: {trusted}")
            return trusted
        except Exception as e:
            print(f"[macOS Accessibility] Gagal memproses izin aksesibilitas macOS: {e}")
    return True

def run_permission_checks():
    # Tunggu 3 detik agar Cocoa run loop & GUI stabil
    time.sleep(3.0)
    request_mac_camera_permission()
    request_mac_accessibility_permission()

class WebviewAPI:
    def js_log(self, level, message):
        print(f"[JS {level}] {message}", flush=True)

def start_flask():
    # Menjalankan Flask di localhost port 5005
    app.run(host="127.0.0.1", port=5005, debug=False, use_reloader=False)

def main():
    print("Memulai El Presentasi - Mode Aplikasi Desktop...")

    # Jika berjalan sebagai standalone app (PyInstaller), sesuaikan working directory ke folder Resources macOS
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        resources_path = os.path.join(os.path.dirname(base_path), 'Resources')
        if os.path.exists(resources_path):
            os.chdir(resources_path)
        else:
            os.chdir(base_path)


    # 1. Jalankan Flask server di thread latar belakang (daemon)
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    # 2. Jalankan loop pemrosesan kamera di thread latar belakang (daemon)
    camera_thread = threading.Thread(target=camera_loop, daemon=True)
    camera_thread.start()

    # 2b. Jalankan permohonan izin kamera & aksesibilitas di thread terpisah (delay 3 detik)
    permission_thread = threading.Thread(target=run_permission_checks, daemon=True)
    permission_thread.start()

    # Tunggu sebentar agar server Flask siap menerima request
    time.sleep(1.5)

    # 3. Dapatkan path file index.html frontend
    if getattr(sys, 'frozen', False):
        # Gunakan path relatif agar pywebview menggunakan server HTTP lokal (Bottle)
        index_html_path = "frontend/index.html"
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        index_html_path = os.path.join(current_dir, "frontend", "index.html")

    if not os.path.exists(index_html_path):
        print(f"Kesalahan: file frontend tidak ditemukan di {index_html_path}")
        sys.exit(1)

    print(f"Membuka antarmuka aplikasi dari: file://{index_html_path}")

    # 4. Buat window aplikasi desktop dan mulai GUI loop pada main thread
    api = WebviewAPI()
    window = webview.create_window(
        title="El Presentasi - Desktop App",
        url=index_html_path,
        js_api=api,
        width=1280,
        height=850,
        resizable=True,
        min_size=(1024, 768),
        background_color='#0a1024'
    )

    def on_loaded():
        try:
            body_width = window.evaluate_js('document.body.offsetWidth')
            body_height = window.evaluate_js('document.body.offsetHeight')
            bg_color = window.evaluate_js('window.getComputedStyle(document.body).backgroundColor')
            color = window.evaluate_js('window.getComputedStyle(document.body).color')
            opacity = window.evaluate_js('window.getComputedStyle(document.body).opacity')
            display = window.evaluate_js('window.getComputedStyle(document.body).display')
            visibility = window.evaluate_js('window.getComputedStyle(document.body).visibility')
            
            html_bg = window.evaluate_js('window.getComputedStyle(document.documentElement).backgroundColor')
            body_bg_img = window.evaluate_js('window.getComputedStyle(document.body).backgroundImage')
            sheets_count = window.evaluate_js('document.styleSheets.length')
            sheets_hrefs = window.evaluate_js('Array.from(document.styleSheets).map(s => s.href)')
            
            # Get rules count for style.css (usually stylesheet index 2)
            css_rules_count = "N/A"
            try:
                css_rules_count = window.evaluate_js('document.styleSheets[2].cssRules.length')
            except Exception as ex:
                css_rules_count = f"Error: {ex}"
                
            header_margin_top = "N/A"
            header_display = "N/A"
            try:
                header_margin_top = window.evaluate_js('window.getComputedStyle(document.querySelector("header")).marginTop')
                header_display = window.evaluate_js('window.getComputedStyle(document.querySelector("header")).display')
            except Exception as ex:
                header_margin_top = f"Error: {ex}"

            # Native Cocoa Diagnostics
            native_width = "N/A"
            native_height = "N/A"
            native_visible = "N/A"
            native_view_class = "N/A"
            try:
                native_window = window.native
                content_view = native_window.contentView()
                frame = content_view.frame()
                native_width = frame.size.width
                native_height = frame.size.height
                native_visible = native_window.isVisible()
                native_view_class = str(content_view.className())
            except Exception as ex:
                native_visible = f"Error: {ex}"

            print(f"----- DIAGNOSTICS -----", flush=True)
            print(f"Body size: {body_width}x{body_height}", flush=True)
            print(f"Body bg: {bg_color}", flush=True)
            print(f"Body text color: {color}", flush=True)
            print(f"Body opacity: {opacity}, display: {display}, visibility: {visibility}", flush=True)
            print(f"HTML bg: {html_bg}", flush=True)
            print(f"Body bg image: {body_bg_img[:100]}...", flush=True)
            print(f"Stylesheets count: {sheets_count}", flush=True)
            print(f"Stylesheets: {sheets_hrefs}", flush=True)
            print(f"style.css rules count: {css_rules_count}", flush=True)
            print(f"Header margin-top: {header_margin_top}, display: {header_display}", flush=True)
            print(f"Native Window visible: {native_visible}", flush=True)
            print(f"Native WebView size: {native_width}x{native_height}", flush=True)
            print(f"Native WebView class: {native_view_class}", flush=True)
            print(f"-----------------------", flush=True)
        except Exception as e:
            print(f"Error evaluating JS on loaded: {e}", flush=True)

    window.events.loaded += on_loaded
    webview.settings['OPEN_DEVTOOLS_IN_DEBUG'] = False
    webview.start(http_server=True, debug=False)

if __name__ == "__main__":
    main()
