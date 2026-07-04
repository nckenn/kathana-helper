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
import ui_bar_detection


def _best_template_match(gray_screen, gray_template, roi=None, scales=None):
    """Multi-scale template match; returns (score, (x, y), tw, th) in screen coords."""
    if scales is None:
        scales = (0.88, 0.94, 1.0, 1.06)
    sh, sw = gray_screen.shape[:2]
    if roi:
        rx1, ry1, rx2, ry2 = roi
        rx1, ry1 = max(0, int(rx1)), max(0, int(ry1))
        rx2, ry2 = min(sw, int(rx2)), min(sh, int(ry2))
        patch = gray_screen[ry1:ry2, rx1:rx2]
        ox, oy = rx1, ry1
    else:
        patch = gray_screen
        ox, oy = 0, 0
    ph, pw = patch.shape[:2]
    if ph < 8 or pw < 8:
        return -1.0, (0, 0), 0, 0
    th0, tw0 = gray_template.shape[:2]
    best_val, best_xy, best_tw, best_th = -1.0, (0, 0), tw0, th0
    for scale in scales:
        tw = max(4, int(round(tw0 * scale)))
        th = max(4, int(round(th0 * scale)))
        templ = cv2.resize(
            gray_template, (tw, th),
            interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR,
        )
        if ph < th or pw < tw:
            continue
        res = cv2.matchTemplate(patch, templ, cv2.TM_CCOEFF_NORMED)
        _, mv, _, ml = cv2.minMaxLoc(res)
        if mv > best_val:
            best_val = float(mv)
            best_xy = (int(ml[0]) + ox, int(ml[1]) + oy)
            best_tw, best_th = tw, th
    return best_val, best_xy, best_tw, best_th


_CHAT_MATCH_SCALES = (0.50, 0.62, 0.75, 0.88, 0.94, 1.0, 1.06)


def _chat_search_rois(screen_h, screen_w):
    """Chat panel is usually bottom-left; also try right side and full frame."""
    return (
        (0, int(screen_h * 0.38), int(screen_w * 0.62), screen_h),
        (int(screen_w * 0.30), int(screen_h * 0.38), screen_w, screen_h),
        None,
    )


def _match_chat_ui_template(gray_screen, gray_template):
    """Best match across bottom chat ROIs with downscaling for small captures."""
    screen_h, screen_w = gray_screen.shape[:2]
    best = (-1.0, (0, 0), 0, 0)
    for roi in _chat_search_rois(screen_h, screen_w):
        score, loc, tw, th = _best_template_match(
            gray_screen, gray_template, roi=roi, scales=_CHAT_MATCH_SCALES,
        )
        if score > best[0]:
            best = (score, loc, tw, th)
    return best


