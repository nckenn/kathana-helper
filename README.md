# Kathana Helper

Kathana Helper is a Windows automation assistant for the game, built with Python,
CustomTkinter, and OpenCV. It detects the player's HP/MP bars, the enemy target
UI, and skill/buff icons directly from the game window (via screen capture and
computer vision — **no OCR**) to automate combat, potions, buffs, looting, and
more.

**Current version:** `3.1.2`

## File Structure

```
kathana_helper/
├── main.py                      # Entry point: license gate, then launch the GUI
├── config.py                    # Global state, defaults, intervals, feature flags, version
├── gui.py                       # Full CustomTkinter GUI (tabs, controls, dialogs)
│
├── window_utils.py              # Win32 window list/connect + screen capture (BitBlt/PrintWindow)
├── input_handler.py             # Send keyboard/mouse input to the game window
├── frame_cache.py               # Shared per-window frame cache (TTL + invalidation)
├── capture_regions.py           # Union capture rectangles for the shared frame cache
├── template_cache.py            # Disk image cache for buff/skill icon templates
│
├── auto_attack.py               # Enemy HP/name detection, auto-target/attack, smart loot
├── mob_filter.py                # Mob whitelist via OpenCV template matching on the name/level bar
├── mob_template_store.py        # Save/load/delete mob template images + max-HP signatures
├── hp_number_reader.py          # Enemy target-strip geometry + max-HP digit signatures (elite skip)
├── loot_helpers.py              # Smart-loot lockout/cooldown logic
│
├── auto_pots.py                 # Auto HP/MP potion usage from bar-fill thresholds
├── auto_repair.py               # CV detection of the "about to break" warning; presses repair key
├── auto_unstuck.py              # Detects stagnant enemy HP and runs an unstuck movement sequence
├── auto_rotate.py               # Periodic camera rotation for better nameplate visibility
├── buffs_manager.py             # Up to 8 buffs: detect active icons, press key when missing
├── skill_sequence_manager.py    # Up to 8 skills fired in sequence while an enemy is engaged
├── skill_bar_actions.py         # Template match built-in skill-bar icons (hammer/assist)
│
├── bot_logic.py                 # Main bot loop: skills, pots, repair, unstuck, rotate, loot
├── calibration.py               # Auto-detect HP/MP bars, skill area, enemy UI, chat area
├── bar_reader.py                # Read player HP/MP fill % from calibrated regions
├── bar_color_calibration.py     # Per-bar color profiles (snap/fit/preview)
├── ui_bar_detection.py          # HSV masks + band detection for HP/MP/enemy bars
├── region_helpers.py            # Region preflight, labels, bot-start readiness checks
├── region_picker.py             # Fullscreen drag-to-select overlay (legacy path)
│
├── settings_manager.py          # JSON profile save/load
├── license_manager.py           # RSA license validation, machine ID, encrypted storage
├── state.py                     # Lightweight bot/combat state dataclasses
├── match_utils.py               # Shared template-match-with-margin helper
├── debug_utils.py / debug_io.py # Debug mode + gated debug-image output
├── logger.py                    # Lightweight logging wrapper
│
├── ui/                          # GUI popups/helpers extracted from gui.py
│   ├── region_editor.py         # Visual Region Editor (draw/drag regions, Auto Calibrate)
│   ├── settings_overlays.py     # Bridge GUI widgets <-> config for save/load
│   ├── keybind_dialogs.py       # Modal key-capture dialogs
│   └── window_helpers.py        # Bring game/GUI window to front
│
├── tools/                       # Admin/dev utilities
│   ├── generate_license.py      # Generate RSA key pair + signed license keys
│   ├── benchmark_mob_filter.py  # Benchmark the mob filter over test fixtures
│   └── download_easyocr_models.py  # Legacy stub (EasyOCR was removed)
│
├── kathana_helper_lite/         # Standalone, license-free "lite" build (see below)
├── tests/                       # Pytest suite
├── requirements.txt             # Python dependencies
└── kathana_helper.spec          # PyInstaller build spec
```

## Installation

### Install Dependencies
```bash
pip install -r requirements.txt
```

Dependencies:
- `customtkinter` — GUI framework
- `pywin32`, `pywinauto` — Windows API / window automation
- `pydirectinput`, `pyautogui` — keyboard/mouse input
- `opencv-python`, `Pillow`, `numpy` — image processing / computer vision
- `cryptography` — license key signing/verification

## Usage

