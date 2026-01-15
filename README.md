# Kathana Helper

## File Structure

```
kathana_bot/
├── __init__.py           # Package initialization
├── main.py               # Entry point - run this to start the bot
├── config.py             # Global variables and configuration
├── window_utils.py       # Window capture and management
├── input_handler.py      # Input sending (keys, mouse)
├── auto_attack.py      # Auto-attack system: enemy HP bar detection, name detection, and mob filtering
├── ocr_utils.py         # OCR functions for text reading
├── auto_repair.py       # Auto repair functionality
├── auto_unstuck.py      # Auto unstuck functionality
├── bot_logic.py         # Main bot loop and skill checking
├── settings_manager.py  # Settings save/load
└── gui.py               # GUI class (CustomTkinter)
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
- **input_handler.py**: Keyboard and mouse input functions
- **auto_attack.py**: Auto-attack system including enemy HP bar detection, name detection using OCR, and mob filtering
- **ocr_utils.py**: EasyOCR integration for text reading
- **auto_repair.py**: Damage monitoring and auto repair
- **auto_unstuck.py**: Stuck detection and unstuck mechanism
- **bot_logic.py**: Main bot loop, skill checking, and state management
- **settings_manager.py**: JSON-based settings persistence
- **gui.py**: Complete GUI interface using CustomTkinter

