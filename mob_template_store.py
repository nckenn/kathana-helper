"""Save and manage mob template images on disk."""
import os
import uuid
import cv2
import config


def ensure_dir():
    os.makedirs(config.MOB_TEMPLATES_DIR, exist_ok=True)


def resolve_path(filename):
    return os.path.join(config.MOB_TEMPLATES_DIR, filename)


def renumber_templates():
    """Keep display names Monster 1..N in list order."""
    for i, entry in enumerate(config.mob_templates, start=1):
        entry['name'] = f'Monster {i}'


def next_monster_name():
    """Next sequential label after renumbering (always len + 1)."""
    return f'Monster {len(config.mob_templates) + 1}'


def find_by_id(entry_id):
    for entry in config.mob_templates:
        if entry.get('id') == entry_id:
            return entry
    return None


def hp_max_filename(entry_id):
    return f'hpmax_{entry_id}.png'


def save_hp_max_sig(entry_id, sig_gray):
    """Save normalized max-HP signature grayscale image."""
    if sig_gray is None or sig_gray.size == 0:
        return None
    ensure_dir()
    filename = hp_max_filename(entry_id)
    path = resolve_path(filename)
    if not cv2.imwrite(path, sig_gray):
        print(f'[mob_templates] Failed to write HP signature: {path}')
        return None
    return filename


def load_hp_max_sig(entry):
    """Load max-HP signature grayscale for a template entry."""
    filename = entry.get('hp_max_file') or hp_max_filename(entry.get('id', ''))
    path = resolve_path(filename)
    if not os.path.isfile(path):
        return None
    return cv2.imread(path, cv2.IMREAD_GRAYSCALE)


def add_template(bgr_image, hp_profile=None):
    """Add a new template from a BGR capture. Returns the new entry dict, or None on failure."""
    ensure_dir()
    entry_id = uuid.uuid4().hex[:8]
    filename = f'mob_{entry_id}.png'
    path = resolve_path(filename)
    if not cv2.imwrite(path, bgr_image):
        print(f'[mob_templates] Failed to write template image: {path}')
        return None
    if not os.path.isfile(path):
        print(f'[mob_templates] Template image missing after write: {path}')
        return None
    entry = {'id': entry_id, 'name': next_monster_name(), 'file': filename}
    if hp_profile:
        sig = hp_profile.get('max_hp_sig')
        if sig is not None and sig.size > 0:
            hp_file = save_hp_max_sig(entry_id, sig)
            if hp_file:
                entry['hp_max_file'] = hp_file
        for key in ('max_hp', 'hp_digit_count', 'hp_text_span'):
            if key in hp_profile and hp_profile[key]:
                entry[key] = int(hp_profile[key])
    config.mob_templates.append(entry)
    renumber_templates()
    return config.mob_templates[-1]


def remove_template(entry_id):
    """Remove template entry and delete its image file."""
    remaining = []
    for entry in config.mob_templates:
        if entry.get('id') == entry_id:
            for fname in (entry.get('file', ''), entry.get('hp_max_file', ''), hp_max_filename(entry_id)):
                if not fname:
                    continue
                path = resolve_path(fname)
                if os.path.isfile(path):
                    try:
                        os.remove(path)
                    except OSError as exc:
                        print(f'[mob_templates] delete failed: {exc}')
        else:
            remaining.append(entry)
    config.mob_templates = remaining
    renumber_templates()


def load_template_bgr(entry):
    path = resolve_path(entry.get('file', ''))
    if not os.path.isfile(path):
        return None
    return cv2.imread(path, cv2.IMREAD_COLOR)


def template_file_exists(entry):
    path = resolve_path(entry.get('file', ''))
    return os.path.isfile(path)


def prune_missing_files():
    """Drop entries whose image files no longer exist (manual cleanup only)."""
    valid = []
    for entry in config.mob_templates:
        if template_file_exists(entry):
            valid.append(entry)
    config.mob_templates = valid


def sync_templates_after_load():
    """Recover orphan PNGs and renumber list order. Keeps JSON entries even if PNG is missing."""
    recover_untracked_files()
    renumber_templates()


def recover_untracked_files():
    """Add list entries for template PNGs on disk that are not in config yet."""
    ensure_dir()
    known_files = {entry.get('file') for entry in config.mob_templates}
    added = False
    try:
        names = sorted(os.listdir(config.MOB_TEMPLATES_DIR))
    except OSError:
        return
    for name in names:
        if not name.startswith('mob_') or not name.lower().endswith('.png'):
            continue
        if name in known_files:
            continue
        entry_id = name[4:-4]  # mob_<id>.png
        if not entry_id:
            continue
        config.mob_templates.append({'id': entry_id, 'name': '', 'file': name})
        known_files.add(name)
        added = True
    if added:
        renumber_templates()
