"""Single-screen GUI for Kathana Helper Lite."""
import sys
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import cv2
import config
import window_utils
import settings_manager
import bot_loop
import region_picker
import bar_reader
import mob_filter
import mob_template_store


# Layout tokens
PAD_X = 14
PAD_Y = 10
BTN_H = 34
ENTRY_H = 34
ENTRY_W = 60
CHK = 22
POT_GAP = 10
POT_MIN_COL = 200       # minimum width per HP/MP column when resizing
WINDOW_W = 660
WINDOW_H = 760
WINDOW_MIN_W = 520
SKILL_COL_GAP = 6
SKILL_KEY_W = 28
SKILL_ENTRY_W = 54
ACTION_ENTRY_W = 44
ACT_CELL_PAD = 8
ACT_COL_GAP = 4

SKILL_COLUMNS = [
    [1, 2, 3, 4, 5],
    [6, 7, 8, 9, 0],
    [f'f{i}' for i in range(1, 6)],
    [f'f{i}' for i in range(6, 11)],
]
COL_TITLES = ['1 – 5', '6 – 0', 'F1 – F5', 'F6 – F10']


def enable_dpi_awareness():
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class LiteGUI:
    def __init__(self):
        enable_dpi_awareness()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('blue')
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)

        self.root = ctk.CTk()
        self.font_body = ctk.CTkFont(family='Segoe UI', size=13)
        self.font_sm = ctk.CTkFont(family='Segoe UI', size=12)
        self.font_cap = ctk.CTkFont(family='Segoe UI', size=11)
        self.font_title = ctk.CTkFont(family='Segoe UI', size=14, weight='bold')
        self.font_key = ctk.CTkFont(family='Segoe UI', size=12, weight='bold')

        self.root.title('Kathana Helper Lite')
        self.root.geometry(f'{WINDOW_W}x{WINDOW_H}')
        self.root.minsize(WINDOW_MIN_W, 480)

        self.window_var = ctk.StringVar(value='')
        self.status_var = ctk.StringVar(value='Stopped')
        self.hp_status_var = ctk.StringVar(value='')
        self.mp_status_var = ctk.StringVar(value='')
        self.skill_vars = {}
        self.action_vars = {}
        self._syncing_ui = False
        self._live_config_ready = False
        self._tracked_var_ids = set()
        self._save_notice_after_id = None

        self._build_ui()
        self._wire_live_config()
        self._live_config_ready = True
        settings_manager.load_settings()
        self._sync_ui_from_config()
        self._refresh_windows()
        self._tick_status()

    def _card(self, parent, title=None, title_extra=None):
        """Return a body frame for content. Title uses pack; use pack OR grid on body, not both."""
        outer = ctk.CTkFrame(parent, corner_radius=10, border_width=1,
                             border_color=('gray80', 'gray30'))
        outer.pack(fill='x', pady=(0, PAD_Y))
        inner = ctk.CTkFrame(outer, fg_color='transparent')
        inner.pack(fill='x', padx=PAD_X, pady=PAD_Y)
        if title:
            title_row = ctk.CTkFrame(inner, fg_color='transparent')
            title_row.pack(fill='x', pady=(0, 6))
            ctk.CTkLabel(title_row, text=title, font=self.font_title, anchor='w').pack(side='left')
            if title_extra:
                title_extra(title_row)
        body = ctk.CTkFrame(inner, fg_color='transparent')
        body.pack(fill='both', expand=True)
        return body

    def _entry(self, parent, textvariable, width=ENTRY_W):
        return ctk.CTkEntry(
            parent, width=width, height=ENTRY_H, textvariable=textvariable,
            font=self.font_body, corner_radius=6,
        )

    def _btn(self, parent, text, command, width=80, secondary=False):
        kw = dict(
            text=text, command=command, width=width, height=BTN_H,
            font=self.font_sm, corner_radius=8,
        )
        if secondary:
            kw['fg_color'] = ('gray85', 'gray25')
            kw['hover_color'] = ('gray75', 'gray35')
        return ctk.CTkButton(parent, **kw)

    def _chk(self, parent, text, variable, command=None, width=None):
        kw = dict(
            text=text, variable=variable, command=command,
            font=self.font_sm, checkbox_width=CHK, checkbox_height=CHK,
            height=ENTRY_H, corner_radius=4,
        )
        if width is not None:
            kw['width'] = width
        return ctk.CTkCheckBox(parent, **kw)

    def _pot_subpanel(self, parent, title, accent_border, grid_col):
        """Colored sub-panel for HP or MP; expands with parent grid."""
        panel = ctk.CTkFrame(
            parent, corner_radius=8, border_width=2, border_color=accent_border,
            fg_color=('gray95', 'gray18'),
        )
        pad = (0, POT_GAP // 2) if grid_col == 0 else (POT_GAP // 2, 0)
        panel.grid(row=0, column=grid_col, sticky='nsew', padx=pad)
        body = ctk.CTkFrame(panel, fg_color='transparent')
        body.pack(fill='x', anchor='n', padx=10, pady=10)
        ctk.CTkLabel(body, text=title, font=self.font_title, anchor='w').pack(
            fill='x', pady=(0, 8),
        )
        return body

    def _pot_pick_button_text(self, kind, fallback):
        area = config.hp_bar_area if kind == 'hp' else config.mp_bar_area
        if not config.bar_area_configured(area):
            return fallback
        return f"✓ ({area['x']},{area['y']}) {area['width']}×{area['height']}"

    def _pot_panel_header(self, parent, enable_var, enable_text, pick_fallback, pick_cmd,
                          region_kind, live_var, live_colors):
        """Enable + live readout + pick button (coords shown on the button)."""
        head = ctk.CTkFrame(parent, fg_color='transparent')
        head.pack(fill='x', pady=(0, 6))
        head.grid_columnconfigure(0, weight=1)

        self._chk(head, enable_text, enable_var, self._apply_live_config).grid(
            row=0, column=0, sticky='w',
        )
        live_lbl = ctk.CTkLabel(
            head, textvariable=live_var, font=self.font_cap,
            text_color=live_colors, anchor='e',
        )
        live_lbl.grid(row=0, column=1, sticky='e', padx=(6, 6))
        pick_btn = self._btn(
            head,
            self._pot_pick_button_text(region_kind, pick_fallback),
            pick_cmd,
            width=148,
            secondary=True,
        )
        pick_btn.grid(row=0, column=2, sticky='e')
        return pick_btn, live_lbl

    def _pot_rule_row(self, parent, pct_label, pct_var, key_var, on_remove=None):
        """Shared HP/MP rule row: [label %] [entry] Pot key [entry] [optional remove]."""
        rule = ctk.CTkFrame(parent, fg_color=('gray90', 'gray22'), corner_radius=6)
        rule.pack(fill='x', pady=2)
        inner = ctk.CTkFrame(rule, fg_color='transparent')
        inner.pack(fill='x', padx=8, pady=8)
        inner.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(inner, text=pct_label, font=self.font_sm).grid(
            row=0, column=0, sticky='w',
        )
        self._entry(inner, pct_var, width=52).grid(row=0, column=1, sticky='ew', padx=(6, 4))
        ctk.CTkLabel(inner, text='Pot key', font=self.font_sm).grid(
            row=0, column=2, sticky='w', padx=(4, 4),
        )
        self._entry(inner, key_var, width=52).grid(row=0, column=3, sticky='w')
        if on_remove:
            ctk.CTkButton(
                inner, text='×', width=28, height=28, font=self.font_body,
                fg_color='transparent', hover_color=('gray80', 'gray30'),
                command=on_remove,
            ).grid(row=0, column=4, sticky='e', padx=(4, 0))
        return rule

    def _mob_scan_button_text(self):
        area = config.mob_scan_area
        if config.bar_area_configured(area):
            return f"✓ ({area['x']},{area['y']}) {area['width']}×{area['height']}"
        return 'Select region'

    def _refresh_mob_scan_btn(self):
        if hasattr(self, 'mob_scan_btn'):
            self.mob_scan_btn.configure(text=self._mob_scan_button_text())

    def _refresh_mob_list(self, select_index=None):
        self.mob_listbox.delete(0, tk.END)
        for entry in config.mob_templates:
            self.mob_listbox.insert(tk.END, entry.get('name', entry.get('id', '?')))
        if not config.mob_templates:
            self._clear_mob_preview()
            return
        idx = select_index if select_index is not None else 0
        idx = min(max(idx, 0), len(config.mob_templates) - 1)
        self.mob_listbox.selection_clear(0, tk.END)
        self.mob_listbox.selection_set(idx)
        self.mob_listbox.activate(idx)
        self._update_mob_preview()

    def _bgr_to_preview_photo(self, bgr):
        """Build a PhotoImage for preview (works in dev and PyInstaller builds)."""
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        pil.thumbnail((320, 52), Image.Resampling.LANCZOS)
        if pil.height < 36:
            scale = 36 / pil.height
            pil = pil.resize(
                (max(1, int(pil.width * scale)), 36),
                Image.Resampling.NEAREST,
            )
        return ImageTk.PhotoImage(pil)

    def _clear_mob_preview(self):
        self._mob_preview_photo = None
        self.mob_preview_label.config(image='', text='')
        self.mob_preview_caption.configure(text='No template selected')

    def _show_mob_preview_bgr(self, bgr, caption=None):
        """Display a captured/template BGR image in the preview box."""
        self._mob_preview_photo = self._bgr_to_preview_photo(bgr)
        self.mob_preview_label.config(image=self._mob_preview_photo, text='')
        if caption:
            self.mob_preview_caption.configure(text=caption)

    def _update_mob_preview(self):
        sel = self.mob_listbox.curselection()
        if not sel or sel[0] >= len(config.mob_templates):
            self._clear_mob_preview()
            return
        entry = config.mob_templates[sel[0]]
        bgr = mob_template_store.load_template_bgr(entry)
        if bgr is None:
            self._clear_mob_preview()
            return
        h, w = bgr.shape[:2]
        self._show_mob_preview_bgr(bgr, f"{entry.get('name', '?')} — {w}×{h} px")

    def _build_mob_filter_section(self, parent):
        def _test_btn(title_row):
            self._btn(title_row, 'Test match', self._test_mob_match,
                      width=96, secondary=True).pack(side='right')

        card = self._card(parent, 'Mob filter (CV)', title_extra=_test_btn)

        self.mob_filter_var = ctk.BooleanVar(value=config.mob_filter_enabled)
        self._chk(card, 'Enable mob filter', self.mob_filter_var,
                  self._apply_live_config).pack(anchor='w', pady=(0, 8))

        row = ctk.CTkFrame(card, fg_color='transparent')
        row.pack(fill='x', pady=(0, 8))
        row.grid_columnconfigure(0, weight=1)
        self.mob_scan_btn = self._btn(
            row, self._mob_scan_button_text(), self._pick_mob_scan_region,
            width=160, secondary=True,
        )
        self.mob_scan_btn.grid(row=0, column=0, sticky='w')
        self._btn(row, 'Learn', self._learn_mob_template, width=72).grid(
            row=0, column=1, sticky='e', padx=(8, 4),
        )
        self._btn(row, 'Remove', self._remove_mob_template, width=80,
                  secondary=True).grid(row=0, column=2, sticky='e')

        body = ctk.CTkFrame(card, fg_color=('gray92', 'gray20'), corner_radius=8)
        body.pack(fill='x')
        inner = ctk.CTkFrame(body, fg_color='transparent')
        inner.pack(fill='x', padx=10, pady=10)

        self.mob_listbox = tk.Listbox(
            inner, height=4, exportselection=False,
            bg='#2b2b2b', fg='white', selectbackground='#1f538d',
            selectforeground='white', highlightthickness=0, bd=0,
            font=('Segoe UI', 11),
        )
        self.mob_listbox.pack(fill='x')
        self.mob_listbox.bind('<<ListboxSelect>>', lambda _e: self._update_mob_preview())

        preview_box = ctk.CTkFrame(
            inner, height=58, corner_radius=6,
            border_width=1, border_color=('gray70', 'gray35'),
            fg_color=('gray88', 'gray14'),
        )
        preview_box.pack(fill='x', pady=(8, 0))
        preview_box.pack_propagate(False)

        self._mob_preview_photo = None
        self.mob_preview_label = tk.Label(
            preview_box, bg='#242424', bd=0, highlightthickness=0,
        )
        self.mob_preview_label.pack(expand=True, fill='both', padx=6, pady=4)
        self.mob_preview_caption = ctk.CTkLabel(
            inner, text='No template selected', font=self.font_cap,
            text_color=('gray35', 'gray65'), anchor='w',
        )
        self.mob_preview_caption.pack(fill='x', pady=(4, 0))

        ctk.CTkLabel(
            card,
            text='Learn captures the scan region. Skills and attack only run when a listed mob matches.',
            font=self.font_cap, text_color=('gray40', 'gray60'), anchor='w',
        ).pack(fill='x', pady=(6, 0))

        self._refresh_mob_list()

    def _pick_mob_scan_region(self):
        if not config.connected_window:
            messagebox.showwarning('Region', 'Connect to the game window first.')
            return
        hwnd = config.connected_window.handle

        def on_done(x, y, w, h):
            config.mob_scan_area.update({'x': x, 'y': y, 'width': w, 'height': h})
            self._refresh_mob_scan_btn()
            mob_filter.invalidate_cache()

        region_picker.pick_region(
            self.root, hwnd, 'Drag mob nameplate scan area · ESC to cancel',
            on_done, on_cancel=lambda: None,
        )

    def _learn_mob_template(self):
        if not config.connected_window:
            messagebox.showwarning('Learn', 'Connect to the game window first.')
            return
        if not config.bar_area_configured(config.mob_scan_area):
            messagebox.showwarning(
                'Learn',
                'Select the mob scan region first, then target the mob you want to learn.',
            )
            return
        self.status_var.set('Switch to game, target mob, capturing in 2s…')
        self.root.after(2000, self._capture_mob_template)

    def _capture_mob_template(self):
        hwnd = window_utils.resolve_hwnd()
        if not hwnd:
            messagebox.showerror('Learn', 'Could not get game window handle.')
            self._set_running_ui(config.bot_running)
            return
        bgr = mob_filter.capture_scan_area(hwnd)
        if bgr is None or bgr.size == 0:
            self._flash_status('Learn failed — could not capture scan region', ok=False)
            return
        h, w = bgr.shape[:2]
        entry = mob_template_store.add_template(bgr)
        mob_filter.invalidate_cache()
        new_idx = len(config.mob_templates) - 1
        self._refresh_mob_list(select_index=new_idx)
        self._show_mob_preview_bgr(bgr, f"Captured {entry['name']} — {w}×{h} px")
        self._flash_status(f"Learned {entry['name']} ({w}×{h})", ok=True, ms=4000)

    def _remove_mob_template(self):
        sel = self.mob_listbox.curselection()
        if not sel:
            messagebox.showinfo('Remove', 'Select a monster from the list first.')
            return
        entry = config.mob_templates[sel[0]]
        mob_template_store.remove_template(entry.get('id'))
        mob_filter.invalidate_cache()
        self._refresh_mob_list()

    def _test_mob_match(self):
        if not config.connected_window:
            self._flash_status('Connect to the game window first', ok=False)
            return
        hwnd = window_utils.resolve_hwnd()
        if not hwnd:
            self._flash_status('Could not get game window handle', ok=False)
            return
        result = mob_filter.probe(int(hwnd))
        if result.get('error'):
            self._flash_status(result['error'], ok=False)
            return
        match = result.get('match')
        if match:
            self._flash_status(
                f"Match: {match['name']} ({match['confidence']:.0%})",
                ok=True,
                ms=4000,
            )
        else:
            self._flash_status(
                f"No match — best: {result['best_name']} "
                f"{result['best_score']:.0%} (need {result['threshold']:.0%})",
                ok=False,
                ms=5000,
            )

    def _build_potions_section(self, parent):
        """Auto HP/MP: two side-by-side panels, pack-only layout."""
        def _test_btn(title_row):
            self._btn(title_row, 'Test bars', self._test_bars, width=96, secondary=True).pack(side='right')

        pot_card = self._card(parent, 'Auto potions', title_extra=_test_btn)

        row = ctk.CTkFrame(pot_card, fg_color='transparent')
        row.pack(fill='x')
        row.grid_columnconfigure(0, weight=1, uniform='pot', minsize=POT_MIN_COL)
        row.grid_columnconfigure(1, weight=1, uniform='pot', minsize=POT_MIN_COL)
        row.grid_rowconfigure(0, weight=1)

        # --- HP panel (red accent) ---
        hp_body = self._pot_subpanel(
            row, 'Health (HP)', accent_border=('#e74c3c', '#c0392b'), grid_col=0,
        )

        self.auto_hp_var = ctk.BooleanVar(value=config.auto_hp_enabled)
        self.hp_pick_btn, self.hp_live_label = self._pot_panel_header(
            hp_body, self.auto_hp_var, 'Enable auto HP', 'Pick HP bar',
            lambda: self._pick_bar('hp'), 'hp', self.hp_status_var,
            ('#c0392b', '#e74c3c'),
        )

        ctk.CTkLabel(
            hp_body, text='Press pot key when HP is at or below:',
            font=self.font_sm, anchor='w',
        ).pack(fill='x', pady=(0, 6))

        self.hp_threshold_frame = ctk.CTkFrame(hp_body, fg_color='transparent')
        self.hp_threshold_frame.pack(fill='x')
        self.hp_rows = []
        self._rebuild_hp_threshold_rows()

        self._btn(hp_body, '+ Add HP rule', self._add_hp_threshold,
                  width=120, secondary=True).pack(anchor='w', pady=(6, 0))

        # --- MP panel (blue accent) ---
        mp_body = self._pot_subpanel(
            row, 'Mana (MP)', accent_border=('#3498db', '#2980b9'), grid_col=1,
        )

        self.auto_mp_var = ctk.BooleanVar(value=config.auto_mp_enabled)
        self.mp_pick_btn, self.mp_live_label = self._pot_panel_header(
            mp_body, self.auto_mp_var, 'Enable auto MP', 'Pick MP bar',
            lambda: self._pick_bar('mp'), 'mp', self.mp_status_var,
            ('#2471a3', '#5dade2'),
        )

        ctk.CTkLabel(
            mp_body, text='Press pot key when MP is at or below:',
            font=self.font_sm, anchor='w',
        ).pack(fill='x', pady=(0, 6))

        self.mp_threshold_var = ctk.StringVar(value=str(config.mp_threshold))
        self.mp_key_var = ctk.StringVar(value=config.mp_key)
        self._pot_rule_row(mp_body, 'MP %', self.mp_threshold_var, self.mp_key_var)

    def _build_skills_section(self, parent):
        sk_card = self._card(parent, 'Skill intervals')

        grid_wrap = ctk.CTkFrame(sk_card, fg_color='transparent')
        grid_wrap.pack(fill='x', expand=True)
        for c in range(4):
            grid_wrap.columnconfigure(c, weight=1, uniform='skillcol')

        for col_idx, slots in enumerate(SKILL_COLUMNS):
            col = ctk.CTkFrame(
                grid_wrap, corner_radius=8, fg_color=('gray92', 'gray20'),
            )
            col.grid(
                row=0, column=col_idx, sticky='nsew',
                padx=(0 if col_idx == 0 else SKILL_COL_GAP, 0),
            )
            inner = ctk.CTkFrame(col, fg_color='transparent')
            inner.pack(fill='x', padx=8, pady=8)

            ctk.CTkLabel(inner, text=COL_TITLES[col_idx], font=self.font_key).pack(
                anchor='w', pady=(0, 4),
            )

            for slot in slots:
                row = ctk.CTkFrame(inner, fg_color='transparent')
                row.pack(fill='x', pady=2)
                label = str(slot).upper() if isinstance(slot, str) else str(slot)
                ctk.CTkLabel(
                    row, text=label, font=self.font_sm, width=SKILL_KEY_W, anchor='w',
                ).pack(side='left')
                enabled_var = ctk.BooleanVar(value=config.skill_slots[slot]['enabled'])
                interval_var = ctk.StringVar(value=str(config.skill_slots[slot]['interval']))
                ctk.CTkCheckBox(
                    row, text='', variable=enabled_var,
                    checkbox_width=CHK, checkbox_height=CHK, width=28,
                ).pack(side='left', padx=(4, 4))
                self._entry(row, interval_var, width=SKILL_ENTRY_W).pack(side='left', fill='x', expand=True)
                self.skill_vars[slot] = (enabled_var, interval_var)

    def _build_ui(self):
        # --- Footer (pinned to bottom, built first so it always stays visible) ---
        foot = ctk.CTkFrame(self.root, fg_color='transparent')
        foot.pack(side='bottom', fill='x', padx=PAD_X, pady=(4, PAD_Y))
        self.status_dot = ctk.CTkLabel(foot, text='●', font=self.font_body,
                                       text_color=('gray60', 'gray50'))
        self.status_dot.pack(side='left', padx=(0, 4))
        self.status_label = ctk.CTkLabel(foot, textvariable=self.status_var, font=self.font_body)
        self.status_label.pack(side='left')
        self.start_btn = self._btn(foot, 'Start', self._toggle_bot, width=120)
        self.start_btn.pack(side='right', padx=(8, 0))
        self._btn(foot, 'Save', self._save, width=88, secondary=True).pack(side='right', padx=(8, 0))

        # --- Scrollable body so content is never clipped ---
        scroll = ctk.CTkScrollableFrame(self.root, fg_color='transparent')
        scroll.pack(side='top', fill='both', expand=True, padx=2, pady=(PAD_Y, 0))
        main = ctk.CTkFrame(scroll, fg_color='transparent')
        main.pack(fill='both', expand=True, padx=PAD_X, pady=0)

        # --- Game window ---
        win_card = self._card(main, 'Game window')
        win_row = ctk.CTkFrame(win_card, fg_color='transparent')
        win_row.pack(fill='x')
        self.window_menu = ctk.CTkOptionMenu(
            win_row, variable=self.window_var, values=[''],
            height=BTN_H, font=self.font_sm, corner_radius=8,
            dynamic_resizing=False,
        )
        self.window_menu.pack(side='left', fill='x', expand=True, padx=(0, 8))
        self._btn(win_row, 'Refresh', self._refresh_windows, width=88, secondary=True).pack(side='left', padx=(0, 8))
        self._btn(win_row, 'Connect', self._connect, width=100).pack(side='left')

        # --- Actions ---
        act_card = self._card(main, 'Actions')
        act_grid = ctk.CTkFrame(act_card, fg_color='transparent')
        act_grid.pack(fill='x')
        for c in range(3):
            act_grid.columnconfigure(c, weight=1, uniform='act')

        for col, (name, slot) in enumerate(config.action_slots.items()):
            cell = ctk.CTkFrame(act_grid, corner_radius=8, fg_color=('gray92', 'gray20'))
            cell.grid(
                row=0, column=col, sticky='nsew',
                padx=(0 if col == 0 else ACT_COL_GAP, 0), pady=2,
            )
            inner = ctk.CTkFrame(cell, fg_color='transparent')
            inner.pack(fill='x', padx=ACT_CELL_PAD, pady=10)

            key = slot['key'].upper()
            ctk.CTkLabel(inner, text=f"{slot['label']}  ({key})",
                         font=self.font_body, anchor='w').pack(fill='x')

            row = ctk.CTkFrame(inner, fg_color='transparent')
            row.pack(fill='x', pady=(6, 0))
            en_var = ctk.BooleanVar(value=slot['enabled'])
            int_var = ctk.StringVar(value=str(slot['interval']))
            self._chk(row, 'On', en_var, width=50).pack(side='left')
            interval = ctk.CTkFrame(row, fg_color='transparent')
            interval.pack(side='left', padx=(2, 0))
            self._entry(interval, int_var, width=ACTION_ENTRY_W).pack(side='left')
            ctk.CTkLabel(interval, text='sec', font=self.font_sm, anchor='w').pack(
                side='left', padx=(2, 0),
            )
            self.action_vars[name] = (en_var, int_var)

        self._build_mob_filter_section(main)
        self._build_potions_section(main)
        self._build_skills_section(main)

    def _refresh_region_labels(self):
        self.hp_pick_btn.configure(text=self._pot_pick_button_text('hp', 'Pick HP bar'))
        self.mp_pick_btn.configure(text=self._pot_pick_button_text('mp', 'Pick MP bar'))

    def _set_live_pct_labels(self, hp=None, mp=None):
        if hp is not None:
            self.hp_status_var.set(f'Live {hp:.0f}%')
        if mp is not None:
            self.mp_status_var.set(f'Live {mp:.0f}%')

    def _refresh_windows(self):
        wins = window_utils.get_open_windows()
        titles = [t for _, t in wins] or ['']
        self.window_menu.configure(values=titles)
        if config.selected_window and config.selected_window in titles:
            self.window_var.set(config.selected_window)
        elif titles[0]:
            self.window_var.set(titles[0])

    def _connect(self):
        title = self.window_var.get()
        if not title:
            messagebox.showwarning('Connect', 'Select a window first.')
            return
        win = window_utils.connect_to_window(title)
        config.connected_window = win
        config.selected_window = title if win else None
        if win:
            self.status_var.set('Connected')
        else:
            messagebox.showerror('Connect', f'Could not connect to:\n{title}')

    def _pick_bar(self, kind):
        if not config.connected_window:
            messagebox.showwarning('Region', 'Connect to the game window first.')
            return
        hwnd = config.connected_window.handle
        label = 'HP' if kind == 'hp' else 'MP'

        def on_done(x, y, w, h):
            area = config.hp_bar_area if kind == 'hp' else config.mp_bar_area
            area.update({'x': x, 'y': y, 'width': w, 'height': h})
            self._refresh_region_labels()

        region_picker.pick_region(
            self.root, hwnd, f'Drag to select {label} bar · ESC to cancel',
            on_done, on_cancel=lambda: None,
        )

    def _rebuild_hp_threshold_rows(self):
        for w in self.hp_threshold_frame.winfo_children():
            w.destroy()
        self.hp_rows = []
        for i, row in enumerate(config.hp_thresholds):
            self._add_hp_row_ui(i, row.get('threshold', 70), row.get('key', '0'))
        if self._live_config_ready:
            self._wire_hp_row_vars()

    def _add_hp_row_ui(self, index, threshold, key):
        th_var = ctk.StringVar(value=str(threshold))
        key_var = ctk.StringVar(value=str(key))

        def remove(idx=index):
            if 0 <= idx < len(config.hp_thresholds):
                config.hp_thresholds.pop(idx)
            self._rebuild_hp_threshold_rows()

        show_remove = len(config.hp_thresholds) > 1
        self._pot_rule_row(
            self.hp_threshold_frame, 'HP %', th_var, key_var,
            on_remove=remove if show_remove else None,
        )
        self.hp_rows.append((th_var, key_var))

    def _add_hp_threshold(self):
        self._apply_hp_rows_to_config()
        config.hp_thresholds.append({'threshold': 50, 'key': '9'})
        self._rebuild_hp_threshold_rows()

    def _apply_hp_rows_to_config(self):
        rows = []
        for th_var, key_var in self.hp_rows:
            try:
                th = int(th_var.get())
            except ValueError:
                th = 70
            rows.append({'threshold': th, 'key': key_var.get().strip() or '0'})
        config.hp_thresholds = sorted(rows, key=lambda x: x['threshold'], reverse=True)

    def _apply_actions_from_ui(self):
        for name, (en_var, int_var) in self.action_vars.items():
            try:
                interval = float(int_var.get())
            except ValueError:
                interval = 1.0
            config.action_slots[name]['enabled'] = en_var.get()
            config.action_slots[name]['interval'] = max(0.1, interval)

    def _apply_skills_from_ui(self):
        for slot, (en_var, int_var) in self.skill_vars.items():
            try:
                interval = float(int_var.get())
            except ValueError:
                interval = 1.0
            config.skill_slots[slot]['enabled'] = en_var.get()
            config.skill_slots[slot]['interval'] = max(0.1, interval)

    def _apply_mob_from_ui(self):
        config.mob_filter_enabled = self.mob_filter_var.get()

    def _apply_pots_from_ui(self):
        config.auto_hp_enabled = self.auto_hp_var.get()
        config.auto_mp_enabled = self.auto_mp_var.get()
        self._apply_hp_rows_to_config()
        try:
            config.mp_threshold = int(self.mp_threshold_var.get())
        except ValueError:
            config.mp_threshold = 50
        config.mp_key = self.mp_key_var.get().strip() or '9'

    def _apply_live_config(self, *_args):
        """Push UI values into in-memory config (no disk write)."""
        if self._syncing_ui:
            return
        self._pull_ui_to_config()

    def _track_live(self, var):
        key = id(var)
        if key in self._tracked_var_ids:
            return
        self._tracked_var_ids.add(key)
        var.trace_add('write', self._apply_live_config)

    def _wire_live_config(self):
        self._track_live(self.auto_hp_var)
        self._track_live(self.auto_mp_var)
        self._track_live(self.mob_filter_var)
        self._track_live(self.mp_threshold_var)
        self._track_live(self.mp_key_var)
        for en_var, int_var in self.action_vars.values():
            self._track_live(en_var)
            self._track_live(int_var)
        for en_var, int_var in self.skill_vars.values():
            self._track_live(en_var)
            self._track_live(int_var)
        self._wire_hp_row_vars()

    def _wire_hp_row_vars(self):
        for th_var, key_var in self.hp_rows:
            self._track_live(th_var)
            self._track_live(key_var)

    def _sync_ui_from_config(self):
        self._syncing_ui = True
        try:
            self.auto_hp_var.set(config.auto_hp_enabled)
            self.auto_mp_var.set(config.auto_mp_enabled)
            self.mob_filter_var.set(config.mob_filter_enabled)
            self._refresh_mob_scan_btn()
            self._refresh_mob_list()
            self.mp_threshold_var.set(str(config.mp_threshold))
            self.mp_key_var.set(config.mp_key)
            self._refresh_region_labels()
            self._rebuild_hp_threshold_rows()
            for name, (en_var, int_var) in self.action_vars.items():
                en_var.set(config.action_slots[name]['enabled'])
                int_var.set(str(config.action_slots[name]['interval']))
            for slot, (en_var, int_var) in self.skill_vars.items():
                en_var.set(config.skill_slots[slot]['enabled'])
                int_var.set(str(config.skill_slots[slot]['interval']))
            if config.selected_window:
                self.window_var.set(config.selected_window)
        finally:
            self._syncing_ui = False

    def _pull_ui_to_config(self):
        self._apply_mob_from_ui()
        self._apply_pots_from_ui()
        self._apply_actions_from_ui()
        self._apply_skills_from_ui()

    def _save(self, silent=False):
        self._pull_ui_to_config()
        ok = settings_manager.save_settings()
        if not silent:
            self._flash_status('Settings saved' if ok else 'Save failed', ok=ok)
        return ok

    def _flash_status(self, message, ok=True, ms=2500):
        if self._save_notice_after_id is not None:
            self.root.after_cancel(self._save_notice_after_id)
        color = ('#1e8449', '#58d68d') if ok else ('#c0392b', '#e74c3c')
        dot_color = '#2ecc71' if ok else '#e74c3c'
        self.status_var.set(message)
        self.status_label.configure(text_color=color)
        self.status_dot.configure(text_color=dot_color)
        self._save_notice_after_id = self.root.after(ms, self._clear_save_notice)

    def _clear_save_notice(self):
        self._save_notice_after_id = None
        self._set_running_ui(config.bot_running)

    def _test_bars(self):
        if not config.connected_window:
            messagebox.showwarning('Test', 'Connect to the game window first.')
            return
        hwnd = config.connected_window.handle
        hp, mp = bar_reader.read_hp_mp(hwnd)
        hp_txt = f'{hp:.0f}%' if hp is not None else '—'
        mp_txt = f'{mp:.0f}%' if mp is not None else '—'
        if hp is not None:
            self._set_live_pct_labels(hp=hp)
        if mp is not None:
            self._set_live_pct_labels(mp=mp)
        messagebox.showinfo('Bar test', f'HP: {hp_txt}\nMP: {mp_txt}')

    def _set_running_ui(self, running):
        if running:
            self.start_btn.configure(text='Stop', fg_color='#c0392b', hover_color='#a93226')
            self.status_var.set('Running')
            self.status_label.configure(text_color=('#1e8449', '#58d68d'))
            self.status_dot.configure(text_color='#2ecc71')
        else:
            self.start_btn.configure(text='Start', fg_color=ctk.ThemeManager.theme['CTkButton']['fg_color'],
                                     hover_color=ctk.ThemeManager.theme['CTkButton']['hover_color'])
            self.status_var.set('Stopped')
            self.status_label.configure(text_color=('gray20', 'gray90'))
            self.status_dot.configure(text_color=('gray60', 'gray50'))

    def _toggle_bot(self):
        if config.bot_running:
            bot_loop.stop()
            self._set_running_ui(False)
            return
        if not config.connected_window:
            messagebox.showwarning('Bot', 'Connect to the game window first.')
            return
        self._pull_ui_to_config()
        bot_loop.start()
        self._set_running_ui(True)

    def _tick_status(self):
        if config.connected_window and (
            config.bar_area_configured(config.hp_bar_area)
            or config.bar_area_configured(config.mp_bar_area)
        ):
            try:
                hwnd = config.connected_window.handle
                hp, mp = bar_reader.read_hp_mp(hwnd)
                if hp is not None:
                    config.current_hp_percentage = hp
                    self._set_live_pct_labels(hp=hp)
                if mp is not None:
                    config.current_mp_percentage = mp
                    self._set_live_pct_labels(mp=mp)
            except Exception:
                pass
        self.root.after(800, self._tick_status)

    def run(self):
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)
        self.root.mainloop()

    def _on_close(self):
        bot_loop.stop()
        self._save(silent=True)
        self.root.destroy()


def create_gui():
    return LiteGUI()
