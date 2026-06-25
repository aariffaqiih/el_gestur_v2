import os
import mediapipe

mediapipe_path = os.path.dirname(mediapipe.__file__)

a = Analysis(
    ['desktop.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('frontend', 'frontend'),
        ('core', 'core'),
        ('yolov8n.pt', '.'),
        (os.path.join(mediapipe_path, 'modules'), 'mediapipe/modules')
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='El Presentasi',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='El Presentasi',
)
app = BUNDLE(
    coll,
    name='El Presentasi.app',
    icon=None,
    bundle_identifier='com.elpresentasi.gestur',
    info_plist={
        'NSCameraUsageDescription': 'Aplikasi membutuhkan akses kamera untuk mendeteksi gestur tangan.',
        'NSMicrophoneUsageDescription': 'Aplikasi membutuhkan akses mikrofon untuk perintah suara.',
        'NSRequiresAquaSystemAppearance': 'No'
    }
)
