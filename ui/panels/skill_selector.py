"""Skill icon picker shared by the buff and skill-sequence slots.

Moved out of gui.py unchanged. Mixed into BotGUI, so these methods keep
using self exactly as before -- no call sites changed.
"""
from PIL import Image
from PIL import ImageTk
import config
import customtkinter as ctk
import os
import tkinter as tk


class SkillSelectorMixin:
    """Skill icon picker shared by the buff and skill-sequence slots."""

    def _preload_skill_images(self):
        """Preload all skill images during app initialization (non-blocking)"""
        try:
            from PIL import Image
            import os
            import re
            
            def natural_sort_key(text):
                return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]
            
            # Static job list (same as in show_skill_selector)
            STATIC_JOB_LIST = [
                {'label': 'Abikara', 'key': 'Abikara', 'sequenceNo': 1},
                {'label': 'Samabat', 'key': 'Samabat', 'sequenceNo': 2},
                {'label': 'Banar', 'key': 'Banar', 'sequenceNo': 3},
                {'label': 'Satya', 'key': 'Satya', 'sequenceNo': 4},
                {'label': 'Nakayuda', 'key': 'Nakayuda', 'sequenceNo': 5},
                {'label': 'Vidya', 'key': 'Vidya', 'sequenceNo': 6},
                {'label': 'Druka', 'key': 'Druka', 'sequenceNo': 7},
                {'label': 'Karya', 'key': 'Karya', 'sequenceNo': 8},
                # {'label': 'Others', 'key': 'Etc', 'sequenceNo': 9},
            ]
            
            # Resolve against the project root / PyInstaller bundle, not this
            # package folder -- this module lives in ui/panels/, jobs/ does not.
            jobs_folder = config.resolve_resource_path('jobs')
            
            if not jobs_folder:
                return
            
            # Preload images for each job
            for job_def in STATIC_JOB_LIST:
                job_key = job_def['key']
                job_path = os.path.join(jobs_folder, job_key)
                
                if not os.path.exists(job_path) or not os.path.isdir(job_path):
                    continue
                
                try:
                    images = [f for f in os.listdir(job_path) 
                             if f.lower().endswith(('.bmp', '.BMP'))]
                    images_sorted = sorted(images, key=natural_sort_key)
                    
                    # Preload and cache images
                    cached_images = []
                    for img_file in images_sorted:
                        try:
                            img_path = os.path.join(job_path, img_file)
                            pil_image = Image.open(img_path)
                            pil_image = pil_image.resize((48, 48), Image.Resampling.LANCZOS)
                            # Store PIL image (will convert to PhotoImage when needed)
                            cached_images.append((img_path, pil_image, img_file))
                        except Exception as e:
                            print(f"Error preloading image {img_file}: {e}")
                            continue
                    
                    self.skill_images_cache[job_key] = cached_images
                except Exception as e:
                    print(f"Error preloading images for job {job_key}: {e}")
                    continue
            
            print(f"✅ Preloaded skill images for {len(self.skill_images_cache)} jobs")
        except Exception as e:
            print(f"Error in _preload_skill_images: {e}")
            import traceback
            traceback.print_exc()

    def show_skill_selector(self, callback_func, callback_arg, title="Choose Skill"):
        """Show popup window to select skill image, grouped by job (reusable for buffs and skill sequence)"""
        try:
            from PIL import Image, ImageTk
            import os
            
            # Static job list: [{label, key, sequenceNo}, ...]
            # label: Display name in the tab
            # key: Folder name in the jobs directory
            # sequenceNo: Order for sorting tabs
            STATIC_JOB_LIST = [
                {'label': 'Abikara', 'key': 'Abikara', 'sequenceNo': 1},
                {'label': 'Samabat', 'key': 'Samabat', 'sequenceNo': 2},
                {'label': 'Banar', 'key': 'Banar', 'sequenceNo': 3},
                {'label': 'Satya', 'key': 'Satya', 'sequenceNo': 4},
                {'label': 'Nakayuda', 'key': 'Nakayuda', 'sequenceNo': 5},
                {'label': 'Vidya', 'key': 'Vidya', 'sequenceNo': 6},
                {'label': 'Druka', 'key': 'Druka', 'sequenceNo': 7},
                {'label': 'Karya', 'key': 'Karya', 'sequenceNo': 8},
                # {'label': 'Others', 'key': 'Etc', 'sequenceNo': 9},
                # Add more jobs as needed
            ]
            
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
            
            # Create main container immediately (folder already checked during preload)
            main_container = ctk.CTkFrame(popup)
            main_container.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Cache to track which tabs have been loaded
            loaded_tabs = set()
            # Map tab labels to job definitions for loading images
            label_to_job = {}
            
            # Function to handle tab changes (will be set as command)
            def on_tab_changed(tab_label=None):
                """Handle tab change event - load images lazily"""
                # If tab_label not provided, get it from tabview
                if tab_label is None:
                    try:
                        tab_label = tabview.get()
                    except:
                        return
            
                if tab_label and tab_label in label_to_job:
                    load_job_tab_images(tab_label)
                self.last_skill_selector_tab = tab_label
            
            # Create tabview for jobs immediately with command callback
            tabview = ctk.CTkTabview(main_container, corner_radius=8, command=on_tab_changed)
            tabview.pack(fill="both", expand=True, pady=(0, 10))
            
            # Create all tabs immediately from static list (no folder checking yet)
            for job_def in sorted(STATIC_JOB_LIST, key=lambda x: x['sequenceNo']):
                label = job_def['label']
                label_to_job[label] = job_def
                
                # Create tab with label (display name) - instant, no I/O
                job_tab = tabview.add(label)
                
                # Create scrollable frame for skills in this job tab
                scroll_frame = ctk.CTkScrollableFrame(job_tab)
                scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
                
                # Store scroll_frame reference in job definition
                job_def['scroll_frame'] = scroll_frame
            
            # Function to load images for a specific job tab (uses preloaded cache)
            def load_job_tab_images(tab_label):
                """Load images for a job tab from preloaded cache"""
                if tab_label in loaded_tabs:
                    return  # Already loaded
                
                # Get the job definition from the label
                job_def = label_to_job.get(tab_label)
                if not job_def:
                    return
                
                job_key = job_def['key']
                scroll_frame = job_def['scroll_frame']
                
                # Get preloaded images from cache
                cached_images = self.skill_images_cache.get(job_key, [])
                
                if not cached_images:
                    return  # No images in cache
                
                loaded_tabs.add(tab_label)
                
                # Create grid for skills (6 columns for compact layout)
                row = 0
                col = 0
                
                for img_path, pil_image, img_file in cached_images:
                    try:
                        # Convert preloaded PIL image to PhotoImage
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
                        img_button.image = image  # Keep reference to prevent garbage collection
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
            
            # Load the first tab immediately (or last active tab)
            def load_initial_tab():
                tab_labels = list(label_to_job.keys())
                if self.last_skill_selector_tab and self.last_skill_selector_tab in label_to_job:
                    tab_to_load = self.last_skill_selector_tab
                elif tab_labels:
                    tab_to_load = tab_labels[0]
                else:
                    return
                
                # Set the tab (this may trigger the command callback)
                tabview.set(tab_to_load)
                # Explicitly load images for the initial tab (in case callback didn't fire)
                on_tab_changed(tab_to_load)
            
            # Load initial tab after window is ready
            popup.after(10, load_initial_tab)
            
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
            pil_image = pil_image.resize((40, 40), Image.Resampling.LANCZOS)
            image = ImageTk.PhotoImage(pil_image)
            canvas = self.skill_sequence_canvases[idx]
            canvas.delete('all')
            canvas.create_image(20, 20, image=image)
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

    def load_buff_image(self, idx, image_path):
        """Load and display buff image (image_path should be absolute for loading)"""
        try:
            from PIL import Image, ImageTk
            pil_image = Image.open(image_path)
            pil_image = pil_image.resize((40, 40), Image.Resampling.LANCZOS)
            image = ImageTk.PhotoImage(pil_image)
            canvas = self.buffs_canvases[idx]
            canvas.delete('all')
            canvas.create_image(20, 20, image=image)
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
