"""Minimised floating overlay pill and its drag handling.

Moved out of gui.py unchanged. Mixed into BotGUI, so these methods keep
using self exactly as before -- no call sites changed.
"""
import config
import customtkinter as ctk
import time
import ui_icons
from ui.widgets import create_tooltip


class MiniOverlayMixin:
    """Minimised floating overlay pill and its drag handling."""

    def toggle_minimize(self):
        """Toggle between minimized and maximized UI"""
        if self.is_minimized:
            # Restore to maximized view
            if self._overlay_after_id:
                try:
                    self.minimized_window.after_cancel(self._overlay_after_id)
                except Exception:
                    pass
                self._overlay_after_id = None
            if self.minimized_window:
                self.minimized_toggle_bot_button = None
                self.overlay_status_dot = None
                self.overlay_timer_label = None
                self.minimized_window.destroy()
                self.minimized_window = None
            self.root.deiconify()
            # Restore saved window position and size
            if self.saved_window_position:
                self.root.geometry(self.saved_window_position)
            else:
                self.root.geometry("720x800")
            self.minimize_button.configure(text="", image=ui_icons.get_icon("minimize", size=16))
            self.is_minimized = False
        else:
            # Save current window position and size before minimizing
            try:
                geometry = self.root.geometry()
                self.saved_window_position = geometry
            except:
                self.saved_window_position = "655x800+100+100"
            # Mark minimized BEFORE building the pill so the refresh loop (which
            # checks is_minimized) actually starts and the timer/status tick.
            self.is_minimized = True
            # Create minimized window at the same position
            self.create_minimized_window()
            self.minimize_button.configure(text="", image=ui_icons.get_icon("minimize", size=16))

    def create_minimized_window(self):
        """Create the compact Mini Overlay pill (frameless, draggable, on top)."""
        if self.minimized_window:
            return

        pill = ctk.CTkToplevel(self.root)
        pill.title(config.APP_TITLE)
        self.minimized_window = pill

        # Position at the previous window's top-left (fallback: near top).
        pos = "+120+80"
        if self.saved_window_position:
            parts = self.saved_window_position.split('+')
            if len(parts) >= 3:
                pos = f"+{parts[1]}+{parts[2]}"
        pill.geometry(f"244x56{pos}")
        pill.resizable(False, False)
        pill.attributes("-topmost", True)
        # Frameless pill look. overrideredirect drops the title bar/taskbar entry.
        try:
            pill.overrideredirect(True)
        except Exception:
            pass
        # Key the window background out to transparency so the square corners
        # around the rounded body disappear (clean floating pill, full border).
        pill.configure(fg_color=self.OVERLAY_TRANSPARENT_KEY)
        try:
            pill.attributes("-transparentcolor", self.OVERLAY_TRANSPARENT_KEY)
        except Exception:
            pass
        pill.columnconfigure(0, weight=1)
        pill.rowconfigure(0, weight=1)

        # Rounded body — padding leaves the border fully visible on every side,
        # and the padding area (window bg) is keyed to transparency.
        body = ctk.CTkFrame(pill, corner_radius=26, fg_color=self.OVERLAY_BG,
                            border_width=1, border_color=self.OVERLAY_BORDER)
        body.grid(row=0, column=0, sticky="nsew", padx=3, pady=3)

        # Status dot (green = running, gray = stopped)
        self.overlay_status_dot = ctk.CTkLabel(
            body, text="●", font=ctk.CTkFont(size=15), text_color="#6b7280", width=14,
        )
        self.overlay_status_dot.pack(side="left", padx=(14, 8))

        # Runtime timer
        self.overlay_timer_label = ctk.CTkLabel(
            body, text="00:00:00",
            font=ctk.CTkFont(family="Consolas", size=15, weight="bold"),
            text_color="#e5e7eb",
        )
        self.overlay_timer_label.pack(side="left", padx=(0, 8))

        # Drag the pill by its body / status area (buttons stay clickable).
        for w in (body, self.overlay_status_dot, self.overlay_timer_label):
            w.bind("<Button-1>", self._overlay_start_move)
            w.bind("<B1-Motion>", self._overlay_on_move)

        # Expand / restore (rightmost)
        expand_btn = ctk.CTkButton(
            body, text="", image=ui_icons.get_icon("expand", size=17),
            width=32, height=32, corner_radius=8,
            fg_color="transparent", hover_color="#2b2f38",
            command=self.toggle_minimize,
        )
        expand_btn.pack(side="right", padx=(4, 10))
        create_tooltip(expand_btn, "Expand — restore the full window")

        # Start / Stop (managed by update_toggle_bot_button_state via cfg_min)
        self.minimized_toggle_bot_button = ctk.CTkButton(
            body, text="", image=ui_icons.get_icon("play", size=16),
            width=40, height=32, corner_radius=8,
            fg_color="#16a34a", hover_color="#15803d",
            command=self.toggle_bot,
        )
        self.minimized_toggle_bot_button.pack(side="right", padx=4)

        self.update_toggle_bot_button_state()

        # Escape restores the full window (needs focus; harmless otherwise).
        pill.bind("<Escape>", lambda _e: self.toggle_minimize())
        pill.protocol("WM_DELETE_WINDOW", self.toggle_minimize)

        # Hide the main window and start the lightweight refresh loop.
        self.root.withdraw()
        self._refresh_overlay()

    def _overlay_start_move(self, event):
        self._overlay_drag_ox = event.x_root - self.minimized_window.winfo_x()
        self._overlay_drag_oy = event.y_root - self.minimized_window.winfo_y()

    def _overlay_on_move(self, event):
        if not self.minimized_window:
            return
        x = event.x_root - getattr(self, "_overlay_drag_ox", 0)
        y = event.y_root - getattr(self, "_overlay_drag_oy", 0)
        self.minimized_window.geometry(f"+{x}+{y}")

    def _bot_runtime_seconds(self):
        if config.bot_running and self._bot_run_start_time:
            return max(0, int(time.time() - self._bot_run_start_time))
        return 0

    @staticmethod
    def _format_hms(seconds):
        h, rem = divmod(int(seconds), 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _refresh_overlay(self):
        """Lightweight overlay refresh loop (runs only while the pill is open).

        Guarded on the window existing (cleared to None on restore) rather than the
        is_minimized flag, so the loop keeps ticking regardless of flag-set ordering.
        """
        if not self.minimized_window:
            self._overlay_after_id = None
            return
        try:
            running = config.bot_running
            self.overlay_status_dot.configure(text_color="#22c55e" if running else "#6b7280")
            self.overlay_timer_label.configure(text=self._format_hms(self._bot_runtime_seconds()))
        except Exception:
            pass
        self._overlay_after_id = self.minimized_window.after(self.OVERLAY_TICK_MS, self._refresh_overlay)
