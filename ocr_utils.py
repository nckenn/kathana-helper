"""
OCR utilities for reading text from game windows using EasyOCR
"""
import easyocr
import numpy as np
import time
import re
import win32gui
from PIL import ImageGrab
import config
import window_utils
import os

try:
    import cv2
except Exception:
    cv2 = None


def _apply_ssl_cert_workaround():
    """Work around SSL 'unable to get local issuer certificate' on some Windows machines.

    EasyOCR downloads model files the first time it runs. On misconfigured machines, Python's
    certificate store can be broken; pointing SSL_CERT_FILE to certifi's CA bundle often fixes it.
    """
    try:
        # Only set if the user/environment hasn't already configured it.
        if os.environ.get("SSL_CERT_FILE"):
            return
        import certifi  # type: ignore
        os.environ["SSL_CERT_FILE"] = certifi.where()
    except Exception:
        # If certifi isn't present or anything fails, we just leave it alone.
        pass


def _get_easyocr_local_model_dir():
    """Return path to bundled EasyOCR models folder if present, else None."""
    try:
        # Works both in dev and PyInstaller builds.
        return config.resolve_resource_path("easyocr_models")
    except Exception:
        return None


def _build_easyocr_reader_kwargs():
    """Build kwargs for easyocr.Reader with backwards compatibility."""
    kwargs = {"verbose": False}
    model_dir = _get_easyocr_local_model_dir()
    if model_dir:
        # Tell EasyOCR to use bundled models and avoid any network access.
        kwargs["model_storage_directory"] = model_dir
        kwargs["user_network_directory"] = model_dir
        kwargs["download_enabled"] = False
    return kwargs


def _downscale_for_ocr(img_array: np.ndarray) -> np.ndarray:
    """Downscale large images to prevent memory issues during OCR processing."""
    if img_array is None:
        return img_array

    h, w = img_array.shape[:2]
    if h <= 0 or w <= 0:
        return img_array

    # Simple limits: max 2000px on any side, or 3M total pixels
    max_side = 2000
    max_pixels = 3_000_000

    # Check if downscaling is needed
    current_max_side = max(h, w)
    pixels = h * w
    
    if current_max_side <= max_side and pixels <= max_pixels:
        return img_array

    # Calculate scale factor
    scale = 1.0
    if current_max_side > max_side:
        scale = min(scale, max_side / float(current_max_side))
    if pixels > max_pixels:
        scale = min(scale, (max_pixels / float(pixels)) ** 0.5)

    if scale >= 0.999:
        return img_array

    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))

    # Prefer OpenCV for speed if available; otherwise fall back to PIL.
    try:
        if cv2 is not None:
            return cv2.resize(img_array, (new_w, new_h), interpolation=cv2.INTER_AREA)
        from PIL import Image
        pil = Image.fromarray(img_array)
        pil = pil.resize((new_w, new_h), resample=Image.BILINEAR)
        return np.array(pil)
    except Exception:
        return img_array


def check_ocr_availability():
    """Check if OCR is available and working
    
    Returns:
        tuple: (is_available: bool, error_message: str, mode: str, troubleshooting: str)
        - is_available: True if OCR works, False otherwise
        - error_message: Error description if unavailable, None if available
        - mode: 'gpu', 'cpu', or None if unavailable
        - troubleshooting: Specific troubleshooting steps based on error type
    """
    try:
        # Only needed if EasyOCR must download models (i.e., not bundled).
        if not _get_easyocr_local_model_dir():
            _apply_ssl_cert_workaround()
        # Try GPU first if enabled
        if config.ocr_use_gpu:
            try:
                reader_kwargs = _build_easyocr_reader_kwargs()
                try:
                    test_reader = easyocr.Reader(['en'], gpu=True, **reader_kwargs)
                except TypeError:
                    # Older EasyOCR versions may not support some kwargs.
                    test_reader = easyocr.Reader(['en'], gpu=True, verbose=False)
                # Test with a simple image (white rectangle)
                test_image = np.ones((50, 200, 3), dtype=np.uint8) * 255
                test_reader.readtext(test_image, detail=0)
                del test_reader  # Clean up test reader
                return True, None, 'gpu', None
            except Exception as gpu_error:
                error_msg = str(gpu_error).lower()
                troubleshooting = _get_troubleshooting_steps(error_msg, 'gpu')
                # Fall through to CPU test
        
        # Try CPU
        try:
            reader_kwargs = _build_easyocr_reader_kwargs()
            try:
                test_reader = easyocr.Reader(['en'], gpu=False, **reader_kwargs)
            except TypeError:
                test_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            # Test with a simple image (white rectangle)
            test_image = np.ones((50, 200, 3), dtype=np.uint8) * 255
            test_reader.readtext(test_image, detail=0)
            del test_reader  # Clean up test reader
            return True, None, 'cpu', None
        except Exception as cpu_error:
            error_msg = str(cpu_error).lower()
            troubleshooting = _get_troubleshooting_steps(error_msg, 'cpu')
            return False, str(cpu_error), None, troubleshooting
            
    except ImportError as e:
        troubleshooting = (
            "EasyOCR is not installed.\n\n"
            "Installation steps:\n"
            "1. Open Command Prompt or PowerShell\n"
            "2. Run: pip install easyocr\n"
            "3. If that fails, install PyTorch first:\n"
            "   • CPU version: pip install torch torchvision torchaudio\n"
            "   • GPU version (NVIDIA): pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118\n"
            "4. Then run: pip install easyocr\n"
            "5. Restart this application"
        )
        return False, f"EasyOCR not installed: {e}", None, troubleshooting
    except Exception as e:
        error_msg = str(e).lower()
        troubleshooting = _get_troubleshooting_steps(error_msg, 'unknown')
        return False, str(e), None, troubleshooting


