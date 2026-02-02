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
import debug_utils

# Movement sequence state tracking
_movement_sequence_active = False
_previous_foreground_hwnd = None


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


def send_silent_key(hwnd, vk_code, use_scan_code=False):
    """Send a key press directly to a window handle without interfering with chat
    Supports scan codes for function keys (F1-F12) for better compatibility"""
    try:
        # Handle function keys with scan codes if requested
        if use_scan_code and vk_code >= 0x70 and vk_code <= 0x7B:  # F1-F12
            try:
                from ctypes import windll
                user32 = windll.user32
                scan_code = user32.MapVirtualKeyW(vk_code, 0)
                lparam_down = 1 | scan_code << 16
                lparam_up = 3221225473 | scan_code << 16
                # Use PostMessage for function keys (asynchronous, better for some games)
                win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk_code, lparam_down)
                sleep(0.08)
                win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk_code, lparam_up)
                return True
            except Exception as e:
                print(f"Error using scan code, falling back to simple method: {e}")
        
        # Standard method for regular keys (use SendMessage for synchronous behavior)
        win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, vk_code, 0)
        sleep(0.01)
        win32api.SendMessage(hwnd, win32con.WM_KEYUP, vk_code, 0)
    except Exception as e:
        print(f"Error sending silent key: {e}")
        return False
    return True


def send_input(key):
    """Send input silently to connected window without interfering with chat
    Supports function keys (F1-F12) with scan codes for better compatibility"""
    try:
        if config.connected_window:
            try:
                hwnd = config.connected_window.handle
                vk_code = get_virtual_key_code(key)
                
                if vk_code:
                    # Use scan codes for function keys (F1-F12)
                    use_scan_code = (vk_code >= 0x70 and vk_code <= 0x7B)
                    if send_silent_key(hwnd, vk_code, use_scan_code=use_scan_code):
                        return
            except Exception as e:
                print(f"Silent input failed, falling back to regular input: {e}")
            
            config.connected_window.send_keystrokes(key)
        else:
            pydirectinput.press(key)
    except Exception as e:
        print(f"Error sending input {key}: {e}")


def start_movement_sequence():
    """Start a movement sequence - sets foreground window once at the start"""
    global _movement_sequence_active, _previous_foreground_hwnd
    try:
        if config.connected_window:
            hwnd = config.connected_window.handle
            # Store the previous foreground window to restore it later
            _previous_foreground_hwnd = win32gui.GetForegroundWindow()
            win32gui.SetForegroundWindow(hwnd)
            sleep(0.05)
            _movement_sequence_active = True
    except Exception as e:
        print(f"Error starting movement sequence: {e}")


def end_movement_sequence():
    """End a movement sequence - restores previous foreground window"""
    global _movement_sequence_active, _previous_foreground_hwnd
    try:
        if _movement_sequence_active and _previous_foreground_hwnd:
            if config.connected_window:
                hwnd = config.connected_window.handle
                # Restore the previous foreground window
                if _previous_foreground_hwnd != hwnd:
                    try:
                        win32gui.SetForegroundWindow(_previous_foreground_hwnd)
                    except:
                        pass  # Ignore errors when restoring foreground window
        _movement_sequence_active = False
        _previous_foreground_hwnd = None
    except Exception as e:
        print(f"Error ending movement sequence: {e}")
        _movement_sequence_active = False
        _previous_foreground_hwnd = None


def send_movement_key(key, hold_duration=0.15):
    """Send movement key with hold duration to actually move the character
    Note: Use start_movement_sequence() and end_movement_sequence() to manage
    foreground window for multiple movement keys"""
    try:
        if config.connected_window and not _movement_sequence_active:
            # Only manage foreground if not in a sequence
            hwnd = config.connected_window.handle
            previous_hwnd = win32gui.GetForegroundWindow()
            win32gui.SetForegroundWindow(hwnd)
            sleep(0.05)
            pydirectinput.keyDown(key)
            sleep(hold_duration)
            pydirectinput.keyUp(key)
            # Restore the previous foreground window
            if previous_hwnd and previous_hwnd != hwnd:
                try:
                    win32gui.SetForegroundWindow(previous_hwnd)
                except:
                    pass  # Ignore errors when restoring foreground window
        else:
            # In a sequence or no connected window - just send the key
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


def perform_mouse_click_at(screen_x, screen_y):
    """Perform a left mouse click at specific screen coordinates"""
    try:
        if not config.connected_window:
            # Fallback to pyautogui if no window connected
            pyautogui.click(screen_x, screen_y)
            return
        
        hwnd = config.connected_window.handle
        rect = win32gui.GetWindowRect(hwnd)
        
        # Convert screen coordinates to window-relative coordinates
        click_x = screen_x - rect[0]
        click_y = screen_y - rect[1]
        
        try:
            # Use SendMessage for synchronous click (more reliable)
            lParam = win32api.MAKELONG(click_x, click_y)
            win32api.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
            sleep(0.05)
            win32api.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
        except:
            # Fallback to pyautogui
            pyautogui.click(screen_x, screen_y)
        
    except Exception as e:
        try:
            # Final fallback to pyautogui
            pyautogui.click(screen_x, screen_y)
        except Exception as e2:
            print(f"Error performing mouse click at ({screen_x}, {screen_y}): {e2}")


def initialize_pyautogui():
    """Initialize PyAutoGUI with failsafe mode"""
    pyautogui.FAILSAFE = True