### Running the Bot
```bash
python main.py
```

### Building with PyInstaller

#### Using the spec file (Recommended)
```bash
pyinstaller kathana_helper.spec
```

#### Using command line
```bash
pyinstaller --name "Kathana Helper" --onefile --windowed --hidden-import=win32api --hidden-import=win32con --hidden-import=win32gui --hidden-import=win32ui --hidden-import=pydirectinput --hidden-import=pyautogui --hidden-import=customtkinter main.py
```

The executable will be created in the `dist` folder.

## Getting Started

1. **Connect** — pick the game window from the dropdown and click **Connect**
   (use **Refresh** to rescan open windows).
2. **Regions** — click **Regions** to open the visual **Region Editor**, then set
   up the on-screen regions the bot reads from (see below). HP Bar and MP Bar are
   required to start.
3. **Configure** — enable the features you want in the **Settings** tab and other
   tabs.
4. **Start** — click **Start** to run the bot. Click again to stop.
5. **Save / Load** — use **Save**, **Save As…**, and **Load…** to manage profiles.

### Region Editor (primary setup)

The Region Editor freezes a capture of the game window and lets you draw and
fine-tune the regions the bot uses:

- **HP Bar** *(required)* and **MP Bar** *(required)*
- **Enemy Name** — used by the mob filter
- **Enemy HP** — target HP bar
- **System Message** — used by auto repair
- **Skill Bar** — used by the skill sequence
- **Buff Strip** — used by the buffs system

Tools: draggable/resizable regions, zoom (+/−, Fit, 100%, Ctrl+wheel), arrow-key
nudge, Delete to clear, per-bar **color calibration**, and **Auto Calibrate**
(auto-detects HP/MP and other UI when visible). Legacy auto-calibration still
powers Auto Calibrate under the hood, but the standalone Calibrate button has been
replaced by the Region Editor.

## GUI Overview

The window has a top bar (window selection, status, Start/Regions/Save controls)
and the following tabs:

- **Status** — live HP / MP / Enemy HP bars, current enemy name, unstuck
  countdown, and license info.
- **Settings** — the main control panel:
  - *Combat & Utility:* Auto Attack, Auto Loot (+ loot lockout seconds), Mage
    mode, Auto Repair (+ repair key), Assist Mode (+ assist key).
  - *Pots & Unstuck:* Auto HP (multi-threshold), Auto MP (% + key), Auto Unstuck
    (+ timeout), Auto Rotate Camera (+ interval).
  - *Mob Filter:* enable, Skip elite mobs, self-target key, "buffs only when not
    fighting", and Learn / Remove / Test match / Compare with a template list and
    preview.
- **Skill Sequence** — 8 slots (enable, skill icon, hotkey, bypass-if-missing).
- **Buffs** — 8 slots (enable, buff icon, hotkey).
- **Skill Interval** — per-key intervals for `1`–`9`, `0`, and `F1`–`F10`.
- **Mouse Clicker** — interval clicking at the cursor or fixed coordinates.

## Features

