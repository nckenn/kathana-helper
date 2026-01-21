"""
Download EasyOCR model files into ./easyocr_models so PyInstaller can bundle them.

Run:
  python tools/download_easyocr_models.py
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    try:
        import easyocr
    except Exception as e:
        print(f"[EasyOCR Models] EasyOCR not installed: {e}")
        print("Run: pip install -r requirements.txt")
        return 1

    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "easyocr_models")
    os.makedirs(out_dir, exist_ok=True)

    print(f"[EasyOCR Models] Downloading into: {out_dir}")
    print("[EasyOCR Models] This may take a few minutes on first run...")

    # Force CPU to avoid any CUDA surprises on build machines.
    # download_enabled=True ensures models are fetched into out_dir.
    try:
        easyocr.Reader(
            ["en"],
            gpu=False,
            verbose=False,
            model_storage_directory=out_dir,
            user_network_directory=out_dir,
            download_enabled=True,
        )
    except TypeError:
        # Older EasyOCR: fewer kwargs available. Still try to at least trigger downloads.
        easyocr.Reader(["en"], gpu=False, verbose=False)

    # Quick sanity check: list .pth files
    pth_files = [f for f in os.listdir(out_dir) if f.lower().endswith(".pth")]
    if pth_files:
        print("[EasyOCR Models] Download complete. Found:")
        for f in sorted(pth_files):
            print(f"  - {f}")
        return 0

    print("[EasyOCR Models] Done, but no .pth files were found in easyocr_models/.")
    print("If your network blocks downloads, try running behind a different network or proxy settings.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

