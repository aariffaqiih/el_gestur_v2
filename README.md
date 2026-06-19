# El Presentasi (el_gestur_v2)

El Presentasi adalah sistem cerdas berbasis *Computer Vision* dan *Voice Recognition* yang memungkinkan pengguna untuk mengontrol perangkat lunak presentasi dan mengelola dokumen menggunakan gestur tangan dan perintah suara. Sistem ini dibangun menggunakan Python dan Flask sebagai server backend, dengan integrasi MediaPipe dan YOLOv8 untuk pemrosesan gambar dan pengenalan gestur secara *real-time*.

## 🚀 Fitur Utama

- **Kontrol Gestur Hands-free**: Mengontrol navigasi slide (Next/Prev), mengaktifkan pointer laser, dan memulai/mengakhiri presentasi hanya dengan gestur tangan.
- **Dukungan Multi-Software**: Mendukung berbagai aplikasi presentasi populer seperti Microsoft PowerPoint, Canva, Figma, dan Notion.
- **Voice Typer**: Integrasi pengenalan suara (Speech-to-Text) untuk mengetik secara otomatis, membantu saat presenter ingin membuat catatan atau mengedit dokumen tanpa menyentuh keyboard.
- **Pencarian & Manajemen Dokumen Cerdas**: Mampu mencari, mengindeks, dan memproses dokumen (Word, Excel, PowerPoint, PDF, dll.) di dalam komputer.
- **Presenter Tracking (Object Locker)**: Menggunakan YOLO untuk mendeteksi presenter utama agar sistem hanya merespons gestur dari presenter yang "dikunci" (locked), mencegah gangguan dari orang lain di latar belakang.

## 🛠️ Teknologi yang Digunakan

- **Python**: Bahasa pemrograman utama.
- **Flask**: Framework web ringan untuk menjalankan server backend dan menyediakan REST API serta Video Feed.
- **MediaPipe**: Framework dari Google untuk pelacakan *landmark* tangan (Hand Tracking) yang sangat cepat dan akurat.
- **YOLOv8**: Model deteksi objek mutakhir untuk mendeteksi wajah/tubuh presenter.
- **PyAutoGUI**: Digunakan untuk mengonversi sinyal gestur menjadi input keyboard dan mouse (simulasi penekanan tombol).
- **OpenCV**: Digunakan untuk menangkap dan memproses *frame* dari kamera (*webcam*).

## 🗂️ Struktur Proyek

- `server.py`: Skrip utama yang menjalankan server Flask, menangani rute API, dan memproses *loop* kamera.
- `gestur_engine.py`: Mesin logika untuk mendeteksi dan menerjemahkan *landmark* tangan dari MediaPipe menjadi aksi spesifik (seperti *swipe*, *fist*, pose *shaka*, *peace*, *prayer*, dll.).
- `voice_typer.py`: Modul untuk menangani input suara dan mengubahnya menjadi teks/perintah.
- `object_lock.py`: Mengatur *tracking* presenter utama menggunakan YOLOv8.
- `config.py`: File konfigurasi yang menyimpan seluruh parameter penting (seperti resolusi kamera, FPS, *threshold* gestur, jalur pencarian dokumen, dll.).
- `document_api.py`, `document_commands.py`, `document_finder.py`: Modul untuk mencari, mengindeks, dan berinteraksi dengan file dokumen.
- `frontend/`: Direktori yang berisi antarmuka pengguna berbasis web (UI).

## 🖐️ Daftar Gestur yang Didukung

Mesin gestur mendeteksi berbagai pose untuk memicu perintah spesifik. Beberapa pose yang diimplementasikan meliputi:
1. **Swipe Kanan/Kiri**: Untuk navigasi *slide* berikutnya/sebelumnya.
2. **Pose OK / Shaka / Peace**: Mengaktifkan/menonaktifkan laser, atau membuka aplikasi tertentu.
3. **Pose Doa (Prayer)**: Untuk keluar (Quit) dari mode presentasi atau menutup aplikasi.
4. **Kepalan Tangan (Fist)**: Digunakan untuk memulai atau sebagai pemicu *intent* tertentu.

*(Catatan: Mapping gestur dapat dilihat dan disesuaikan pada file `server.py` di bagian fungsi `handle_gesture`)*

## ⚙️ Instalasi dan Persiapan

1. **Clone repositori ini**:
   ```bash
   git clone <url-repo>
   cd el_gestur_v2
   ```

2. **Buat dan aktifkan Virtual Environment (opsional namun disarankan)**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Untuk Linux/Mac
   # atau venv\Scripts\activate untuk Windows
   ```

3. **Instal dependensi**:
   Pastikan Anda telah menginstal seluruh pustaka yang dibutuhkan (OpenCV, Flask, PyAutoGUI, MediaPipe, Ultralytics YOLO, dll.).
   ```bash
   pip install -r requirements.txt
   ```
   *(Jika file requirements.txt belum ada, Anda bisa menginstal manual seperti `pip install flask opencv-python mediapipe pyautogui ultralytics flask-cors`)*

4. **Jalankan Server**:
   ```bash
   python server.py
   ```
   Server akan berjalan di `http://0.0.0.0:5005/`. Anda bisa mengakses Video Feed melalui `http://localhost:5005/video_feed`.

## 🌐 Endpoint API

Sistem ini mengekspos beberapa Endpoint API untuk dikendalikan melalui UI Frontend:
- `POST /set_software`: Mengatur software target (ppt, canva, figma, notion).
- `POST /start` & `POST /stop`: Menyalakan dan mematikan deteksi gestur.
- `POST /voice_start` & `POST /voice_stop`: Mengontrol fitur *Voice Typer*.
- `GET /status`: Mengambil status terkini dari sistem, termasuk apakah *engine* aktif, software yang dipilih, dan status dokumen.

## 📝 Catatan Laporan Proyek

Jika Anda menggunakan file README ini untuk keperluan penyusunan Laporan Proyek, Anda dapat mengembangkan bagian-bagian di atas sesuai dengan struktur laporan akademik/formal, seperti:
- **Bab Pendahuluan**: Mengambil inspirasi dari deskripsi proyek di bagian atas.
- **Bab Metodologi**: Menjelaskan alur dari `server.py` -> `object_lock.py` -> `gestur_engine.py` (Kamera menangkap frame -> YOLO mendeteksi orang -> MediaPipe mendeteksi tangan -> PyAutoGUI menekan tombol).
- **Bab Implementasi & Pengujian**: Menjelaskan fungsionalitas dari setiap Endpoint API dan menguji tingkat keberhasilan pembacaan gestur.

---
*Dibuat untuk mempermudah pengalaman presentasi secara interaktif dan modern.*
