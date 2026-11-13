"""
Video Color Correction & Grading Interactive Dialog
Provides intelligent automatic color analysis and full manual precision controls
(Brightness, Contrast, Saturation, Gamma, Temperature, Red/Green/Blue channels)
with real-time split/before-after preview, presets, and single-click reset.

Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Dict, Any, Optional

import numpy as np
from PIL import Image, ImageTk, ImageDraw

from video_studio.color_grading import (
    DEFAULT_COLOR_CONFIG,
    COLOR_PRESETS,
    AUTO_COLOR_MODES,
    auto_analyze_and_correct,
    analyze_video_multi_frame,
    apply_color_to_image,
    extract_video_sample_frame,
    is_color_neutral,
)
from video_studio.arabic_support import prepare_arabic_for_rendering
from .color_theater_dialog import ColorTheaterDialog


class VideoColorDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.app = getattr(parent, "parent", parent)
        self.is_ar = getattr(self.app, "language_var", tk.StringVar(value="English")).get() == "العربية"

        dlg_title = "🎨 تصحيح وتدرج ألوان الفيديو" if self.is_ar else "🎨 Video Color Correction & Grading"
        self.title(dlg_title)
        if hasattr(self.app, "_apply_theme_to_toplevel"):
            self.app._apply_theme_to_toplevel(self)
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        target_w = min(960, max(820, int(screen_w * 0.85)))
        target_h = min(840, max(660, int(screen_h * 0.88)))
        self.geometry(f"{target_w}x{target_h}")
        self.minsize(min(820, target_w), min(640, target_h))
        self.transient(parent)
        self.resizable(True, True)

        # Load existing config or default
        branding_cfg = getattr(self.app, "video_branding_config", {})
        saved_color = branding_cfg.get("color_config", {})
        self.current_config = dict(DEFAULT_COLOR_CONFIG)
        if isinstance(saved_color, dict):
            self.current_config.update(saved_color)

        # State Variables
        self.enabled_var = tk.BooleanVar(value=bool(self.current_config.get("enabled", True)))
        self.brightness_var = tk.DoubleVar(value=float(self.current_config.get("brightness", 0.0)))
        self.contrast_var = tk.DoubleVar(value=float(self.current_config.get("contrast", 1.0)))
        self.saturation_var = tk.DoubleVar(value=float(self.current_config.get("saturation", 1.0)))
        self.gamma_var = tk.DoubleVar(value=float(self.current_config.get("gamma", 1.0)))
        self.temperature_var = tk.DoubleVar(value=float(self.current_config.get("temperature", 0.0)))
        self.red_var = tk.DoubleVar(value=float(self.current_config.get("red", 0.0)))
        self.green_var = tk.DoubleVar(value=float(self.current_config.get("green", 0.0)))
        self.blue_var = tk.DoubleVar(value=float(self.current_config.get("blue", 0.0)))

        # Preview mode: "graded", "split", "original"
        self.preview_mode_var = tk.StringVar(value="split")
        self.diagnosis_text_var = tk.StringVar(value="")

        # Image state
        self.base_image: Optional[Image.Image] = None
        self.photo_image: Optional[ImageTk.PhotoImage] = None
        self.preview_pending = False

        # Interactive Split & Fullscreen Cinema State
        self.split_ratio = 0.5
        self._dragging_split = False
        self._cached_graded_im: Optional[Image.Image] = None
        self._cached_cfg_hash = None
        self._theater_dialog: Optional[ColorTheaterDialog] = None
        self._canvas_img_x0 = 0
        self._canvas_img_y0 = 0
        self._canvas_img_w = 0
        self._canvas_img_h = 0

        self._initial_config = dict(self.current_config)
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

        self._build_ui()
        self._load_source_frame()

        # Center on parent
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        dw = self.winfo_width()
        dh = self.winfo_height()
        x = max(20, px + (pw - dw) // 2)
        y = max(20, py + (ph - dh) // 2)
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        # ------------------ Row 0: Top Header & Toggle ------------------
        header_card = ttk.Frame(container)
        header_card.pack(fill="x", pady=(0, 6))

        title_lbl = ttk.Label(
            header_card,
            text="🎨 " + ("تصحيح وتدرج ألوان الفيديو" if self.is_ar else "Video Color Grading & Balance"),
            font=("Segoe UI", 13, "bold"),
        )
        title_lbl.pack(side="left")

        self.chk_enable = ttk.Checkbutton(
            header_card,
            text=("تفعيل تصحيح الألوان في الفيديو" if self.is_ar else "Enable Video Color Grading"),
            variable=self.enabled_var,
            command=self._schedule_preview,
        )
        self.chk_enable.pack(side="right")

        # ------------------ Row 1: Preview Canvas & View Controls ------------------
        prev_card = ttk.LabelFrame(
            container,
            text="🎥 " + ("معاينة الألوان الحية" if self.is_ar else "Live Color Preview"),
            padding=(6, 6),
        )
        prev_card.pack(fill="both", expand=True, pady=(0, 6))

        # View Mode Toolbar
        view_bar = ttk.Frame(prev_card)
        view_bar.pack(fill="x", pady=(0, 4))

        ttk.Label(view_bar, text=("طريقة العرض:" if self.is_ar else "View Mode:")).pack(side="left", padx=(0, 6))

        r_split = ttk.Radiobutton(
            view_bar,
            text=("🌓 قبل / بعد (مقسم)" if self.is_ar else "🌓 Split (Before / After)"),
            variable=self.preview_mode_var,
            value="split",
            command=self._schedule_preview,
        )
        r_split.pack(side="left", padx=4)

        r_graded = ttk.Radiobutton(
            view_bar,
            text=("✨ بعد التصحيح فقط" if self.is_ar else "✨ Graded Result"),
            variable=self.preview_mode_var,
            value="graded",
            command=self._schedule_preview,
        )
        r_graded.pack(side="left", padx=4)

        r_orig = ttk.Radiobutton(
            view_bar,
            text=("👁️ الأصل بدون تعديل" if self.is_ar else "👁️ Original"),
            variable=self.preview_mode_var,
            value="original",
            command=self._schedule_preview,
        )
        r_orig.pack(side="left", padx=4)

        self.btn_fullscreen = ttk.Button(
            view_bar,
            text=("⛶ ملء الشاشة (F)" if self.is_ar else "⛶ Fullscreen (F)"),
            command=self.open_fullscreen_preview,
            style="PrimaryPlayer.TButton",
        )
        self.btn_fullscreen.pack(side="right", padx=(6, 0))

        self.btn_refresh_frame = ttk.Button(
            view_bar,
            text=("🔄 تحديث اللقطة" if self.is_ar else "🔄 Refresh Frame"),
            command=self._reload_video_frame,
            style="Player.TButton",
        )
        self.btn_refresh_frame.pack(side="right", padx=(6, 0))

        self.lbl_split_hint = ttk.Label(
            view_bar,
            text=("💡 اسحب الخط الفاصل للمقارنة" if self.is_ar else "💡 Drag split line to compare"),
            foreground="#8b949e",
            font=("Segoe UI", 8),
        )
        self.lbl_split_hint.pack(side="left", padx=(10, 0))

        # Canvas for preview rendering
        self.preview_canvas = tk.Canvas(prev_card, bg="#0d1117", highlightthickness=1, highlightbackground="#30363d")
        self.preview_canvas.pack(fill="both", expand=True)
        self.preview_canvas.bind("<Configure>", lambda e: self._schedule_preview())
        self.preview_canvas.bind("<Motion>", self._on_canvas_motion)
        self.preview_canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.preview_canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.preview_canvas.bind("<Double-Button-1>", lambda _e: self.open_fullscreen_preview())

        # Keyboard shortcut for quick fullscreen toggle
        self.bind("<f>", lambda _e: self.open_fullscreen_preview())
        self.bind("<F>", lambda _e: self.open_fullscreen_preview())

        # ------------------ Row 2: Smart Auto Balance & Presets Card ------------------
        action_card = ttk.LabelFrame(
            container,
            text="✨ " + ("المعالجة الذكية والقوالب السريعة" if self.is_ar else "Smart Auto Balance & Presets"),
            padding=(8, 6),
        )
        action_card.pack(fill="x", pady=(0, 6))

        auto_row = ttk.Frame(action_card)
        auto_row.pack(fill="x", pady=(0, 4))

        ttk.Label(auto_row, text=("درجة التصحيح:" if self.is_ar else "Intensity:")).pack(side="left", padx=(0, 6))

        mode_items = [(k, info["label_ar"] if self.is_ar else info["label_en"]) for k, info in AUTO_COLOR_MODES.items()]
        self._auto_mode_map = {d: k for k, d in mode_items}
        self._auto_mode_rev = {k: d for k, d in mode_items}
        self.auto_mode_var = tk.StringVar(value=mode_items[0][1])

        self.auto_mode_combo = ttk.Combobox(
            auto_row,
            textvariable=self.auto_mode_var,
            values=[d for _, d in mode_items],
            state="readonly",
            width=22,
        )
        self.auto_mode_combo.pack(side="left", padx=(0, 8))
        self.auto_mode_combo.bind("<<ComboboxSelected>>", lambda _e: self.run_auto_correction())

        self.btn_auto = ttk.Button(
            auto_row,
            text=("🤖 فحص وتحليل وتصحيح ذكي" if self.is_ar else "🤖 Analyze & Auto Correct"),
            command=self.run_auto_correction,
            style="Action.TButton",
        )
        self.btn_auto.pack(side="left", padx=(0, 10))

        # Diagnosis badge / status
        self.lbl_diagnosis = ttk.Label(
            action_card,
            textvariable=self.diagnosis_text_var,
            foreground="#58a6ff",
            font=("Segoe UI", 8, "bold"),
            wraplength=850,
        )
        self.lbl_diagnosis.pack(fill="x", pady=(2, 4))

        # Presets Grid (2 rows x 4 equal-width columns so all preset names are 100% visible and never cut off!)
        preset_grid = ttk.Frame(action_card)
        preset_grid.pack(fill="x", pady=(4, 2))
        for col_i in range(4):
            preset_grid.columnconfigure(col_i, weight=1, uniform="pcol")

        ttk.Label(
            preset_grid,
            text=("قوالب ألوان جاهزة:" if self.is_ar else "Color Presets:"),
            font=("Segoe UI", 8, "bold"),
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 2))

        seen_p_btns = set()
        btn_idx = 0
        for key, p_data in COLOR_PRESETS.items():
            btn_txt = p_data["label_ar"] if self.is_ar else p_data["label_en"]
            if btn_txt in seen_p_btns:
                continue
            seen_p_btns.add(btn_txt)
            r_idx = 1 + (btn_idx // 4)
            c_idx = btn_idx % 4
            btn_p = ttk.Button(
                preset_grid,
                text=btn_txt,
                command=lambda k=key: self.apply_preset(k),
                style="Player.TButton",
            )
            btn_p.grid(row=r_idx, column=c_idx, sticky="ew", padx=2, pady=2)
            btn_idx += 1

        # ------------------ Row 3: Manual Precision Sliders ------------------
        manual_card = ttk.LabelFrame(
            container,
            text="🎛️ " + ("التحكم اليدوي الدقيق في الألوان" if self.is_ar else "Manual Precision Color Controls"),
            padding=(10, 6),
        )
        manual_card.pack(fill="x", pady=(0, 8))

        # Split into 2 columns
        manual_card.columnconfigure(0, weight=1)
        manual_card.columnconfigure(1, weight=1)

        col_left = ttk.Frame(manual_card)
        col_left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        col_right = ttk.Frame(manual_card)
        col_right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # Left Column: Tone & Exposure (Brightness, Contrast, Saturation, Gamma)
        self.val_lbls = {}
        self._add_slider_row(
            parent=col_left,
            var=self.brightness_var,
            name="brightness",
            label_ar="السطوع / الإضاءة",
            label_en="Brightness",
            from_val=-0.5,
            to_val=0.5,
            default_val=0.0,
            formatter=lambda v: f"{int(v*100):+d}%",
        )
        self._add_slider_row(
            parent=col_left,
            var=self.contrast_var,
            name="contrast",
            label_ar="التباين الديناميكي",
            label_en="Contrast",
            from_val=0.5,
            to_val=2.0,
            default_val=1.0,
            formatter=lambda v: f"{int(v*100)}%",
        )
        self._add_slider_row(
            parent=col_left,
            var=self.saturation_var,
            name="saturation",
            label_ar="التشبع اللوني",
            label_en="Saturation",
            from_val=0.0,
            to_val=2.5,
            default_val=1.0,
            formatter=lambda v: f"{int(v*100)}%" if v > 0.02 else ("أبيض وأسود" if self.is_ar else "B&W"),
        )
        self._add_slider_row(
            parent=col_left,
            var=self.gamma_var,
            name="gamma",
            label_ar="جاما (الظلال والمتوسطات)",
            label_en="Gamma (Midtones)",
            from_val=0.5,
            to_val=2.0,
            default_val=1.0,
            formatter=lambda v: f"{v:.2f}",
        )

        # Right Column: Color Balance & Temperature (Temperature, Red, Green, Blue)
        self._add_slider_row(
            parent=col_right,
            var=self.temperature_var,
            name="temperature",
            label_ar="حرارة اللون (بارد ↔ دافئ)",
            label_en="Color Temp (Cool ↔ Warm)",
            from_val=-0.5,
            to_val=0.5,
            default_val=0.0,
            formatter=lambda v: f"{int(v*100):+d}%",
        )
        self._add_slider_row(
            parent=col_right,
            var=self.red_var,
            name="red",
            label_ar="قناة الأحمر (Red Balance)",
            label_en="Red Channel Gain",
            from_val=-0.5,
            to_val=0.5,
            default_val=0.0,
            formatter=lambda v: f"{int(v*100):+d}%",
        )
        self._add_slider_row(
            parent=col_right,
            var=self.green_var,
            name="green",
            label_ar="قناة الأخضر (Green Balance)",
            label_en="Green Channel Gain",
            from_val=-0.5,
            to_val=0.5,
            default_val=0.0,
            formatter=lambda v: f"{int(v*100):+d}%",
        )
        self._add_slider_row(
            parent=col_right,
            var=self.blue_var,
            name="blue",
            label_ar="قناة الأزرق (Blue Balance)",
            label_en="Blue Channel Gain",
            from_val=-0.5,
            to_val=0.5,
            default_val=0.0,
            formatter=lambda v: f"{int(v*100):+d}%",
        )

        # ------------------ Row 4: Bottom Action Buttons ------------------
        bottom_box = ttk.Frame(container)
        bottom_box.pack(fill="x", pady=(4, 0))

        btn_reset = ttk.Button(
            bottom_box,
            text=("↺ إعادة ضبط الكل" if self.is_ar else "↺ Reset All"),
            command=self.reset_all,
            style="Player.TButton",
        )
        btn_reset.pack(side="left")

        btn_cancel = ttk.Button(
            bottom_box,
            text=("❌ إلغاء" if self.is_ar else "❌ Cancel"),
            command=self.on_cancel,
            style="Player.TButton",
        )
        btn_cancel.pack(side="right", padx=(6, 0))

        btn_save = ttk.Button(
            bottom_box,
            text=("💾 حفظ وتطبيق الألوان" if self.is_ar else "💾 Save & Apply"),
            command=self.save_and_apply,
            style="Action.TButton",
        )
        btn_save.pack(side="right")

    def _add_slider_row(
        self,
        parent,
        var: tk.DoubleVar,
        name: str,
        label_ar: str,
        label_en: str,
        from_val: float,
        to_val: float,
        default_val: float,
        formatter,
    ):
        f = ttk.Frame(parent)
        f.pack(fill="x", pady=2)
        f.columnconfigure(1, weight=1)

        txt = label_ar if self.is_ar else label_en
        lbl = ttk.Label(f, text=txt, width=22, anchor="w")
        lbl.grid(row=0, column=0, sticky="w")

        slider = ttk.Scale(
            f,
            from_=from_val,
            to=to_val,
            variable=var,
            command=lambda *_: self._on_slider_change(name, var, formatter),
        )
        slider.grid(row=0, column=1, sticky="ew", padx=(4, 6))

        val_lbl = ttk.Label(f, text=formatter(var.get()), width=7, anchor="e", font=("Segoe UI", 9, "bold"))
        val_lbl.grid(row=0, column=2, sticky="e")
        self.val_lbls[name] = (val_lbl, formatter)

        # Reset button for this individual slider
        btn_r = ttk.Button(
            f,
            text="↺",
            width=2,
            style="Player.TButton",
            command=lambda: self._reset_single_slider(name, var, default_val),
        )
        btn_r.grid(row=0, column=3, padx=(4, 0))

    def _reset_single_slider(self, name: str, var: tk.DoubleVar, default_val: float):
        var.set(default_val)
        if name in self.val_lbls:
            lbl, fmt = self.val_lbls[name]
            lbl.configure(text=fmt(default_val))
        self._schedule_preview()

    def _on_slider_change(self, name: str, var: tk.DoubleVar, formatter):
        val = var.get()
        if name in self.val_lbls:
            self.val_lbls[name][0].configure(text=formatter(val))
        self._schedule_preview()

    def _refresh_all_value_labels(self):
        for name, (lbl, fmt) in self.val_lbls.items():
            var = getattr(self, f"{name}_var", None)
            if var:
                lbl.configure(text=fmt(var.get()))

    def _load_source_frame(self):
        """Extracts a frame from the loaded video or generates a sample frame."""
        video_p = getattr(self.app, "input_path", None)
        timestamp = 1.0
        try:
            cur_dur = float(getattr(self.app, "media_duration", 0) or 0)
            cur_sec = float(getattr(self.app, "timeline_var", tk.DoubleVar(value=1.0)).get() or 1.0)
            if cur_dur > 2.0:
                timestamp = max(0.5, min(cur_dur - 1.0, cur_sec))
            else:
                timestamp = max(0.1, cur_sec)
        except Exception:
            pass

        # Immediately provide fallback base_image so UI never freezes or waits
        if self.base_image is None:
            self.base_image = self._generate_sample_frame()
            self._render_preview()

        ffmpeg_exe = None
        try:
            import convert
            ffmpeg_exe = str(convert.ffmpeg_executable())
        except Exception:
            pass

        def _bg_extract():
            frame = None
            if video_p and Path(video_p).is_file():
                frame = extract_video_sample_frame(
                    video_path=video_p,
                    timestamp=timestamp,
                    max_dim=720,
                    ffmpeg_exe=ffmpeg_exe,
                )

            if frame is not None:
                self.base_image = frame
                try:
                    if self.winfo_exists():
                        self.after(10, self._render_preview)
                except Exception:
                    pass

        threading.Thread(target=_bg_extract, daemon=True).start()

    def _reload_video_frame(self):
        self._load_source_frame()

    def _generate_sample_frame(self) -> Image.Image:
        """Generates a realistic multi-color gradient canvas with skin tones, sky, and shadows."""
        w, h = 640, 360
        arr = np.zeros((h, w, 3), dtype=np.uint8)
        # Sky gradient on top
        for y in range(h // 2):
            val_b = int(180 + (75 * (y / (h / 2))))
            val_r = int(90 + (50 * (y / (h / 2))))
            val_g = int(140 + (60 * (y / (h / 2))))
            arr[y, :, 0] = val_r
            arr[y, :, 1] = val_g
            arr[y, :, 2] = val_b
        # Warm ground on bottom
        for y in range(h // 2, h):
            dy = (y - h // 2) / (h / 2)
            arr[y, :, 0] = int(140 - 50 * dy)
            arr[y, :, 1] = int(120 - 45 * dy)
            arr[y, :, 2] = int(90 - 35 * dy)

        im = Image.fromarray(arr, mode="RGB")
        draw = ImageDraw.Draw(im)
        # Add color swatches for testing
        draw.rectangle([60, 100, 160, 220], fill=(225, 175, 140), outline="black")  # Skin tone
        draw.rectangle([180, 100, 280, 220], fill=(185, 30, 40), outline="black")   # Deep Red
        draw.rectangle([300, 100, 400, 220], fill=(35, 155, 60), outline="black")   # Greenery
        draw.rectangle([420, 100, 520, 220], fill=(30, 90, 190), outline="black")   # Vibrant Blue
        draw.rectangle([540, 100, 600, 220], fill=(240, 210, 40), outline="black")  # Golden Yellow
        return im

    def _schedule_preview(self):
        if not self.preview_pending:
            self.preview_pending = True
            self.after(25, self._render_preview)

    def _get_active_config(self) -> Dict[str, Any]:
        return {
            "enabled": bool(self.enabled_var.get()),
            "brightness": float(self.brightness_var.get()),
            "contrast": float(self.contrast_var.get()),
            "saturation": float(self.saturation_var.get()),
            "gamma": float(self.gamma_var.get()),
            "temperature": float(self.temperature_var.get()),
            "red": float(self.red_var.get()),
            "green": float(self.green_var.get()),
            "blue": float(self.blue_var.get()),
        }

    def _render_preview(self):
        self.preview_pending = False
        if not self.winfo_exists():
            return
        if self.base_image is None:
            return

        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()
        if cw < 60 or ch < 60:
            cw, ch = 680, 360

        cfg = self._get_active_config()
        mode = self.preview_mode_var.get()
        enabled = self.enabled_var.get()

        # Update live player in background if video is playing/loaded
        if hasattr(self.app, "apply_video_color_adjustments"):
            self.app.apply_video_color_adjustments(cfg)

        # Cache graded version for instantaneous 60fps split dragging
        cfg_key = (id(self.base_image), tuple(sorted(cfg.items())), enabled)
        if (
            self._cached_graded_im is None
            or getattr(self, "_cached_cfg_hash", None) != cfg_key
            or self._cached_graded_im.size != self.base_image.size
        ):
            if enabled:
                self._cached_graded_im = apply_color_to_image(self.base_image, cfg)
            else:
                self._cached_graded_im = self.base_image.copy()
            self._cached_cfg_hash = cfg_key

        graded_im = self._cached_graded_im

        # Composite based on view mode
        w, h = self.base_image.size
        if mode == "original" or not enabled:
            disp_im = self.base_image.copy()
        elif mode == "graded":
            disp_im = graded_im.copy()
        else:
            # Split View (Left: Original, Right: Graded) with interactive draggable split
            split_ratio = getattr(self, "split_ratio", 0.5)
            split_x = int(round(w * split_ratio))
            split_x = max(0, min(w, split_x))

            disp_im = self.base_image.copy()
            right_crop = graded_im.crop((split_x, 0, w, h))
            disp_im.paste(right_crop, (split_x, 0))

            # Draw white separator line with dark contrast edges
            draw = ImageDraw.Draw(disp_im)
            line_w = max(2, int(w * 0.0025))
            draw.line([(split_x - 1, 0), (split_x - 1, h)], fill="#000000", width=1)
            draw.line([(split_x + line_w, 0), (split_x + line_w, h)], fill="#000000", width=1)
            draw.line([(split_x, 0), (split_x, h)], fill="#ffffff", width=line_w)

            # Circular draggable handle in vertical center
            cy = h // 2
            hr = max(16, int(h * 0.032))
            draw.ellipse([split_x - hr, cy - hr, split_x + hr, cy + hr], fill="#161b22", outline="#ffffff", width=2)
            draw.polygon([(split_x - hr + 4, cy), (split_x - 3, cy - 5), (split_x - 3, cy + 5)], fill="#ffffff")
            draw.polygon([(split_x + hr - 4, cy), (split_x + 3, cy - 5), (split_x + 3, cy + 5)], fill="#ffffff")
            draw.line([(split_x, cy - 6), (split_x, cy + 6)], fill="#58a6ff", width=2)

            # Text badges
            lbl_l = prepare_arabic_for_rendering("الأصل (Before)" if self.is_ar else "Before")
            lbl_r = prepare_arabic_for_rendering("بعد التصحيح (After)" if self.is_ar else "After")
            badge_h = max(24, int(h * 0.045))
            badge_w_l = max(110, int(w * 0.15))
            badge_w_r = max(135, int(w * 0.17))
            draw.rectangle([10, 10, 10 + badge_w_l, 10 + badge_h], fill="#1c2128", outline="#58a6ff")
            draw.text((16, 14), lbl_l, fill="#ffffff")
            draw.rectangle([w - badge_w_r - 10, 10, w - 10, 10 + badge_h], fill="#1c2128", outline="#2ea043")
            draw.text((w - badge_w_r + 6, 14), lbl_r, fill="#ffffff")

        # Fit into canvas
        iw, ih = disp_im.size
        aspect = iw / max(ih, 1)
        target_h = ch - 12
        target_w = int(target_h * aspect)
        if target_w > cw - 12:
            target_w = cw - 12
            target_h = int(target_w / aspect)

        target_w = max(10, target_w)
        target_h = max(10, target_h)

        scaled_im = disp_im.resize((target_w, target_h), Image.Resampling.BILINEAR)
        self.photo_image = ImageTk.PhotoImage(scaled_im)

        self.preview_canvas.delete("all")
        cx = cw // 2
        cy = ch // 2
        self.preview_canvas.create_image(cx, cy, image=self.photo_image)

        # Record canvas geometry for mouse interaction
        self._canvas_img_w = target_w
        self._canvas_img_h = target_h
        self._canvas_img_x0 = cx - (target_w // 2)
        self._canvas_img_y0 = cy - (target_h // 2)

        # Propagate to fullscreen theater dialog if active
        if getattr(self, "_theater_dialog", None) and self._theater_dialog.winfo_exists():
            self._theater_dialog.refresh_preview()

    def _on_canvas_motion(self, event):
        curr_mode = self.preview_mode_var.get()
        if curr_mode != "split" or getattr(self, "_canvas_img_w", 0) <= 0:
            if not getattr(self, "_dragging_split", False):
                self.preview_canvas.config(cursor="")
            return

        split_x = self._canvas_img_x0 + (self._canvas_img_w * self.split_ratio)
        is_near = (abs(event.x - split_x) <= 15) and (self._canvas_img_y0 - 10 <= event.y <= self._canvas_img_y0 + self._canvas_img_h + 10)
        if is_near:
            self.preview_canvas.config(cursor="sb_h_double_arrow")
        elif not getattr(self, "_dragging_split", False):
            self.preview_canvas.config(cursor="")

    def _on_canvas_press(self, event):
        curr_mode = self.preview_mode_var.get()
        if curr_mode != "split" or getattr(self, "_canvas_img_w", 0) <= 0:
            return
        self._dragging_split = True
        self.preview_canvas.config(cursor="sb_h_double_arrow")
        ratio = (event.x - self._canvas_img_x0) / float(self._canvas_img_w)
        self.split_ratio = max(0.01, min(0.99, ratio))
        self._render_preview()

    def _on_canvas_drag(self, event):
        if not getattr(self, "_dragging_split", False) or getattr(self, "_canvas_img_w", 0) <= 0:
            return
        ratio = (event.x - self._canvas_img_x0) / float(self._canvas_img_w)
        self.split_ratio = max(0.01, min(0.99, ratio))
        self._render_preview()

    def _on_canvas_release(self, _event):
        self._dragging_split = False
        self.preview_canvas.config(cursor="")

    def open_fullscreen_preview(self):
        if getattr(self, "_theater_dialog", None) and self._theater_dialog.winfo_exists():
            self._theater_dialog.focus_force()
            return
        self._theater_dialog = ColorTheaterDialog(self)

    def run_auto_correction(self):
        """Runs the intelligent multi-zone auto color balance analysis."""
        if self.base_image is None:
            return

        mode_key = getattr(self, "_auto_mode_map", {}).get(self.auto_mode_var.get(), "balanced")
        video_p = getattr(self.app, "input_path", None)

        if video_p and Path(video_p).is_file():
            import convert
            suggested_cfg, s_ar, s_en, diag_ar, diag_en = analyze_video_multi_frame(
                video_p,
                num_samples=5,
                intensity=mode_key,
                ffmpeg_exe=str(convert.ffmpeg_executable()),
                fallback_image=self.base_image,
            )
        else:
            suggested_cfg, s_ar, s_en, diag_ar, diag_en = auto_analyze_and_correct(self.base_image, intensity=mode_key)

        # Apply suggested values to sliders
        self.enabled_var.set(True)
        self.brightness_var.set(suggested_cfg["brightness"])
        self.contrast_var.set(suggested_cfg["contrast"])
        self.saturation_var.set(suggested_cfg["saturation"])
        self.gamma_var.set(suggested_cfg["gamma"])
        self.temperature_var.set(suggested_cfg["temperature"])
        self.red_var.set(suggested_cfg["red"])
        self.green_var.set(suggested_cfg["green"])
        self.blue_var.set(suggested_cfg["blue"])

        self._refresh_all_value_labels()
        self._schedule_preview()

        # Display diagnosis badge with bullet points
        diag_list = diag_ar if self.is_ar else diag_en
        summary_txt = " • ".join(diag_list[:3]) if diag_list else (s_ar if self.is_ar else s_en)
        self.diagnosis_text_var.set("✅ " + summary_txt)

    def apply_preset(self, preset_key: str):
        if preset_key not in COLOR_PRESETS:
            return
        p_cfg = COLOR_PRESETS[preset_key]["config"]
        self.enabled_var.set(p_cfg.get("enabled", True))
        self.brightness_var.set(p_cfg.get("brightness", 0.0))
        self.contrast_var.set(p_cfg.get("contrast", 1.0))
        self.saturation_var.set(p_cfg.get("saturation", 1.0))
        self.gamma_var.set(p_cfg.get("gamma", 1.0))
        self.temperature_var.set(p_cfg.get("temperature", 0.0))
        self.red_var.set(p_cfg.get("red", 0.0))
        self.green_var.set(p_cfg.get("green", 0.0))
        self.blue_var.set(p_cfg.get("blue", 0.0))

        label_txt = COLOR_PRESETS[preset_key]["label_ar"] if self.is_ar else COLOR_PRESETS[preset_key]["label_en"]
        self.diagnosis_text_var.set(f"🎨 {label_txt}")
        self._refresh_all_value_labels()
        self._schedule_preview()

    def reset_all(self):
        self.enabled_var.set(True)
        self.brightness_var.set(0.0)
        self.contrast_var.set(1.0)
        self.saturation_var.set(1.0)
        self.gamma_var.set(1.0)
        self.temperature_var.set(0.0)
        self.red_var.set(0.0)
        self.green_var.set(0.0)
        self.blue_var.set(0.0)
        self.diagnosis_text_var.set("↺ " + ("تمت إعادة الضبط للوضع الطبيعي" if self.is_ar else "Reset to neutral default"))
        self._refresh_all_value_labels()
        self._schedule_preview()

    def save_and_apply(self):
        """Saves current color config to the app state and persists to settings."""
        cfg = self._get_active_config()

        # Check if values differ from neutral defaults
        b = abs(float(cfg.get("brightness", 0.0)))
        c = abs(float(cfg.get("contrast", 1.0)) - 1.0)
        s = abs(float(cfg.get("saturation", 1.0)) - 1.0)
        g = abs(float(cfg.get("gamma", 1.0)) - 1.0)
        t = abs(float(cfg.get("temperature", 0.0)))
        r = abs(float(cfg.get("red", 0.0)))
        gr = abs(float(cfg.get("green", 0.0)))
        bl = abs(float(cfg.get("blue", 0.0)))
        has_adjustments = (b > 0.005 or c > 0.005 or s > 0.005 or g > 0.005 or t > 0.005 or r > 0.005 or gr > 0.005 or bl > 0.005)

        if has_adjustments or self.enabled_var.get():
            cfg["enabled"] = True
            self.enabled_var.set(True)
            is_active = True
        else:
            cfg["enabled"] = False
            is_active = False

        # Update app branding config
        if not hasattr(self.app, "video_branding_config") or not isinstance(self.app.video_branding_config, dict):
            self.app.video_branding_config = {}

        self.app.video_branding_config["color_config"] = cfg
        if hasattr(self.app, "settings") and isinstance(self.app.settings, dict):
            self.app.settings["video_branding_config"] = self.app.video_branding_config

        # Also synchronize main UI checkbutton if present
        if hasattr(self.app, "trim_color_var"):
            self.app.trim_color_var.set(is_active)

        if hasattr(self.app, "_save_settings"):
            self.app._save_settings()

        if hasattr(self.app, "_refresh_master_export_summary"):
            self.app._refresh_master_export_summary()

        if hasattr(self.app, "apply_video_color_adjustments"):
            self.app.apply_video_color_adjustments(cfg)

        self.destroy()

    def on_cancel(self):
        # Revert live adjustment on the player
        if hasattr(self, "_initial_config") and hasattr(self.app, "apply_video_color_adjustments"):
            self.app.apply_video_color_adjustments(self._initial_config)
        self.destroy()
