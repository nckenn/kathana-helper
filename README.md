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
- **gui.py**: Complete GUI interface using CustomTkinter with tabs for Settings, Skill Sequence, Skill Slots, Buffs, Calibration, and Mouse Clicker

## Features

### Core Features
- **Auto Attack**: Automatic enemy targeting and attack with mob filtering
- **Auto Pots**: Automatic HP/MP potion usage based on thresholds
- **Auto Repair**: Automatic equipment repair when damaged
- **Auto Unstuck**: Detects and resolves stuck situations
- **Skill Slots**: Configurable skill rotation with intervals
- **Mouse Clicker**: Automated mouse clicking at specified intervals

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
  - Bypass option to skip skills not found
  - Automatically resets when enemy dies or changes target
  - Executes skills in sequence when enemy is found

- **Calibration**: Automatic detection of HP/MP bars and skill areas
- **Mob Filtering**: Target only specific mobs from a configurable list
- **OCR Integration**: Enemy name detection using EasyOCR