def _get_troubleshooting_steps(error_msg, mode):
    """Get specific troubleshooting steps based on error message"""
    error_lower = error_msg.lower()
    
    if 'cuda' in error_lower or 'gpu' in error_lower or 'nvidia' in error_lower:
        return (
            f"GPU/CUDA error detected ({mode} mode).\n\n"
            "Solutions:\n"
            "1. If you don't have NVIDIA GPU, set ocr_use_gpu = False in config.py\n"
            "2. If you have NVIDIA GPU:\n"
            "   • Install CUDA toolkit: https://developer.nvidia.com/cuda-downloads\n"
            "   • Install PyTorch with CUDA: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118\n"
            "   • Verify: python -c \"import torch; print(torch.cuda.is_available())\"\n"
            "3. Try CPU mode by setting ocr_use_gpu = False in config.py"
        )
    elif ('ssl' in error_lower and 'certificate' in error_lower) or 'unable to get local issuer certificate' in error_lower:
        return (
            "SSL certificate error detected while downloading OCR model files.\n\n"
            "This is not a RAM issue; EasyOCR can't download its models due to broken/missing root certificates.\n\n"
            "Solutions:\n"
            "1. Update certs (recommended): pip install --upgrade certifi\n"
            "2. If you're behind a proxy/antivirus doing HTTPS inspection, disable it or add a bypass for Python/GitHub\n"
            "3. Ensure system date/time is correct\n"
            "4. Restart the app after fixing\n"
        )
    elif 'torch' in error_lower or 'pytorch' in error_lower:
        return (
            "PyTorch error detected.\n\n"
            "Solutions:\n"
            "1. Install PyTorch:\n"
            "   • CPU: pip install torch torchvision torchaudio\n"
            "   • GPU (NVIDIA): pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118\n"
            "2. Verify installation: python -c \"import torch; print(torch.__version__)\"\n"
            "3. Restart this application"
        )
    elif 'no module named' in error_lower or 'cannot import' in error_lower:
        return (
            "Missing Python module.\n\n"
            "Solutions:\n"
            "1. Install EasyOCR: pip install easyocr\n"
            "2. Install dependencies: pip install torch torchvision torchaudio opencv-python pillow\n"
            "3. Restart this application"
        )
    elif 'memory' in error_lower or 'out of memory' in error_lower:
        return (
            "Memory error detected.\n\n"
            "Solutions:\n"
            "1. Close other applications to free up memory\n"
            "2. Try CPU mode (slower but uses less memory): Set ocr_use_gpu = False in config.py\n"
            "3. Restart this application"
        )
    else:
        return (
            "General OCR error.\n\n"
            "Solutions:\n"
            "1. Reinstall EasyOCR: pip uninstall easyocr && pip install easyocr\n"
            "2. Install/update PyTorch: pip install --upgrade torch torchvision torchaudio\n"
            "3. Try CPU mode: Set ocr_use_gpu = False in config.py\n"
            "4. Check console for detailed error message\n"
            "5. Restart this application"
        )


