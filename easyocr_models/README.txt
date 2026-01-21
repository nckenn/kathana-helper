Put EasyOCR model files here so the app can run OCR completely offline.

Required for English OCR (typical EasyOCR defaults):
- craft_mlt_25k.pth
- english_g2.pth (or latin_g2.pth depending on your EasyOCR version)

How to populate automatically (recommended):
1) Install deps: pip install -r requirements.txt
2) Run: python tools/download_easyocr_models.py
3) Build: pyinstaller kathana_helper.spec

If this folder is present in the built app, `ocr_utils.py` will force EasyOCR to load models
from here and will disable network downloads (avoids SSL/cert issues on user machines).

