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
        """Set reference to UI for accessing configured keys"""
        self.ui_reference = ui
    
    def get_buff_key(self, buff_index):
        """Get the configured key for a specific buff"""
        if hasattr(self, 'ui_reference') and self.ui_reference:
            if hasattr(self.ui_reference, 'buffs_keys'):
                key = self.ui_reference.buffs_keys[buff_index].get()
                return key if key else None
        return None
    
    def update_and_activate_buffs(self, hwnd, screen, area_skills, area_buffs_activos, x1, y1, run_active=True):
        """
        For each selected buff:
        - Search in area_skills (template matching > 0.7).
        - Search in area_buffs_activos (template matching > 0.7).
        - If NOT in area_buffs_activos and YES in area_skills, click on the skill in area_skills every 0.3s.
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
            
            # Search in area_skills
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
            else:
                print(f'[DEBUG] Buff {idx + 1} - skills area too small: {area_skills.shape} vs {template.shape}')
            
            # Search in area_buffs_activos
            found_in_buffs = False
            if area_buffs_activos.shape[0] >= template.shape[0] and area_buffs_activos.shape[1] >= template.shape[1]:
                res_buff = cv2.matchTemplate(area_buffs_activos, template, cv2.TM_CCOEFF_NORMED)
                min_val_b, max_val_b, min_loc_b, max_loc_b = cv2.minMaxLoc(res_buff)
                print(f'[DEBUG] Buff {idx + 1} in active buffs - confidence: {max_val_b:.3f}')
                if max_val_b > 0.7:
                    found_in_buffs = True
                    print(f'[DEBUG] Buff {idx + 1} found in active buffs')
            else:
                print(f'[DEBUG] Buff {idx + 1} - active buffs area too small: {area_buffs_activos.shape} vs {template.shape}')
            
            # Activate buff if found in skills but not in active buffs
            if found_in_skills and not found_in_buffs:
                print(f'[DEBUG] Buff {idx + 1} found in skills but not in active buffs')
                if now - self.last_click_times[idx] >= 0.3:
                    key_input = self.get_buff_key(idx)
                    if key_input:
                        print(f'[BUFF] Buff {idx + 1} found, sending key: {key_input}')
                        input_handler.send_input(key_input)
                    else:
                        print(f'[BUFF] No key configured for buff {idx + 1}')
                    self.last_click_times[idx] = now
            else:
                if found_in_skills and found_in_buffs:
                    print(f'[DEBUG] Buff {idx + 1} found in both skills and active buffs')
                elif not found_in_skills:
                    print(f'[DEBUG] Buff {idx + 1} not found in skills')
            
            # Save debug image if found in skills
            if found_in_skills and skill_loc:
                debug_img = area_skills.copy()
                th, tw = template.shape[:2]
                cv2.circle(debug_img, (skill_loc[0] + tw // 2, skill_loc[1] + th // 2), 20, (0, 0, 255), 3)
                cv2.imwrite(os.path.join(debug_dir, f'buff_click_{idx}.png'), debug_img)
