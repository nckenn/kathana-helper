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


def initialize_ocr_reader():
    """Lazy initialize EasyOCR reader (only when first needed)"""
    if config.ocr_reader is None:
        print("Initializing EasyOCR (this may take a moment)...")
        try:
            config.ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            print("EasyOCR initialized successfully!")
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
        results = config.ocr_reader.readtext(img_array, detail=1, paragraph=False)
        
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
