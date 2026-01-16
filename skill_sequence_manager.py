"""
Skill Sequence Manager - Handles automatic skill sequence execution
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


class SkillSequenceManager:
    def __init__(self, num_skills=8):
        self.skills = [None] * num_skills
        self.skill_sequence_index = 0
        self.skill_waiting_activation = False
        self.last_skill_count = 0
        self.ultimo_tiempo_skill = 0
        self.ui_reference = None
        self.enemy_found_previous = False
    
    def set_skill(self, idx, image_path):
        """Set a skill image path for a specific index (should be relative path)"""
        if 0 <= idx < len(self.skills):
            self.skills[idx] = image_path
            print(f'[SkillSequenceManager] Skill {idx + 1} set to: {image_path}')
    
    def clear_skill(self, idx):
        """Clear a skill at a specific index"""
        if 0 <= idx < len(self.skills):
            self.skills[idx] = None
            print(f'[SkillSequenceManager] Skill {idx + 1} cleared')
    
    def set_ui_reference(self, ui):
        """Set reference to UI for accessing configured keys"""
        self.ui_reference = ui
    
    def get_skill_key(self, skill_index):
        """Get the configured key for a specific skill"""
        if hasattr(self, 'ui_reference') and self.ui_reference:
            if hasattr(self.ui_reference, 'skill_sequence_keys'):
                key = self.ui_reference.skill_sequence_keys[skill_index].get()
                return key if key else None
        return None
    
    def reset_sequence(self):
        """Reset the skill sequence to start from the beginning"""
        self.skill_sequence_index = 0
        self.skill_waiting_activation = False
        self.enemy_found_previous = False
        print('[SKILL-SEQUENCE] Sequence reset')
    
    def execute_skill_sequence(self, hwnd, screen, area_skills, enemy_found, run_active=True):
        """
        Execute skill sequence:
        - Cycles through enabled skills in sequence
        - Checks if skill is present in area_skills (template matching > 0.7)
        - If skill found and waiting_activation is False, send key and set waiting_activation
        - If skill disappears (was waiting_activation), advance to next skill
        - Resets sequence when new enemy is detected or enemy is lost
        """
        if not run_active:
            return
        
        if not CV2_AVAILABLE:
            return
        
        # Check if area_skills is available (should be tuple (x1, y1, x2, y2))
        if not area_skills or not isinstance(area_skills, (tuple, list)) or len(area_skills) != 4:
            return
        
        # Build skill_sequence list from config (paths should be relative)
        skill_sequence = []
        for idx in range(len(self.skills)):
            if (self.skills[idx] and 
                config.skill_sequence_config[idx]['enabled']):
                skill_sequence.append(self.skills[idx])
            else:
                skill_sequence.append(None)
        
        # Resolve relative paths and filter to valid skills
        valid_skills = []
        skill_index_map = {}  # Map resolved paths to original indices
        for i, relative_path in enumerate(skill_sequence):
            if relative_path:
                resolved_path = config.resolve_resource_path(relative_path)
                if resolved_path and os.path.exists(resolved_path):
                    valid_skills.append(resolved_path)
                    skill_index_map[resolved_path] = i
        
        n = len(valid_skills)
        
        if n == 0:
            return
        
        # Reset sequence when enemy state changes (new enemy detected or enemy lost)
        if enemy_found and not self.enemy_found_previous:
            # New enemy detected - reset sequence
            self.skill_sequence_index = 0
            self.skill_waiting_activation = False
            print('[SKILL-SEQUENCE] Resetting sequence - new enemy detected')
        elif not enemy_found and self.enemy_found_previous:
            # Enemy lost - reset sequence
            self.skill_sequence_index = 0
            self.skill_waiting_activation = False
            print('[SKILL-SEQUENCE] Resetting sequence - enemy lost')
        
        self.enemy_found_previous = enemy_found
        
        if not enemy_found:
            return
        
        # Reset if skill count changed
        if not hasattr(self, 'last_skill_count') or self.last_skill_count != n:
            self.skill_sequence_index = 0
            self.skill_waiting_activation = False
            self.last_skill_count = n
        
        if not hasattr(self, 'ultimo_tiempo_skill'):
            self.ultimo_tiempo_skill = 0
        
        if not hasattr(self, 'skill_sequence_index'):
            self.skill_sequence_index = 0
        
        if not hasattr(self, 'skill_waiting_activation'):
            self.skill_waiting_activation = False
        
        # Extract area from screen
        x1, y1, x2, y2 = area_skills
        area = screen[y1:y2, x1:x2]
        
        # Get current skill index
        idx = self.skill_sequence_index % n
        skill_path = valid_skills[idx]
        
        # Find original skill index for this path
        original_idx = skill_index_map.get(skill_path)
        
        if original_idx is None:
            return
        
        # Load template (skill_path is already resolved)
        template = cv2.imread(skill_path, cv2.IMREAD_COLOR)
        if template is None:
            print(f'[SKILL-SEQUENCE] Could not load template from: {skill_path}')
            return
        
        # Check if area is large enough
        if area.shape[0] >= template.shape[0] and area.shape[1] >= template.shape[1]:
            # Template matching
            res = cv2.matchTemplate(area, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            
            if max_val > 0.7:
                # Skill found
                current_time = time.time()
                if current_time - self.ultimo_tiempo_skill >= 0.1:
                    key_input = self.get_skill_key(original_idx)
                    if key_input:
                        print(f'[SKILL-SEQUENCE] Skill {original_idx + 1} present, sending key: {key_input}')
                        input_handler.send_input(key_input)
                    else:
                        print(f'[SKILL-SEQUENCE] No key configured for skill {original_idx + 1}')
                    self.ultimo_tiempo_skill = current_time
                self.skill_waiting_activation = True
            else:
                # Skill not found
                if self.skill_waiting_activation:
                    # Skill disappeared after activation, advance to next
                    print(f'[SKILL-SEQUENCE] Skill {original_idx + 1} disappeared, advancing to next')
                    self.skill_sequence_index += 1
                    if self.skill_sequence_index >= n:
                        print('[SKILL-SEQUENCE] Last skill executed, resetting sequence')
                        self.skill_sequence_index = 0
                    self.skill_waiting_activation = False
        else:
            print(f'[SKILL-SEQUENCE] Template or area invalid for skill {original_idx + 1}')