### Combat
- **Auto Attack** — automatic enemy targeting and attacking.
- **Mob Filter** — target only whitelisted mobs, matched by **OpenCV template
  matching** on the enemy name/level bar (visual shape matching, **no OCR**).
  - **Learn** a mob to capture its template (stored per profile under
    `mob_templates/<profile>/`).
  - **Skip elite mobs** — an elite shares the name but has a higher max HP; the
    bot compares the max-HP digit signature and skips it.
  - **Self-target** — presses a self-target key (default `` ` ``) before
    retargeting so heals/buffs land on you, not the mob.
  - **Test match** / **Compare** tools for debugging matches.
- **Smart Loot** — after a kill, presses the loot key with a short lockout so
  retargeting waits for looting to finish.
- **Mage mode** — skips the basic attack after targeting (for casters).
- **Auto Unstuck** — detects stagnant enemy HP and runs a movement sequence to get
  unstuck.
- **Auto Rotate Camera** — periodically rotates the camera to keep nameplates
  visible.

### Survival & Utility
- **Auto Pots** — automatic HP/MP potion usage based on bar-fill thresholds
  (HP supports multiple thresholds).
- **Auto Repair** — detects the "about to break" warning via CV and presses the
  repair key (requires the System Message region).

### Skills & Buffs
- **Skill Sequence** — up to 8 skills fired in order while an enemy is engaged;
  advances when the current skill icon disappears and resets on kill/target
  change (icons matched in the Skill Bar region).
- **Buffs** — up to 8 buffs; detects whether each buff icon is active in the Buff
  Strip and presses the key when it's missing. Optionally held while in combat
  (buffs only when not fighting).
- **Skill Interval** — fire keys `1`–`0` and `F1`–`F10` on independent timed
  intervals.

### Party & Input
- **Assist Only Mode** — party support mode: presses a configurable **assist
  hotkey** (default F9) on an interval to assist the party leader's target. While
  active it disables Auto Attack, Mob Filter, and Auto Unstuck; those previous
  settings are restored when Assist Only is turned off.
- **Mouse Clicker** — automated clicking at a set interval, either at the current
  cursor position or fixed coordinates.

### Profiles & Performance
- **Profiles** — save/load full configurations (`bot_settings.json` by default, or
  named profiles via Save As / Load). Mob templates are scoped per profile.
- **Shared frame cache** — a single per-window capture is reused across detectors
  each tick for lower CPU use, with a Low CPU mode and an idle mode that slows
  scanning when no enemy is present.

## Kathana Helper Lite

`kathana_helper_lite/` is a standalone, **license-free** subset focused on skill
intervals and automatic HP/MP potions. Differences from the full app:

| | Full (`kathana_helper`) | Lite (`kathana_helper_lite`) |
|--|-------------------------|------------------------------|
| License | Required | None |
| GUI | 7 tabs + Region Editor | Single screen + drag region picker |
| Combat | Full auto-attack, smart loot, unstuck, rotate, repair, assist | Interval-based Target/Attack/Loot |
| Skills | Skill Interval + Skill Sequence + Buffs | Skill timers only |
| Settings file | `bot_settings.json` | `settings_lite.json` |
| Build | `kathana_helper.spec` | `kathana_helper_lite.spec` |

Run it with `python kathana_helper_lite/main.py`, or build it with
`pyinstaller kathana_helper_lite/kathana_helper_lite.spec`.

## License System

Kathana Helper uses a signed license key system to control access to the application. License keys are cryptographically signed using RSA-2048 to prevent forgery.

### Generating License Keys

**Note:** The private key (`private_key.pem`) has **no password** - it is stored unencrypted. Keep it secure and never distribute it.

#### First Time Setup (Generate Key Pair)

Before generating license keys, you need to create a key pair:

```bash
python tools/generate_license.py --generate-keys
```

This will create:
- `private_key.pem` - **KEEP THIS SECRET!** Never distribute this file.
- `public_key.pem` - This key is embedded in the application for verification.

#### Generate a License Key

Once you have the key pair, you can generate license keys for users:

```bash
# Basic license (365 days, no machine binding)
python tools/generate_license.py --user "John Doe" --days 365

# License with custom validity period
python tools/generate_license.py --user "Jane Smith" --days 30

# License bound to a specific machine (optional)
# First, get the user's Machine ID from the license dialog in the app
# Then generate the license with that Machine ID:
python tools/generate_license.py --user "Bob Wilson" --days 365 --machine-id "abc123def456" --machine-bound

# Save license key to a file
python tools/generate_license.py --user "Alice Brown" --days 365 --output license_key.txt
```

#### Command Line Options

- `--generate-keys`: Generate a new RSA key pair (first time setup)
- `--private-key PATH`: Specify path to private key file (default: `private_key.pem`)
- `--user NAME`: License holder name
- `--days N`: Number of days license is valid (default: 365)
- `--machine-id ID`: Optional machine ID to bind license to
- `--machine-bound`: Enable machine binding (license only works on specified machine)
- `--output FILE`: Save license key to a file

### License Activation

When users run the application:
1. If no valid license is found, a license entry dialog will appear
2. The dialog displays the user's **Machine ID** (for machine-bound licenses)
   - Users can copy their Machine ID to provide it to the license issuer
   - The Machine ID is unique to each computer
3. Users can enter their license key to activate the application
4. License status can be viewed and managed in the Settings tab under "License Management"
5. Users can change/update their license key at any time through the Settings tab

**For Machine-Bound Licenses:**
- The license dialog shows the user's Machine ID
- Users should copy this ID and provide it when requesting a machine-bound license
- The license issuer will use this Machine ID when generating the license key

### Security Notes

- The private key is stored **without encryption** (no password required)
- Keep `private_key.pem` secure and never commit it to version control
- The public key is embedded in the application and cannot be changed without recompiling
- License keys are cryptographically signed and cannot be forged without the private key