def window_image_to_client(hwnd, window_x, window_y):
    """
    Convert coordinates from the "captured window image" space (0,0 at top-left of the window rect,
    including title bar + borders because capture_window() uses GetWindowRect/GetWindowDC)
    into client-area coordinates (0,0 at top-left of client area).
    """
    try:
        # Screen position of the client-area origin
        client_origin_screen = win32gui.ClientToScreen(hwnd, (0, 0))
        # Screen position of the window (includes non-client)
        window_left, window_top, window_right, window_bottom = win32gui.GetWindowRect(hwnd)
        offset_x = client_origin_screen[0] - window_left
        offset_y = client_origin_screen[1] - window_top
        
        # Get client area for debugging
        client_rect = win32gui.GetClientRect(hwnd)
        client_width = client_rect[2]
        client_height = client_rect[3]
        window_width = window_right - window_left
        window_height = window_bottom - window_top
        
        debug_utils.debug_print(f"Window rect: ({window_left}, {window_top}) to ({window_right}, {window_bottom}), size: {window_width}x{window_height}", "InputHandler")
        debug_utils.debug_print(f"Client origin (screen): ({client_origin_screen[0]}, {client_origin_screen[1]})", "InputHandler")
        debug_utils.debug_print(f"Client area size: {client_width}x{client_height}", "InputHandler")
        debug_utils.debug_print(f"Offset (border/title): ({offset_x}, {offset_y})", "InputHandler")
        
        client_x = int(window_x - offset_x)
        client_y = int(window_y - offset_y)
        
        return client_x, client_y
    except Exception as e:
        debug_utils.debug_print_error(f"Error in window_image_to_client: {type(e).__name__}: {e}", "InputHandler", e)
        # Fallback: assume no offset (may be wrong if borders/title exist)
        return int(window_x), int(window_y)


def perform_mouse_click_client(hwnd, client_x, client_y):
    """Perform a left mouse click using client-area coordinates via SendMessage."""
    try:
        # Validate window handle
        if not win32gui.IsWindow(hwnd):
            debug_utils.debug_print_error("Invalid window handle", "InputHandler")
            return False
        
        # Check if window is visible (not minimized)
        if not win32gui.IsWindowVisible(hwnd):
            debug_utils.debug_print_warning("Window is not visible (might be minimized)", "InputHandler")
            # Still try to send message, some windows accept messages when minimized
        
        # Get client area dimensions for validation
        try:
            client_rect = win32gui.GetClientRect(hwnd)
            client_width = client_rect[2]
            client_height = client_rect[3]
            
            # Check if coordinates are within bounds
            if client_x < 0 or client_y < 0 or client_x >= client_width or client_y >= client_height:
                debug_utils.debug_print_error(f"Client coordinates out of bounds: ({client_x}, {client_y}) not in [0,0] to [{client_width},{client_height}]", "InputHandler")
                return False
        except Exception as e:
            debug_utils.debug_print_warning(f"Could not validate client bounds: {e}", "InputHandler")
        
        # Perform the click
        lParam = win32api.MAKELONG(int(client_x), int(client_y))
        result_down = win32api.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
        sleep(0.05)
        result_up = win32api.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
        
        # Check if messages were processed (0 usually means success)
        if result_down == 0 and result_up == 0:
            return True
        else:
            debug_utils.debug_print_warning(f"SendMessage returned non-zero: down={result_down}, up={result_up}", "InputHandler")
            return True  # Still return True as non-zero doesn't always mean failure
    except Exception as e:
        debug_utils.debug_print_error("Error in perform_mouse_click_client", "InputHandler", e)
        return False


def perform_mouse_click_window_image(hwnd, window_x, window_y):
    """
    Click a point specified in 'window image' coordinates (same coordinate space as Calibrator.capture_window()).
    Converts to client coords for SendMessage; falls back to pyautogui click with screen coords.
    """
    try:
        # 1) Try client-coord click (background click)
        client_x, client_y = window_image_to_client(hwnd, window_x, window_y)
        debug_utils.debug_print(f"Attempting client-coord click: window_image=({window_x}, {window_y}) -> client=({client_x}, {client_y})", "InputHandler")
        if perform_mouse_click_client(hwnd, client_x, client_y):
            debug_utils.debug_print("SUCCESS: Using client-coord click method (background click)", "InputHandler")
            return True

        # 2) Fallback to real cursor click on screen coords
        # IMPORTANT: Use client-to-screen conversion for accurate screen coordinates
        debug_utils.debug_print("Client-coord click failed, falling back to pyautogui click", "InputHandler")
        try:
            # Convert client coordinates to screen coordinates (more accurate than window rect)
            screen_coords = win32gui.ClientToScreen(hwnd, (client_x, client_y))
            screen_x, screen_y = screen_coords[0], screen_coords[1]
            debug_utils.debug_print(f"Using pyautogui click with client-to-screen conversion: screen=({screen_x}, {screen_y}) from client=({client_x}, {client_y})", "InputHandler")
        except Exception as e:
            # Fallback to window rect method if client-to-screen fails
            debug_utils.debug_print_warning(f"ClientToScreen failed ({e}), using window rect method", "InputHandler")
            window_left, window_top, _, _ = win32gui.GetWindowRect(hwnd)
            screen_x = window_left + int(window_x)
            screen_y = window_top + int(window_y)
            debug_utils.debug_print(f"Using pyautogui click with window rect: screen=({screen_x}, {screen_y})", "InputHandler")
        
        pyautogui.click(screen_x, screen_y)
        debug_utils.debug_print("SUCCESS: Using pyautogui click method (screen coords)", "InputHandler")
        return True
    except Exception as e:
        debug_utils.debug_print_error("Error in perform_mouse_click_window_image", "InputHandler", e)
        return False
