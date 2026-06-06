# ============================================================
# MANDOR AI — APP LAUNCHER UTILITIES
# ============================================================

import os
import subprocess
import sys
import time


def open_word_blank_document():
    """
    Buka Microsoft Word dan buat blank document.

    Urutan dibuat sengaja:
    1. COM automation via pywin32: paling stabil di Windows + memastikan Documents.Add().
    2. Fallback ke App Paths/Start Menu resolver Windows: membuka Word tanpa bergantung
       pada urutan tombol keyboard atau posisi fokus UI.

    Return:
        tuple[bool, str]: (berhasil, detail_metode_atau_error)
    """
    if sys.platform != "win32":
        return False, "Fitur buka Microsoft Word otomatis hanya didukung di Windows."

    # Metode terbaik: COM automation. Butuh: pip install pywin32
    try:
        import win32com.client  # type: ignore

        word = win32com.client.Dispatch("Word.Application")
        word.Visible = True
        word.Documents.Add()
        try:
            word.Activate()
        except Exception:
            pass
        return True, "Microsoft Word dibuka via COM automation dan blank document dibuat."
    except Exception as com_error:
        com_error_msg = str(com_error)

    # Fallback tanpa pywin32. Tidak memakai urutan tombol Windows + W + O + R + D.
    # Windows akan mencari winword.exe melalui App Paths/Start Menu registration.
    try:
        subprocess.Popen(
            ['cmd', '/c', 'start', '', 'winword.exe'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
        return True, (
            "Microsoft Word dibuka via Windows app resolver. "
            "Untuk jaminan blank document 100%, install pywin32: pip install pywin32. "
            f"COM fallback reason: {com_error_msg}"
        )
    except Exception as start_error:
        return False, (
            "Gagal membuka Microsoft Word. Pastikan Microsoft Word terinstal. "
            f"COM error: {com_error_msg}; fallback error: {start_error}"
        )