def _system_message_rect_from_chat_anchors(
    screen_h, screen_w, scroll_xy, scroll_wh, mode_xy=None, mode_wh=None,
):
    """
    Upper chat pane (combat / system damage log) sits above guild chat.

    scroll: double-scrollbar strip (chat_bar_1). mode: Mode1 button (chat_bar_2).
    """
    sx, sy = scroll_xy
    sw, sh = scroll_wh
    chat_left = max(0, min(screen_w, sx + sw))
    upper_top = max(0, sy + 2)
    upper_bottom = max(upper_top + 12, sy + sh // 2 - 2)

    if mode_xy is not None and mode_wh is not None:
        mx, _my = mode_xy
        mw, _mh = mode_wh
        # Text/combat log spans the full chat row — through the Mode1 button on the right.
        chat_right = max(chat_left + 20, min(screen_w, mx + mw + 6))
    else:
        chat_right = min(screen_w, chat_left + 320)

    chat_width = max(0, chat_right - chat_left)
    chat_height = max(0, upper_bottom - upper_top)
    if chat_width < 30 or chat_height < 12:
        return None
    return chat_left, upper_top, chat_width, chat_height


class Calibrator:
    """Handles automatic detection of HP/MP bar positions"""
    
    def __init__(self):
        """Initialize the calibrator"""
        self.hp_dimensions = (210, 15)  # Expected HP bar dimensions (width, height)
        self.mp_dimensions = (210, 15)  # Expected MP bar dimensions (width, height)
        self.hp_position = None  # (x, y) position of HP bar
        self.mp_position = None  # (x, y) position of MP bar
        self.skills_bar1_position = None  # (x, y) position of first skill bar
        self.skills_bar2_position = None  # (x, y) position of second skill bar
        self.skills_spacing = None  # Spacing between skill bars in pixels
        self.skills_orientation = None  # "horizontal" or "vertical" - orientation of skill bars
        self.area_skills = None  # (x_min, y_min, x_max, y_max) for skills area
        self.system_message_area = None  # (left, top, width, height) top-left coords
        self.enemy_hp_area = None  # (x, y, width, height) for enemy HP bar area
        self.enemy_name_area = None  # (x, y, width, height) for enemy name area
        self.last_capture_path = None
        self.last_capture_method = None
        self.last_capture_stats = {}
        self.debug_dir = os.path.join(os.path.dirname(__file__), 'debug')
        
        # Create debug directory if it doesn't exist
        if not os.path.exists(self.debug_dir):
            try:
                os.makedirs(self.debug_dir)
                print(f'[Calibration] Debug directory created: {self.debug_dir}')
            except Exception as e:
                print(f'[Calibration] Error creating debug directory: {e}')
    
    def save_debug_image(self, image, name, force=False):
        """Save a debug image (debug mode, or force=True on calibration failure)."""
        import debug_io
        if not force and not debug_io.should_save_debug_images():
            return None
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
        """Capture the game window — delegates to window_utils (PrintWindow / screen grab fallbacks)."""
        window_utils.focus_game_window(hwnd)
        screen, method = window_utils.capture_window_bgr(hwnd)
        self.last_capture_method = method
        self.last_capture_stats = window_utils.capture_stats(screen)
        path = self.save_debug_image(screen, 'original', force=True)
        self.last_capture_path = path
        if screen is not None:
            stats = self.last_capture_stats
            print(
                f"[Calibration] Capture {stats.get('width', 0)}x{stats.get('height', 0)} "
                f"via {method} (mean={stats.get('mean', 0):.1f}, std={stats.get('std', 0):.1f})"
            )
            if not window_utils.capture_has_content(screen):
                print(
                    '[Calibration] WARNING: capture looks empty/black — '
                    'use windowed mode, keep game visible, and check calibrate_original.png'
                )
        return screen
    
    def find_bars(self, screen_img):
        """
        Find HP and MP bars by color and dimensions.
        Uses row-merged masks so glossy bars with white number overlays still match.
        """
        self.save_debug_image(screen_img, 'original')

        hp_rect, mp_rect, red_merged, blue_merged, red_bands, blue_bands = (
            ui_bar_detection.find_player_hp_mp(screen_img)
        )

        self.save_debug_image(red_merged, 'red_mask')
        self.save_debug_image(blue_merged, 'blue_mask')

        debug_img = screen_img.copy()
        for i, (x, y, w, h) in enumerate(red_bands):
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 0, 255), 1)
            cv2.putText(debug_img, f'R{i}', (x, max(0, y - 2)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
        for j, (x, y, w, h) in enumerate(blue_bands):
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (255, 0, 0), 1)
            cv2.putText(debug_img, f'B{j}', (x, max(0, y - 2)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 0, 0), 1)
        self.save_debug_image(debug_img, 'contours')

        print(f'[Calibration] Red bar bands found: {len(red_bands)}')
        print(f'[Calibration] Blue bar bands found: {len(blue_bands)}')
        for i, (x, y, w, h) in enumerate(red_bands):
            print(f'[Calibration] Red band {i}: pos=({x},{y}), dim={w}x{h}')
        for j, (x, y, w, h) in enumerate(blue_bands):
            print(f'[Calibration] Blue band {j}: pos=({x},{y}), dim={w}x{h}')

        if hp_rect and mp_rect:
            hp_x, hp_y, hp_w, hp_h = hp_rect
            mp_x, mp_y, mp_w, mp_h = mp_rect
            self.hp_position = (hp_x, hp_y)
            self.mp_position = (mp_x, mp_y)
            self.hp_dimensions = (hp_w, hp_h)
            self.mp_dimensions = (mp_w, mp_h)
            print(f'[Calibration] HP bar selected: ({hp_x}, {hp_y}) with dimensions: {hp_w}x{hp_h}')
            print(f'[Calibration] MP bar selected: ({mp_x}, {mp_y}) with dimensions: {mp_w}x{mp_h}')
            self.save_debug_image(screen_img[hp_y:hp_y + hp_h, hp_x:hp_x + hp_w], 'hp_found')
            self.save_debug_image(screen_img[mp_y:mp_y + mp_h, mp_x:mp_x + mp_w], 'mp_found')
            return True

        print('[Calibration] No valid HP/MP bars found')
        debug_img_all = screen_img.copy()
        for i, (x, y, w, h) in enumerate(red_bands):
            cv2.rectangle(debug_img_all, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(debug_img_all, f'R{i}: {w}x{h}', (x, max(0, y - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        for j, (x, y, w, h) in enumerate(blue_bands):
            cv2.rectangle(debug_img_all, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.putText(debug_img_all, f'B{j}: {w}x{h}', (x, max(0, y - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
        self.save_debug_image(debug_img_all, 'no_bars_found_all_contours', force=True)
        self.save_debug_image(red_merged, 'no_bars_red_merged', force=True)
        self.save_debug_image(blue_merged, 'no_bars_blue_merged', force=True)
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
        Find enemy HP bar and name area below the player's MP bar.

        Uses dynamic red-bar detection for the stacked UI (player name+HP+MP,
        then enemy name+HP).
        """
        if self.mp_position is None:
            print('[Calibration] Cannot find enemy HP/name area: MP position not calibrated')
            return (None, None)

        try:
            import hp_number_reader as hr
            mp_x, mp_y = self.mp_position
            mp_h = self.mp_dimensions[1] if self.mp_dimensions else hr.PLAYER_MP_BAR_HEIGHT
            mp_w = self.mp_dimensions[0] if self.mp_dimensions else hr.SEARCH_AREA_WIDTH
            found = hr.locate_enemy_target_strip(
                screen_img, mp_x, mp_y, mp_bar_h=mp_h, mp_bar_w=mp_w,
            )
            if not found:
                print('[Calibration] Could not locate enemy target strip')
                return (None, None)

            self.enemy_name_area = found['name_area']
            hp_area = found.get('hp_area')
            search_x, search_y = found['search_origin']
            nw = int(found['name_area'][2])

            if hp_area:
                self.enemy_hp_area = hp_area
            else:
                self.enemy_hp_area = (
                    search_x + nw // 2,
                    search_y + hr.NAME_AREA_HEIGHT + 9,
                    nw,
                    13,
                )

            debug_img = screen_img.copy()
            cv2.rectangle(
                debug_img,
                (search_x, search_y),
                (search_x + nw, search_y + hr.SEARCH_AREA_HEIGHT),
                (255, 255, 0), 2,
            )
            ncx, ncy, _, nh = self.enemy_name_area
            cv2.rectangle(
                debug_img,
                (int(ncx - nw // 2), int(ncy - nh // 2)),
                (int(ncx + nw // 2), int(ncy + nh // 2)),
                (0, 255, 255), 2,
            )
            if hp_area:
                hcx, hcy, hw, hh = hp_area
                cv2.rectangle(
                    debug_img,
                    (int(hcx - hw // 2), int(hcy - hh // 2)),
                    (int(hcx + hw // 2), int(hcy + hh // 2)),
                    (0, 255, 0), 2,
                )
            self.save_debug_image(debug_img, 'enemy_hp_name_area')
            name_slice = screen_img[search_y:search_y + hr.NAME_AREA_HEIGHT, search_x:search_x + nw]
            self.save_debug_image(name_slice, 'enemy_name_area_extracted')

            print(
                f'[Calibration] Enemy name area calibrated: center=({ncx}, {ncy}), '
                f'size={nw}x{hr.NAME_AREA_HEIGHT}'
            )
            if hp_area:
                print(f'[Calibration] Enemy HP bar found at center {hp_area[:2]}')
            else:
                print('[Calibration] Enemy HP bar not found; name row still calibrated')

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
            
            gray_screen = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
            gray_template = cv2.cvtColor(scrollbar_template, cv2.COLOR_BGR2GRAY)
            screen_h, screen_w = screen_img.shape[:2]

            max_val, max_loc, template_w, template_h = _match_chat_ui_template(
                gray_screen, gray_template,
            )
            print(f'[Calibration] Chat scrollbar match: {max_val:.4f} at {max_loc}')

            scroll_threshold = 0.52
            anchor_path = config.resolve_resource_path('chat_bar_2.png')
            if anchor_path is None:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                anchor_path = os.path.join(current_dir, 'chat_bar_2.png')

            mode_loc = None
            mode_wh = None
            mode_score = -1.0
            if anchor_path and os.path.exists(anchor_path):
                anchor_template = cv2.imread(anchor_path)
                if anchor_template is not None:
                    self.save_debug_image(anchor_template, 'chat_bar_2_loaded')
                    gray_anchor = cv2.cvtColor(anchor_template, cv2.COLOR_BGR2GRAY)
                    mode_score, mode_loc, mode_w, mode_h = _match_chat_ui_template(
                        gray_screen, gray_anchor,
                    )
                    mode_wh = (mode_w, mode_h)
                    print(f'[Calibration] Mode1 anchor match: {mode_score:.4f} at {mode_loc}')
                else:
                    print(f'[Calibration] ERROR: Could not load image {anchor_path}')
            else:
                print(f'[Calibration] Warning: File {anchor_path} does not exist')

            mode_threshold = 0.50
            mode_ok = mode_score >= mode_threshold and mode_loc is not None
            scroll_ok = max_val >= scroll_threshold

            if scroll_ok or mode_ok:
                if scroll_ok:
                    scrollbar_x, scrollbar_y = max_loc
                    scrollbar_y = max(0, scrollbar_y + 4)
                    scroll_xy = (scrollbar_x, scrollbar_y)
                    scroll_wh = (template_w, template_h)
                else:
                    mx, my = mode_loc
                    mw, mh = mode_wh
                    est_h = max(80, min(220, int(screen_h * 0.35)))
                    scroll_xy = (max(0, mx - mw - 300), max(0, my - est_h))
                    scroll_wh = (template_w, est_h)
                    print('[Calibration] Scrollbar weak — estimating from Mode1 anchor')

                rect = _system_message_rect_from_chat_anchors(
                    screen_h,
                    screen_w,
                    scroll_xy,
                    scroll_wh,
                    mode_loc if mode_ok else None,
                    mode_wh if mode_ok else None,
                )
                if rect is None and scroll_ok:
                    scrollbar_x, scrollbar_y = scroll_xy
                    chat_left = scrollbar_x + scroll_wh[0]
                    half_h = max(12, scroll_wh[1] // 2 - 2)
                    rect = (
                        chat_left,
                        scrollbar_y + 2,
                        min(screen_w, chat_left + 320) - chat_left,
                        half_h,
                    )

                if rect is None:
                    print('[Calibration] Could not compute system message rect from anchors')
                    return None

                chat_left, chat_top, chat_width, chat_height = rect
                chat_bottom = chat_top + chat_height
                scrollbar_x, scrollbar_y = scroll_xy
                template_w, template_h = scroll_wh
                self.system_message_area = (chat_left, chat_top, chat_width, chat_height)
                
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

                if mode_ok and mode_loc is not None and mode_wh is not None:
                    ax, ay = mode_loc
                    mw, mh = mode_wh
                    cv2.rectangle(debug_img, (ax, ay), (ax + mw, ay + mh), (0, 255, 255), 2)
                
                self.save_debug_image(debug_img, 'system_message_area_found')
                
                print(f'[Calibration] Chat scrollbar found at: {max_loc}')
                print(
                    f'[Calibration] System message area: top-left=({chat_left}, {chat_top}), '
                    f'size={chat_width}x{chat_height}',
                )
                
                return self.system_message_area
            else:
                print('[Calibration] Chat scrollbar not found with sufficient confidence')
                print(f'[Calibration] Match value: {max_val:.4f} (minimum threshold: {threshold})')
                
                # Create debug image showing failed match
                debug_img = screen_img.copy()
                sx, sy = max_loc
                cv2.rectangle(
                    debug_img,
                    (sx, sy),
                    (sx + template_w, sy + template_h),
                    (0, 0, 255), 2,
                )
                self.save_debug_image(debug_img, 'system_message_area_not_found')
                
                return None
                
        except Exception as e:
            print(f'[Calibration] Error finding system message area: {e}')
            import traceback
            traceback.print_exc()
            self.save_debug_image(screen_img, 'system_message_area_error')
            return None

    @staticmethod
    def _center_rect_to_area(cx, cy, width, height):
        w, h = int(width), int(height)
        return {
            'x': int(cx) - w // 2,
            'y': int(cy) - h // 2,
            'width': w,
            'height': h,
        }

    def export_region_areas(self):
        """Export detected regions as config-style {x, y, width, height} dicts."""
        areas = {}
        if self.hp_position and self.hp_dimensions:
            x, y = self.hp_position
            w, h = self.hp_dimensions
            areas['hp_bar_area'] = {'x': int(x), 'y': int(y), 'width': int(w), 'height': int(h)}
        if self.mp_position and self.mp_dimensions:
            x, y = self.mp_position
            w, h = self.mp_dimensions
            areas['mp_bar_area'] = {'x': int(x), 'y': int(y), 'width': int(w), 'height': int(h)}
        if self.enemy_name_area:
            cx, cy, w, h = self.enemy_name_area
            areas['target_name_area'] = self._center_rect_to_area(cx, cy, w, h)
        if self.enemy_hp_area:
            cx, cy, w, h = self.enemy_hp_area
            areas['target_hp_bar_area'] = self._center_rect_to_area(cx, cy, w, h)
        if self.area_skills:
            x1, y1, x2, y2 = self.area_skills
            areas['skill_area'] = {
                'x': int(x1), 'y': int(y1),
                'width': int(x2 - x1), 'height': int(y2 - y1),
            }
        if self.system_message_area:
            x, y, w, h = self.system_message_area
            areas['system_message_area'] = {
                'x': int(x), 'y': int(y), 'width': int(w), 'height': int(h),
            }
        if areas.get('system_message_area'):
            import region_helpers
            buff = region_helpers.derive_buff_area_from_system_message(
                areas['system_message_area'],
            )
            if buff:
                areas['buff_area'] = buff
        return areas

    def calibrate_from_image(self, screen_img):
        """
        Run full region detection on an existing BGR capture (no window capture).

        Returns True when player HP/MP bars are found (minimum for success).
        """
        if screen_img is None or screen_img.size == 0:
            return False
        if not self.find_bars(screen_img):
            return False
        self.find_skill_bars(screen_img)
        self.find_enemy_hp_and_name_area(screen_img)
        self.find_system_message_area(screen_img)
        return True

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
    
    def _hp_percentage_from_screen(self, screen):
        """Calculate HP percentage from an already-captured screen."""
        if self.hp_position is None or screen is None:
            return 0
        import debug_utils
        try:
            x, y = self.hp_position
            w, h = self.hp_dimensions
            import frame_cache
            origin = frame_cache.get_origin()
            hp_region = frame_cache.crop_rect(screen, x, y, x + w, y + h, origin)
            if hp_region is None or hp_region.size == 0:
                return 0
            self.save_debug_image(hp_region, 'hp_region_percent')
            hsv = cv2.cvtColor(hp_region, cv2.COLOR_BGR2HSV)
            lower_red1 = np.array([0, 120, 120])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([170, 120, 120])
            upper_red2 = np.array([180, 255, 255])
            red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
            red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            red_mask = cv2.bitwise_or(red_mask1, red_mask2)
            self.save_debug_image(red_mask, 'hp_mask_percent')
            red_pixels = np.sum(red_mask > 0, axis=0)
            total_height = red_mask.shape[0]
            last_red_column = 0
            min_pixels_required = total_height * 0.5
            for i in range(len(red_pixels)):
                if red_pixels[i] >= min_pixels_required:
                    last_red_column = i + 1
            if last_red_column >= w - 2:
                percentage = 100.0
            else:
                percentage = round(last_red_column / w * 100, 1)
            debug_img = hp_region.copy()
            if last_red_column > 0:
                cv2.line(debug_img, (last_red_column - 1, 0), (last_red_column - 1, h - 1), (0, 255, 0), 1)
            self.save_debug_image(debug_img, 'hp_last_column')
            debug_utils.debug_print(
                f'HP: column {last_red_column}/{w} -> {percentage}%',
                'Calibration'
            )
            return percentage
        except Exception as e:
            print(f'[Calibration] Error calculating HP percentage: {e}')
            return 0

    def _mp_percentage_from_screen(self, screen):
        """Calculate MP percentage from an already-captured screen."""
        if self.mp_position is None or screen is None:
            return 0
        import debug_utils
        try:
            x, y = self.mp_position
            w, h = self.mp_dimensions
            import frame_cache
            origin = frame_cache.get_origin()
            mp_region = frame_cache.crop_rect(screen, x, y, x + w, y + h, origin)
            if mp_region is None or mp_region.size == 0:
                return 0
            self.save_debug_image(mp_region, 'mp_region_percent')
            hsv = cv2.cvtColor(mp_region, cv2.COLOR_BGR2HSV)
            lower_blue = np.array([100, 120, 120])
            upper_blue = np.array([140, 255, 255])
            blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
            self.save_debug_image(blue_mask, 'mp_mask_percent')
            blue_pixels = np.sum(blue_mask > 0, axis=0)
            total_height = blue_mask.shape[0]
            last_blue_column = 0
            min_pixels_required = total_height * 0.5
            for i in range(len(blue_pixels)):
                if blue_pixels[i] >= min_pixels_required:
                    last_blue_column = i + 1
            if last_blue_column >= w - 2:
                percentage = 100.0
            else:
                percentage = round(last_blue_column / w * 100, 1)
            debug_img = mp_region.copy()
            if last_blue_column > 0:
                cv2.line(debug_img, (last_blue_column - 1, 0), (last_blue_column - 1, h - 1), (0, 255, 0), 1)
            self.save_debug_image(debug_img, 'mp_last_column')
            debug_utils.debug_print(
                f'MP: column {last_blue_column}/{w} -> {percentage}%',
                'Calibration'
            )
            return percentage
        except Exception as e:
            print(f'[Calibration] Error calculating MP percentage: {e}')
            return 0

    def get_hp_mp_percentages_from_screen(self, screen):
        """Read HP and MP from one shared frame. Returns (hp, mp) or None if screen invalid."""
        if screen is None:
            return None
        hp = self._hp_percentage_from_screen(screen) if self.hp_position else 0
        mp = self._mp_percentage_from_screen(screen) if self.mp_position else 0
        return (hp, mp)

    def get_hp_percentage(self, hwnd, screen=None):
        """
        Calculate current HP percentage by analyzing the HP bar
        
        Args:
            hwnd: Window handle
            screen: Optional pre-captured frame
        Returns:
            float: HP percentage (0-100)
        """
        if self.hp_position is None:
            return 0
        try:
            if screen is None:
                import frame_cache
                screen = frame_cache.get_frame(hwnd, self)
            if screen is None:
                return 0
            return self._hp_percentage_from_screen(screen)
        except Exception as e:
            print(f'[Calibration] Error calculating HP percentage: {e}')
            return 0

    def get_mp_percentage(self, hwnd, screen=None):
        """
        Calculate current MP percentage by analyzing the MP bar
        
        Args:
            hwnd: Window handle
            screen: Optional pre-captured frame
        Returns:
            float: MP percentage (0-100)
        """
        if self.mp_position is None:
            return 0
        try:
            if screen is None:
                import frame_cache
                screen = frame_cache.get_frame(hwnd, self)
            if screen is None:
                return 0
            return self._mp_percentage_from_screen(screen)
        except Exception as e:
            print(f'[Calibration] Error calculating MP percentage: {e}')
            return 0


def detect_regions_from_bgr(bgr):
    """
    Auto-detect UI regions on a window capture.

    Returns (success, areas_dict, calibrator). areas_dict maps config keys to
    {x, y, width, height}; optional regions are omitted when not found.
    """
    import bar_color_calibration as bcc

    cal = Calibrator()
    if not cal.calibrate_from_image(bgr):
        return False, {}, cal
    areas = bcc.refine_detected_bar_areas(bgr, cal.export_region_areas())
    return True, areas, cal
