# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

hiddenimports = [
    "queue",
    "threading",

    # Windows / pywin32
    "win32api",
    "win32con",
    "win32gui",
    "win32ui",

    # Input automation
    "pydirectinput",
    "pyautogui",
    "pywinauto",

    # GUI
    "tkinter",
    "customtkinter",

    # OCR
    "easyocr",
]

datas = [
    ("config.py", "."),
    ("window_utils.py", "."),
    ("input_handler.py", "."),
    ("bar_detection.py", "."),
    ("ocr_utils.py", "."),
    ("mob_detection.py", "."),
    ("auto_repair.py", "."),
    ("auto_unstuck.py", "."),
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
    name="Kathana Helper v2.0.0",
    debug=False,
    strip=False,
    upx=True,
    console=False,  # Change to True if you want a terminal window
)
