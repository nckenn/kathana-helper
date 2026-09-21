"""
GUI module for Kathana Bot.

BotGUI is composed from panel mixins under ui/panels/, each holding one
cohesive area of the interface (license, region pickers, mob filter, debug
window, skill selector, mini overlay). The mixins were moved out of this file
verbatim, so they still use `self` exactly as before and no call site changed.
What remains here is the window construction, settings wiring, and the
per-feature toggles that touch widgets across several panels.
"""
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
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
import cv2
import mob_filter
import mob_template_store
from PIL import Image, ImageTk
import calibration
from license_manager import get_license_manager
import debug_utils
import logger
from ui.keybind_dialogs import open_keybind_dialog
from ui.panels.debug_window import DebugWindowMixin
from ui.panels.license_panel import LicensePanelMixin
from ui.panels.mini_overlay import MiniOverlayMixin
from ui.panels.mob_filter_panel import MobFilterPanelMixin
from ui.panels.region_pickers import RegionPickerMixin
from ui.panels.skill_selector import SkillSelectorMixin
from ui import styles
from ui.widgets import (
    KEY_BUTTON_DEFAULT_LABEL,
    format_license_date,
    license_days_left,
    KEY_BUTTON_TOOLTIP,
    ToolTip,
    bind_key_button_clear,
    create_tooltip,
    key_button_label,
)
from ui.settings_overlays import collect_gui_overlay, sync_gui_to_config
import ui_fonts
import ui_icons


def _ellipsize(text, limit):
    """Shorten a window title so it cannot stretch the toolbar."""
    text = str(text or '')
    return text if len(text) <= limit else text[:limit - 1].rstrip() + '…'


