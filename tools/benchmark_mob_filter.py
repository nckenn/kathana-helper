#!/usr/bin/env python3
"""One-shot mob filter benchmark over fixture images (set PERF_LOG=1 for verbose)."""
import os
import sys
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import cv2
import config
import mob_filter


def main():
    fixtures_dir = os.path.join(REPO_ROOT, 'tests', 'fixtures')
    paths = [
        os.path.join(fixtures_dir, name)
        for name in os.listdir(fixtures_dir)
        if name.lower().endswith('.png')
    ] if os.path.isdir(fixtures_dir) else []

    if not paths:
        print('No fixture PNGs found in tests/fixtures')
        return 1

    config.mob_detection_enabled = True
    config.mob_templates = [
        {'id': 'bench', 'name': 'BenchMob', 'file': paths[0]},
    ]
    entry = config.mob_templates[0]
    prep = mob_filter._get_prepared_template(entry)
    if prep is None:
        bgr = cv2.imread(paths[0])
        mob_filter._template_cache[f'prep_{entry["id"]}'] = mob_filter.normalize_for_match(bgr)

    templates = [entry]
    total_ms = 0.0
    for path in paths:
        bgr = cv2.imread(path)
        if bgr is None:
            continue
        t0 = time.perf_counter()
        for _ in range(5):
            mob_filter.match_in_image(bgr, templates=templates)
        elapsed = (time.perf_counter() - t0) * 1000
        total_ms += elapsed
        if os.environ.get('PERF_LOG') == '1':
            print(f'{os.path.basename(path)}: {elapsed / 5:.2f} ms/match (x5)')

    print(f'Benchmark complete: {len(paths)} images, avg {total_ms / max(1, len(paths) * 5):.2f} ms/match')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
