"""
Window utilities for capturing and managing game windows
"""
import win32gui
import win32ui
import win32con
from PIL import Image
from PIL import ImageGrab
import pywinauto


def get_open_windows():
    """Get list of open windows with their titles"""
    windows = []
    
    def enum_windows_callback(hwnd, windows_list):
        if win32gui.IsWindowVisible(hwnd):
            window_title = win32gui.GetWindowText(hwnd)
            if window_title.strip():
                windows_list.append((hwnd, window_title))
        return True
    
    win32gui.EnumWindows(enum_windows_callback, windows)
    return windows


def capture_window_pixel(hwnd, x, y):
    """Capture a pixel from a specific window at given coordinates (relative to window's client area)"""
    try:
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, 1, 1)
        saveDC.SelectObject(saveBitMap)
        
        saveDC.BitBlt((0, 0), (1, 1), mfcDC, (x, y), win32con.SRCCOPY)
        
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        
        b = bmpstr[0]
        g = bmpstr[1]
        r = bmpstr[2]
        
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        
        return (r, g, b)
    except Exception as e:
        print(f"Error capturing window pixel: {e}")
        return None


def capture_window_region(hwnd, x, y, width, height):
    """Capture a region from a specific window at given coordinates (relative to window's client area)
    Returns a PIL Image object"""
    try:
        bgr = capture_window_region_bgr(hwnd, x, y, width, height)
        if bgr is None:
            return None
        from PIL import Image
        rgb = bgr[:, :, ::-1]
        return Image.fromarray(rgb)
    except Exception as e:
        print(f"Error capturing window region: {e}")
        return None


def capture_window_region_bgr(hwnd, x, y, width, height):
    """Capture a window sub-region as a BGR numpy array (window-image coordinates)."""
    import numpy as np
    try:
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)
        saveDC.BitBlt((0, 0), (width, height), mfcDC, (x, y), win32con.SRCCOPY)
        signedIntsArray = saveBitMap.GetBitmapBits(True)
        img = np.frombuffer(signedIntsArray, dtype='uint8')
        img.shape = (height, width, 4)
        try:
            import cv2
            result = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        except ImportError:
            result = img[:, :, :3][:, :, ::-1].copy()
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        return result
    except Exception as e:
        print(f"Error capturing window region BGR: {e}")
        return None


def connect_to_window(window_title=None):
    """Connect to a game window using pywinauto"""
    app = pywinauto.application.Application()
    try:
        if window_title:
            app.connect(title=window_title)
            window = app.window(title=window_title)
        else:
            app.connect(title="0")
            window = app.window(title="0")
        
        if window is not None:
            print(f"✅ Successfully connected to window: {window_title or '0'}")
            return window
        else:
            print("Failed to connect to window")
            return None
    except Exception as e:
        print(f"Error connecting to window: {e}")
        return None


def resolve_hwnd():
    """Return the connected game window handle, with title fallback."""
    import config

    if config.connected_window:
        try:
            handle = config.connected_window.handle
            if handle:
                return int(handle)
        except Exception:
            pass
    if config.selected_window:
        hwnd = win32gui.FindWindow(None, config.selected_window)
        if hwnd:
            return int(hwnd)
    return None


def focus_game_window(hwnd):
    """Bring the game window to the foreground before capture (best-effort)."""
    if not hwnd:
        return False
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, 9)  # SW_RESTORE
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


def connect_attacker(window_title=None):
    """Connect to a game window and update global config (legacy compatibility)."""
    import config

    window = connect_to_window(window_title)
    config.selected_window = window_title if window_title else "0"
    config.connected_window = window
    if window is None:
        config.connected_window = None
