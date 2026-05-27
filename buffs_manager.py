"""
Buffs Manager - Handles automatic buff activation
"""
import time
import os
import config
import input_handler
import debug_io
import debug_utils
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print('[CV2] OpenCV not available. Install with: pip install opencv-python')




class BuffsManager:
    def __init__(self, num_buffs=8):
        self.buffs = [None] * num_buffs
        self.last_click_times = [0.0] * num_buffs
        self.ui_reference = None
    
    def set_buff(self, idx, image_path):
        """Set a buff image path for a specific index (should be relative path)"""
        if 0 <= idx < len(self.buffs):
            self.buffs[idx] = image_path
            print(f'[BuffsManager] Buff {idx + 1} set to: {image_path}')
    
    def clear_buff(self, idx):
        """Clear a buff at a specific index"""
        if 0 <= idx < len(self.buffs):
            self.buffs[idx] = None
            print(f'[BuffsManager] Buff {idx + 1} cleared')
    
    def set_ui_reference(self, ui):
        """Set reference to UI (kept for compatibility; keys are no longer used)"""
        self.ui_reference = ui
    
    def _buff_active_in_area(self, template, area_buffs_activos):
        """Return True if buff template is visible in the active-buffs strip."""
        if (area_buffs_activos is None or area_buffs_activos.size == 0
                or template is None):
            return False
        if (area_buffs_activos.shape[0] < template.shape[0]
                or area_buffs_activos.shape[1] < template.shape[1]):
            return False
        res = cv2.matchTemplate(area_buffs_activos, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        return max_val > 0.7

    def update_and_activate_buffs(self, hwnd, screen, area_skills, area_buffs_activos, x1, y1, run_active=True):
        """
        For each selected buff:
        - Search in area_buffs_activos (template matching > 0.7) to check if buff is already active.
        - If NOT found in area_buffs_activos, activate buff by clicking its location in area_skills.
        - Save debug image of area_buffs_activos (overwrite).
        """
        if not run_active:
            return None
        
        if not CV2_AVAILABLE:
            return None
        
        now = time.time()
        debug_utils.debug_print(f'Buffs update - run_active: {run_active}', 'BuffsManager')
        debug_utils.debug_print(
            f'Buffs configured: {[i for i, buff in enumerate(self.buffs) if buff]}',
            'BuffsManager',
        )

        debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug')
        if debug_io.should_save_debug_images():
            os.makedirs(debug_dir, exist_ok=True)
            debug_io.save_cv2_image(
                os.path.join(debug_dir, 'buffs_active_area.png'), area_buffs_activos)
        
        for idx, image_path in enumerate(self.buffs):
            if not image_path:
                continue
            
            # Check if buff is enabled (bypass if disabled)
            if not config.buffs_config[idx]['enabled']:
                continue
            
            debug_utils.debug_print(f'Processing buff {idx + 1}: {image_path}', 'BuffsManager')
            # Resolve relative path before loading template
            resolved_path = config.resolve_resource_path(image_path)
            if not resolved_path:
                debug_utils.debug_print(f'Could not resolve path for buff {idx + 1}: {image_path}', 'BuffsManager')
                continue
            
            template = cv2.imread(resolved_path, cv2.IMREAD_COLOR)
            if template is None:
                debug_utils.debug_print(f'Could not load template for buff {idx + 1}', 'BuffsManager')
                continue
            
            debug_utils.debug_print(f'Template loaded for buff {idx + 1}, dimensions: {template.shape}', 'BuffsManager')
            
            # Search in area_buffs_activos to check if buff is already active
            found_in_buffs = self._buff_active_in_area(template, area_buffs_activos)
            if found_in_buffs:
                debug_utils.debug_print(f'Buff {idx + 1} already active', 'BuffsManager')
            else:
                debug_utils.debug_print(
                    f'Buff {idx + 1} in active buffs - not found',
                    'BuffsManager',
                )
            
            # Activate buff if NOT found in active buffs area
            if not found_in_buffs:
                debug_utils.debug_print(f'Buff {idx + 1} not active, activating...', 'BuffsManager')
                if now - self.last_click_times[idx] >= 0.3:
                    # Image-only mode: find skill in area_skills and click it
                    if area_skills is not None and area_skills.shape[0] > 0 and area_skills.shape[1] > 0:
                        # Search for skill in area_skills
                        found_in_skills = False
                        skill_loc = None
                        if area_skills.shape[0] >= template.shape[0] and area_skills.shape[1] >= template.shape[1]:
                            res = cv2.matchTemplate(area_skills, template, cv2.TM_CCOEFF_NORMED)
                            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                            debug_utils.debug_print(f'Buff {idx + 1} in skills - confidence: {max_val:.3f}', 'BuffsManager')
                            if max_val > 0.7:
                                found_in_skills = True
                                skill_loc = max_loc
                                debug_utils.debug_print(f'Buff {idx + 1} found in skills at {skill_loc}', 'BuffsManager')
                                
                                # Calculate click position in "window image" coordinates
                                # (same coordinate system as Calibrator.capture_window())
                                th, tw = template.shape[:2]
                                click_x = x1 + skill_loc[0] + tw // 2
                                click_y = y1 + skill_loc[1] + th // 2

                                print(f'[BUFF] Buff {idx + 1} not active, clicking skill at window-image ({click_x}, {click_y})')
                                if not input_handler.perform_mouse_click_window_image(hwnd, click_x, click_y):
                                    print(f'[BUFF] Failed to click skill for buff {idx + 1}')

                                if debug_io.should_save_debug_images():
                                    debug_img = area_skills.copy()
                                    cv2.circle(debug_img, (skill_loc[0] + tw // 2, skill_loc[1] + th // 2), 20, (0, 0, 255), 3)
                                    debug_io.save_cv2_image(
                                        os.path.join(debug_dir, f'buff_click_{idx}.png'), debug_img)
                            else:
                                print(f'[BUFF] Buff {idx + 1} not found in skills area (confidence too low: {max_val:.3f})')
                        else:
                            print(f'[BUFF] Skills area too small for buff {idx + 1}: {area_skills.shape} vs {template.shape}')
                    else:
                        print(f'[BUFF] area_skills not available for buff {idx + 1}')
                    
                    self.last_click_times[idx] = now
            else:
                print(f'[DEBUG] Buff {idx + 1} is already active, no action needed')
