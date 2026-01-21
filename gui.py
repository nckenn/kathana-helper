"""
GUI module for Kathana Bot
Refactored to use modular structure
"""
import tkinter as tk
from tkinter import messagebox, simpledialog
import customtkinter as ctk
import threading
import time
import win32gui
import queue
import os
import sys
import config
import window_utils
import settings_manager
import bot_logic
import input_handler
import auto_attack
import ocr_utils
import calibration

class BotGUI:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BotGUI, cls).__new__(cls)
        return cls._instance
    
    def check_ocr_on_startup(self):
        """Check OCR availability on startup and show warning if not available"""
        print("Checking OCR availability...")
        is_available, error_msg, mode, troubleshooting = ocr_utils.check_ocr_availability()
        
        # Store OCR availability in config
        config.ocr_available = is_available
        config.ocr_mode = mode
        
        if not is_available:
            error_details = f"\n\nError: {error_msg}" if error_msg else ""
            troubleshooting_text = f"\n\n{troubleshooting}" if troubleshooting else ""
            warning_message = (
                "OCR (Optical Character Recognition) is not available on this system.\n\n"
                "Features that require OCR (such as auto-repair, damage detection, etc.) "
                "will not work."
                f"{error_details}"
                f"{troubleshooting_text}\n\n"
                "You can re-check OCR availability from the Settings tab after fixing the issue."
            )
            messagebox.showwarning("OCR Not Available", warning_message)
            print("WARNING: OCR is not available - OCR features will be disabled")
        else:
            print(f"OCR check passed - Available in {mode.upper()} mode")
    
    def update_ocr_status_display(self):
        """Update the OCR status display in the Settings tab"""
        if not hasattr(self, 'ocr_status_text'):
            return  # GUI elements not created yet
        
        if config.ocr_available:
            status_text = f"✓ Available ({config.ocr_mode.upper()} mode)"
            self.ocr_status_text.configure(text=status_text, text_color="green")
        else:
            status_text = "✗ Not Available"
            self.ocr_status_text.configure(text=status_text, text_color="red")
    
    def recheck_ocr_availability(self):
        """Re-check OCR availability (called from GUI button)"""
        # Disable button during check
        self.recheck_ocr_button.configure(state="disabled", text="Checking...")
        self.ocr_status_text.configure(text="Checking...", text_color="gray")
        
        # Run in a separate thread to avoid blocking GUI
        def check_thread():
            try:
                is_available, error_msg, mode, troubleshooting = ocr_utils.recheck_ocr_availability()
                
                # Update status display in GUI thread
                def update_gui():
                    self.update_ocr_status_display()
                    self.recheck_ocr_button.configure(state="normal", text="Re-check OCR")
                    
                    if is_available:
                        messagebox.showinfo("OCR Status", 
                            f"OCR is now available in {config.ocr_mode.upper()} mode!\n\n"
                            "OCR features are now enabled.")
                    else:
                        error_details = f"\n\nError: {error_msg}" if error_msg else ""
                        troubleshooting_text = f"\n\n{troubleshooting}" if troubleshooting else ""
                        messagebox.showwarning("OCR Status", 
                            "OCR is still not available."
                            f"{error_details}"
                            f"{troubleshooting_text}")
                
                # Schedule GUI update in main thread
                self.root.after(0, update_gui)
            except Exception as e:
                def show_error():
                    self.recheck_ocr_button.configure(state="normal", text="Re-check OCR")
                    messagebox.showerror("OCR Check Error", f"Error checking OCR: {e}")
                self.root.after(0, show_error)
        
        threading.Thread(target=check_thread, daemon=True).start()
    
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
            
            # Apply Mage setting
            if hasattr(self, 'is_mage_var'):
                self.is_mage_var.set(config.is_mage)
                print(f"  Applied mage: enabled={config.is_mage}")
            
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
            
            # Apply buffs settings
            if hasattr(self, 'buffs_vars') and hasattr(self, 'buffs_keys') and hasattr(self, 'buffs_canvases'):
                for i in range(8):
                    try:
                        # Update enabled state
                        self.buffs_vars[i].set(config.buffs_config[i]['enabled'])
                        # Update key
                        self.buffs_keys[i].set(config.buffs_config[i]['key'])
                        # Load image if exists - resolve relative path
                        if config.buffs_config[i]['image_path']:
                            image_path = self.convert_to_absolute_path(config.buffs_config[i]['image_path'])
                            if image_path and os.path.exists(image_path):
                                # Keep relative path in config, use absolute for loading
                                self.buffs_state[i]['image_path'] = config.buffs_config[i]['image_path']
                                # Load and display the image
                                self.load_buff_image(i, image_path)
                                # Sync with buffs manager (use relative path)
                                if config.buffs_manager:
                                    if config.buffs_config[i]['enabled']:
                                        config.buffs_manager.set_buff(i, config.buffs_config[i]['image_path'])
                                    else:
                                        config.buffs_manager.clear_buff(i)
                                print(f"  Applied buff {i+1}: enabled={config.buffs_config[i]['enabled']}, key={config.buffs_config[i]['key']}, path={config.buffs_config[i]['image_path']}")
                            else:
                                print(f"  Buff {i+1} image path not found: {config.buffs_config[i]['image_path']}")
                                self.clear_buff_skill(i)
                        else:
                            self.clear_buff_skill(i)
                            # Update buffs manager
                            if config.buffs_manager:
                                config.buffs_manager.clear_buff(i)
                    except Exception as e:
                        print(f"  Error applying buff {i+1} settings: {e}")
                        import traceback
                        traceback.print_exc()
            
            # Apply skill sequence settings
            if hasattr(self, 'skill_sequence_vars') and hasattr(self, 'skill_sequence_keys') and hasattr(self, 'skill_sequence_canvases'):
                for i in range(8):
                    try:
                        # Update enabled state
                        self.skill_sequence_vars[i].set(config.skill_sequence_config[i]['enabled'])
                        # Update key
                        self.skill_sequence_keys[i].set(config.skill_sequence_config[i].get('key', ''))
                        # Load image if exists - resolve relative path
                        if config.skill_sequence_config[i].get('image_path'):
                            image_path = self.convert_to_absolute_path(config.skill_sequence_config[i]['image_path'])
                            if image_path and os.path.exists(image_path):
                                # Keep relative path in config, use absolute for loading
                                self.skill_sequence_state[i]['image_path'] = config.skill_sequence_config[i]['image_path']
                                # Load and display the image
                                self.load_skill_sequence_image(i, image_path)
                                # Sync with skill sequence manager (use relative path)
                                if config.skill_sequence_manager:
                                    if config.skill_sequence_config[i]['enabled']:
                                        config.skill_sequence_manager.set_skill(i, config.skill_sequence_config[i]['image_path'])
                                    else:
                                        config.skill_sequence_manager.clear_skill(i)
                                print(f"  Applied skill sequence {i+1}: enabled={config.skill_sequence_config[i]['enabled']}, key={config.skill_sequence_config[i].get('key', '')}, path={config.skill_sequence_config[i]['image_path']}")
                            else:
                                print(f"  Skill Sequence {i+1} image path not found: {config.skill_sequence_config[i]['image_path']}")
                                self.clear_skill_sequence_skill(i)
                        else:
                            self.clear_skill_sequence_skill(i)
                            # Update skill sequence manager
                            if config.skill_sequence_manager:
                                config.skill_sequence_manager.clear_skill(i)
                    except Exception as e:
                        print(f"  Error applying skill sequence {i+1} settings: {e}")
                        import traceback
                        traceback.print_exc()
            
            # Apply target list
            target_text = '\n'.join(config.mob_target_list)
            self.target_list_text.delete("1.0", tk.END)
            self.target_list_text.insert("1.0", target_text)
            
            # Apply selected window
            if config.selected_window:
                self.window_var.set(config.selected_window)
                # Try to refresh and select the window
                self.refresh_windows_with_selection(config.selected_window)
            
            # Update toggle bot button state after applying settings
            self.update_toggle_bot_button_state()
            
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
        self.root.title("Kathana Helper by xCrypto v2.1.0")
        self.root.geometry("655x800")
        self.root.resizable(True, True)
        
        # Track minimized state
        self.is_minimized = False
        self.minimized_window = None
        self.saved_window_position = None  # Store window position when minimizing
        
        # Track last active tab in skill selector
        self.last_skill_selector_tab = None
        
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
        
        # Minimize/Maximize button
        self.minimize_button = ctk.CTkButton(status_info_frame, text="−", command=self.toggle_minimize, width=30, height=25, font=ctk.CTkFont(size=16, weight="bold"))
        self.minimize_button.grid(row=0, column=2, padx=(10, 10), pady=6)
        
        # Bot control frame - fixed height to prevent fluid expansion
        bot_frame = ctk.CTkFrame(main_frame, corner_radius=8)
        bot_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 0), padx=10)
        # Set minimum height to prevent frame from expanding
        bot_frame.grid_rowconfigure(0, weight=0)  # Don't allow row to expand
        
        # Connect button
        self.connect_button = ctk.CTkButton(bot_frame, text="Connect", command=self.connect_window, width=120, height=32, corner_radius=6)
        self.connect_button.grid(row=0, column=0, padx=(10, 5), pady=5)
        
        # Calibrate button
        self.calibrate_button = ctk.CTkButton(bot_frame, text="Calibrate", command=self.calibrate_bars, width=100, height=32, corner_radius=6, state="disabled")
        self.calibrate_button.grid(row=0, column=1, padx=5, pady=5)
        
        # Start/Stop toggle button
        self.toggle_bot_button = ctk.CTkButton(bot_frame, text="Start", command=self.toggle_bot, state="disabled", width=100, height=32, corner_radius=6, fg_color="green", hover_color="darkgreen")
        self.toggle_bot_button.grid(row=0, column=2, padx=5, pady=5)
        
        # Separator frame (using a thin frame as separator) - fixed height to match buttons
        separator = ctk.CTkFrame(bot_frame, width=2, height=40, fg_color="gray50")
        separator.grid(row=0, column=4, padx=6, pady=5)
        
        # Save Settings button
        self.save_settings_button = ctk.CTkButton(bot_frame, text="Save Settings", command=self.save_settings_gui, width=110, height=32, corner_radius=6)
        self.save_settings_button.grid(row=0, column=5, padx=5, pady=5)
        
        # Load Settings button
        self.load_settings_button = ctk.CTkButton(bot_frame, text="Load Settings", command=self.load_settings_gui, width=110, height=32, corner_radius=6)
        self.load_settings_button.grid(row=0, column=6, padx=(5, 10), pady=5)
        
        # Create tabview for all sections
        tabview = ctk.CTkTabview(main_frame, corner_radius=8)
        tabview.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(0, 10), padx=10)
        
        # Configure tabview to expand
        main_frame.rowconfigure(3, weight=1)
        
        # Create tabs
        status_tab = tabview.add("Status")
        settings_tab = tabview.add("Settings")
        skill_sequence_tab = tabview.add("Skill Sequence")
        skills_tab = tabview.add("Skill Interval")
        buffs_tab = tabview.add("Buffs")
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
        self.enemy_hp_percent_label.grid(row=0, column=2)
        
        # Enemy Name display
        enemy_name_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
        enemy_name_frame.grid(row=3, column=0, sticky="w", padx=15, pady=(5, 5))
        
        enemy_name_label = ctk.CTkLabel(enemy_name_frame, text="Enemy Name:", width=70, anchor='w', font=ctk.CTkFont(size=11))
        enemy_name_label.grid(row=0, column=0, padx=(0, 10))
        self.current_mob_label = ctk.CTkLabel(enemy_name_frame, text="None", width=170, anchor='w', font=ctk.CTkFont(size=11), text_color="red")
        self.current_mob_label.grid(row=0, column=1, sticky="w", padx=(0, 10))
        self.unstuck_countdown_label = ctk.CTkLabel(enemy_name_frame, text="Unstuck: ---", font=ctk.CTkFont(size=10), text_color="gray")
        self.unstuck_countdown_label.grid(row=0, column=2)
        
        # Auto Repair Count display
        auto_repair_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
        auto_repair_frame.grid(row=4, column=0, sticky="w", padx=15, pady=(5, 15))
        
        auto_repair_label = ctk.CTkLabel(auto_repair_frame, text="Auto Repair:", width=70, anchor='w', font=ctk.CTkFont(size=11))
        auto_repair_label.grid(row=0, column=0, padx=(0, 10))
        self.auto_repair_count_label = ctk.CTkLabel(auto_repair_frame, text="0/3", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray")
        self.auto_repair_count_label.grid(row=0, column=1, sticky="w")
        
        # Configure status frame grid
        status_frame.columnconfigure(0, weight=1)
        
        # Options frame - moved to Settings tab
        settings_frame = settings_tab
        
        # Configure settings frame for 2 columns with padding
        settings_frame.columnconfigure(0, weight=1)
        settings_frame.columnconfigure(1, weight=1)
        settings_frame.rowconfigure(0, weight=0)
        settings_frame.rowconfigure(1, weight=0)
        settings_frame.rowconfigure(2, weight=0)
        settings_frame.rowconfigure(3, weight=0)
        settings_frame.rowconfigure(4, weight=0)
        
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
        
        # Mage frame
        mage_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        mage_frame.grid(row=4, column=0, sticky="ew", padx=(15, 5), pady=(0, 0))
        
        # Mage checkbox
        self.is_mage_var = tk.BooleanVar(value=config.is_mage)
        mage_checkbox = ctk.CTkCheckBox(mage_frame, text="Mage?", 
                                         variable=self.is_mage_var,
                                         command=self.update_is_mage,
                                         font=ctk.CTkFont(size=11))
        mage_checkbox.grid(row=0, column=0, sticky="w", pady=5)
        
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
        
        # OCR Status frame (row 0, spans both columns)
        ocr_status_frame = ctk.CTkFrame(settings_frame, corner_radius=8)
        ocr_status_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=15, pady=(10, 5))
        ocr_status_frame.columnconfigure(1, weight=1)
        
        # OCR Status label
        ocr_status_label = ctk.CTkLabel(ocr_status_frame, text="OCR Status:", font=ctk.CTkFont(size=12, weight="bold"))
        ocr_status_label.grid(row=0, column=0, sticky="w", padx=(10, 5), pady=10)
        
        # OCR Status indicator
        self.ocr_status_text = ctk.CTkLabel(ocr_status_frame, 
                                           text="Checking...", 
                                           font=ctk.CTkFont(size=11))
        self.ocr_status_text.grid(row=0, column=1, sticky="w", padx=5, pady=10)
        
        # Re-check OCR button
        self.recheck_ocr_button = ctk.CTkButton(ocr_status_frame, 
                                                text="Re-check OCR", 
                                                command=self.recheck_ocr_availability,
                                                width=120, 
                                                height=28, 
                                                corner_radius=6)
        self.recheck_ocr_button.grid(row=0, column=2, padx=(5, 10), pady=10)
        
        # Update OCR status display
        self.update_ocr_status_display()
        
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
        
        mob_label = ctk.CTkLabel(settings_frame, text="Mob Filter", font=ctk.CTkFont(size=12, weight="bold"))
        mob_label.grid(row=5, column=0, columnspan=2, sticky="w", padx=15, pady=(5, 5))
        
        # Mob detection checkbox
        self.mob_detection_var = tk.BooleanVar()
        mob_checkbox = ctk.CTkCheckBox(settings_frame, text="Enable", 
                                     variable=self.mob_detection_var,
                                     command=self.update_mob_detection,
                                     font=ctk.CTkFont(size=11))
        mob_checkbox.grid(row=6, column=0, columnspan=2, sticky="w", padx=15, pady=(0, 5))
        
        # Target list
        ctk.CTkLabel(settings_frame, text="Target List (one per line, only attack mobs in this list):", font=ctk.CTkFont(size=11)).grid(row=7, column=0, columnspan=2, sticky="w", padx=15, pady=(5, 5))
        self.target_list_text = ctk.CTkTextbox(settings_frame, height=150, width=400, font=ctk.CTkFont(size=11))
        self.target_list_text.grid(row=8, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 5))
        
        # Mob filter buttons
        mob_btn_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        mob_btn_frame.grid(row=9, column=0, columnspan=2, sticky="ew", padx=15, pady=(10, 15))
        
        update_btn = ctk.CTkButton(mob_btn_frame, text="Update List", command=self.update_target_list, width=100, corner_radius=6)
        update_btn.grid(row=0, column=0, padx=(0, 10))
        
        test_btn = ctk.CTkButton(mob_btn_frame, text="Test", command=self.test_mob_detection, width=100, corner_radius=6)
        test_btn.grid(row=0, column=1, padx=(0, 10))
        
        # Record button - captures current enemy name automatically
        is_calibrated = config.calibrator is not None and config.calibrator.mp_position is not None and config.connected_window is not None
        self.record_target_btn = ctk.CTkButton(mob_btn_frame, text="Record", command=self.record_target_mob, width=100, corner_radius=6, 
                                  state="normal" if is_calibrated else "disabled")
        self.record_target_btn.grid(row=0, column=2)
        
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
        
        # Skill Sequence frame - moved to Skill Sequence tab
        skill_sequence_frame = skill_sequence_tab
        
        # Initialize skill sequence variables
        self.skill_sequence_vars = {}
        self.skill_sequence_keys = []
        self.skill_sequence_canvases = []
        self.skill_sequence_state = []
        
        # Title label
        skill_sequence_title = ctk.CTkLabel(skill_sequence_frame, text="Skill Sequence Configuration", 
                                           font=ctk.CTkFont(size=14, weight="bold"))
        skill_sequence_title.grid(row=0, column=0, columnspan=4, sticky="w", padx=15, pady=(15, 10))
        
        # Create skill sequence slots in a grid (first column: 1-4, second column: 5-8)
        for i in range(8):
            if i < 4:
                # First column: slots 1-4
                row = i + 1
                col = 0
            else:
                # Second column: slots 5-8
                row = i - 3  # i=4->row=1, i=5->row=2, i=6->row=3, i=7->row=4
                col = 2
            
            # Create frame for each skill sequence slot
            skill_slot_frame = ctk.CTkFrame(skill_sequence_frame, corner_radius=8)
            padx_left = 15 if col == 0 else 5
            padx_right = 5 if col == 0 else 15
            skill_slot_frame.grid(row=row, column=col, columnspan=2, sticky="ew", 
                                 padx=(padx_left, padx_right), pady=5)
            
            # Enable checkbox
            self.skill_sequence_vars[i] = tk.BooleanVar(value=config.skill_sequence_config[i]['enabled'])
            checkbox = ctk.CTkCheckBox(skill_slot_frame, text=f"Skill {i+1}", 
                                      variable=self.skill_sequence_vars[i],
                                      command=lambda idx=i: self.update_skill_sequence_enabled(idx),
                                      font=ctk.CTkFont(size=11))
            checkbox.grid(row=0, column=0, padx=10, pady=5, sticky="w")
            
            # Skill image canvas (clickable to select skill)
            canvas_frame = ctk.CTkFrame(skill_slot_frame, fg_color="transparent")
            canvas_frame.grid(row=1, column=0, padx=10, pady=5)
            
            canvas = tk.Canvas(canvas_frame, width=48, height=48, bg='gray20', 
                             highlightthickness=1, highlightbackground='gray50')
            canvas.grid(row=0, column=0, padx=5)
            canvas.bind('<Button-1>', lambda e, idx=i: self.show_skill_sequence_selector(idx))
            canvas.bind('<Button-3>', lambda e, idx=i: self.clear_skill_sequence_skill(idx))
            self.skill_sequence_canvases.append(canvas)
            
            # Key registration button
            key_frame = ctk.CTkFrame(skill_slot_frame, fg_color="transparent")
            key_frame.grid(row=1, column=1, padx=10, pady=5, sticky="w")
            
            key_label = ctk.CTkLabel(key_frame, text="Key:", font=ctk.CTkFont(size=11))
            key_label.grid(row=0, column=0, padx=(0, 5))
            
            key_var = tk.StringVar(value=config.skill_sequence_config[i].get('key', ''))
            self.skill_sequence_keys.append(key_var)
            
            key_button = ctk.CTkButton(key_frame, textvariable=key_var, width=50, height=30,
                                     command=lambda idx=i: self.register_skill_sequence_key(idx),
                                     font=ctk.CTkFont(size=11))
            key_button.grid(row=0, column=1, padx=(0, 5))
            
            # Clear key button (right-click)
            key_button.bind('<Button-3>', lambda e, idx=i: self.clear_skill_sequence_key(idx))
            
            # Initialize skill sequence state
            self.skill_sequence_state.append({
                'image_path': config.skill_sequence_config[i].get('image_path'),
                'enabled': config.skill_sequence_config[i]['enabled']
            })
            
            # Load skill image if exists - convert relative paths to absolute
            if config.skill_sequence_config[i].get('image_path'):
                image_path = self.convert_to_absolute_path(config.skill_sequence_config[i]['image_path'])
                if image_path and os.path.exists(image_path):
                    # load_skill_sequence_image will convert to relative and store in config
                    self.load_skill_sequence_image(i, image_path)
                else:
                    print(f"Skill Sequence {i+1} image path not found: {config.skill_sequence_config[i]['image_path']}")
                    config.skill_sequence_config[i]['image_path'] = None
                    self.skill_sequence_state[i]['image_path'] = None
        
        # Configure skill sequence frame grid
        skill_sequence_frame.columnconfigure(0, weight=1)
        skill_sequence_frame.columnconfigure(2, weight=1)
        
        # Initialize skill sequence manager
        import skill_sequence_manager
        config.skill_sequence_manager = skill_sequence_manager.SkillSequenceManager(num_skills=8)
        config.skill_sequence_manager.set_ui_reference(self)
        
        # Skill slots frame - moved to Skill Interval tab
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
        
        # Buffs frame - moved to Buffs tab
        buffs_frame = buffs_tab
        
        # Initialize buffs variables
        self.buffs_vars = {}
        self.buffs_keys = []
        self.buffs_canvases = []
        self.buffs_state = []
        
        # Title label
        buffs_title = ctk.CTkLabel(buffs_frame, text="Buffs Configuration", 
                                   font=ctk.CTkFont(size=14, weight="bold"))
        buffs_title.grid(row=0, column=0, columnspan=4, sticky="w", padx=15, pady=(15, 10))
        
        # Create buff slots in a grid (first column: 1-4, second column: 5-8)
        for i in range(8):
            if i < 4:
                # First column: slots 1-4
                row = i + 1
                col = 0
            else:
                # Second column: slots 5-8
                row = i - 3  # i=4->row=1, i=5->row=2, i=6->row=3, i=7->row=4
                col = 2
            
            # Create frame for each buff slot
            buff_slot_frame = ctk.CTkFrame(buffs_frame, corner_radius=8)
            padx_left = 15 if col == 0 else 5
            padx_right = 5 if col == 0 else 15
            buff_slot_frame.grid(row=row, column=col, columnspan=2, sticky="ew", 
                               padx=(padx_left, padx_right), pady=5)
            
            # Enable checkbox
            self.buffs_vars[i] = tk.BooleanVar(value=config.buffs_config[i]['enabled'])
            checkbox = ctk.CTkCheckBox(buff_slot_frame, text=f"Buff {i+1}", 
                                      variable=self.buffs_vars[i],
                                      command=lambda idx=i: self.update_buff_enabled(idx),
                                      font=ctk.CTkFont(size=11))
            checkbox.grid(row=0, column=0, padx=10, pady=5, sticky="w")
            
            # Skill image canvas (clickable to select skill)
            canvas_frame = ctk.CTkFrame(buff_slot_frame, fg_color="transparent")
            canvas_frame.grid(row=1, column=0, padx=10, pady=5)
            
            canvas = tk.Canvas(canvas_frame, width=48, height=48, bg='gray20', 
                             highlightthickness=1, highlightbackground='gray50')
            canvas.grid(row=0, column=0, padx=5)
            canvas.bind('<Button-1>', lambda e, idx=i: self.show_buff_skill_selector(idx))
            canvas.bind('<Button-3>', lambda e, idx=i: self.clear_buff_skill(idx))
            self.buffs_canvases.append(canvas)
            
            # Key registration button
            key_frame = ctk.CTkFrame(buff_slot_frame, fg_color="transparent")
            key_frame.grid(row=1, column=1, padx=10, pady=5, sticky="w")
            
            key_label = ctk.CTkLabel(key_frame, text="Key:", font=ctk.CTkFont(size=11))
            key_label.grid(row=0, column=0, padx=(0, 5))
            
            key_var = tk.StringVar(value=config.buffs_config[i]['key'])
            self.buffs_keys.append(key_var)
            
            key_button = ctk.CTkButton(key_frame, textvariable=key_var, width=50, height=30,
                                     command=lambda idx=i: self.register_buff_key(idx),
                                     font=ctk.CTkFont(size=11))
            key_button.grid(row=0, column=1, padx=(0, 5))
            
            # Clear key button (right-click)
            key_button.bind('<Button-3>', lambda e, idx=i: self.clear_buff_key(idx))
            
            # Initialize buff state
            self.buffs_state.append({
                'image_path': config.buffs_config[i]['image_path'],
                'enabled': config.buffs_config[i]['enabled']
            })
            
            # Load buff image if exists - convert relative paths to absolute
            if config.buffs_config[i]['image_path']:
                image_path = self.convert_to_absolute_path(config.buffs_config[i]['image_path'])
                if image_path and os.path.exists(image_path):
                    # load_buff_image will convert to relative and store in config
                    self.load_buff_image(i, image_path)
                else:
                    print(f"Buff {i+1} image path not found: {config.buffs_config[i]['image_path']}")
                    config.buffs_config[i]['image_path'] = None
                    self.buffs_state[i]['image_path'] = None
        
        # Configure buffs frame grid
        buffs_frame.columnconfigure(0, weight=1)
        buffs_frame.columnconfigure(2, weight=1)
        
        # Initialize buffs manager
        import buffs_manager
        config.buffs_manager = buffs_manager.BuffsManager(num_buffs=8)
        config.buffs_manager.set_ui_reference(self)
        
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
        
        # Update Start/Stop button state based on calibration
        self.update_toggle_bot_button_state()
        
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
            self.toggle_bot_button.configure(state="disabled")
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
            self.calibrate_button.configure(state="normal")
            # Don't enable toggle button here - it will be enabled when calibrated
            self.update_toggle_bot_button_state()
            self.connection_label.configure(text=f"Window: {selected_window_title}")
            self.status_label.configure(text="Status: Connected")
            print(f"Successfully connected to: {selected_window_title}")
        else:
            self.connect_button.configure(text="Connect")
            self.calibrate_button.configure(state="disabled")
            self.toggle_bot_button.configure(state="disabled")
            self.connection_label.configure(text="Window: Connection Failed")
            self.status_label.configure(text="Status: Connection Failed")
            print(f"Failed to connect to: {selected_window_title}")

    def calibrate_bars(self):
        """Perform auto-calibration to detect HP/MP bar positions"""
        if not config.connected_window:
            messagebox.showwarning("Not Connected", "Please connect to a window first")
            return
        
        # Disable button during calibration
        self.calibrate_button.configure(state="disabled", text="Calibrating...")
        
        def calibration_thread():
            try:
                hwnd = config.connected_window.handle
                
                # Create calibrator instance
                calibrator = calibration.Calibrator()
                
                # Perform calibration
                success = calibrator.calibrate(hwnd)
                
                if success:
                    # Update config with calibrated positions
                    if calibrator.hp_position:
                        config.hp_bar_area['x'] = calibrator.hp_position[0]
                        config.hp_bar_area['y'] = calibrator.hp_position[1]
                        config.hp_bar_area['width'] = calibrator.hp_dimensions[0]
                        config.hp_bar_area['height'] = calibrator.hp_dimensions[1]
                        print(f"[Calibration] HP bar position set: {calibrator.hp_position}")
                    
                    if calibrator.mp_position:
                        config.mp_bar_area['x'] = calibrator.mp_position[0]
                        config.mp_bar_area['y'] = calibrator.mp_position[1]
                        config.mp_bar_area['width'] = calibrator.mp_dimensions[0]
                        config.mp_bar_area['height'] = calibrator.mp_dimensions[1]
                        print(f"[Calibration] MP bar position set: {calibrator.mp_position}")
                    
                    # Store calibrator instance in config for later use
                    config.calibrator = calibrator
                    
                    # Calculate and store area_skills
                    if (calibrator.skills_bar1_position and calibrator.skills_bar2_position):
                        try:
                            import cv2
                            x1, y1 = calibrator.skills_bar1_position
                            x2, y2 = calibrator.skills_bar2_position
                            
                            # Load skill bar templates to get dimensions
                            current_dir = os.path.dirname(os.path.abspath(__file__))
                            bar1_path = os.path.join(current_dir, 'skill_bar_1.bmp')
                            bar2_path = os.path.join(current_dir, 'skill_bar_2.bmp')
                            
                            if os.path.exists(bar1_path) and os.path.exists(bar2_path):
                                bar1 = cv2.imread(bar1_path)
                                bar2 = cv2.imread(bar2_path)
                                
                                if bar1 is not None and bar2 is not None:
                                    bar1_h, bar1_w = bar1.shape[:2]
                                    bar2_h, bar2_w = bar2.shape[:2]
                                    x_min = min(x1, x2)
                                    y_min = min(y1, y2)
                                    x_max = max(x1 + bar1_w, x2 + bar2_w)
                                    y_max_original = max(y1 + bar1_h, y2 + bar2_h)
                                    original_height = y_max_original - y_min
                                    new_height = original_height * 5
                                    y_max_new = y_min + new_height
                                    config.area_skills = (x_min, y_min, x_max, y_max_new)
                                    print(f"[Calibration] Skills area set: {config.area_skills}")
                        except Exception as e:
                            print(f"[Calibration] Error calculating skills area: {e}")
                    
                    # Store system message area if found
                    if calibrator.system_message_area:
                        try:
                            x, y, width, height = calibrator.system_message_area
                            config.system_message_area = {
                                'x': x,
                                'y': y,
                                'width': width,
                                'height': height
                            }
                            print(f"[Calibration] System message area set: {config.system_message_area}")
                        except Exception as e:
                            print(f"[Calibration] Error storing system message area: {e}")
                    
                    # Update GUI with calibrated values
                    def update_gui():
                        try:
                            self.hp_x_var.set(str(config.hp_bar_area['x']))
                            self.hp_y_var.set(str(config.hp_bar_area['y']))
                            self.hp_width_var.set(str(config.hp_bar_area['width']))
                            self.hp_height_var.set(str(config.hp_bar_area['height']))
                            self.hp_coords_var.set(f"{config.hp_bar_area['x']},{config.hp_bar_area['y']}")
                            
                            self.mp_x_var.set(str(config.mp_bar_area['x']))
                            self.mp_y_var.set(str(config.mp_bar_area['y']))
                            self.mp_width_var.set(str(config.mp_bar_area['width']))
                            self.mp_height_var.set(str(config.mp_bar_area['height']))
                            self.mp_coords_var.set(f"{config.mp_bar_area['x']},{config.mp_bar_area['y']}")
                            
                            self.calibrate_button.configure(state="normal", text="Calibrate")
                            # Enable record button if calibration successful
                            if hasattr(self, 'record_target_btn'):
                                self.record_target_btn.configure(state="normal")
                            # Update toggle bot button state to enable Start button
                            self.update_toggle_bot_button_state()
                            messagebox.showinfo("Calibration Success", 
                                f"Calibration completed successfully!\n\n"
                                f"HP Bar: ({config.hp_bar_area['x']}, {config.hp_bar_area['y']})\n"
                                f"MP Bar: ({config.mp_bar_area['x']}, {config.mp_bar_area['y']})")
                        except Exception as e:
                            print(f"[Calibration] Error updating GUI: {e}")
                            self.calibrate_button.configure(state="normal", text="Calibrate")
                    
                    self.root.after(0, update_gui)
                else:
                    def show_error():
                        self.calibrate_button.configure(state="normal", text="Calibrate")
                        messagebox.showerror("Calibration Failed", 
                            "Failed to detect HP/MP bars.\n\n"
                            "Please ensure:\n"
                            "1. The game window is visible\n"
                            "2. HP/MP bars are visible on screen\n"
                            "3. No other red/blue UI elements are blocking the bars\n"
                            "4. Make sure HP/MP bars are full")
                    
                    self.root.after(0, show_error)
                    
            except Exception as e:
                print(f"[Calibration] Error during calibration: {e}")
                import traceback
                traceback.print_exc()
                
                def show_error():
                    self.calibrate_button.configure(state="normal", text="Calibrate")
                    messagebox.showerror("Calibration Error", f"An error occurred during calibration:\n{str(e)}")
                
                self.root.after(0, show_error)
        
        # Run calibration in separate thread to avoid blocking GUI
        threading.Thread(target=calibration_thread, daemon=True).start()

    def toggle_bot(self):
        """Toggle bot between start and stop states"""
        if not config.bot_running:
            self.start_bot()
        else:
            self.stop_bot()
    
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
            
            # Update button to show Stop state
            self.toggle_bot_button.configure(text="Stop", command=self.toggle_bot, fg_color="red", hover_color="darkred")
            self.status_label.configure(text="Status: Running")
            
            # Start periodic status updates
            self.update_status()
        else:
            print("Bot is already running")
            
    def stop_bot(self):
        config.bot_running = False
        
        # Reset all bot state for clean stop
        bot_logic.reset_bot_state()
        
        # Update button to show Start state
        self.toggle_bot_button.configure(text="Start", command=self.toggle_bot, fg_color="green", hover_color="darkgreen")
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
    
    def update_buff_enabled(self, idx):
        """Update buff enabled status"""
        config.buffs_config[idx]['enabled'] = self.buffs_vars[idx].get()
        self.buffs_state[idx]['enabled'] = config.buffs_config[idx]['enabled']
        if config.buffs_manager:
            if config.buffs_config[idx]['enabled'] and config.buffs_config[idx]['image_path']:
                config.buffs_manager.set_buff(idx, config.buffs_config[idx]['image_path'])
            else:
                config.buffs_manager.clear_buff(idx)
        status = "enabled" if config.buffs_config[idx]['enabled'] else "disabled"
        print(f"Buff {idx + 1} {status}")
    
    def load_buff_image(self, idx, image_path):
        """Load and display buff image (image_path should be absolute for loading)"""
        try:
            from PIL import Image, ImageTk
            pil_image = Image.open(image_path)
            pil_image = pil_image.resize((48, 48), Image.Resampling.LANCZOS)
            image = ImageTk.PhotoImage(pil_image)
            canvas = self.buffs_canvases[idx]
            canvas.delete('all')
            canvas.create_image(24, 24, image=image)
            canvas.image = image
            canvas.image_path = image_path  # Store absolute for display
            
            # Convert to relative path for storage in config
            relative_path = self.convert_to_relative_path(image_path)
            self.buffs_state[idx]['image_path'] = relative_path
            config.buffs_config[idx]['image_path'] = relative_path
            
            # Sync with buffs_manager (use relative path)
            if config.buffs_manager:
                config.buffs_manager.set_buff(idx, relative_path)
                print(f"[Buffs] Buff {idx + 1} synced with buffs_manager: {relative_path}")
        except Exception as e:
            print(f"Error loading buff image: {e}")
            import traceback
            traceback.print_exc()
    
    def clear_buff_skill(self, idx):
        """Clear buff skill image"""
        canvas = self.buffs_canvases[idx]
        canvas.delete('all')
        canvas.image = None
        canvas.image_path = None
        self.buffs_state[idx]['image_path'] = None
        config.buffs_config[idx]['image_path'] = None
        if config.buffs_manager:
            config.buffs_manager.clear_buff(idx)
        print(f"Buff {idx + 1} skill cleared")
    
    def show_skill_selector(self, callback_func, callback_arg, title="Choose Skill"):
        """Show popup window to select skill image, grouped by job (reusable for buffs and skill sequence)"""
        try:
            from PIL import Image, ImageTk
            import os
            
            # Create popup window
            popup = ctk.CTkToplevel(self.root)
            popup.title(title)
            popup.transient(self.root)
            popup.grab_set()
            
            # Position popup relative to main window's current position
            self.root.update_idletasks()  # Ensure root window position is updated
            root_x = self.root.winfo_x()
            root_y = self.root.winfo_y()
            root_width = self.root.winfo_width()
            root_height = self.root.winfo_height()
            
            # Calculate center position relative to main window
            popup_width = 550
            popup_height = 450
            popup_x = root_x + (root_width // 2) - (popup_width // 2)
            popup_y = root_y + (root_height // 2) - (popup_height // 2)
            
            # Ensure popup stays on screen
            popup_x = max(0, popup_x)
            popup_y = max(0, popup_y)
            
            popup.geometry(f"{popup_width}x{popup_height}+{popup_x}+{popup_y}")
            
            # Jobs folder path
            jobs_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jobs')
            
            if not os.path.exists(jobs_folder):
                messagebox.showerror("Error", f"Jobs folder not found: {jobs_folder}")
                popup.destroy()
                return
            
            # Get all job folders
            job_folders = [f for f in os.listdir(jobs_folder) 
                          if os.path.isdir(os.path.join(jobs_folder, f)) and not f.startswith('.')]
            # Natural sort (handles numbers correctly: Item 1, Item 2, Item 10 instead of Item 1, Item 10, Item 2)
            import re
            def natural_sort_key(text):
                return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]
            job_folders.sort(key=natural_sort_key)
            
            if not job_folders:
                messagebox.showinfo("No Jobs", "No job folders found in Jobs directory")
                popup.destroy()
                return
            
            # Create main container
            main_container = ctk.CTkFrame(popup)
            main_container.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Create tabview for jobs
            tabview = ctk.CTkTabview(main_container, corner_radius=8)
            tabview.pack(fill="both", expand=True, pady=(0, 10))
            
            # Track tab names for later selection
            tab_names = []
            
            # Create a tab for each job
            for job_name in job_folders:
                job_path = os.path.join(jobs_folder, job_name)
                images = [f for f in os.listdir(job_path) 
                         if f.lower().endswith(('.bmp', '.BMP'))]
                
                if not images:
                    continue
                
                # Create tab for this job
                job_tab = tabview.add(job_name)
                tab_names.append(job_name)
                
                # Create scrollable frame for skills in this job tab
                scroll_frame = ctk.CTkScrollableFrame(job_tab)
                scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
                
                # Create grid for skills (6 columns for compact layout)
                row = 0
                col = 0
                
                # Natural sort images (handles numbers correctly)
                images_sorted = sorted(images, key=natural_sort_key)
                for img_file in images_sorted:
                    try:
                        img_path = os.path.join(job_path, img_file)
                        pil_image = Image.open(img_path)
                        pil_image = pil_image.resize((48, 48), Image.Resampling.LANCZOS)
                        image = ImageTk.PhotoImage(pil_image)
                        
                        # Create skill frame (compact, just fits the image)
                        skill_frame = ctk.CTkFrame(scroll_frame, corner_radius=3, width=52, height=52)
                        skill_frame.grid(row=row, column=col, padx=2, pady=2, sticky="")
                        skill_frame.grid_propagate(False)
                        
                        # Skill image button
                        img_button = tk.Canvas(skill_frame, width=48, height=48, 
                                              bg='gray20', highlightthickness=1,
                                              highlightbackground='gray50',
                                              cursor='hand2')
                        img_button.place(relx=0.5, rely=0.5, anchor='center')
                        img_button.create_image(24, 24, image=image)
                        img_button.image = image
                        img_button.image_path = img_path
                        
                        # Bind click event - track tab before calling callback
                        def on_skill_click(e, path=img_path, p=popup, arg=callback_arg):
                            # Track current tab before closing
                            try:
                                current_tab = tabview.get()
                                if current_tab:
                                    self.last_skill_selector_tab = current_tab
                            except:
                                pass
                            callback_func(arg, path, p)
                        
                        img_button.bind('<Button-1>', on_skill_click)
                        
                        # Hover effect
                        def on_enter(e, frame=skill_frame):
                            frame.configure(fg_color=("gray70", "gray30"))
                        def on_leave(e, frame=skill_frame):
                            frame.configure(fg_color=("gray17", "gray17"))
                        skill_frame.bind('<Enter>', on_enter)
                        skill_frame.bind('<Leave>', on_leave)
                        img_button.bind('<Enter>', lambda e, f=skill_frame: on_enter(e, f))
                        img_button.bind('<Leave>', lambda e, f=skill_frame: on_leave(e, f))
                        
                        col += 1
                        if col >= 6:
                            col = 0
                            row += 1
                    except Exception as e:
                        print(f"Error loading skill image {img_file}: {e}")
                        continue
                
                # Configure grid weights for scrollable frame
                for i in range(6):
                    scroll_frame.grid_columnconfigure(i, weight=0)
            
            # Track tab changes to remember last active tab
            def track_tab_change():
                try:
                    current_tab = tabview.get()
                    if current_tab:
                        self.last_skill_selector_tab = current_tab
                except:
                    pass
            
            # Override tab selection to track changes
            original_set = tabview.set
            def tracked_set(tab_name):
                original_set(tab_name)
                self.last_skill_selector_tab = tab_name
            
            tabview.set = tracked_set
            
            # Set the last active tab if it exists (after window is ready)
            def restore_last_tab():
                if self.last_skill_selector_tab and self.last_skill_selector_tab in tab_names:
                    try:
                        # Use the tracked_set function to properly set the tab
                        tracked_set(self.last_skill_selector_tab)
                    except Exception as e:
                        print(f"Error restoring tab {self.last_skill_selector_tab}: {e}")
                        pass  # Tab might not exist, use default
            
            # Update window to ensure tabview is ready, then restore tab
            popup.update_idletasks()
            # Use after() to ensure tabview is fully initialized before setting tab
            popup.after(50, restore_last_tab)
            
            # Also track when popup is destroyed to save current tab
            def on_popup_destroy():
                try:
                    current_tab = tabview.get()
                    if current_tab:
                        self.last_skill_selector_tab = current_tab
                except:
                    pass
                popup.destroy()
            
            # Override popup destroy to track tab before closing
            popup.protocol("WM_DELETE_WINDOW", on_popup_destroy)
            
            # Close button - track tab before closing
            def close_and_track():
                try:
                    current_tab = tabview.get()
                    if current_tab:
                        self.last_skill_selector_tab = current_tab
                except:
                    pass
                popup.destroy()
            
            close_button = ctk.CTkButton(main_container, text="Close", 
                                        command=close_and_track, width=100)
            close_button.pack(pady=10)
            
        except Exception as e:
            print(f"Error showing skill selector: {e}")
            import traceback
            traceback.print_exc()
            if 'popup' in locals():
                popup.destroy()
    
    def show_buff_skill_selector(self, buff_index):
        """Show popup window to select skill image for buff"""
        self.show_skill_selector(self.select_buff_skill, buff_index, "Choose Skill for Buff")
    
    def select_buff_skill(self, buff_index, image_path, popup):
        """Select a skill image for a buff"""
        self.load_buff_image(buff_index, image_path)
        popup.destroy()
        print(f"Buff {buff_index + 1} skill selected: {image_path}")
    
    def register_buff_key(self, idx):
        """Register a key for a buff by capturing keyboard input"""
        # Create popup window
        popup = ctk.CTkToplevel(self.root)
        popup.title("Press a key")
        popup.geometry("300x150")
        popup.transient(self.root)
        popup.grab_set()
        
        # Position popup near main window
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        popup.geometry(f'+{root_x + 50}+{root_y + 50}')
        
        # Label
        label = ctk.CTkLabel(popup, text="Press any key to register...", 
                            font=ctk.CTkFont(size=12))
        label.pack(pady=30)
        
        def on_key_press(event):
            """Handle key press event"""
            key = event.keysym.upper()
            
            # Handle single character keys (letters, numbers)
            if len(key) == 1:
                self.buffs_keys[idx].set(key)
                config.buffs_config[idx]['key'] = key
                print(f"Buff {idx + 1} key registered: {key}")
                popup.destroy()
            # Handle function keys (F1-F12)
            elif key in ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12']:
                self.buffs_keys[idx].set(key)
                config.buffs_config[idx]['key'] = key
                print(f"Buff {idx + 1} key registered: {key}")
                popup.destroy()
            # Handle special keys
            elif key in ['SPACE', 'TAB', 'RETURN', 'ESCAPE']:
                key_map = {
                    'SPACE': 'SPACE',
                    'TAB': 'TAB',
                    'RETURN': 'ENTER',
                    'ESCAPE': 'ESC'
                }
                mapped_key = key_map.get(key, key)
                self.buffs_keys[idx].set(mapped_key)
                config.buffs_config[idx]['key'] = mapped_key
                print(f"Buff {idx + 1} key registered: {mapped_key}")
                popup.destroy()
        
        # Bind key press event to popup
        popup.bind('<Key>', on_key_press)
        popup.focus_set()
        
        # Cancel button
        cancel_btn = ctk.CTkButton(popup, text="Cancel", command=popup.destroy, width=100)
        cancel_btn.pack(pady=10)
    
    def clear_buff_key(self, idx):
        """Clear buff key"""
        self.buffs_keys[idx].set('')
        config.buffs_config[idx]['key'] = ''
        print(f"Buff {idx + 1} key cleared")
    
    def show_skill_sequence_selector(self, skill_index):
        """Show popup window to select skill image for skill sequence"""
        self.show_skill_selector(self.select_skill_sequence_skill, skill_index, "Choose Skill for Sequence")
    
    def select_skill_sequence_skill(self, skill_index, image_path, popup):
        """Select a skill image for skill sequence"""
        self.load_skill_sequence_image(skill_index, image_path)
        popup.destroy()
        print(f"Skill Sequence {skill_index + 1} skill selected: {image_path}")
    
    def load_skill_sequence_image(self, idx, image_path):
        """Load and display skill sequence image (image_path should be absolute for loading)"""
        try:
            from PIL import Image, ImageTk
            pil_image = Image.open(image_path)
            pil_image = pil_image.resize((48, 48), Image.Resampling.LANCZOS)
            image = ImageTk.PhotoImage(pil_image)
            canvas = self.skill_sequence_canvases[idx]
            canvas.delete('all')
            canvas.create_image(24, 24, image=image)
            canvas.image = image
            canvas.image_path = image_path  # Store absolute for display
            
            # Convert to relative path for storage in config
            relative_path = self.convert_to_relative_path(image_path)
            self.skill_sequence_state[idx]['image_path'] = relative_path
            config.skill_sequence_config[idx]['image_path'] = relative_path
            
            # Sync with skill sequence manager (use relative path)
            if config.skill_sequence_manager:
                config.skill_sequence_manager.set_skill(idx, relative_path)
                print(f"[SkillSequence] Skill {idx + 1} synced with skill_sequence_manager: {relative_path}")
        except Exception as e:
            print(f"Error loading skill sequence image: {e}")
            import traceback
            traceback.print_exc()
    
    def clear_skill_sequence_skill(self, idx):
        """Clear skill sequence skill image"""
        canvas = self.skill_sequence_canvases[idx]
        canvas.delete('all')
        canvas.image = None
        canvas.image_path = None
        self.skill_sequence_state[idx]['image_path'] = None
        config.skill_sequence_config[idx]['image_path'] = None
        if config.skill_sequence_manager:
            config.skill_sequence_manager.clear_skill(idx)
        print(f"Skill Sequence {idx + 1} skill cleared")
    
    def update_skill_sequence_enabled(self, idx):
        """Update skill sequence enabled status"""
        config.skill_sequence_config[idx]['enabled'] = self.skill_sequence_vars[idx].get()
        self.skill_sequence_state[idx]['enabled'] = config.skill_sequence_config[idx]['enabled']
        if config.skill_sequence_manager:
            if config.skill_sequence_config[idx]['enabled'] and config.skill_sequence_config[idx].get('image_path'):
                config.skill_sequence_manager.set_skill(idx, config.skill_sequence_config[idx]['image_path'])
            else:
                config.skill_sequence_manager.clear_skill(idx)
        status = "enabled" if config.skill_sequence_config[idx]['enabled'] else "disabled"
        print(f"Skill Sequence {idx + 1} {status}")
    
    def register_skill_sequence_key(self, idx):
        """Register a key for skill sequence by capturing keyboard input"""
        # Create popup window
        popup = ctk.CTkToplevel(self.root)
        popup.title("Press a key")
        popup.geometry("300x150")
        popup.transient(self.root)
        popup.grab_set()
        
        # Position popup near main window
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        popup.geometry(f'+{root_x + 50}+{root_y + 50}')
        
        # Label
        label = ctk.CTkLabel(popup, text="Press any key to register...", 
                            font=ctk.CTkFont(size=12))
        label.pack(pady=30)
        
        def on_key_press(event):
            """Handle key press event"""
            key = event.keysym.upper()
            
            # Handle single character keys (letters, numbers)
            if len(key) == 1:
                self.skill_sequence_keys[idx].set(key)
                config.skill_sequence_config[idx]['key'] = key
                print(f"Skill Sequence {idx + 1} key registered: {key}")
                popup.destroy()
            # Handle function keys (F1-F12)
            elif key in ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12']:
                self.skill_sequence_keys[idx].set(key)
                config.skill_sequence_config[idx]['key'] = key
                print(f"Skill Sequence {idx + 1} key registered: {key}")
                popup.destroy()
            # Handle special keys
            elif key in ['SPACE', 'TAB', 'RETURN', 'ESCAPE']:
                key_map = {
                    'SPACE': 'SPACE',
                    'TAB': 'TAB',
                    'RETURN': 'ENTER',
                    'ESCAPE': 'ESC'
                }
                mapped_key = key_map.get(key, key)
                self.skill_sequence_keys[idx].set(mapped_key)
                config.skill_sequence_config[idx]['key'] = mapped_key
                print(f"Skill Sequence {idx + 1} key registered: {mapped_key}")
                popup.destroy()
        
        # Bind key press event to popup
        popup.bind('<Key>', on_key_press)
        popup.focus_set()
        
        # Cancel button
        cancel_btn = ctk.CTkButton(popup, text="Cancel", command=popup.destroy, width=100)
        cancel_btn.pack(pady=10)
    
    def clear_skill_sequence_key(self, idx):
        """Clear skill sequence key"""
        self.skill_sequence_keys[idx].set('')
        config.skill_sequence_config[idx]['key'] = ''
        print(f"Skill Sequence {idx + 1} key cleared")
    
    def send_key(self, key_input):
        """Send a key input (used by BuffsManager)"""
        try:
            input_handler.send_input(key_input)
            return True
        except Exception as e:
            print(f"Error sending key {key_input}: {e}")
            return False
    
    def convert_to_absolute_path(self, relative_path):
        """Convert a relative path to absolute path for loading from configuration"""
        if not relative_path:
            return None
        
        # Use the config helper function to resolve relative paths
        return config.resolve_resource_path(relative_path)
    
    def convert_to_relative_path(self, absolute_path):
        """Convert an absolute path to relative path for saving in configuration"""
        # Use the settings_manager function
        return settings_manager.convert_to_relative_path(absolute_path)
    
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
    
    def update_is_mage(self):
        """Update mage setting"""
        config.is_mage = self.is_mage_var.get()
        status = "enabled" if config.is_mage else "disabled"
        print(f"Mage? {status}")
    
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
                    self.update_toggle_bot_button_state()
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
                    self.update_toggle_bot_button_state()
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
                    self.update_toggle_bot_button_state()
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
                    self.update_toggle_bot_button_state()
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
                    self.update_toggle_bot_button_state()
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

        
        # Check if System Message is set
        # (Calibration tab removed) - only update this if the legacy button exists.
        if hasattr(self, "system_message_calib_btn"):
            if config.system_message_area.get('width', 0) > 0 and config.system_message_area.get('height', 0) > 0:
                self.system_message_calib_btn.configure(text="✓ System Message")
            else:
                self.system_message_calib_btn.configure(text="Set System Message")
        
        # Update toggle bot button state based on calibration
        self.update_toggle_bot_button_state()
    
    def update_toggle_bot_button_state(self):
        """Update the Start/Stop button state based on calibration and connection"""
        # Button should be enabled only if:
        # 1. Window is connected
        # 2. Calibration has been completed (calibrator exists)
        is_calibrated = config.calibrator is not None and config.calibrator.mp_position is not None
        
        if config.connected_window and is_calibrated and not config.bot_running:
            self.toggle_bot_button.configure(state="normal", text="Start", fg_color="green", hover_color="darkgreen", command=self.toggle_bot)
        elif config.bot_running:
            # Keep button enabled when running so user can stop
            self.toggle_bot_button.configure(state="normal", text="Stop", fg_color="red", hover_color="darkred", command=self.toggle_bot)
        else:
            self.toggle_bot_button.configure(state="disabled")
    
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
    
    def update_target_list(self):
        """Update mob target list"""

        target_text = self.target_list_text.get("1.0", tk.END).strip()
        config.mob_target_list = [line.strip() for line in target_text.split('\n') if line.strip()]
        print(f"Updated target list: {config.mob_target_list}")
    
    def test_mob_detection(self):
        """Test mob detection and display result"""
        if not config.connected_window or not config.calibrator or config.calibrator.mp_position is None:
            print("TEST: Calibration required for mob detection")
            self.current_mob_label.configure(text="Calibration Required", text_color="red")
            return
        
        hwnd = config.connected_window.handle
        result = auto_attack.detect_enemy_for_auto_attack(hwnd, targets=None)
        mob_name = result.get('name')
        
        if mob_name:
            self.current_mob_label.configure(text=mob_name, text_color="green")
            config.current_target_mob = mob_name
            if not auto_attack.should_target_current_mob():
                self.current_mob_label.configure(text_color="orange")
                print(f"TEST: Mob '{mob_name}' would be SKIPPED (not in target list)")
            else:
                print(f"TEST: Mob '{mob_name}' would be ATTACKED (in target list)")
        else:
            self.current_mob_label.configure(text="None", text_color="red")
            print("TEST: No mob detected")
    
    def record_target_mob(self):
        """Record current enemy name automatically and add to target list"""
        if not config.connected_window:
            print("[Record] No window connected")
            return
        
        if not config.calibrator or config.calibrator.mp_position is None:
            print("[Record] Calibration required. Please calibrate first.")
            return
        
        try:
            hwnd = config.connected_window.handle
            
            # Detect enemy using calibration-based method (without target filtering)
            result = auto_attack.detect_enemy_for_auto_attack(hwnd, targets=None)
            
            if result.get('found') and result.get('name'):
                detected_name = result.get('name', '').strip()
                if detected_name:
                    detected_name_lower = detected_name.lower()
                    # Check if already in target list
                    if not any(t.lower() == detected_name_lower for t in config.mob_target_list):
                        config.mob_target_list.append(detected_name)
                        # Update GUI textbox - ensure it exists and update it
                        if hasattr(self, 'target_list_text'):
                            target_text = '\n'.join(config.mob_target_list)
                            self.target_list_text.delete("1.0", tk.END)
                            self.target_list_text.insert("1.0", target_text)
                            # Force GUI update to show the change
                            self.target_list_text.update_idletasks()
                        print(f"[Record] Added target: {detected_name}")
                    else:
                        print(f"[Record] Target '{detected_name}' already in list")
                else:
                    print("[Record] Enemy name detected but empty")
            else:
                print("[Record] No enemy detected. Make sure you have a target selected.")
        except Exception as e:
            print(f"[Record] Error recording target: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def update_status(self):
        """Update HP/MP/Enemy HP status display (reads from config, updated by bot_logic/auto_attack)"""
        if config.bot_running and config.connected_window:
            # Check and update buffs
            try:
                # Check if enabled buffs are configured (have image paths and are enabled)
                buffs_configured = any(
                    self.buffs_state[i]['image_path'] and self.buffs_state[i]['enabled']
                    for i in range(8) 
                    if hasattr(self, 'buffs_state') and i < len(self.buffs_state)
                )
                
                if buffs_configured and config.calibrator and config.area_skills:
                    try:
                        import cv2
                        # Get window handle
                        if hasattr(config.connected_window, 'handle'):
                            hwnd = config.connected_window.handle
                        else:
                            hwnd = config.connected_window
                        
                        # Capture screen
                        screen = config.calibrator.capture_window(hwnd)
                        if screen is not None:
                            # Extract area_skills from stored coordinates
                            x_min, y_min, x_max, y_max = config.area_skills
                            
                            # Ensure coordinates are within screen bounds
                            h, w = screen.shape[:2]
                            if (x_min >= 0 and y_min >= 0 and x_max <= w and y_max <= h):
                                area_skills = screen[y_min:y_max, x_min:x_max]
                                
                                # Calculate area_buffs_activos (40 pixels above skills area)
                                buff_height_start = max(0, y_min - 40)
                                buff_height_end = y_min
                                buff_width_start = x_min
                                buff_width_end = x_max
                                
                                if (buff_height_start >= 0 and buff_height_end <= h and
                                    buff_width_start >= 0 and buff_width_end <= w and
                                    buff_height_start < buff_height_end):
                                    area_buffs_activos = screen[buff_height_start:buff_height_end, buff_width_start:buff_width_end]
                                    
                                    # Call buffs manager update
                                    if config.buffs_manager:
                                        config.buffs_manager.update_and_activate_buffs(
                                            hwnd,
                                            screen,
                                            area_skills,
                                            area_buffs_activos,
                                            x_min,
                                            y_min,
                                            run_active=True
                                        )
                    except Exception as e:
                        print(f"[GUI] Error updating buffs in update_status: {e}")
            except Exception as e:
                print(f"[GUI] Error checking buffs configuration: {e}")
        
        if config.bot_running:
            # Read HP/MP percentages from config (calculated by bot_logic in separate thread)
            hp_percent = config.current_hp_percentage
            mp_percent = config.current_mp_percentage
            
            # Update GUI progress bars and labels (maximized view)
            self.hp_progress_bar.set(hp_percent / 100.0)
            self.hp_percent_label.configure(text=f"{int(hp_percent)}%")
            self.mp_progress_bar.set(mp_percent / 100.0)
            self.mp_percent_label.configure(text=f"{int(mp_percent)}%")
            
            # Read enemy HP percentage from config (updated by auto_attack in separate thread)
            enemy_hp_percent = config.current_enemy_hp_percentage
            if hasattr(self, 'enemy_hp_progress_bar'):
                self.enemy_hp_progress_bar.set(enemy_hp_percent / 100.0)
            if hasattr(self, 'enemy_hp_percent_label'):
                self.enemy_hp_percent_label.configure(text=f"{int(enemy_hp_percent)}%")
            
            # Read enemy name from config (updated by auto_attack/bot_logic in separate thread)
            if hasattr(self, 'current_mob_label'):
                enemy_name = config.current_enemy_name
                if enemy_name:
                    # Check if mob should be targeted (for color coding)
                    if config.mob_detection_enabled and not auto_attack.should_target_current_mob():
                        self.current_mob_label.configure(text=enemy_name, text_color="orange")
                    else:
                        self.current_mob_label.configure(text=enemy_name, text_color="green")
                else:
                    self.current_mob_label.configure(text="None", text_color="red")
            
            # Update unstuck countdown when enemy HP is displayed
            if hasattr(self, 'unstuck_countdown_label'):
                import auto_unstuck
                auto_unstuck.update_unstuck_countdown_display(time.time())
            
            # Update auto repair count
            if hasattr(self, 'auto_repair_count_label'):
                try:
                    import auto_repair
                    current_count = auto_repair.get_repair_count()
                    trigger_count = auto_repair.get_repair_trigger_count()
                    
                    # Update text and color based on count
                    count_text = f"{current_count}/{trigger_count}"
                    if current_count == 0:
                        text_color = "gray"
                    elif current_count < trigger_count:
                        text_color = "yellow"
                    else:
                        text_color = "red"  # Ready to trigger
                    
                    self.auto_repair_count_label.configure(text=count_text, text_color=text_color)
                except Exception as e:
                    # Silently fail if auto_repair not available
                    pass
            
            # Update minimized window if it exists
            if self.is_minimized and self.minimized_window:
                try:
                    # Update minimized progress bars
                    if hasattr(self, 'minimized_hp_progress_bar'):
                        self.minimized_hp_progress_bar.set(hp_percent / 100.0)
                        self.minimized_hp_percent_label.configure(text=f"{int(hp_percent)}%")
                    if hasattr(self, 'minimized_mp_progress_bar'):
                        self.minimized_mp_progress_bar.set(mp_percent / 100.0)
                        self.minimized_mp_percent_label.configure(text=f"{int(mp_percent)}%")
                    if hasattr(self, 'minimized_enemy_hp_progress_bar'):
                        self.minimized_enemy_hp_progress_bar.set(enemy_hp_percent / 100.0)
                        self.minimized_enemy_hp_percent_label.configure(text=f"{int(enemy_hp_percent)}%")
                    
                    # Update minimized enemy name
                    if hasattr(self, 'minimized_current_mob_label'):
                        enemy_name = config.current_enemy_name
                        if enemy_name:
                            if config.mob_detection_enabled and not auto_attack.should_target_current_mob():
                                self.minimized_current_mob_label.configure(text=enemy_name, text_color="orange")
                            else:
                                self.minimized_current_mob_label.configure(text=enemy_name, text_color="green")
                        else:
                            self.minimized_current_mob_label.configure(text="None", text_color="red")
                    
                    # Update minimized unstuck countdown
                    if hasattr(self, 'minimized_unstuck_countdown_label'):
                        import auto_unstuck
                        current_time = time.time()
                        _, remaining_time = auto_unstuck.get_unstuck_remaining_time(config.unstuck_timeout)
                        if config.enemy_hp_stagnant_time == 0 or config.last_enemy_hp_before_stagnant is None:
                            self.minimized_unstuck_countdown_label.configure(text="Unstuck: ---", text_color="gray")
                        else:
                            import math
                            display_seconds = math.ceil(remaining_time)
                            if remaining_time > config.unstuck_timeout * 0.5:
                                color = "green"
                            elif remaining_time > config.unstuck_timeout * 0.25:
                                color = "yellow"
                            else:
                                color = "red"
                            target_indicator = " (no target)" if config.enemy_target_time == 0 else ""
                            self.minimized_unstuck_countdown_label.configure(
                                text=f"Unstuck: {display_seconds}s{target_indicator}",
                                text_color=color
                            )
                except Exception as e:
                    # Ignore errors if minimized window was closed
                    pass
        
        # Schedule next update (every 100ms for smooth display)
        if config.bot_running:
            self.root.after(100, self.update_status)
    
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
    
    def toggle_minimize(self):
        """Toggle between minimized and maximized UI"""
        if self.is_minimized:
            # Restore to maximized view
            if self.minimized_window:
                self.minimized_window.destroy()
                self.minimized_window = None
            self.root.deiconify()
            # Restore saved window position and size
            if self.saved_window_position:
                self.root.geometry(self.saved_window_position)
            else:
                self.root.geometry("655x800")
            self.minimize_button.configure(text="−")
            self.is_minimized = False
        else:
            # Save current window position and size before minimizing
            try:
                geometry = self.root.geometry()
                self.saved_window_position = geometry
            except:
                self.saved_window_position = "655x800+100+100"
            # Create minimized window at the same position
            self.create_minimized_window()
            self.minimize_button.configure(text="+")
            self.is_minimized = True
    
    def create_minimized_window(self):
        """Create a minimized window showing only progress bars"""
        if self.minimized_window:
            return
        
        # Create new window for minimized view
        self.minimized_window = ctk.CTkToplevel(self.root)
        self.minimized_window.title("Kathana Helper xCrypto v2.1.1")
        
        # Position minimized window at the same location as main window
        if self.saved_window_position:
            # Extract position from geometry string (format: "WxH+X+Y")
            try:
                parts = self.saved_window_position.split('+')
                if len(parts) >= 3:
                    x_pos = parts[1]
                    y_pos = parts[2]
                    self.minimized_window.geometry(f"350x180+{x_pos}+{y_pos}")
                else:
                    self.minimized_window.geometry("350x180")
            except:
                self.minimized_window.geometry("350x180")
        else:
            self.minimized_window.geometry("350x180")
        
        self.minimized_window.resizable(False, False)
        self.minimized_window.overrideredirect(False)  # Keep window controls
        
        # Make it stay on top
        self.minimized_window.attributes("-topmost", True)
        
        # Configure grid
        self.minimized_window.columnconfigure(0, weight=1)
        self.minimized_window.rowconfigure(0, weight=1)
        
        # Create main frame
        minimized_frame = ctk.CTkFrame(self.minimized_window, corner_radius=5)
        minimized_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        minimized_frame.columnconfigure(1, weight=1)
        
        # HP Progress Bar
        hp_bar_frame = ctk.CTkFrame(minimized_frame, fg_color="transparent")
        hp_bar_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 5))
        
        hp_label = ctk.CTkLabel(hp_bar_frame, text="HP:", width=70, anchor='w', font=ctk.CTkFont(size=11))
        hp_label.grid(row=0, column=0, padx=(0, 10))
        self.minimized_hp_progress_bar = ctk.CTkProgressBar(hp_bar_frame, width=200, height=20, progress_color="red", corner_radius=0)
        self.minimized_hp_progress_bar.set(0)
        self.minimized_hp_progress_bar.grid(row=0, column=1, padx=(0, 10))
        self.minimized_hp_percent_label = ctk.CTkLabel(hp_bar_frame, text="---%", font=ctk.CTkFont(size=11, weight="bold"), text_color="white")
        self.minimized_hp_percent_label.grid(row=0, column=2)
        
        # MP Progress Bar
        mp_bar_frame = ctk.CTkFrame(minimized_frame, fg_color="transparent")
        mp_bar_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        
        mp_label = ctk.CTkLabel(mp_bar_frame, text="MP:", width=70, anchor='w', font=ctk.CTkFont(size=11))
        mp_label.grid(row=0, column=0, padx=(0, 10))
        self.minimized_mp_progress_bar = ctk.CTkProgressBar(mp_bar_frame, width=200, height=20, progress_color="#0b58b0", corner_radius=0)
        self.minimized_mp_progress_bar.set(0)
        self.minimized_mp_progress_bar.grid(row=0, column=1, padx=(0, 10))
        self.minimized_mp_percent_label = ctk.CTkLabel(mp_bar_frame, text="---%", font=ctk.CTkFont(size=11, weight="bold"), text_color="white")
        self.minimized_mp_percent_label.grid(row=0, column=2)
        
        # Enemy HP Progress Bar
        enemy_hp_bar_frame = ctk.CTkFrame(minimized_frame, fg_color="transparent")
        enemy_hp_bar_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        
        enemy_hp_label = ctk.CTkLabel(enemy_hp_bar_frame, text="Enemy HP:", width=70, anchor='w', font=ctk.CTkFont(size=11))
        enemy_hp_label.grid(row=0, column=0, padx=(0, 10))
        self.minimized_enemy_hp_progress_bar = ctk.CTkProgressBar(enemy_hp_bar_frame, width=200, height=20, progress_color="green", corner_radius=0)
        self.minimized_enemy_hp_progress_bar.set(0)
        self.minimized_enemy_hp_progress_bar.grid(row=0, column=1, padx=(0, 10))
        self.minimized_enemy_hp_percent_label = ctk.CTkLabel(enemy_hp_bar_frame, text="---%", font=ctk.CTkFont(size=11, weight="bold"), text_color="white")
        self.minimized_enemy_hp_percent_label.grid(row=0, column=2)
        
        # Enemy Name display
        enemy_name_frame = ctk.CTkFrame(minimized_frame, fg_color="transparent")
        enemy_name_frame.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=(5, 10))
        
        enemy_name_label = ctk.CTkLabel(enemy_name_frame, text="Enemy Name:", width=70, anchor='w', font=ctk.CTkFont(size=11))
        enemy_name_label.grid(row=0, column=0, padx=(0, 10))
        self.minimized_current_mob_label = ctk.CTkLabel(enemy_name_frame, text="None", width=170, anchor='w', font=ctk.CTkFont(size=11), text_color="red")
        self.minimized_current_mob_label.grid(row=0, column=1, sticky="w", padx=(0, 10))
        self.minimized_unstuck_countdown_label = ctk.CTkLabel(enemy_name_frame, text="Unstuck: ---", font=ctk.CTkFont(size=10), text_color="gray")
        self.minimized_unstuck_countdown_label.grid(row=0, column=2)
        
        # Handle window close - restore to maximized
        self.minimized_window.protocol("WM_DELETE_WINDOW", self.toggle_minimize)
        
        # Hide main window
        self.root.withdraw()
    
    def run(self):
        # Update OCR status display after GUI is fully initialized
        self.update_ocr_status_display()
        
        # Start processing GUI updates from background threads
        self.process_gui_updates()
        self.root.mainloop()
