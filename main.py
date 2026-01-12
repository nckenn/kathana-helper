"""
Main entry point for Kathana Bot
Refactored version with modular structure
"""
import config
import input_handler
from gui import BotGUI


def main():
    """Main entry point"""
    # Initialize PyAutoGUI
    input_handler.initialize_pyautogui()
    
    # Create and run GUI
    gui = BotGUI()
    gui.run()


if __name__ == "__main__":
    main()
