"""License activation dialogs and status display.

Moved out of gui.py unchanged. Mixed into BotGUI, so these methods keep
using self exactly as before -- no call sites changed.
"""
import customtkinter as ctk
from license_manager import get_license_manager
from ui.widgets import format_license_date, license_days_left
from tkinter import messagebox


class LicensePanelMixin:
    """License activation dialogs and status display."""

    def _on_license_activated(self, license_dialog):
        """Called when license is successfully activated"""
        license_dialog.destroy()
        # Show main window if it was hidden
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _build_machine_id_section(self, parent, dialog, get_status_label):
        """The "Your Machine ID" panel, shared by both licence dialogs.

        `get_status_label` is a callable rather than the widget itself: both
        dialogs build their status label after this section, so it does not
        exist yet at call time. It is only needed when Copy is clicked.
        """
        machine_id_frame = ctk.CTkFrame(parent, corner_radius=8)
        machine_id_frame.pack(fill="x", padx=20, pady=(0, 10))
        machine_id_frame.columnconfigure(0, weight=1)

        machine_id_label = ctk.CTkLabel(
            machine_id_frame,
            text="Your Machine ID:",
            font=ctk.CTkFont(size=11, weight="bold")
        )
        machine_id_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))

        license_manager = get_license_manager()
        machine_id = license_manager.get_machine_id()

        machine_id_value_frame = ctk.CTkFrame(machine_id_frame, fg_color="transparent")
        machine_id_value_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        machine_id_value_frame.columnconfigure(0, weight=1)

        machine_id_entry = ctk.CTkEntry(
            machine_id_value_frame,
            width=400,
            height=30,
            font=ctk.CTkFont(size=10, family="Courier"),
            state="readonly"
        )
        machine_id_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        # Need to temporarily change state to insert text in readonly entry
        machine_id_entry.configure(state="normal")
        machine_id_entry.insert(0, machine_id)
        machine_id_entry.configure(state="readonly")

        def copy_machine_id():
            """Copy machine ID to clipboard"""
            dialog.clipboard_clear()
            dialog.clipboard_append(machine_id)
            dialog.update()
            status_label = get_status_label()
            status_label.configure(text="Machine ID copied to clipboard!", text_color="green")
            dialog.after(2000, lambda: status_label.configure(text=""))

        copy_machine_id_btn = ctk.CTkButton(
            machine_id_value_frame,
            text="Copy",
            command=copy_machine_id,
            width=80,
            height=30,
            font=ctk.CTkFont(size=10)
        )
        copy_machine_id_btn.grid(row=0, column=1)

        machine_id_help = ctk.CTkLabel(
            machine_id_frame,
            text="If you need a machine-bound license, provide this Machine ID to the license issuer.",
            font=ctk.CTkFont(size=9),
            text_color="gray",
            wraplength=540
        )
        machine_id_help.grid(row=2, column=0, sticky="w", padx=10, pady=(0, 10))

    def show_license_dialog_blocking(self):
        """Show license entry dialog that blocks until valid license is entered"""
        license_dialog = ctk.CTkToplevel(self.root)
        license_dialog.title("License Activation Required")
        license_dialog.geometry("600x530")
        license_dialog.resizable(False, False)
        license_dialog.transient(self.root)
        license_dialog.grab_set()  # Make dialog modal
        
        # Make it a top-level window (not dependent on hidden root)
        license_dialog.attributes('-topmost', True)
        
        # Center the dialog
        license_dialog.update_idletasks()
        x = (license_dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (license_dialog.winfo_screenheight() // 2) - (530 // 2)
        license_dialog.geometry(f"600x530+{x}+{y}")
        
        # Prevent closing without valid license
        def on_closing():
            """Exit app if user tries to close without license"""
            self.root.quit()
            self.root.destroy()
        
        license_dialog.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Main frame
        main_frame = ctk.CTkFrame(license_dialog, corner_radius=10)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="License Activation Required",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=(20, 10))
        
        # Instructions
        instructions = ctk.CTkLabel(
            main_frame,
            text="Please enter your license key to continue using Kathana Helper.",
            font=ctk.CTkFont(size=12),
            wraplength=550
        )
        instructions.pack(pady=(0, 10))
        
        # Also used further down, by the activation handler.
        license_manager = get_license_manager()

        # Machine ID section (for machine-bound licenses)
        self._build_machine_id_section(
            main_frame, license_dialog, lambda: status_label)

        # License key entry
        license_label = ctk.CTkLabel(
            main_frame,
            text="License Key:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        license_label.pack(anchor="w", padx=20, pady=(10, 5))
        
        license_entry = ctk.CTkTextbox(
            main_frame,
            width=540,
            height=100,
            font=ctk.CTkFont(size=11),
            wrap="word"
        )
        license_entry.pack(padx=20, pady=(0, 10))
        license_entry.focus()
        
        # Status label
        status_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=11),
            wraplength=540
        )
        status_label.pack(pady=(0, 10))
        
        # License info display (if license exists but is invalid)
        license_info = license_manager.get_license_info()
        
        if license_info:
            info_text = f"Current License: {license_info['data'].get('user_name', 'Unknown')}\n"
            if 'expires' in license_info['data']:
                from datetime import datetime
                expires = datetime.fromisoformat(license_info['data']['expires'])
                info_text += f"{expires.strftime('%Y-%m-%d')}"
            info_label = ctk.CTkLabel(
                main_frame,
                text=info_text,
                font=ctk.CTkFont(size=10),
                text_color="gray"
            )
            info_label.pack(pady=(0, 10))
        
        def validate_and_save():
            """Validate and save the license key"""
            license_key = license_entry.get("1.0", "end-1c").strip()
            
            if not license_key:
                status_label.configure(text="Please enter a license key.", text_color="red")
                return
            
            # Validate license
            is_valid, message, license_data = license_manager.validate_license(license_key)
            
            if is_valid:
                # Save license
                success, save_message = license_manager.save_license(license_key)
                if success:
                    status_label.configure(text="License activated successfully! Closing...", text_color="green")
                    
                    # Update license status info immediately
                    self.update_license_status_info()
                    
                    # Give user a moment to see the success message, then close dialog
                    license_dialog.after(1000, lambda: self._on_license_activated_blocking(license_dialog))
                else:
                    status_label.configure(text=f"Error saving license: {save_message}", text_color="red")
            else:
                status_label.configure(text=message, text_color="red")
        
        # Buttons frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=20)
        
        # Activate button
        activate_button = ctk.CTkButton(
            button_frame,
            text="Activate License",
            command=validate_and_save,
            width=150,
            height=35,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        activate_button.pack(side="left", padx=10)
        
        # Cancel/Exit button
        def exit_app():
            """Exit the application"""
            self.root.quit()
            self.root.destroy()
        
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Exit",
            command=exit_app,
            width=150,
            height=35,
            font=ctk.CTkFont(size=12),
            fg_color="gray",
            hover_color="darkgray"
        )
        cancel_button.pack(side="left", padx=10)
        
        # Bind Ctrl+Enter to activate (since it's a text area now)
        license_entry.bind("<Control-Return>", lambda e: validate_and_save())
        
        # Make dialog close on Escape
        license_dialog.bind("<Escape>", lambda e: exit_app())
        
        # Wait for dialog to close
        license_dialog.wait_window()

    def _on_license_activated_blocking(self, license_dialog):
        """Called when license is successfully activated from blocking dialog"""
        # Close the dialog - this will cause wait_window() to return
        license_dialog.destroy()
        # Ensure the dialog is fully closed
        license_dialog.update()

    def show_license_dialog(self):
        """Show license entry dialog (non-blocking, for Settings tab)"""
        license_dialog = ctk.CTkToplevel(self.root)
        license_dialog.title("License Activation")
        license_dialog.geometry("600x500")
        license_dialog.resizable(False, False)
        license_dialog.transient(self.root)
        license_dialog.grab_set()  # Make dialog modal
        
        # Center the dialog
        license_dialog.update_idletasks()
        x = (license_dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (license_dialog.winfo_screenheight() // 2) - (500 // 2)
        license_dialog.geometry(f"600x500+{x}+{y}")
        
        # Main frame
        main_frame = ctk.CTkFrame(license_dialog, corner_radius=10)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="License Activation",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=(20, 10))
        
        # Instructions
        instructions = ctk.CTkLabel(
            main_frame,
            text="Please enter your license key to activate Kathana Helper.",
            font=ctk.CTkFont(size=12),
            wraplength=550
        )
        instructions.pack(pady=(0, 10))
        
        # Also used further down, by the activation handler.
        license_manager = get_license_manager()

        # Machine ID section (for machine-bound licenses)
        self._build_machine_id_section(
            main_frame, license_dialog, lambda: status_label)

        # License key entry (text area)
        license_label = ctk.CTkLabel(
            main_frame,
            text="License Key:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        license_label.pack(anchor="w", padx=20, pady=(10, 5))
        
        license_entry = ctk.CTkTextbox(
            main_frame,
            width=540,
            height=100,
            font=ctk.CTkFont(size=11),
            wrap="word"
        )
        license_entry.pack(padx=20, pady=(0, 10))
        license_entry.focus()
        
        # Status label
        status_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=11),
            wraplength=540
        )
        status_label.pack(pady=(0, 10))
        
        # License info display (if license exists but is invalid)
        license_info = license_manager.get_license_info()
        
        if license_info:
            info_text = f"Current License: {license_info['data'].get('user_name', 'Unknown')}\n"
            if 'expires' in license_info['data']:
                from datetime import datetime
                expires = datetime.fromisoformat(license_info['data']['expires'])
                info_text += f"{expires.strftime('%Y-%m-%d')}"
            info_label = ctk.CTkLabel(
                main_frame,
                text=info_text,
                font=ctk.CTkFont(size=10),
                text_color="gray"
            )
            info_label.pack(pady=(0, 10))
        
        def validate_and_save():
            """Validate and save the license key"""
            license_key = license_entry.get("1.0", "end-1c").strip()
            
            if not license_key:
                status_label.configure(text="Please enter a license key.", text_color="red")
                return
            
            # Validate license
            is_valid, message, license_data = license_manager.validate_license(license_key)
            
            if is_valid:
                # Save license
                success, save_message = license_manager.save_license(license_key)
                if success:
                    status_label.configure(text="License activated successfully!", text_color="green")
                    
                    # Close dialog and refresh license status
                    self.update_license_status_info()  # Update status tab immediately
                    license_dialog.after(1000, lambda: [license_dialog.destroy(), self.refresh_license_status()])
                else:
                    status_label.configure(text=f"Error saving license: {save_message}", text_color="red")
            else:
                status_label.configure(text=message, text_color="red")
        
        # Buttons frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=20)
        
        # Activate button
        activate_button = ctk.CTkButton(
            button_frame,
            text="Activate License",
            command=validate_and_save,
            width=150,
            height=35,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        activate_button.pack(side="left", padx=10)
        
        # Cancel button (just close dialog, don't exit app)
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=license_dialog.destroy,
            width=150,
            height=35,
            font=ctk.CTkFont(size=12),
            fg_color="gray",
            hover_color="darkgray"
        )
        cancel_button.pack(side="left", padx=10)
        
        # Bind Ctrl+Enter to activate (since it's a text area now)
        license_entry.bind("<Control-Return>", lambda e: validate_and_save())
        
        # Make dialog close on Escape
        license_dialog.bind("<Escape>", lambda e: license_dialog.destroy())

    def update_license_status_info(self):
        """Update license status info in Status tab (now uses refresh_license_status_display)"""
        self.refresh_license_status_display()

    def refresh_license_status(self):
        """Refresh license status display (shows a messagebox; updates Status tab UI)"""
        if not hasattr(self, 'license_expiry_label'):
            return  # GUI elements not created yet
        
        license_manager = get_license_manager()
        license_info = license_manager.get_license_info()
        
        # Build info text for messagebox
        if license_info and license_info.get('valid'):
            user_name = license_info['data'].get('user_name', 'Unknown')
            expires = license_info['data'].get('expires', 'Never')
            issued = license_info['data'].get('issued', 'Unknown')
            machine_bound = license_info['data'].get('machine_bound', False)
            
            if expires != 'Never':
                try:
                    expires_str = format_license_date(expires)
                    days_left = license_days_left(expires)
                    if days_left < 0:
                        expiry_info = f"{expires_str}"
                    elif days_left <= 7:
                        expiry_info = f"{expires_str} ({days_left} day{'s' if days_left != 1 else ''} left)"
                    else:
                        expiry_info = f"{expires_str}"
                except:
                    expiry_info = f"{expires}"
            else:
                expiry_info = "No expiration"
            
            if issued != 'Unknown':
                issued_str = format_license_date(issued)
            else:
                issued_str = "Unknown"
            
            info_text = f"User: {user_name}\n"
            info_text += f"Issued: {issued_str}\n"
            info_text += f"{expiry_info}"
            if machine_bound:
                info_text += "\nMachine Bound: Yes"
        else:
            info_text = "No valid license found. Please activate a license."
        
        # Update all license displays
        self.update_license_status_info()  # Update status tab
        self.refresh_license_status_display()  # Update settings tab
        
        messagebox.showinfo("License Status", info_text)

    def refresh_license_status_display(self):
        """Refresh license status display in Settings tab"""
        # Status-tab "License Info" widgets may not exist yet during startup
        if not hasattr(self, 'license_expiry_label'):
            return  # GUI elements not created yet
        
        license_manager = get_license_manager()
        license_info = license_manager.get_license_info()
        
        if license_info and license_info.get('valid'):
            status_color = "green"
            user_name = license_info['data'].get('user_name', 'Unknown')
            expires = license_info['data'].get('expires', 'Never')
            issued = license_info['data'].get('issued', 'Unknown')
            machine_bound = license_info['data'].get('machine_bound', False)
            
            if expires != 'Never':
                try:
                    expires_str = format_license_date(expires)
                    days_left = license_days_left(expires)
                    if days_left < 0:
                        status_color = "red"
                        expiry_info = f"{expires_str}"
                    elif days_left <= 7:
                        status_color = "orange"
                        expiry_info = f"{expires_str} ({days_left} day{'s' if days_left != 1 else ''} left)"
                    elif days_left <= 30:
                        status_color = "yellow"
                        expiry_info = f"{expires_str} ({days_left} days left)"
                    else:
                        expiry_info = f"{expires_str}"
                except:
                    expiry_info = f"{expires}"
            else:
                expiry_info = "No expiration"
            
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

        # Update status-tab "License Info" values
        if hasattr(self, 'license_user_value'):
            self.license_user_value.configure(text=user_name, text_color="white" if license_info and license_info.get('valid') else "gray")
        if hasattr(self, 'license_expiry_label'):
            self.license_expiry_label.configure(text=expiry_info, text_color=status_color if license_info and license_info.get('valid') else "gray")
        if hasattr(self, 'license_issued_value'):
            self.license_issued_value.configure(text=issued_str, text_color="gray")
        if hasattr(self, 'license_binding_value'):
            binding_text = "Machine Bound" if machine_bound else "—"
            binding_color = "orange" if machine_bound else "gray"
            self.license_binding_value.configure(text=binding_text, text_color=binding_color)
