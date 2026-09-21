"""Mob filter template list, previews, capture and match testing.

Moved out of gui.py unchanged. Mixed into BotGUI, so these methods keep
using self exactly as before -- no call sites changed.
"""
from PIL import Image
from PIL import ImageTk
import config
import customtkinter as ctk
import cv2
from tkinter import messagebox
import mob_filter
import mob_template_store
import threading
import time
import tkinter as tk
import window_utils


class MobFilterPanelMixin:
    """Mob filter template list, previews, capture and match testing."""

    def _mob_filter_ready(self):
        """Mob filter controls require connect + enemy name region."""
        return (
            config.connected_window is not None
            and mob_filter.scan_area_available()
        )

    def _mob_scan_status_text(self):
        if not config.connected_window:
            return 'Scan area: connect to game first'
        if not mob_filter.scan_area_available():
            return 'Scan area: set Enemy Name in Region Editor'
        area = mob_filter.get_scan_area()
        return f"Scan area: ({area['x']},{area['y']}) {area['width']}×{area['height']}"

    def update_mob_filter_ui_state(self):
        """Enable mob filter controls when connected and enemy name region is set."""
        if not hasattr(self, 'mob_checkbox'):
            return
        ready = self._mob_filter_ready() and not config.assist_only_enabled
        state = 'normal' if ready else 'disabled'
        try:
            self.mob_checkbox.configure(state=state)
            if hasattr(self, 'mob_elite_skip_checkbox'):
                self.mob_elite_skip_checkbox.configure(state=state)
            if hasattr(self, 'mob_safe_buffs_checkbox'):
                self.mob_safe_buffs_checkbox.configure(state=state)
            if hasattr(self, 'self_target_entry'):
                self.self_target_entry.configure(state='normal' if state == 'normal' else 'disabled')
            self.mob_learn_btn.configure(state=state)
            self.mob_remove_btn.configure(state=state)
            self.mob_test_btn.configure(state=state)
            if hasattr(self, 'mob_compare_btn'):
                self.mob_compare_btn.configure(state=state)
            # Keep list readable even before connect/calibrate (disabled listboxes hide inserts).
            self.mob_listbox.configure(state='normal')
        except (tk.TclError, AttributeError):
            pass
        if hasattr(self, 'mob_scan_label'):
            self.mob_scan_label.configure(text=self._mob_scan_status_text())

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
            import region_helpers
            region_helpers.sync_mob_scan_from_enemy_name()
            mob_filter.invalidate_cache()
            
            print(f"Updated mob coordinates: {config.target_name_area}")
        except (ValueError, AttributeError) as e:
            print(f"Invalid coordinates - please enter numbers only: {e}")

    def _refresh_mob_list(self, select_index=None, update_preview=True):
        if not hasattr(self, 'mob_listbox'):
            return
        lb = self.mob_listbox
        prev_state = str(lb.cget('state'))
        try:
            if prev_state == 'disabled':
                lb.configure(state='normal')
            lb.delete(0, tk.END)
            for entry in config.mob_templates:
                lb.insert(tk.END, entry.get('name', entry.get('id', '?')))
            if not config.mob_templates:
                self._clear_mob_preview()
                return
            idx = select_index if select_index is not None else 0
            idx = min(max(idx, 0), len(config.mob_templates) - 1)
            lb.selection_clear(0, tk.END)
            lb.selection_set(idx)
            lb.activate(idx)
            if update_preview:
                self._update_mob_preview()
        finally:
            if prev_state == 'disabled':
                lb.configure(state='disabled')

    def _bgr_to_preview_photo(self, bgr):
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        pil.thumbnail((360, 80), Image.Resampling.LANCZOS)
        if pil.height < 40:
            scale = 40 / max(pil.height, 1)
            pil = pil.resize(
                (max(1, int(pil.width * scale)), 40),
                Image.Resampling.NEAREST,
            )
        return ImageTk.PhotoImage(pil)

    def _clear_mob_preview(self):
        self._mob_preview_photo = None
        self.mob_preview_label.config(image='', text='')
        self.mob_preview_caption.configure(text='Select a template')

    def _mob_hp_profile_caption(self, entry):
        if entry.get('hp_max_file') or mob_template_store.load_hp_max_sig(entry) is not None:
            return " — max HP signature saved (elite skip)"
        return ""

    def _show_mob_preview_bgr(self, bgr, caption=None):
        self._mob_preview_photo = self._bgr_to_preview_photo(bgr)
        self.mob_preview_label.config(image=self._mob_preview_photo, text='')
        if caption:
            self.mob_preview_caption.configure(text=caption)

    def _mob_preview_caption(self, entry, w, h):
        note = "captured region"
        if entry.get('normalized') and getattr(config, 'mob_normalize_match', True):
            note = "captured region (name corners used for matching)"
        return (
            f"{entry.get('name', '?')} — {w}×{h} px — {note}"
            f"{self._mob_hp_profile_caption(entry)}"
        )

    def _update_mob_preview(self):
        sel = self.mob_listbox.curselection()
        if not sel or sel[0] >= len(config.mob_templates):
            self._clear_mob_preview()
            return
        entry = config.mob_templates[sel[0]]
        if not mob_template_store.template_file_exists(entry):
            self._clear_mob_preview()
            self.mob_preview_caption.configure(
                text=f"{entry.get('name', '?')} — image missing, use Learn again",
            )
            return
        preview = mob_filter.preview_bgr_for_entry(entry)
        if preview is None:
            self._clear_mob_preview()
            return
        h, w = preview.shape[:2]
        self._show_mob_preview_bgr(preview, self._mob_preview_caption(entry, w, h))

    def _learn_mob_template(self):
        if not self._mob_filter_ready():
            messagebox.showwarning(
                'Learn',
                'Connect to the game and set Enemy Name in Region Editor first.',
            )
            return
        print('Switch to game, target mob — capturing in 2s…')
        self.root.after(2000, self._start_mob_template_capture_thread)

    def _start_mob_template_capture_thread(self):
        threading.Thread(target=self._capture_mob_template_worker, daemon=True).start()

    def _capture_mob_template_worker(self):
        if not config.connected_window:
            config.safe_update_gui(
                lambda: messagebox.showerror('Learn', 'No window connected.'),
            )
            return
        hwnd = window_utils.resolve_hwnd()
        if not hwnd:
            config.safe_update_gui(
                lambda: messagebox.showerror('Learn', 'Could not get game window handle.'),
            )
            return
        window_utils.focus_game_window(hwnd)
        bgr = mob_filter.capture_scan_area(hwnd)
        if bgr is None or bgr.size == 0:
            print('Learn failed — could not capture scan region')
            return
        save_img = mob_filter.prepare_template_for_storage(bgr)
        if save_img is None:
            print('Learn failed — could not prepare template image')
            return
        h, w = save_img.shape[:2]
        hp_profile = mob_filter.build_hp_profile(hwnd)
        entry = mob_template_store.add_template(
            save_img,
            hp_profile=hp_profile,
            normalized=getattr(config, 'mob_normalize_match', True),
        )
        if entry is None:
            config.safe_update_gui(
                lambda: messagebox.showerror('Learn', 'Could not save template image to disk.'),
            )
            return
        mob_filter.invalidate_cache()
        new_idx = len(config.mob_templates) - 1

        def _finish_ui():
            self._refresh_mob_list(select_index=new_idx, update_preview=False)
            caption = self._mob_preview_caption(entry, w, h)
            if not hp_profile:
                caption += " — no HP numbers detected"
            preview = mob_filter.preview_bgr_for_entry(entry)
            if preview is not None:
                self._show_mob_preview_bgr(preview, caption)
            hp_note = self._mob_hp_profile_caption(entry).strip(' —') or "no HP profile"
            print(f"Learned {entry['name']} ({w}×{h}), {hp_note}")

        config.safe_update_gui(_finish_ui)

    def _remove_mob_template(self):
        sel = self.mob_listbox.curselection()
        if not sel:
            messagebox.showinfo('Remove', 'Select a monster from the list first.')
            return
        entry = config.mob_templates[sel[0]]
        sel_idx = sel[0]
        mob_template_store.remove_template(entry.get('id'))
        mob_filter.invalidate_cache()
        if config.mob_templates:
            self._refresh_mob_list(select_index=min(sel_idx, len(config.mob_templates) - 1))
        else:
            self._refresh_mob_list()

    def _test_mob_match(self):
        if not self._mob_filter_ready():
            messagebox.showwarning(
                'Test match',
                'Connect to the game and set Enemy Name in Region Editor first.',
            )
            return
        if not config.mob_templates:
            messagebox.showwarning('Test match', 'Learn at least one mob template first.')
            return
        self.root.after(150, self._run_mob_match_test)

    def _run_mob_match_test(self):
        hwnd = window_utils.resolve_hwnd()
        if not hwnd:
            messagebox.showerror('Test match', 'Could not get game window handle.')
            return
        window_utils.focus_game_window(hwnd)
        time.sleep(0.15)
        result = mob_filter.probe(hwnd)
        if result.get('error'):
            print(f"TEST: {result['error']}")
            messagebox.showerror('Test match', result['error'])
            if hasattr(self, 'current_mob_label'):
                self.current_mob_label.configure(text=result['error'], text_color="red")
            return
        match = result.get('match')
        if match:
            msg = (
                f"Match: {match['name']} ({match['confidence']:.0%})\n\n"
                "Visual match on name/level bar (forgiving of small pixel shifts). "
                "Not letter case — uses shape, not OCR."
            )
            print(f"TEST: {msg}")
            messagebox.showinfo('Test match', msg)
            if hasattr(self, 'current_mob_label'):
                self.current_mob_label.configure(text=match['name'], text_color="green")
        elif result.get('elite_skipped'):
            name = result.get('best_name', '?')
            msg = (
                f"Name matched {name}, but skipped as elite (higher max HP than learned normal mob).\n\n"
                "Learn templates from normal mobs at full HP, or disable elite skip."
            )
            print(f"TEST: {msg}")
            messagebox.showwarning('Test match', msg)
            if hasattr(self, 'current_mob_label'):
                self.current_mob_label.configure(text=f"{name} (elite)", text_color="orange")
        else:
            best = result.get('best_score', 0)
            name = result.get('best_name', '?')
            thresh = result.get('threshold', config.mob_match_threshold)
            size = result.get('scan_size')
            size_txt = f' Capture size: {size[0]}×{size[1]}.' if size else ''
            msg = (
                f"No match.\n\n"
                f"Best: {name} at {best:.0%}\n"
                f"Need: {thresh:.0%} (threshold in settings){size_txt}\n\n"
                f"Tip: Re-learn the template with the same scan region while this mob is targeted."
            )
            print(f"TEST: {msg}")
            messagebox.showwarning('Test match', msg)
            if hasattr(self, 'current_mob_label'):
                self.current_mob_label.configure(text="No match", text_color="orange")

    def _compare_selected_mob_template_live(self):
        if not self._mob_filter_ready():
            messagebox.showwarning(
                'Compare',
                'Connect to the game and set Enemy Name in Region Editor first.',
            )
            return
        if not config.mob_templates:
            messagebox.showwarning('Compare', 'Learn at least one mob template first.')
            return
        sel = self.mob_listbox.curselection()
        if not sel or sel[0] >= len(config.mob_templates):
            messagebox.showinfo('Compare', 'Select a template from the list first.')
            return
        entry = config.mob_templates[sel[0]]
        threading.Thread(
            target=self._compare_mob_template_worker,
            args=(entry,),
            daemon=True,
        ).start()

    def _compare_mob_template_worker(self, entry):
        hwnd = window_utils.resolve_hwnd()
        if not hwnd:
            config.safe_update_gui(
                lambda: messagebox.showerror('Compare', 'Could not get game window handle.'),
            )
            return
        window_utils.focus_game_window(hwnd)
        time.sleep(0.15)

        result = mob_filter.compare_live_to_entry(hwnd, entry)
        if result.get('error'):
            config.safe_update_gui(
                lambda: messagebox.showerror('Compare', result['error']),
            )
            return
        config.safe_update_gui(lambda: self._show_mob_compare_window(entry, result))

    def _show_mob_compare_window(self, entry, result):
        def to_bgr(img):
            if img is None:
                return None
            if img.ndim == 2:
                return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            return img

        scan_bgr = to_bgr(result.get('scan_bgr'))
        tmpl_bgr = to_bgr(result.get('template_bgr'))
        scan_norm = to_bgr(result.get('scan_norm'))
        tmpl_norm = to_bgr(result.get('template_norm'))

        win = tk.Toplevel(self.root)
        win.title('Mob Filter Compare')
        win.configure(bg='#242424')
        win.resizable(False, False)
        win.transient(self.root)

        header = ctk.CTkFrame(win, fg_color=('gray18', 'gray14'))
        header.pack(fill='x', padx=12, pady=(12, 8))
        score = float(result.get('score', 0.0))
        agree = float(result.get('column_agreement', 0.0))
        thresh = float(result.get('threshold', config.mob_match_threshold))
        name = entry.get('name', entry.get('id', '?'))
        ctk.CTkLabel(
            header,
            text=f'{name} — score {score:.0%} (need {thresh:.0%}) · column agreement {agree:.0%}',
            font=ctk.CTkFont(size=12, weight='bold'),
            anchor='w',
        ).pack(anchor='w', padx=10, pady=(8, 2))
        ctk.CTkLabel(
            header,
            text='Top row: raw capture (live vs template). Bottom row: normalized match mask (what matcher uses).',
            font=ctk.CTkFont(size=10),
            text_color=('gray55', 'gray65'),
            anchor='w',
        ).pack(anchor='w', padx=10, pady=(0, 8))

        body = ctk.CTkFrame(win, fg_color='transparent')
        body.pack(padx=12, pady=(0, 12))

        grid = ctk.CTkFrame(body, fg_color=('gray92', 'gray20'), corner_radius=8)
        grid.pack()

        # Prevent PhotoImage GC.
        win._mob_compare_photos = []

        def add_cell(r, c, title, bgr):
            cell = ctk.CTkFrame(grid, fg_color='transparent')
            cell.grid(row=r, column=c, padx=10, pady=10)
            ctk.CTkLabel(
                cell, text=title, font=ctk.CTkFont(size=10, weight='bold'),
                text_color=('gray30', 'gray70'),
            ).pack(anchor='w', pady=(0, 4))
            img = self._bgr_to_preview_photo(bgr) if bgr is not None else None
            lbl = tk.Label(cell, bg='#242424', bd=0, highlightthickness=0)
            lbl.pack()
            if img is not None:
                lbl.configure(image=img)
                win._mob_compare_photos.append(img)
            else:
                lbl.configure(text='(missing)', fg='white', bg='#242424')

        add_cell(0, 0, 'Live scan (raw)', scan_bgr)
        add_cell(0, 1, 'Template (raw)', tmpl_bgr)
        add_cell(1, 0, 'Live scan (normalized)', scan_norm)
        add_cell(1, 1, 'Template (normalized)', tmpl_norm)

    def test_mob_detection(self):
        """Test mob filter match (alias for status bar testing)."""
        self._test_mob_match()
