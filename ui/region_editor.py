"""Visual region editor — capture game window and draw/move colored regions."""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

import config
import region_helpers
import window_utils

try:
    import cv2
    from PIL import Image, ImageTk
    CV_AVAILABLE = True
except ImportError:
    CV_AVAILABLE = False

# (config_key, label, required, hex color)
REGION_DEFS = (
    ('hp_bar_area', 'HP Bar', True, '#e74c3c'),
    ('mp_bar_area', 'MP Bar', True, '#3498db'),
    ('target_name_area', 'Enemy Name', False, '#2ecc71'),
    ('target_hp_bar_area', 'Enemy HP', False, '#9b59b6'),
    ('system_message_area', 'System Message', False, '#f39c12'),
    ('skill_area', 'Skill Bar', False, '#1abc9c'),
    ('buff_area', 'Buff Strip', False, '#e91e63'),
)

HANDLE_SIZE = 7
MIN_W, MIN_H = 10, 5
ZOOM_MIN = 0.5
ZOOM_MAX = 3.0
ZOOM_STEP = 0.1
DEFAULT_ZOOM = 1.0
ARROW_NUDGE = 1
ARROW_NUDGE_SHIFT = 8

_CORNER_CURSORS = {
    'nw': 'top_left_corner',
    'ne': 'top_right_corner',
    'sw': 'bottom_left_corner',
    'se': 'bottom_right_corner',
}


def _copy_area(area):
    return {
        'x': int(area.get('x', 0)),
        'y': int(area.get('y', 0)),
        'width': int(area.get('width', 0)),
        'height': int(area.get('height', 0)),
    }


