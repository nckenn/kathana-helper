# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

hiddenimports = [
    # Python stdlib (often missed)
    "queue",
    "threading",
    "multiprocessing",
    "asyncio",
    "concurrent.futures",
    "uuid",

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

    # Imaging stack
    "cv2",
    "numpy",
    "PIL",

    # License validation
    "cryptography",
    "cryptography.hazmat.primitives",
    "cryptography.hazmat.primitives.asymmetric",
    "cryptography.hazmat.primitives.asymmetric.padding",
    "cryptography.hazmat.primitives.hashes",
    "cryptography.hazmat.primitives.serialization",
    "cryptography.hazmat.backends",
    "cryptography.hazmat.backends.openssl",

    # Dynamically imported at runtime (must be explicit for onefile builds)
    "loot_helpers",
    "hp_number_reader",
]

datas = [
    ("config.py", "."),
    ("window_utils.py", "."),
    ("debug_utils.py", "."),
    ("debug_io.py", "."),
    ("frame_cache.py", "."),
    ("capture_regions.py", "."),
    ("input_handler.py", "."),
    ("auto_attack.py", "."),
    ("auto_repair.py", "."),
    ("auto_unstuck.py", "."),
    ("auto_pots.py", "."),
    ("calibration.py", "."),
    ("bot_logic.py", "."),
    ("settings_manager.py", "."),
    ("logger.py", "."),
    ("loot_helpers.py", "."),
    ("state.py", "."),
    ("template_cache.py", "."),
    ("skill_bar_actions.py", "."),
    ("mob_filter.py", "."),
    ("mob_template_store.py", "."),
    ("hp_number_reader.py", "."),
    ("region_picker.py", "."),
    ("buffs_manager.py", "."),
    ("skill_sequence_manager.py", "."),
    ("gui.py", "."),
    ("ui", "ui"),
    ("license_manager.py", "."),
    ("icon.ico", "."),  # Application icon
    ("jobs", "jobs"),  # Skill images folder for buffs and skill sequence (all job folders and images)
    ("skill_bar_1.bmp", "."),  # Skill bar template for calibration
    ("skill_bar_2.bmp", "."),  # Skill bar template for calibration
    ("skill_bar_1_vertical.bmp", "."),  # Skill bar template for calibration
    ("skill_bar_2_vertical.bmp", "."),  # Skill bar template for calibration
    ("assist.bmp", "."),
    ("hammer.bmp", "."),
    ("chat_bar_1.png", "."),  # Chat scrollbar template for system message area calibration
    ("chat_bar_2.png", "."),  # Chat anchor template for system message area calibration
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
    name="Kathana Helper v3.0.0",
    debug=False,
    strip=False,
    upx=True,
    console=False,  # Change to True if you want a terminal window
    icon="icon.ico",  # Application icon (embedded in executable for desktop shortcuts)
)
