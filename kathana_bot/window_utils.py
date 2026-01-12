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
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)
        
        saveDC.BitBlt((0, 0), (width, height), mfcDC, (x, y), win32con.SRCCOPY)
        
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        img = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1)
        
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        
        return img
    except Exception as e:
        print(f"Error capturing window region: {e}")
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


def connect_attacker(window_title=None):
    """Connect to a game window and update global config (legacy compatibility)"""
    import config
    import pywinauto
    
    app = pywinauto.application.Application()
    try:
        if window_title:
            app.connect(title=window_title)
            window = app.window(title=window_title)
            config.selected_window = window_title
        else:
            app.connect(title="0")
            window = app.window(title="0")
            config.selected_window = "0"
        
        config.connected_window = window
        
        if window is not None:
            print(f"✅ Successfully connected to window: {config.selected_window}")
        else:
            config.connected_window = None
            print("Failed to connect to window")
    except Exception as e:
        config.connected_window = None
        print(f"Error connecting to window: {e}")
        return