class RegionEditorWindow:
    """Popup editor: frozen window capture + colored, movable region rectangles."""

    def __init__(self, parent, gui):
        self.gui = gui
        self.parent = parent
        self._areas = {key: _copy_area(getattr(config, key)) for key, *_ in REGION_DEFS}
        self._selected_key = REGION_DEFS[0][0]
        self._photo = None
        self._bgr = None
        self._zoom = DEFAULT_ZOOM
        self._img_w = 0
        self._img_h = 0

        self._drag_mode = None
        self._resize_corner = None
        self._drag_start = None
        self._move_offset = (0, 0)
        self._preview_id = None
        self._rect_ids = {}
        self._handle_ids = []
        self._hover_region = None

        self.win = ctk.CTkToplevel(parent)
        self.win.title('Region Editor')
        self.win.geometry('1220x820')
        self.win.minsize(960, 620)
        self.win.transient(parent)
        self.win.grab_set()

        self._build_ui()
        self.win.protocol('WM_DELETE_WINDOW', self._on_cancel)
        self._raise_editor()
        self._set_status('Capturing game window… (editor stays on top)')
        threading.Thread(target=self._capture_worker, daemon=True).start()

    def _raise_editor(self):
        """Keep the editor above the game after capture."""
        try:
            self.win.deiconify()
            self.win.lift()
            self.win.focus_force()
            self.win.attributes('-topmost', True)
            self.win.after(400, lambda: self.win.attributes('-topmost', False))
        except Exception:
            pass

    def _build_ui(self):
        top = ctk.CTkFrame(self.win, fg_color='transparent')
        top.pack(fill='x', padx=12, pady=(12, 6))

        ctk.CTkLabel(
            top,
            text='Click any row in the list or draw on the image. Arrow keys nudge the selected box '
                 '(Shift = faster). Up/Down with no box selected changes list selection.',
            font=ctk.CTkFont(size=12),
            anchor='w',
            wraplength=720,
            justify='left',
        ).pack(side='left', fill='x', expand=True)

        btn_row = ctk.CTkFrame(top, fg_color='transparent')
        btn_row.pack(side='right')
        ctk.CTkButton(
            btn_row, text='Refresh Capture', width=120,
            command=self._refresh_capture,
        ).pack(side='left', padx=4)
        ctk.CTkButton(
            btn_row, text='Save', width=80, fg_color='#2d6a4f',
            command=self._on_save,
        ).pack(side='left', padx=4)
        ctk.CTkButton(
            btn_row, text='Cancel', width=80, fg_color=('gray70', 'gray35'),
            command=self._on_cancel,
        ).pack(side='left', padx=4)

        zoom_row = ctk.CTkFrame(self.win, fg_color='transparent')
        zoom_row.pack(fill='x', padx=12, pady=(0, 6))
        ctk.CTkButton(zoom_row, text='−', width=36, command=self._zoom_out).pack(side='left')
        self._zoom_label = ctk.CTkLabel(zoom_row, text='100%', width=64, font=ctk.CTkFont(size=12))
        self._zoom_label.pack(side='left', padx=4)
        ctk.CTkButton(zoom_row, text='+', width=36, command=self._zoom_in).pack(side='left')
        ctk.CTkButton(zoom_row, text='Fit', width=48, command=self._zoom_fit).pack(side='left', padx=(8, 0))
        ctk.CTkButton(zoom_row, text='100%', width=48, command=self._zoom_reset).pack(side='left', padx=4)

        body = ctk.CTkFrame(self.win, fg_color='transparent')
        body.pack(fill='both', expand=True, padx=12, pady=(0, 12))

        sidebar = ctk.CTkScrollableFrame(body, width=240, label_text='Regions — click a row')
        sidebar.pack(side='left', fill='y', padx=(0, 10))

        self._region_rows = {}
        for key, label, required, color in REGION_DEFS:
            title = f'{label} *' if required else label

            row = ctk.CTkFrame(sidebar, fg_color='transparent')
            row.pack(fill='x', pady=2, padx=2)

            card = ctk.CTkFrame(row, corner_radius=6, fg_color=('gray92', 'gray22'))
            card.pack(side='left', fill='x', expand=True)

            inner = ctk.CTkFrame(card, fg_color='transparent')
            inner.pack(fill='x', padx=4, pady=4)

            swatch = tk.Canvas(inner, width=14, height=14, highlightthickness=0, bd=0, cursor='hand2')
            swatch.pack(side='left', padx=(2, 6))
            swatch_id = swatch.create_rectangle(1, 1, 13, 13, fill=color, outline=color)

            text_col = ctk.CTkFrame(inner, fg_color='transparent')
            text_col.pack(side='left', fill='x', expand=True)

            name_lbl = ctk.CTkLabel(
                text_col,
                text=title,
                anchor='w',
                font=ctk.CTkFont(size=11, weight='bold'),
                text_color=('gray10', 'gray90'),
            )
            name_lbl.pack(fill='x', anchor='w')

            status_lbl = ctk.CTkLabel(
                text_col,
                text='○ Not set',
                anchor='w',
                font=ctk.CTkFont(size=10),
                text_color=('gray50', 'gray55'),
            )
            status_lbl.pack(fill='x', anchor='w')

            clr = ctk.CTkButton(
                row, text='×', width=28, height=28,
                fg_color=('gray75', 'gray30'),
                hover_color=('gray65', 'gray40'),
                state='disabled',
                command=lambda k=key: self._clear_region(k),
            )
            clr.pack(side='right', padx=(4, 0))

            for widget in (card, inner, swatch, text_col, name_lbl, status_lbl):
                self._bind_row_select(widget, key)

            self._region_rows[key] = {
                'row': row,
                'card': card,
                'name': name_lbl,
                'status': status_lbl,
                'clear': clr,
                'swatch': swatch,
                'swatch_id': swatch_id,
                'color': color,
                'label': title,
            }

        self._canvas_outer = ctk.CTkFrame(body, fg_color=('gray92', 'gray18'))
        self._canvas_outer.pack(side='left', fill='both', expand=True)

        scroll_wrap = tk.Frame(self._canvas_outer, bg='#1a1a1a')
        scroll_wrap.pack(fill='both', expand=True, padx=4, pady=4)
        scroll_wrap.grid_rowconfigure(0, weight=1)
        scroll_wrap.grid_columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(
            scroll_wrap, bg='#1a1a1a', highlightthickness=0, bd=0, cursor='crosshair',
        )
        vbar = tk.Scrollbar(scroll_wrap, orient='vertical', command=self._canvas.yview)
        hbar = tk.Scrollbar(scroll_wrap, orient='horizontal', command=self._canvas.xview)
        self._canvas.configure(xscrollcommand=vbar.set, yscrollcommand=hbar.set)

        self._canvas.grid(row=0, column=0, sticky='nsew')
        vbar.grid(row=0, column=1, sticky='ns')
        hbar.grid(row=1, column=0, sticky='ew')

        self._canvas.bind('<Button-1>', self._on_press)
        self._canvas.bind('<B1-Motion>', self._on_motion)
        self._canvas.bind('<ButtonRelease-1>', self._on_release)
        self._canvas.bind('<Motion>', self._on_hover)
        self._canvas.bind('<Leave>', lambda _e: self._canvas.configure(cursor='crosshair'))
        self._canvas.bind('<Control-MouseWheel>', self._on_wheel_zoom)
        self._canvas.bind('<Control-Button-4>', lambda e: self._zoom_by(ZOOM_STEP))
        self._canvas.bind('<Control-Button-5>', lambda e: self._zoom_by(-ZOOM_STEP))

        self._bind_keyboard()

        self._status = ctk.CTkLabel(
            self.win, text='', font=ctk.CTkFont(size=11),
            text_color=('gray40', 'gray60'), anchor='w',
        )
        self._status.pack(fill='x', padx=14, pady=(0, 10))

        self._refresh_sidebar()

    def _area_is_set(self, key):
        area = self._areas.get(key, {})
        return int(area.get('width', 0)) > 0 and int(area.get('height', 0)) > 0

    def _bind_row_select(self, widget, key):
        def _select(_event=None):
            self._select_region(key)

        widget.bind('<Button-1>', _select)
        try:
            widget.configure(cursor='hand2')
        except (tk.TclError, AttributeError):
            pass

    def _bind_keyboard(self):
        for keysym in ('Up', 'Down', 'Left', 'Right', 'Prior', 'Next'):
            self.win.bind(f'<{keysym}>', self._on_key_nav)
            self._canvas.bind(f'<{keysym}>', self._on_key_nav)
        self.win.bind('<Delete>', self._on_delete_key)
        self._canvas.bind('<Delete>', self._on_delete_key)
        self._canvas.focus_set()

    def _region_keys(self):
        return [key for key, *_ in REGION_DEFS]

    def _cycle_selection(self, delta):
        keys = self._region_keys()
        idx = keys.index(self._selected_key)
        self._select_region(keys[(idx + delta) % len(keys)])

    def _nudge_selected(self, dx, dy):
        area = self._areas.get(self._selected_key)
        if not area or not self._area_is_set(self._selected_key):
            return
        w, h = area['width'], area['height']
        area['x'] = max(0, min(area['x'] + dx, self._img_w - w))
        area['y'] = max(0, min(area['y'] + dy, self._img_h - h))
        self._redraw_regions()
        self._refresh_sidebar()
        self._set_status(
            f'{self._label_for(self._selected_key)}: ({area["x"]}, {area["y"]}) '
            f'{w}×{h} — arrows to nudge, Shift for larger steps',
        )

    def _on_key_nav(self, event):
        keysym = event.keysym
        if keysym in ('Prior', 'Next'):
            self._cycle_selection(-1 if keysym == 'Prior' else 1)
            return 'break'

        if not self._area_is_set(self._selected_key):
            if keysym == 'Up':
                self._cycle_selection(-1)
                return 'break'
            if keysym == 'Down':
                self._cycle_selection(1)
                return 'break'
            return 'break'

        shift = bool(event.state & 0x0001)
        step = ARROW_NUDGE_SHIFT if shift else ARROW_NUDGE
        dx = dy = 0
        if keysym == 'Left':
            dx = -step
        elif keysym == 'Right':
            dx = step
        elif keysym == 'Up':
            dy = -step
        elif keysym == 'Down':
            dy = step
        else:
            return 'break'

        if event.state & 0x0004 and keysym in ('Up', 'Down'):
            self._cycle_selection(-1 if keysym == 'Up' else 1)
            return 'break'

        self._nudge_selected(dx, dy)
        return 'break'

    def _on_delete_key(self, event):
        if self._area_is_set(self._selected_key):
            self._clear_region(self._selected_key)
        return 'break'

    def _refresh_sidebar(self):
        for key, widgets in self._region_rows.items():
            color = widgets['color']
            is_set = self._area_is_set(key)
            is_selected = key == self._selected_key
            card = widgets['card']
            name = widgets['name']
            status = widgets['status']
            clr = widgets['clear']
            swatch = widgets['swatch']
            swatch_id = widgets['swatch_id']

            if is_set:
                area = self._areas[key]
                status.configure(
                    text=f"✓ {area['width']}×{area['height']} @ ({area['x']}, {area['y']})",
                    text_color=('#1a7f4b', '#6ecf8a'),
                )
                swatch.itemconfigure(swatch_id, fill=color, outline=color)
                clr.configure(state='normal')
            else:
                status.configure(text='○ Not set', text_color=('gray50', 'gray55'))
                swatch.itemconfigure(swatch_id, fill='#555555', outline='#777777')
                clr.configure(state='disabled')

            if is_selected:
                card.configure(
                    fg_color=('gray88', 'gray26'),
                    border_width=2,
                    border_color=color,
                )
                name.configure(text_color=('gray10', 'gray90'))
            elif is_set:
                card.configure(
                    fg_color=('#e8f5e9', '#1e3a2f'),
                    border_width=0,
                )
                name.configure(text_color=('gray10', 'gray90'))
            else:
                card.configure(fg_color=('gray92', 'gray22'), border_width=0)
                name.configure(text_color=('gray45', 'gray60'))

    @property
    def _scale(self):
        return self._zoom

    def _update_zoom_label(self):
        self._zoom_label.configure(text=f'{int(round(self._zoom * 100))}%')

    def _zoom_by(self, delta):
        self._zoom = max(ZOOM_MIN, min(ZOOM_MAX, round(self._zoom + delta, 2)))
        self._update_zoom_label()
        self._render_image()

    def _zoom_in(self):
        self._zoom_by(ZOOM_STEP)

    def _zoom_out(self):
        self._zoom_by(-ZOOM_STEP)

    def _zoom_reset(self):
        self._zoom = DEFAULT_ZOOM
        self._update_zoom_label()
        self._render_image()

    def _zoom_fit(self):
        if self._bgr is None:
            return
        self.win.update_idletasks()
        view_w = max(200, self._canvas_outer.winfo_width() - 24)
        view_h = max(200, self._canvas_outer.winfo_height() - 24)
        fit = min(view_w / max(1, self._img_w), view_h / max(1, self._img_h))
        self._zoom = max(ZOOM_MIN, min(ZOOM_MAX, round(fit, 2)))
        self._update_zoom_label()
        self._render_image()

    def _on_wheel_zoom(self, event):
        delta = ZOOM_STEP if event.delta > 0 else -ZOOM_STEP
        self._zoom_by(delta)

    def _set_status(self, text):
        self._status.configure(text=text)

    def _select_region(self, key):
        self._selected_key = key
        self._redraw_regions()
        self._refresh_sidebar()
        try:
            self._canvas.focus_set()
        except tk.TclError:
            pass

    def _clear_region(self, key):
        if not self._area_is_set(key):
            return
        self._areas[key] = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
        self._redraw_regions()
        self._refresh_sidebar()
        self._set_status(f'Cleared {self._label_for(key)}')

    def _refresh_capture(self):
        self._set_status('Refreshing capture…')
        self._raise_editor()
        threading.Thread(target=self._capture_worker, daemon=True).start()

    def _capture_worker(self):
        if not config.connected_window:
            self.win.after(0, lambda: messagebox.showerror(
                'Region Editor', 'Connect to a game window first.',
            ))
            return
        try:
            hwnd = config.connected_window.handle
            # Do not focus the game — that hides this editor behind the game window.
            bgr, method = window_utils.capture_window_bgr(hwnd)
            if bgr is None or bgr.size == 0:
                self.win.after(0, lambda: self._set_status('Capture failed — try Refresh.'))
                return

            def _done():
                self._apply_capture(bgr, method)
                self._raise_editor()

            self.win.after(0, _done)
        except Exception as exc:
            self.win.after(0, lambda: self._set_status(f'Capture error: {exc}'))

    def _apply_capture(self, bgr, method=''):
        self._bgr = bgr
        self._img_h, self._img_w = bgr.shape[:2]
        if self._zoom == DEFAULT_ZOOM:
            self._zoom = DEFAULT_ZOOM
        self._render_image()
        note = f' ({method})' if method else ''
        self._set_status(
            f'Capture {self._img_w}×{self._img_h}{note} at {int(self._zoom * 100)}% — '
            f'click a list row, draw or drag boxes; arrow keys to nudge.',
        )

    def _render_image(self):
        if self._bgr is None:
            return
        disp_w = max(1, int(self._img_w * self._zoom))
        disp_h = max(1, int(self._img_h * self._zoom))

        rgb = cv2.cvtColor(self._bgr, cv2.COLOR_BGR2RGB)
        if abs(self._zoom - 1.0) > 0.01:
            interp = cv2.INTER_LINEAR if self._zoom > 1.0 else cv2.INTER_AREA
            rgb = cv2.resize(rgb, (disp_w, disp_h), interpolation=interp)
        pil = Image.fromarray(rgb)
        self._photo = ImageTk.PhotoImage(pil)

        self._canvas.delete('all')
        self._canvas.configure(scrollregion=(0, 0, disp_w, disp_h))
        self._canvas.create_image(0, 0, anchor='nw', image=self._photo, tags='bg')
        self._rect_ids.clear()
        self._redraw_regions()
        self._refresh_sidebar()

    def _w2c(self, area):
        if not area or area.get('width', 0) <= 0:
            return None
        s = self._zoom
        return (
            area['x'] * s,
            area['y'] * s,
            area['x'] * s + area['width'] * s,
            area['y'] * s + area['height'] * s,
        )

    def _c2w(self, x1, y1, x2, y2):
        s = self._zoom
        if s <= 0:
            return 0, 0, MIN_W, MIN_H
        left = int(min(x1, x2) / s)
        top = int(min(y1, y2) / s)
        w = max(MIN_W, int(abs(x2 - x1) / s))
        h = max(MIN_H, int(abs(y2 - y1) / s))
        left = max(0, min(left, max(0, self._img_w - w)))
        top = max(0, min(top, max(0, self._img_h - h)))
        return left, top, w, h

    def _color_for(self, key):
        for k, _l, _r, color in REGION_DEFS:
            if k == key:
                return color
        return '#ffffff'

    def _label_for(self, key):
        for k, label, _r, _c in REGION_DEFS:
            if k == key:
                return label
        return key

    def _redraw_regions(self):
        if self._photo is None:
            return
        self._canvas.delete('region')
        self._canvas.delete('region_fill')
        self._canvas.delete('handle')
        self._rect_ids.clear()
        self._handle_ids.clear()
        if self._preview_id:
            self._canvas.delete(self._preview_id)
            self._preview_id = None

        for key, _label, _req, color in REGION_DEFS:
            area = self._areas.get(key)
            box = self._w2c(area)
            if box is None:
                continue
            x1, y1, x2, y2 = box
            self._canvas.create_rectangle(
                x1, y1, x2, y2,
                outline='',
                fill=color,
                stipple='gray50',
                tags=('region_fill', key),
            )
            width = 3 if key == self._selected_key else 2
            rid = self._canvas.create_rectangle(
                x1, y1, x2, y2,
                outline=color,
                width=width,
                tags=('region', key),
            )
            self._rect_ids[key] = rid

        sel = self._areas.get(self._selected_key)
        box = self._w2c(sel)
        if box:
            x1, y1, x2, y2 = box
            color = self._color_for(self._selected_key)
            for cx, cy in ((x1, y1), (x2, y1), (x1, y2), (x2, y2)):
                hid = self._canvas.create_rectangle(
                    cx - HANDLE_SIZE, cy - HANDLE_SIZE,
                    cx + HANDLE_SIZE, cy + HANDLE_SIZE,
                    fill='white', outline=color,
                    width=2, tags='handle',
                )
                self._handle_ids.append(hid)

        self._canvas.tag_raise('region')
        self._canvas.tag_raise('handle')
        self._canvas.tag_lower('region_fill')
        self._canvas.tag_lower('bg')

    def _canvas_pos(self, event):
        return self._canvas.canvasx(event.x), self._canvas.canvasy(event.y)

    def _hit_handle(self, cx, cy):
        sel = self._areas.get(self._selected_key)
        box = self._w2c(sel)
        if not box:
            return None
        x1, y1, x2, y2 = box
        corners = {
            'nw': (x1, y1), 'ne': (x2, y1),
            'sw': (x1, y2), 'se': (x2, y2),
        }
        for name, (hx, hy) in corners.items():
            if abs(cx - hx) <= HANDLE_SIZE + 3 and abs(cy - hy) <= HANDLE_SIZE + 3:
                return name
        return None

    def _hit_region(self, key, cx, cy):
        box = self._w2c(self._areas.get(key))
        if not box:
            return False
        x1, y1, x2, y2 = box
        return x1 <= cx <= x2 and y1 <= cy <= y2

    def _hit_any_region(self, cx, cy):
        """Topmost region under cursor (selected region wins on overlap)."""
        if self._hit_region(self._selected_key, cx, cy):
            return self._selected_key
        for key, _label, _req, _color in reversed(REGION_DEFS):
            if key != self._selected_key and self._hit_region(key, cx, cy):
                return key
        return None

    def _on_hover(self, event):
        if self._drag_mode:
            return
        cx, cy = self._canvas_pos(event)
        corner = self._hit_handle(cx, cy)
        if corner:
            self._canvas.configure(cursor=_CORNER_CURSORS.get(corner, 'crosshair'))
            return

        hit = self._hit_any_region(cx, cy)
        self._hover_region = hit
        if hit:
            self._canvas.configure(cursor='fleur')
            return
        self._canvas.configure(cursor='crosshair')

    def _on_press(self, event):
        if self._photo is None:
            return
        cx, cy = self._canvas_pos(event)

        hit = self._hit_any_region(cx, cy)
        if hit and hit != self._selected_key:
            self._select_region(hit)

        corner = self._hit_handle(cx, cy)
        if corner:
            self._drag_mode = 'resize'
            self._resize_corner = corner
            self._drag_start = (cx, cy)
            self._canvas.configure(cursor=_CORNER_CURSORS.get(corner, 'crosshair'))
            return

        if hit:
            box = self._w2c(self._areas[hit])
            self._drag_mode = 'move'
            self._drag_start = (cx, cy)
            self._move_offset = (cx - box[0], cy - box[1])
            self._canvas.configure(cursor='fleur')
            return

        self._drag_mode = 'draw'
        self._drag_start = (cx, cy)
        self._canvas.configure(cursor='crosshair')

    def _on_motion(self, event):
        cx, cy = self._canvas_pos(event)

        if not self._drag_mode:
            self._on_hover(event)
            return

        if not self._drag_start:
            return

        x0, y0 = self._drag_start

        if self._preview_id:
            self._canvas.delete(self._preview_id)

        color = self._color_for(self._selected_key)

        if self._drag_mode == 'draw':
            self._preview_id = self._canvas.create_rectangle(
                x0, y0, cx, cy, outline=color, width=2, dash=(4, 4),
            )
            return

        area = self._areas[self._selected_key]
        if area.get('width', 0) <= 0:
            return

        if self._drag_mode == 'move':
            s = self._zoom
            new_x = int((cx - self._move_offset[0]) / s)
            new_y = int((cy - self._move_offset[1]) / s)
            new_x = max(0, min(new_x, self._img_w - area['width']))
            new_y = max(0, min(new_y, self._img_h - area['height']))
            area['x'] = new_x
            area['y'] = new_y
            self._redraw_regions()
            return

        if self._drag_mode == 'resize':
            box = self._w2c(area)
            if not box:
                return
            x1, y1, x2, y2 = box
            corner = self._resize_corner
            if corner == 'nw':
                nx1, ny1, nx2, ny2 = cx, cy, x2, y2
            elif corner == 'ne':
                nx1, ny1, nx2, ny2 = x1, cy, cx, y2
            elif corner == 'sw':
                nx1, ny1, nx2, ny2 = cx, y1, x2, cy
            else:
                nx1, ny1, nx2, ny2 = x1, y1, cx, cy
            self._preview_id = self._canvas.create_rectangle(
                nx1, ny1, nx2, ny2, outline=color, width=2, dash=(3, 3),
            )

    def _on_release(self, event):
        if not self._drag_mode:
            return
        cx, cy = self._canvas_pos(event)
        x0, y0 = self._drag_start or (cx, cy)

        if self._drag_mode == 'draw':
            x, y, w, h = self._c2w(x0, y0, cx, cy)
            self._areas[self._selected_key] = {'x': x, 'y': y, 'width': w, 'height': h}
        elif self._drag_mode == 'resize':
            box = self._w2c(self._areas[self._selected_key])
            if box:
                x1, y1, x2, y2 = box
                corner = self._resize_corner
                if corner == 'nw':
                    nx1, ny1, nx2, ny2 = cx, cy, x2, y2
                elif corner == 'ne':
                    nx1, ny1, nx2, ny2 = x1, cy, cx, y2
                elif corner == 'sw':
                    nx1, ny1, nx2, ny2 = cx, y1, x2, cy
                else:
                    nx1, ny1, nx2, ny2 = x1, y1, cx, cy
                x, y, w, h = self._c2w(nx1, ny1, nx2, ny2)
                self._areas[self._selected_key] = {'x': x, 'y': y, 'width': w, 'height': h}

        if self._preview_id:
            self._canvas.delete(self._preview_id)
            self._preview_id = None

        self._drag_mode = None
        self._drag_start = None
        self._resize_corner = None
        self._redraw_regions()
        self._refresh_sidebar()
        self._on_hover(event)

        area = self._areas[self._selected_key]
        if area.get('width', 0) > 0:
            self._set_status(
                f'{self._label_for(self._selected_key)}: ({area["x"]}, {area["y"]}) '
                f'{area["width"]}×{area["height"]}',
            )

    def _on_save(self):
        for key, area in self._areas.items():
            target = getattr(config, key)
            if area.get('width', 0) > 0 and area.get('height', 0) > 0:
                region_helpers.apply_area_dict(
                    target, area['x'], area['y'], area['width'], area['height'],
                )
            else:
                region_helpers.clear_area(target)

        region_helpers.sync_mob_scan_from_enemy_name()
        region_helpers.sync_skill_area_tuple()

        try:
            import mob_filter
            import frame_cache
            mob_filter.invalidate_cache()
            frame_cache.invalidate()
        except ImportError:
            pass

        if hasattr(self.gui, 'refresh_region_pick_labels'):
            self.gui.refresh_region_pick_labels()

        self._set_status('Regions saved.')
        self.win.grab_release()
        self.win.destroy()

    def _on_cancel(self):
        self.win.grab_release()
        self.win.destroy()


def open_region_editor(parent, gui):
    """Open the visual region editor (requires connected window)."""
    if not config.connected_window:
        messagebox.showwarning('Region Editor', 'Connect to a game window first.')
        return
    if not CV_AVAILABLE:
        messagebox.showerror('Region Editor', 'OpenCV and Pillow are required.')
        return
    editor = RegionEditorWindow(parent, gui)
    parent.lift()
    editor.win.lift()
