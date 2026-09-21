"""Debug message window and debug-mode toggle.

Moved out of gui.py unchanged. Mixed into BotGUI, so these methods keep
using self exactly as before -- no call sites changed.
"""
import customtkinter as ctk
import debug_utils
import time
import tkinter as tk


class DebugWindowMixin:
    """Debug message window and debug-mode toggle."""

    def toggle_debug_mode(self):
        """Toggle global debug mode on/off (internal; no UI button)."""
        current_state = debug_utils.get_debug_enabled()
        new_state = debug_utils.set_debug_enabled(not current_state, callback=self.add_debug_message)
        if hasattr(self, 'debug_var'):
            self.debug_var.set(new_state)
        if new_state:
            if hasattr(self, 'debug_button'):
                self.debug_button.configure(text="Debug Mode: ON", fg_color=("green", "darkgreen"))
            self.show_debug_window()
            debug_utils.debug_print("Debug mode ENABLED - all debug messages will be shown here", "DebugSystem")
        else:
            if hasattr(self, 'debug_button'):
                self.debug_button.configure(text="Debug Mode: OFF", fg_color=("gray70", "gray30"))
            if hasattr(self, 'debug_window') and self.debug_window:
                try:
                    self.debug_window.destroy()
                except:
                    pass
                self.debug_window = None

    def show_debug_window(self):
        """Show or create the debug window"""
        # Check if window exists and is valid
        window_exists = False
        if hasattr(self, 'debug_window') and self.debug_window is not None:
            try:
                self.debug_window.winfo_exists()
                window_exists = True
            except:
                window_exists = False
        
        if not window_exists:
            self.debug_window = ctk.CTkToplevel(self.root)
            self.debug_window.title("Debug Window - All Module Messages")
            self.debug_window.geometry("800x500")
            self.debug_window.resizable(True, True)
            
            # Create scrollable text frame
            debug_frame = ctk.CTkFrame(self.debug_window)
            debug_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Text widget for messages (using tkinter Text for better performance)
            text_frame = tk.Frame(debug_frame, bg=ctk.ThemeManager.theme["CTkFrame"]["fg_color"][1])
            text_frame.pack(fill="both", expand=True)
            
            scrollbar = tk.Scrollbar(text_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            self.debug_text = tk.Text(
                text_frame,
                wrap=tk.WORD,
                yscrollcommand=scrollbar.set,
                bg=ctk.ThemeManager.theme["CTkFrame"]["fg_color"][1],
                fg=ctk.ThemeManager.theme["CTkLabel"]["text_color"][1],
                font=("Consolas", 10),
                padx=10,
                pady=10
            )
            self.debug_text.pack(side=tk.LEFT, fill="both", expand=True)
            scrollbar.config(command=self.debug_text.yview)
            
            # Clear button
            button_frame = ctk.CTkFrame(debug_frame)
            button_frame.pack(fill="x", pady=(10, 0))
            
            clear_button = ctk.CTkButton(
                button_frame,
                text="Clear",
                command=self.clear_debug_messages,
                width=100,
                height=28
            )
            clear_button.pack(side=tk.LEFT, padx=(0, 10))
            
            close_button = ctk.CTkButton(
                button_frame,
                text="Close",
                command=self.close_debug_window,
                width=100,
                height=28
            )
            close_button.pack(side=tk.LEFT)
            
            # Handle window close
            self.debug_window.protocol("WM_DELETE_WINDOW", self.close_debug_window)
        else:
            # Bring existing window to front
            self.debug_window.lift()
            self.debug_window.focus()

    def add_debug_message(self, message):
        """Add a debug message to the debug window (thread-safe)"""
        # Schedule update in main thread to avoid threading issues
        if hasattr(self, 'root') and self.root:
            self.root.after(0, lambda: self._add_debug_message_sync(message))
        else:
            # Fallback if root doesn't exist
            print(f"[Click Debug] {message}")

    def _add_debug_message_sync(self, message):
        """Internal method to add debug message (must be called from main thread)"""
        if hasattr(self, 'debug_text') and self.debug_text:
            try:
                timestamp = time.strftime("%H:%M:%S")
                formatted_message = f"[{timestamp}] {message}\n"
                self.debug_text.insert(tk.END, formatted_message)
                self.debug_text.see(tk.END)  # Auto-scroll to bottom
                # Limit to last 1000 lines to prevent memory issues
                lines = self.debug_text.get("1.0", tk.END).split('\n')
                if len(lines) > 1000:
                    self.debug_text.delete("1.0", f"{len(lines) - 1000}.0")
            except Exception as e:
                # Fallback to print if text widget fails
                print(f"[Click Debug] {message}")

    def clear_debug_messages(self):
        """Clear all debug messages from the window"""
        if hasattr(self, 'debug_text') and self.debug_text:
            self.debug_text.delete("1.0", tk.END)

    def close_debug_window(self):
        """Close the debug window and disable debug mode"""
        if hasattr(self, 'debug_window') and self.debug_window:
            try:
                self.debug_window.destroy()
            except:
                pass
            self.debug_window = None
        # Disable debug mode
        debug_utils.set_debug_enabled(False, callback=None)
        if hasattr(self, 'debug_var'):
            self.debug_var.set(False)
        if hasattr(self, 'debug_button'):
            self.debug_button.configure(text="Debug Mode: OFF", fg_color=("gray70", "gray30"))
