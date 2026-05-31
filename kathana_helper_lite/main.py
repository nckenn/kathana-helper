"""Kathana Helper Lite — skill intervals + auto HP/MP pots."""
import input_handler
import settings_manager
from gui import LiteGUI


def main():
    input_handler.initialize_pyautogui()
    settings_manager.load_settings()
    app = LiteGUI()
    app.run()


if __name__ == '__main__':
    main()
