"""
Input handling functions for sending keys and mouse clicks to the game window
"""
import win32api
import win32con
import win32gui
import pydirectinput
from time import sleep
import pyautogui
import config


def get_virtual_key_code(key):
    """Convert key string to virtual key code"""
    key_mappings = {
        '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
        '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
        'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45, 'f': 0x46,
        'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A, 'k': 0x4B, 'l': 0x4C,
        'm': 0x4D, 'n': 0x4E, 'o': 0x4F, 'p': 0x50, 'q': 0x51, 'r': 0x52,
        's': 0x53, 't': 0x54, 'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58,
        'y': 0x59, 'z': 0x5A,
        'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
        'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
        'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
        'space': 0x20, 'enter': 0x0D, 'escape': 0x1B, 'tab': 0x09,
        'shift': 0x10, 'ctrl': 0x11, 'alt': 0x12
    }
    return key_mappings.get(key.lower(), ord(key.upper()) if len(key) == 1 else 0)


def send_silent_key(hwnd, vk_code):
    """Send a key press directly to a window handle without interfering with chat"""
    try:
        win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, vk_code, 0)
        sleep(0.01)
        win32api.SendMessage(hwnd, win32con.WM_KEYUP, vk_code, 0)
    except Exception as e:
        print(f"Error sending silent key: {e}")
        return False
    return True


def send_input(key):
    """Send input silently to connected window without interfering with chat"""
    try:
        if config.connected_window:
            try:
                hwnd = config.connected_window.handle
                vk_code = get_virtual_key_code(key)
                
                if vk_code and send_silent_key(hwnd, vk_code):
                    return
            except Exception as e:
                print(f"Silent input failed, falling back to regular input: {e}")
            
            config.connected_window.send_keystrokes(key)
        else:
            pydirectinput.press(key)
    except Exception as e:
        print(f"Error sending input {key}: {e}")


def send_movement_key(key, hold_duration=0.15):
    """Send movement key with hold duration to actually move the character"""
    try:
        if config.connected_window:
            hwnd = config.connected_window.handle
            win32gui.SetForegroundWindow(hwnd)
            sleep(0.05)
            pydirectinput.keyDown(key)
            sleep(hold_duration)
            pydirectinput.keyUp(key)
        else:
            pydirectinput.keyDown(key)
            sleep(hold_duration)
            pydirectinput.keyUp(key)
    except Exception as e:
        print(f"Error sending movement key {key}: {e}")


def perform_mouse_click():
    """Perform a left mouse click at current cursor position or specific coordinates"""
    try:
        if not config.connected_window:
            return
        
        hwnd = config.connected_window.handle
        
        if config.mouse_clicker_use_cursor:
            cursor_pos = win32gui.GetCursorPos()
            screen_x = cursor_pos[0]
            screen_y = cursor_pos[1]
            
            rect = win32gui.GetWindowRect(hwnd)
            click_x = screen_x - rect[0]
            click_y = screen_y - rect[1]
        else:
            click_x = config.mouse_clicker_coords['x']
            click_y = config.mouse_clicker_coords['y']
            rect = win32gui.GetWindowRect(hwnd)
            screen_x = rect[0] + click_x
            screen_y = rect[1] + click_y
        
        try:
            lParam = win32api.MAKELONG(click_x, click_y)
            win32api.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
            sleep(0.05)
            win32api.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
        except:
            if config.mouse_clicker_use_cursor:
                pyautogui.click()
            else:
                pyautogui.click(screen_x, screen_y)
        
    except Exception as e:
        try:
            if config.mouse_clicker_use_cursor:
                pyautogui.click()
            else:
                rect = win32gui.GetWindowRect(config.connected_window.handle)
                screen_x = rect[0] + config.mouse_clicker_coords['x']
                screen_y = rect[1] + config.mouse_clicker_coords['y']
                pyautogui.click(screen_x, screen_y)
        except Exception as e2:
            print(f"Error performing mouse click: {e2}")


def initialize_pyautogui():
    """Initialize PyAutoGUI with failsafe mode"""
    pyautogui.FAILSAFE = True
