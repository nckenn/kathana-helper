"""Window listing and screen capture."""
import win32gui
import win32ui
import win32con
import pywinauto
import numpy as np
import config


def get_open_windows():
    windows = []

    def callback(hwnd, result):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title.strip():
                result.append((hwnd, title))
        return True

    win32gui.EnumWindows(callback, windows)
    return windows


def capture_window_region_bgr(hwnd, x, y, width, height):
    try:
        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(bitmap)
        save_dc.BitBlt((0, 0), (width, height), mfc_dc, (x, y), win32con.SRCCOPY)
        bits = bitmap.GetBitmapBits(True)
        img = np.frombuffer(bits, dtype='uint8')
        img.shape = (height, width, 4)
        try:
            import cv2
            result = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        except ImportError:
            result = img[:, :, :3][:, :, ::-1].copy()
        win32gui.DeleteObject(bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)
        return result
    except Exception as exc:
        print(f'[window_utils] capture error: {exc}')
        return None


def connect_to_window(window_title):
    app = pywinauto.application.Application()
    try:
        app.connect(title=window_title)
        window = app.window(title=window_title)
        if window is not None:
            print(f'Connected to: {window_title}')
            return window
    except Exception as exc:
        print(f'[window_utils] connect error: {exc}')
    return None


def resolve_hwnd():
    """Return the connected game window handle, with title fallback."""
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