def recheck_ocr_availability():
    """Re-check OCR availability (useful after user fixes installation issues)
    
    This will update config.ocr_available and config.ocr_mode.
    Returns tuple: (is_available: bool, error_message: str, mode: str, troubleshooting: str)
    """
    print("Re-checking OCR availability...")
    is_available, error_msg, mode, troubleshooting = check_ocr_availability()
    
    # Update config
    config.ocr_available = is_available
    config.ocr_mode = mode
    
    # Reset reader if availability changed
    if not is_available and config.ocr_reader is not None:
        config.ocr_reader = None
        print("OCR reader cleared due to unavailability")
    
    if is_available:
        print(f"OCR is now available in {mode.upper()} mode!")
    else:
        print(f"OCR is still not available: {error_msg}")
    
    return is_available, error_msg, mode, troubleshooting


def initialize_ocr_reader():
    """Lazy initialize EasyOCR reader (only when first needed)
    
    Tries GPU first if enabled, falls back to CPU if GPU is unavailable.
    Returns False if OCR is not available (checked on startup).
    """
    # Check if OCR was determined to be unavailable on startup
    if not config.ocr_available:
        print("OCR is not available on this system (checked on startup)")
        return False

    # Only needed if EasyOCR must download models (i.e., not bundled).
    if not _get_easyocr_local_model_dir():
        _apply_ssl_cert_workaround()
    
    if config.ocr_reader is None:
        print("Initializing EasyOCR (this may take a moment)...")
        
        # Try GPU first if enabled
        if config.ocr_use_gpu:
            try:
                reader_kwargs = _build_easyocr_reader_kwargs()
                try:
                    config.ocr_reader = easyocr.Reader(['en'], gpu=True, **reader_kwargs)
                except TypeError:
                    config.ocr_reader = easyocr.Reader(['en'], gpu=True, verbose=False)
                print("EasyOCR initialized successfully with GPU acceleration!")
                return True
            except Exception as e:
                print(f"GPU initialization failed: {e}")
                print("Falling back to CPU mode...")
                # Fall through to CPU initialization
        
        # Use CPU (either because GPU is disabled or GPU failed)
        try:
            reader_kwargs = _build_easyocr_reader_kwargs()
            try:
                config.ocr_reader = easyocr.Reader(['en'], gpu=False, **reader_kwargs)
            except TypeError:
                config.ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            print("EasyOCR initialized successfully with CPU mode!")
        except Exception as e:
            print(f"Error initializing EasyOCR: {e}")
            return False
    return True


def read_system_message_ocr(debug_prefix="[System Message]"):
    """Generic OCR reader for system messages area
    
    Returns a dictionary with parsed text in multiple formats for easy parsing.
    
    Args:
        debug_prefix: Optional prefix for debug messages (default: "[System Message]")
    
    Returns:
        dict with keys: 'lines', 'full', 'space'
        None if area not calibrated or error occurred
    """
    if not config.connected_window:
        return None
    
    if not initialize_ocr_reader():
        return None
    
    try:
        hwnd = config.connected_window.handle
        
        x = config.system_message_area['x']
        y = config.system_message_area['y']
        width = config.system_message_area['width']
        height = config.system_message_area['height']
        
        if width <= 0 or height <= 0:
            return None
        
        center_x = x
        center_y = y
        half_width = width // 2
        half_height = height // 2
        
        left = center_x - half_width
        top = center_y - half_height
        
        img = window_utils.capture_window_region(hwnd, left, top, width, height)
        
        if img is None:
            try:
                right = center_x + half_width
                bottom = center_y + half_height
                rect = win32gui.GetWindowRect(hwnd)
                screen_left = rect[0] + left
                screen_top = rect[1] + top
                screen_right = rect[0] + right
                screen_bottom = rect[1] + bottom
                img = ImageGrab.grab(bbox=(screen_left, screen_top, screen_right, screen_bottom))
            except:
                return None
        
        img_array = np.array(img)
        img_array = _downscale_for_ocr(img_array)
        results = config.ocr_reader.readtext(
            img_array,
            detail=1,
            paragraph=False,
            batch_size=1,
        )
        
        if results and len(results) > 0:
            text_lines = []
            for result in results:
                if len(result) >= 2:
                    text = result[1].strip()
                    if text:
                        text_lines.append(text)
            
            if text_lines:
                full_text = '\n'.join(text_lines)
                space_separated = ' '.join(text_lines)
                
                current_time = time.time()
                if not hasattr(read_system_message_ocr, 'last_debug_time'):
                    read_system_message_ocr.last_debug_time = {}
                if debug_prefix not in read_system_message_ocr.last_debug_time:
                    read_system_message_ocr.last_debug_time[debug_prefix] = 0
                if current_time - read_system_message_ocr.last_debug_time[debug_prefix] > 5.0:
                    print(f"{debug_prefix} OCR read ({len(text_lines)} lines):")
                    for i, line in enumerate(text_lines):
                        print(f"  [{i}] {line}")
                    read_system_message_ocr.last_debug_time[debug_prefix] = current_time
                
                return {'lines': text_lines, 'full': full_text, 'space': space_separated}
        
        return None
            
    except Exception as e:
        current_time = time.time()
        if not hasattr(read_system_message_ocr, 'last_error_time'):
            read_system_message_ocr.last_error_time = {}
        if debug_prefix not in read_system_message_ocr.last_error_time:
            read_system_message_ocr.last_error_time[debug_prefix] = 0
        if current_time - read_system_message_ocr.last_error_time[debug_prefix] > 10.0:
            print(f"{debug_prefix} Error reading system message: {e}")
            read_system_message_ocr.last_error_time[debug_prefix] = current_time
        return None


