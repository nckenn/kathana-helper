"""Manual region picking panel for the main GUI."""
import customtkinter as ctk
import config
import region_picker
import region_helpers
import settings_manager


REGION_ROWS = (
    ('hp_bar_area', 'HP Bar', True, 'Drag to select HP bar · ESC to cancel'),
    ('mp_bar_area', 'MP Bar', True, 'Drag to select MP bar · ESC to cancel'),
    ('target_name_area', 'Enemy Name', False,
     'Drag the full enemy name/level bar (include all text) · ESC to cancel'),
    ('target_hp_bar_area', 'Enemy HP', False, 'Drag enemy HP bar · ESC to cancel'),
    ('system_message_area', 'System Message', False,
     'Drag system message / chat area · ESC to cancel'),
    ('skill_area', 'Skill Area', False, 'Drag skill hotbar area · ESC to cancel'),
    ('buff_area', 'Buff Area', False, 'Drag active buff icons strip · ESC to cancel'),
)

_LABEL_W = 120
_STATUS_W = 200
_PICK_W = 56
_CLEAR_W = 28
_ROW_PADY = 3
_STATUS_UNSET = ('gray45', 'gray55')


def build_regions_panel(parent, gui):
    """Create the Regions tab content; stores pick buttons on gui.region_pick_buttons."""
    scroll = ctk.CTkScrollableFrame(parent)
    scroll.pack(fill='both', expand=True)

    info = ctk.CTkFrame(
        scroll, corner_radius=6, fg_color=('gray18', 'gray14'),
        border_width=1, border_color='gray25',
    )
    info.pack(fill='x', padx=10, pady=(10, 12))
    ctk.CTkLabel(
        info,
        text='Connect to the game window, then drag-select each UI region.\n'
             'HP + MP are required to start the bot. Regions are saved with your settings.',
        font=ctk.CTkFont(size=12),
        justify='left',
        anchor='w',
    ).pack(anchor='w', padx=10, pady=10)

    gui.region_pick_buttons = {}
    gui.region_status_labels = {}
    gui.region_clear_buttons = {}

    table = ctk.CTkFrame(scroll, fg_color='transparent')
    table.pack(fill='x', padx=10, pady=(0, 8))
    table.grid_columnconfigure(0, minsize=_LABEL_W, weight=0)
    table.grid_columnconfigure(1, minsize=_STATUS_W, weight=0)
    table.grid_columnconfigure(2, minsize=_PICK_W, weight=0)
    table.grid_columnconfigure(3, minsize=_CLEAR_W, weight=0)

    for row_idx, (key, label, required, instruction) in enumerate(REGION_ROWS):
        title = f'{label} *' if required else label
        ctk.CTkLabel(
            table, text=title, width=_LABEL_W, anchor='w',
            font=ctk.CTkFont(size=11, weight='bold'),
        ).grid(row=row_idx, column=0, sticky='w', padx=(0, 8), pady=_ROW_PADY)

        area = getattr(config, key)
        configured = config.bar_area_configured(area)
        status = region_helpers.region_status_text(area)

        status_lbl = ctk.CTkLabel(
            table,
            text=status,
            width=_STATUS_W,
            anchor='w',
            font=ctk.CTkFont(size=11, family='Consolas' if configured else None),
            text_color=('green', '#6ecf6e') if configured else _STATUS_UNSET,
        )
        status_lbl.grid(row=row_idx, column=1, sticky='w', pady=_ROW_PADY)
        gui.region_status_labels[key] = status_lbl

        pick_btn = ctk.CTkButton(
            table,
            text='Pick',
            width=_PICK_W,
            height=28,
            command=lambda k=key, ins=instruction: _pick_region(gui, k, ins),
            font=ctk.CTkFont(size=11),
        )
        pick_btn.grid(row=row_idx, column=2, sticky='w', padx=(6, 4), pady=_ROW_PADY)
        gui.region_pick_buttons[key] = pick_btn

        clear_btn = ctk.CTkButton(
            table,
            text='×',
            width=_CLEAR_W,
            height=28,
            command=lambda k=key: _clear_region(gui, k),
            font=ctk.CTkFont(size=16),
            fg_color=('gray75', 'gray30'),
            hover_color=('gray65', 'gray40'),
            state='normal' if configured else 'disabled',
        )
        clear_btn.grid(row=row_idx, column=3, sticky='w', pady=_ROW_PADY)
        gui.region_clear_buttons[key] = clear_btn

        _bind_region_tooltip(gui, pick_btn, instruction)
        _bind_region_tooltip(gui, clear_btn, 'Clear this region')

    gui.refresh_region_pick_labels = lambda: _refresh_labels(gui)


def _bind_region_tooltip(gui, widget, text):
    try:
        from gui import create_tooltip
        create_tooltip(widget, text)
    except ImportError:
        pass


def _refresh_labels(gui):
    for key in getattr(gui, 'region_pick_buttons', {}):
        area = getattr(config, key)
        configured = config.bar_area_configured(area)
        status = region_helpers.region_status_text(area)
        status_lbl = gui.region_status_labels.get(key)
        if status_lbl is not None:
            status_lbl.configure(
                text=status,
                text_color=('green', '#6ecf6e') if configured else _STATUS_UNSET,
                font=ctk.CTkFont(size=11, family='Consolas' if configured else None),
            )
        clear_btn = gui.region_clear_buttons.get(key)
        if clear_btn is not None:
            clear_btn.configure(state='normal' if configured else 'disabled')
    if hasattr(gui, 'update_toggle_bot_button_state'):
        gui.update_toggle_bot_button_state()
    if hasattr(gui, 'update_mob_filter_ui_state'):
        gui.update_mob_filter_ui_state()


def _clear_region(gui, config_key):
    area = getattr(config, config_key)
    if not config.bar_area_configured(area):
        return
    region_helpers.clear_area(area)
    if config_key == 'target_name_area':
        region_helpers.clear_area(config.mob_scan_area)
        try:
            import mob_filter
            import frame_cache
            mob_filter.invalidate_cache()
            frame_cache.invalidate()
        except ImportError:
            pass
    if config_key == 'skill_area':
        config.area_skills = None
        region_helpers.sync_skill_area_tuple()
    _refresh_labels(gui)
    settings_manager.save_settings()
    print(f'[Regions] {config_key} cleared')


def _pick_region(gui, config_key, instruction):
    from tkinter import messagebox
    if not config.connected_window:
        messagebox.showwarning('No Window', 'Please connect to a game window first!')
        return
    hwnd = config.connected_window.handle
    area = getattr(config, config_key)

    def on_complete(x, y, width, height):
        region_helpers.apply_area_dict(area, x, y, width, height)
        if config_key == 'target_name_area':
            region_helpers.sync_mob_scan_from_enemy_name()
            try:
                import mob_filter
                import frame_cache
                mob_filter.invalidate_cache()
                frame_cache.invalidate()
            except ImportError:
                pass
        if config_key == 'skill_area':
            region_helpers.sync_skill_area_tuple()
        _refresh_labels(gui)
        settings_manager.save_settings()
        print(f'[Regions] {config_key} set to ({x}, {y}, {width}x{height})')

    region_picker.pick_region(gui.root, hwnd, instruction, on_complete)
