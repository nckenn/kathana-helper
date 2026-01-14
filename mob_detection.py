"""
Mob detection and filtering using OCR
Includes calibration-based enemy name extraction
"""
import threading
import numpy as np
import time
import win32gui
import os
import re
import difflib
import cv2
from PIL import ImageGrab
import config
import window_utils
import ocr_utils


# Initialize lock for thread-safe mob detection
if config.mob_detection_lock is None:
    config.mob_detection_lock = threading.Lock()


def normalize_text(text):
    """Convert to lowercase, remove special characters but preserve spaces"""
    if not text:
        return ''
    return re.sub('[^a-zA-Z\\s]', '', text.lower())


def contains_complete_word(target, detected):
    """Returns True if target matches EXACTLY with detected (same words, same order)"""
    target = target.lower().strip()
    detected = detected.lower().strip()
    detected_clean = re.sub('[^a-zA-Z0-9\\s]', '', detected)
    target_words = target.split()
    detected_words = detected_clean.split()
    if len(target_words) != len(detected_words):
        return False
    for i in range(len(target_words)):
        if target_words[i] != detected_words[i]:
            return False
    return True


def calculate_similarity(a, b):
    """Returns similarity between two strings (0-1) using SequenceMatcher"""
    return difflib.SequenceMatcher(None, a, b).ratio()


