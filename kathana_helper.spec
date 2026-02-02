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
    ("debug_utils.py", "."),
    ("input_handler.py", "."),
    ("auto_attack.py", "."),
    ("ocr_utils.py", "."),
    ("auto_repair.py", "."),
    ("auto_unstuck.py", "."),
    ("auto_pots.py", "."),
    ("calibration.py", "."),
    ("bot_logic.py", "."),
    ("settings_manager.py", "."),
    ("buffs_manager.py", "."),
    ("skill_sequence_manager.py", "."),
    ("gui.py", "."),
    ("license_manager.py", "."),
    ("jobs", "jobs"),  # Skill images folder for buffs and skill sequence (all job folders and images)
    ("skill_bar_1.bmp", "."),  # Skill bar template for calibration
    ("skill_bar_2.bmp", "."),  # Skill bar template for calibration
    ("skill_bar_1_vertical.bmp", "."),  # Skill bar template for calibration
    ("skill_bar_2_vertical.bmp", "."),  # Skill bar template for calibration
    ("assist.bmp", "."),
    ("hammer.bmp", "."),
    ("chat_bar_1.png", "."),  # Chat scrollbar template for system message area calibration
    ("chat_bar_2.png", "."),  # Chat anchor template for system message area calibration
    ("easyocr_models", "easyocr_models"),  # Bundled EasyOCR model weights (offline OCR)
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
    name="Kathana Helper v2.1.2",
    debug=False,
    strip=False,
    upx=True,
    console=False,  # Change to True if you want a terminal window
)
