"""
Window utilities for capturing and managing game windows
"""
import ctypes
import win32gui
import win32ui
import win32con
from PIL import Image
from PIL import ImageGrab
import pywinauto

PW_RENDERFULLCONTENT = 0x00000002


def get_window_rect(hwnd):
    """Return (left, top, right, bottom) for the window including borders."""
    return win32gui.GetWindowRect(hwnd)


def capture_has_content(bgr, min_mean=6.0, min_std=4.0):
    """False when capture is empty/black (common with BitBlt on DirectX games)."""
    if bgr is None or bgr.size == 0:
        return False
    import cv2
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return float(gray.mean()) >= min_mean and float(gray.std()) >= min_std


def capture_stats(bgr):
    if bgr is None or bgr.size == 0:
        return {'width': 0, 'height': 0, 'mean': 0.0, 'std': 0.0}
    import cv2
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    return {
        'width': int(w),
        'height': int(h),
        'mean': float(gray.mean()),
        'std': float(gray.std()),
    }


def _bitmap_to_bgr(saveBitMap, width, height):
    import numpy as np
    import cv2
    signed = saveBitMap.GetBitmapBits(True)
    img = np.frombuffer(signed, dtype='uint8')
    img.shape = (height, width, 4)
    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def _capture_bitblt(hwnd, width, height):
    hwndDC = mfcDC = saveDC = saveBitMap = None
    try:
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)
        saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
        return _bitmap_to_bgr(saveBitMap, width, height)
    finally:
        if saveBitMap is not None:
            win32gui.DeleteObject(saveBitMap.GetHandle())
        if saveDC is not None:
            saveDC.DeleteDC()
        if mfcDC is not None:
            mfcDC.DeleteDC()
        if hwndDC is not None:
            win32gui.ReleaseDC(hwnd, hwndDC)


def _capture_print_window(hwnd, width, height):
    hwndDC = mfcDC = saveDC = saveBitMap = None
    try:
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)
        ok = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), PW_RENDERFULLCONTENT)
        if not ok:
            ok = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 0)
        if not ok:
            return None
        return _bitmap_to_bgr(saveBitMap, width, height)
    finally:
        if saveBitMap is not None:
            win32gui.DeleteObject(saveBitMap.GetHandle())
        if saveDC is not None:
            saveDC.DeleteDC()
        if mfcDC is not None:
            mfcDC.DeleteDC()
        if hwndDC is not None:
            win32gui.ReleaseDC(hwnd, hwndDC)


def _capture_screen_grab(hwnd, width, height):
    import cv2
    import numpy as np
    left, top, right, bottom = get_window_rect(hwnd)
    pil = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
    if pil is None:
        return None
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def capture_window_bgr(hwnd):
    """
    Capture the full window image (same coordinate space as legacy Calibrator.capture_window).

    Tries PrintWindow, BitBlt, then screen grab — DirectX games often return black with BitBlt only.
    Returns (bgr, method_name).
    """
    left, top, right, bottom = get_window_rect(hwnd)
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        return None, 'invalid_rect'

    attempts = (
        ('printwindow', _capture_print_window),
        ('bitblt', _capture_bitblt),
        ('screen_grab', _capture_screen_grab),
    )
    best = None
    best_method = 'empty'
    for name, fn in attempts:
        try:
            img = fn(hwnd, width, height)
        except Exception as exc:
            print(f'[Capture] {name} failed: {exc}')
            continue
        if img is None:
            continue
        if capture_has_content(img):
            return img, name
        if best is None or capture_stats(img)['mean'] > capture_stats(best)['mean']:
            best = img
            best_method = name

    if best is not None:
        return best, best_method
    return None, 'failed'


def capture_window_region_bgr(hwnd, x, y, width, height):
    """Capture a window sub-region as BGR (window-image coordinates)."""
    import cv2
    import numpy as np
    if width <= 0 or height <= 0:
        return None
    try:
        full, method = capture_window_bgr(hwnd)
        if full is not None and capture_has_content(full):
            fh, fw = full.shape[:2]
            x2 = min(fw, x + width)
            y2 = min(fh, y + height)
            x1 = max(0, min(x, fw - 1))
            y1 = max(0, min(y, fh - 1))
            if x2 > x1 and y2 > y1:
                return full[y1:y2, x1:x2].copy()
    except Exception:
        pass

    try:
        img = _capture_bitblt_region(hwnd, x, y, width, height)
        if img is not None and capture_has_content(img):
            return img
    except Exception as e:
        print(f'Error capturing window region BGR (bitblt): {e}')

    try:
        left, top, _, _ = get_window_rect(hwnd)
        pil = ImageGrab.grab(
            bbox=(left + x, top + y, left + x + width, top + y + height),
            all_screens=True,
        )
        return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    except Exception as e:
        print(f'Error capturing window region BGR (screen): {e}')
        return None


def _capture_bitblt_region(hwnd, x, y, width, height):
    hwndDC = mfcDC = saveDC = saveBitMap = None
    try:
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)
        saveDC.BitBlt((0, 0), (width, height), mfcDC, (x, y), win32con.SRCCOPY)
        return _bitmap_to_bgr(saveBitMap, width, height)
    finally:
        if saveBitMap is not None:
            win32gui.DeleteObject(saveBitMap.GetHandle())
        if saveDC is not None:
            saveDC.DeleteDC()
        if mfcDC is not None:
            mfcDC.DeleteDC()
        if hwndDC is not None:
            win32gui.ReleaseDC(hwnd, hwndDC)


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
    """Capture a region from a specific window at given coordinates (relative to window rect)."""
    try:
        bgr = capture_window_region_bgr(hwnd, x, y, width, height)
        if bgr is None:
            return None
        rgb = bgr[:, :, ::-1]
        return Image.fromarray(rgb)
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
