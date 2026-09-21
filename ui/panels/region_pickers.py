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
                                       font=(ui_fonts.APP_FONT_FAMILY, 16), 
                                       fg="white", 
                                       bg="black")
            instruction_label.place(relx=0.5, rely=0.1, anchor="center")
            
            # Label to show current position and size
            info_label = tk.Label(picker_window, 
                                text="", 
                                font=(ui_fonts.APP_FONT_FAMILY, 12), 
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
                                       font=(ui_fonts.APP_FONT_FAMILY, 16), 
                                       fg="white", 
                                       bg="black")
            instruction_label.place(relx=0.5, rely=0.1, anchor="center")
            
            # Label to show current position and size
            info_label = tk.Label(picker_window, 
                                text="", 
                                font=(ui_fonts.APP_FONT_FAMILY, 12), 
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
                                       font=(ui_fonts.APP_FONT_FAMILY, 16), 
                                       fg="white", 
                                       bg="black")
            instruction_label.place(relx=0.5, rely=0.1, anchor="center")
            
            # Label to show current position and size
            info_label = tk.Label(picker_window, 
                                text="", 
                                font=(ui_fonts.APP_FONT_FAMILY, 12), 
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
                                       font=(ui_fonts.APP_FONT_FAMILY, 16), 
                                       fg="white", 
                                       bg="black")
            instruction_label.place(relx=0.5, rely=0.1, anchor="center")
            
            # Label to show current position and size
            info_label = tk.Label(picker_window, 
                                text="", 
                                font=(ui_fonts.APP_FONT_FAMILY, 12), 
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
                                       font=(ui_fonts.APP_FONT_FAMILY, 16), 
                                       fg="white", 
                                       bg="black")
            instruction_label.place(relx=0.5, rely=0.1, anchor="center")
            
            # Label to show current position and size
            info_label = tk.Label(picker_window, 
                                text="", 
                                font=(ui_fonts.APP_FONT_FAMILY, 12), 
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
                    
                    config.system_message_area['x'] = rel_x
                    config.system_message_area['y'] = rel_y
                    config.system_message_area['width'] = width
                    config.system_message_area['height'] = height
                    
                    # Close picker window and show main window
                    picker_window.destroy()
                    self.root.deiconify()
                    
                    print(f"System message area set to: ({rel_x}, {rel_y}) {width}x{height}")
                    messagebox.showinfo(
                        "System Message Area",
                        f"Top-left: ({rel_x}, {rel_y})\nSize: {width}x{height} pixels",
                    )
                    
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
