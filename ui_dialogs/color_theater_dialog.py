"""
Color Studio Fullscreen Cinema Preview Dialog
Provides a distraction-free edge-to-edge fullscreen comparison view for color grading
with interactive draggable before/after split line, smooth cursor handle, and minimal floating toolbar.

Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
from PIL import Image, ImageTk, ImageDraw

from video_studio.color_grading import apply_color_to_image
from video_studio.arabic_support import prepare_arabic_for_rendering


class ColorTheaterDialog(tk.Toplevel):
    def __init__(self, color_dialog):
        super().__init__(color_dialog)
        self.color_dialog = color_dialog
        self.app = getattr(color_dialog, "app", color_dialog)
        self.is_ar = getattr(self.color_dialog, "is_ar", True)

        self.title("🎨 ملء الشاشة - فحص ومقارنة الألوان" if self.is_ar else "🎨 Fullscreen Color Grading Comparison")
        self.configure(bg="#000000")

        # Fullscreen borderless window
        try:
            self.attributes("-fullscreen", True)
        except Exception:
            self.state("zoomed")

        self.focus_force()
        self.transient(color_dialog)

        # Rendering and drag states
        self.photo_image: Optional[ImageTk.PhotoImage] = None
        self._dragging = False
        self._img_x0 = 0
        self._img_y0 = 0
        self._img_w = 0
        self._img_h = 0

        self._build_ui()
        self._bind_events()

        self.after(50, self.refresh_preview)

    def _build_ui(self):
        # 1. Edge-to-edge canvas with pitch-black cinema backdrop
        self.canvas = tk.Canvas(self, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # 2. Sleek floating minimal bottom control toolbar
        self.float_bar = tk.Frame(
            self,
            bg="#161b22",
            highlightthickness=1,
            highlightbackground="#30363d",
            padx=14,
            pady=8,
        )
        # Position floating cleanly at bottom center
        self.float_bar.place(relx=0.5, rely=0.93, anchor="center")

        # View mode toggle buttons
        btn_font = ("Segoe UI", 9, "bold")

        self.btn_split = tk.Button(
            self.float_bar,
            text=("🌓 قبل / بعد (مقسم)" if self.is_ar else "🌓 Split (Before / After)"),
            font=btn_font,
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            command=lambda: self._set_mode("split"),
        )
        self.btn_split.pack(side="left", padx=4)

        self.btn_graded = tk.Button(
            self.float_bar,
            text=("✨ بعد التصحيح فقط" if self.is_ar else "✨ After (Graded)"),
            font=btn_font,
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            command=lambda: self._set_mode("graded"),
        )
        self.btn_graded.pack(side="left", padx=4)

        self.btn_orig = tk.Button(
            self.float_bar,
            text=("👁️ قبل التصحيح فقط" if self.is_ar else "👁️ Before (Original)"),
            font=btn_font,
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            command=lambda: self._set_mode("original"),
        )
        self.btn_orig.pack(side="left", padx=4)

        # Subtle separator
        sep = tk.Frame(self.float_bar, width=1, height=20, bg="#30363d")
        sep.pack(side="left", padx=8)

        # Interactive gesture tip label
        self.lbl_tip = tk.Label(
            self.float_bar,
            text=("💡 اسحب الخط الفاصل بالماوس يميناً ويساراً للمقارنة" if self.is_ar else "💡 Drag the vertical split line to compare"),
            font=("Segoe UI", 8),
            fg="#8b949e",
            bg="#161b22",
        )
        self.lbl_tip.pack(side="left", padx=6)

        # Close fullscreen button
        self.btn_close = tk.Button(
            self.float_bar,
            text=("✕ خروج (Esc)" if self.is_ar else "✕ Exit (Esc)"),
            font=btn_font,
            bg="#21262d",
            fg="#f85149",
            activebackground="#da3633",
            activeforeground="#ffffff",
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.close,
        )
        self.btn_close.pack(side="left", padx=(10, 0))

        self._update_btn_styles()

    def _set_mode(self, mode: str):
        if hasattr(self.color_dialog, "preview_mode_var"):
            self.color_dialog.preview_mode_var.set(mode)
        self._update_btn_styles()
        self.refresh_preview()

    def _update_btn_styles(self):
        curr_mode = getattr(self.color_dialog, "preview_mode_var", tk.StringVar(value="split")).get()

        def style_btn(btn, is_active, active_fg="#58a6ff"):
            if is_active:
                btn.configure(bg="#238636" if active_fg == "#2ea043" else "#1f6feb", fg="#ffffff")
            else:
                btn.configure(bg="#21262d", fg="#c9d1d9")

        style_btn(self.btn_split, curr_mode == "split", active_fg="#58a6ff")
        style_btn(self.btn_graded, curr_mode == "graded", active_fg="#2ea043")
        style_btn(self.btn_orig, curr_mode == "original", active_fg="#8b949e")

        if curr_mode == "split":
            self.lbl_tip.configure(text=("💡 اسحب الخط الفاصل بالماوس يميناً ويساراً للمقارنة" if self.is_ar else "💡 Drag vertical line left/right to compare"))
        elif curr_mode == "graded":
            self.lbl_tip.configure(text=("✨ عرض النتيجة النهائية بعد التصحيح" if self.is_ar else "✨ Showing graded color result"))
        else:
            self.lbl_tip.configure(text=("👁️ عرض الفيديو الأصلي بدون أي تعديل" if self.is_ar else "👁️ Showing original untouched frame"))

    def _bind_events(self):
        self.bind("<Escape>", lambda _e: self.close())
        self.bind("<f>", lambda _e: self.close())
        self.bind("<F>", lambda _e: self.close())
        self.bind("<Key-1>", lambda _e: self._set_mode("original"))
        self.bind("<Key-2>", lambda _e: self._set_mode("graded"))
        self.bind("<Key-3>", lambda _e: self._set_mode("split"))
        self.bind("<space>", lambda _e: self._toggle_split_graded())
        self.bind("<Left>", lambda _e: self._nudge_split(-0.05))
        self.bind("<Right>", lambda _e: self._nudge_split(+0.05))
        self.bind("<Home>", lambda _e: self._set_split_ratio(0.02))
        self.bind("<End>", lambda _e: self._set_split_ratio(0.98))

        # Canvas mouse events for interactive split dragging
        self.canvas.bind("<Configure>", lambda _e: self.refresh_preview())
        self.canvas.bind("<Motion>", self._on_canvas_motion)
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Double-Button-1>", lambda _e: self.close())

    def _toggle_split_graded(self):
        curr = getattr(self.color_dialog, "preview_mode_var", tk.StringVar(value="split")).get()
        new_mode = "graded" if curr == "split" else "split"
        self._set_mode(new_mode)

    def _nudge_split(self, delta: float):
        cur_ratio = getattr(self.color_dialog, "split_ratio", 0.5)
        self._set_split_ratio(cur_ratio + delta)

    def _set_split_ratio(self, ratio: float):
        ratio = max(0.01, min(0.99, float(ratio)))
        self.color_dialog.split_ratio = ratio
        if getattr(self.color_dialog, "preview_mode_var", None) and self.color_dialog.preview_mode_var.get() != "split":
            self.color_dialog.preview_mode_var.set("split")
            self._update_btn_styles()
        self.refresh_preview()

    def _on_canvas_motion(self, event):
        curr_mode = getattr(self.color_dialog, "preview_mode_var", tk.StringVar(value="split")).get()
        if curr_mode != "split" or self._img_w <= 0:
            if not self._dragging:
                self.canvas.config(cursor="")
            return

        split_ratio = getattr(self.color_dialog, "split_ratio", 0.5)
        split_canvas_x = self._img_x0 + (self._img_w * split_ratio)

        # Check if hovering near the split line
        is_near_split = (abs(event.x - split_canvas_x) <= 16) and (self._img_y0 - 20 <= event.y <= self._img_y0 + self._img_h + 20)
        if is_near_split:
            self.canvas.config(cursor="sb_h_double_arrow")
        elif not self._dragging:
            self.canvas.config(cursor="")

    def _on_canvas_press(self, event):
        curr_mode = getattr(self.color_dialog, "preview_mode_var", tk.StringVar(value="split")).get()
        if curr_mode != "split":
            return
        if self._img_w <= 0:
            return

        # Start dragging anywhere inside canvas or near split line
        self._dragging = True
        self.canvas.config(cursor="sb_h_double_arrow")
        ratio = (event.x - self._img_x0) / float(self._img_w)
        self._set_split_ratio(ratio)

    def _on_canvas_drag(self, event):
        if not self._dragging or self._img_w <= 0:
            return
        ratio = (event.x - self._img_x0) / float(self._img_w)
        self._set_split_ratio(ratio)

    def _on_canvas_release(self, _event):
        self._dragging = False
        self.canvas.config(cursor="")

    def refresh_preview(self):
        if not self.winfo_exists():
            return
        base_im = getattr(self.color_dialog, "base_image", None)
        if base_im is None:
            return

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 200 or ch < 200:
            cw = self.winfo_screenwidth()
            ch = self.winfo_screenheight()

        mode = getattr(self.color_dialog, "preview_mode_var", tk.StringVar(value="split")).get()
        enabled = getattr(self.color_dialog, "enabled_var", tk.BooleanVar(value=True)).get()

        # Retrieve or generate graded frame
        graded_im = getattr(self.color_dialog, "_cached_graded_im", None)
        if graded_im is None or graded_im.size != base_im.size:
            cfg = self.color_dialog._get_active_config()
            if enabled:
                graded_im = apply_color_to_image(base_im, cfg)
            else:
                graded_im = base_im.copy()
            self.color_dialog._cached_graded_im = graded_im

        # Composite frame according to mode
        w, h = base_im.size
        if mode == "original" or not enabled:
            disp_im = base_im.copy()
        elif mode == "graded":
            disp_im = graded_im.copy()
        else:
            # Interactive Split View
            split_ratio = getattr(self.color_dialog, "split_ratio", 0.5)
            split_x = int(round(w * split_ratio))
            split_x = max(0, min(w, split_x))

            disp_im = base_im.copy()
            right_crop = graded_im.crop((split_x, 0, w, h))
            disp_im.paste(right_crop, (split_x, 0))

            # Draw high-contrast separator line & round double-arrow handle
            draw = ImageDraw.Draw(disp_im)
            line_w = max(2, int(w * 0.0025))

            # Outer dark contrast borders
            draw.line([(split_x - 1, 0), (split_x - 1, h)], fill="#000000", width=1)
            draw.line([(split_x + line_w, 0), (split_x + line_w, h)], fill="#000000", width=1)
            # Pure white main line
            draw.line([(split_x, 0), (split_x, h)], fill="#ffffff", width=line_w)

            # Circular draggable handle in vertical center
            cy = h // 2
            hr = max(18, int(h * 0.032))
            draw.ellipse([split_x - hr, cy - hr, split_x + hr, cy + hr], fill="#161b22", outline="#ffffff", width=2)
            # Draggable arrows / lines inside circle
            draw.polygon([(split_x - hr + 5, cy), (split_x - 4, cy - 6), (split_x - 4, cy + 6)], fill="#ffffff")
            draw.polygon([(split_x + hr - 5, cy), (split_x + 4, cy - 6), (split_x + 4, cy + 6)], fill="#ffffff")
            draw.line([(split_x, cy - 7), (split_x, cy + 7)], fill="#58a6ff", width=2)

            # Text badges for Before and After
            lbl_l = prepare_arabic_for_rendering("الأصل (Before)" if self.is_ar else "Before (Original)")
            lbl_r = prepare_arabic_for_rendering("بعد التصحيح (After)" if self.is_ar else "After (Graded)")

            badge_h = max(28, int(h * 0.045))
            badge_w_l = max(130, int(w * 0.12))
            badge_w_r = max(150, int(w * 0.13))

            # Left badge (Before) anchored top-left
            draw.rectangle([14, 14, 14 + badge_w_l, 14 + badge_h], fill="#161b22", outline="#58a6ff", width=2)
            draw.text((24, 18), lbl_l, fill="#ffffff")

            # Right badge (After) anchored top-right
            draw.rectangle([w - badge_w_r - 14, 14, w - 14, 14 + badge_h], fill="#161b22", outline="#2ea043", width=2)
            draw.text((w - badge_w_r - 4, 18), lbl_r, fill="#ffffff")

        # Fit scaled image into canvas while preserving aspect ratio
        aspect = w / max(h, 1)
        avail_w = cw
        avail_h = ch
        target_h = avail_h
        target_w = int(target_h * aspect)
        if target_w > avail_w:
            target_w = avail_w
            target_h = int(target_w / aspect)

        target_w = max(10, target_w)
        target_h = max(10, target_h)

        scaled_im = disp_im.resize((target_w, target_h), Image.Resampling.BILINEAR)
        self.photo_image = ImageTk.PhotoImage(scaled_im)

        self.canvas.delete("all")
        cx = cw // 2
        cy = ch // 2
        self.canvas.create_image(cx, cy, image=self.photo_image)

        # Store canvas bounding box for coordinate translation
        self._img_w = target_w
        self._img_h = target_h
        self._img_x0 = cx - (target_w // 2)
        self._img_y0 = cy - (target_h // 2)

    def close(self):
        if getattr(self.color_dialog, "_theater_dialog", None) is self:
            self.color_dialog._theater_dialog = None
        # Refresh parent preview in normal mode so split ratio & mode remain synced
        if hasattr(self.color_dialog, "_render_preview"):
            self.color_dialog._render_preview()
        self.destroy()
