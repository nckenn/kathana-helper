# Kathana Helper

## File Structure

```
kathana_bot/
├── __init__.py           # Package initialization
├── main.py               # Entry point - run this to start the bot
├── config.py             # Global variables and configuration
├── window_utils.py       # Window capture and management
├── input_handler.py      # Input sending (keys, mouse)
├── bar_detection.py      # HP/MP bar detection
├── ocr_utils.py         # OCR functions for text reading
├── mob_detection.py     # Mob detection and filtering
├── auto_repair.py       # Auto repair functionality
├── auto_unstuck.py      # Auto unstuck functionality
├── bot_logic.py         # Main bot loop and skill checking
├── settings_manager.py  # Settings save/load
└── gui.py               # GUI class (CustomTkinter)
```

## Usage

### Running the Bot
```bash
cd kathana_bot
python main.py
```

### With auto_py_to_exe
1. Point `auto-py-to-exe` to `main.py`
2. All modules will be automatically included
3. Works perfectly with PyInstaller

## Module Descriptions

- **config.py**: All global variables, constants, and configuration
- **window_utils.py**: Window capture, connection, and management
- **input_handler.py**: Keyboard and mouse input functions
- **bar_detection.py**: HP/MP bar detection and percentage calculation
- **ocr_utils.py**: EasyOCR integration for text reading
- **mob_detection.py**: Mob name detection and filtering
- **auto_repair.py**: Damage monitoring and auto repair
- **auto_unstuck.py**: Stuck detection and unstuck mechanism
- **bot_logic.py**: Main bot loop, skill checking, and state management
- **settings_manager.py**: JSON-based settings persistence
- **gui.py**: Complete GUI interface using CustomTkinter

