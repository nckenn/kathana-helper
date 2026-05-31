# Kathana Helper Lite

Minimal helper for Kathana: **skill intervals** (keys `1`–`0`, `F1`–`F10`) and **auto HP/MP pots** with in-game bar region capture.

## Features

- Connect to a game window
- Drag a rectangle on screen to set HP and MP bar regions
- Multiple HP thresholds (e.g. ≤70% → `0`, ≤40% → `3`)
- Single MP threshold + potion key
- **Actions:** Target (`E`), Attack (`R`), Loot (`F`) with enable + interval (seconds)
- Per-slot skill timers with enable + interval (seconds)
- Settings saved as `settings_lite.json` next to the app (or next to the `.exe`)

## Setup

```bash
cd kathana_helper_lite
pip install -r requirements.txt
python main.py
```

## Calibration

1. **Refresh** → pick your game window → **Connect**
2. **Pick HP bar** — drag over the red HP bar in-game
3. **Pick MP bar** — drag over the blue MP bar
4. **Test bars** — confirm HP/MP percentages look right
5. Set pot thresholds and keys; enable skills and intervals
6. **Save**, then **Start**

## Build executable

```bash
pip install -r requirements-dev.txt
pyinstaller kathana_helper_lite.spec
```

Output: `dist/kathana_helper_lite.exe`

Place `settings_lite.json` beside the exe (created automatically on first save).

## Tests

```bash
pip install pytest
pytest tests/
```
