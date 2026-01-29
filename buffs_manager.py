"""
Buffs Manager - Handles automatic buff activation
"""
import time
import os
import config
import input_handler
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
        print(f'[DEBUG] Buffs update_and_activate_buffs - run_active: {run_active}')
        print(f'[DEBUG] Buffs configured: {[i for i, buff in enumerate(self.buffs) if buff]}')
        
        # Save debug image of active buffs area
        debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug')
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        cv2.imwrite(os.path.join(debug_dir, 'buffs_active_area.png'), area_buffs_activos)
        
        for idx, image_path in enumerate(self.buffs):
            if not image_path:
                continue
            
            # Check if buff is enabled (bypass if disabled)
            if not config.buffs_config[idx]['enabled']:
                continue
            
            print(f'[DEBUG] Processing buff {idx + 1}: {image_path}')
            # Resolve relative path before loading template
            resolved_path = config.resolve_resource_path(image_path)
            if not resolved_path:
                print(f'[DEBUG] Could not resolve path for buff {idx + 1}: {image_path}')
                continue
            
            template = cv2.imread(resolved_path, cv2.IMREAD_COLOR)
            if template is None:
                print(f'[DEBUG] Could not load template for buff {idx + 1}')
                continue
            
            print(f'[DEBUG] Template loaded for buff {idx + 1}, dimensions: {template.shape}')
            
            # Search in area_buffs_activos to check if buff is already active
            found_in_buffs = False
            if area_buffs_activos.shape[0] >= template.shape[0] and area_buffs_activos.shape[1] >= template.shape[1]:
                res_buff = cv2.matchTemplate(area_buffs_activos, template, cv2.TM_CCOEFF_NORMED)
                min_val_b, max_val_b, min_loc_b, max_loc_b = cv2.minMaxLoc(res_buff)
                print(f'[DEBUG] Buff {idx + 1} in active buffs - confidence: {max_val_b:.3f}')
                if max_val_b > 0.7:
                    found_in_buffs = True
                    print(f'[DEBUG] Buff {idx + 1} found in active buffs (already active)')
            else:
                print(f'[DEBUG] Buff {idx + 1} - active buffs area too small: {area_buffs_activos.shape} vs {template.shape}')
            
            # Activate buff if NOT found in active buffs area
            if not found_in_buffs:
                print(f'[DEBUG] Buff {idx + 1} not found in active buffs, activating...')
                if now - self.last_click_times[idx] >= 0.3:
                    # Image-only mode: find skill in area_skills and click it
                    if area_skills is not None and area_skills.shape[0] > 0 and area_skills.shape[1] > 0:
                        # Search for skill in area_skills
                        found_in_skills = False
                        skill_loc = None
                        if area_skills.shape[0] >= template.shape[0] and area_skills.shape[1] >= template.shape[1]:
                            res = cv2.matchTemplate(area_skills, template, cv2.TM_CCOEFF_NORMED)
                            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                            print(f'[DEBUG] Buff {idx + 1} in skills - confidence: {max_val:.3f}')
                            if max_val > 0.7:
                                found_in_skills = True
                                skill_loc = max_loc
                                print(f'[DEBUG] Buff {idx + 1} found in skills at position: {skill_loc}')
                                
                                # Calculate click position in "window image" coordinates
                                # (same coordinate system as Calibrator.capture_window())
                                th, tw = template.shape[:2]
                                click_x = x1 + skill_loc[0] + tw // 2
                                click_y = y1 + skill_loc[1] + th // 2

                                print(f'[BUFF] Buff {idx + 1} not active, clicking skill at window-image ({click_x}, {click_y})')
                                if not input_handler.perform_mouse_click_window_image(hwnd, click_x, click_y):
                                    print(f'[BUFF] Failed to click skill for buff {idx + 1}')

                                # Save debug image
                                debug_img = area_skills.copy()
                                cv2.circle(debug_img, (skill_loc[0] + tw // 2, skill_loc[1] + th // 2), 20, (0, 0, 255), 3)
                                cv2.imwrite(os.path.join(debug_dir, f'buff_click_{idx}.png'), debug_img)
                            else:
                                print(f'[BUFF] Buff {idx + 1} not found in skills area (confidence too low: {max_val:.3f})')
                        else:
                            print(f'[BUFF] Skills area too small for buff {idx + 1}: {area_skills.shape} vs {template.shape}')
                    else:
                        print(f'[BUFF] area_skills not available for buff {idx + 1}')
                    
                    self.last_click_times[idx] = now
            else:
                print(f'[DEBUG] Buff {idx + 1} is already active, no action needed')
