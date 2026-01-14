"""
Auto-calibration module for detecting HP/MP bar positions
Based on the decompiled Calibrar.py functionality
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
            filename = f'calibrar_{name}.png'
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
                print('[Calibration] Calibration completed successfully!')
                return True
            else:
                print('[Calibration] Calibration failed: Could not find HP/MP bars')
                return False
                
        except Exception as e:
            print(f'[Calibration] Error during calibration: {e}')
            import traceback
            traceback.print_exc()
            return False
    
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
