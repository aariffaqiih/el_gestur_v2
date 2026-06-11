import subprocess
import sys


def open_powerpoint_application():
    """
    Buka Microsoft PowerPoint dan buat presentasi kosong.

    Return:
        tuple[bool, str]: (berhasil, detail_metode_atau_error)
    """
    if sys.platform != "win32":
        return False, "Fitur buka Microsoft PowerPoint otomatis hanya didukung di Windows."

    try:
        import win32com.client

        powerpoint = win32com.client.Dispatch("PowerPoint.Application")
        powerpoint.Visible = True
        powerpoint.Presentations.Add()
        try:
            powerpoint.Activate()
        except Exception:
            pass
        return True, "Microsoft PowerPoint dibuka via COM automation dan presentasi kosong dibuat."
    except Exception as com_error:
        com_error_msg = str(com_error)

    try:
        subprocess.Popen(
            ["cmd", "/c", "start", "", "powerpnt.exe"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
        return True, (
            "Microsoft PowerPoint dibuka via Windows app resolver. "
            "Untuk jaminan presentasi kosong 100%, install pywin32: pip install pywin32. "
            f"COM fallback reason: {com_error_msg}"
        )
    except Exception as start_error:
        return False, (
            "Gagal membuka Microsoft PowerPoint. Pastikan Microsoft PowerPoint terinstal. "
            f"COM error: {com_error_msg}; fallback error: {start_error}"
        )
