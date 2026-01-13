"""
GUI module for Kathana Bot
Refactored to use modular structure
"""
import tkinter as tk
from tkinter import messagebox, simpledialog
import customtkinter as ctk
import threading
import win32gui
import queue
import config
import window_utils
import settings_manager
import bot_logic
import input_handler
import mob_detection
import ocr_utils

class BotGUI:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BotGUI, cls).__new__(cls)
        return cls._instance
    
    def check_ocr_on_startup(self):
        """Check OCR availability on startup and show warning if not available"""
        print("Checking OCR availability...")
        is_available, error_msg, mode = ocr_utils.check_ocr_availability()
        
        # Store OCR availability in config
        config.ocr_available = is_available
        config.ocr_mode = mode
        
        if not is_available:
            error_details = f"\n\nError: {error_msg}" if error_msg else ""
            warning_message = (
                "OCR (Optical Character Recognition) is not available on this system.\n\n"
                "Features that require OCR (such as auto-repair, damage detection, etc.) "
                "will not work.\n\n"
                "Possible solutions:\n"
                "• Install EasyOCR: pip install easyocr\n"
                "• Install required dependencies (PyTorch, etc.)\n"
                "• Check if your system meets the requirements\n"
                f"{error_details}\n\n"
                "The application will continue, but OCR features will be disabled."
            )
            messagebox.showwarning("OCR Not Available", warning_message)
            print("WARNING: OCR is not available - OCR features will be disabled")
        else:
            print(f"OCR check passed - Available in {mode.upper()} mode")
    
    def save_settings_gui(self):
        """Save settings from GUI"""
        if settings_manager.save_settings():
            print("Settings saved successfully!")
            messagebox.showinfo("Save Settings", "Settings saved successfully!")
        else:
            print("Failed to save settings!")
            messagebox.showerror("Save Settings", "Failed to save settings!")
    
    def load_settings_gui(self):
        """Load settings to GUI"""
        print("Loading settings...")
        if settings_manager.load_settings():
            print("Settings loaded from file, applying to GUI...")
            self.apply_settings_to_gui()
            print("Settings loaded and applied successfully!")
            messagebox.showinfo("Load Settings", "Settings loaded successfully!")
        else:
            print("Failed to load settings!")
            messagebox.showwarning("Load Settings", "No saved settings found or failed to load settings!")
    
    def apply_settings_to_gui(self):
        """Apply loaded settings to the GUI components"""
        try:
            print("Applying settings to GUI...")
            # Apply skill slot settings
            for slot_key, slot_data in config.skill_slots.items():
                if slot_key in self.skill_vars:
                    self.skill_vars[slot_key].set(slot_data['enabled'])
                    print(f"  Applied skill slot {slot_key}: enabled={slot_data['enabled']}")
                if slot_key in self.skill_intervals:
                    self.skill_intervals[slot_key].set(str(slot_data['interval']))
                    print(f"  Applied skill slot {slot_key}: interval={slot_data['interval']}")
            
            # Apply action slot settings
            for action_key, action_data in config.action_slots.items():
                if action_key in self.action_vars:
                    self.action_vars[action_key].set(action_data['enabled'])
                    print(f"  Applied action {action_key}: enabled={action_data['enabled']}")
                if action_key in self.action_intervals:
                    self.action_intervals[action_key].set(str(action_data['interval']))
                    print(f"  Applied action {action_key}: interval={action_data['interval']}")
            
            # Apply mob detection settings
            self.mob_detection_var.set(config.mob_detection_enabled)
            self.mob_coords_var.set(f"{config.target_name_area['x']},{config.target_name_area['y']}")
            print(f"  Applied mob detection: enabled={config.mob_detection_enabled}, coords={config.target_name_area['x']},{config.target_name_area['y']}")
            
            # Apply enemy HP bar settings
            if hasattr(self, 'enemy_hp_coords_var'):
                self.enemy_hp_coords_var.set(f"{config.target_hp_bar_area['x']},{config.target_hp_bar_area['y']}")
                self.enemy_hp_x_var.set(str(config.target_hp_bar_area['x']))
                self.enemy_hp_y_var.set(str(config.target_hp_bar_area['y']))
                self.enemy_hp_width_var.set(str(config.target_hp_bar_area['width']))
                self.enemy_hp_height_var.set(str(config.target_hp_bar_area['height']))
                print(f"  Applied enemy HP bar area: {config.target_hp_bar_area}")
            
            # Apply Auto Attack settings
            self.auto_attack_var.set(config.auto_attack_enabled)
            print(f"  Applied auto attack: enabled={config.auto_attack_enabled}")
            
            # Apply Auto Repair settings
            if hasattr(self, 'auto_repair_var'):
                self.auto_repair_var.set(config.auto_repair_enabled)
                print(f"  Applied auto repair: enabled={config.auto_repair_enabled}")
            
            # Apply Auto Change Target settings
            if hasattr(self, 'auto_change_target_var'):
                self.auto_change_target_var.set(config.auto_change_target_enabled)
                print(f"  Applied auto change target: enabled={config.auto_change_target_enabled}")
            if hasattr(self, 'unstuck_timeout_var'):
                self.unstuck_timeout_var.set(str(config.unstuck_timeout))
                print(f"  Applied unstuck timeout: {config.unstuck_timeout} seconds")
            
            # Apply HP settings
            self.auto_hp_var.set(config.auto_hp_enabled)
            print(f"  Applied auto HP: enabled={config.auto_hp_enabled}")
            # Load HP settings from global variables
            try:
                self.hp_threshold_var.set(str(config.hp_threshold))
                self.hp_x_var.set(str(config.hp_bar_area['x']))
                self.hp_y_var.set(str(config.hp_bar_area['y']))
                self.hp_width_var.set(str(config.hp_bar_area['width']))
                self.hp_height_var.set(str(config.hp_bar_area['height']))
                self.hp_coords_var.set(f"{config.hp_bar_area['x']},{config.hp_bar_area['y']}")
                print(f"  Applied HP threshold: {config.hp_threshold}%, area: {config.hp_bar_area}")
            except Exception as e:
                print(f"  Error applying HP settings: {e}")
            
            # Apply MP settings
            self.auto_mp_var.set(config.auto_mp_enabled)
            print(f"  Applied auto MP: enabled={config.auto_mp_enabled}")
            # Load MP settings from global variables
            try:
                self.mp_threshold_var.set(str(config.mp_threshold))
                self.mp_x_var.set(str(config.mp_bar_area['x']))
                self.mp_y_var.set(str(config.mp_bar_area['y']))
                self.mp_width_var.set(str(config.mp_bar_area['width']))
                self.mp_height_var.set(str(config.mp_bar_area['height']))
                self.mp_coords_var.set(f"{config.mp_bar_area['x']},{config.mp_bar_area['y']}")
                print(f"  Applied MP threshold: {config.mp_threshold}%, area: {config.mp_bar_area}")
            except Exception as e:
                print(f"  Error applying MP settings: {e}")
            
            # Apply mouse clicker settings
            self.mouse_clicker_var.set(config.mouse_clicker_enabled)
            print(f"  Applied mouse clicker: enabled={config.mouse_clicker_enabled}")
            try:
                self.mouse_clicker_interval_var.set(str(config.mouse_clicker_interval))
                self.mouse_clicker_mode_var.set("cursor" if config.mouse_clicker_use_cursor else "coords")
                self.mouse_clicker_x_var.set(str(config.mouse_clicker_coords['x']))
                self.mouse_clicker_y_var.set(str(config.mouse_clicker_coords['y']))
                self.update_mouse_clicker_mode()  # Update visibility
                print(f"  Applied mouse clicker: interval={config.mouse_clicker_interval}s, mode={'cursor' if config.mouse_clicker_use_cursor else 'coords'}, coords={config.mouse_clicker_coords}")
            except Exception as e:
                print(f"  Error applying mouse clicker settings: {e}")
            
            # Apply skip list
            skip_text = '\n'.join(config.mob_skip_list)
            self.skip_list_text.delete("1.0", tk.END)
            self.skip_list_text.insert("1.0", skip_text)
            
            # Apply selected window
            if config.selected_window:
                self.window_var.set(config.selected_window)
                # Try to refresh and select the window
                self.refresh_windows_with_selection(config.selected_window)
            
            print("Settings applied to GUI")
        except Exception as e:
            print(f"Error applying settings to GUI: {e}")
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        # Configure customtkinter appearance and theme
        ctk.set_appearance_mode("dark")  # Options: "dark", "light", "system"
        ctk.set_default_color_theme("blue")  # Options: "blue", "green", "dark-blue"
        
        # Initialize root window with customtkinter
        self.root = ctk.CTk()
        self.root.title("Kathana Helper by xCrypto v2.0.0")
        self.root.geometry("655x740")
        self.root.resizable(True, True)
        
        # Check OCR availability on startup
        self.check_ocr_on_startup()
        
        # Configure root window grid to allow resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Create main frame with padding
        main_frame = ctk.CTkFrame(self.root, corner_radius=10)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Configure main frame grid for two columns
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Configure main frame rows for proper expansion
        # Rows: 0=window, 1=status_info, 2=bot_controls, 3=tabview
        main_frame.rowconfigure(3, weight=1)  # Tabview can expand
        
        # Window selection frame
        window_frame = ctk.CTkFrame(main_frame, corner_radius=8)
        window_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=10, padx=10)
        window_frame_label = ctk.CTkLabel(window_frame, text="Window Selection", font=ctk.CTkFont(size=14, weight="bold"))
        window_frame_label.grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 5))
        
        # Window dropdown
        self.window_var = tk.StringVar()
        self.window_var.trace('w', self.on_window_change)  # Reset connection when window changes
        self.window_combo = ctk.CTkComboBox(window_frame, variable=self.window_var, state="readonly", width=400, height=32)
        self.window_combo.grid(row=1, column=0, sticky="ew", padx=(10, 5), pady=(0, 8))
        
        # Refresh button
        self.refresh_button = ctk.CTkButton(window_frame, text="Refresh", command=self.refresh_windows, width=100, height=32)
        self.refresh_button.grid(row=1, column=1, padx=5, pady=(0, 8))
        
        # Rename button
        self.rename_button = ctk.CTkButton(window_frame, text="Rename", command=self.rename_window, width=100, height=32)
        self.rename_button.grid(row=1, column=2, padx=(5, 10), pady=(0, 8))
        
        # Configure window frame grid
        window_frame.columnconfigure(0, weight=1)
        
        # Status frame
        status_info_frame = ctk.CTkFrame(main_frame, corner_radius=8)
        status_info_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10), padx=10)
        
        # Status label
        self.status_label = ctk.CTkLabel(status_info_frame, text="Status: Stopped", font=ctk.CTkFont(size=12, weight="bold"))
        self.status_label.grid(row=0, column=0, padx=10, pady=6)
        
        # Connection status label
        self.connection_label = ctk.CTkLabel(status_info_frame, text="Window: Not Connected", font=ctk.CTkFont(size=11))
        self.connection_label.grid(row=0, column=1, padx=(10, 10), pady=6)
        
        # Bot control frame - fixed height to prevent fluid expansion
        bot_frame = ctk.CTkFrame(main_frame, corner_radius=8)
        bot_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 0), padx=10)
        # Set minimum height to prevent frame from expanding
        bot_frame.grid_rowconfigure(0, weight=0)  # Don't allow row to expand
        
        # Connect button
        self.connect_button = ctk.CTkButton(bot_frame, text="Connect", command=self.connect_window, width=120, height=32, corner_radius=6)
        self.connect_button.grid(row=0, column=0, padx=(10, 5), pady=5)
        
        # Start button
        self.start_button = ctk.CTkButton(bot_frame, text="Start", command=self.start_bot, state="disabled", width=100, height=32, corner_radius=6, fg_color="green", hover_color="darkgreen")
        self.start_button.grid(row=0, column=1, padx=5, pady=5)
        
        # Stop button
        self.stop_button = ctk.CTkButton(bot_frame, text="Stop", command=self.stop_bot, state="disabled", width=100, height=32, corner_radius=6, fg_color="red", hover_color="darkred")
        self.stop_button.grid(row=0, column=2, padx=5, pady=5)
        
        # Separator frame (using a thin frame as separator) - fixed height to match buttons
        separator = ctk.CTkFrame(bot_frame, width=2, height=40, fg_color="gray50")
        separator.grid(row=0, column=3, padx=6, pady=5)
        
        # Save Settings button
        self.save_settings_button = ctk.CTkButton(bot_frame, text="Save Settings", command=self.save_settings_gui, width=110, height=32, corner_radius=6)
        self.save_settings_button.grid(row=0, column=4, padx=5, pady=5)
        
        # Load Settings button
        self.load_settings_button = ctk.CTkButton(bot_frame, text="Load Settings", command=self.load_settings_gui, width=110, height=32, corner_radius=6)
        self.load_settings_button.grid(row=0, column=5, padx=(5, 10), pady=5)
        
        # Create tabview for all sections
        tabview = ctk.CTkTabview(main_frame, corner_radius=8)
        tabview.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(0, 10), padx=10)
        
        # Configure tabview to expand
        main_frame.rowconfigure(3, weight=1)
        
        # Create tabs
        status_tab = tabview.add("Status")
        settings_tab = tabview.add("Settings")
        skills_tab = tabview.add("Skill Slots")
        calibration_tab = tabview.add("Calibration")
        mouse_clicker_tab = tabview.add("Mouse Clicker")
        
        # Action slots frame - moved to Status tab
        status_frame = status_tab
        
        # Create action slot controls in a horizontal layout
        self.action_vars = {}
        self.action_intervals = {}
        
        # HP Progress Bar
        hp_bar_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
        hp_bar_frame.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        
        hp_label = ctk.CTkLabel(hp_bar_frame, text="HP:", width=70, anchor='w', font=ctk.CTkFont(size=11))
        hp_label.grid(row=0, column=0, padx=(0, 10))
        self.hp_progress_bar = ctk.CTkProgressBar(hp_bar_frame, width=200, height=20, progress_color="red", corner_radius=0)
        self.hp_progress_bar.set(0)
        self.hp_progress_bar.grid(row=0, column=1, padx=(0, 10))
        self.hp_percent_label = ctk.CTkLabel(hp_bar_frame, text="---%", font=ctk.CTkFont(size=11, weight="bold"), text_color="white")
        self.hp_percent_label.grid(row=0, column=2)
        
        # MP Progress Bar
        mp_bar_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
        mp_bar_frame.grid(row=1, column=0, sticky="w", padx=15, pady=5)
        
        mp_label = ctk.CTkLabel(mp_bar_frame, text="MP:", width=70, anchor='w', font=ctk.CTkFont(size=11))
        mp_label.grid(row=0, column=0, padx=(0, 10))
        self.mp_progress_bar = ctk.CTkProgressBar(mp_bar_frame, width=200, height=20, progress_color="#0b58b0", corner_radius=0)
        self.mp_progress_bar.set(0)
        self.mp_progress_bar.grid(row=0, column=1, padx=(0, 10))
        self.mp_percent_label = ctk.CTkLabel(mp_bar_frame, text="---%", font=ctk.CTkFont(size=11, weight="bold"), text_color="white")
        self.mp_percent_label.grid(row=0, column=2)
        
        # Enemy HP Progress Bar
        enemy_hp_bar_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
        enemy_hp_bar_frame.grid(row=2, column=0, sticky="w", padx=15, pady=5)
        
        enemy_hp_label = ctk.CTkLabel(enemy_hp_bar_frame, text="Enemy HP:", width=70, anchor='w', font=ctk.CTkFont(size=11))
        enemy_hp_label.grid(row=0, column=0, padx=(0, 10))
        self.enemy_hp_progress_bar = ctk.CTkProgressBar(enemy_hp_bar_frame, width=200, height=20, progress_color="green", corner_radius=0)
        self.enemy_hp_progress_bar.set(0)
        self.enemy_hp_progress_bar.grid(row=0, column=1, padx=(0, 10))
        self.enemy_hp_percent_label = ctk.CTkLabel(enemy_hp_bar_frame, text="---%", font=ctk.CTkFont(size=11, weight="bold"), text_color="white")
        self.enemy_hp_percent_label.grid(row=0, column=2, padx=(0, 10))
        self.unstuck_countdown_label = ctk.CTkLabel(enemy_hp_bar_frame, text="Unstuck: ---", font=ctk.CTkFont(size=10), text_color="gray")
        self.unstuck_countdown_label.grid(row=0, column=3)
        
        # Enemy Name display
        enemy_name_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
        enemy_name_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=(5, 15))
        
        enemy_name_label = ctk.CTkLabel(enemy_name_frame, text="Enemy Name:", width=60, anchor='w', font=ctk.CTkFont(size=11))
        enemy_name_label.grid(row=0, column=0, padx=(0, 10))
        self.current_mob_label = ctk.CTkLabel(enemy_name_frame, text="None", font=ctk.CTkFont(size=11), text_color="red")
        self.current_mob_label.grid(row=0, column=1, sticky="w")
        
        # Configure status frame grid
        status_frame.columnconfigure(0, weight=1)
        
        # Options frame - moved to Settings tab
        settings_frame = settings_tab
        
        # Configure settings frame for 2 columns with padding
        settings_frame.columnconfigure(0, weight=1)
        settings_frame.columnconfigure(1, weight=1)
        settings_frame.rowconfigure(0, weight=0)
        
        # Column 0: Auto Attack, Auto Loot, Auto Repair
        # Auto Attack frame
        auto_attack_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        auto_attack_frame.grid(row=1, column=0, sticky="ew", padx=(15, 5), pady=(10, 0))
        
        # Auto Attack checkbox
        self.auto_attack_var = tk.BooleanVar()
        auto_attack_checkbox = ctk.CTkCheckBox(auto_attack_frame, text="Auto Attack", 
                                         variable=self.auto_attack_var,
                                         command=self.update_auto_attack,
                                         font=ctk.CTkFont(size=11))
        auto_attack_checkbox.grid(row=0, column=0, sticky="w", pady=5)
        
        # Auto Loot frame
        auto_loot_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        auto_loot_frame.grid(row=2, column=0, sticky="ew", padx=(15, 5), pady=(0, 0))
        
        # Auto Loot checkbox
        self.action_vars['pick'] = tk.BooleanVar(value=config.action_slots['pick']['enabled'])
        auto_loot_checkbox = ctk.CTkCheckBox(auto_loot_frame, text="Auto Loot", 
                                         variable=self.action_vars['pick'],
                                         command=lambda: self.update_action_slot('pick'),
                                         font=ctk.CTkFont(size=11))
        auto_loot_checkbox.grid(row=0, column=0, sticky="w", pady=5)
        
        # Auto Repair frame
        auto_repair_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        auto_repair_frame.grid(row=3, column=0, sticky="ew", padx=(15, 5), pady=(0, 0))
        
        # Auto Repair checkbox
        self.auto_repair_var = tk.BooleanVar(value=config.auto_repair_enabled)
        auto_repair_checkbox = ctk.CTkCheckBox(auto_repair_frame, text="Auto Repair", 
                                         variable=self.auto_repair_var,
                                         command=self.update_auto_repair,
                                         font=ctk.CTkFont(size=11))
        auto_repair_checkbox.grid(row=0, column=0, sticky="w", pady=5)
        
        # Column 1: Auto HP, Auto MP, Auto Unstuck
        # Auto HP frame
        auto_hp_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        auto_hp_frame.grid(row=1, column=1, sticky="ew", padx=(5, 15), pady=(10, 0))
        
        # Auto HP checkbox
        self.auto_hp_var = tk.BooleanVar()
        auto_hp_checkbox = ctk.CTkCheckBox(auto_hp_frame, text="Auto HP", 
                                         variable=self.auto_hp_var,
                                         command=self.update_auto_hp,
                                         font=ctk.CTkFont(size=11))
        auto_hp_checkbox.grid(row=0, column=0, sticky="w", pady=5)
        
        # HP threshold input (percentage)
        self.hp_threshold_var = tk.StringVar(value=str(config.hp_threshold))
        hp_threshold_entry = ctk.CTkEntry(auto_hp_frame, textvariable=self.hp_threshold_var, width=50, font=ctk.CTkFont(size=11))
        hp_threshold_entry.grid(row=0, column=1, padx=(10, 5))
        hp_percent_label = ctk.CTkLabel(auto_hp_frame, text="%", font=ctk.CTkFont(size=11))
        hp_percent_label.grid(row=0, column=2, sticky="w")
        
        # HP bar area input (x, y, width, height) - hidden, only used internally
        self.hp_x_var = tk.StringVar(value=str(config.hp_bar_area['x']))
        self.hp_y_var = tk.StringVar(value=str(config.hp_bar_area['y']))
        self.hp_width_var = tk.StringVar(value=str(config.hp_bar_area['width']))
        self.hp_height_var = tk.StringVar(value=str(config.hp_bar_area['height']))
        self.hp_coords_var = tk.StringVar(value=f"{config.hp_bar_area['x']},{config.hp_bar_area['y']}")
        
        # Auto MP frame
        auto_mp_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        auto_mp_frame.grid(row=2, column=1, sticky="ew", padx=(5, 15), pady=(0, 0))
        
        # Auto MP checkbox
        self.auto_mp_var = tk.BooleanVar()
        auto_mp_checkbox = ctk.CTkCheckBox(auto_mp_frame, text="Auto MP", 
                                         variable=self.auto_mp_var,
                                         command=self.update_auto_mp,
                                         font=ctk.CTkFont(size=11))
        auto_mp_checkbox.grid(row=0, column=0, sticky="w", pady=5)
        
        # MP threshold input (percentage)
        self.mp_threshold_var = tk.StringVar(value=str(config.mp_threshold))
        mp_threshold_entry = ctk.CTkEntry(auto_mp_frame, textvariable=self.mp_threshold_var, width=50, font=ctk.CTkFont(size=11))
        mp_threshold_entry.grid(row=0, column=1, padx=(10, 5))
        mp_percent_label = ctk.CTkLabel(auto_mp_frame, text="%", font=ctk.CTkFont(size=11))
        mp_percent_label.grid(row=0, column=2, sticky="w")
        
        # MP bar area input (x, y, width, height) - hidden, only used internally
        self.mp_x_var = tk.StringVar(value=str(config.mp_bar_area['x']))
        self.mp_y_var = tk.StringVar(value=str(config.mp_bar_area['y']))
        self.mp_width_var = tk.StringVar(value=str(config.mp_bar_area['width']))
        self.mp_height_var = tk.StringVar(value=str(config.mp_bar_area['height']))
        self.mp_coords_var = tk.StringVar(value=f"{config.mp_bar_area['x']},{config.mp_bar_area['y']}")
        
        # Auto Unstuck frame
        auto_change_target_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        auto_change_target_frame.grid(row=3, column=1, sticky="ew", padx=(5, 15), pady=(0, 0))
        
        # Auto Unstuck checkbox
        self.auto_change_target_var = tk.BooleanVar(value=config.auto_change_target_enabled)
        auto_change_target_checkbox = ctk.CTkCheckBox(auto_change_target_frame, text="Auto Unstuck", 
                                         variable=self.auto_change_target_var,
                                         command=self.update_auto_change_target,
                                         font=ctk.CTkFont(size=11))
        auto_change_target_checkbox.grid(row=0, column=0, sticky="w", pady=5)
        
        # Unstuck timeout input (seconds)
        self.unstuck_timeout_var = tk.StringVar(value=str(config.unstuck_timeout))
        unstuck_timeout_entry = ctk.CTkEntry(auto_change_target_frame, textvariable=self.unstuck_timeout_var, width=50, font=ctk.CTkFont(size=11))
        unstuck_timeout_entry.grid(row=0, column=1, padx=(10, 0))
        unstuck_timeout_entry.bind('<KeyRelease>', lambda event: self.update_unstuck_timeout())
        
        # Configure options frame rows for proper visibility
        settings_frame.rowconfigure(1, weight=0)
        settings_frame.rowconfigure(2, weight=0)
        settings_frame.rowconfigure(3, weight=0)
        
        # Add Mob Filter to Settings tab
        mob_separator = ctk.CTkFrame(settings_frame, height=1, fg_color="gray50")
        mob_separator.grid(row=4, column=0, columnspan=2, sticky="ew", padx=15, pady=15)
        
        mob_label = ctk.CTkLabel(settings_frame, text="Mob Filter", font=ctk.CTkFont(size=12, weight="bold"))
        mob_label.grid(row=5, column=0, columnspan=2, sticky="w", padx=15, pady=(5, 5))
        
        # Mob detection checkbox
        self.mob_detection_var = tk.BooleanVar()
        mob_checkbox = ctk.CTkCheckBox(settings_frame, text="Enable", 
                                     variable=self.mob_detection_var,
                                     command=self.update_mob_detection,
                                     font=ctk.CTkFont(size=11))
        mob_checkbox.grid(row=6, column=0, columnspan=2, sticky="w", padx=15, pady=(0, 5))
        
        # Skip list
        ctk.CTkLabel(settings_frame, text="Skip List (one per line):", font=ctk.CTkFont(size=11)).grid(row=7, column=0, columnspan=2, sticky="w", padx=15, pady=(5, 5))
        self.skip_list_text = ctk.CTkTextbox(settings_frame, height=150, width=400, font=ctk.CTkFont(size=11))
        self.skip_list_text.grid(row=8, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 5))
        
        # Mob filter buttons
        mob_btn_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        mob_btn_frame.grid(row=9, column=0, columnspan=2, sticky="ew", padx=15, pady=(10, 15))
        
        update_btn = ctk.CTkButton(mob_btn_frame, text="Update List", command=self.update_skip_list, width=100, corner_radius=6)
        update_btn.grid(row=0, column=0, padx=(0, 10))
        
        test_btn = ctk.CTkButton(mob_btn_frame, text="Test", command=self.test_mob_detection, width=100, corner_radius=6)
        test_btn.grid(row=0, column=1)
        
        settings_frame.columnconfigure(0, weight=1)
        settings_frame.columnconfigure(1, weight=1)
        settings_frame.rowconfigure(8, weight=0)
        
        # Hidden variables for mob detection (only used internally)
        self.mob_coords_var = tk.StringVar(value=f"{config.target_name_area['x']},{config.target_name_area['y']}")
        self.enemy_hp_coords_var = tk.StringVar(value=f"{config.target_hp_bar_area['x']},{config.target_hp_bar_area['y']}")
        self.enemy_hp_x_var = tk.StringVar(value=str(config.target_hp_bar_area['x']))
        self.enemy_hp_y_var = tk.StringVar(value=str(config.target_hp_bar_area['y']))
        self.enemy_hp_width_var = tk.StringVar(value=str(config.target_hp_bar_area['width']))
        self.enemy_hp_height_var = tk.StringVar(value=str(config.target_hp_bar_area['height']))
        self.mob_width_var = tk.StringVar(value=str(config.target_name_area['width']))
        self.mob_height_var = tk.StringVar(value=str(config.target_name_area['height']))
        
        # Skill slots frame - moved to Skill Slots tab
        skill_frame = skills_tab
        
        # Create skill slot controls in a grid
        self.skill_vars = {}
        self.skill_intervals = {}
        
        # Helper function to create a slot control
        def create_slot_control(parent, slot, row, col):
            """Helper function to create a skill slot control"""
            # Initialize slot if it doesn't exist
            if slot not in config.skill_slots:
                config.skill_slots[slot] = {'enabled': False, 'interval': 1, 'last_used': 0}
            
            # Create frame for each slot
            slot_frame = ctk.CTkFrame(parent, fg_color="transparent")
            padx_left = 15 if col == 0 else 5
            padx_right = 5 if col == 0 else 15
            slot_frame.grid(row=row, column=col, sticky="ew", padx=(padx_left, padx_right), pady=2)
            
            # Checkbox
            self.skill_vars[slot] = tk.BooleanVar(value=config.skill_slots[slot]['enabled'])
            checkbox = ctk.CTkCheckBox(slot_frame, variable=self.skill_vars[slot], 
                                     command=lambda s=slot: self.update_skill_slot(s),
                                     text="", width=20)
            checkbox.grid(row=0, column=0, padx=(0, 5))
            
            # Slot label
            slot_label_text = f"S{slot}" if isinstance(slot, int) else slot.upper()
            slot_label = ctk.CTkLabel(slot_frame, text=slot_label_text, font=ctk.CTkFont(size=11), width=40)
            slot_label.grid(row=0, column=1, padx=(0, 5))
            
            # Interval input
            self.skill_intervals[slot] = tk.StringVar(value=str(config.skill_slots[slot]['interval']))
            interval_entry = ctk.CTkEntry(slot_frame, textvariable=self.skill_intervals[slot], width=60, font=ctk.CTkFont(size=11))
            interval_entry.grid(row=0, column=2, padx=(0, 0))
            interval_entry.bind('<KeyRelease>', lambda event, s=slot: self.update_skill_interval(s))
        
        # Section 1: Numeric slots (1-8) - 4 rows x 2 columns
        numeric_label = ctk.CTkLabel(skill_frame, text="Number Keys (1-8):", font=ctk.CTkFont(size=12, weight="bold"))
        numeric_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(15, 10))
        
        # Numeric slots layout: 4 rows x 2 columns
        numeric_row = 1
        for i in range(1, 9):
            if i <= 4:
                # First column: slots 1-4
                row = numeric_row + (i - 1)
                col = 0
            else:
                # Second column: slots 5-8
                row = numeric_row + (i - 5)
                col = 1
            create_slot_control(skill_frame, i, row, col)
        
        # Separator between numeric and function key sections
        separator_row = numeric_row + 4
        separator = ctk.CTkFrame(skill_frame, height=2, fg_color="gray50")
        separator.grid(row=separator_row, column=0, columnspan=2, sticky="ew", padx=15, pady=15)
        
        # Section 2: Function key slots (F1-F10) - 5 rows x 2 columns
        function_label = ctk.CTkLabel(skill_frame, text="Function Keys (F1-F10):", font=ctk.CTkFont(size=12, weight="bold"))
        function_label.grid(row=separator_row + 1, column=0, columnspan=2, sticky="w", padx=15, pady=(5, 10))
        
        # Function key slots layout: 5 rows x 2 columns
        function_row = separator_row + 2
        for i in range(1, 11):
            f_key = f'f{i}'
            if i <= 5:
                # First column: F1-F5
                row = function_row + (i - 1)
                col = 0
            else:
                # Second column: F6-F10
                row = function_row + (i - 6)
                col = 1
            create_slot_control(skill_frame, f_key, row, col)
        
        # Configure skill frame grid
        skill_frame.columnconfigure(0, weight=1)
        skill_frame.columnconfigure(1, weight=1)
        
        # Calibration Tool frame - moved to Calibration tab
        calibration_frame = calibration_tab
        
        # Create buttons for each calibration
        ctk.CTkLabel(calibration_frame, text="Set calibration areas:", font=ctk.CTkFont(size=11)).grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(15, 10))
        
        # Player HP button - store as instance variable
        self.hp_calib_btn = ctk.CTkButton(calibration_frame, text="Set Player HP", command=self.pick_hp_coordinates, width=150, corner_radius=6)
        self.hp_calib_btn.grid(row=1, column=0, sticky="ew", padx=(15, 5), pady=5)
        
        # Player MP button - store as instance variable
        self.mp_calib_btn = ctk.CTkButton(calibration_frame, text="Set Player MP", command=self.pick_mp_coordinates, width=150, corner_radius=6)
        self.mp_calib_btn.grid(row=1, column=1, sticky="ew", padx=(5, 15), pady=5)
        
        # Enemy HP button - store as instance variable
        self.enemy_hp_calib_btn = ctk.CTkButton(calibration_frame, text="Set Enemy HP", command=self.pick_enemy_hp_coordinates, width=150, corner_radius=6)
        self.enemy_hp_calib_btn.grid(row=2, column=0, sticky="ew", padx=(15, 5), pady=5)
        
        # Enemy Name button - store as instance variable
        self.enemy_name_calib_btn = ctk.CTkButton(calibration_frame, text="Set Enemy Name", command=self.pick_mob_coordinates, width=150, corner_radius=6)
        self.enemy_name_calib_btn.grid(row=2, column=1, sticky="ew", padx=(5, 15), pady=5)
        
        # System Message button - store as instance variable
        self.system_message_calib_btn = ctk.CTkButton(calibration_frame, text="Set System Message", command=self.pick_system_message_coordinates, width=150, corner_radius=6)
        self.system_message_calib_btn.grid(row=3, column=0, sticky="ew", padx=(15, 5), pady=(5, 15))
        
        # Configure calibration frame grid
        calibration_frame.columnconfigure(0, weight=1)
        calibration_frame.columnconfigure(1, weight=1)
        
        # Mouse Clicker frame - moved to Mouse Clicker tab
        mouse_clicker_frame = mouse_clicker_tab
        
        # First row: Checkbox and Interval
        row1_frame = ctk.CTkFrame(mouse_clicker_frame, fg_color="transparent")
        row1_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))
        
        # Mouse clicker checkbox
        self.mouse_clicker_var = tk.BooleanVar(value=config.mouse_clicker_enabled)
        mouse_clicker_checkbox = ctk.CTkCheckBox(row1_frame, text="Enable", 
                                                 variable=self.mouse_clicker_var,
                                                 command=self.update_mouse_clicker,
                                                 font=ctk.CTkFont(size=11))
        mouse_clicker_checkbox.grid(row=0, column=0, sticky="w", padx=(0, 10))
        
        # Interval input
        self.mouse_clicker_interval_var = tk.StringVar(value=str(config.mouse_clicker_interval))
        mouse_clicker_interval_entry = ctk.CTkEntry(row1_frame, textvariable=self.mouse_clicker_interval_var, width=80, font=ctk.CTkFont(size=11))
        mouse_clicker_interval_entry.grid(row=0, column=1, padx=(0, 0))
        mouse_clicker_interval_entry.bind('<KeyRelease>', lambda event: self.update_mouse_clicker_interval())
        
        # Second row: Mode selection and coordinates
        row2_frame = ctk.CTkFrame(mouse_clicker_frame, fg_color="transparent")
        row2_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 15))
        
        # Click mode selection (cursor position or specific coords)
        ctk.CTkLabel(row2_frame, text="Mode:", font=ctk.CTkFont(size=11)).grid(row=0, column=0, padx=(0, 10), sticky="w")
        self.mouse_clicker_mode_var = tk.StringVar(value="cursor" if config.mouse_clicker_use_cursor else "coords")
        mouse_clicker_mode_frame = ctk.CTkFrame(row2_frame, fg_color="transparent")
        mouse_clicker_mode_frame.grid(row=0, column=1, padx=(0, 10), sticky="w")
        
        ctk.CTkRadioButton(mouse_clicker_mode_frame, text="Cursor", variable=self.mouse_clicker_mode_var, 
                       value="cursor", command=self.update_mouse_clicker_mode, font=ctk.CTkFont(size=11)).grid(row=0, column=0, padx=(0, 10))
        ctk.CTkRadioButton(mouse_clicker_mode_frame, text="Coords", variable=self.mouse_clicker_mode_var, 
                       value="coords", command=self.update_mouse_clicker_mode, font=ctk.CTkFont(size=11)).grid(row=0, column=1)
        
        # Coordinate input (only visible when coords mode is selected)
        # Hidden variables for coordinates (only used internally)
        self.mouse_clicker_x_var = tk.StringVar(value=str(config.mouse_clicker_coords['x']))
        self.mouse_clicker_y_var = tk.StringVar(value=str(config.mouse_clicker_coords['y']))
        
        # Coordinate picker frame (only visible when coords mode is selected)
        self.mouse_clicker_coords_frame = ctk.CTkFrame(row2_frame, fg_color="transparent")
        self.mouse_clicker_coords_frame.grid(row=0, column=2, sticky="w")
        
        # Coordinate picker button
        mouse_clicker_picker_btn = ctk.CTkButton(self.mouse_clicker_coords_frame, text="...", command=self.pick_mouse_clicker_coordinates, width=30, corner_radius=6)
        mouse_clicker_picker_btn.grid(row=0, column=0, padx=(0, 0))
        
        # Initially hide/show coords frame based on mode
        self.update_mouse_clicker_mode()
        
        # Configure mouse clicker frame
        mouse_clicker_frame.columnconfigure(0, weight=1)
        
        
        # Load initial window list
        self.refresh_windows()
        
        # Load settings on startup
        if settings_manager.load_settings():
            self.apply_settings_to_gui()
            print("Settings loaded on startup")
        
        # Update calibration button texts to show current state
        self.update_calibration_button_texts()
        
    def refresh_windows(self):
        """Refresh the list of open windows"""
        try:
            windows = window_utils.get_open_windows()
            window_titles = [title for hwnd, title in windows]
            # CTkComboBox uses configure() method to update values
            self.window_combo.configure(values=window_titles)
            
            # Select first window if available
            if window_titles:
                # CTkComboBox uses set() method to select by value
                self.window_combo.set(window_titles[0])
            else:
                self.window_combo.set("No windows found")
                
        except Exception as e:
            print(f"Error refreshing windows: {e}")
            self.window_combo.set("Error loading windows")
    
    def refresh_windows_with_selection(self, target_window_name):
        """Refresh the list of open windows and select a specific window"""
        try:
            windows = window_utils.get_open_windows()
            window_titles = [title for hwnd, title in windows]
            # CTkComboBox uses configure() method to update values
            self.window_combo.configure(values=window_titles)
            
            # Try to select the target window
            if target_window_name in window_titles:
                # CTkComboBox uses set() method to select by value
                self.window_combo.set(target_window_name)
                print(f"Selected renamed window: {target_window_name}")
            elif window_titles:
                # Fallback to first window if target not found
                self.window_combo.set(window_titles[0])
                print(f"Target window '{target_window_name}' not found, selected first available window")
            else:
                self.window_combo.set("No windows found")
                
        except Exception as e:
            print(f"Error refreshing windows with selection: {e}")
            self.window_combo.set("Error loading windows")
    
    def rename_window(self):
        """Rename the selected window"""
        try:
            selected_window_title = self.window_var.get()
            if not selected_window_title or selected_window_title == "No windows found" or selected_window_title == "Error loading windows":
                print("Please select a valid window to rename")
                return
            
            # Create a simple input dialog
            from tkinter import simpledialog
            new_name = simpledialog.askstring("Rename Window", 
                                            f"Enter new name for window:\n'{selected_window_title}'",
                                            initialvalue=selected_window_title)
            
            if new_name and new_name.strip() and new_name != selected_window_title:
                # Find the window handle for the selected window
                windows = window_utils.get_open_windows()
                target_hwnd = None
                for hwnd, title in windows:
                    if title == selected_window_title:
                        target_hwnd = hwnd
                        break
                
                if target_hwnd:
                    # Rename the window using win32gui
                    win32gui.SetWindowText(target_hwnd, new_name.strip())
                    print(f"Window renamed from '{selected_window_title}' to '{new_name.strip()}'")
                    
                    # Refresh the window list and select the renamed window
                    self.refresh_windows_with_selection(new_name.strip())
                else:
                    print(f"Could not find window handle for '{selected_window_title}'")
            elif new_name == selected_window_title:
                print("New name is the same as current name")
            else:
                print("Rename cancelled or invalid name")
                
        except Exception as e:
            print(f"Error renaming window: {e}")
    
    def on_window_change(self, *args):
        """Called when window selection changes - reset connection"""
        if config.connected_window:
            config.connected_window = None
            self.connect_button.configure(text="Connect", state="normal")
            self.start_button.configure(state="disabled")
            self.connection_label.configure(text="Window: Not Connected")
            self.status_label.configure(text="Status: Disconnected")
            print("Window changed - connection reset")

    def connect_window(self):
        """Connect to the selected window"""
        selected_window_title = self.window_var.get()
        
        if not selected_window_title or selected_window_title == "No windows found" or selected_window_title == "Error loading windows":
            print("Please select a valid window")
            return
        
        # Disconnect if already connected
        if config.connected_window:
            config.connected_window = None
        
        # Connect to the selected window
        window_utils.connect_attacker(selected_window_title)
        
        if config.connected_window:
            self.connect_button.configure(text="Connected", state="disabled")
            self.start_button.configure(state="normal")
            self.connection_label.configure(text=f"Window: {selected_window_title}")
            self.status_label.configure(text="Status: Connected")
            print(f"Successfully connected to: {selected_window_title}")
        else:
            self.connect_button.configure(text="Connect")
            self.start_button.configure(state="disabled")
            self.connection_label.configure(text="Window: Connection Failed")
            self.status_label.configure(text="Status: Connection Failed")
            print(f"Failed to connect to: {selected_window_title}")

    def start_bot(self):
        if not config.bot_running:
            # Check if window is connected
            if not config.connected_window:
                print("Please connect to a window first")
                return
                
            # Reset all bot state for clean start
            bot_logic.reset_bot_state()
                
            config.bot_running = True
            input_handler.initialize_pyautogui()
            
            config.bot_thread = threading.Thread(target=bot_logic.bot_loop, daemon=True)
            config.bot_thread.start()
            
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.status_label.configure(text="Status: Running")
        else:
            print("Bot is already running")
            
    def stop_bot(self):
        config.bot_running = False
        
        # Reset all bot state for clean stop
        bot_logic.reset_bot_state()
        
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.status_label.configure(text="Status: Stopped")
        # Keep connection status - don't reset to "Not Connected"
    
    def update_skill_slot(self, slot_num):
        """Update skill slot enabled status"""

        config.skill_slots[slot_num]['enabled'] = self.skill_vars[slot_num].get()
        status = "enabled" if config.skill_slots[slot_num]['enabled'] else "disabled"
        print(f"Skill slot {slot_num} {status}")
    
    def update_skill_interval(self, slot_num):
        """Update skill slot interval"""

        try:
            interval = float(self.skill_intervals[slot_num].get())
            config.skill_slots[slot_num]['interval'] = interval
            print(f"Skill slot {slot_num} interval updated to {interval} seconds")
        except ValueError:
            print(f"Invalid interval for skill slot {slot_num}")
    
    def update_action_slot(self, action_key):
        """Update action slot enabled status"""

        config.action_slots[action_key]['enabled'] = self.action_vars[action_key].get()
        status = "enabled" if config.action_slots[action_key]['enabled'] else "disabled"
        print(f"Action {action_key} {status}")
    
    def update_action_interval(self, action_key):
        """Update action slot interval"""

        try:
            interval = float(self.action_intervals[action_key].get())
            config.action_slots[action_key]['interval'] = interval
            print(f"Action {action_key} interval updated to {interval} seconds")
        except ValueError:
            print(f"Invalid interval for action {action_key}")
    
    def update_mob_detection(self):
        """Update mob detection enabled status"""

        config.mob_detection_enabled = self.mob_detection_var.get()
        status = "enabled" if config.mob_detection_enabled else "disabled"
        print(f"Mob detection (OCR) {status}")
        if config.mob_detection_enabled:
            print("Note: OCR will initialize on first use (may take a moment)")
    
    def update_auto_attack(self):
        """Update auto attack enabled status"""

        config.auto_attack_enabled = self.auto_attack_var.get()
        status = "enabled" if config.auto_attack_enabled else "disabled"
        print(f"Auto Attack {status}")
    
    def update_auto_repair(self):
        """Update auto repair enabled status"""

        config.auto_repair_enabled = self.auto_repair_var.get()
        status = "enabled" if config.auto_repair_enabled else "disabled"
        print(f"Auto Repair {status}")
    
    def update_auto_change_target(self):
        """Update auto change target enabled status"""

        config.auto_change_target_enabled = self.auto_change_target_var.get()
        status = "enabled" if config.auto_change_target_enabled else "disabled"
        print(f"Auto Change Target {status}")
    
    def update_unstuck_timeout(self):
        """Update unstuck timeout value"""

        try:
            timeout = float(self.unstuck_timeout_var.get())
            if timeout > 0:
                config.unstuck_timeout = timeout
                print(f"Unstuck timeout updated to {config.unstuck_timeout} seconds")
            else:
                print(f"Invalid unstuck timeout: must be greater than 0")
                self.unstuck_timeout_var.set(str(config.unstuck_timeout))
        except ValueError:
            print(f"Invalid unstuck timeout value")
            self.unstuck_timeout_var.set(str(config.unstuck_timeout))
    
    def update_auto_hp(self):
        """Update auto HP enabled status"""

        config.auto_hp_enabled = self.auto_hp_var.get()
        status = "enabled" if config.auto_hp_enabled else "disabled"
        print(f"Auto HP {status}")
    
    def update_auto_mp(self):
        """Update auto MP enabled status"""

        config.auto_mp_enabled = self.auto_mp_var.get()
        status = "enabled" if config.auto_mp_enabled else "disabled"
        print(f"Auto MP {status}")
    
    def update_mouse_clicker(self):
        """Update mouse clicker enabled status"""

        config.mouse_clicker_enabled = self.mouse_clicker_var.get()
        status = "enabled" if config.mouse_clicker_enabled else "disabled"
        print(f"Mouse Clicker (Anti-Stuck) {status}")
    
    def update_mouse_clicker_interval(self):
        """Update mouse clicker interval"""

        try:
            interval = float(self.mouse_clicker_interval_var.get())
            config.mouse_clicker_interval = interval
            print(f"Mouse clicker interval updated to {interval} seconds")
        except ValueError:
            print(f"Invalid interval for mouse clicker")
    
    def update_mouse_clicker_mode(self):
        """Update mouse clicker mode (cursor or coords)"""

        mode = self.mouse_clicker_mode_var.get()
        config.mouse_clicker_use_cursor = (mode == "cursor")
        
        # Show/hide coordinate inputs based on mode
        if mode == "coords":
            self.mouse_clicker_coords_frame.grid()
        else:
            self.mouse_clicker_coords_frame.grid_remove()
        
        mode_text = "cursor position" if config.mouse_clicker_use_cursor else "specific coordinates"
        print(f"Mouse clicker mode: {mode_text}")
    
    def update_mouse_clicker_coords(self):
        """Update mouse clicker coordinates"""

        try:
            x = int(self.mouse_clicker_x_var.get())
            y = int(self.mouse_clicker_y_var.get())
            config.mouse_clicker_coords['x'] = x
            config.mouse_clicker_coords['y'] = y
            print(f"Mouse clicker coordinates updated to ({x}, {y})")
        except ValueError:
            print(f"Invalid coordinates for mouse clicker")
    
    def pick_mouse_clicker_coordinates(self):
        """Allow user to click to set mouse clicker coordinates"""

        
        try:
            # Check if window is connected
            if not config.connected_window:
                messagebox.showwarning("No Window", "Please connect to a game window first!")
                return
            
            # Get window handle
            hwnd = config.connected_window.handle
            
            # Hide the main window temporarily
            self.root.withdraw()
            
            # Show instruction message
            print("Click on the game window to set mouse clicker coordinates. Press ESC to cancel.")
            
            # Create a fullscreen window to capture clicks
            picker_window = tk.Toplevel()
            picker_window.attributes('-fullscreen', True)
            picker_window.attributes('-alpha', 0.3)  # Semi-transparent
            picker_window.configure(bg='black')
            picker_window.attributes('-topmost', True)
            
            # Add instruction label
            instruction_label = tk.Label(picker_window, 
                                       text="Click on the game window to set click position\nPress ESC to cancel", 
                                       font=("Arial", 16), 
                                       fg="white", 
                                       bg="black")
            instruction_label.place(relx=0.5, rely=0.1, anchor="center")
            
            # Label to show current position
            info_label = tk.Label(picker_window, 
                                text="", 
                                font=("Arial", 12), 
                                fg="yellow", 
                                bg="black")
            info_label.place(relx=0.5, rely=0.15, anchor="center")
            
            def on_click(event):
                try:
                    click_x = event.x_root
                    click_y = event.y_root
                    
                    # Get window position
                    rect = win32gui.GetWindowRect(hwnd)
                    window_x = rect[0]
                    window_y = rect[1]
                    
                    # Calculate window-relative coordinates
                    rel_x = click_x - window_x
                    rel_y = click_y - window_y
                    
                    # Update the variables
                    self.mouse_clicker_x_var.set(str(rel_x))
                    self.mouse_clicker_y_var.set(str(rel_y))
                    config.mouse_clicker_coords['x'] = rel_x
                    config.mouse_clicker_coords['y'] = rel_y
                    
                    # Close picker window and show main window
                    picker_window.destroy()
                    self.root.deiconify()
                    
                    print(f"Mouse clicker coordinates set to: ({rel_x}, {rel_y})")
                    messagebox.showinfo("Mouse Clicker Coordinates", 
                                      f"Position set to: ({rel_x}, {rel_y})")
                except Exception as e:
                    print(f"Error setting mouse clicker coordinates: {e}")
                    picker_window.destroy()
                    self.root.deiconify()
            
            def on_escape(event):
                picker_window.destroy()
                self.root.deiconify()
                print("Mouse clicker coordinate picking cancelled")
            
            def on_motion(event):
                try:
                    click_x = event.x_root
                    click_y = event.y_root
                    
                    # Get window position
                    rect = win32gui.GetWindowRect(hwnd)
                    window_x = rect[0]
                    window_y = rect[1]
                    
                    # Calculate window-relative coordinates
                    rel_x = click_x - window_x
                    rel_y = click_y - window_y
                    
                    # Update info label
                    info_label.configure(text=f"Position: ({rel_x}, {rel_y})")
                except:
                    pass
            
            # Bind events
            picker_window.bind('<Button-1>', on_click)
            picker_window.bind('<Motion>', on_motion)
            picker_window.bind('<Escape>', on_escape)
            picker_window.focus_set()
            
        except Exception as e:
            print(f"Error in mouse clicker coordinate picker: {e}")
            self.root.deiconify()
    
    def pick_hp_coordinates(self):
        """Allow user to drag and select HP bar area dynamically"""

        
        try:
            # Check if window is connected
            if not config.connected_window:
                messagebox.showwarning("No Window", "Please connect to a game window first!")
                return
            
            # Get window handle
            hwnd = config.connected_window.handle
            
            # Hide the main window temporarily
            self.root.withdraw()
            
            # Show instruction message
            print("Drag to select HP bar detection area. Press ESC to cancel.")
            
            # Create a fullscreen window to capture clicks
            picker_window = tk.Toplevel()
            picker_window.attributes('-fullscreen', True)
            picker_window.attributes('-alpha', 0.5)  # Semi-transparent
            picker_window.configure(bg='black')
            picker_window.attributes('-topmost', True)
            
            # Create canvas to draw preview rectangle
            canvas = tk.Canvas(picker_window, bg='black', highlightthickness=0, bd=0)
            canvas.pack(fill='both', expand=True)
            
            # Add instruction label
            instruction_label = tk.Label(picker_window, 
                                       text="Click and drag to select HP bar area\nRelease to confirm, Press ESC to cancel", 
                                       font=("Arial", 16), 
                                       fg="white", 
                                       bg="black")
            instruction_label.place(relx=0.5, rely=0.1, anchor="center")
            
            # Label to show current position and size
            info_label = tk.Label(picker_window, 
                                text="", 
                                font=("Arial", 12), 
                                fg="yellow", 
                                bg="black")
            info_label.place(relx=0.5, rely=0.15, anchor="center")
            
            # Drag state variables
            rect_id = None
            start_x = None
            start_y = None
            dragging = False
            
            def on_button_press(event):
                nonlocal start_x, start_y, dragging, rect_id
                start_x = event.x_root
                start_y = event.y_root
                dragging = True
                # Clear any existing rectangle
                if rect_id:
                    canvas.delete(rect_id)
                    rect_id = None
            
            def on_motion(event):
                nonlocal rect_id, start_x, start_y, dragging
                if not dragging or start_x is None or start_y is None:
                    return
                
                try:
                    current_x = event.x_root
                    current_y = event.y_root
                    
                    # Get window position
                    rect = win32gui.GetWindowRect(hwnd)
                    window_x = rect[0]
                    window_y = rect[1]
                    
                    # Calculate rectangle bounds (ensure top-left is min, bottom-right is max)
                    min_x = min(start_x, current_x)
                    max_x = max(start_x, current_x)
                    min_y = min(start_y, current_y)
                    max_y = max(start_y, current_y)
                    
                    # Calculate window-relative coordinates
                    rel_x = min_x - window_x
                    rel_y = min_y - window_y
                    width = max_x - min_x
                    height = max_y - min_y
                    
                    # Update info label
                    info_label.configure(text=f"Position: ({rel_x}, {rel_y}) | Size: {width}x{height} pixels")
                    
                    # Draw preview rectangle
                    if rect_id:
                        canvas.delete(rect_id)
                    
                    rect_id = canvas.create_rectangle(
                        min_x, min_y, max_x, max_y,
                        outline='red', width=2
                    )
                except:
                    pass
            
            def on_button_release(event):
                nonlocal start_x, start_y, dragging, rect_id
                if not dragging or start_x is None or start_y is None:
                    return
                
                try:
                    end_x = event.x_root
                    end_y = event.y_root
                    
                    # Get window position
                    rect = win32gui.GetWindowRect(hwnd)
                    window_x = rect[0]
                    window_y = rect[1]
                    
                    # Calculate rectangle bounds
                    min_x = min(start_x, end_x)
                    max_x = max(start_x, end_x)
                    min_y = min(start_y, end_y)
                    max_y = max(start_y, end_y)
                    
                    # Calculate window-relative coordinates
                    rel_x = min_x - window_x
                    rel_y = min_y - window_y
                    width = max_x - min_x
                    height = max_y - min_y
                    
                    # Ensure minimum size
                    if width < 10:
                        width = 10
                    if height < 5:
                        height = 5
                    
                    # Update the variables
                    self.hp_x_var.set(str(rel_x))
                    self.hp_y_var.set(str(rel_y))
                    self.hp_width_var.set(str(width))
                    self.hp_height_var.set(str(height))
                    self.hp_coords_var.set(f"{rel_x},{rel_y}")
                    
                    # Update global variable
                    config.hp_bar_area['x'] = rel_x
                    config.hp_bar_area['y'] = rel_y
                    config.hp_bar_area['width'] = width
                    config.hp_bar_area['height'] = height
                    
                    # Close picker window and show main window
                    picker_window.destroy()
                    self.root.deiconify()
                    
                    print(f"HP bar area set to: ({rel_x}, {rel_y}, {width}x{height})")
                    messagebox.showinfo("HP Bar Area", 
                                      f"Position: ({rel_x}, {rel_y})\nSize: {width}x{height} pixels")
                    
                    # Update button text to show it's been set
                    self.update_calibration_button_texts()
                except Exception as e:
                    print(f"Error in HP bar selection: {e}")
                    picker_window.destroy()
                    self.root.deiconify()
                
                dragging = False
                start_x = None
                start_y = None
            
            def on_escape(event):
                picker_window.destroy()
                self.root.deiconify()
                print("HP bar selection cancelled")
            
            # Bind events
            picker_window.bind('<Button-1>', on_button_press)
            picker_window.bind('<B1-Motion>', on_motion)
            picker_window.bind('<ButtonRelease-1>', on_button_release)
            picker_window.bind('<Escape>', on_escape)
            picker_window.focus_set()
            
        except Exception as e:
            print(f"Error in HP bar picker: {e}")
            self.root.deiconify()
    
    def pick_mp_coordinates(self):
        """Allow user to drag and select MP bar area dynamically"""

        
        try:
            # Check if window is connected
            if not config.connected_window:
                messagebox.showwarning("No Window", "Please connect to a game window first!")
                return
            
            # Get window handle
            hwnd = config.connected_window.handle
            
            # Hide the main window temporarily
            self.root.withdraw()
            
            # Show instruction message
            print("Drag to select MP bar detection area. Press ESC to cancel.")
            
            # Create a fullscreen window to capture clicks
            picker_window = tk.Toplevel()
            picker_window.attributes('-fullscreen', True)
            picker_window.attributes('-alpha', 0.5)  # Semi-transparent
            picker_window.configure(bg='black')
            picker_window.attributes('-topmost', True)
            
            # Create canvas to draw preview rectangle
            canvas = tk.Canvas(picker_window, bg='black', highlightthickness=0, bd=0)
            canvas.pack(fill='both', expand=True)
            
            # Add instruction label
            instruction_label = tk.Label(picker_window, 
                                       text="Click and drag to select MP bar area\nRelease to confirm, Press ESC to cancel", 
                                       font=("Arial", 16), 
                                       fg="white", 
                                       bg="black")
            instruction_label.place(relx=0.5, rely=0.1, anchor="center")
            
            # Label to show current position and size
            info_label = tk.Label(picker_window, 
                                text="", 
                                font=("Arial", 12), 
                                fg="cyan", 
                                bg="black")
            info_label.place(relx=0.5, rely=0.15, anchor="center")
            
            # Drag state variables
            rect_id = None
            start_x = None
            start_y = None
            dragging = False
            
            def on_button_press(event):
                nonlocal start_x, start_y, dragging, rect_id
                start_x = event.x_root
                start_y = event.y_root
                dragging = True
                # Clear any existing rectangle
                if rect_id:
                    canvas.delete(rect_id)
                    rect_id = None
            
            def on_motion(event):
                nonlocal rect_id, start_x, start_y, dragging
                if not dragging or start_x is None or start_y is None:
                    return
                
                try:
                    current_x = event.x_root
                    current_y = event.y_root
                    
                    # Get window position
                    rect = win32gui.GetWindowRect(hwnd)
                    window_x = rect[0]
                    window_y = rect[1]
                    
                    # Calculate rectangle bounds (ensure top-left is min, bottom-right is max)
                    min_x = min(start_x, current_x)
                    max_x = max(start_x, current_x)
                    min_y = min(start_y, current_y)
                    max_y = max(start_y, current_y)
                    
                    # Calculate window-relative coordinates
                    rel_x = min_x - window_x
                    rel_y = min_y - window_y
                    width = max_x - min_x
                    height = max_y - min_y
                    
                    # Update info label
                    info_label.configure(text=f"Position: ({rel_x}, {rel_y}) | Size: {width}x{height} pixels")
                    
                    # Draw preview rectangle
                    if rect_id:
                        canvas.delete(rect_id)
                    
                    rect_id = canvas.create_rectangle(
                        min_x, min_y, max_x, max_y,
                        outline='blue', width=2
                    )
                except:
                    pass
            
            def on_button_release(event):
                nonlocal start_x, start_y, dragging, rect_id
                if not dragging or start_x is None or start_y is None:
                    return
                
                try:
                    end_x = event.x_root
                    end_y = event.y_root
                    
                    # Get window position
                    rect = win32gui.GetWindowRect(hwnd)
                    window_x = rect[0]
                    window_y = rect[1]
                    
                    # Calculate rectangle bounds
                    min_x = min(start_x, end_x)
                    max_x = max(start_x, end_x)
                    min_y = min(start_y, end_y)
                    max_y = max(start_y, end_y)
                    
                    # Calculate window-relative coordinates
                    rel_x = min_x - window_x
                    rel_y = min_y - window_y
                    width = max_x - min_x
                    height = max_y - min_y
                    
                    # Ensure minimum size
                    if width < 10:
                        width = 10
                    if height < 5:
                        height = 5
                    
                    # Update the variables
                    self.mp_x_var.set(str(rel_x))
                    self.mp_y_var.set(str(rel_y))
                    self.mp_width_var.set(str(width))
                    self.mp_height_var.set(str(height))
                    self.mp_coords_var.set(f"{rel_x},{rel_y}")
                    
                    # Update global variable
                    config.mp_bar_area['x'] = rel_x
                    config.mp_bar_area['y'] = rel_y
                    config.mp_bar_area['width'] = width
                    config.mp_bar_area['height'] = height
                    
                    # Close picker window and show main window
                    picker_window.destroy()
                    self.root.deiconify()
                    
                    print(f"MP bar area set to: ({rel_x}, {rel_y}, {width}x{height})")
                    messagebox.showinfo("MP Bar Area", 
                                      f"Position: ({rel_x}, {rel_y})\nSize: {width}x{height} pixels")
                    
                    # Update button text to show it's been set
                    self.update_calibration_button_texts()
                except Exception as e:
                    print(f"Error in MP bar selection: {e}")
                    picker_window.destroy()
                    self.root.deiconify()
                
                dragging = False
                start_x = None
                start_y = None
            
            def on_escape(event):
                picker_window.destroy()
                self.root.deiconify()
                print("MP bar selection cancelled")
            
            # Bind events
            picker_window.bind('<Button-1>', on_button_press)
            picker_window.bind('<B1-Motion>', on_motion)
            picker_window.bind('<ButtonRelease-1>', on_button_release)
            picker_window.bind('<Escape>', on_escape)
            picker_window.focus_set()
            
        except Exception as e:
            print(f"Error in MP bar picker: {e}")
            self.root.deiconify()
    
    def pick_mob_coordinates(self):
        """Allow user to drag and select mob detection area dynamically"""

        
        try:
            # Check if window is connected
            if not config.connected_window:
                messagebox.showwarning("No Window", "Please connect to a game window first!")
                return
            
            # Get window handle
            hwnd = config.connected_window.handle
            
            # Hide the main window temporarily
            self.root.withdraw()
            
            # Show instruction message
            print("Drag to select mob name detection area. Press ESC to cancel.")
            
            # Create a fullscreen window to capture clicks
            picker_window = tk.Toplevel()
            picker_window.attributes('-fullscreen', True)
            picker_window.attributes('-alpha', 0.5)  # Semi-transparent
            picker_window.configure(bg='black')
            picker_window.attributes('-topmost', True)
            
            # Create canvas to draw preview rectangle
            canvas = tk.Canvas(picker_window, bg='black', highlightthickness=0, bd=0)
            canvas.pack(fill='both', expand=True)
            
            # Add instruction label
            instruction_label = tk.Label(picker_window, 
                                       text="Click and drag to select mob name area\nRelease to confirm, Press ESC to cancel", 
                                       font=("Arial", 16), 
                                       fg="white", 
                                       bg="black")
            instruction_label.place(relx=0.5, rely=0.1, anchor="center")
            
            # Label to show current position and size
            info_label = tk.Label(picker_window, 
                                text="", 
                                font=("Arial", 12), 
                                fg="lime", 
                                bg="black")
            info_label.place(relx=0.5, rely=0.15, anchor="center")
            
            # Drag state variables
            rect_id = None
            start_x = None
            start_y = None
            dragging = False
            
            def on_button_press(event):
                nonlocal start_x, start_y, dragging, rect_id
                start_x = event.x_root
                start_y = event.y_root
                dragging = True
                # Clear any existing rectangle
                if rect_id:
                    canvas.delete(rect_id)
                    rect_id = None
            
            def on_motion(event):
                nonlocal rect_id, start_x, start_y, dragging
                if not dragging or start_x is None or start_y is None:
                    return
                
                try:
                    current_x = event.x_root
                    current_y = event.y_root
                    
                    # Get window position
                    rect = win32gui.GetWindowRect(hwnd)
                    window_x = rect[0]
                    window_y = rect[1]
                    
                    # Calculate rectangle bounds (ensure top-left is min, bottom-right is max)
                    min_x = min(start_x, current_x)
                    max_x = max(start_x, current_x)
                    min_y = min(start_y, current_y)
                    max_y = max(start_y, current_y)
                    
                    # Calculate window-relative coordinates
                    rel_x = min_x - window_x
                    rel_y = min_y - window_y
                    width = max_x - min_x
                    height = max_y - min_y
                    
                    # Update info label
                    info_label.configure(text=f"Position: ({rel_x}, {rel_y}) | Size: {width}x{height} pixels")
                    
                    # Draw preview rectangle
                    if rect_id:
                        canvas.delete(rect_id)
                    
                    rect_id = canvas.create_rectangle(
                        min_x, min_y, max_x, max_y,
                        outline='white', width=2
                    )
                except:
                    pass
            
            def on_button_release(event):
                nonlocal start_x, start_y, dragging, rect_id
                if not dragging or start_x is None or start_y is None:
                    return
                
                try:
                    end_x = event.x_root
                    end_y = event.y_root
                    
                    # Get window position
                    rect = win32gui.GetWindowRect(hwnd)
                    window_x = rect[0]
                    window_y = rect[1]
                    
                    # Calculate rectangle bounds
                    min_x = min(start_x, end_x)
                    max_x = max(start_x, end_x)
                    min_y = min(start_y, end_y)
                    max_y = max(start_y, end_y)
                    
                    # Calculate window-relative coordinates
                    rel_x = min_x - window_x
                    rel_y = min_y - window_y
                    width = max_x - min_x
                    height = max_y - min_y
                    
                    # Ensure minimum size
                    if width < 10:
                        width = 10
                    if height < 5:
                        height = 5
                    
                    # Update the coordinate variables (center point for display)
                    center_x = rel_x + (width // 2)
                    center_y = rel_y + (height // 2)
                    self.mob_coords_var.set(f"{center_x},{center_y}")
                    
                    # Update width and height variables
                    self.mob_width_var.set(str(width))
                    self.mob_height_var.set(str(height))
                    
                    # Update global variable (using center point for x,y as before)
                    config.target_name_area['x'] = center_x
                    config.target_name_area['y'] = center_y
                    config.target_name_area['width'] = width
                    config.target_name_area['height'] = height
                    
                    # Close picker window and show main window
                    picker_window.destroy()
                    self.root.deiconify()
                    
                    print(f"Mob detection area set to: Center ({center_x}, {center_y}), Size {width}x{height}")
                    messagebox.showinfo("Mob Detection Area", 
                                      f"Center: ({center_x}, {center_y})\nSize: {width}x{height} pixels")
                    
                    # Update button text to show it's been set
                    self.update_calibration_button_texts()
                except Exception as e:
                    print(f"Error in mob coordinate selection: {e}")
                    picker_window.destroy()
                    self.root.deiconify()
                
                dragging = False
                start_x = None
                start_y = None
            
            def on_escape(event):
                # Close picker window and show main window
                picker_window.destroy()
                self.root.deiconify()
                print("Mob coordinate picking cancelled")
            
            # Bind events
            picker_window.bind('<Button-1>', on_button_press)
            picker_window.bind('<B1-Motion>', on_motion)
            picker_window.bind('<ButtonRelease-1>', on_button_release)
            picker_window.bind('<Escape>', on_escape)
            picker_window.focus_set()
            
        except Exception as e:
            print(f"Error in mob coordinate picker: {e}")
            # Make sure main window is shown
            self.root.deiconify()
    
    def pick_enemy_hp_coordinates(self):
        """Allow user to drag and select enemy HP bar area dynamically"""

        
        try:
            # Check if window is connected
            if not config.connected_window:
                messagebox.showwarning("No Window", "Please connect to a game window first!")
                return
            
            # Get window handle
            hwnd = config.connected_window.handle
            
            # Hide the main window temporarily
            self.root.withdraw()
            
            # Show instruction message
            print("Drag to select enemy HP bar detection area. Press ESC to cancel.")
            
            # Create a fullscreen window to capture clicks
            picker_window = tk.Toplevel()
            picker_window.attributes('-fullscreen', True)
            picker_window.attributes('-alpha', 0.5)  # Semi-transparent
            picker_window.configure(bg='black')
            picker_window.attributes('-topmost', True)
            
            # Create canvas to draw preview rectangle
            canvas = tk.Canvas(picker_window, bg='black', highlightthickness=0, bd=0)
            canvas.pack(fill='both', expand=True)
            
            # Add instruction label
            instruction_label = tk.Label(picker_window, 
                                       text="Click and drag to select enemy HP bar area\nRelease to confirm, Press ESC to cancel", 
                                       font=("Arial", 16), 
                                       fg="white", 
                                       bg="black")
            instruction_label.place(relx=0.5, rely=0.1, anchor="center")
            
            # Label to show current position and size
            info_label = tk.Label(picker_window, 
                                text="", 
                                font=("Arial", 12), 
                                fg="orange", 
                                bg="black")
            info_label.place(relx=0.5, rely=0.15, anchor="center")
            
            # Drag state variables
            rect_id = None
            start_x = None
            start_y = None
            dragging = False
            
            def on_button_press(event):
                nonlocal start_x, start_y, dragging, rect_id
                start_x = event.x_root
                start_y = event.y_root
                dragging = True
                # Clear any existing rectangle
                if rect_id:
                    canvas.delete(rect_id)
                    rect_id = None
            
            def on_motion(event):
                nonlocal rect_id, start_x, start_y, dragging
                if not dragging or start_x is None or start_y is None:
                    return
                
                try:
                    current_x = event.x_root
                    current_y = event.y_root
                    
                    # Get window position
                    rect = win32gui.GetWindowRect(hwnd)
                    window_x = rect[0]
                    window_y = rect[1]
                    
                    # Calculate rectangle bounds (ensure top-left is min, bottom-right is max)
                    min_x = min(start_x, current_x)
                    max_x = max(start_x, current_x)
                    min_y = min(start_y, current_y)
                    max_y = max(start_y, current_y)
                    
                    # Calculate window-relative coordinates
                    rel_x = min_x - window_x
                    rel_y = min_y - window_y
                    width = max_x - min_x
                    height = max_y - min_y
                    
                    # Update info label
                    info_label.configure(text=f"Position: ({rel_x}, {rel_y}) | Size: {width}x{height} pixels")
                    
                    # Draw preview rectangle
                    if rect_id:
                        canvas.delete(rect_id)
                    
                    rect_id = canvas.create_rectangle(
                        min_x, min_y, max_x, max_y,
                        outline='orange', width=2
                    )
                except:
                    pass
            
            def on_button_release(event):
                nonlocal start_x, start_y, dragging, rect_id
                if not dragging or start_x is None or start_y is None:
                    return
                
                try:
                    end_x = event.x_root
                    end_y = event.y_root
                    
                    # Get window position
                    rect = win32gui.GetWindowRect(hwnd)
                    window_x = rect[0]
                    window_y = rect[1]
                    
                    # Calculate rectangle bounds
                    min_x = min(start_x, end_x)
                    max_x = max(start_x, end_x)
                    min_y = min(start_y, end_y)
                    max_y = max(start_y, end_y)
                    
                    # Calculate window-relative coordinates
                    rel_x = min_x - window_x
                    rel_y = min_y - window_y
                    width = max_x - min_x
                    height = max_y - min_y
                    
                    # Ensure minimum size
                    if width < 10:
                        width = 10
                    if height < 5:
                        height = 5
                    
                    # Update the variables
                    self.enemy_hp_x_var.set(str(rel_x))
                    self.enemy_hp_y_var.set(str(rel_y))
                    self.enemy_hp_width_var.set(str(width))
                    self.enemy_hp_height_var.set(str(height))
                    self.enemy_hp_coords_var.set(f"{rel_x},{rel_y}")
                    
                    # Update global variable
                    config.target_hp_bar_area['x'] = rel_x
                    config.target_hp_bar_area['y'] = rel_y
                    config.target_hp_bar_area['width'] = width
                    config.target_hp_bar_area['height'] = height
                    
                    # Close picker window and show main window
                    picker_window.destroy()
                    self.root.deiconify()
                    
                    print(f"Enemy HP bar area set to: ({rel_x}, {rel_y}, {width}x{height})")
                    messagebox.showinfo("Enemy HP Bar Area", 
                                      f"Position: ({rel_x}, {rel_y})\nSize: {width}x{height} pixels")
                    
                    # Update button text to show it's been set
                    self.update_calibration_button_texts()
                except Exception as e:
                    print(f"Error in enemy HP bar selection: {e}")
                    picker_window.destroy()
                    self.root.deiconify()
                
                dragging = False
                start_x = None
                start_y = None
            
            def on_escape(event):
                picker_window.destroy()
                self.root.deiconify()
                print("Enemy HP bar selection cancelled")
            
            # Bind events
            picker_window.bind('<Button-1>', on_button_press)
            picker_window.bind('<B1-Motion>', on_motion)
            picker_window.bind('<ButtonRelease-1>', on_button_release)
            picker_window.bind('<Escape>', on_escape)
            picker_window.focus_set()
            
        except Exception as e:
            print(f"Error in enemy HP bar picker: {e}")
            self.root.deiconify()
    
    def pick_system_message_coordinates(self):
        """Allow user to drag and select system message area dynamically"""

        
        try:
            # Check if window is connected
            if not config.connected_window:
                messagebox.showwarning("No Window", "Please connect to a game window first!")
                return
            
            # Get window handle
            hwnd = config.connected_window.handle
            
            # Hide the main window temporarily
            self.root.withdraw()
            
            # Show instruction message
            print("Drag to select system message detection area. Press ESC to cancel.")
            
            # Create a fullscreen window to capture clicks
            picker_window = tk.Toplevel()
            picker_window.attributes('-fullscreen', True)
            picker_window.attributes('-alpha', 0.5)  # Semi-transparent
            picker_window.configure(bg='black')
            picker_window.attributes('-topmost', True)
            
            # Create canvas to draw preview rectangle
            canvas = tk.Canvas(picker_window, bg='black', highlightthickness=0, bd=0)
            canvas.pack(fill='both', expand=True)
            
            # Add instruction label
            instruction_label = tk.Label(picker_window, 
                                       text="Click and drag to select system message area\nRelease to confirm, Press ESC to cancel", 
                                       font=("Arial", 16), 
                                       fg="white", 
                                       bg="black")
            instruction_label.place(relx=0.5, rely=0.1, anchor="center")
            
            # Label to show current position and size
            info_label = tk.Label(picker_window, 
                                text="", 
                                font=("Arial", 12), 
                                fg="orange", 
                                bg="black")
            info_label.place(relx=0.5, rely=0.15, anchor="center")
            
            # Drag state variables
            rect_id = None
            dragging = False
            start_x = None
            start_y = None
            
            def on_button_press(event):
                nonlocal start_x, start_y, dragging
                start_x = event.x_root
                start_y = event.y_root
                dragging = True
            
            def on_motion(event):
                nonlocal start_x, start_y, rect_id
                if not dragging or start_x is None or start_y is None:
                    return
                
                try:
                    end_x = event.x_root
                    end_y = event.y_root
                    
                    min_x = min(start_x, end_x)
                    max_x = max(start_x, end_x)
                    min_y = min(start_y, end_y)
                    max_y = max(start_y, end_y)
                    
                    width = max_x - min_x
                    height = max_y - min_y
                    
                    # Update info label
                    info_label.configure(text=f"Size: {width}x{height} pixels")
                    
                    # Draw preview rectangle
                    if rect_id:
                        canvas.delete(rect_id)
                    
                    rect_id = canvas.create_rectangle(
                        min_x, min_y, max_x, max_y,
                        outline='orange', width=2
                    )
                except:
                    pass
            
            def on_button_release(event):
                nonlocal start_x, start_y, dragging, rect_id
                if not dragging or start_x is None or start_y is None:
                    return
                
                try:
                    end_x = event.x_root
                    end_y = event.y_root
                    
                    # Get window position
                    rect = win32gui.GetWindowRect(hwnd)
                    window_x = rect[0]
                    window_y = rect[1]
                    
                    # Calculate rectangle bounds
                    min_x = min(start_x, end_x)
                    max_x = max(start_x, end_x)
                    min_y = min(start_y, end_y)
                    max_y = max(start_y, end_y)
                    
                    # Calculate window-relative coordinates
                    rel_x = min_x - window_x
                    rel_y = min_y - window_y
                    width = max_x - min_x
                    height = max_y - min_y
                    
                    # Ensure minimum size
                    if width < 10:
                        width = 10
                    if height < 5:
                        height = 5
                    
                    # Calculate center coordinates
                    center_x = rel_x + (width // 2)
                    center_y = rel_y + (height // 2)
                    
                    # Update global variable (using center point for x,y)
                    config.system_message_area['x'] = center_x
                    config.system_message_area['y'] = center_y
                    config.system_message_area['width'] = width
                    config.system_message_area['height'] = height
                    
                    # Close picker window and show main window
                    picker_window.destroy()
                    self.root.deiconify()
                    
                    print(f"System message area set to: Center ({center_x}, {center_y}), Size {width}x{height}")
                    messagebox.showinfo("System Message Area", 
                                      f"Center: ({center_x}, {center_y})\nSize: {width}x{height} pixels")
                    
                    # Update button text to show it's been set
                    self.update_calibration_button_texts()
                except Exception as e:
                    print(f"Error in system message coordinate selection: {e}")
                    picker_window.destroy()
                    self.root.deiconify()
                
                dragging = False
                start_x = None
                start_y = None
            
            def on_escape(event):
                # Close picker window and show main window
                picker_window.destroy()
                self.root.deiconify()
                print("System message coordinate picking cancelled")
            
            # Bind events
            picker_window.bind('<Button-1>', on_button_press)
            picker_window.bind('<B1-Motion>', on_motion)
            picker_window.bind('<ButtonRelease-1>', on_button_release)
            picker_window.bind('<Escape>', on_escape)
            picker_window.focus_set()
            
        except Exception as e:
            print(f"Error in system message coordinate picker: {e}")
            # Make sure main window is shown
            self.root.deiconify()
    
    def update_calibration_button_texts(self):
        """Update calibration button texts to show if areas are already set"""

        
        # Check if Player HP is set (has valid width and height)
        if config.hp_bar_area.get('width', 0) > 0 and config.hp_bar_area.get('height', 0) > 0:
            self.hp_calib_btn.configure(text="✓ Player HP")
        else:
            self.hp_calib_btn.configure(text="Set Player HP")
        
        # Check if Player MP is set
        if config.mp_bar_area.get('width', 0) > 0 and config.mp_bar_area.get('height', 0) > 0:
            self.mp_calib_btn.configure(text="✓ Player MP")
        else:
            self.mp_calib_btn.configure(text="Set Player MP")
        
        # Check if Enemy HP is set
        if config.target_hp_bar_area.get('width', 0) > 0 and config.target_hp_bar_area.get('height', 0) > 0:
            self.enemy_hp_calib_btn.configure(text="✓ Enemy HP")
        else:
            self.enemy_hp_calib_btn.configure(text="Set Enemy HP")
        
        # Check if Enemy Name is set
        if config.target_name_area.get('width', 0) > 0 and config.target_name_area.get('height', 0) > 0:
            self.enemy_name_calib_btn.configure(text="✓ Enemy Name")
        else:
            self.enemy_name_calib_btn.configure(text="Set Enemy Name")
        
        # Check if System Message is set
        if config.system_message_area.get('width', 0) > 0 and config.system_message_area.get('height', 0) > 0:
            self.system_message_calib_btn.configure(text="✓ System Message")
        else:
            self.system_message_calib_btn.configure(text="Set System Message")
    
    def update_mob_coordinates(self):
        """Update mob name detection coordinates"""

        try:
            # Parse coordinates from the display string
            coords_str = self.mob_coords_var.get()
            x, y = map(int, coords_str.split(','))
            
            config.target_name_area['x'] = x
            config.target_name_area['y'] = y
            config.target_name_area['width'] = int(self.mob_width_var.get())
            config.target_name_area['height'] = int(self.mob_height_var.get())
            
            print(f"Updated mob coordinates: {config.target_name_area}")
        except (ValueError, AttributeError) as e:
            print(f"Invalid coordinates - please enter numbers only: {e}")
    
    def update_skip_list(self):
        """Update mob skip list"""

        skip_text = self.skip_list_text.get("1.0", tk.END).strip()
        config.mob_skip_list = [line.strip() for line in skip_text.split('\n') if line.strip()]
        print(f"Updated skip list: {config.mob_skip_list}")
    
    def test_mob_detection(self):
        """Test mob detection and display result"""
        mob_name = mob_detection.detect_mob_name()
        if mob_name:
            self.current_mob_label.configure(text=mob_name, text_color="green")
            if mob_detection.should_skip_current_mob():
                self.current_mob_label.configure(text_color="orange")
                print(f"TEST: Mob '{mob_name}' would be SKIPPED")
            else:
                print(f"TEST: Mob '{mob_name}' would be ATTACKED")
        else:
            self.current_mob_label.configure(text="None", text_color="red")
            print("TEST: No mob detected")
    
    # Legacy functions removed - no longer needed with OCR mode
    
    
    # Calibration function removed - Tesseract OCR is automatic, no calibration needed!
    
    def process_gui_updates(self):
        """Process queued GUI updates from background threads (thread-safe)"""
        try:
            # Process up to 100 updates per cycle to prevent blocking
            for _ in range(100):
                update_func = config.gui_update_queue.get_nowait()
                update_func()  # Execute the queued GUI update
        except queue.Empty:
            pass  # No more updates to process
        
        # Schedule next check (every 50ms for responsive UI)
        self.root.after(50, self.process_gui_updates)
    
    def run(self):
        # Start processing GUI updates from background threads
        self.process_gui_updates()
        self.root.mainloop()
