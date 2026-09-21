"""Drag-to-select screen region pickers for each calibrated area.

Moved out of gui.py unchanged. Mixed into BotGUI, so these methods keep
using self exactly as before -- no call sites changed.
"""
from PIL import Image
from PIL import ImageTk
import config
from tkinter import messagebox
import os
import tkinter as tk
import ui_fonts
import win32gui


class RegionPickerMixin:
    """Drag-to-select screen region pickers for each calibrated area."""

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
                                       font=(ui_fonts.APP_FONT_FAMILY, 16), 
                                       fg="white", 
                                       bg="black")
            instruction_label.place(relx=0.5, rely=0.1, anchor="center")
            
            # Label to show current position
            info_label = tk.Label(picker_window, 
                                text="", 
                                font=(ui_fonts.APP_FONT_FAMILY, 12), 
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

    def _pick_region(self, what, title, hint_color, outline, commit):
        """Drag a rectangle over the game window, then hand it to `commit`.

        Shared by every region picker. The caller supplies only what differs:
        the wording, the two colours, and what to do with the result.

        commit(rel_x, rel_y, width, height) stores the region and returns the
        summary shown in the confirmation dialog. Coordinates are relative to
        the game window, not the screen.
        """
        try:
            if not config.connected_window:
                messagebox.showwarning("No Window", "Please connect to a game window first!")
                return

            hwnd = config.connected_window.handle
            self.root.withdraw()
            print(f"Drag to select {what} detection area. Press ESC to cancel.")

            picker_window = tk.Toplevel()
            picker_window.attributes('-fullscreen', True)
            picker_window.attributes('-alpha', 0.5)  # Semi-transparent
            picker_window.configure(bg='black')
            picker_window.attributes('-topmost', True)

            canvas = tk.Canvas(picker_window, bg='black', highlightthickness=0, bd=0)
            canvas.pack(fill='both', expand=True)

            instruction_label = tk.Label(
                picker_window,
                text=f"Click and drag to select {what} area\n"
                     f"Release to confirm, Press ESC to cancel",
                font=(ui_fonts.APP_FONT_FAMILY, 16), fg="white", bg="black",
            )
            instruction_label.place(relx=0.5, rely=0.1, anchor="center")

            info_label = tk.Label(
                picker_window, text="",
                font=(ui_fonts.APP_FONT_FAMILY, 12), fg=hint_color, bg="black",
            )
            info_label.place(relx=0.5, rely=0.15, anchor="center")

            rect_id = None
            start_x = None
            start_y = None
            dragging = False

            def drag_bounds(end_x, end_y):
                """Screen bounds plus window-relative origin and size for a drag."""
                rect = win32gui.GetWindowRect(hwnd)
                min_x, max_x = min(start_x, end_x), max(start_x, end_x)
                min_y, max_y = min(start_y, end_y), max(start_y, end_y)
                return (min_x, min_y, max_x, max_y,
                        min_x - rect[0], min_y - rect[1],
                        max_x - min_x, max_y - min_y)

            def on_button_press(event):
                nonlocal start_x, start_y, dragging, rect_id
                start_x = event.x_root
                start_y = event.y_root
                dragging = True
                if rect_id:
                    canvas.delete(rect_id)
                    rect_id = None

            def on_motion(event):
                nonlocal rect_id
                if not dragging or start_x is None or start_y is None:
                    return
                try:
                    (min_x, min_y, max_x, max_y,
                     rel_x, rel_y, width, height) = drag_bounds(event.x_root, event.y_root)
                    info_label.configure(
                        text=f"Position: ({rel_x}, {rel_y}) | Size: {width}x{height} pixels")
                    if rect_id:
                        canvas.delete(rect_id)
                    rect_id = canvas.create_rectangle(
                        min_x, min_y, max_x, max_y, outline=outline, width=2)
                except Exception:
                    pass

            def on_button_release(event):
                nonlocal start_x, start_y, dragging
                if not dragging or start_x is None or start_y is None:
                    return
                try:
                    (_, _, _, _,
                     rel_x, rel_y, width, height) = drag_bounds(event.x_root, event.y_root)

                    # A stray click should not set a zero-sized region.
                    width = max(width, 10)
                    height = max(height, 5)

                    summary = commit(rel_x, rel_y, width, height)

                    picker_window.destroy()
                    self.root.deiconify()

                    print(f"{title} set to: ({rel_x}, {rel_y}, {width}x{height})")
                    messagebox.showinfo(title, summary)
                    self.update_toggle_bot_button_state()
                except Exception as e:
                    print(f"Error in {what} selection: {e}")
                    picker_window.destroy()
                    self.root.deiconify()

                dragging = False
                start_x = None
                start_y = None

            def on_escape(_event):
                picker_window.destroy()
                self.root.deiconify()
                print(f"{what} selection cancelled")

            picker_window.bind('<Button-1>', on_button_press)
            picker_window.bind('<B1-Motion>', on_motion)
            picker_window.bind('<ButtonRelease-1>', on_button_release)
            picker_window.bind('<Escape>', on_escape)
            picker_window.focus_set()

        except Exception as e:
            print(f"Error in {what} picker: {e}")
            self.root.deiconify()

    # --- the regions ------------------------------------------------------
    # Each names its wording and colours and says where the result goes. The
    # variable names stay spelled out so they remain greppable.

    def pick_hp_coordinates(self):
        """Allow user to drag and select HP bar area dynamically"""
        self._pick_region("HP bar", "HP Bar Area", "yellow", "red", self._commit_hp_area)

    def _commit_hp_area(self, x, y, width, height):
        self.hp_x_var.set(str(x))
        self.hp_y_var.set(str(y))
        self.hp_width_var.set(str(width))
        self.hp_height_var.set(str(height))
        self.hp_coords_var.set(f"{x},{y}")
        config.hp_bar_area.update({'x': x, 'y': y, 'width': width, 'height': height})
        return f"Position: ({x}, {y})\nSize: {width}x{height} pixels"

    def pick_mp_coordinates(self):
        """Allow user to drag and select MP bar area dynamically"""
        self._pick_region("MP bar", "MP Bar Area", "cyan", "blue", self._commit_mp_area)

    def _commit_mp_area(self, x, y, width, height):
        self.mp_x_var.set(str(x))
        self.mp_y_var.set(str(y))
        self.mp_width_var.set(str(width))
        self.mp_height_var.set(str(height))
        self.mp_coords_var.set(f"{x},{y}")
        config.mp_bar_area.update({'x': x, 'y': y, 'width': width, 'height': height})
        return f"Position: ({x}, {y})\nSize: {width}x{height} pixels"

    def pick_enemy_hp_coordinates(self):
        """Allow user to drag and select enemy HP bar area dynamically"""
        self._pick_region("enemy HP bar", "Enemy HP Bar Area", "orange", "orange",
                          self._commit_enemy_hp_area)

    def _commit_enemy_hp_area(self, x, y, width, height):
        self.enemy_hp_x_var.set(str(x))
        self.enemy_hp_y_var.set(str(y))
        self.enemy_hp_width_var.set(str(width))
        self.enemy_hp_height_var.set(str(height))
        self.enemy_hp_coords_var.set(f"{x},{y}")
        config.target_hp_bar_area.update({'x': x, 'y': y, 'width': width, 'height': height})
        return f"Position: ({x}, {y})\nSize: {width}x{height} pixels"

    def pick_mob_coordinates(self):
        """Allow user to drag and select mob detection area dynamically"""
        self._pick_region("mob name", "Mob Detection Area", "lime", "white",
                          self._commit_mob_area)

    def _commit_mob_area(self, x, y, width, height):
        # This one stores the centre, not the top-left: the mob name is matched
        # around a point rather than from a corner.
        center_x = x + (width // 2)
        center_y = y + (height // 2)
        self.mob_coords_var.set(f"{center_x},{center_y}")
        self.mob_width_var.set(str(width))
        self.mob_height_var.set(str(height))
        config.target_name_area.update(
            {'x': center_x, 'y': center_y, 'width': width, 'height': height})
        return (f"Center: ({center_x}, {center_y})\n"
                f"Size: {width}x{height} pixels")

    def pick_system_message_coordinates(self):
        """Allow user to drag and select system message area dynamically"""
        self._pick_region("system message", "System Message Area", "orange", "orange",
                          self._commit_system_message_area)

    def _commit_system_message_area(self, x, y, width, height):
        config.system_message_area.update(
            {'x': x, 'y': y, 'width': width, 'height': height})
        return f"Top-left: ({x}, {y})\nSize: {width}x{height} pixels"

    def _show_calibration_capture_preview(self, image_path, method, stats, success=True):
        """Show what Calibrate actually captured (saved to debug/calibrate_original.png)."""
        import os
        import tkinter as tk
        if not image_path or not os.path.isfile(image_path):
            return
        try:
            pil = Image.open(image_path)
        except Exception as exc:
            print(f'[Calibration] Could not open capture preview: {exc}')
            return

        top = tk.Toplevel(self.root)
        top.title('Calibration capture preview')
        top.transient(self.root)
        top.grab_set()

        mean = stats.get('mean', 0) if stats else 0
        std = stats.get('std', 0) if stats else 0
        w = stats.get('width', pil.width)
        h = stats.get('height', pil.height)
        status = 'OK' if success else 'FAILED'
        if mean < 6:
            status = 'BLACK / EMPTY CAPTURE'
        caption = (
            f"{status} — {w}×{h}px via {method} "
            f"(brightness mean={mean:.1f}, std={std:.1f})\n"
            f"{image_path}"
        )

        max_w = 960
        scale = min(1.0, max_w / max(1, pil.width))
        if scale < 1.0:
            pil = pil.resize(
                (max(1, int(pil.width * scale)), max(1, int(pil.height * scale))),
                Image.Resampling.LANCZOS,
            )

        photo = ImageTk.PhotoImage(pil)
        label = tk.Label(top, image=photo)
        label.image = photo
        label.pack(padx=8, pady=(8, 4))
        tk.Label(top, text=caption, justify='left', wraplength=max_w).pack(padx=8, pady=(0, 8))
        tk.Button(top, text='Close', command=top.destroy).pack(pady=(0, 8))
