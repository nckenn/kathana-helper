"""
Auto-calibration module for detecting HP/MP bar positions
"""
import os
import cv2
import numpy as np
import win32gui
import win32con
import win32ui
import win32api
import config
import window_utils


class Calibrator:
    """Handles automatic detection of HP/MP bar positions"""
    
    def __init__(self):
        """Initialize the calibrator"""
        self.hp_dimensions = (164, 15)  # Expected HP bar dimensions (width, height)
        self.mp_dimensions = (164, 15)  # Expected MP bar dimensions (width, height)
        self.hp_position = None  # (x, y) position of HP bar
        self.mp_position = None  # (x, y) position of MP bar
        self.skills_bar1_position = None  # (x, y) position of first skill bar
        self.skills_bar2_position = None  # (x, y) position of second skill bar
        self.skills_spacing = None  # Spacing between skill bars in pixels
        self.skills_orientation = None  # "horizontal" or "vertical" - orientation of skill bars
        self.area_skills = None  # (x_min, y_min, x_max, y_max) for skills area
        self.system_message_area = None  # (x, y, width, height) for system message region
        self.enemy_hp_area = None  # (x, y, width, height) for enemy HP bar area
        self.enemy_name_area = None  # (x, y, width, height) for enemy name area
        self.debug_dir = os.path.join(os.path.dirname(__file__), 'debug')
        
        # Create debug directory if it doesn't exist
        if not os.path.exists(self.debug_dir):
            try:
                os.makedirs(self.debug_dir)
                print(f'[Calibration] Debug directory created: {self.debug_dir}')
            except Exception as e:
                print(f'[Calibration] Error creating debug directory: {e}')
    
    def save_debug_image(self, image, name):
        """Save a debug image"""
        try:
            filename = f'calibrate_{name}.png'
            filepath = os.path.join(self.debug_dir, filename)
            cv2.imwrite(filepath, image)
            print(f'[Calibration] Debug image saved: {filename}')
            return filepath
        except Exception as e:
            print(f'[Calibration] Error saving debug image: {e}')
            return None
    
    def capture_window(self, hwnd):
        """
        Capture the screen of a specific window
        Args:
            hwnd: Window handle to capture
        Returns:
            numpy.array: Image in BGR format
        """
        hwndDC = None
        mfcDC = None
        saveDC = None
        saveBitMap = None
        
        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
            
            signedIntsArray = saveBitMap.GetBitmapBits(True)
            img = np.frombuffer(signedIntsArray, dtype='uint8')
            img.shape = (height, width, 4)
            result = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            return result
        except Exception as e:
            print(f'[Calibration] Error capturing window: {e}')
            raise
        finally:
            if saveDC is not None:
                saveDC.DeleteDC()
            if mfcDC is not None:
                mfcDC.DeleteDC()
            if hwndDC is not None:
                win32gui.ReleaseDC(hwnd, hwndDC)
            if saveBitMap is not None:
                win32gui.DeleteObject(saveBitMap.GetHandle())
    
    def find_bars(self, screen_img):
        """
        Find HP and MP bars by color and dimensions
        Excludes red bars that don't have an associated blue bar (like Kubasang)
        
        Args:
            screen_img: Screen image in BGR format
        Returns:
            bool: True if both HP and MP bars were found
        """
        self.save_debug_image(screen_img, 'original')
        
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(screen_img, cv2.COLOR_BGR2HSV)
        
        # Define color ranges for red (HP) and blue (MP)
        # Red can be in two ranges (wrapping around hue)
        lower_red1 = np.array([0, 120, 120])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 120, 120])
        upper_red2 = np.array([180, 255, 255])
        lower_blue = np.array([100, 120, 120])
        upper_blue = np.array([140, 255, 255])
        
        # Create masks
        red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
        
        # Apply morphological operations to clean up the masks
        kernel = np.ones((2, 2), np.uint8)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
        blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_OPEN, kernel)
        
        self.save_debug_image(red_mask, 'red_mask')
        self.save_debug_image(blue_mask, 'blue_mask')
        
        # Find contours
        red_contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        blue_contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Draw contours for debugging
        debug_img = screen_img.copy()
        cv2.drawContours(debug_img, red_contours, -1, (0, 0, 255), 1)
        cv2.drawContours(debug_img, blue_contours, -1, (255, 0, 0), 1)
        self.save_debug_image(debug_img, 'contours')
        
        print(f'[Calibration] Red contours found: {len(red_contours)}')
        print(f'[Calibration] Blue contours found: {len(blue_contours)}')
        
        valid_red_bars = []
        valid_blue_bars = []
        
        # Look for red bars with expected dimensions
        for i, red_contour in enumerate(red_contours):
            red_x, red_y, red_w, red_h = cv2.boundingRect(red_contour)
            print(f'[Calibration] Analyzing red contour {i}: pos=({red_x},{red_y}), dim={red_w}x{red_h}')
            
            # Check if dimensions match expected HP bar (with some tolerance)
            if 160 <= red_w <= 168 and 12 <= red_h <= 16:
                # Look for associated blue bar (MP bar should be below HP bar)
                has_associated_blue = False
                associated_blue = None
                
                for j, blue_contour in enumerate(blue_contours):
                    blue_x, blue_y, blue_w, blue_h = cv2.boundingRect(blue_contour)
                    
                    # Check if blue bar has similar width and is positioned below red bar
                    if (160 <= blue_w <= 168 and 12 <= blue_h <= 16 and 
                        abs(blue_y - (red_y + 14)) <= 5):  # MP bar is typically ~14 pixels below HP
                        has_associated_blue = True
                        associated_blue = (blue_x, blue_y, blue_w, blue_h, j)
                        print(f'[Calibration] Found associated blue bar at ({blue_x}, {blue_y})')
                        break
                
                if has_associated_blue:
                    valid_red_bars.append((red_x, red_y, red_w, red_h, i))
                    valid_blue_bars.append(associated_blue)
                    print(f'[Calibration] Valid HP bar found (with associated MP bar)')
                else:
                    print(f'[Calibration] Red bar without blue bar - EXCLUDED (likely Kubasang)')
            else:
                print(f'[Calibration] Red contour does not match HP bar dimensions')
        
        print(f'[Calibration] Valid blue bars (associated with HP): {len(valid_blue_bars)}')
        
        if valid_red_bars and valid_blue_bars:
            # Use the first valid pair
            hp_x, hp_y, hp_w, hp_h, hp_idx = valid_red_bars[0]
            mp_x, mp_y, mp_w, mp_h, mp_idx = valid_blue_bars[0]
            
            self.hp_position = (hp_x, hp_y)
            self.mp_position = (mp_x, mp_y)
            
            print(f'[Calibration] HP bar selected: ({hp_x}, {hp_y}) with dimensions: {hp_w}x{hp_h}')
            print(f'[Calibration] MP bar selected: ({mp_x}, {mp_y}) with dimensions: {mp_w}x{mp_h}')
            
            # Save debug images
            self.save_debug_image(screen_img[hp_y:hp_y + hp_h, hp_x:hp_x + hp_w], 'hp_found')
            self.save_debug_image(screen_img[mp_y:mp_y + mp_h, mp_x:mp_x + mp_w], 'mp_found')
            
            return True
        else:
            print('[Calibration] No valid HP/MP bars found (with both bars associated)')
            return False
    
    def find_skill_bars(self, screen_img):
        """
        Find skill bars using template matching and calculate spacing between them
        
        Args:
            screen_img: Screen image in BGR format
        Returns:
            tuple: (bar1_position, bar2_position) or (None, None) if not found
        """
        try:
            # Use resolve_resource_path for PyInstaller compatibility
            bar1_path = config.resolve_resource_path('skill_bar_1.bmp')
            bar2_path = config.resolve_resource_path('skill_bar_2.bmp')
            
            # Fallback to old method for development if resolve_resource_path returns None
            if bar1_path is None:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                bar1_path = os.path.join(current_dir, 'skill_bar_1.bmp')
            if bar2_path is None:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                bar2_path = os.path.join(current_dir, 'skill_bar_2.bmp')
            
            print(f'[Calibration] Looking for skill bar 1 at: {bar1_path}')
            print(f'[Calibration] Looking for skill bar 2 at: {bar2_path}')
            
            # Check if template files exist
            if not os.path.exists(bar1_path):
                print(f'[Calibration] ERROR: File {bar1_path} does not exist')
                self.save_debug_image(screen_img, 'skill_bars_missing_file1')
                return (None, None)
            
            if not os.path.exists(bar2_path):
                print(f'[Calibration] ERROR: File {bar2_path} does not exist')
                self.save_debug_image(screen_img, 'skill_bars_missing_file2')
                return (None, None)
            
            # Check for vertical-specific templates first
            bar1_vertical_path = None
            bar2_vertical_path = None
            
            # Try to find vertical templates (skill_bar_1_vertical.bmp, skill_bar_2_vertical.bmp)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            bar1_vertical_path = os.path.join(current_dir, 'skill_bar_1_vertical.bmp')
            bar2_vertical_path = os.path.join(current_dir, 'skill_bar_2_vertical.bmp')
            
            # Also try with resolve_resource_path
            bar1_vertical_path_resolved = config.resolve_resource_path('skill_bar_1_vertical.bmp')
            bar2_vertical_path_resolved = config.resolve_resource_path('skill_bar_2_vertical.bmp')
            
            if bar1_vertical_path_resolved and os.path.exists(bar1_vertical_path_resolved):
                bar1_vertical_path = bar1_vertical_path_resolved
            elif not os.path.exists(bar1_vertical_path):
                bar1_vertical_path = None
                
            if bar2_vertical_path_resolved and os.path.exists(bar2_vertical_path_resolved):
                bar2_vertical_path = bar2_vertical_path_resolved
            elif not os.path.exists(bar2_vertical_path):
                bar2_vertical_path = None
            
            # Load template images
            bar1 = cv2.imread(bar1_path)
            bar2 = cv2.imread(bar2_path)
            
            if bar1 is None:
                print(f'[Calibration] ERROR: Could not load image {bar1_path}')
                self.save_debug_image(screen_img, 'skill_bars_load_error1')
                return (None, None)
            
            if bar2 is None:
                print(f'[Calibration] ERROR: Could not load image {bar2_path}')
                self.save_debug_image(screen_img, 'skill_bars_load_error2')
                return (None, None)
            
            # Load vertical templates if they exist
            bar1_vertical = None
            bar2_vertical = None
            has_vertical_templates = False
            
            if bar1_vertical_path and bar2_vertical_path:
                bar1_vertical = cv2.imread(bar1_vertical_path)
                bar2_vertical = cv2.imread(bar2_vertical_path)
                
                if bar1_vertical is not None and bar2_vertical is not None:
                    has_vertical_templates = True
                    print(f'[Calibration] Found vertical-specific templates: {bar1_vertical_path}, {bar2_vertical_path}')
                    self.save_debug_image(bar1_vertical, 'skill_bar_1_vertical_loaded')
                    self.save_debug_image(bar2_vertical, 'skill_bar_2_vertical_loaded')
                else:
                    print(f'[Calibration] Vertical templates found but could not load, will use rotated horizontal templates')
            else:
                print(f'[Calibration] No vertical-specific templates found, will use rotated horizontal templates')
            
            # Get template dimensions
            bar1_h, bar1_w = bar1.shape[:2]
            bar2_h, bar2_w = bar2.shape[:2]
            
            print(f'[Calibration] Skill bar 1 dimensions: {bar1_w}x{bar1_h}')
            print(f'[Calibration] Skill bar 2 dimensions: {bar2_w}x{bar2_h}')
            
            # Save loaded templates for debugging
            self.save_debug_image(bar1, 'skill_bar_1_loaded')
            self.save_debug_image(bar2, 'skill_bar_2_loaded')
            
            # Convert to grayscale for template matching
            gray_screen = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
            gray_bar1 = cv2.cvtColor(bar1, cv2.COLOR_BGR2GRAY)
            gray_bar2 = cv2.cvtColor(bar2, cv2.COLOR_BGR2GRAY)
            
            # Threshold for acceptable match
            threshold = 0.65
            
            # Try horizontal orientation first (original templates)
            result1_h = cv2.matchTemplate(gray_screen, gray_bar1, cv2.TM_CCOEFF_NORMED)
            result2_h = cv2.matchTemplate(gray_screen, gray_bar2, cv2.TM_CCOEFF_NORMED)
            
            min_val1_h, max_val1_h, min_loc1_h, max_loc1_h = cv2.minMaxLoc(result1_h)
            min_val2_h, max_val2_h, min_loc2_h, max_loc2_h = cv2.minMaxLoc(result2_h)
            
            print(f'[Calibration] Horizontal - Skill bar 1 match: {max_val1_h:.4f} at {max_loc1_h}')
            print(f'[Calibration] Horizontal - Skill bar 2 match: {max_val2_h:.4f} at {max_loc2_h}')
            
            horizontal_score = (max_val1_h + max_val2_h) / 2.0
            horizontal_valid = max_val1_h >= threshold and max_val2_h >= threshold
            
            # Try vertical orientation
            if has_vertical_templates:
                # Use actual vertical templates (best option)
                print(f'[Calibration] Using vertical-specific templates for matching')
                gray_bar1_vertical = cv2.cvtColor(bar1_vertical, cv2.COLOR_BGR2GRAY)
                gray_bar2_vertical = cv2.cvtColor(bar2_vertical, cv2.COLOR_BGR2GRAY)
                
                result1_v = cv2.matchTemplate(gray_screen, gray_bar1_vertical, cv2.TM_CCOEFF_NORMED)
                result2_v = cv2.matchTemplate(gray_screen, gray_bar2_vertical, cv2.TM_CCOEFF_NORMED)
                
                min_val1_v, max_val1_v, min_loc1_v, max_loc1_v = cv2.minMaxLoc(result1_v)
                min_val2_v, max_val2_v, min_loc2_v, max_loc2_v = cv2.minMaxLoc(result2_v)
                
                bar1_rotated = bar1_vertical
                bar2_rotated = bar2_vertical
                vertical_rotation = "vertical templates"
                
                print(f'[Calibration] Vertical (templates) - Skill bar 1 match: {max_val1_v:.4f} at {max_loc1_v}')
                print(f'[Calibration] Vertical (templates) - Skill bar 2 match: {max_val2_v:.4f} at {max_loc2_v}')
            else:
                # Fall back to rotating horizontal templates - try both rotation directions
                # Try clockwise rotation first
                bar1_rotated_cw = cv2.rotate(bar1, cv2.ROTATE_90_CLOCKWISE)
                bar2_rotated_cw = cv2.rotate(bar2, cv2.ROTATE_90_CLOCKWISE)
                gray_bar1_rotated_cw = cv2.cvtColor(bar1_rotated_cw, cv2.COLOR_BGR2GRAY)
                gray_bar2_rotated_cw = cv2.cvtColor(bar2_rotated_cw, cv2.COLOR_BGR2GRAY)
                
                result1_v_cw = cv2.matchTemplate(gray_screen, gray_bar1_rotated_cw, cv2.TM_CCOEFF_NORMED)
                result2_v_cw = cv2.matchTemplate(gray_screen, gray_bar2_rotated_cw, cv2.TM_CCOEFF_NORMED)
                
                min_val1_v_cw, max_val1_v_cw, min_loc1_v_cw, max_loc1_v_cw = cv2.minMaxLoc(result1_v_cw)
                min_val2_v_cw, max_val2_v_cw, min_loc2_v_cw, max_loc2_v_cw = cv2.minMaxLoc(result2_v_cw)
                
                # Try counter-clockwise rotation
                bar1_rotated_ccw = cv2.rotate(bar1, cv2.ROTATE_90_COUNTERCLOCKWISE)
                bar2_rotated_ccw = cv2.rotate(bar2, cv2.ROTATE_90_COUNTERCLOCKWISE)
                gray_bar1_rotated_ccw = cv2.cvtColor(bar1_rotated_ccw, cv2.COLOR_BGR2GRAY)
                gray_bar2_rotated_ccw = cv2.cvtColor(bar2_rotated_ccw, cv2.COLOR_BGR2GRAY)
                
                result1_v_ccw = cv2.matchTemplate(gray_screen, gray_bar1_rotated_ccw, cv2.TM_CCOEFF_NORMED)
                result2_v_ccw = cv2.matchTemplate(gray_screen, gray_bar2_rotated_ccw, cv2.TM_CCOEFF_NORMED)
                
                min_val1_v_ccw, max_val1_v_ccw, min_loc1_v_ccw, max_loc1_v_ccw = cv2.minMaxLoc(result1_v_ccw)
                min_val2_v_ccw, max_val2_v_ccw, min_loc2_v_ccw, max_loc2_v_ccw = cv2.minMaxLoc(result2_v_ccw)
                
                # Choose best vertical match (clockwise or counter-clockwise)
                vertical_cw_score = (max_val1_v_cw + max_val2_v_cw) / 2.0
                vertical_ccw_score = (max_val1_v_ccw + max_val2_v_ccw) / 2.0
                
                if vertical_cw_score >= vertical_ccw_score:
                    max_val1_v = max_val1_v_cw
                    max_val2_v = max_val2_v_cw
                    max_loc1_v = max_loc1_v_cw
                    max_loc2_v = max_loc2_v_cw
                    bar1_rotated = bar1_rotated_cw
                    bar2_rotated = bar2_rotated_cw
                    vertical_rotation = "clockwise"
                else:
                    max_val1_v = max_val1_v_ccw
                    max_val2_v = max_val2_v_ccw
                    max_loc1_v = max_loc1_v_ccw
                    max_loc2_v = max_loc2_v_ccw
                    bar1_rotated = bar1_rotated_ccw
                    bar2_rotated = bar2_rotated_ccw
                    vertical_rotation = "counter-clockwise"
                
                print(f'[Calibration] Vertical (CW) - Skill bar 1 match: {max_val1_v_cw:.4f} at {max_loc1_v_cw}')
                print(f'[Calibration] Vertical (CW) - Skill bar 2 match: {max_val2_v_cw:.4f} at {max_loc2_v_cw}')
                print(f'[Calibration] Vertical (CCW) - Skill bar 1 match: {max_val1_v_ccw:.4f} at {max_loc1_v_ccw}')
                print(f'[Calibration] Vertical (CCW) - Skill bar 2 match: {max_val2_v_ccw:.4f} at {max_loc2_v_ccw}')
                print(f'[Calibration] Vertical - Best: {vertical_rotation} (score: {max(vertical_cw_score, vertical_ccw_score):.4f})')
                
                # Save rotated templates for debugging
                self.save_debug_image(bar1_rotated, 'skill_bar_1_rotated_vertical')
                self.save_debug_image(bar2_rotated, 'skill_bar_2_rotated_vertical')
            
            # Calculate vertical score
            if has_vertical_templates:
                vertical_score = (max_val1_v + max_val2_v) / 2.0
            else:
                vertical_score = max(vertical_cw_score, vertical_ccw_score)
            
            # Use slightly lower threshold for vertical (might be harder to match)
            vertical_threshold = threshold - 0.05  # 0.60 instead of 0.65
            vertical_valid = max_val1_v >= vertical_threshold and max_val2_v >= vertical_threshold
            
            # Determine which orientation to use (prefer the one with better match)
            use_horizontal = False
            use_vertical = False
            
            if horizontal_valid and vertical_valid:
                # Both valid, use the one with better score
                if horizontal_score >= vertical_score:
                    use_horizontal = True
                    print(f'[Calibration] Both orientations valid, using horizontal (score: {horizontal_score:.4f} vs {vertical_score:.4f})')
                else:
                    use_vertical = True
                    print(f'[Calibration] Both orientations valid, using vertical (score: {vertical_score:.4f} vs {horizontal_score:.4f})')
            elif horizontal_valid:
                use_horizontal = True
                print(f'[Calibration] Using horizontal orientation')
            elif vertical_valid:
                use_vertical = True
                print(f'[Calibration] Using vertical orientation')
            else:
                print('[Calibration] Skill bars not found with sufficient confidence in either orientation')
                print(f'[Calibration] Horizontal - Skill bar 1: {max_val1_h:.4f}, Skill bar 2: {max_val2_h:.4f} (minimum threshold: {threshold})')
                print(f'[Calibration] Vertical - Skill bar 1: {max_val1_v:.4f}, Skill bar 2: {max_val2_v:.4f} (minimum threshold: {vertical_threshold:.2f})')
                
                # Create debug image showing failed matches (use horizontal for visualization)
                debug_img = screen_img.copy()
                cv2.rectangle(debug_img, max_loc1_h, 
                             (max_loc1_h[0] + bar1_w, max_loc1_h[1] + bar1_h), (0, 0, 255), 2)
                cv2.rectangle(debug_img, max_loc2_h, 
                             (max_loc2_h[0] + bar2_w, max_loc2_h[1] + bar2_h), (0, 0, 255), 2)
                self.save_debug_image(debug_img, 'skill_bars_not_found')
                
                return (None, None)
            
            # Use the selected orientation
            if use_horizontal:
                max_loc1 = max_loc1_h
                max_loc2 = max_loc2_h
                max_val1 = max_val1_h
                max_val2 = max_val2_h
                bar1_w_used = bar1_w
                bar1_h_used = bar1_h
                bar2_w_used = bar2_w
                bar2_h_used = bar2_h
                orientation = "horizontal"
            else:  # use_vertical
                max_loc1 = max_loc1_v
                max_loc2 = max_loc2_v
                max_val1 = max_val1_v
                max_val2 = max_val2_v
                
                if has_vertical_templates:
                    # Use actual dimensions from vertical templates
                    bar1_h_used, bar1_w_used = bar1_vertical.shape[:2]
                    bar2_h_used, bar2_w_used = bar2_vertical.shape[:2]
                else:
                    # Dimensions are swapped for rotated templates
                    bar1_w_used = bar1_h
                    bar1_h_used = bar1_w
                    bar2_w_used = bar2_h
                    bar2_h_used = bar2_w
                
                orientation = "vertical"
            
            # Store positions, orientation, and calculate spacing
            self.skills_bar1_position = max_loc1
            self.skills_bar2_position = max_loc2
            self.skills_orientation = orientation
            
            # Calculate spacing based on orientation
            if orientation == "horizontal":
                self.skills_spacing = max_loc2[0] - max_loc1[0]
            else:  # vertical
                self.skills_spacing = max_loc2[1] - max_loc1[1]
            
            # Calculate area_skills based on orientation
            x1, y1 = max_loc1
            x2, y2 = max_loc2
            
            if orientation == "vertical":
                # Vertical bars: stacked vertically
                # Similar to horizontal: keep height as actual span, expand width (to the right)
                x_min = min(x1, x2)
                # For vertical bars, determine which bar is on top
                # Top bar is the one with smaller y coordinate
                if y1 <= y2:
                    # bar1 is on top (or same level)
                    top_y = y1
                    bottom_y = y2 + bar2_h_used  # Bottom of bar2 (which is below)
                else:
                    # bar2 is on top
                    top_y = y2
                    bottom_y = y1 + bar1_h_used  # Bottom of bar1 (which is below)
                
                y_min = top_y
                y_max = bottom_y
                x_max_original = max(x1 + bar1_w_used, x2 + bar2_w_used)
                original_width = x_max_original - x_min
                original_height = y_max - y_min  # Actual height from top of first bar to bottom of last bar
                # Keep height as actual span (like horizontal keeps width)
                # Expand width by 5x to capture more skill columns to the right (like horizontal expands height downward)
                new_width = original_width * 5
                x_max_new = x_min + new_width
                # Use actual height span, no expansion (mirror of horizontal which keeps width)
                y_max_new = y_max
                self.area_skills = (x_min, y_min, x_max_new, y_max_new)
                print(f'[Calibration] Skills area set (vertical): {self.area_skills}')
                print(f'[Calibration]   Bar positions: bar1=({x1},{y1}), bar2=({x2},{y2})')
                print(f'[Calibration]   Bar dimensions: bar1={bar1_w_used}x{bar1_h_used}, bar2={bar2_w_used}x{bar2_h_used}')
                print(f'[Calibration]   Vertical span: top={y_min}, bottom={y_max}, height={original_height}')
                print(f'[Calibration]   Expanded: width={new_width} (5x original), height={original_height} (actual span, no expansion)')
            else:
                # Horizontal bars: side by side, expand height to capture more skills
                x_min = min(x1, x2)
                y_min = min(y1, y2)
                x_max = max(x1 + bar1_w_used, x2 + bar2_w_used)
                y_max_original = max(y1 + bar1_h_used, y2 + bar2_h_used)
                original_height = y_max_original - y_min
                new_height = original_height * 5
                y_max_new = y_min + new_height
                self.area_skills = (x_min, y_min, x_max, y_max_new)
                print(f'[Calibration] Skills area set (horizontal): {self.area_skills}')
                print(f'[Calibration]   Bar positions: bar1=({x1},{y1}), bar2=({x2},{y2})')
                print(f'[Calibration]   Bar dimensions: bar1={bar1_w_used}x{bar1_h_used}, bar2={bar2_w_used}x{bar2_h_used}')
                print(f'[Calibration]   Original height: {original_height}, Expanded height: {new_height}')
            
            # Create debug image showing found bars
            debug_img = screen_img.copy()
            cv2.rectangle(debug_img, max_loc1, 
                         (max_loc1[0] + bar1_w_used, max_loc1[1] + bar1_h_used), (0, 255, 0), 2)
            cv2.rectangle(debug_img, max_loc2, 
                         (max_loc2[0] + bar2_w_used, max_loc2[1] + bar2_h_used), (0, 255, 0), 2)
            self.save_debug_image(debug_img, 'skill_bars_found')
            
            # Calculate and save area image
            if self.area_skills:
                x_min, y_min, x_max, y_max = self.area_skills
                area_img = screen_img.copy()
                cv2.rectangle(area_img, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
                self.save_debug_image(area_img, 'skills_sequence_area')
            
            print(f'[Calibration] Skill bar 1 found at: {max_loc1} ({orientation})')
            print(f'[Calibration] Skill bar 2 found at: {max_loc2} ({orientation})')
            print(f'[Calibration] Spacing between bars: {self.skills_spacing} pixels ({orientation})')
            
            return (max_loc1, max_loc2)
                
        except Exception as e:
            print(f'[Calibration] Error finding skill bars: {e}')
            import traceback
            traceback.print_exc()
            self.save_debug_image(screen_img, 'skill_bars_error')
            return (None, None)
    
    def find_enemy_hp_and_name_area(self, screen_img):
        """
        Find enemy HP bar and name area using MP position as reference
        
        Args:
            screen_img: Screen image in BGR format
        Returns:
            tuple: (enemy_hp_area, enemy_name_area) or (None, None) if not found
        """
        if self.mp_position is None:
            print('[Calibration] Cannot find enemy HP/name area: MP position not calibrated')
            return (None, None)
        
        try:
            mp_x, mp_y = self.mp_position
            
            # Constants for enemy detection area (matching auto_attack.py)
            SEARCH_AREA_OFFSET_Y = 19  # Pixels below MP position
            SEARCH_AREA_WIDTH = 163    # Width of search area
            SEARCH_AREA_HEIGHT = 35    # Height of search area
            SEARCH_AREA_OFFSET_X = -1  # X offset from MP position
            NAME_AREA_HEIGHT = 18      # Height of name area
            
            screen_h, screen_w = screen_img.shape[:2]
            
            # Calculate search area bounds
            search_x = max(0, mp_x + SEARCH_AREA_OFFSET_X)
            search_y = max(0, mp_y + SEARCH_AREA_OFFSET_Y)
            search_x2 = min(screen_w, search_x + SEARCH_AREA_WIDTH)
            search_y2 = min(screen_h, search_y + SEARCH_AREA_HEIGHT)
            
            # Ensure valid area
            if search_x2 <= search_x or search_y2 <= search_y:
                print('[Calibration] Invalid search area bounds for enemy detection')
                return (None, None)
            
            # Extract search area
            search_area = screen_img[search_y:search_y2, search_x:search_x2]
            
            if search_area.size == 0 or search_area.shape[0] < NAME_AREA_HEIGHT:
                print('[Calibration] Search area too small for enemy detection')
                return (None, None)
            
            # Extract enemy name area (first 18 pixels)
            name_area = search_area[0:NAME_AREA_HEIGHT, :]
            
            # Convert to HSV for red detection (HP bar)
            hsv = cv2.cvtColor(search_area, cv2.COLOR_BGR2HSV)
            
            # Red color ranges for HP bar detection
            lower_red1 = np.array([0, 100, 100])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([160, 100, 100])
            upper_red2 = np.array([180, 255, 255])
            
            red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
            red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            red_mask = cv2.bitwise_or(red_mask1, red_mask2)
            
            # Look for HP bar in the area below name (rows 18-35)
            hp_search_region = red_mask[NAME_AREA_HEIGHT:, :]
            
            # Find contours in HP search region
            hp_contours, _ = cv2.findContours(hp_search_region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            hp_found = False
            hp_x, hp_y, hp_w, hp_h = 0, 0, 0, 0
            
            # Look for a red bar with reasonable dimensions
            for contour in hp_contours:
                x, y, w, h = cv2.boundingRect(contour)
                # HP bar should be roughly 10-163 pixels wide and 6-18 pixels tall
                if w >= 10 and w <= 163 and h >= 6 and h <= 18:
                    hp_x = x
                    hp_y = y + NAME_AREA_HEIGHT  # Adjust Y to absolute position in search area
                    hp_w = w
                    hp_h = h
                    hp_found = True
                    break
            
            # Store areas as (center_x, center_y, width, height)
            if hp_found:
                # Enemy HP area: relative to screen
                enemy_hp_x = search_x + hp_x
                enemy_hp_y = search_y + hp_y
                enemy_hp_center_x = enemy_hp_x + hp_w // 2
                enemy_hp_center_y = enemy_hp_y + hp_h // 2
                self.enemy_hp_area = (enemy_hp_center_x, enemy_hp_center_y, hp_w, hp_h)
            else:
                # Still set area even if no HP bar found (for calibration purposes)
                # Use the expected area location
                enemy_hp_x = search_x
                enemy_hp_y = search_y + NAME_AREA_HEIGHT
                enemy_hp_center_x = enemy_hp_x + SEARCH_AREA_WIDTH // 2
                enemy_hp_center_y = enemy_hp_y + 9  # Center of HP bar region
                self.enemy_hp_area = (enemy_hp_center_x, enemy_hp_center_y, SEARCH_AREA_WIDTH, 18)
            
            # Enemy name area: relative to screen
            name_center_x = search_x + SEARCH_AREA_WIDTH // 2
            name_center_y = search_y + NAME_AREA_HEIGHT // 2
            self.enemy_name_area = (name_center_x, name_center_y, SEARCH_AREA_WIDTH, NAME_AREA_HEIGHT)
            
            # Create debug image
            debug_img = screen_img.copy()
            cv2.rectangle(debug_img, (search_x, search_y), (search_x2, search_y2), (255, 255, 0), 2)
            if hp_found:
                cv2.rectangle(debug_img, 
                             (search_x + hp_x, search_y + hp_y), 
                             (search_x + hp_x + hp_w, search_y + hp_y + hp_h), 
                             (0, 255, 0), 2)
            cv2.rectangle(debug_img, 
                         (search_x, search_y), 
                         (search_x2, search_y + NAME_AREA_HEIGHT), 
                         (0, 255, 255), 2)
            self.save_debug_image(debug_img, 'enemy_hp_name_area')
            self.save_debug_image(name_area, 'enemy_name_area_extracted')
            
            if hp_found:
                print(f'[Calibration] Enemy HP bar found at search area position ({hp_x}, {hp_y})')
            else:
                print('[Calibration] Enemy HP bar not found, but area calibrated for detection')
            print(f'[Calibration] Enemy name area calibrated: center=({name_center_x}, {name_center_y}), size={SEARCH_AREA_WIDTH}x{NAME_AREA_HEIGHT}')
            
            return (self.enemy_hp_area, self.enemy_name_area)
            
        except Exception as e:
            print(f'[Calibration] Error finding enemy HP/name area: {e}')
            import traceback
            traceback.print_exc()
            self.save_debug_image(screen_img, 'enemy_hp_name_error')
            return (None, None)
    
    def find_system_message_area(self, screen_img):
        """
        Find system message area using chat scrollbar as reference
        
        Args:
            screen_img: Screen image in BGR format
        Returns:
            tuple: (x, y, width, height) or None if not found
        """
        try:
            # Use resolve_resource_path for PyInstaller compatibility
            scrollbar_path = config.resolve_resource_path('chat_bar_1.png')
            
            if scrollbar_path is None:
                # Fallback to old method for development
                current_dir = os.path.dirname(os.path.abspath(__file__))
                scrollbar_path = os.path.join(current_dir, 'chat_bar_1.png')
            
            print(f'[Calibration] Looking for chat scrollbar at: {scrollbar_path}')
            
            # Check if template file exists
            if not os.path.exists(scrollbar_path):
                print(f'[Calibration] ERROR: File {scrollbar_path} does not exist')
                self.save_debug_image(screen_img, 'system_message_missing_file')
                return None
            
            # Load template image
            scrollbar_template = cv2.imread(scrollbar_path)
            
            if scrollbar_template is None:
                print(f'[Calibration] ERROR: Could not load image {scrollbar_path}')
                self.save_debug_image(screen_img, 'system_message_load_error')
                return None
            
            # Get template dimensions
            template_h, template_w = scrollbar_template.shape[:2]
            
            print(f'[Calibration] Chat scrollbar template dimensions: {template_w}x{template_h}')
            
            # Save loaded template for debugging
            self.save_debug_image(scrollbar_template, 'chat_scrollbar_loaded')
            
            # Convert to grayscale for template matching
            gray_screen = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
            gray_template = cv2.cvtColor(scrollbar_template, cv2.COLOR_BGR2GRAY)
            
            # Perform template matching
            result = cv2.matchTemplate(gray_screen, gray_template, cv2.TM_CCOEFF_NORMED)
            
            # Get best match location
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            print(f'[Calibration] Chat scrollbar match: {max_val:.4f} at {max_loc}')
            
            # Threshold for acceptable match
            threshold = 0.65
            
            if max_val >= threshold:
                scrollbar_x, scrollbar_y = max_loc

                # Optional vertical offset to nudge the scrollbar reference + chat area downward
                # (useful if the match is slightly above the actual text region)
                vertical_offset_px = 4
                scrollbar_y = max(0, scrollbar_y + vertical_offset_px)
                
                # Calculate system message area
                # In your UI, the scrollbar sits on the LEFT edge of the chat panel.
                # The actual system message/chat text region is to the RIGHT of the scrollbar
                # and should have the SAME height as the scrollbar.
                
                screen_h, screen_w = screen_img.shape[:2]
                
                # Height is exactly the scrollbar height (clamped to screen)
                chat_top = max(0, scrollbar_y)
                chat_bottom = min(screen_h, scrollbar_y + template_h)
                chat_height = max(0, chat_bottom - chat_top)

                # Text region begins immediately to the right of the scrollbar (no gap)
                gap_from_scrollbar = 0
                chat_left = scrollbar_x + template_w + gap_from_scrollbar
                chat_left = max(0, min(screen_w, chat_left))

                # Determine the RIGHT boundary by locating a second UI anchor (`chat_bar_2.png`)
                # This is more stable than scanning for dark pixels.
                anchor_path = config.resolve_resource_path('chat_bar_2.png')
                
                if anchor_path is None:
                    # Fallback to old method for development
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    anchor_path = os.path.join(current_dir, 'chat_bar_2.png')
                
                anchor_template = None
                anchor_loc = None
                anchor_w = 0
                anchor_h = 0

                if anchor_path and os.path.exists(anchor_path):
                    anchor_template = cv2.imread(anchor_path)
                    if anchor_template is not None:
                        anchor_h, anchor_w = anchor_template.shape[:2]
                        self.save_debug_image(anchor_template, 'chat_bar_2_loaded')

                        gray_anchor = cv2.cvtColor(anchor_template, cv2.COLOR_BGR2GRAY)
                        anchor_result = cv2.matchTemplate(gray_screen, gray_anchor, cv2.TM_CCOEFF_NORMED)
                        _, anchor_max_val, _, anchor_max_loc = cv2.minMaxLoc(anchor_result)
                        print(f'[Calibration] Char bar 2 match: {anchor_max_val:.4f} at {anchor_max_loc}')

                        anchor_threshold = 0.60
                        if anchor_max_val >= anchor_threshold:
                            anchor_loc = anchor_max_loc
                        else:
                            print(f'[Calibration] Warning: chat_bar_2 match below threshold ({anchor_max_val:.4f} < {anchor_threshold})')
                    else:
                        print(f'[Calibration] ERROR: Could not load image {anchor_path}')
                else:
                    print(f'[Calibration] Warning: File {anchor_path} does not exist')

                # Compute width based on distance from scrollbar to the anchor
                # If anchor is found, we use its RIGHT edge as the boundary (with a small margin).
                right_margin_from_anchor = 2
                if anchor_loc is not None:
                    anchor_x, anchor_y = anchor_loc
                    chat_right = max(chat_left, (anchor_x + anchor_w) - right_margin_from_anchor)
                else:
                    # Fallback if anchor not found: keep a conservative width
                    chat_right = min(screen_w, chat_left + 320)

                chat_width = max(0, chat_right - chat_left)

                # Calculate center and dimensions for system_message_area format
                chat_center_x = chat_left + chat_width // 2
                chat_center_y = chat_top + chat_height // 2
                
                # Store as (x, y, width, height) where x,y is center
                self.system_message_area = (chat_center_x, chat_center_y, chat_width, chat_height)
                
                # Create debug image showing found scrollbar and calculated area
                debug_img = screen_img.copy()
                
                # Draw scrollbar location (apply vertical offset so debug matches calibrated area)
                cv2.rectangle(
                    debug_img,
                    (scrollbar_x, scrollbar_y),
                    (scrollbar_x + template_w, scrollbar_y + template_h),
                    (0, 255, 0),
                    2
                )
                
                # Draw calculated chat area
                left = chat_left
                top = chat_top
                right = min(screen_w, chat_left + chat_width)
                bottom = chat_bottom
                cv2.rectangle(debug_img, (left, top), (right, bottom), (255, 0, 0), 2)

                # Draw detected width boundary for easier visual tuning
                try:
                    boundary_x = right
                    cv2.line(debug_img, (boundary_x, top), (boundary_x, bottom), (255, 255, 0), 2)
                except Exception:
                    pass

                # Draw anchor location if found
                if anchor_loc is not None and anchor_w > 0 and anchor_h > 0:
                    ax, ay = anchor_loc
                    cv2.rectangle(debug_img, (ax, ay), (ax + anchor_w, ay + anchor_h), (0, 255, 255), 2)
                
                self.save_debug_image(debug_img, 'system_message_area_found')
                
                print(f'[Calibration] Chat scrollbar found at: {max_loc}')
                print(f'[Calibration] System message area calculated: center=({chat_center_x}, {chat_center_y}), size={chat_width}x{chat_height}')
                
                return self.system_message_area
            else:
                print('[Calibration] Chat scrollbar not found with sufficient confidence')
                print(f'[Calibration] Match value: {max_val:.4f} (minimum threshold: {threshold})')
                
                # Create debug image showing failed match
                debug_img = screen_img.copy()
                cv2.rectangle(debug_img, max_loc, 
                             (max_loc[0] + template_w, max_loc[1] + template_h), (0, 0, 255), 2)
                self.save_debug_image(debug_img, 'system_message_area_not_found')
                
                return None
                
        except Exception as e:
            print(f'[Calibration] Error finding system message area: {e}')
            import traceback
            traceback.print_exc()
            self.save_debug_image(screen_img, 'system_message_area_error')
            return None
    
    def calibrate(self, hwnd):
        """
        Perform calibration by capturing the window and finding bars
        
        Args:
            hwnd: Window handle to calibrate
        Returns:
            bool: True if calibration was successful
        """
        try:
            print('[Calibration] Starting calibration...')
            screen = self.capture_window(hwnd)
            
            if screen is None:
                print('[Calibration] Failed to capture window')
                return False
            
            result = self.find_bars(screen)
            
            if result:
                # Find skill bars after HP/MP bars are found
                skill_bars_result = self.find_skill_bars(screen)
                if skill_bars_result[0] is not None and skill_bars_result[1] is not None:
                    print('[Calibration] Skill bars found successfully!')
                else:
                    print('[Calibration] Warning: Skill bars not found, but HP/MP calibration succeeded')
                
                # Find enemy HP and name area
                enemy_result = self.find_enemy_hp_and_name_area(screen)
                if enemy_result[0] is not None and enemy_result[1] is not None:
                    print('[Calibration] Enemy HP and name area found successfully!')
                else:
                    print('[Calibration] Warning: Enemy HP/name area not found, but HP/MP calibration succeeded')
                
                # Find system message area using chat scrollbar
                system_message_result = self.find_system_message_area(screen)
                if system_message_result is not None:
                    print('[Calibration] System message area found successfully!')
                else:
                    print('[Calibration] Warning: System message area not found, but HP/MP calibration succeeded')
                
                # Print detailed calibration summary
                self.print_calibration_summary()
                print('[Calibration] Calibration completed successfully!')
                print(f'[Calibration] Debug images saved to: {self.debug_dir}')
                return True
            else:
                print('[Calibration] Calibration failed: Could not find HP/MP bars')
                print(f'[Calibration] Check debug images in: {self.debug_dir}')
                return False
                
        except Exception as e:
            print(f'[Calibration] Error during calibration: {e}')
            import traceback
            traceback.print_exc()
            return False
    
    def get_calibration_summary(self):
        """
        Get a formatted summary string of what was calibrated
        
        Returns:
            str: Formatted summary string for GUI display
        """
        # Check if calibration is successful
        hp_ok = self.hp_position is not None
        mp_ok = self.mp_position is not None
        skills_ok = self.skills_bar1_position is not None and self.skills_bar2_position is not None
        enemy_ok = self.enemy_hp_area is not None and self.enemy_name_area is not None
        system_msg_ok = self.system_message_area is not None
        
        # Build summary string
        summary_lines = []
        summary_lines.append("CALIBRATION SUMMARY")
        summary_lines.append("=" * 40)
        
        # Show checkmarks only if successful, otherwise show X
        if hp_ok:
            summary_lines.append("✓ HP Bar")
        else:
            summary_lines.append("✗ HP Bar: NOT FOUND")
        
        if mp_ok:
            summary_lines.append("✓ MP Bar")
        else:
            summary_lines.append("✗ MP Bar: NOT FOUND")
        
        if skills_ok:
            orientation_text = f" ({self.skills_orientation})" if self.skills_orientation else ""
            summary_lines.append(f"✓ Skill Bars{orientation_text}")
        else:
            summary_lines.append("✗ Skill Bars: NOT FOUND")
        
        if enemy_ok:
            summary_lines.append("✓ Enemy HP")
            summary_lines.append("✓ Enemy Name")
        else:
            summary_lines.append("✗ Enemy HP: NOT FOUND")
            summary_lines.append("✗ Enemy Name: NOT FOUND")
        
        if system_msg_ok:
            summary_lines.append("✓ System Message")
        else:
            summary_lines.append("✗ System Message: NOT FOUND")
        
        return "\n".join(summary_lines)
    
    def print_calibration_summary(self):
        """Print a summary of what was calibrated"""
        print('\n' + '='*60)
        print('[Calibration] CALIBRATION SUMMARY')
        print('='*60)
        
        # Check if calibration is successful
        hp_ok = self.hp_position is not None
        mp_ok = self.mp_position is not None
        skills_ok = self.skills_bar1_position is not None and self.skills_bar2_position is not None
        enemy_ok = self.enemy_hp_area is not None and self.enemy_name_area is not None
        system_msg_ok = self.system_message_area is not None
        
        # Show checkmarks only if successful, otherwise show X
        if hp_ok:
            print('[Calibration] ✓ HP Bar')
        else:
            print('[Calibration] ✗ HP Bar: NOT FOUND')
        
        if mp_ok:
            print('[Calibration] ✓ MP Bar')
        else:
            print('[Calibration] ✗ MP Bar: NOT FOUND')
        
        if skills_ok:
            print('[Calibration] ✓ Skill Bars')
        else:
            print('[Calibration] ✗ Skill Bars: NOT FOUND')
        
        if enemy_ok:
            print('[Calibration] ✓ Enemy HP')
            print('[Calibration] ✓ Enemy Name')
        else:
            print('[Calibration] ✗ Enemy HP: NOT FOUND')
            print('[Calibration] ✗ Enemy Name: NOT FOUND')
        
        if system_msg_ok:
            print('[Calibration] ✓ System Message')
        else:
            print('[Calibration] ✗ System Message: NOT FOUND')
        
        print('='*60)
        print('[Calibration] To verify calibration, check these debug images:')
        print(f'[Calibration]   - calibrate_original.png (full screen capture)')
        print(f'[Calibration]   - calibrate_contours.png (detected HP/MP contours)')
        print(f'[Calibration]   - calibrate_hp_found.png (extracted HP bar)')
        print(f'[Calibration]   - calibrate_mp_found.png (extracted MP bar)')
        if skills_ok:
            print(f'[Calibration]   - calibrate_skill_bars_found.png (skill bars with green boxes)')
            print(f'[Calibration]   - calibrate_skills_sequence_area.png (skill area)')
        if enemy_ok:
            print(f'[Calibration]   - calibrate_enemy_hp_name_area.png (enemy HP and name area)')
            print(f'[Calibration]   - calibrate_enemy_name_area_extracted.png (enemy name area)')
        if system_msg_ok:
            print(f'[Calibration]   - calibrate_system_message_area_found.png (scrollbar and chat area)')
        print('='*60 + '\n')
    
    def is_calibrated(self):
        """
        Check if calibration is complete
        
        Returns:
            dict: Status of calibration with details
        """
        status = {
            'hp_calibrated': self.hp_position is not None,
            'mp_calibrated': self.mp_position is not None,
            'skills_calibrated': (self.skills_bar1_position is not None and 
                                 self.skills_bar2_position is not None),
            'fully_calibrated': (self.hp_position is not None and 
                               self.mp_position is not None),
            'hp_position': self.hp_position,
            'mp_position': self.mp_position,
            'skills_bar1_position': self.skills_bar1_position,
            'skills_bar2_position': self.skills_bar2_position,
            'skills_spacing': self.skills_spacing,
            'skills_orientation': self.skills_orientation,
            'area_skills': self.area_skills,
            'system_message_calibrated': self.system_message_area is not None,
            'system_message_area': self.system_message_area,
            'enemy_hp_calibrated': self.enemy_hp_area is not None,
            'enemy_name_calibrated': self.enemy_name_area is not None,
            'enemy_hp_area': self.enemy_hp_area,
            'enemy_name_area': self.enemy_name_area
        }
        return status
    
    def get_hp_percentage(self, hwnd):
        """
        Calculate current HP percentage by analyzing the HP bar
        
        Args:
            hwnd: Window handle
        Returns:
            float: HP percentage (0-100)
        """
        if self.hp_position is None:
            return 0
        
        try:
            screen = self.capture_window(hwnd)
            if screen is None:
                return 0
            
            x, y = self.hp_position
            w, h = self.hp_dimensions
            
            # Extract HP bar region
            hp_region = screen[y:y + h, x:x + w]
            self.save_debug_image(hp_region, 'hp_region_percent')
            
            # Convert to HSV for better color detection
            hsv = cv2.cvtColor(hp_region, cv2.COLOR_BGR2HSV)
            
            # Red color range for HP bar
            lower_red1 = np.array([0, 120, 120])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([170, 120, 120])
            upper_red2 = np.array([180, 255, 255])
            
            red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
            red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            red_mask = cv2.bitwise_or(red_mask1, red_mask2)
            
            self.save_debug_image(red_mask, 'hp_mask_percent')
            
            # Count red pixels per column
            red_pixels = np.sum(red_mask > 0, axis=0)
            total_height = red_mask.shape[0]
            last_red_column = 0
            min_pixels_required = total_height * 0.5  # At least 50% of height should be red
            
            # Find the last column with enough red pixels
            for i in range(len(red_pixels)):
                if red_pixels[i] >= min_pixels_required:
                    last_red_column = i + 1
            
            # Calculate percentage
            if last_red_column >= w - 2:
                percentage = 100.0
            else:
                percentage = round(last_red_column / w * 100, 1)
            
            # Debug visualization
            debug_img = hp_region.copy()
            if last_red_column > 0:
                cv2.line(debug_img, (last_red_column - 1, 0), (last_red_column - 1, h - 1), (0, 255, 0), 1)
            self.save_debug_image(debug_img, 'hp_last_column')
            
            print(f'[Calibration] HP: Last red column: {last_red_column} of {w}')
            print(f'[Calibration] HP: Calculated percentage: {percentage}%')
            
            return percentage
            
        except Exception as e:
            print(f'[Calibration] Error calculating HP percentage: {e}')
            return 0
    
    def get_mp_percentage(self, hwnd):
        """
        Calculate current MP percentage by analyzing the MP bar
        
        Args:
            hwnd: Window handle
        Returns:
            float: MP percentage (0-100)
        """
        if self.mp_position is None:
            return 0
        
        try:
            screen = self.capture_window(hwnd)
            if screen is None:
                return 0
            
            x, y = self.mp_position
            w, h = self.mp_dimensions
            
            # Extract MP bar region
            mp_region = screen[y:y + h, x:x + w]
            self.save_debug_image(mp_region, 'mp_region_percent')
            
            # Convert to HSV for better color detection
            hsv = cv2.cvtColor(mp_region, cv2.COLOR_BGR2HSV)
            
            # Blue color range for MP bar
            lower_blue = np.array([100, 120, 120])
            upper_blue = np.array([140, 255, 255])
            blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
            
            self.save_debug_image(blue_mask, 'mp_mask_percent')
            
            # Count blue pixels per column
            blue_pixels = np.sum(blue_mask > 0, axis=0)
            total_height = blue_mask.shape[0]
            last_blue_column = 0
            min_pixels_required = total_height * 0.5  # At least 50% of height should be blue
            
            # Find the last column with enough blue pixels
            for i in range(len(blue_pixels)):
                if blue_pixels[i] >= min_pixels_required:
                    last_blue_column = i + 1
            
            # Calculate percentage
            if last_blue_column >= w - 2:
                percentage = 100.0
            else:
                percentage = round(last_blue_column / w * 100, 1)
            
            # Debug visualization
            debug_img = mp_region.copy()
            if last_blue_column > 0:
                cv2.line(debug_img, (last_blue_column - 1, 0), (last_blue_column - 1, h - 1), (0, 255, 0), 1)
            self.save_debug_image(debug_img, 'mp_last_column')
            
            print(f'[Calibration] MP: Last blue column: {last_blue_column} of {w}')
            print(f'[Calibration] MP: Calculated percentage: {percentage}%')
            
            return percentage
            
        except Exception as e:
            print(f'[Calibration] Error calculating MP percentage: {e}')
            return 0
