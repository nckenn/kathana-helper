"""Send keystrokes to the connected game window."""
import win32api
import win32con
from time import sleep
import pydirectinput
import pyautogui
import config


def initialize_pyautogui():
    pyautogui.FAILSAFE = True


def parse_key_with_modifiers(key_string):
    if '+' not in key_string:
        return [], key_string
    modifiers = []
    base_key = None
    for part in key_string.split('+'):
        part_lower = part.lower().strip()
        if part_lower in ('ctrl', 'control'):
            modifiers.append('Ctrl')
        elif part_lower == 'shift':
            modifiers.append('Shift')
        elif part_lower == 'alt':
            modifiers.append('Alt')
        else:
            base_key = part.strip()
    return modifiers, base_key if base_key else key_string


def get_virtual_key_code(key):
    key_mappings = {
        '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
        '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
        'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
        'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
        'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
    }
    _, base_key = parse_key_with_modifiers(key)
    base_lower = base_key.lower()
    if base_lower in key_mappings:
        return key_mappings[base_lower]
    if len(base_key) == 1:
        return ord(base_key.upper())
    return 0


def send_silent_key(hwnd, vk_code, use_scan_code=False, modifiers=None):
    modifier_codes = {'Ctrl': 0x11, 'Shift': 0x10, 'Alt': 0x12}
    try:
        if modifiers:
            for mod in modifiers:
                if mod in modifier_codes:
                    win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, modifier_codes[mod], 0)
            sleep(0.01)

        if use_scan_code and 0x70 <= vk_code <= 0x7B:
            from ctypes import windll
            scan_code = windll.user32.MapVirtualKeyW(vk_code, 0)
            lparam_down = 1 | scan_code << 16
            lparam_up = 3221225473 | scan_code << 16
            win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk_code, lparam_down)
            sleep(0.08)
            win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk_code, lparam_up)
        else:
            win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, vk_code, 0)
            sleep(0.01)
            win32api.SendMessage(hwnd, win32con.WM_KEYUP, vk_code, 0)

        if modifiers:
            sleep(0.01)
            for mod in reversed(modifiers):
                if mod in modifier_codes:
                    win32api.SendMessage(hwnd, win32con.WM_KEYUP, modifier_codes[mod], 0)
        return True
    except Exception as exc:
        print(f'[input] send_silent_key failed: {exc}')
        return False


def send_input(key):
    try:
        if config.connected_window:
            hwnd = config.connected_window.handle
            modifiers, base_key = parse_key_with_modifiers(key)
            vk_code = get_virtual_key_code(base_key)
            if vk_code:
                use_scan_code = 0x70 <= vk_code <= 0x7B
                if send_silent_key(hwnd, vk_code, use_scan_code=use_scan_code,
                                   modifiers=modifiers or None):
                    return
            config.connected_window.send_keystrokes(key)
        else:
            pydirectinput.press(key)
    except Exception as exc:
        print(f'[input] send_input({key}) failed: {exc}')
