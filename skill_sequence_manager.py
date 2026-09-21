"""
Skill Sequence Manager - Handles automatic skill sequence execution
"""
import time
import os
import config
import input_handler
import template_cache
import match_utils
import logger
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.error('OpenCV not available. Install with: pip install opencv-python', 'CV2')


class SkillSequenceManager:
    # Safety cap: how many presses to spend on a ready skill before assuming it
    # cast (or can't be cast right now) and moving on, so the rotation never
    # stalls on a skill whose icon lingers (~MAX_CAST_ATTEMPTS * 0.1s).
    MAX_CAST_ATTEMPTS = 10

    def __init__(self, num_skills=8):
        self.skills = [None] * num_skills
        self.skill_sequence_index = 0
        self.skill_waiting_activation = False
        self.last_skill_count = 0
        self.ultimo_tiempo_skill = 0
        self.ui_reference = None
        self.enemy_found_previous = False
        self._skills_loc_cache = {}
        self._cast_attempts = 0

    def set_skill(self, idx, image_path):
        if 0 <= idx < len(self.skills):
            self.skills[idx] = image_path
            logger.info(f'Skill {idx + 1} set to: {image_path}', 'SkillSequence')

    def clear_skill(self, idx):
        if 0 <= idx < len(self.skills):
            self.skills[idx] = None
            logger.info(f'Skill {idx + 1} cleared', 'SkillSequence')

    def set_ui_reference(self, ui):
        self.ui_reference = ui

    def reset_sequence(self):
        self.skill_sequence_index = 0
        self.skill_waiting_activation = False
        self.enemy_found_previous = False
        self._cast_attempts = 0
        logger.info('Sequence reset', 'SkillSequence')

    def _park(self, idx, n):
        """Point the rotation at slot `idx` and clear per-skill cast state."""
        self.skill_sequence_index = idx % n
        self.skill_waiting_activation = False
        self._cast_attempts = 0

    def _advance(self, n):
        """Move to the next slot in the rotation and clear per-skill state."""
        self._park(self.skill_sequence_index + 1, n)

    def _match_skill(self, area_img, template_img, cache_key, threshold=None):
        """Return (found, loc, confidence) for one skill icon inside the skill-bar crop.

        Uses a cached last-known location to search a small ROI first for speed,
        falling back to a full-area search.
        """
        if threshold is None:
            threshold = float(getattr(config, 'skill_match_threshold', 0.7))
        margin = float(getattr(config, 'template_match_margin', 0.05))
        if area_img is None or template_img is None or area_img.size == 0:
            return False, None, 0.0
        if area_img.shape[0] < template_img.shape[0] or area_img.shape[1] < template_img.shape[1]:
            return False, None, 0.0

        hint = self._skills_loc_cache.get(cache_key)
        if hint is not None:
            hx, hy = hint
            pad = 30
            x0 = max(0, hx - pad)
            y0 = max(0, hy - pad)
            x1r = min(area_img.shape[1], hx + template_img.shape[1] + pad)
            y1r = min(area_img.shape[0], hy + template_img.shape[0] + pad)
            roi = area_img[y0:y1r, x0:x1r]
            if roi.shape[0] >= template_img.shape[0] and roi.shape[1] >= template_img.shape[1]:
                matched, conf, max_loc = match_utils.template_match_with_margin(
                    roi, template_img, threshold, margin,
                )
                if matched and max_loc is not None:
                    loc = (x0 + max_loc[0], y0 + max_loc[1])
                    self._skills_loc_cache[cache_key] = loc
                    return True, loc, conf

        matched, conf, max_loc = match_utils.template_match_with_margin(
            area_img, template_img, threshold, margin,
        )
        if matched and max_loc is not None:
            self._skills_loc_cache[cache_key] = max_loc
            return True, max_loc, conf
        return False, None, conf

    def execute_skill_sequence(self, hwnd, screen, area_skills, enemy_found, run_active=True):
        """Cast the enabled skills as a strict rotation in slot order.

        The rotation walks the enabled skills in slot order (1 -> 2 -> 3 -> ...
        -> back to 1) and does not cast a later skill before an earlier one. Each
        cycle it looks at the current slot:

        * If that skill's icon is present (off cooldown), it presses the key and
          waits for the icon to disappear (cast confirmed) before advancing.
        * If that skill's icon is missing (on cooldown), it waits there, so the
          order is never broken -- unless that skill has "Skip if on cooldown"
          ticked, in which case the rotation moves past it for this lap and picks
          it up again on the next one.

        Ticking "Skip if on cooldown" for every slot gives the "cast whatever is
        ready" behaviour; leaving it off everywhere gives a literal 1-2-3 opener.

        A safety cap (MAX_CAST_ATTEMPTS) advances past a ready skill that never
        casts (e.g. not enough resources) so it can never stall.
        """
        if not run_active or not CV2_AVAILABLE:
            return

        import mob_filter
        if mob_filter.is_active():
            if not hwnd or not mob_filter.should_allow_combat(hwnd):
                return

        if not area_skills or not isinstance(area_skills, (tuple, list)) or len(area_skills) != 4:
            return

        if screen is None:
            import frame_cache
            screen = frame_cache.get_frame(hwnd, config.calibrator)
        if screen is None:
            return

        # Ordered list of castable skills; list order is the rotation order.
        valid_skills = []  # (original_idx, resolved_path)
        for idx in range(len(self.skills)):
            cfg = config.skill_sequence_config[idx]
            key = (cfg.get('key') or '').strip()
            if self.skills[idx] and cfg.get('enabled') and key:
                resolved_path = config.resolve_resource_path(self.skills[idx])
                if resolved_path and os.path.exists(resolved_path):
                    valid_skills.append((idx, resolved_path))

        n = len(valid_skills)
        if n == 0:
            return

        # Restart the rotation when the enemy changes so we always open at slot 1.
        if enemy_found and not self.enemy_found_previous:
            self.skill_sequence_index = 0
            self.skill_waiting_activation = False
            self._cast_attempts = 0
        self.enemy_found_previous = enemy_found
        if not enemy_found:
            return

        # Keep the index valid if the number of enabled skills changed.
        if self.last_skill_count != n:
            self.skill_sequence_index = 0
            self.skill_waiting_activation = False
            self._cast_attempts = 0
            self.last_skill_count = n

        x1, y1, x2, y2 = area_skills
        import frame_cache
        area = frame_cache.crop_rect(screen, x1, y1, x2, y2, frame_cache.get_origin())
        if area is None or area.size == 0:
            return

        # Throttle: bound scanning + pressing to ~10x/sec.
        current_time = time.time()
        if current_time - self.ultimo_tiempo_skill < 0.1:
            return
        self.ultimo_tiempo_skill = current_time

        self._run_rotation(valid_skills, n, area)

    def _press_skill(self, original_idx):
        hotkey = (config.skill_sequence_config[original_idx].get('key') or '').strip()
        if hotkey:
            logger.info(f'Skill {original_idx + 1} ready; pressing key {hotkey!r}', 'SkillSequence')
            input_handler.send_input(hotkey)

    @staticmethod
    def _skips_cooldown(original_idx):
        """True when this slot is allowed to be passed over while on cooldown."""
        return bool(config.skill_sequence_config[original_idx].get('bypass', False))

    def _run_rotation(self, valid_skills, n, area):
        """Cast in strict slot order, passing over only slots that opted in.

        Scans forward from the current slot within this tick so a run of
        skip-enabled skills on cooldown does not cost a tick each. `start` is the
        scan cursor and stays fixed for the tick; the rotation pointer
        (`skill_sequence_index`) is moved separately as slots are resolved. It
        stops at the first slot it can act on, so at most one key is pressed
        per tick.
        """
        start = self.skill_sequence_index % n
        # Whether the previous tick pressed the slot we are starting from; only
        # that slot's icon going dark means a cast landed.
        awaiting_cast = self.skill_waiting_activation

        for step in range(n):
            idx = (start + step) % n
            original_idx, skill_path = valid_skills[idx]

            template = template_cache.get_template(skill_path, cv2.IMREAD_COLOR)
            if template is None:
                logger.warn(f'Could not load template for skill '
                            f'{original_idx + 1}; skipping', 'SkillSequence')
                self._park(idx + 1, n)
                continue
            if area.shape[0] < template.shape[0] or area.shape[1] < template.shape[1]:
                self._park(idx + 1, n)
                continue

            found, _loc, _conf = self._match_skill(area, template, skill_path)

            if found:
                # Ready: press it and hold here until its icon goes dark.
                if idx != self.skill_sequence_index:
                    self._park(idx, n)
                self._press_skill(original_idx)
                self.skill_waiting_activation = True
                self._cast_attempts += 1
                # Give up on a ready skill that won't cast so we never stall here.
                if self._cast_attempts >= self.MAX_CAST_ATTEMPTS:
                    logger.warn(f'Skill {original_idx + 1} did not cast after '
                                f'{self._cast_attempts} tries; advancing', 'SkillSequence')
                    self._advance(n)
                return

            if step == 0 and awaiting_cast:
                # We pressed it and its icon is now gone -> cast confirmed.
                self._park(idx + 1, n)
                continue

            if self._skips_cooldown(original_idx):
                # Opted out of the wait: move past it for this lap.
                self._park(idx + 1, n)
                continue

            # On cooldown and not skippable -> hold the order and wait here.
            if idx != self.skill_sequence_index:
                self._park(idx, n)
            return
