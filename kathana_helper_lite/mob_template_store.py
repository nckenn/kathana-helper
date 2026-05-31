"""Save and manage mob template images on disk."""
import os
import uuid
import cv2
import config


def ensure_dir():
    os.makedirs(config.MOB_TEMPLATES_DIR, exist_ok=True)


def resolve_path(filename):
    return os.path.join(config.MOB_TEMPLATES_DIR, filename)


def next_monster_name():
    used = {entry.get('name', '') for entry in config.mob_templates}
    n = 1
    while True:
        name = f'Monster {n}'
        if name not in used:
            return name
        n += 1


def add_template(bgr_image):
    """Add a new template from a BGR capture. Returns the new entry dict."""
    ensure_dir()
    entry_id = uuid.uuid4().hex[:8]
    filename = f'mob_{entry_id}.png'
    path = resolve_path(filename)
    cv2.imwrite(path, bgr_image)
    entry = {'id': entry_id, 'name': next_monster_name(), 'file': filename}
    config.mob_templates.append(entry)
    return entry


def remove_template(entry_id):
    """Remove template entry and delete its image file."""
    remaining = []
    for entry in config.mob_templates:
        if entry.get('id') == entry_id:
            path = resolve_path(entry.get('file', ''))
            if os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError as exc:
                    print(f'[mob_templates] delete failed: {exc}')
        else:
            remaining.append(entry)
    config.mob_templates = remaining


def load_template_bgr(entry):
    path = resolve_path(entry.get('file', ''))
    if not os.path.isfile(path):
        return None
    return cv2.imread(path, cv2.IMREAD_COLOR)


def prune_missing_files():
    """Drop entries whose image files no longer exist."""
    valid = []
    for entry in config.mob_templates:
        path = resolve_path(entry.get('file', ''))
        if os.path.isfile(path):
            valid.append(entry)
    config.mob_templates = valid