def extract_enemy_name_easyocr(name_area):
    """
    Extract enemy name using EasyOCR (better performance and speed)
    Uses white character filtering for better detection
    
    Args:
        name_area: Image area containing enemy name (BGR format)
        
    Returns:
        tuple: (name: str, original_text: str) or ('', '') if not found
    """
    if not ocr_utils.initialize_ocr_reader():
        return ('', '')
    
    if config.ocr_reader is None:
        return ('', '')
    
    try:
        # Convert to HSV for white detection
        hsv = cv2.cvtColor(name_area, cv2.COLOR_BGR2HSV)
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 50, 255])
        mask_white = cv2.inRange(hsv, lower_white, upper_white)
        white_chars = cv2.bitwise_and(name_area, name_area, mask=mask_white)
        
        # Morphological operations to clean up the mask
        kernel_close = np.ones((2, 2), np.uint8)
        kernel_open = np.ones((1, 1), np.uint8)
        mask_white = cv2.morphologyEx(mask_white, cv2.MORPH_CLOSE, kernel_close)
        mask_white = cv2.morphologyEx(mask_white, cv2.MORPH_OPEN, kernel_open)
        
        # Convert to RGB for EasyOCR
        img_rgb = cv2.cvtColor(white_chars, cv2.COLOR_BGR2RGB)
        
        # Count white pixels for debugging
        white_pixels = cv2.countNonZero(mask_white)
        total_pixels = mask_white.shape[0] * mask_white.shape[1]
        white_percentage = white_pixels / total_pixels * 100
        
        # Try OCR with white-filtered image first
        results = config.ocr_reader.readtext(
            img_rgb, 
            paragraph=False, 
            detail=1, 
            contrast_ths=0.1, 
            adjust_contrast=0.3, 
            text_threshold=0.5, 
            link_threshold=0.3, 
            low_text=0.3, 
            canvas_size=1280, 
            mag_ratio=1.0
        )
        
        if results:
            # Filter results to only letters
            filtered_results = []
            for result in results:
                text = result[1].strip()
                text_letters_only = re.sub('[^a-zA-Z\\s]', '', text)
                if text_letters_only and len(text_letters_only.strip()) >= 1:
                    filtered_results.append((result[0], text_letters_only.strip(), result[2]))
            
            if filtered_results:
                # Find best result (longest word count, then longest text)
                best_result = max(filtered_results, key=lambda x: len(x[1].split()))
                if len([r for r in filtered_results if len(r[1].split()) == len(best_result[1].split())]) > 1:
                    best_result = max(filtered_results, key=lambda x: len(x[1]))
            else:
                best_result = max(results, key=lambda x: len(x[1]))
            
            name = best_result[1].strip()
            original_text = best_result[1]
            
            # Save debug images
            debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug')
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
            cv2.imwrite(os.path.join(debug_dir, 'enemy_name_easyocr_input.png'), name_area)
            cv2.imwrite(os.path.join(debug_dir, 'enemy_name_white_chars.png'), white_chars)
            cv2.imwrite(os.path.join(debug_dir, 'enemy_name_mask.png'), mask_white)
            
            debug_img = name_area.copy()
            cv2.putText(debug_img, f'OCR Detected: {name}', (2, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1, cv2.LINE_AA)
            cv2.putText(debug_img, f'Original Text: {original_text}', (2, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 0), 1, cv2.LINE_AA)
            cv2.putText(debug_img, f'Confidence: {best_result[2]:.2f}', (2, 37), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 0), 1, cv2.LINE_AA)
            cv2.imwrite(os.path.join(debug_dir, 'enemy_name_ocr_detected.png'), debug_img)
            
            return (name, original_text)
        else:
            # Try with original image if filtered version fails
            img_rgb_original = cv2.cvtColor(name_area, cv2.COLOR_BGR2RGB)
            results_original = config.ocr_reader.readtext(img_rgb_original)
            
            if results_original:
                best_result = max(results_original, key=lambda x: len(x[1]))
                text = best_result[1]
                confidence = best_result[2]
                text_letters_only = re.sub('[^a-zA-Z\\s]', '', text)
                name = text_letters_only.strip()
                
                # Save debug image
                debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug')
                if not os.path.exists(debug_dir):
                    os.makedirs(debug_dir)
                debug_img = name_area.copy()
                cv2.putText(debug_img, f'OCR Detected: {name}', (2, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1, cv2.LINE_AA)
                cv2.putText(debug_img, f'Original Text: {text}', (2, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 0), 1, cv2.LINE_AA)
                cv2.putText(debug_img, f'Confidence: {confidence:.2f}', (2, 37), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 0), 1, cv2.LINE_AA)
                cv2.putText(debug_img, 'No Filters', (2, 49), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 0, 255), 1, cv2.LINE_AA)
                cv2.imwrite(os.path.join(debug_dir, 'enemy_name_ocr_detected.png'), debug_img)
                
                return (name, text)
            else:
                # No detection
                debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug')
                if not os.path.exists(debug_dir):
                    os.makedirs(debug_dir)
                debug_img = name_area.copy()
                cv2.putText(debug_img, 'OCR Detected: NONE', (2, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1, cv2.LINE_AA)
                cv2.putText(debug_img, 'Original Text: N/A', (2, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1, cv2.LINE_AA)
                cv2.putText(debug_img, 'Confidence: 0.00', (2, 37), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1, cv2.LINE_AA)
                cv2.putText(debug_img, 'No Detection', (2, 49), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1, cv2.LINE_AA)
                cv2.imwrite(os.path.join(debug_dir, 'enemy_name_ocr_detected.png'), debug_img)
                return ('', '')
                
    except Exception as e:
        print(f'[Enemy Name OCR] Error: {str(e)}')
        debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug')
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        debug_img = name_area.copy()
        cv2.putText(debug_img, 'OCR Error', (2, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1, cv2.LINE_AA)
        cv2.putText(debug_img, f'Error: {str(e)[:30]}', (2, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1, cv2.LINE_AA)
        cv2.putText(debug_img, 'Confidence: N/A', (2, 37), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1, cv2.LINE_AA)
        cv2.imwrite(os.path.join(debug_dir, 'enemy_name_ocr_detected.png'), debug_img)
        return ('', '')
    
    return ('', '')


def should_target_current_mob():
    """Check if current mob should be targeted (opposite of skip - only attack if in target list)"""
    if not config.current_target_mob:
        return False
    
    # If no target list, attack all mobs
    if not config.mob_target_list:
        return True
    
    # Only attack if mob is in target list
    detected_normalized = normalize_text(config.current_target_mob)
    for target_mob in config.mob_target_list:
        target_normalized = normalize_text(target_mob)
        # Check for exact match or contains match
        if contains_complete_word(target_mob, config.current_target_mob):
            return True
        # Also check similarity for partial matches
        if abs(len(detected_normalized) - len(target_normalized)) <= 2:
            similarity = calculate_similarity(detected_normalized, target_normalized)
            if similarity >= 0.7:
                return True
    
    return False


def detect_and_verify_mob_after_target(delay=0.15, retry_delay=0.1):
    """
    Detect and verify mob after retargeting (reusable function)
    Uses calibration-based detection to get enemy name and verify if it should be targeted
    
    Args:
        delay: Initial delay before detection (default: 0.15s)
        retry_delay: Delay before retry if first detection fails (default: 0.1s)
        
    Returns:
        dict: {
            'detected': bool,
            'name': str or None,
            'should_target': bool,
            'needs_retarget': bool  # True if mob detected but not in target list
        }
    """
    if not config.connected_window:
        return {'detected': False, 'name': None, 'should_target': False, 'needs_retarget': False}
    
    if not config.calibrator or config.calibrator.mp_position is None:
        return {'detected': False, 'name': None, 'should_target': False, 'needs_retarget': False}
    
    import enemy_bar_detection
    import time
    
    # Initial delay to allow mob name to appear after targeting
    time.sleep(delay)
    
    hwnd = config.connected_window.handle
    detected_mob = None
    
    # Try to detect mob name using calibration-based detection
    result = enemy_bar_detection.detect_enemy_for_auto_attack(hwnd, targets=None)
    detected_mob = result.get('name')
    
    # If not detected and mob detection is enabled, retry once
    if not detected_mob and config.mob_detection_enabled:
        time.sleep(retry_delay)
        result = enemy_bar_detection.detect_enemy_for_auto_attack(hwnd, targets=None)
        detected_mob = result.get('name')
    
    # Update config with detected mob name
    if detected_mob:
        config.current_target_mob = detected_mob
        config.current_enemy_name = detected_mob
        config.last_mob_detection_time = time.time()
    else:
        config.current_enemy_name = None
    
    # Check if mob should be targeted
    should_target = should_target_current_mob() if detected_mob else False
    needs_retarget = detected_mob and config.mob_detection_enabled and config.mob_target_list and not should_target
    
    return {
        'detected': bool(detected_mob),
        'name': detected_mob,
        'should_target': should_target,
        'needs_retarget': needs_retarget
    }