class BotGUI(
    DebugWindowMixin,
    LicensePanelMixin,
    MiniOverlayMixin,
    MobFilterPanelMixin,
    RegionPickerMixin,
    SkillSelectorMixin,
):
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BotGUI, cls).__new__(cls)
        return cls._instance
    
    
    
    
    
    
    
    
    def _settings_dialog_dir(self):
        return os.path.dirname(settings_manager.get_settings_path()) or config.app_dir()

    def _fit_status_row(self, _event=None):
        """Hide the profile name rather than let it render half-drawn.

        It is the least important thing on the row, so it is what gives way
        when the window is narrow. Below ~720px there is not room for all four.
        """
        row = getattr(self, '_status_row', None)
        if row is None:
            return
        available = row.winfo_width()
        if available <= 1:
            return  # not laid out yet

        needed = sum(
            w.winfo_reqwidth() + 12
            for w in (self.status_label, self.connection_label, self.bars_status_label)
        )
        fits = needed + self.settings_profile_label.winfo_reqwidth() + 12 <= available

        # Only act on a change; re-packing fires <Configure> again.
        if fits and not self._profile_label_shown:
            self.settings_profile_label.pack(side="right")
            self._profile_label_shown = True
        elif not fits and self._profile_label_shown:
            self.settings_profile_label.pack_forget()
            self._profile_label_shown = False

    def _update_settings_profile_label(self):
        if not hasattr(self, 'settings_profile_label'):
            return
        profile = settings_manager.settings_profile_label()
        self.settings_profile_label.configure(text=profile)
        self._fit_status_row()

    def save_settings_gui(self):
        """Save current GUI state to the active profile file."""
        sync_gui_to_config(self)
        path = settings_manager.get_settings_path()
        if settings_manager.save_settings(path=path):
            self._update_settings_profile_label()
            logger.info(f"Settings saved to {path}", "Settings")
            messagebox.showinfo(
                "Save Settings",
                f"Settings saved to:\n{path}",
            )
        else:
            logger.warn("Failed to save settings!", "Settings")
            messagebox.showerror("Save Settings", "Failed to save settings!")

    def save_settings_as_gui(self):
        """Save current GUI state to a new profile file."""
        sync_gui_to_config(self)
        initial = settings_manager.get_settings_path()
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save Settings As",
            initialdir=self._settings_dialog_dir(),
            initialfile=os.path.basename(initial),
            defaultextension=".json",
            filetypes=settings_manager.SETTINGS_FILE_FILTER,
        )
        if not path:
            return
        if settings_manager.save_settings(path=path):
            self._update_settings_profile_label()
            logger.info(f"Settings saved to {path}", "Settings")
            messagebox.showinfo(
                "Save Settings As",
                f"Settings saved to:\n{path}",
            )
        else:
            messagebox.showerror("Save Settings As", "Failed to save settings!")

    def load_settings_gui(self):
        """Load a profile file into the GUI."""
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Load Settings",
            initialdir=self._settings_dialog_dir(),
            filetypes=settings_manager.LOAD_SETTINGS_FILE_FILTER,
        )
        if not path:
            return
        logger.info(f"Loading settings from {path}...", "Settings")
        if settings_manager.load_settings(path=path):
            self.apply_settings_to_gui()
            self._update_settings_profile_label()
            logger.info("Settings loaded and applied successfully!", "Settings")
            messagebox.showinfo(
                "Load Settings",
                f"Settings loaded from:\n{path}",
            )
        else:
            logger.warn("Failed to load settings!", "Settings")
            messagebox.showwarning("Load Settings", "Failed to load settings!")
    
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
            if hasattr(self, 'mob_elite_skip_var'):
                self.mob_elite_skip_var.set(config.mob_elite_skip_enabled)
            if hasattr(self, 'self_target_key_var'):
                self.self_target_key_var.set(config.self_target_key)
            if hasattr(self, 'mob_safe_buffs_var'):
                self.mob_safe_buffs_var.set(config.mob_filter_safe_buffs)
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
            
            # Apply Auto Loot settings
            if hasattr(self, 'looting_duration_var'):
                self.looting_duration_var.set(str(config.LOOTING_DURATION))
                print(f"  Applied looting duration: {config.LOOTING_DURATION} seconds")
            
            # Apply Auto Repair settings
            if hasattr(self, 'auto_repair_var'):
                self.auto_repair_var.set(config.auto_repair_enabled)
                print(f"  Applied auto repair: enabled={config.auto_repair_enabled}")
            self._update_auto_repair_count_display()
            # Apply Auto Change Target settings
            if hasattr(self, 'auto_change_target_var'):
                self.auto_change_target_var.set(config.auto_change_target_enabled)
                print(f"  Applied auto change target: enabled={config.auto_change_target_enabled}")
            if hasattr(self, 'unstuck_timeout_var'):
                self.unstuck_timeout_var.set(str(config.unstuck_timeout))
                print(f"  Applied unstuck timeout: {config.unstuck_timeout} seconds")
            if hasattr(self, 'auto_rotate_var'):
                self.auto_rotate_var.set(config.auto_rotate_enabled)
                if hasattr(self, 'auto_rotate_interval_var'):
                    self.auto_rotate_interval_var.set(str(config.auto_rotate_interval))
                print(f"  Applied auto rotate camera: enabled={config.auto_rotate_enabled}, interval={config.auto_rotate_interval}s")

            # Apply Mage setting
            if hasattr(self, 'is_mage_var'):
                self.is_mage_var.set(config.is_mage)
                print(f"  Applied mage: enabled={config.is_mage}")
            
            # Apply Assist Only setting
            if hasattr(self, 'assist_only_var'):
                self.assist_only_var.set(config.assist_only_enabled)
                print(f"  Applied assist only: enabled={config.assist_only_enabled}")
                if hasattr(self, 'assist_key_var'):
                    self.assist_key_var.set(config.assist_key)
                if config.assist_only_enabled:
                    self._set_assist_only_dependent_widgets_state('disabled')
            if hasattr(self, 'repair_key_var'):
                self.repair_key_var.set(config.repair_key)
            if hasattr(self, 'refresh_region_pick_labels'):
                self.refresh_region_pick_labels()
            # Low CPU mode is always enabled (no UI var)
            
            # Apply HP settings
            self.auto_hp_var.set(config.auto_hp_enabled)
            print(f"  Applied auto HP: enabled={config.auto_hp_enabled}")
            # Load HP settings from global variables
            try:
                self.hp_x_var.set(str(config.hp_bar_area['x']))
                self.hp_y_var.set(str(config.hp_bar_area['y']))
                self.hp_width_var.set(str(config.hp_bar_area['width']))
                self.hp_height_var.set(str(config.hp_bar_area['height']))
                self.hp_coords_var.set(f"{config.hp_bar_area['x']},{config.hp_bar_area['y']}")
                thresholds_info = ", ".join([f"{t['threshold']}%={t['key']}" for t in config.hp_thresholds])
                print(f"  Applied HP thresholds: {thresholds_info}, area: {config.hp_bar_area}")
            except Exception as e:
                print(f"  Error applying HP settings: {e}")
            
            # Apply MP settings
            self.auto_mp_var.set(config.auto_mp_enabled)
            print(f"  Applied auto MP: enabled={config.auto_mp_enabled}")
            # Load MP settings from global variables
            try:
                self.mp_threshold_var.set(str(config.mp_threshold))
                if hasattr(self, 'mp_key_var'):
                    self.mp_key_var.set(config.mp_key)
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
            if hasattr(self, 'buffs_vars') and hasattr(self, 'buffs_canvases'):
                for i in range(8):
                    try:
                        # Update enabled state
                        self.buffs_vars[i].set(config.buffs_config[i]['enabled'])
                        if hasattr(self, 'buffs_key_vars') and i in self.buffs_key_vars:
                            self.buffs_key_vars[i].set(config.buffs_config[i].get('key', ''))
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
            if hasattr(self, 'skill_sequence_vars') and hasattr(self, 'skill_sequence_canvases'):
                for i in range(8):
                    try:
                        # Update enabled state
                        self.skill_sequence_vars[i].set(config.skill_sequence_config[i]['enabled'])
                        # Update bypass state
                        if hasattr(self, 'skill_sequence_bypass_vars') and i in self.skill_sequence_bypass_vars:
                            self.skill_sequence_bypass_vars[i].set(config.skill_sequence_config[i].get('bypass', False))
                        if hasattr(self, 'skill_sequence_key_vars') and i in self.skill_sequence_key_vars:
                            self.skill_sequence_key_vars[i].set(config.skill_sequence_config[i].get('key', ''))
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
            
            if hasattr(self, 'mob_listbox'):
                self._refresh_mob_list()
            self.update_mob_filter_ui_state()
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
        finally:
            if hasattr(self, 'mob_listbox'):
                self._refresh_mob_list()
            if hasattr(self, 'update_mob_filter_ui_state'):
                self.update_mob_filter_ui_state()
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        # Configure customtkinter appearance and theme
        ctk.set_appearance_mode("dark")  # Options: "dark", "light", "system"
        ctk.set_default_color_theme("blue")  # Options: "blue", "green", "dark-blue"

        # Register the bundled JetBrains Mono font and make it the app-wide default
        # (all CTkFont(size=...) calls without an explicit family inherit this).
        ui_fonts.apply_app_font()

        # Initialize root window with customtkinter
        self.root = ctk.CTk()
        self.root.title(config.APP_TITLE)
        self.root.geometry("720x800")
        self.root.resizable(True, True)
        # Below this the toolbar's button row has nowhere left to go.
        self.root.minsize(620, 560)
        
        # Set application icon
        try:
            # Get the directory where the script/executable is located
            if getattr(sys, 'frozen', False):
                # If running as compiled executable (PyInstaller)
                # Use the directory where the executable is located, not _MEIPASS
                base_path = os.path.dirname(sys.executable)
            else:
                # If running as script
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            icon_path = os.path.join(base_path, 'icon.ico')
            if os.path.exists(icon_path):
                # Set icon for Windows taskbar, window, and desktop
                self.root.iconbitmap(icon_path)
                print(f'✅ Application icon set: {icon_path}')
            else:
                print(f'⚠️ Icon file not found at: {icon_path}')
        except Exception as e:
            print(f'❌ Error setting application icon: {e}')
        
        # Track minimized state
        self.is_minimized = False
        self.minimized_window = None
        self.minimized_toggle_bot_button = None
        self.saved_window_position = None  # Store window position when minimizing

        # Mini Overlay Mode state
        self._bot_run_start_time = None   # Set when bot starts (runtime timer)
        self._overlay_after_id = None     # Pending overlay refresh callback
        self.overlay_status_dot = None
        self.overlay_timer_label = None

        # Track last active tab in skill selector
        self.last_skill_selector_tab = None
        
        # Debug window for click coordinate debugging
        self.debug_window = None
        self.debug_text = None
        
        # Preload skill images cache
        self.skill_images_cache = {}  # {job_key: [(image_path, image_obj, img_file), ...]}
        
        # Preload all skill images in background (non-blocking)
        self.root.after(100, self._preload_skill_images)
        
        # Initialize debug system (disabled — no debug UI button)
        debug_utils.set_debug_enabled(False, callback=None)
        
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
        # Rows: 0=toolbar, 1=tabview
        main_frame.rowconfigure(1, weight=1)  # Tabview can expand

        # One toolbar card instead of three stacked ones (window / status /
        # controls). Same controls, ~140px less chrome above every tab.
        toolbar = ctk.CTkFrame(main_frame, corner_radius=8)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(10, 8), padx=10)

        # Each row packs independently. A shared grid does not work here: the two
        # rows have different structures, and the combo's columnspan starved the
        # first column, leaving the Start button unmapped.
        top_row = ctk.CTkFrame(toolbar, fg_color="transparent")
        top_row.pack(fill="x", padx=10, pady=(10, 0))

        bottom_row = ctk.CTkFrame(toolbar, fg_color="transparent")
        bottom_row.pack(fill="x", padx=10, pady=(12, 0))

        # Status gets its own row. Sharing the button row meant the two competed
        # for width, and at the default 720px window the labels lost.
        status_row = ctk.CTkFrame(toolbar, fg_color="transparent")
        status_row.pack(fill="x", padx=10, pady=(8, 10))

        # --- top row: pick a window and connect to it -------------------
        self.window_var = tk.StringVar()
        self.window_var.trace_add('write', self.on_window_change)  # Reset connection when window changes

        self.minimize_button = ctk.CTkButton(
            top_row, text="", image=ui_icons.get_icon("minimize", size=16),
            command=self.toggle_minimize, width=32, height=32, corner_radius=6,
            **styles.SECONDARY,
        )
        self.minimize_button.pack(side="right")
        create_tooltip(self.minimize_button, "Shrink to the floating overlay pill.")

        self.refresh_button = ctk.CTkButton(
            top_row, text="Refresh", command=self.refresh_windows,
            width=84, height=32, corner_radius=6, **styles.SECONDARY,
        )
        self.refresh_button.pack(side="right", padx=(6, 8))

        self.connect_button = ctk.CTkButton(
            top_row, text="Connect", command=self.connect_window,
            width=96, height=32, corner_radius=6, **styles.ACCENT,
        )
        self.connect_button.pack(side="right", padx=(6, 0))
        create_tooltip(
            self.connect_button,
            "Refresh the window list and connect to the selected game window.",
        )

        # Packed last so it takes whatever width the buttons leave.
        self.window_combo = ctk.CTkComboBox(
            top_row, variable=self.window_var, state="readonly", height=32,
        )
        self.window_combo.pack(side="left", fill="x", expand=True)

        # --- bottom row: run the bot, manage the profile, read status ---
        self.toggle_bot_button = ctk.CTkButton(
            bottom_row, text="Start", command=self.toggle_bot, state="disabled",
            width=96, height=32, corner_radius=6, **styles.PRIMARY,
        )
        self.toggle_bot_button.pack(side="left", padx=(0, 6))
        create_tooltip(self.toggle_bot_button, "Start or stop the bot. Set HP + MP in Region Editor first.")

        self.regions_button = ctk.CTkButton(
            bottom_row, text="Regions", command=self.open_region_editor,
            state="disabled", width=96, height=32, corner_radius=6, **styles.SECONDARY,
        )
        self.regions_button.pack(side="left", padx=(0, 10))
        create_tooltip(
            self.regions_button,
            "Open the Region Editor to pick HP/MP, enemy UI, skills, buffs, and chat areas.",
        )

        separator = ctk.CTkFrame(bottom_row, width=1, height=24, fg_color=("gray70", "gray35"))
        separator.pack(side="left", padx=(0, 10), pady=4)

        self.save_settings_button = ctk.CTkButton(
            bottom_row, text="Save", command=self.save_settings_gui,
            width=68, height=32, corner_radius=6, **styles.SECONDARY,
        )
        self.save_settings_button.pack(side="left", padx=(0, 5))
        create_tooltip(self.save_settings_button, "Save all settings to the current profile file.")

        self.save_settings_as_button = ctk.CTkButton(
            bottom_row, text="Save As…", command=self.save_settings_as_gui,
            width=80, height=32, corner_radius=6, **styles.SECONDARY,
        )
        self.save_settings_as_button.pack(side="left", padx=(0, 5))
        create_tooltip(self.save_settings_as_button, "Save settings to a new profile file.")

        self.load_settings_button = ctk.CTkButton(
            bottom_row, text="Load…", command=self.load_settings_gui,
            width=68, height=32, corner_radius=6, **styles.SECONDARY,
        )
        self.load_settings_button.pack(side="left", padx=(0, 10))
        create_tooltip(self.load_settings_button, "Load settings from a profile file.")

        # Most important first, so the leftmost thing is the one you look for.
        self.status_label = ctk.CTkLabel(
            status_row, text="Stopped", font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.status_label.pack(side="left")

        self.connection_label = ctk.CTkLabel(
            status_row, text="Not connected", font=ctk.CTkFont(size=11),
            text_color=styles.MUTED_TEXT,
        )
        self.connection_label.pack(side="left", padx=(12, 0))

        self.bars_status_label = ctk.CTkLabel(
            status_row, text="", font=ui_fonts.mono(10),
            text_color=styles.MUTED_TEXT,
        )
        self.bars_status_label.pack(side="left", padx=(12, 0))

        self.settings_profile_label = ctk.CTkLabel(
            status_row, text="", font=ui_fonts.mono(11),
            text_color=styles.MUTED_TEXT, anchor="e",
        )
        self.settings_profile_label.pack(side="right")
        self._profile_label_shown = True
        self._status_row = status_row
        status_row.bind('<Configure>', self._fit_status_row)
        # Remembered so the red "Stopped (error)" styling can be undone on restart.
        self._status_label_default_color = self.status_label.cget("text_color")

        # Create tabview for all sections
        tabview = ctk.CTkTabview(main_frame, corner_radius=8)
        tabview.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 10), padx=10)
        
        # Create tabs
        status_tab = tabview.add("Status")
        settings_tab = tabview.add("Settings")
        skill_sequence_tab = tabview.add("Skill Sequence")
        buffs_tab = tabview.add("Buffs")
        skills_tab = tabview.add("Skill Interval")
        mouse_clicker_tab = tabview.add("Mouse Clicker")

        # Action slots frame - moved to Status tab (wrap in scrollable frame)
        # Typography tuned for small screens (avoid global widget scaling, which looks pixelated).
        _h_font = ctk.CTkFont(size=11, weight="bold")
        _t_font = ctk.CTkFont(size=11)
        _small_font = ctk.CTkFont(size=10)
        # Sized for the bundled monospace app font (JetBrains Mono): the
        # longest label here is 11 chars, which needs ~110px plus the box.
        _chk_w = 145

        _sub_font = ctk.CTkFont(size=10)
        _chev_color = "#9aa4b2"

        def _wrap_to_card(card, label, inset):
            """Keep a card subtitle wrapped to the card width instead of clipping.

            Card widths come from the grid, so the text that fits depends on the
            font — the app font is monospace and noticeably wider than the system
            UI font. Wrapping on <Configure> keeps subtitles readable at any
            window size without hand-tuning each string.
            """
            def _sync(_event=None):
                w = card.winfo_width()
                if w > inset + 40:
                    label.configure(wraplength=w - inset)

            card.bind("<Configure>", _sync, add="+")
            card.after(0, _sync)

        def _card(parent, title, subtitle=None):
            frame = ctk.CTkFrame(parent, fg_color=("gray92", "gray20"), corner_radius=10)
            frame.columnconfigure(0, weight=1)
            ctk.CTkLabel(
                frame,
                text=title,
                font=_h_font,
                text_color=("gray25", "gray80"),
                anchor="w",
            ).grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 0))
            next_row = 1
            if subtitle:
                sub_lbl = ctk.CTkLabel(
                    frame, text=subtitle, font=_sub_font,
                    text_color=("gray45", "gray55"), anchor="w", justify="left",
                )
                sub_lbl.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 2))
                _wrap_to_card(frame, sub_lbl, 24)
                next_row = 2
            body = ctk.CTkFrame(frame, fg_color="transparent")
            body.grid(row=next_row, column=0, sticky="ew", padx=12, pady=(4, 10))
            body.columnconfigure(0, weight=1)
            return frame, body

        def _collapsible_card(parent, title, subtitle=None, expanded=False):
            frame = ctk.CTkFrame(parent, fg_color=("gray92", "gray20"), corner_radius=10)
            frame.columnconfigure(0, weight=1)
            header = ctk.CTkFrame(frame, fg_color="transparent")
            header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 2))
            header.columnconfigure(1, weight=1)
            chev = ctk.CTkLabel(
                header, text="", width=18,
                image=ui_icons.get_icon(
                    "chevron_down" if expanded else "chevron_right",
                    size=14, color=_chev_color,
                ),
            )
            chev.grid(row=0, column=0, sticky="w")
            tlbl = ctk.CTkLabel(
                header, text=title, font=_h_font,
                text_color=("gray25", "gray80"), anchor="w",
            )
            tlbl.grid(row=0, column=1, sticky="w", padx=(4, 0))
            sub_lbl = None
            if subtitle:
                sub_lbl = ctk.CTkLabel(
                    frame, text=subtitle, font=_sub_font,
                    text_color=("gray45", "gray55"), anchor="w", justify="left",
                )
                _wrap_to_card(frame, sub_lbl, 46)  # 34 chevron indent + 12 pad
            body = ctk.CTkFrame(frame, fg_color="transparent")
            body.columnconfigure(0, weight=1)
            state = {"open": expanded}

            def _apply():
                chev.configure(image=ui_icons.get_icon(
                    "chevron_down" if state["open"] else "chevron_right",
                    size=14, color=_chev_color,
                ))
                if state["open"]:
                    if sub_lbl is not None:
                        sub_lbl.grid(row=1, column=0, sticky="ew", padx=34, pady=(0, 2))
                    body.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 10))
                else:
                    if sub_lbl is not None:
                        sub_lbl.grid_forget()
                    body.grid_forget()

            def _toggle(_e=None):
                state["open"] = not state["open"]
                _apply()

            for w in (header, chev, tlbl):
                w.bind("<Button-1>", _toggle)
            _apply()
            return frame, body

        status_scroll = ctk.CTkScrollableFrame(status_tab)
        status_scroll.pack(fill="both", expand=True)
        status_frame = status_scroll
        status_frame.columnconfigure(0, weight=1)
        
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
        self.hp_percent_label = ctk.CTkLabel(hp_bar_frame, text="---%", font=ui_fonts.mono(11, "bold"), text_color="white")
        self.hp_percent_label.grid(row=0, column=2)
        
        # MP Progress Bar
        mp_bar_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
        mp_bar_frame.grid(row=1, column=0, sticky="w", padx=15, pady=5)
        
        mp_label = ctk.CTkLabel(mp_bar_frame, text="MP:", width=70, anchor='w', font=ctk.CTkFont(size=11))
        mp_label.grid(row=0, column=0, padx=(0, 10))
        self.mp_progress_bar = ctk.CTkProgressBar(mp_bar_frame, width=200, height=20, progress_color="#0b58b0", corner_radius=0)
        self.mp_progress_bar.set(0)
        self.mp_progress_bar.grid(row=0, column=1, padx=(0, 10))
        self.mp_percent_label = ctk.CTkLabel(mp_bar_frame, text="---%", font=ui_fonts.mono(11, "bold"), text_color="white")
        self.mp_percent_label.grid(row=0, column=2)
        
        # Enemy HP Progress Bar
        enemy_hp_bar_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
        enemy_hp_bar_frame.grid(row=2, column=0, sticky="w", padx=15, pady=5)
        
        enemy_hp_label = ctk.CTkLabel(enemy_hp_bar_frame, text="Enemy HP:", width=70, anchor='w', font=ctk.CTkFont(size=11))
        enemy_hp_label.grid(row=0, column=0, padx=(0, 10))
        self.enemy_hp_progress_bar = ctk.CTkProgressBar(enemy_hp_bar_frame, width=200, height=20, progress_color="green", corner_radius=0)
        self.enemy_hp_progress_bar.set(0)
        self.enemy_hp_progress_bar.grid(row=0, column=1, padx=(0, 10))
        self.enemy_hp_percent_label = ctk.CTkLabel(enemy_hp_bar_frame, text="---%", font=ui_fonts.mono(11, "bold"), text_color="white")
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
        
        # License Info card (styled like OCR status frame)
        # Collapsed by default: the bars above are what changes while the bot
        # runs; the licence details are read once, if ever.
        license_card, license_info_frame = _collapsible_card(
            status_frame, "License", expanded=False,
        )
        license_card.grid(row=4, column=0, sticky="ew", padx=15, pady=(14, 8))
        license_info_frame.columnconfigure(0, weight=1)

        # Header row
        license_header = ctk.CTkLabel(
            license_info_frame,
            text="License Info",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        license_header.grid(row=0, column=0, sticky="w", padx=(12, 8), pady=(10, 6))

        activate_license_btn = ctk.CTkButton(
            license_info_frame,
            text="Activate/Change License",
            command=self.show_license_dialog,
            width=160,
            height=28,
            corner_radius=6,
            **styles.SECONDARY,
        )
        activate_license_btn.grid(row=0, column=1, sticky="e", padx=(8, 12), pady=(10, 6))
        create_tooltip(activate_license_btn, "Activate or change your license key")
        
        # License status (enhanced display)
        license_manager = get_license_manager()
        license_info = license_manager.get_license_info()

        if license_info and license_info.get('valid'):
            status_color = "green"
            user_name = license_info['data'].get('user_name', 'Unknown')
            expires = license_info['data'].get('expires', 'Never')
            issued = license_info['data'].get('issued', 'Unknown')
            machine_bound = license_info['data'].get('machine_bound', False)
            
            # Calculate days left if expiration exists
            if expires != 'Never':
                from datetime import datetime
                try:
                    expires_str = format_license_date(expires)
                    days_left = license_days_left(expires)
                    if days_left < 0:
                        status_color = "red"
                        status_indicator = "●"
                        expiry_info = f"Expired: {expires_str}"
                    elif days_left <= 7:
                        status_color = "orange"
                        status_indicator = "●"
                        expiry_info = f"{expires_str} ({days_left} day{'s' if days_left != 1 else ''} left)"
                    elif days_left <= 30:
                        status_color = "yellow"
                        status_indicator = "●"
                        expiry_info = f"{expires_str} ({days_left} days left)"
                    else:
                        expiry_info = f"{expires_str}"
                except:
                    expiry_info = f"{expires}"
            else:
                expiry_info = "No expiration"
            
            # Format issued date
            if issued != 'Unknown':
                issued_str = format_license_date(issued)
            else:
                issued_str = "Unknown"
        else:
            status_color = "red"
            user_name = "N/A"
            expiry_info = "No valid license found"
            issued_str = "N/A"
            machine_bound = False
        
        # License details
        details_frame = ctk.CTkFrame(license_info_frame, fg_color="transparent")
        details_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 10))
        details_frame.columnconfigure(1, weight=1)
        
        # User name
        ctk.CTkLabel(details_frame, text="User:", font=ctk.CTkFont(size=10, weight="bold")).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=(0, 2))
        self.license_user_value = ctk.CTkLabel(details_frame, text=user_name, font=ctk.CTkFont(size=10), text_color="white")
        self.license_user_value.grid(row=0, column=1, sticky="w", pady=(0, 2))
        
        # Expiration
        ctk.CTkLabel(details_frame, text="Expiration:", font=ctk.CTkFont(size=10, weight="bold")).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=2)
        self.license_expiry_label = ctk.CTkLabel(
            details_frame,
            text=expiry_info,
            font=ctk.CTkFont(size=10),
            text_color=status_color if license_info and license_info.get('valid') else "gray"
        )
        self.license_expiry_label.grid(row=1, column=1, sticky="w", pady=2)
        
        # Issued date
        ctk.CTkLabel(details_frame, text="Issued:", font=ctk.CTkFont(size=10, weight="bold")).grid(row=2, column=0, sticky="w", padx=(0, 10), pady=2)
        self.license_issued_value = ctk.CTkLabel(details_frame, text=issued_str, font=ctk.CTkFont(size=10), text_color="gray")
        self.license_issued_value.grid(row=2, column=1, sticky="w", pady=2)

        # Binding indicator (compact)
        ctk.CTkLabel(details_frame, text="Binding:", font=ctk.CTkFont(size=10, weight="bold")).grid(row=3, column=0, sticky="w", padx=(0, 10), pady=(2, 0))
        binding_text = "Machine Bound" if machine_bound else "—"
        binding_color = "orange" if machine_bound else "gray"
        self.license_binding_value = ctk.CTkLabel(details_frame, text=binding_text, font=ctk.CTkFont(size=10), text_color=binding_color)
        self.license_binding_value.grid(row=3, column=1, sticky="w", pady=(2, 0))
        
        # Configure status frame grid
        status_frame.columnconfigure(0, weight=1)
        
        # Options frame - moved to Settings tab (wrap in scrollable frame)
        settings_scroll = ctk.CTkScrollableFrame(settings_tab)
        settings_scroll.pack(fill="both", expand=True)
        settings_frame = settings_scroll
        
        # Configure settings frame for 2 columns
        settings_frame.columnconfigure(0, weight=1, uniform="settings_cols")
        settings_frame.columnconfigure(1, weight=1, uniform="settings_cols")

        # --- Quick Start card (compact readiness checklist + one-click presets) ---
        qs_card, qs_body = _card(settings_frame, "Quick Start")
        qs_card.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=15, pady=(12, 6))
        qs_body.columnconfigure(0, weight=1)

        qs_row = ctk.CTkFrame(qs_body, fg_color="transparent")
        qs_row.pack(fill="x")

        steps_wrap = ctk.CTkFrame(qs_row, fg_color="transparent")
        steps_wrap.pack(side="left")
        self.qs_dots = {}
        self.qs_texts = {}
        _qs_steps = [
            ("connect", "Connect", "Connect to your game window using the top bar."),
            ("regions", "Regions", "Click \u201cRegions\u201d and set the HP & MP bar areas."),
            ("start", "Start", "Press Start once the first two steps are done."),
        ]
        for key, label, tip in _qs_steps:
            cell = ctk.CTkFrame(steps_wrap, fg_color="transparent")
            cell.pack(side="left", padx=(0, 12))
            dot = ctk.CTkLabel(cell, text="", width=16, image=ui_icons.get_icon("dot", size=13, color="#6b7280"))
            dot.pack(side="left")
            txt = ctk.CTkLabel(cell, text=label, font=_t_font, text_color=("gray30", "gray75"), anchor="w")
            txt.pack(side="left", padx=(3, 0))
            create_tooltip(cell, tip)
            create_tooltip(txt, tip)
            self.qs_dots[key] = dot
            self.qs_texts[key] = txt

        preset_wrap = ctk.CTkFrame(qs_row, fg_color="transparent")
        preset_wrap.pack(side="right")
        ctk.CTkLabel(preset_wrap, text="Presets:", font=_small_font, text_color=("gray40", "gray60")).pack(side="left", padx=(0, 6))
        for _pk, _plabel, _ptip in (
            ("melee", "Melee", "Auto attack + loot, HP/MP pots, repair, unstuck."),
            ("caster", "Caster", "Like Melee but casts skills instead of basic attack."),
            ("support", "Support", "Party assist mode + HP/MP pots (no auto-target)."),
        ):
            b = ctk.CTkButton(
                preset_wrap, text=_plabel, width=74, height=24, corner_radius=6,
                font=_small_font, command=lambda k=_pk: self.apply_quick_preset(k),
                **styles.SECONDARY,
            )
            b.pack(side="left", padx=(0, 4))
            create_tooltip(b, _ptip)

        left_card, left_body = _card(
            settings_frame, "Combat",
            "Targeting, attacking, looting, repair.",
        )
        left_card.grid(row=1, column=0, sticky="nsew", padx=(15, 6), pady=(6, 6))

        right_card, right_body = _card(
            settings_frame, "Staying Alive",
            "Automatic HP and MP potions.",
        )
        right_card.grid(row=1, column=1, sticky="nsew", padx=(6, 15), pady=(6, 6))

        movement_card, movement_body = _collapsible_card(
            settings_frame, "Movement & Camera",
            "Get unstuck and rotate the camera.",
        )
        movement_card.grid(row=2, column=0, sticky="nsew", padx=(15, 6), pady=(6, 6))

        extras_card, extras_body = _collapsible_card(
            settings_frame, "Party & Misc",
            "Party assist instead of auto-targeting.",
        )
        extras_card.grid(row=2, column=1, sticky="nsew", padx=(6, 15), pady=(6, 6))

        # --- Left card (Combat & Utility) ---
        auto_attack_row = ctk.CTkFrame(left_body, fg_color="transparent")
        auto_attack_row.pack(fill="x", pady=(0, 6))
        self.auto_attack_var = tk.BooleanVar()
        self.auto_attack_checkbox = ctk.CTkCheckBox(
            auto_attack_row,
            text="Auto Attack",
            width=_chk_w,
            variable=self.auto_attack_var,
            command=self.update_auto_attack,
            font=_t_font,
        )
        self.auto_attack_checkbox.pack(side="left")
        create_tooltip(self.auto_attack_checkbox, "Automatically targets and attacks enemies.")

        auto_loot_row = ctk.CTkFrame(left_body, fg_color="transparent")
        auto_loot_row.pack(fill="x", pady=(0, 6))
        self.action_vars['pick'] = tk.BooleanVar(value=config.action_slots['pick']['enabled'])
        auto_loot_checkbox = ctk.CTkCheckBox(
            auto_loot_row,
            text="Auto Loot",
            width=_chk_w,
            variable=self.action_vars['pick'],
            command=lambda: self.update_action_slot('pick'),
            font=_t_font,
        )
        auto_loot_checkbox.pack(side="left")
        create_tooltip(auto_loot_checkbox, "Picks items after kills (uses your Pick hotkey).")
        self.looting_duration_var = tk.StringVar(value=str(config.LOOTING_DURATION))
        looting_duration_entry = ctk.CTkEntry(
            auto_loot_row,
            textvariable=self.looting_duration_var,
            width=52,
            font=_t_font,
        )
        looting_duration_entry.pack(side="left", padx=(10, 4))
        looting_duration_entry.bind('<KeyRelease>', lambda event: self.update_looting_duration())
        looting_duration_entry.bind('<FocusOut>', lambda event: self.update_looting_duration())
        ctk.CTkLabel(auto_loot_row, text="s", font=_t_font).pack(side="left")
        create_tooltip(looting_duration_entry, "Looting lockout duration (seconds).")

        mage_row = ctk.CTkFrame(left_body, fg_color="transparent")
        mage_row.pack(fill="x", pady=(0, 6))
        self.is_mage_var = tk.BooleanVar(value=config.is_mage)
        mage_checkbox = ctk.CTkCheckBox(
            mage_row,
            text="Caster mode",
            width=_chk_w,
            variable=self.is_mage_var,
            command=self.update_is_mage,
            font=_t_font,
        )
        mage_checkbox.pack(side="left")
        create_tooltip(mage_checkbox, "Caster mode — skip the basic attack after targeting (use skills instead).")

        auto_repair_row = ctk.CTkFrame(left_body, fg_color="transparent")
        auto_repair_row.pack(fill="x", pady=(0, 6))
        self.auto_repair_var = tk.BooleanVar(value=config.auto_repair_enabled)
        auto_repair_checkbox = ctk.CTkCheckBox(
            auto_repair_row,
            text="Auto Repair",
            width=_chk_w,
            variable=self.auto_repair_var,
            command=self.update_auto_repair,
            font=_t_font,
        )
        auto_repair_checkbox.pack(side="left")
        create_tooltip(auto_repair_checkbox, "Repairs after repeated 'about to break' warnings.")
        self.auto_repair_count_label = ctk.CTkLabel(auto_repair_row, text="0/10", font=_small_font, text_color="gray")
        self.auto_repair_count_label.pack(side="left", padx=(10, 0))
        self.auto_repair_reset_btn = ctk.CTkButton(
            auto_repair_row,
            text="",
            image=ui_icons.get_icon("refresh", size=15),
            width=28,
            height=24,
            corner_radius=6,
            command=self.reset_auto_repair_count,
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray40"),
        )
        self.auto_repair_reset_btn.pack(side="left", padx=(6, 0))
        self._update_auto_repair_count_display()

        repair_key_row = ctk.CTkFrame(left_body, fg_color="transparent")
        repair_key_row.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(repair_key_row, text="Repair key", font=_small_font, text_color=("gray35", "gray70")).pack(side="left")
        self.repair_key_var = tk.StringVar(value=config.repair_key)
        self.repair_key_btn = ctk.CTkButton(
            repair_key_row,
            width=78,
            height=28,
            text=key_button_label(config.repair_key),
            command=self.register_repair_key,
            font=ui_fonts.mono(10),
            corner_radius=6,
            **styles.CHIP,
        )
        self.repair_key_btn.pack(side="left", padx=(10, 0))
        self.repair_key_var.trace_add('write', lambda *_: self.repair_key_btn.configure(
            text=key_button_label(self.repair_key_var.get()),
        ))
        bind_key_button_clear(self.repair_key_btn, self.clear_repair_key)

        assist_row = ctk.CTkFrame(extras_body, fg_color="transparent")
        assist_row.pack(fill="x", pady=(0, 2))
        self.assist_only_var = tk.BooleanVar(value=config.assist_only_enabled)
        self.assist_only_checkbox = ctk.CTkCheckBox(
            assist_row,
            text="Assist Mode",
            width=_chk_w,
            variable=self.assist_only_var,
            command=self.update_assist_only,
            font=_t_font,
        )
        self.assist_only_checkbox.pack(side="left")
        create_tooltip(self.assist_only_checkbox, "Party assist: presses Assist key on an interval.")

        assist_key_row = ctk.CTkFrame(extras_body, fg_color="transparent")
        assist_key_row.pack(fill="x", pady=(0, 2))
        ctk.CTkLabel(assist_key_row, text="Assist key", font=_small_font, text_color=("gray35", "gray70")).pack(side="left")
        self.assist_key_var = tk.StringVar(value=config.assist_key)
        self.assist_key_btn = ctk.CTkButton(
            assist_key_row,
            width=78,
            height=28,
            text=key_button_label(config.assist_key),
            command=self.register_assist_key,
            font=ui_fonts.mono(10),
            corner_radius=6,
            **styles.CHIP,
        )
        self.assist_key_btn.pack(side="left", padx=(10, 0))
        self.assist_key_var.trace_add('write', lambda *_: self.assist_key_btn.configure(
            text=key_button_label(self.assist_key_var.get()),
        ))
        bind_key_button_clear(self.assist_key_btn, self.clear_assist_key)
        
        # If assist_only is enabled on startup, disable dependent features
        if config.assist_only_enabled:
            # Store previous state before disabling
            if config._assist_only_previous_auto_attack is None:
                config._assist_only_previous_auto_attack = config.auto_attack_enabled
            if config._assist_only_previous_mob_detection is None:
                config._assist_only_previous_mob_detection = config.mob_detection_enabled
            if config._assist_only_previous_auto_change_target is None:
                config._assist_only_previous_auto_change_target = config.auto_change_target_enabled
            
            # Disable features
            config.auto_attack_enabled = False
            config.mob_detection_enabled = False
            config.auto_change_target_enabled = False
            
            # Disable checkboxes in GUI (will be set after widgets are created)
            self.root.after(100, lambda: self._set_assist_only_dependent_widgets_state('disabled'))
        
        # If assist_only is enabled on startup, disable dependent features
        if config.assist_only_enabled:
            if config._assist_only_previous_auto_attack is None:
                config._assist_only_previous_auto_attack = config.auto_attack_enabled
            if config._assist_only_previous_mob_detection is None:
                config._assist_only_previous_mob_detection = config.mob_detection_enabled
            if config._assist_only_previous_auto_change_target is None:
                config._assist_only_previous_auto_change_target = config.auto_change_target_enabled
            config.auto_attack_enabled = False
            config.mob_detection_enabled = False
            config.auto_change_target_enabled = False
            self.root.after(100, lambda: self._set_assist_only_dependent_widgets_state('disabled'))

        # --- Right card (Pots & Unstuck) ---
        auto_hp_row = ctk.CTkFrame(right_body, fg_color="transparent")
        auto_hp_row.pack(fill="x", pady=(0, 6))
        self.auto_hp_var = tk.BooleanVar()
        auto_hp_checkbox = ctk.CTkCheckBox(
            auto_hp_row,
            text="Auto HP",
            variable=self.auto_hp_var,
            command=self.update_auto_hp,
            font=_t_font,
        )
        auto_hp_checkbox.pack(side="left")
        create_tooltip(auto_hp_checkbox, "Uses HP potions based on configured thresholds.")

        hp_thresholds_button = ctk.CTkButton(
            auto_hp_row,
            text="⋯",
            width=28,
            height=28,
            command=self.configure_hp_thresholds,
            font=ctk.CTkFont(size=16),
            **styles.SECONDARY,
            corner_radius=6,
        )
        hp_thresholds_button.pack(side="left", padx=(10, 0))
        create_tooltip(hp_thresholds_button, "Configure multiple HP thresholds and keys.")
        
        # HP bar area input (x, y, width, height) - hidden, only used internally
        self.hp_x_var = tk.StringVar(value=str(config.hp_bar_area['x']))
        self.hp_y_var = tk.StringVar(value=str(config.hp_bar_area['y']))
        self.hp_width_var = tk.StringVar(value=str(config.hp_bar_area['width']))
        self.hp_height_var = tk.StringVar(value=str(config.hp_bar_area['height']))
        self.hp_coords_var = tk.StringVar(value=f"{config.hp_bar_area['x']},{config.hp_bar_area['y']}")
        
        auto_mp_row = ctk.CTkFrame(right_body, fg_color="transparent")
        auto_mp_row.pack(fill="x", pady=(0, 6))
        self.auto_mp_var = tk.BooleanVar()
        auto_mp_checkbox = ctk.CTkCheckBox(
            auto_mp_row,
            text="Auto MP",
            variable=self.auto_mp_var,
            command=self.update_auto_mp,
            font=_t_font,
        )
        auto_mp_checkbox.pack(side="left")
        create_tooltip(auto_mp_checkbox, "Uses MP potions when MP drops below the threshold.")

        self.mp_threshold_var = tk.StringVar(value=str(config.mp_threshold))
        mp_threshold_entry = ctk.CTkEntry(
            auto_mp_row,
            textvariable=self.mp_threshold_var,
            width=52,
            font=_t_font,
        )
        mp_threshold_entry.pack(side="left", padx=(10, 4))
        mp_threshold_entry.bind('<KeyRelease>', lambda event: self.update_mp_threshold())
        mp_threshold_entry.bind('<FocusOut>', lambda event: self.update_mp_threshold())
        ctk.CTkLabel(auto_mp_row, text="%", font=_t_font).pack(side="left")
        create_tooltip(mp_threshold_entry, "MP % threshold (0–100).")

        self.mp_key_var = tk.StringVar(value=config.mp_key)
        def update_mp_key_button_text(var=self.mp_key_var, btn=None):
            btn.configure(text=key_button_label(var.get()))
        mp_key_button = ctk.CTkButton(
            auto_mp_row,
            width=78,
            height=28,
            command=self.register_mp_key,
            font=ui_fonts.mono(10),
            corner_radius=6,
            **styles.CHIP,
        )
        mp_key_button.pack(side="left", padx=(10, 0))
        update_mp_key_button_text(btn=mp_key_button)
        self.mp_key_var.trace_add('write', lambda *args: update_mp_key_button_text(btn=mp_key_button))
        bind_key_button_clear(mp_key_button, self.clear_mp_key)
        
        # MP bar area input (x, y, width, height) - hidden, only used internally
        self.mp_x_var = tk.StringVar(value=str(config.mp_bar_area['x']))
        self.mp_y_var = tk.StringVar(value=str(config.mp_bar_area['y']))
        self.mp_width_var = tk.StringVar(value=str(config.mp_bar_area['width']))
        self.mp_height_var = tk.StringVar(value=str(config.mp_bar_area['height']))
        self.mp_coords_var = tk.StringVar(value=f"{config.mp_bar_area['x']},{config.mp_bar_area['y']}")
        
        auto_unstuck_row = ctk.CTkFrame(movement_body, fg_color="transparent")
        auto_unstuck_row.pack(fill="x", pady=(0, 2))
        self.auto_change_target_var = tk.BooleanVar(value=config.auto_change_target_enabled)
        self.auto_change_target_checkbox = ctk.CTkCheckBox(
            auto_unstuck_row,
            text="Auto Unstuck",
            variable=self.auto_change_target_var,
            command=self.update_auto_change_target,
            font=_t_font,
        )
        self.auto_change_target_checkbox.pack(side="left")
        create_tooltip(self.auto_change_target_checkbox, "Switch target if enemy HP stops changing for too long.")

        self.unstuck_timeout_var = tk.StringVar(value=str(config.unstuck_timeout))
        unstuck_timeout_entry = ctk.CTkEntry(
            auto_unstuck_row,
            textvariable=self.unstuck_timeout_var,
            width=52,
            font=_t_font,
        )
        unstuck_timeout_entry.pack(side="left", padx=(10, 4))
        unstuck_timeout_entry.bind('<KeyRelease>', lambda event: self.update_unstuck_timeout())
        unstuck_timeout_entry.bind('<FocusOut>', lambda event: self.update_unstuck_timeout())
        ctk.CTkLabel(auto_unstuck_row, text="s", font=_t_font).pack(side="left")
        create_tooltip(unstuck_timeout_entry, "Seconds before considering HP stagnant.")

        auto_rotate_row = ctk.CTkFrame(movement_body, fg_color="transparent")
        auto_rotate_row.pack(fill="x", pady=(0, 2))
        self.auto_rotate_var = tk.BooleanVar(value=config.auto_rotate_enabled)
        self.auto_rotate_checkbox = ctk.CTkCheckBox(
            auto_rotate_row,
            text="Auto Rotate Camera",
            variable=self.auto_rotate_var,
            command=self.update_auto_rotate,
            font=_t_font,
        )
        self.auto_rotate_checkbox.pack(side="left")
        create_tooltip(
            self.auto_rotate_checkbox,
            "Every few seconds, briefly focus the game and spin the camera (hold right-click "
            "+ drag) so nameplate detection isn't fooled by the background and hidden mobs "
            "come into view. Set the interval on the right.",
        )

        ctk.CTkLabel(auto_rotate_row, text="every", font=_t_font).pack(side="left", padx=(10, 4))
        self.auto_rotate_interval_var = tk.StringVar(value=str(config.auto_rotate_interval))
        auto_rotate_interval_entry = ctk.CTkEntry(
            auto_rotate_row,
            textvariable=self.auto_rotate_interval_var,
            width=52,
            font=_t_font,
        )
        auto_rotate_interval_entry.pack(side="left", padx=(0, 4))
        auto_rotate_interval_entry.bind('<KeyRelease>', lambda event: self.update_auto_rotate_timing())
        auto_rotate_interval_entry.bind('<FocusOut>', lambda event: self.update_auto_rotate_timing())
        ctk.CTkLabel(auto_rotate_row, text="s", font=_t_font).pack(side="left")
        create_tooltip(auto_rotate_interval_entry, "Seconds between camera rotations.")

        mob_card, mob_filter_body = _collapsible_card(
            settings_frame, "Mob Filter (advanced)",
            "Only attack specific mobs you\u2019ve taught the bot to recognize.",
        )
        mob_card.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=15, pady=(6, 12))
        mob_filter_body.columnconfigure(0, weight=1)

        self.mob_detection_var = tk.BooleanVar()
        self.mob_checkbox = ctk.CTkCheckBox(
            mob_filter_body, text="Enable mob filter",
            variable=self.mob_detection_var,
            command=self.update_mob_detection,
            font=ctk.CTkFont(size=11),
            state="disabled",
        )
        self.mob_checkbox.pack(anchor="w", pady=(0, 6))
        create_tooltip(
            self.mob_checkbox,
            "Only attack mobs that match learned templates. Set Enemy Name in Region Editor, then Learn.",
        )

        self.mob_elite_skip_var = tk.BooleanVar(value=config.mob_elite_skip_enabled)
        self.mob_elite_skip_checkbox = ctk.CTkCheckBox(
            mob_filter_body,
            text="Skip elite mobs (higher max HP, same name)",
            variable=self.mob_elite_skip_var,
            command=self.update_mob_elite_skip,
            font=ctk.CTkFont(size=11),
            state="disabled",
        )
        self.mob_elite_skip_checkbox.pack(anchor="w", pady=(0, 6))
        create_tooltip(
            self.mob_elite_skip_checkbox,
            "Learn templates from normal mobs only. Elites with the same name but larger HP numbers are skipped.",
        )

        self_target_row = ctk.CTkFrame(mob_filter_body, fg_color="transparent")
        self_target_row.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(
            self_target_row, text="Self-target key", font=ctk.CTkFont(size=11),
        ).pack(side="left")
        self.self_target_key_var = tk.StringVar(value=config.self_target_key)
        self.self_target_entry = ctk.CTkEntry(
            self_target_row, textvariable=self.self_target_key_var, width=44, height=28,
        )
        self.self_target_entry.pack(side="left", padx=(10, 0))
        self.self_target_entry.bind('<FocusOut>', lambda _e: self.update_self_target_key())
        create_tooltip(
            self.self_target_entry,
            "In-game key that focuses your character (default `). "
            "Pressed before retarget and before buffs when mob filter is on.",
        )

        self.mob_safe_buffs_var = tk.BooleanVar(value=config.mob_filter_safe_buffs)
        self.mob_safe_buffs_checkbox = ctk.CTkCheckBox(
            mob_filter_body,
            text="Buffs only when not fighting",
            variable=self.mob_safe_buffs_var,
            command=self.update_mob_safe_buffs,
            font=ctk.CTkFont(size=11),
            state="disabled",
        )
        self.mob_safe_buffs_checkbox.pack(anchor="w", pady=(0, 6))
        create_tooltip(
            self.mob_safe_buffs_checkbox,
            "Skip auto-buffs while a mob is targeted. HP/MP pots always work in combat. "
            "Uses self-target key before buffs when safe.",
        )

        mob_btn_row = ctk.CTkFrame(mob_filter_body, fg_color="transparent")
        mob_btn_row.pack(fill="x", pady=(0, 8))
        self.mob_scan_label = ctk.CTkLabel(
            mob_btn_row, text=self._mob_scan_status_text(),
            font=ctk.CTkFont(size=10), text_color=("gray40", "gray60"), anchor='w',
        )
        self.mob_scan_label.pack(side="left", padx=(0, 12))
        self.mob_learn_btn = ctk.CTkButton(
            mob_btn_row, text="Learn", command=self._learn_mob_template,
            width=68, height=28, corner_radius=6, state="disabled",
            **styles.SECONDARY,
        )
        self.mob_learn_btn.pack(side="left", padx=(0, 6))
        self.mob_remove_btn = ctk.CTkButton(
            mob_btn_row, text="Remove", command=self._remove_mob_template,
            width=76, height=28, corner_radius=6,
            state="disabled", **styles.SECONDARY,
        )
        self.mob_remove_btn.pack(side="left", padx=(0, 6))
        self.mob_test_btn = ctk.CTkButton(
            mob_btn_row, text="Test match", command=self._test_mob_match,
            width=96, height=28, corner_radius=6,
            state="disabled", **styles.SECONDARY,
        )
        self.mob_test_btn.pack(side="left", padx=(0, 6))

        self.mob_compare_btn = ctk.CTkButton(
            mob_btn_row, text="Compare", command=self._compare_selected_mob_template_live,
            width=84, height=28, corner_radius=6,
            state="disabled", **styles.SECONDARY,
        )
        self.mob_compare_btn.pack(side="left")

        mob_body = ctk.CTkFrame(
            mob_filter_body, fg_color=("gray88", "gray17"), corner_radius=8,
        )
        mob_body.pack(fill="x", pady=(0, 6))
        mob_body.columnconfigure(1, weight=1)
        mob_body.rowconfigure(0, weight=1)

        list_col = ctk.CTkFrame(mob_body, fg_color="transparent")
        list_col.grid(row=0, column=0, sticky="ns", padx=(10, 6), pady=10)
        ctk.CTkLabel(
            list_col, text="Templates", font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("gray30", "gray70"),
        ).pack(anchor="w", pady=(0, 4))
        self.mob_listbox = tk.Listbox(
            list_col, width=12, height=6, exportselection=False,
            bg='#2b2b2b', fg='white', selectbackground='#1f538d',
            selectforeground='white', highlightthickness=0, bd=0,
            font=(ui_fonts.APP_FONT_FAMILY, 10),
        )
        self.mob_listbox.pack(fill="y")
        self.mob_listbox.bind('<<ListboxSelect>>', lambda _e: self._update_mob_preview())

        preview_col = ctk.CTkFrame(mob_body, fg_color="transparent")
        preview_col.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        preview_col.columnconfigure(0, weight=1)
        preview_col.rowconfigure(0, weight=1)
        ctk.CTkLabel(
            preview_col, text="Preview", font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("gray30", "gray70"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        preview_box = ctk.CTkFrame(
            preview_col, height=88, corner_radius=6,
            border_width=1, border_color=("gray70", "gray35"),
            fg_color=("gray88", "gray14"),
        )
        preview_box.grid(row=1, column=0, sticky="nsew")
        preview_box.grid_propagate(False)
        preview_box.columnconfigure(0, weight=1)
        preview_box.rowconfigure(0, weight=1)
        self._mob_preview_photo = None
        self.mob_preview_label = tk.Label(
            preview_box, bg='#242424', bd=0, highlightthickness=0,
        )
        self.mob_preview_label.grid(row=0, column=0, sticky="nsew", padx=6, pady=4)
        self.mob_preview_caption = ctk.CTkLabel(
            preview_col, text='Select a template', font=ctk.CTkFont(size=10),
            text_color=("gray40", "gray60"), anchor='w',
        )
        self.mob_preview_caption.grid(row=2, column=0, sticky="ew", pady=(4, 0))

        self.mob_filter_help = ctk.CTkLabel(
            mob_filter_body,
            text='Set Enemy Name in Region Editor (full width of the name/level bar). '
                 'Learn saves that exact region. Matching uses name text shape, not OCR. '
                 'Re-learn templates if you change the region.',
            font=ctk.CTkFont(size=10), text_color=("gray40", "gray60"), anchor='w',
            justify='left',
        )
        self.mob_filter_help.pack(fill='x', pady=(0, 4))

        def _sync_mob_help_wrap(_event=None):
            if not hasattr(self, 'mob_filter_help'):
                return
            w = settings_frame.winfo_width()
            if w > 60:
                self.mob_filter_help.configure(wraplength=max(200, w - 80))

        settings_frame.bind('<Configure>', _sync_mob_help_wrap, add='+')
        self.root.after(100, _sync_mob_help_wrap)

        self._refresh_mob_list()
        self.update_mob_filter_ui_state()
        
        settings_frame.rowconfigure(13, weight=0)
        
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
        # Wrap skill sequence tab in scrollable frame
        skill_sequence_scroll = ctk.CTkScrollableFrame(skill_sequence_tab)
        skill_sequence_scroll.pack(fill="both", expand=True)
        skill_sequence_frame = skill_sequence_scroll
        
        # Instructions collapse: read once while setting the tab up, and
        # they were taking 160px above the controls they describe.
        info_frame, info_body = _collapsible_card(
            skill_sequence_frame, "How to use", expanded=False,
        )
        info_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 12))

        info_text = ctk.CTkLabel(
            info_body,
            text="1. Click the skill image to select a skill icon\n"
                 "2. Assign a hotkey for each skill (pressed instead of clicking)\n"
                 "3. Left checkbox: include this skill in the rotation\n"
                 "4. Right checkbox: skip this skill while it is on cooldown\n"
                 "   Skills cast in slot order 1\u21922\u21923\u2026 then back to 1. A skill\n"
                 "   without \u201cskip\u201d is waited for, so the order is never broken.\n"
                 "   (Runs when an enemy is found — set Skill Bar in Region Editor)",
            font=_t_font, text_color=("gray35", "gray65"),
            justify="left", anchor="w",
        )
        info_text.grid(row=0, column=0, sticky="w")

        # Initialize skill sequence variables
        self.skill_sequence_vars = {}
        self.skill_sequence_bypass_vars = {}
        self.skill_sequence_key_vars = {}
        self.skill_sequence_canvases = []
        self.skill_sequence_state = []
        
        # Create skill sequence slots in a compact grid (2 columns, 4 rows)
        for i in range(8):
            if i < 4:
                # First column: slots 1-4
                row = i + 1  # +1 because info_frame is at row 0
                col = 0
            else:
                # Second column: slots 5-8
                row = i - 3  # -3 because info_frame is at row 0, and we want slots 5-8 to start at row 2
                col = 1
            
            # Create compact frame for each skill sequence slot (horizontal layout)
            skill_slot_frame = ctk.CTkFrame(skill_sequence_frame, corner_radius=6, fg_color=("gray18", "gray14"))
            padx_left = 10 if col == 0 else 5
            padx_right = 5 if col == 0 else 10
            skill_slot_frame.grid(row=row, column=col, sticky="ew", padx=(padx_left, padx_right), pady=3)
            skill_slot_frame.columnconfigure(3, weight=1)  # Make column 3 expandable to push bypass to right
            
            # Enable checkbox (no text, just the box)
            self.skill_sequence_vars[i] = tk.BooleanVar(value=config.skill_sequence_config[i]['enabled'])
            checkbox = ctk.CTkCheckBox(skill_slot_frame, text="", 
                                      variable=self.skill_sequence_vars[i],
                                      command=lambda idx=i: self.update_skill_sequence_enabled(idx),
                                      font=ctk.CTkFont(size=10), width=20)
            checkbox.grid(row=0, column=0, padx=(8, 5), pady=6, sticky="w")
            
            # Label for slot info
            slot_label = ctk.CTkLabel(skill_slot_frame, text=f"Skill {i+1}", 
                                     font=ctk.CTkFont(size=11, weight="bold"), width=60)
            slot_label.grid(row=0, column=1, padx=(0, 5), pady=6, sticky="w")

            canvas = tk.Canvas(skill_slot_frame, width=40, height=40, bg='gray20',
                             highlightthickness=1, highlightbackground='gray50', cursor='hand2')
            canvas.grid(row=0, column=2, padx=5, pady=6)
            canvas.bind('<Button-1>', lambda e, idx=i: self.show_skill_sequence_selector(idx))
            canvas.bind('<Button-3>', lambda e, idx=i: self.clear_skill_sequence_skill(idx))
            self.skill_sequence_canvases.append(canvas)

            self.skill_sequence_key_vars[i] = tk.StringVar(
                value=config.skill_sequence_config[i].get('key', ''),
            )
            key_btn = ctk.CTkButton(
                skill_slot_frame, width=72, height=28, text=KEY_BUTTON_DEFAULT_LABEL,
                command=lambda idx=i: self.register_skill_sequence_key(idx),
                font=ui_fonts.mono(10), corner_radius=6, **styles.CHIP,
            )
            key_btn.grid(row=0, column=3, padx=(5, 5), pady=6, sticky="w")
            self.skill_sequence_key_vars[i].trace_add(
                'write',
                lambda *_a, idx=i, btn=key_btn: btn.configure(
                    text=key_button_label(self.skill_sequence_key_vars[idx].get()),
                ),
            )
            if config.skill_sequence_config[i].get('key'):
                key_btn.configure(text=key_button_label(config.skill_sequence_config[i]['key']))
            bind_key_button_clear(key_btn, lambda idx=i: self.clear_skill_sequence_key(idx))

            # Skip if on cooldown (icon not visible in the Skill Area)
            self.skill_sequence_bypass_vars[i] = tk.BooleanVar(value=config.skill_sequence_config[i].get('bypass', False))
            bypass_checkbox = ctk.CTkCheckBox(skill_slot_frame, text="",
                                             variable=self.skill_sequence_bypass_vars[i],
                                             command=lambda idx=i: self.update_skill_sequence_bypass(idx),
                                             font=ctk.CTkFont(size=10), width=20)
            bypass_checkbox.grid(row=0, column=4, padx=(5, 8), pady=6, sticky="e")
            create_tooltip(
                bypass_checkbox,
                "Skip if on cooldown: when this skill's icon is not found in the Skill Area "
                "(likely on cooldown), move on to the next skill instead of waiting for it. "
                "Leave unticked to keep this skill's place in the order.",
            )
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
        skill_sequence_frame.columnconfigure(1, weight=1)
        
        # Initialize skill sequence manager
        import skill_sequence_manager
        config.skill_sequence_manager = skill_sequence_manager.SkillSequenceManager(num_skills=8)
        config.skill_sequence_manager.set_ui_reference(self)
        
        # Skill slots frame - moved to Skill Interval tab (wrap in scrollable frame)
        skill_scroll = ctk.CTkScrollableFrame(skills_tab)
        skill_scroll.pack(fill="both", expand=True)
        skill_frame = skill_scroll
        
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
            interval_entry.grid(row=0, column=2, padx=(0, 5))
            interval_entry.bind('<KeyRelease>', lambda event, s=slot: self.update_skill_interval(s))
            interval_entry.bind('<FocusOut>', lambda event, s=slot: self.update_skill_interval(s))
            # Seconds label
            seconds_label = ctk.CTkLabel(slot_frame, text="s", font=ctk.CTkFont(size=11))
            seconds_label.grid(row=0, column=3, sticky="w")
            # Tooltip for skill interval
            slot_name = f"S{slot}" if isinstance(slot, int) else slot.upper()
            create_tooltip(interval_entry, f"Input: {slot_name} cooldown interval in seconds. Enter the minimum time (in seconds) that must pass before this skill can be used again. Skill will only trigger if this cooldown has elapsed since last use. Example: 10 means skill can be used every 10 seconds.")
        
        # Section 1: Numeric slots (1-9, 0) - 5 rows x 2 columns
        numeric_label = ctk.CTkLabel(skill_frame, text="Number Keys (1-9, 0):", font=ctk.CTkFont(size=12, weight="bold"))
        numeric_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(15, 10))
        
        # Numeric slots layout: 5 rows x 2 columns
        numeric_row = 1
        # First create slots 1-9
        for i in range(1, 10):
            if i <= 5:
                # First column: slots 1-5
                row = numeric_row + (i - 1)
                col = 0
            else:
                # Second column: slots 6-9
                row = numeric_row + (i - 6)
                col = 1
            create_slot_control(skill_frame, i, row, col)
        
        # Then add slot 0 after 9 (in the second column, last row)
        create_slot_control(skill_frame, 0, numeric_row + 4, 1)
        
        # Separator between numeric and function key sections
        separator_row = numeric_row + 5
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
        # Wrap buffs tab in scrollable frame
        buffs_scroll = ctk.CTkScrollableFrame(buffs_tab)
        buffs_scroll.pack(fill="both", expand=True)
        buffs_frame = buffs_scroll
        
        buffs_info_frame, buffs_info_body = _collapsible_card(
            buffs_frame, "How to use", expanded=False,
        )
        buffs_info_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 12))

        buffs_info_text = ctk.CTkLabel(
            buffs_info_body,
            text="1. Set Buff Strip in Region Editor (active buff icons)\n"
                 "2. Click a buff image to detect when it is already active\n"
                 "3. Assign a hotkey — pressed when the buff is missing",
            font=_t_font, text_color=("gray35", "gray65"),
            justify="left", anchor="w",
        )
        buffs_info_text.grid(row=0, column=0, sticky="w")

        # Initialize buffs variables
        self.buffs_vars = {}
        self.buffs_key_vars = {}
        self.buffs_canvases = []
        self.buffs_state = []
        
        # Create buff slots in a compact grid (2 columns, 4 rows)
        for i in range(8):
            if i < 4:
                # First column: slots 1-4
                row = i + 1  # +1 because buffs_info_frame is at row 0
                col = 0
            else:
                # Second column: slots 5-8
                row = i - 3  # -3 because buffs_info_frame is at row 0, and we want slots 5-8 to start at row 2
                col = 1
            
            # Create compact frame for each buff slot (horizontal layout)
            buff_slot_frame = ctk.CTkFrame(buffs_frame, corner_radius=6, fg_color=("gray18", "gray14"))
            padx_left = 10 if col == 0 else 5
            padx_right = 5 if col == 0 else 10
            buff_slot_frame.grid(row=row, column=col, sticky="ew", padx=(padx_left, padx_right), pady=3)
            buff_slot_frame.columnconfigure(3, weight=1)
            
            # Enable checkbox (no text, just the box)
            self.buffs_vars[i] = tk.BooleanVar(value=config.buffs_config[i]['enabled'])
            checkbox = ctk.CTkCheckBox(buff_slot_frame, text="", 
                                      variable=self.buffs_vars[i],
                                      command=lambda idx=i: self.update_buff_enabled(idx),
                                      font=ctk.CTkFont(size=10), width=20)
            checkbox.grid(row=0, column=0, padx=(8, 5), pady=6, sticky="w")
            
            # Label for slot info
            slot_label = ctk.CTkLabel(buff_slot_frame, text=f"Buff {i+1}", 
                                     font=ctk.CTkFont(size=11, weight="bold"), width=60)
            slot_label.grid(row=0, column=1, padx=(0, 5), pady=6, sticky="w")
            
            # Skill image canvas (clickable to select skill) - smaller size
            canvas = tk.Canvas(buff_slot_frame, width=40, height=40, bg='gray20', 
                             highlightthickness=1, highlightbackground='gray50', cursor='hand2')
            canvas.grid(row=0, column=2, padx=5, pady=6)
            canvas.bind('<Button-1>', lambda e, idx=i: self.show_buff_skill_selector(idx))
            canvas.bind('<Button-3>', lambda e, idx=i: self.clear_buff_skill(idx))
            self.buffs_canvases.append(canvas)

            self.buffs_key_vars[i] = tk.StringVar(value=config.buffs_config[i].get('key', ''))
            buff_key_btn = ctk.CTkButton(
                buff_slot_frame, width=72, height=28, text=KEY_BUTTON_DEFAULT_LABEL,
                command=lambda idx=i: self.register_buff_key(idx),
                font=ui_fonts.mono(10), corner_radius=6, **styles.CHIP,
            )
            buff_key_btn.grid(row=0, column=3, padx=(5, 8), pady=6, sticky="e")
            self.buffs_key_vars[i].trace_add(
                'write',
                lambda *_a, idx=i, btn=buff_key_btn: btn.configure(
                    text=key_button_label(self.buffs_key_vars[idx].get()),
                ),
            )
            if config.buffs_config[i].get('key'):
                buff_key_btn.configure(text=key_button_label(config.buffs_config[i]['key']))
            bind_key_button_clear(buff_key_btn, lambda idx=i: self.clear_buff_key(idx))

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
        buffs_frame.columnconfigure(1, weight=1)
        
        # Initialize buffs manager
        import buffs_manager
        config.buffs_manager = buffs_manager.BuffsManager(num_buffs=8)
        config.buffs_manager.set_ui_reference(self)
        
        # Mouse Clicker frame - moved to Mouse Clicker tab
        # Wrap mouse clicker tab in scrollable frame
        mouse_clicker_scroll = ctk.CTkScrollableFrame(mouse_clicker_tab)
        mouse_clicker_scroll.pack(fill="both", expand=True)
        mouse_clicker_frame = mouse_clicker_scroll
        
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
        mouse_clicker_interval_entry.bind('<FocusOut>', lambda event: self.update_mouse_clicker_interval())
        
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
        mouse_clicker_picker_btn = ctk.CTkButton(self.mouse_clicker_coords_frame, text="...", command=self.pick_mouse_clicker_coordinates, width=30, corner_radius=6,
                                                  **styles.SECONDARY)
        mouse_clicker_picker_btn.grid(row=0, column=0, padx=(0, 0))
        
        # Initially hide/show coords frame based on mode
        self.update_mouse_clicker_mode()
        
        # Configure mouse clicker frame
        mouse_clicker_frame.columnconfigure(0, weight=1)
        
        
        # Load initial window list
        self.refresh_windows()

        # Provide GUI overlay snapshot to settings_manager (no GUI import in settings_manager).
        settings_manager.register_gui_overlay_provider(lambda: collect_gui_overlay(self))
        
        # Load default profile on startup (changes are not written until Save)
        settings_manager.reset_settings_path()
        if settings_manager.load_settings(config.SETTINGS_FILE):
            self.apply_settings_to_gui()
            print("Settings loaded on startup")
        else:
            config.set_profile_mob_templates_dir(config.SETTINGS_FILE)
            import mob_template_store
            mob_template_store.sync_templates_after_load()
            if hasattr(self, 'mob_listbox'):
                self._refresh_mob_list()
        self._update_settings_profile_label()
        
        self.update_regions_button_state()
        self.update_toggle_bot_button_state()
        # Refresh mob list once the window is mapped (listbox updates can be dropped during __init__).
        self.root.after(0, self._refresh_mob_list)
        
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
    
    def on_window_change(self, *args):
        """Called when window selection changes - reset connection"""
        import frame_cache
        frame_cache.invalidate()
        config.calibrator = None
        if config.connected_window:
            config.connected_window = None
            self.connect_button.configure(text="Connect", state="normal")
            self.update_regions_button_state()
            self.toggle_bot_button.configure(state="disabled")
            self.connection_label.configure(text="Not connected")
            self.status_label.configure(text="Disconnected")
            print("Window changed - connection reset")
            self.update_mob_filter_ui_state()

    def open_region_editor(self):
        """Open the visual region editor popup."""
        from ui.region_editor import open_region_editor
        open_region_editor(self.root, self)

    def refresh_region_pick_labels(self):
        """Refresh region button state after editor save or settings load."""
        self.update_regions_button_state()
        self.update_toggle_bot_button_state()
        self._update_bars_status_label()

    def _update_bars_status_label(self):
        if not hasattr(self, 'bars_status_label'):
            return
        import bar_color_calibration
        hp = config.current_hp_percentage if config.bot_running else None
        mp = config.current_mp_percentage if config.bot_running else None
        text = bar_color_calibration.bars_status_text(hp_pct=hp, mp_pct=mp)
        self.bars_status_label.configure(text=text)

    def update_regions_button_state(self):
        if not hasattr(self, 'regions_button'):
            return
        if not config.connected_window:
            self.regions_button.configure(state='disabled', text='Regions')
            return
        self.regions_button.configure(state='normal')
        if config.bot_regions_ready():
            self.regions_button.configure(text='✓ Regions')
        else:
            self.regions_button.configure(text='Regions')

    def connect_window(self):
        """Refresh the window list, then connect to the selected window."""
        selected_window_title = self.window_var.get()
        invalid = ("", "No windows found", "Error loading windows")
        if selected_window_title and selected_window_title not in invalid:
            self.refresh_windows_with_selection(selected_window_title)
        else:
            self.refresh_windows()
        selected_window_title = self.window_var.get()

        if not selected_window_title or selected_window_title in invalid:
            print("Please select a valid window")
            return
        
        import frame_cache
        frame_cache.invalidate()
        config.calibrator = None
        # Disconnect if already connected
        if config.connected_window:
            config.connected_window = None
        
        # Connect to the selected window
        window_utils.connect_attacker(selected_window_title)
        
        if config.connected_window:
            self.connect_button.configure(text="Connected", state="disabled")
            self.update_toggle_bot_button_state()
            self.connection_label.configure(text=_ellipsize(selected_window_title, 28))
            self.status_label.configure(text="Connected")
            print(f"Successfully connected to: {selected_window_title}")
            try:
                import bar_color_calibration
                migrated = bar_color_calibration.migrate_saved_calibrations(
                    config.connected_window.handle,
                )
                if migrated:
                    print(f"[Connect] Auto-calibrated bar colors: {', '.join(migrated)}")
            except Exception as exc:
                print(f"[Connect] Bar color migration skipped: {exc}")
            if hasattr(self, 'refresh_region_pick_labels'):
                self.refresh_region_pick_labels()
            self.update_mob_filter_ui_state()
        else:
            self.connect_button.configure(text="Connect")
            self.update_regions_button_state()
            self.toggle_bot_button.configure(state="disabled")
            self.connection_label.configure(text="Connect failed")
            self.status_label.configure(text="Connect failed")
            print(f"Failed to connect to: {selected_window_title}")
            self.update_mob_filter_ui_state()

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
                window_utils.focus_game_window(hwnd)
                
                # Create calibrator instance
                calibrator = calibration.Calibrator()
                
                # Perform calibration
                success = calibrator.calibrate(hwnd)
                preview_path = calibrator.last_capture_path
                capture_note = calibrator.last_capture_stats or {}
                capture_method = calibrator.last_capture_method or '?'
                
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
                    mob_filter.sync_scan_area_from_calibration()
                    
                    # Store area_skills from calibrator (calculated in calibration.py)
                    if calibrator.area_skills:
                        config.area_skills = calibrator.area_skills
                        print(f"[Calibration] Skills area loaded from calibrator: {config.area_skills}")
                    
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
                            if config.SYSTEM_MESSAGE_HEIGHT_REDUCTION > 0:
                                print(f"[Calibration] System message area set: {config.system_message_area} (height reduced by {config.SYSTEM_MESSAGE_HEIGHT_REDUCTION}px)")
                            else:
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
                            self.update_toggle_bot_button_state()
                            self.update_mob_filter_ui_state()
                            # Get calibration summary from calibrator (stored in config)
                            if config.calibrator:
                                summary = config.calibrator.get_calibration_summary()
                                messagebox.showinfo("Calibration Success", summary)
                            else:
                                messagebox.showinfo("Calibration Success", 
                                    "Calibration completed successfully!")
                            self._show_calibration_capture_preview(
                                preview_path, capture_method, capture_note, success=True,
                            )
                        except Exception as e:
                            print(f"[Calibration] Error updating GUI: {e}")
                            self.calibrate_button.configure(state="normal", text="Calibrate")
                    
                    self.root.after(0, update_gui)
                else:
                    def show_error():
                        self.calibrate_button.configure(state="normal", text="Calibrate")
                        mean = capture_note.get('mean', 0)
                        black_hint = (
                            "\n\nCapture looks black/empty — try windowed mode, "
                            "keep the game visible on screen, and avoid minimizing."
                            if mean < 6 else ""
                        )
                        messagebox.showerror(
                            "Calibration Failed",
                            "Failed to detect HP/MP bars.\n\n"
                            "Please ensure:\n"
                            "1. The game window is visible (not minimized)\n"
                            "2. Player HP/MP bars are on screen\n"
                            "3. A mob is targeted (enemy name bar visible)\n"
                            "4. Check the capture preview that opens next"
                            f"{black_hint}",
                        )
                        self._show_calibration_capture_preview(
                            preview_path, capture_method, capture_note, success=False,
                        )
                    
                    self.root.after(0, show_error)
                    
            except Exception as e:
                print(f"[Calibration] Error during calibration: {e}")
                import traceback
                traceback.print_exc()
                
                # Bound now: `e` is gone by the time after() runs show_error.
                def show_error(message=str(e)):
                    self.calibrate_button.configure(state="normal", text="Calibrate")
                    messagebox.showerror(
                        "Calibration Error",
                        f"An error occurred during calibration:\n{message}",
                    )
                
                self.root.after(0, show_error)
        
        # Run calibration in separate thread to avoid blocking GUI
        threading.Thread(target=calibration_thread, daemon=True).start()

    def toggle_bot(self):
        """Toggle bot between start and stop states"""
        if not config.bot_running:
            self.start_bot()
        else:
            self.stop_bot()
    

    def update_low_cpu_mode(self):
        """Deprecated: Low CPU mode is always enabled."""
        config.low_cpu_mode = True
    
    
    
    
    
    
    def start_bot(self):
        if not config.bot_running:
            if not config.connected_window:
                print("Please connect to a window first")
                return
            import region_helpers
            preflight = region_helpers.bot_start_preflight_issues()
            if preflight:
                messagebox.showwarning(
                    "Regions Required",
                    "Before starting:\n\n• " + "\n• ".join(preflight),
                )
                return
            
            # Reset all bot state for clean start
            bot_logic.reset_bot_state()
                
            config.bot_running = True
            self._bot_run_start_time = time.time()
            input_handler.initialize_pyautogui()

            config.bot_thread = threading.Thread(target=bot_logic.bot_loop, daemon=True)
            config.bot_thread.start()
            
            self.update_toggle_bot_button_state()
            # Clear any red "Stopped (error)" styling from a previous crash.
            self.status_label.configure(text="Running", text_color=self._status_label_default_color)
            
            # Start periodic status updates
            self.update_status()
        else:
            print("Bot is already running")
            
    def stop_bot(self):
        config.bot_running = False
        self._bot_run_start_time = None

        # Reset all bot state for clean stop
        bot_logic.reset_bot_state()
        
        self.update_toggle_bot_button_state()
        self.status_label.configure(text="Stopped", text_color=self._status_label_default_color)
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
    
    def update_skill_sequence_bypass(self, idx):
        """Update skill sequence bypass status"""
        if hasattr(self, 'skill_sequence_bypass_vars') and idx in self.skill_sequence_bypass_vars:
            config.skill_sequence_config[idx]['bypass'] = self.skill_sequence_bypass_vars[idx].get()
            status = "enabled" if config.skill_sequence_config[idx]['bypass'] else "disabled"
            print(f"Skill Sequence {idx + 1} bypass {status}")
    
    def configure_hp_thresholds(self):
        """Open dialog to configure multiple HP thresholds"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Configure HP Thresholds")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        dialog.geometry(f'+{root_x + 50}+{root_y + 50}')
        
        # Main frame
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(main_frame, text="HP Thresholds Configuration",
                                  font=ctk.CTkFont(size=16, weight="bold"))
        title_label.pack(pady=(0, 10))
        
        # Instructions
        instructions = ctk.CTkLabel(main_frame, 
                                   text="Configure multiple thresholds. When HP drops below a threshold,\nthe corresponding key will be pressed. Thresholds are checked from highest to lowest.",
                                   font=ctk.CTkFont(size=11),
                                   justify="left")
        instructions.pack(pady=(0, 15))
        
        # Scrollable frame for threshold entries
        scroll_frame = ctk.CTkScrollableFrame(main_frame, height=200)
        scroll_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # Initialize thresholds list from config (ensure it exists)
        if not hasattr(config, 'hp_thresholds') or not config.hp_thresholds:
            config.hp_thresholds = [{'threshold': 70, 'key': '0'}]
        
        threshold_widgets = []
        
        def add_threshold_row(threshold_entry=None):
            """Add a new threshold row"""
            row_frame = ctk.CTkFrame(scroll_frame)
            row_frame.pack(fill="x", pady=5)
            
            threshold_var = tk.StringVar(value=str(threshold_entry['threshold']) if threshold_entry else "70")
            key_var = tk.StringVar(value=threshold_entry['key'] if threshold_entry else "0")
            
            # Threshold entry
            threshold_label = ctk.CTkLabel(row_frame, text="Threshold:", width=80)
            threshold_label.grid(row=0, column=0, padx=5, pady=5)
            
            threshold_entry_widget = ctk.CTkEntry(row_frame, textvariable=threshold_var, width=60)
            threshold_entry_widget.grid(row=0, column=1, padx=5, pady=5)
            
            percent_label = ctk.CTkLabel(row_frame, text="%")
            percent_label.grid(row=0, column=2, padx=2, pady=5)
            
            # Key button
            key_label = ctk.CTkLabel(row_frame, text="Key:", width=50)
            key_label.grid(row=0, column=3, padx=5, pady=5)
            
            def update_key_button_text(var=key_var, btn=None):
                btn.configure(text=key_button_label(var.get()))
            
            key_button = ctk.CTkButton(row_frame, width=72, height=28,
                                      command=lambda: self.register_key_in_dialog(key_var, dialog),
                                      font=ui_fonts.mono(10), corner_radius=4,
                                      **styles.CHIP)
            key_button.grid(row=0, column=4, padx=5, pady=5)
            update_key_button_text(btn=key_button)
            key_var.trace_add('write', lambda *args: update_key_button_text(btn=key_button))
            bind_key_button_clear(key_button, lambda var=key_var: var.set(''))

            # Delete button
            delete_button = ctk.CTkButton(row_frame, text="×", width=30, height=28,
                                         command=lambda: remove_threshold_row(row_frame, widget_data),
                                         font=ctk.CTkFont(size=16), corner_radius=4,
                                         **styles.SECONDARY)
            delete_button.grid(row=0, column=5, padx=5, pady=5)
            
            widget_data = {
                'frame': row_frame,
                'threshold_var': threshold_var,
                'key_var': key_var,
                'key_button': key_button
            }
            threshold_widgets.append(widget_data)
        
        def remove_threshold_row(row_frame, widget_data):
            """Remove a threshold row"""
            if len(threshold_widgets) > 1:  # Keep at least one row
                row_frame.destroy()
                threshold_widgets.remove(widget_data)
            else:
                messagebox.showwarning("Warning", "At least one threshold must be configured.")
        
        # Add initial rows from config
        for threshold_entry in config.hp_thresholds:
            add_threshold_row(threshold_entry)
        
        # If no thresholds, add one default
        if not threshold_widgets:
            add_threshold_row()
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=(10, 0))
        
        add_button = ctk.CTkButton(buttons_frame, text="Add Threshold", width=120,
                                   command=lambda: add_threshold_row(), **styles.SECONDARY)
        add_button.pack(side="left", padx=5)
        
        def save_thresholds():
            """Save thresholds to config"""
            try:
                new_thresholds = []
                for widget_data in threshold_widgets:
                    threshold_str = widget_data['threshold_var'].get().strip()
                    key_str = widget_data['key_var'].get().strip()
                    
                    if not threshold_str or not key_str:
                        messagebox.showerror("Error", "All thresholds must have both a percentage and a key.")
                        return
                    
                    try:
                        threshold = float(threshold_str)
                        if not (0 <= threshold <= 100):
                            messagebox.showerror("Error", "Threshold must be between 0 and 100.")
                            return
                    except ValueError:
                        messagebox.showerror("Error", f"Invalid threshold value: {threshold_str}")
                        return
                    
                    new_thresholds.append({
                        'threshold': threshold,
                        'key': key_str.lower()
                    })
                
                # Sort by threshold (highest first) and save
                new_thresholds.sort(key=lambda x: x['threshold'], reverse=True)
                config.hp_thresholds = new_thresholds
                
                # Update display summary (optional - could show in tooltip or label)
                print(f"HP thresholds configured: {len(new_thresholds)} thresholds")
                for t in new_thresholds:
                    print(f"  {t['threshold']}% = key {t['key']}")
                
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save thresholds: {e}")
        
        save_button = ctk.CTkButton(buttons_frame, text="Save", width=100,
                                   command=save_thresholds, **styles.ACCENT)
        save_button.pack(side="right", padx=5)
        
        cancel_button = ctk.CTkButton(buttons_frame, text="Cancel", width=100,
                                     command=dialog.destroy, **styles.SECONDARY)
        cancel_button.pack(side="right", padx=5)
        
        dialog.focus_set()
    
    def register_key_in_dialog(self, key_var, parent_dialog):
        """Register a key for HP threshold in the dialog"""
        popup = ctk.CTkToplevel(parent_dialog)
        popup.title("Press a key")
        popup.geometry("300x150")
        popup.transient(parent_dialog)
        popup.grab_set()
        
        parent_x = parent_dialog.winfo_x()
        parent_y = parent_dialog.winfo_y()
        popup.geometry(f'+{parent_x + 50}+{parent_y + 50}')
        
        label = ctk.CTkLabel(popup, text="Press any key to register...", 
                            font=ctk.CTkFont(size=12))
        label.pack(pady=30)
        
        def on_key_press(event):
            key = event.keysym.upper()
            
            # Check for modifier keys
            modifiers = []
            state = event.state
            keysym = event.keysym.upper()
            
            # Check state bits for modifiers
            if state & 0x0004:  # Control key
                modifiers.append('Ctrl')
            if state & 0x0001:  # Shift key
                modifiers.append('Shift')
            # Check for Alt key - can be in state or keysym
            if state & 0x20000 or keysym in ['ALT_L', 'ALT_R', 'META']:  # Alt key
                if 'Alt' not in modifiers:
                    modifiers.append('Alt')
            
            # Check if it's a number key (0-9)
            if key in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
                if modifiers:
                    # Combine modifier with number (e.g., "Ctrl+1", "Shift+2")
                    combined_key = '+'.join(modifiers) + '+' + key
                    key_var.set(combined_key)
                    print(f"Key registered: {combined_key}")
                    popup.destroy()
                    return
                else:
                    # Just the number key
                    key_var.set(key)
                    print(f"Key registered: {key}")
                    popup.destroy()
                    return
            
            # Handle single character keys (letters, etc.)
            if len(key) == 1:
                if modifiers:
                    # Combine modifier with key
                    combined_key = '+'.join(modifiers) + '+' + key
                    key_var.set(combined_key)
                    print(f"Key registered: {combined_key}")
                    popup.destroy()
                else:
                    key_var.set(key)
                    print(f"Key registered: {key}")
                    popup.destroy()
            elif key in ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12']:
                if modifiers:
                    combined_key = '+'.join(modifiers) + '+' + key
                    key_var.set(combined_key)
                    print(f"Key registered: {combined_key}")
                    popup.destroy()
                else:
                    key_var.set(key)
                    print(f"Key registered: {key}")
                    popup.destroy()
            elif key in ['SPACE', 'TAB', 'RETURN', 'ESCAPE']:
                key_map = {
                    'SPACE': 'SPACE',
                    'TAB': 'TAB',
                    'RETURN': 'ENTER',
                    'ESCAPE': 'ESC'
                }
                mapped_key = key_map.get(key, key)
                if modifiers:
                    combined_key = '+'.join(modifiers) + '+' + mapped_key
                    key_var.set(combined_key)
                    print(f"Key registered: {combined_key}")
                    popup.destroy()
                else:
                    key_var.set(mapped_key)
                    print(f"Key registered: {mapped_key}")
                    popup.destroy()
        
        popup.bind('<Key>', on_key_press)
        popup.focus_set()
        
        cancel_btn = ctk.CTkButton(popup, text="Cancel", command=popup.destroy, width=100,
                                   **styles.SECONDARY)
        cancel_btn.pack(pady=10)
    
    def register_mp_key(self):
        """Register a key for MP potion by capturing keyboard input"""
        def set_value(value: str):
            self.mp_key_var.set(value)
            config.mp_key = value.lower()
            logger.info(f"MP key registered: {value}", "Keybind")

        open_keybind_dialog(
            self.root,
            title="Press a key",
            prompt="Press any key to register...",
            on_value=set_value,
        )
    
    def clear_mp_key(self):
        """Clear MP key"""
        self.mp_key_var.set('')
        config.mp_key = ''

    def clear_repair_key(self):
        """Clear repair key"""
        self.repair_key_var.set('')
        config.repair_key = ''

    def clear_assist_key(self):
        """Clear assist key"""
        self.assist_key_var.set('')
        config.assist_key = ''

    def clear_skill_sequence_key(self, idx):
        """Clear skill sequence hotkey for a slot"""
        self.skill_sequence_key_vars[idx].set('')
        config.skill_sequence_config[idx]['key'] = ''

    def clear_buff_key(self, idx):
        """Clear buff hotkey for a slot"""
        self.buffs_key_vars[idx].set('')
        config.buffs_config[idx]['key'] = ''

    def register_repair_key(self):
        def set_value(value: str):
            self.repair_key_var.set(value)
            config.repair_key = value.lower()
        open_keybind_dialog(self.root, title="Repair key", prompt="Press repair hotkey...", on_value=set_value)

    def register_assist_key(self):
        def set_value(value: str):
            self.assist_key_var.set(value)
            config.assist_key = value.lower()
        open_keybind_dialog(self.root, title="Assist key", prompt="Press assist hotkey...", on_value=set_value)

    def register_skill_sequence_key(self, idx):
        def set_value(value: str):
            self.skill_sequence_key_vars[idx].set(value)
            config.skill_sequence_config[idx]['key'] = value.lower()
        open_keybind_dialog(
            self.root, title=f"Skill {idx + 1} key",
            prompt="Press skill hotkey...", on_value=set_value,
        )

    def register_buff_key(self, idx):
        def set_value(value: str):
            self.buffs_key_vars[idx].set(value)
            config.buffs_config[idx]['key'] = value.lower()
        open_keybind_dialog(
            self.root, title=f"Buff {idx + 1} key",
            prompt="Press buff hotkey...", on_value=set_value,
        )

    def _update_auto_repair_count_display(self):
        if not hasattr(self, 'auto_repair_count_label'):
            return
        import auto_repair
        needed = auto_repair.get_repair_trigger_count()
        count = auto_repair.get_repair_count()
        if not config.auto_repair_enabled:
            text = f"—/{needed}"
            color = "gray"
            progress = 0.0
        else:
            text = f"{count}/{needed}"
            if count >= needed:
                color = "green"
            elif count > 0:
                color = "orange"
            else:
                color = "gray"
            progress = min(1.0, count / needed) if needed > 0 else 0.0
        self.auto_repair_count_label.configure(text=text, text_color=color)
        if hasattr(self, 'auto_repair_progress'):
            self.auto_repair_progress.set(progress)
            if not config.auto_repair_enabled:
                self.auto_repair_progress.configure(progress_color=("gray60", "gray45"))
            elif count >= needed:
                self.auto_repair_progress.configure(progress_color=("green", "green"))
            elif count > 0:
                self.auto_repair_progress.configure(progress_color=("orange", "orange"))
            else:
                self.auto_repair_progress.configure(progress_color=("#1f538d", "#1f538d"))

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
    
    def update_looting_duration(self):
        """Update looting duration value"""
        try:
            duration = float(self.looting_duration_var.get())
            if duration > 0:
                config.LOOTING_DURATION = duration
                print(f"Looting duration updated to {config.LOOTING_DURATION} seconds")
            else:
                print(f"Invalid looting duration: must be greater than 0")
                self.looting_duration_var.set(str(config.LOOTING_DURATION))
        except ValueError:
            print(f"Invalid looting duration value")
            self.looting_duration_var.set(str(config.LOOTING_DURATION))
    
    def update_mob_elite_skip(self):
        """Update elite mob skip setting."""
        config.mob_elite_skip_enabled = self.mob_elite_skip_var.get()
        status = "enabled" if config.mob_elite_skip_enabled else "disabled"
        print(f"Elite mob skip {status}")

    def update_self_target_key(self):
        """Update self-target key used with mob filter."""
        key = self.self_target_key_var.get().strip()
        config.self_target_key = key or '`'
        if not key:
            self.self_target_key_var.set('`')

    def update_mob_safe_buffs(self):
        """Update whether buffs wait until not in combat."""
        config.mob_filter_safe_buffs = bool(self.mob_safe_buffs_var.get())
        status = "enabled" if config.mob_filter_safe_buffs else "disabled"
        print(f"Mob filter safe buffs {status}")

    def _refresh_quick_start(self):
        """Update the Quick Start readiness checklist (Connect / Regions / Start)."""
        if not hasattr(self, 'qs_dots'):
            return
        connected = config.connected_window is not None
        regions = config.bot_regions_ready()
        status = {'connect': connected, 'regions': regions, 'start': connected and regions}
        for key, ok in status.items():
            dot = self.qs_dots.get(key)
            if dot is not None:
                dot.configure(image=ui_icons.get_icon(
                    'check' if ok else 'dot', size=13,
                    color='#16a34a' if ok else '#6b7280',
                ))
            txt = self.qs_texts.get(key)
            if txt is not None:
                txt.configure(text_color=("#15803d", "#4ade80") if ok else ("gray30", "gray75"))

    def apply_quick_preset(self, kind):
        """One-click config presets for beginners (Melee / Caster / Support)."""
        try:
            # Assist mode gates auto-attack/mob/unstuck, so clear it first for combat presets.
            if kind != 'support' and self.assist_only_var.get():
                self.assist_only_var.set(False)
                self.update_assist_only()

            # Survival defaults shared by every preset.
            for var_name, handler in (
                ('auto_hp_var', self.update_auto_hp),
                ('auto_mp_var', self.update_auto_mp),
                ('auto_repair_var', self.update_auto_repair),
            ):
                getattr(self, var_name).set(True)
                handler()

            if kind in ('melee', 'caster'):
                self.action_vars['pick'].set(True)
                self.update_action_slot('pick')
                self.auto_change_target_var.set(True)
                self.update_auto_change_target()
                self.auto_attack_var.set(True)
                self.update_auto_attack()
                self.is_mage_var.set(kind == 'caster')
                self.update_is_mage()
            elif kind == 'support':
                self.is_mage_var.set(False)
                self.update_is_mage()
                self.assist_only_var.set(True)
                self.update_assist_only()

            self._refresh_quick_start()
            print(f"[Preset] Applied '{kind}' preset")
        except Exception as e:
            print(f"[Preset] Failed to apply '{kind}': {e}")

    def update_mob_detection(self):
        """Update mob filter enabled status"""
        config.mob_detection_enabled = self.mob_detection_var.get()
        status = "enabled" if config.mob_detection_enabled else "disabled"
        print(f"Mob filter {status}")
        if config.mob_detection_enabled and not mob_filter.is_active():
            print("Note: Select scan region and learn at least one template for filtering to take effect")
    
    def update_auto_attack(self):
        """Update auto attack enabled status"""

        config.auto_attack_enabled = self.auto_attack_var.get()
        status = "enabled" if config.auto_attack_enabled else "disabled"
        print(f"Auto Attack {status}")
    
    def reset_auto_repair_count(self):
        """Reset break warning counter to 0."""
        import auto_repair
        auto_repair.reset_repair_count()
        print("Auto Repair count reset")

    def update_auto_repair(self):
        """Update auto repair enabled status"""
        enabled = self.auto_repair_var.get()
        if not enabled and config.auto_repair_enabled:
            import auto_repair
            auto_repair.reset_repair_count()
        config.auto_repair_enabled = enabled
        status = "enabled" if config.auto_repair_enabled else "disabled"
        print(f"Auto Repair {status}")
        self._update_auto_repair_count_display()
    
    def update_is_mage(self):
        """Update mage setting"""
        config.is_mage = self.is_mage_var.get()
        status = "enabled" if config.is_mage else "disabled"
        print(f"Mage? {status}")
    
    def _set_assist_only_dependent_widgets_state(self, state):
        """Enable or disable widgets that depend on assist_only mode"""
        if hasattr(self, 'auto_attack_checkbox'):
            self.auto_attack_checkbox.configure(state=state)
        if hasattr(self, 'auto_change_target_checkbox'):
            self.auto_change_target_checkbox.configure(state=state)
        self.update_mob_filter_ui_state()
    
    def update_assist_only(self):
        """Update assist only setting"""
        import frame_cache
        frame_cache.invalidate()
        config.assist_only_enabled = self.assist_only_var.get()
        status = "enabled" if config.assist_only_enabled else "disabled"
        print(f"Assist Only {status}")
        
        if config.assist_only_enabled:
            # Store previous state before disabling
            if config._assist_only_previous_auto_attack is None:
                config._assist_only_previous_auto_attack = config.auto_attack_enabled
            if config._assist_only_previous_mob_detection is None:
                config._assist_only_previous_mob_detection = config.mob_detection_enabled
            if config._assist_only_previous_auto_change_target is None:
                config._assist_only_previous_auto_change_target = config.auto_change_target_enabled
            
            # Disable auto attack, mob filter, and auto unstuck
            config.auto_attack_enabled = False
            config.mob_detection_enabled = False
            config.auto_change_target_enabled = False
            
            # Update GUI checkboxes
            if hasattr(self, 'auto_attack_var'):
                self.auto_attack_var.set(False)
            if hasattr(self, 'mob_detection_var'):
                self.mob_detection_var.set(False)
            if hasattr(self, 'auto_change_target_var'):
                self.auto_change_target_var.set(False)
            
            # Disable checkboxes in GUI
            self._set_assist_only_dependent_widgets_state('disabled')
            
            print("[Assist Only] Auto Attack, Mob Filter, and Auto Unstuck disabled")
        else:
            # Restore previous state
            if config._assist_only_previous_auto_attack is not None:
                config.auto_attack_enabled = config._assist_only_previous_auto_attack
                config._assist_only_previous_auto_attack = None
            if config._assist_only_previous_mob_detection is not None:
                config.mob_detection_enabled = config._assist_only_previous_mob_detection
                config._assist_only_previous_mob_detection = None
            if config._assist_only_previous_auto_change_target is not None:
                config.auto_change_target_enabled = config._assist_only_previous_auto_change_target
                config._assist_only_previous_auto_change_target = None
            
            # Update GUI checkboxes to restored state
            if hasattr(self, 'auto_attack_var'):
                self.auto_attack_var.set(config.auto_attack_enabled)
            if hasattr(self, 'mob_detection_var'):
                self.mob_detection_var.set(config.mob_detection_enabled)
            if hasattr(self, 'auto_change_target_var'):
                self.auto_change_target_var.set(config.auto_change_target_enabled)
            
            # Re-enable checkboxes in GUI
            self._set_assist_only_dependent_widgets_state('normal')
            
            # Reset enemy tracking when assist_only is disabled
            config.enemy_initial_hp = None
            config.enemy_detected = False
            
            print("[Assist Only] Auto Attack, Mob Filter, and Auto Unstuck restored to previous state")
    
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

    def update_auto_rotate(self):
        """Update Auto Rotate Camera enabled status"""
        config.auto_rotate_enabled = self.auto_rotate_var.get()
        status = "enabled" if config.auto_rotate_enabled else "disabled"
        print(f"Auto Rotate Camera {status}")

    def update_auto_rotate_timing(self):
        """Update the interval (seconds) between camera rotations"""
        try:
            interval = float(self.auto_rotate_interval_var.get())
            if interval > 0:
                config.auto_rotate_interval = interval
                print(f"Auto Rotate interval updated to {config.auto_rotate_interval} seconds")
            else:
                self.auto_rotate_interval_var.set(str(config.auto_rotate_interval))
        except ValueError:
            self.auto_rotate_interval_var.set(str(config.auto_rotate_interval))

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
    
    def update_mp_threshold(self):
        """Update MP threshold value"""
        try:
            threshold = float(self.mp_threshold_var.get())
            if 0 <= threshold <= 100:
                config.mp_threshold = threshold
                print(f"MP threshold updated to {config.mp_threshold}%")
            else:
                print(f"Invalid MP threshold: must be between 0 and 100")
                self.mp_threshold_var.set(str(config.mp_threshold))
        except ValueError:
            print(f"Invalid MP threshold value")
            self.mp_threshold_var.set(str(config.mp_threshold))
    
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
        """Update the Start/Stop button state based on regions and connection."""
        is_ready = config.bot_regions_ready()

        def cfg_min(btn, **kwargs):
            if not btn:
                return
            try:
                btn.configure(**kwargs)
            except tk.TclError:
                pass

        minib = getattr(self, "minimized_toggle_bot_button", None)
        
        if config.connected_window and is_ready and not config.bot_running:
            self.toggle_bot_button.configure(
                state="normal", text="Start", fg_color="green", hover_color="darkgreen", command=self.toggle_bot
            )
            cfg_min(minib, state="normal", text="", image=ui_icons.get_icon("play", size=16), fg_color="#16a34a", hover_color="#15803d", command=self.toggle_bot)
        elif config.bot_running:
            # Keep button enabled when running so user can stop
            self.toggle_bot_button.configure(
                state="normal", text="Stop", fg_color="red", hover_color="darkred", command=self.toggle_bot
            )
            cfg_min(minib, state="normal", text="", image=ui_icons.get_icon("stop", size=15), fg_color="#dc2626", hover_color="#b91c1c", command=self.toggle_bot)
        else:
            self.toggle_bot_button.configure(state="disabled")
            cfg_min(minib, state="disabled", text="", image=ui_icons.get_icon("play", size=16), fg_color="#16a34a", hover_color="#15803d", command=self.toggle_bot)
        self.update_mob_filter_ui_state()
    



    
















    
    def _bot_thread_died(self):
        """True when the bot is meant to be running but its thread is gone.

        bot_loop guards each tick, so this only fires if it died outside that
        guard. Without the check the GUI would keep reporting "Running" over a
        thread that stopped doing anything.
        """
        thread = getattr(config, 'bot_thread', None)
        return bool(config.bot_running and thread is not None and not thread.is_alive())

    def _handle_bot_thread_death(self):
        """Put the UI back in a truthful state after the bot thread died."""
        logger.error("Bot thread stopped unexpectedly; marking the bot as stopped", "Bot")
        config.bot_running = False
        self._bot_run_start_time = None
        self.update_toggle_bot_button_state()
        self.status_label.configure(text="Stopped (error)", text_color="red")
        messagebox.showerror(
            "Bot Stopped",
            "The bot stopped unexpectedly.\n\n"
            "Check the console or log for the error, then start it again.",
        )

    def update_status(self):
        """Update HP/MP/Enemy HP status display (reads from config, updated by bot_logic/auto_attack)"""
        if self._bot_thread_died():
            self._handle_bot_thread_death()
            return

        if config.bot_running:
            # Read HP/MP percentages from config (calculated by bot_logic in separate thread)
            hp_percent = config.current_hp_percentage
            mp_percent = config.current_mp_percentage
            
            # Update GUI progress bars and labels (maximized view)
            self.hp_progress_bar.set(hp_percent / 100.0)
            self.hp_percent_label.configure(text=f"{int(hp_percent)}%")
            self.mp_progress_bar.set(mp_percent / 100.0)
            self.mp_percent_label.configure(text=f"{int(mp_percent)}%")
            self._update_bars_status_label()
            
            # Read enemy HP percentage from config (updated by auto_attack in separate thread)
            # Reset enemy HP bar when auto attack is disabled
            if not config.auto_attack_enabled:
                enemy_hp_percent = 0.0
                enemy_name = None
            else:
                enemy_hp_percent = config.current_enemy_hp_percentage
                enemy_name = config.current_enemy_name
            
            if hasattr(self, 'enemy_hp_progress_bar'):
                self.enemy_hp_progress_bar.set(enemy_hp_percent / 100.0)
            if hasattr(self, 'enemy_hp_percent_label'):
                self.enemy_hp_percent_label.configure(text=f"{int(enemy_hp_percent)}%" if enemy_hp_percent > 0 else "---%")
            
            if hasattr(self, 'current_mob_label'):
                display_name = enemy_name
                if mob_filter.is_active() and config.current_mob_match:
                    display_name = config.current_mob_match.get('name', enemy_name)
                if display_name:
                    if mob_filter.is_active() and not auto_attack.should_target_current_mob():
                        self.current_mob_label.configure(text=display_name, text_color="orange")
                    else:
                        self.current_mob_label.configure(text=display_name, text_color="green")
                else:
                    self.current_mob_label.configure(text="None", text_color="red")
            
            # Update unstuck countdown when enemy HP is displayed
            if hasattr(self, 'unstuck_countdown_label'):
                import auto_unstuck
                auto_unstuck.update_unstuck_countdown_display(time.time())

            self._update_auto_repair_count_display()
            # The Mini Overlay pill refreshes itself via _refresh_overlay().

        if config.bot_running:
            self.root.after(config.get_gui_status_interval_ms(), self.update_status)
    
    def process_gui_updates(self):
        """Process queued GUI updates from background threads (thread-safe)"""
        try:
            # Process up to 100 updates per cycle to prevent blocking
            for _ in range(100):
                update_func = config.gui_update_queue.get_nowait()
                update_func()  # Execute the queued GUI update
        except queue.Empty:
            pass  # No more updates to process

        try:
            self._refresh_quick_start()
        except Exception:
            pass

        self.root.after(config.get_gui_updates_interval_ms(), self.process_gui_updates)
    
    
    # ------------------------------------------------------------------
    # Mini Overlay Mode — compact, frameless, always-on-top control pill.
    # Replaces the old minimized panel: a slim floating bar (like a screen
    # recorder widget) with a live status dot, runtime timer, Start/Stop,
    # and an expand-to-restore button.
    # ------------------------------------------------------------------
    OVERLAY_BG = "#15181e"
    OVERLAY_BORDER = "#333947"
    # Colour keyed out to transparency so only the rounded pill shows (no square
    # corners around it). Must not appear elsewhere in the overlay.
    OVERLAY_TRANSPARENT_KEY = "#010203"
    OVERLAY_TICK_MS = 500







    def run(self):
        # Update license status info
        self.update_license_status_info()
        
        # Periodically update license status info (every 60 seconds) in background thread
        def update_license_periodically():
            """Update license status in background thread to avoid blocking UI"""
            def check_license_thread():
                """Background thread to check license"""
                license_manager = get_license_manager()
                license_info = license_manager.get_license_info()
                
                # Update GUI in main thread
                def update_gui():
                    self.refresh_license_status_display()
                
                # Schedule GUI update in main thread
                self.root.after(0, update_gui)
            
            # Start background thread for license check
            threading.Thread(target=check_license_thread, daemon=True).start()
            
            # Schedule next check
            self.root.after(60000, update_license_periodically)  # Update every 60 seconds
        
        self.root.after(60000, update_license_periodically)
        
        # Start processing GUI updates from background threads
        self.process_gui_updates()
        self.root.after(0, self._refresh_mob_list)
        self.root.protocol('WM_DELETE_WINDOW', self._on_app_close)
        self.root.mainloop()

    def _on_app_close(self):
        self.root.destroy()