def filter_messages_by_keywords(ocr_result, keywords, case_sensitive=False):
    """Filter OCR result lines by keywords"""
    if not ocr_result:
        return []
    
    if isinstance(ocr_result, dict):
        lines = ocr_result.get('lines', [])
    elif isinstance(ocr_result, list):
        lines = ocr_result
    else:
        return []
    
    if not keywords:
        return lines
    
    filtered = []
    for line in lines:
        line_lower = line if case_sensitive else line.lower()
        if all(keyword if case_sensitive else keyword.lower() in line_lower for keyword in keywords):
            filtered.append(line)
    
    return filtered


def check_item_break_warning(ocr_result):
    """Check for 'is about to break' keyword in system message OCR result
    
    Returns True if the keyword is found, False otherwise.
    Example message: "Datu Madanti is about to break"
    """
    if not ocr_result:
        return False
    
    # Filter lines containing "about" and "break" keywords
    break_lines = filter_messages_by_keywords(ocr_result, ['about', 'break'], case_sensitive=False)
    
    if isinstance(ocr_result, dict):
        lines = break_lines if break_lines else ocr_result.get('lines', [])
        full_text = ocr_result.get('full', '')
        space_text = ocr_result.get('space', '')
    else:
        lines = [ocr_result] if ocr_result else []
        full_text = ocr_result
        space_text = ocr_result
    
    try:
        # Check lines for "is about to break" pattern
        # More flexible pattern to handle OCR variations (e.g., "isabout", "aboutto", etc.)
        # Pattern: must contain "is", "about", "to", and "break" in that order (allowing some flexibility)
        pattern = r'is.*?about.*?to.*?break'
        
        if break_lines:
            for line in reversed(break_lines):
                # Case-insensitive match with flexible spacing
                if re.search(pattern, line, re.IGNORECASE):
                    current_time = time.time()
                    if not hasattr(check_item_break_warning, 'last_debug_time'):
                        check_item_break_warning.last_debug_time = 0
                    if current_time - check_item_break_warning.last_debug_time > 2.0:
                        print(f"[Auto Repair] Item break warning detected: {line[:80]}")
                        check_item_break_warning.last_debug_time = current_time
                    return True
        
        # Fallback: check full text (all lines combined)
        text_to_parse = space_text if space_text else full_text
        if text_to_parse:
            if re.search(pattern, text_to_parse, re.IGNORECASE):
                current_time = time.time()
                if not hasattr(check_item_break_warning, 'last_debug_time'):
                    check_item_break_warning.last_debug_time = 0
                if current_time - check_item_break_warning.last_debug_time > 2.0:
                    print(f"[Auto Repair] Item break warning detected (fallback): {text_to_parse[:80]}")
                    check_item_break_warning.last_debug_time = current_time
                return True
        
        # Additional fallback: Check if we have all keywords even if pattern doesn't match exactly
        # This handles cases where OCR might split words incorrectly
        if break_lines:
            for line in reversed(break_lines):
                line_lower = line.lower()
                # Check if all required words are present (in any order but should be close)
                has_is = 'is' in line_lower
                has_about = 'about' in line_lower
                has_to = 'to' in line_lower
                has_break = 'break' in line_lower
                
                if has_is and has_about and has_to and has_break:
                    # Try to find positions to verify order
                    pos_is = line_lower.find('is')
                    pos_about = line_lower.find('about')
                    pos_to = line_lower.find(' to ')  # Space before/after 'to' to avoid matching 'to' in words
                    if pos_to == -1:
                        pos_to = line_lower.find('to', pos_about)
                    pos_break = line_lower.find('break')
                    
                    # Check if they appear in roughly the right order (allow some flexibility)
                    if (pos_is < pos_break and pos_about < pos_break and 
                        (pos_to == -1 or (pos_about < pos_to < pos_break))):
                        current_time = time.time()
                        if not hasattr(check_item_break_warning, 'last_debug_time'):
                            check_item_break_warning.last_debug_time = 0
                        if current_time - check_item_break_warning.last_debug_time > 2.0:
                            print(f"[Auto Repair] Item break warning detected (flexible match): {line[:80]}")
                            check_item_break_warning.last_debug_time = current_time
                        return True
                
    except Exception as e:
        current_time = time.time()
        if not hasattr(check_item_break_warning, 'last_error_time'):
            check_item_break_warning.last_error_time = 0
        if current_time - check_item_break_warning.last_error_time > 10.0:
            error_text = str(ocr_result)[:100] if not isinstance(ocr_result, dict) else str(ocr_result.get('full', ''))[:100]
            print(f"[Auto Repair] Error checking break warning: {e}, text: {error_text}")
            check_item_break_warning.last_error_time = current_time
    
    return False


