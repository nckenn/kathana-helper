"""Window focus helpers for the bot GUI and game client."""


def bring_window_to_front(hwnd):
    """Bring a Win32 window to the foreground."""
    import win32gui
    import win32con
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False
