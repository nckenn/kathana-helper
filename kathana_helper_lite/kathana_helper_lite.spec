# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

hiddenimports = [
    'queue',
    'threading',
    'win32gui',
    'win32con',
    'win32api',
    'win32process',
    'win32ui',
    'pywintypes',
    'pydirectinput',
    'pyautogui',
    'tkinter',
    'customtkinter',
    'cv2',
    'numpy',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL._tkinter_finder',
]

datas = [
    ('icon.ico', '.'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['easyocr', 'cryptography'],
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
    name='kathana_helper_lite',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon='icon.ico',
)
