"""
Modern Universal Tooltip System for ClipCraft Studio.
Provides high-performance, dark-themed, bilingual floating tooltips for any Tkinter/ttk widget.
Automatically repositions within screen bounds and supports hover delays and theme styling.

Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Union, Callable, Tuple


class ToolTip:
    """
    Sleek, dark-themed floating tooltip for any Tkinter or TTK widget.
    Supports hover delay, dynamic text, bilingual translation, and boundary checking.
    """

    def __init__(
        self,
        widget: tk.Widget,
        text_ar: str = "",
        text_en: str = "",
        delay_ms: int = 500,
        app=None,
    ):
        self.widget = widget
        self.text_ar = text_ar or text_en
        self.text_en = text_en or text_ar
        self.delay_ms = delay_ms
        self.app = app
        self._tip_window: Optional[tk.Toplevel] = None
        self._after_id: Optional[str] = None

        self.widget.bind("<Enter>", self._on_enter, add="+")
        self.widget.bind("<Leave>", self._on_leave, add="+")
        self.widget.bind("<ButtonPress>", self._on_leave, add="+")
        self.widget.bind("<Destroy>", self._on_destroy, add="+")

    def _get_text(self) -> str:
        if self.app and hasattr(self.app, "language_var"):
            is_ar = self.app.language_var.get() == "العربية"
        else:
            is_ar = True
        return self.text_ar if is_ar else self.text_en

    def update_text(self, text_ar: str, text_en: str = ""):
        self.text_ar = text_ar
        self.text_en = text_en or text_ar

    def _on_enter(self, event=None):
        self._cancel_scheduled()
        self._after_id = self.widget.after(self.delay_ms, self._show_tip)

    def _on_leave(self, event=None):
        self._cancel_scheduled()
        self._hide_tip()

    def _on_destroy(self, event=None):
        self._cancel_scheduled()
        self._hide_tip()

    def _cancel_scheduled(self):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show_tip(self):
        if not self.widget.winfo_exists():
            return
        tip_text = self._get_text()
        if not tip_text:
            return

        if self._tip_window is not None:
            return

        # Calculate coordinates directly below widget
        try:
            wx = self.widget.winfo_rootx()
            wy = self.widget.winfo_rooty()
            ww = self.widget.winfo_width()
            wh = self.widget.winfo_height()
        except Exception:
            return

        # Position slightly below widget center
        x = wx + (ww // 2) - 30
        y = wy + wh + 6

        # Screen boundary clamp
        sw = self.widget.winfo_screenwidth()
        sh = self.widget.winfo_screenheight()

        self._tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        try:
            tw.attributes("-topmost", True)
        except Exception:
            pass

        # Outer card frame with accent border
        card = tk.Frame(tw, bg="#363e4f", bd=1, relief="solid")
        card.pack(fill="both", expand=True)

        inner = tk.Frame(card, bg="#161b22", padx=8, pady=5)
        inner.pack(fill="both", expand=True)

        lbl = tk.Label(
            inner,
            text=tip_text,
            bg="#161b22",
            fg="#f0f6fc",
            font=("Segoe UI", 9),
            justify="center",
            wraplength=320,
        )
        lbl.pack()

        tw.update_idletasks()
        req_w = tw.winfo_reqwidth()
        req_h = tw.winfo_reqheight()

        # Adjust position if overflowing screen right or bottom
        if x + req_w > sw - 12:
            x = max(10, sw - req_w - 12)
        if x < 10:
            x = 10
        if y + req_h > sh - 36:
            # Place above widget instead
            y = max(10, wy - req_h - 6)

        tw.wm_geometry(f"+{int(x)}+{int(y)}")

    def _hide_tip(self):
        tw = self._tip_window
        self._tip_window = None
        if tw:
            try:
                tw.destroy()
            except Exception:
                pass


def add_tooltip(widget: tk.Widget, text_ar: str, text_en: str = "", app=None, delay_ms: int = 500) -> ToolTip:
    """Convenience helper to attach a bilingual tooltip to any widget."""
    return ToolTip(widget, text_ar=text_ar, text_en=text_en, delay_ms=delay_ms, app=app)