def parse_damage_from_message(ocr_result):
    """Parse damage value from system message OCR result"""
    if not ocr_result:
        return None
    
    damage_lines = filter_messages_by_keywords(ocr_result, ['you', 'damaged'], case_sensitive=False)
    damage_lines = [line for line in damage_lines 
                    if re.search(r'you\s+damaged', line, re.IGNORECASE) is not None]
    
    if isinstance(ocr_result, dict):
        lines = damage_lines if damage_lines else ocr_result.get('lines', [])
        full_text = ocr_result.get('full', '')
        space_text = ocr_result.get('space', '')
    else:
        lines = [ocr_result] if ocr_result else []
        full_text = ocr_result
        space_text = ocr_result
    
    try:
        if damage_lines:
            for line in reversed(damage_lines):
                patterns = [
                    r'you\s+damaged\s+.*?\s+by\s+([\d,]+)',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        damage_str = match.group(1).replace(',', '').strip()
                        if damage_str:
                            damage = int(damage_str)
                            current_time = time.time()
                            if not hasattr(parse_damage_from_message, 'last_debug_time'):
                                parse_damage_from_message.last_debug_time = 0
                            if current_time - parse_damage_from_message.last_debug_time > 2.0:
                                print(f"[Auto Repair] Parsed damage: {damage} from line: {line[:80]}")
                                parse_damage_from_message.last_debug_time = current_time
                            return damage
        
        text_to_parse = space_text if space_text else full_text
        if text_to_parse:
            pattern = r'you\s+damaged\s+.*?\s+by\s+([\d,]+)'
            matches = re.findall(pattern, text_to_parse, re.IGNORECASE)
            if matches:
                damage_str = matches[-1].replace(',', '').strip()
                if damage_str:
                    damage = int(damage_str)
                    current_time = time.time()
                    if not hasattr(parse_damage_from_message, 'last_debug_time'):
                        parse_damage_from_message.last_debug_time = 0
                    if current_time - parse_damage_from_message.last_debug_time > 2.0:
                        print(f"[Auto Repair] Parsed damage (fallback): {damage} from text")
                        parse_damage_from_message.last_debug_time = current_time
                    return damage
                
    except Exception as e:
        current_time = time.time()
        if not hasattr(parse_damage_from_message, 'last_error_time'):
            parse_damage_from_message.last_error_time = 0
        if current_time - parse_damage_from_message.last_error_time > 10.0:
            error_text = str(ocr_result)[:100] if not isinstance(ocr_result, dict) else str(ocr_result.get('full', ''))[:100]
            print(f"[Auto Repair] Error parsing damage: {e}, text: {error_text}")
            parse_damage_from_message.last_error_time = current_time
    
    return None
