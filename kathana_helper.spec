# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

hiddenimports = [
    # Python stdlib (often missed)
    "queue",
    "threading",
    "multiprocessing",
    "asyncio",
    "concurrent.futures",

    # Windows / pywin32
    "win32gui",
    "win32con",
    "win32api",
    "win32process",
    "win32ui",
    "pywintypes",

    # Input automation
    "pydirectinput",
    "pyautogui",
    "pywinauto",

    # GUI
    "tkinter",
    "customtkinter",

    # OCR / Imaging stack
    "easyocr",
    "easyocr.reader",
    "easyocr.utils",
    "easyocr.model",
    "easyocr.character",
    "easyocr.detection",
    "easyocr.recognition",
    "cv2",
    "numpy",
    "PIL",
]

datas = [
    ("config.py", "."),
    ("window_utils.py", "."),
    ("input_handler.py", "."),
    ("auto_attack.py", "."),
    ("ocr_utils.py", "."),
    ("auto_repair.py", "."),
    ("auto_unstuck.py", "."),
    ("auto_pots.py", "."),
    ("calibration.py", "."),
    ("bot_logic.py", "."),
    ("settings_manager.py", "."),
    ("gui.py", "."),
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Kathana Helper v2.0.1",
    debug=False,
    strip=False,
    upx=True,
    console=False,  # Change to True if you want a terminal window
)
