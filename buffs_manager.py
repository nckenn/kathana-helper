"""
Buffs Manager - Handles automatic buff activation
"""
import time
import os
import config
import input_handler
import debug_io
import debug_utils
import template_cache
import match_utils
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
        self._inactive_streak = [0] * num_buffs
        self._pending_activation_until = [0.0] * num_buffs
        self.ui_reference = None
        # Cache last seen icon positions in the skills area to avoid full-bar scans.
        # key: resolved template path -> (x, y) in area_skills coordinates (top-left match)
        self._skills_loc_cache = {}
    
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
    
    def _enabled_buff_indices(self):
        indices = []
        for idx, image_path in enumerate(self.buffs):
            if not image_path or not config.buffs_config[idx]['enabled']:
                continue
            if not (config.buffs_config[idx].get('key') or '').strip():
                continue
            indices.append(idx)
        return indices

    def _buff_active_in_area(self, template, area_buffs_activos):
        """Return True if buff template is visible in the active-buffs strip."""
        if (area_buffs_activos is None or area_buffs_activos.size == 0
                or template is None):
            return False
        if (area_buffs_activos.shape[0] < template.shape[0]
                or area_buffs_activos.shape[1] < template.shape[1]):
            return False
        threshold = float(getattr(config, 'buff_match_threshold', 0.7))
        margin = float(getattr(config, 'template_match_margin', 0.05))
        matched, _, _ = match_utils.template_match_with_margin(
            area_buffs_activos, template, threshold, margin,
        )
        return matched

    def _buff_template_for_index(self, idx):
        image_path = self.buffs[idx]
        if not image_path:
            return None, None
        resolved_path = config.resolve_resource_path(image_path)
        if not resolved_path:
            return None, None
        template = template_cache.get_template(resolved_path, cv2.IMREAD_COLOR)
        return resolved_path, template

    def all_buffs_active(self, area_buffs_activos, now=None):
        """True when every enabled buff icon is visible in the active strip."""
        if now is None:
            now = time.time()
        for idx in self._enabled_buff_indices():
            _, template = self._buff_template_for_index(idx)
            if template is None:
                continue
            if not self._buff_active_in_area(template, area_buffs_activos):
                grace_until = self._pending_activation_until[idx]
                if grace_until and now < grace_until:
                    continue
                return False
        return bool(self._enabled_buff_indices())

    def needs_buff_refresh(self, area_buffs_activos, now=None):
        """True while any buff is missing or still in post-cast grace."""
        return not self.all_buffs_active(area_buffs_activos, now=now)

    def begin_buffing_session(self):
        if config.is_buffing:
            return
        if config.mob_detection_enabled:
            import mob_filter
            mob_filter.focus_self_target()
        config.is_buffing = True
        config.buffing_start_time = time.time()
        print('[Buffs] Buff session started — holding retarget until buffs are active')

    def end_buffing_session(self):
        if not config.is_buffing:
            return
        config.is_buffing = False
        print('[Buffs] Buff session finished — resuming retarget')

    def _retarget_after_buffs(self):
        """Resume mob targeting after a buff session (whitelisted mobs deferred until now)."""
        if not config.auto_attack_enabled or config.assist_only_enabled:
            return
        if config.is_looting:
            return
        import auto_attack
        auto_attack._auto_target_manager.reset_search_timer()
        auto_attack._auto_target_manager.try_auto_target("buffs finished")

    def manage_buffing_session(self, area_buffs_activos):
        """Start/hold/end buff session; returns True while combat retarget should wait."""
        now = time.time()
        was_buffing = config.is_buffing
        if not self._enabled_buff_indices():
            self.end_buffing_session()
            return False

        if config.is_buffing:
            timeout = float(getattr(config, 'BUFFING_SESSION_TIMEOUT', 45.0))
            if now - config.buffing_start_time > timeout:
                print('[Buffs] Buff session timed out — resuming retarget')
                self.end_buffing_session()
                self._retarget_after_buffs()
                return False

        if self.needs_buff_refresh(area_buffs_activos, now=now):
            self.begin_buffing_session()
            return True

        self.end_buffing_session()
        if was_buffing:
            self._retarget_after_buffs()
        return False

    def _match_in_skills_with_hint(self, area_skills, template, resolved_path, threshold=None):
        """
        Try to match template in a small ROI around the cached position first,
        then fall back to full-area template matching.
        Returns (found: bool, loc: (x,y) top-left in area_skills coords, confidence: float).
        """
        if threshold is None:
            threshold = float(getattr(config, 'buff_match_threshold', 0.7))
        margin = float(getattr(config, 'template_match_margin', 0.05))
        if area_skills is None or template is None or area_skills.size == 0:
            return False, None, 0.0
        if area_skills.shape[0] < template.shape[0] or area_skills.shape[1] < template.shape[1]:
            return False, None, 0.0

        hint = self._skills_loc_cache.get(resolved_path)
        if hint is not None:
            hx, hy = hint
            pad = 30
            x0 = max(0, hx - pad)
            y0 = max(0, hy - pad)
            x1 = min(area_skills.shape[1], hx + template.shape[1] + pad)
            y1 = min(area_skills.shape[0], hy + template.shape[0] + pad)

            roi = area_skills[y0:y1, x0:x1]
            if roi.shape[0] >= template.shape[0] and roi.shape[1] >= template.shape[1]:
                matched, conf, max_loc = match_utils.template_match_with_margin(
                    roi, template, threshold, margin,
                )
                if matched and max_loc is not None:
                    loc = (x0 + max_loc[0], y0 + max_loc[1])
                    self._skills_loc_cache[resolved_path] = loc
                    return True, loc, conf

        matched, conf, max_loc = match_utils.template_match_with_margin(
            area_skills, template, threshold, margin,
        )
        if matched and max_loc is not None:
            self._skills_loc_cache[resolved_path] = max_loc
            return True, max_loc, conf
        return False, None, conf

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

            # If no key assigned, do nothing (no matching, no clicking).
            key = (config.buffs_config[idx].get('key') or '').strip()
            if not key:
                continue
            
            debug_utils.debug_print(f'Processing buff {idx + 1}: {image_path}', 'BuffsManager')
            # Resolve relative path before loading template
            resolved_path = config.resolve_resource_path(image_path)
            if not resolved_path:
                debug_utils.debug_print(f'Could not resolve path for buff {idx + 1}: {image_path}', 'BuffsManager')
                continue
            
            template = template_cache.get_template(resolved_path, cv2.IMREAD_COLOR)
            if template is None:
                debug_utils.debug_print(f'Could not load template for buff {idx + 1}', 'BuffsManager')
                continue
            
            debug_utils.debug_print(f'Template loaded for buff {idx + 1}, dimensions: {template.shape}', 'BuffsManager')
            
            found_in_buffs = self._buff_active_in_area(template, area_buffs_activos)
            if found_in_buffs:
                self._inactive_streak[idx] = 0
                self._pending_activation_until[idx] = 0.0
                debug_utils.debug_print(f'Buff {idx + 1} already active', 'BuffsManager')
                continue

            debug_utils.debug_print(
                f'Buff {idx + 1} not seen in active strip',
                'BuffsManager',
            )

            self._inactive_streak[idx] += 1
            miss_required = int(getattr(config, 'buff_inactive_miss_required', 2))
            if self._inactive_streak[idx] < miss_required:
                debug_utils.debug_print(
                    f'Buff {idx + 1} miss {self._inactive_streak[idx]}/{miss_required} — waiting',
                    'BuffsManager',
                )
                continue

            grace_until = self._pending_activation_until[idx]
            if grace_until and now < grace_until:
                debug_utils.debug_print(
                    f'Buff {idx + 1} activation grace until {grace_until:.1f}',
                    'BuffsManager',
                )
                continue

            press_cooldown = float(getattr(config, 'buff_press_cooldown', 4.0))
            if now - self.last_click_times[idx] < press_cooldown:
                continue

            grace_s = float(getattr(config, 'buff_activation_grace_seconds', 4.0))
            debug_utils.debug_print(f'Buff {idx + 1} not active, pressing key {key!r}', 'BuffsManager')
            print(f'[BUFF] Buff {idx + 1} not active, pressing key {key!r}')
            input_handler.send_input(key)
            self.last_click_times[idx] = now
            self._pending_activation_until[idx] = now + grace_s
            self._inactive_streak[idx] = 0
