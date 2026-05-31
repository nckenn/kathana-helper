"""
Main entry point for Kathana Bot
Refactored version with modular structure
"""
import config
import input_handler
from gui import BotGUI
from license_manager import get_license_manager
import logger


def main():
    """Main entry point"""
    # Check license before starting
    license_manager = get_license_manager()
    is_valid, message, license_data = license_manager.validate_license()
    
    # Initialize PyAutoGUI
    input_handler.initialize_pyautogui()
    
    # Create GUI (but don't show main window yet if license is invalid)
    gui = BotGUI()
    
    if not is_valid:
        # License is invalid or missing - show only license dialog, hide main window
        logger.warn(f"License check failed: {message}", "License")
        gui.root.withdraw()  # Hide main window
        gui.show_license_dialog_blocking()  # Show blocking license dialog (waits until closed)
        
        # After dialog closes, re-check license
        logger.info("License dialog closed, re-checking license...", "License")
        import time
        time.sleep(0.5)  # Small delay to ensure file is fully written
        is_valid, message, license_data = license_manager.validate_license()
        if is_valid:
            # License is now valid - show main app
            logger.info("License is now valid, showing main window...", "License")
            gui.root.deiconify()
            gui.root.update_idletasks()
            gui.root.lift()
            gui.root.focus_force()
            gui.root.update()
            gui.run()
        else:
            # Still invalid - exit app
            logger.warn(f"License still invalid after activation: {message}", "License")
            gui.root.quit()
    else:
        # License is valid - show main app directly
        logger.info("License is valid, showing main window...", "License")
        gui.run()


if __name__ == "__main__":
    main()
