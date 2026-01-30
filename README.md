# Kathana Helper

## File Structure

```
kathana_helper/
├── __init__.py                  # Package initialization
├── main.py                      # Entry point - run this to start the bot
├── config.py                    # Global variables and configuration
├── window_utils.py              # Window capture and management
├── input_handler.py             # Input sending (keys, mouse)
├── auto_attack.py               # Auto-attack system: enemy HP bar detection, name detection, and mob filtering
├── ocr_utils.py                 # OCR functions for text reading
├── auto_repair.py               # Auto repair functionality
├── auto_unstuck.py              # Auto unstuck functionality
├── auto_pots.py                 # Auto potion usage
├── bot_logic.py                 # Main bot loop and skill checking
├── calibration.py               # HP/MP bar calibration and skill area detection
├── settings_manager.py          # Settings save/load
├── buffs_manager.py             # Buffs management and activation
├── skill_sequence_manager.py    # Skill sequence execution
├── license_manager.py           # License key validation and management
└── gui.py                       # GUI class (CustomTkinter)
```

## Installation

### Install Dependencies
```bash
pip install -r requirements.txt
```

## Usage

### Running the Bot
```bash
python main.py
```

### Building with PyInstaller

#### Using the spec file (Recommended)
```bash
python tools/download_easyocr_models.py
pyinstaller kathana_helper.spec
```

#### Using command line
```bash
pyinstaller --name "Kathana Helper" --onefile --windowed --hidden-import=win32api --hidden-import=win32con --hidden-import=win32gui --hidden-import=win32ui --hidden-import=pydirectinput --hidden-import=pyautogui --hidden-import=customtkinter --hidden-import=easyocr main.py
```

The executable will be created in the `dist` folder.

## Module Descriptions

- **config.py**: All global variables, constants, and configuration
- **window_utils.py**: Window capture, connection, and management
- **input_handler.py**: Keyboard and mouse input functions (reusable across all features)
- **auto_attack.py**: Auto-attack system including enemy HP bar detection, name detection using OCR, and mob filtering
- **ocr_utils.py**: EasyOCR integration for text reading
- **auto_repair.py**: Damage monitoring and auto repair
- **auto_unstuck.py**: Stuck detection and unstuck mechanism
- **auto_pots.py**: Automatic potion usage based on HP/MP thresholds
- **bot_logic.py**: Main bot loop, skill checking, and state management
- **calibration.py**: HP/MP bar calibration and skill area detection
- **settings_manager.py**: JSON-based settings persistence
- **buffs_manager.py**: Automatic buff activation system (up to 8 buffs)
- **skill_sequence_manager.py**: Skill sequence execution system (up to 8 skills in sequence)
- **gui.py**: Complete GUI interface using CustomTkinter with tabs for Status, Settings, Skill Sequence, Skill Interval, Buffs, and Mouse Clicker

## Features

### Core Features
- **Auto Attack**: Automatic enemy targeting and attack with mob filtering
- **Auto Pots**: Automatic HP/MP potion usage based on thresholds
- **Auto Repair**: Automatic equipment repair when damaged
- **Auto Unstuck**: Detects and resolves stuck situations by changing targets
- **Assist Only**: Party support mode - assists party leader's target by clicking assist button
- **Skill Interval**: Configurable skill rotation with custom intervals (1-8 and F1-F10 keys)
- **Mouse Clicker**: Automated mouse clicking at specified intervals and coordinates

### Advanced Features
- **Buffs System**: Automatic buff activation (up to 8 buffs)
  - Enable/disable individual buffs
  - Select skill images from Jobs folder
  - Register keyboard keys for each buff
  - Automatically activates buffs when not active
  
- **Skill Sequence**: Sequential skill execution system (up to 8 skills)
  - Enable/disable individual skills
  - Select skill images from Jobs folder
  - Register keyboard keys for each skill
  - Automatically resets when enemy dies or changes target
  - Executes skills in sequence when enemy is found
  - Advances to next skill when current skill disappears

- **Assist Only Mode**: Party support mode for group play
  - **Purpose**: Allows the bot to assist a party leader's target instead of auto-targeting
  - **How it works**:
    - Automatically disables Auto Attack, Mob Filter, and Auto Unstuck when enabled
    - Continuously searches for and clicks the assist button (`assist.bmp`) in the skill area
    - Clicks assist button every 1 second when found
    - Skills execute normally (no HP decrease check needed)
    - Basic attack (R key) is disabled (assist button handles attacking)
  - **Setup**:
    1. Place `assist.bmp` image file in the bot directory (same location as the bot executable)
    2. Enable "Assist Only" checkbox in Settings tab
    3. Ensure skill area is calibrated (assist button must be visible in skill area)
  - **Requirements**:
    - `assist.bmp` image file must exist in bot directory
    - Skill area must be calibrated (assist button must be in the calibrated skill area)
    - Party leader must have a target selected
  - **Note**: When Assist Only is disabled, previous settings for Auto Attack, Mob Filter, and Auto Unstuck are restored

- **Calibration**: Automatic detection of HP/MP bars and skill areas (available in Settings tab)
- **Mob Filtering**: Target only specific mobs from a configurable list using OCR
- **OCR Integration**: Enemy name detection using EasyOCR for mob filtering

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
