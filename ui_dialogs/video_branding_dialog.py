"""
Video Branding, Aspect Ratio & Interactive Transform Dialog
Provides interactive free transform (drag & resize with white bounding box and corner handles)
for Logo watermark and Multiple Text overlays, plus aspect ratio presets (9:16 Reels, 16:9, etc.) with live preview.
Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from video_studio.aspect_ratios import ASPECT_RATIOS, FIT_MODES
from video_studio.branding import (
    BANNER_BG_COLORS,
    BANNER_TEXT_COLORS,
)
from video_studio.arabic_support import prepare_arabic_for_rendering


class VideoBrandingDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.app = getattr(parent, "parent", parent)
        is_ar = self.app.language_var.get() == "العربية"
        self.is_ar = is_ar
        self.title(self.app.text("branding_dialog_title"))
        if hasattr(self.app, "_apply_theme_to_toplevel"):
            self.app._apply_theme_to_toplevel(self)
        self.geometry("820x780")
        self.minsize(740, 680)
        self.transient(parent)
        self.resizable(True, True)

        # Load existing config or defaults
        cfg = dict(getattr(self.app, "video_branding_config", {}))

        # 1. Aspect Ratio state
        self.aspect_ratio_var = tk.StringVar(value=cfg.get("aspect_ratio", "original"))
        self.fit_mode_var = tk.StringVar(value=cfg.get("fit_mode", "crop"))

        # 2. Logo state
        self.logo_enabled_var = tk.BooleanVar(value=cfg.get("logo_enabled", False))
        self.logo_path_var = tk.StringVar(value=cfg.get("logo_path", ""))
        self.logo_x = float(cfg.get("logo_x", 0.82))
        self.logo_y = float(cfg.get("logo_y", 0.04))
        self.logo_scale_var = tk.DoubleVar(value=float(cfg.get("logo_scale", 0.16)))
        self.logo_opacity_var = tk.DoubleVar(value=float(cfg.get("logo_opacity", 0.85)))

        # 3. Multiple Text Overlays state
        self.text_items = []
        raw_items = cfg.get("text_items")
        if isinstance(raw_items, list) and raw_items:
            for item in raw_items:
                if isinstance(item, dict):
                    merged = dict(item)
                    merged["id"] = str(item.get("id", f"t_{len(self.text_items)+1}"))
                    merged["text"] = str(item.get("text", ""))
                    merged["x"] = float(item.get("x", item.get("x_pct", 0.5)))
                    merged["y"] = float(item.get("y", item.get("y_pct", 0.1)))
                    merged["font_size"] = int(item.get("font_size", 34))
                    merged["bg_color"] = str(item.get("bg_color", "black"))
                    merged["text_color"] = str(item.get("text_color", "white"))
                    merged["enabled"] = bool(item.get("enabled", True))
                    self.text_items.append(merged)
        elif cfg.get("title_text"):
            # Migrate legacy single title
            self.text_items.append({
                "id": "t_1",
                "text": str(cfg.get("title_text", "")),
                "x": 0.5,
                "y": 0.08 if cfg.get("title_position", "top") == "top" else 0.88,
                "font_size": 34,
                "bg_color": str(cfg.get("title_bg", "black")),
                "text_color": str(cfg.get("title_color", "white")),
                "enabled": bool(cfg.get("title_enabled", True)),
            })

        if not self.text_items:
            # Starter empty text item
            self.text_items.append({
                "id": "t_1",
                "text": "عنوان الفيديو الرئيسي",
                "x": 0.5,
                "y": 0.08,
                "font_size": 34,
                "bg_color": "black",
                "text_color": "white",
                "enabled": False,
            })

        self.current_text_index = 0

        # 4. Subtitle Burning state
        self.burn_subs_var = tk.BooleanVar(value=cfg.get("burn_subtitles", True))

        # Interactive Transform tracking state
        self.selected_element = None  # "logo" or f"text_{idx}"
        self.drag_mode = None  # None, "move", or handle name: "tl", "tr", "bl", "br"
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_item_orig_x = 0.0
        self.drag_item_orig_y = 0.0
        self.drag_item_orig_scale = 0.0
        self.canvas_element_boxes = {}

        self._build_ui()
        self.after(50, self._update_preview)

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

        # Top Bar: Aspect Ratio & Fit Mode
        top_card = ttk.LabelFrame(container, text="📐 " + self.app.text("branding_aspect_group"), padding=(10, 6))
        top_card.pack(fill="x", pady=(0, 6))
        top_card.columnconfigure(1, weight=1)
        top_card.columnconfigure(3, weight=1)

        ttk.Label(top_card, text=self.app.text("branding_aspect_ratio")).grid(row=0, column=0, sticky="w", padx=(0, 6))

        ratio_display_vals = [
            (k, info["label_ar"] if self.is_ar else info["label_en"])
            for k, info in ASPECT_RATIOS.items()
        ]
        self.ratio_map = {disp: k for k, disp in ratio_display_vals}
        self.ratio_rev = {k: disp for k, disp in ratio_display_vals}

        cur_ratio_label = self.ratio_rev.get(self.aspect_ratio_var.get(), ratio_display_vals[0][1])
        self.ratio_combo_var = tk.StringVar(value=cur_ratio_label)
        self.ratio_combo = ttk.Combobox(
            top_card,
            textvariable=self.ratio_combo_var,
            values=[d[1] for d in ratio_display_vals],
            state="readonly",
            width=24,
        )
        self.ratio_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        self.ratio_combo.bind("<<ComboboxSelected>>", self._on_ratio_changed)

        ttk.Label(top_card, text=self.app.text("branding_fit_mode")).grid(row=0, column=2, sticky="w", padx=(0, 6))

        fit_display_vals = [
            (k, info["label_ar"] if self.is_ar else info["label_en"])
            for k, info in FIT_MODES.items()
        ]
        self.fit_map = {disp: k for k, disp in fit_display_vals}
        self.fit_rev = {k: disp for k, disp in fit_display_vals}

        cur_fit_label = self.fit_rev.get(self.fit_mode_var.get(), fit_display_vals[0][1])
        self.fit_combo_var = tk.StringVar(value=cur_fit_label)
        self.fit_combo = ttk.Combobox(
            top_card,
            textvariable=self.fit_combo_var,
            values=[d[1] for d in fit_display_vals],
            state="readonly",
            width=22,
        )
        self.fit_combo.grid(row=0, column=3, sticky="ew")
        self.fit_combo.bind("<<ComboboxSelected>>", self._on_fit_changed)

        # Middle: Interactive Canvas Preview (Supports mouse drag & resize!)
        prev_card = ttk.LabelFrame(container, text="🎬 " + self.app.text("branding_preview_title"), padding=(4, 4))
        prev_card.pack(fill="both", expand=True, pady=(0, 6))

        hint_txt = "💡 " + ("انقر على اللوجو أو النص لتحريكه بحرية بالماوس وتكبيره وتصغيره من الأركان البيضاء" if self.is_ar else "Click logo or text to drag and resize freely with corner handles")
        lbl_hint = ttk.Label(prev_card, text=hint_txt, font=("Segoe UI", 8, "italic"), foreground="#57606a")
        lbl_hint.pack(anchor="w", padx=6, pady=(0, 2))

        self.preview_canvas = tk.Canvas(prev_card, bg="#0d1117", height=230, highlightthickness=1, highlightbackground="#30363d")
        self.preview_canvas.pack(fill="both", expand=True)

        # Bind Interactive Mouse Events on Canvas
        self.preview_canvas.bind("<Configure>", lambda _e: self._update_preview())
        self.preview_canvas.bind("<Button-1>", self._on_canvas_press)
        self.preview_canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.preview_canvas.bind("<Motion>", self._on_canvas_hover)

        # Notebook tabs for Logo, Text Overlays, and Subtitles
        nb = ttk.Notebook(container)
        nb.pack(fill="x", pady=(0, 8))

        # Tab 1: Logo Watermark
        tab_logo = ttk.Frame(nb, padding=10)
        nb.add(tab_logo, text="🛡️ " + self.app.text("branding_logo_group"))
        self._build_tab_logo(tab_logo)

        # Tab 2: Multiple Text Overlays
        tab_texts = ttk.Frame(nb, padding=10)
        nb.add(tab_texts, text="🏷️ " + ("النصوص والعناوين المتعددة" if self.is_ar else "Multiple Text Overlays"))
        self._build_tab_texts(tab_texts)

        # Tab 3: Subtitles Option
        tab_subs = ttk.Frame(nb, padding=10)
        nb.add(tab_subs, text="💬 " + self.app.text("caption_settings_group"))
        self._build_tab_subs(tab_subs)

        # Bottom Bar: Save / Reset / Close
        btn_box = ttk.Frame(container)
        btn_box.pack(fill="x")

        self.btn_save = ttk.Button(
            btn_box,
            text="💾 " + self.app.text("sub_save_apply"),
            command=self._save_and_apply,
            style="Action.TButton",
        )
        self.btn_save.pack(side="left" if not self.is_ar else "right", padx=(0, 8))

        self.btn_reset = ttk.Button(
            btn_box,
            text="🔄 " + self.app.text("sub_reset_defaults"),
            command=self._reset_defaults,
            style="Player.TButton",
        )
        self.btn_reset.pack(side="left" if not self.is_ar else "right", padx=(0, 8))

        self.btn_color = ttk.Button(
            btn_box,
            text="🎨 " + ("تصحيح ألوان الفيديو..." if self.is_ar else "Color Grading..."),
            command=self._open_color_dialog,
            style="Player.TButton",
        )
        self.btn_color.pack(side="left" if not self.is_ar else "right", padx=(0, 8))

        self.btn_close = ttk.Button(
            btn_box,
            text=self.app.text("close"),
            command=self.destroy,
            style="Player.TButton",
        )
        self.btn_close.pack(side="right" if not self.is_ar else "left")

    def _open_color_dialog(self):
        from .video_color_dialog import VideoColorDialog
        VideoColorDialog(self)

    def _build_tab_logo(self, parent):
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(3, weight=1)

        chk_logo = ttk.Checkbutton(
            parent,
            text=self.app.text("branding_logo_enable"),
            variable=self.logo_enabled_var,
            command=self._update_preview,
        )
        chk_logo.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        path_row = ttk.Frame(parent)
        path_row.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(0, 6))
        path_row.columnconfigure(1, weight=1)

        ttk.Label(path_row, text=self.app.text("branding_logo_file")).grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.entry_logo = ttk.Entry(path_row, textvariable=self.logo_path_var)
        self.entry_logo.grid(row=0, column=1, sticky="ew", padx=(0, 6))
        btn_browse = ttk.Button(path_row, text=self.app.text("choose_file"), command=self._choose_logo_file, style="Player.TButton")
        btn_browse.grid(row=0, column=2)

        ctrl_row = ttk.Frame(parent)
        ctrl_row.grid(row=2, column=0, columnspan=4, sticky="ew")
        ctrl_row.columnconfigure(1, weight=1)
        ctrl_row.columnconfigure(3, weight=1)

        ttk.Label(ctrl_row, text=("حجم اللوجو:" if self.is_ar else "Logo Size:")).grid(row=0, column=0, sticky="w", padx=(0, 6))
        scale_slider = ttk.Scale(ctrl_row, from_=0.06, to=0.45, variable=self.logo_scale_var, orient="horizontal", command=lambda _v: self._update_preview())
        scale_slider.grid(row=0, column=1, sticky="ew", padx=(0, 14))

        ttk.Label(ctrl_row, text=self.app.text("branding_logo_opacity")).grid(row=0, column=2, sticky="w", padx=(0, 6))
        scale_op = ttk.Scale(ctrl_row, from_=0.15, to=1.0, variable=self.logo_opacity_var, orient="horizontal", command=lambda _v: self._update_preview())
        scale_op.grid(row=0, column=3, sticky="ew")

        # Quick reset logo position button
        btn_reset_pos = ttk.Button(
            parent,
            text="↺ " + ("وضع اللوجو في أعلى اليمين" if self.is_ar else "Reset Logo to Top-Right"),
            command=self._reset_logo_position,
            style="Player.TButton",
        )
        btn_reset_pos.grid(row=3, column=0, columnspan=4, sticky="w", pady=(8, 0))

    def _build_tab_texts(self, parent):
        parent.columnconfigure(1, weight=1)

        # Header with Add Text button and Selector
        header_row = ttk.Frame(parent)
        header_row.pack(fill="x", pady=(0, 6))

        ttk.Label(header_row, text=("اختر النص للتعديل:" if self.is_ar else "Select Text to Edit:")).pack(side="left", padx=(0, 8))

        self.text_selector_var = tk.StringVar()
        self.combo_text_selector = ttk.Combobox(header_row, textvariable=self.text_selector_var, state="readonly", width=22)
        self.combo_text_selector.pack(side="left", padx=(0, 10))
        self.combo_text_selector.bind("<<ComboboxSelected>>", self._on_text_selected)

        btn_add = ttk.Button(
            header_row,
            text="➕ " + ("إضافة نص جديد" if self.is_ar else "Add New Text"),
            command=self._add_new_text_item,
            style="Player.TButton",
        )
        btn_add.pack(side="left", padx=(0, 8))

        self.btn_del_text = ttk.Button(
            header_row,
            text="🗑️ " + ("حذف هذا النص" if self.is_ar else "Delete Text"),
            command=self._delete_current_text_item,
            style="Player.TButton",
        )
        self.btn_del_text.pack(side="right")

        # Active Item Editor Card
        editor_frame = ttk.LabelFrame(parent, padding=8)
        editor_frame.pack(fill="x", pady=(4, 0))
        editor_frame.columnconfigure(1, weight=1)
        editor_frame.columnconfigure(3, weight=1)

        # Row 1: Enable & Text string
        self.cur_text_enabled_var = tk.BooleanVar(value=True)
        chk_item_en = ttk.Checkbutton(
            editor_frame,
            text=("تفعيل هذا النص" if self.is_ar else "Enable this text"),
            variable=self.cur_text_enabled_var,
            command=self._on_cur_text_edited,
        )
        chk_item_en.grid(row=0, column=0, sticky="w", padx=(0, 10), pady=4)

        ttk.Label(editor_frame, text=self.app.text("branding_title_text")).grid(row=0, column=1, sticky="w", padx=(0, 6))
        self.cur_text_content_var = tk.StringVar()
        self.entry_cur_text = ttk.Entry(editor_frame, textvariable=self.cur_text_content_var)
        self.entry_cur_text.grid(row=0, column=2, columnspan=2, sticky="ew", pady=4)
        self.cur_text_content_var.trace_add("write", lambda *_: self._on_cur_text_edited())

        # Row 2: Styling (Colors & Size)
        ttk.Label(editor_frame, text=self.app.text("branding_title_bg")).grid(row=1, column=0, sticky="w", padx=(0, 6), pady=4)

        bg_vals = [
            (k, info["label_ar"] if self.is_ar else info["label_en"])
            for k, info in BANNER_BG_COLORS.items()
        ]
        self.bg_map = {disp: k for k, disp in bg_vals}
        self.bg_rev = {k: disp for k, disp in bg_vals}

        self.cur_bg_combo_var = tk.StringVar()
        self.combo_cur_bg = ttk.Combobox(
            editor_frame,
            textvariable=self.cur_bg_combo_var,
            values=[b[1] for b in bg_vals],
            state="readonly",
            width=18,
        )
        self.combo_cur_bg.grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=4)
        self.combo_cur_bg.bind("<<ComboboxSelected>>", lambda _e: self._on_cur_text_edited())

        ttk.Label(editor_frame, text=self.app.text("branding_title_color")).grid(row=1, column=2, sticky="w", padx=(0, 6), pady=4)

        fg_vals = [
            (k, info["label_ar"] if self.is_ar else info["label_en"])
            for k, info in BANNER_TEXT_COLORS.items()
        ]
        self.fg_map = {disp: k for k, disp in fg_vals}
        self.fg_rev = {k: disp for k, disp in fg_vals}

        self.cur_fg_combo_var = tk.StringVar()
        self.combo_cur_fg = ttk.Combobox(
            editor_frame,
            textvariable=self.cur_fg_combo_var,
            values=[f[1] for f in fg_vals],
            state="readonly",
            width=18,
        )
        self.combo_cur_fg.grid(row=1, column=3, sticky="ew", pady=4)
        self.combo_cur_fg.bind("<<ComboboxSelected>>", lambda _e: self._on_cur_text_edited())

        # Row 3: Font Size
        ttk.Label(editor_frame, text=("حجم الخط:" if self.is_ar else "Font Size:")).grid(row=2, column=0, sticky="w", padx=(0, 6), pady=4)
        self.cur_font_size_var = tk.IntVar(value=34)
        scale_fsize = ttk.Scale(
            editor_frame,
            from_=18,
            to=72,
            variable=self.cur_font_size_var,
            orient="horizontal",
            command=lambda _v: self._on_cur_text_edited(),
        )
        scale_fsize.grid(row=2, column=1, sticky="ew", padx=(0, 12), pady=4)

        self._refresh_text_selector_combo()

    def _build_tab_subs(self, parent):
        chk_subs = ttk.Checkbutton(
            parent,
            text=self.app.text("branding_burn_subtitles_chk"),
            variable=self.burn_subs_var,
            command=self._update_preview,
        )
        chk_subs.pack(side="left" if not self.is_ar else "right", padx=(0, 14), pady=6)

        btn_style = ttk.Button(
            parent,
            text="🎨 " + self.app.text("caption_style_btn"),
            command=self._open_subtitle_style,
            style="Player.TButton",
        )
        btn_style.pack(side="left" if not self.is_ar else "right", pady=6)

    def _refresh_text_selector_combo(self):
        titles = []
        for i, item in enumerate(self.text_items):
            preview = item.get("text", "").strip() or ("نص فارغ" if self.is_ar else "Empty text")
            if len(preview) > 18:
                preview = preview[:16] + "..."
            status = "✓" if item.get("enabled", True) else "✗"
            titles.append(f"{i+1}: [{status}] {preview}")

        self.combo_text_selector.configure(values=titles)
        if 0 <= self.current_text_index < len(titles):
            self.combo_text_selector.current(self.current_text_index)
            self._load_active_text_into_ui()
        elif titles:
            self.current_text_index = 0
            self.combo_text_selector.current(0)
            self._load_active_text_into_ui()

    def _load_active_text_into_ui(self):
        if not (0 <= self.current_text_index < len(self.text_items)):
            return
        item = self.text_items[self.current_text_index]
        self.cur_text_enabled_var.set(item.get("enabled", True))
        self.cur_text_content_var.set(item.get("text", ""))

        bg_label = self.bg_rev.get(item.get("bg_color", "black"), "")
        self.cur_bg_combo_var.set(bg_label)

        fg_label = self.fg_rev.get(item.get("text_color", "white"), "")
        self.cur_fg_combo_var.set(fg_label)

        self.cur_font_size_var.set(item.get("font_size", 34))

    def _on_text_selected(self, _e=None):
        idx = self.combo_text_selector.current()
        if idx >= 0:
            self.current_text_index = idx
            self.selected_element = f"text_{idx}"
            self._load_active_text_into_ui()
            self._update_preview()

    def _on_cur_text_edited(self):
        if not (0 <= self.current_text_index < len(self.text_items)):
            return
        item = self.text_items[self.current_text_index]
        item["enabled"] = bool(self.cur_text_enabled_var.get())
        item["text"] = self.cur_text_content_var.get()
        item["bg_color"] = self.bg_map.get(self.cur_bg_combo_var.get(), "black")
        item["text_color"] = self.fg_map.get(self.cur_fg_combo_var.get(), "white")
        item["font_size"] = int(self.cur_font_size_var.get())
        self._update_preview()

    def _add_new_text_item(self):
        new_idx = len(self.text_items) + 1
        new_item = {
            "id": f"t_{new_idx}",
            "text": f"نص {new_idx}" if self.is_ar else f"Text {new_idx}",
            "x": 0.5,
            "y": min(0.85, 0.15 + (new_idx - 1) * 0.12),
            "font_size": 34,
            "bg_color": "black",
            "text_color": "yellow" if new_idx % 2 == 0 else "white",
            "enabled": True,
        }
        self.text_items.append(new_item)
        self.current_text_index = len(self.text_items) - 1
        self.selected_element = f"text_{self.current_text_index}"
        self._refresh_text_selector_combo()
        self._update_preview()

    def _delete_current_text_item(self):
        if len(self.text_items) <= 1:
            # Just clear text if only 1
            self.text_items[0]["text"] = ""
            self.text_items[0]["enabled"] = False
            self._refresh_text_selector_combo()
            self._update_preview()
            return
        del self.text_items[self.current_text_index]
        self.current_text_index = max(0, self.current_text_index - 1)
        self.selected_element = f"text_{self.current_text_index}"
        self._refresh_text_selector_combo()
        self._update_preview()

    def _reset_logo_position(self):
        self.logo_x = 0.82
        self.logo_y = 0.04
        self.logo_scale_var.set(0.16)
        self.selected_element = "logo"
        self._update_preview()

    def _choose_logo_file(self):
        types = [
            ("Image files", "*.png *.jpg *.jpeg *.webp *.bmp"),
            ("PNG Transparent", "*.png"),
            ("All files", "*.*"),
        ]
        chosen = filedialog.askopenfilename(
            parent=self,
            title=self.app.text("branding_logo_file"),
            filetypes=types,
        )
        if chosen:
            self.logo_path_var.set(chosen)
            self.logo_enabled_var.set(True)
            self.selected_element = "logo"
            self._update_preview()

    def _on_ratio_changed(self, _e=None):
        disp = self.ratio_combo_var.get()
        self.aspect_ratio_var.set(self.ratio_map.get(disp, "original"))
        self._update_preview()

    def _on_fit_changed(self, _e=None):
        disp = self.fit_combo_var.get()
        self.fit_mode_var.set(self.fit_map.get(disp, "blur"))
        self._update_preview()

    def _open_subtitle_style(self):
        from .subtitle_style_dialog import SubtitleStyleDialog
        dlg = SubtitleStyleDialog(self)
        dlg.wait_window()
        self._update_preview()

    # ----------------------------------------------------
    # Interactive Canvas Mouse Transform (Move & Resize)
    # ----------------------------------------------------
    def _on_canvas_press(self, event):
        mx, my = event.x, event.y
        self.drag_start_x = mx
        self.drag_start_y = my

        # 1. Check if clicked on a corner handle of the currently selected element
        if self.selected_element in self.canvas_element_boxes:
            box = self.canvas_element_boxes[self.selected_element]
            for h_name, (hx, hy) in box["handles"].items():
                if abs(mx - hx) <= 8 and abs(my - hy) <= 8:
                    self.drag_mode = h_name
                    if self.selected_element == "logo":
                        self.drag_item_orig_scale = float(self.logo_scale_var.get())
                    elif self.selected_element.startswith("text_"):
                        t_idx = int(self.selected_element.split("_")[1])
                        self.drag_item_orig_scale = self.text_items[t_idx].get("font_size", 34)
                    return

        # 2. Check if clicked inside any element (Text or Logo)
        clicked_elem = None
        for elem_id, box in reversed(list(self.canvas_element_boxes.items())):
            x0, y0, x1, y1 = box["rect"]
            if x0 <= mx <= x1 and y0 <= my <= y1:
                clicked_elem = elem_id
                break

        if clicked_elem:
            self.selected_element = clicked_elem
            self.drag_mode = "move"
            if clicked_elem == "logo":
                self.drag_item_orig_x = self.logo_x
                self.drag_item_orig_y = self.logo_y
            elif clicked_elem.startswith("text_"):
                t_idx = int(clicked_elem.split("_")[1])
                self.current_text_index = t_idx
                self.drag_item_orig_x = self.text_items[t_idx].get("x", 0.5)
                self.drag_item_orig_y = self.text_items[t_idx].get("y", 0.1)
                self._load_active_text_into_ui()
                self.combo_text_selector.current(t_idx)
            self._update_preview()
        else:
            # Clicked outside
            self.selected_element = None
            self.drag_mode = None
            self._update_preview()

    def _on_canvas_drag(self, event):
        if not self.drag_mode or not self.selected_element:
            return

        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()
        if not hasattr(self, "_canvas_video_box"):
            return
        vx0, vy0, vx1, vy1 = self._canvas_video_box
        vw = max(1, vx1 - vx0)
        vh = max(1, vy1 - vy0)

        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y

        if self.drag_mode == "move":
            # Translate position
            delta_x_pct = dx / vw
            delta_y_pct = dy / vh

            if self.selected_element == "logo":
                new_x = max(0.0, min(0.95, self.drag_item_orig_x + delta_x_pct))
                new_y = max(0.0, min(0.95, self.drag_item_orig_y + delta_y_pct))
                self.logo_x = new_x
                self.logo_y = new_y
            elif self.selected_element.startswith("text_"):
                t_idx = int(self.selected_element.split("_")[1])
                new_x = max(0.05, min(0.95, self.drag_item_orig_x + delta_x_pct))
                new_y = max(0.02, min(0.98, self.drag_item_orig_y + delta_y_pct))
                self.text_items[t_idx]["x"] = new_x
                self.text_items[t_idx]["y"] = new_y

            self._update_preview()

        elif self.drag_mode in ("tl", "tr", "bl", "br"):
            # Resize / Scale
            dist_delta = (dx + dy) / 2.0
            if "t" in self.drag_mode or "l" in self.drag_mode:
                dist_delta = -dist_delta

            if self.selected_element == "logo":
                scale_delta = dist_delta / vw
                new_scale = max(0.06, min(0.55, self.drag_item_orig_scale + scale_delta))
                self.logo_scale_var.set(round(new_scale, 3))
            elif self.selected_element.startswith("text_"):
                t_idx = int(self.selected_element.split("_")[1])
                font_delta = int(dist_delta * 0.4)
                new_font = max(18, min(80, int(self.drag_item_orig_scale + font_delta)))
                self.text_items[t_idx]["font_size"] = new_font
                self.cur_font_size_var.set(new_font)

            self._update_preview()

    def _on_canvas_release(self, _e):
        self.drag_mode = None
        self._refresh_text_selector_combo()

    def _on_canvas_hover(self, event):
        mx, my = event.x, event.y
        new_cursor = "arrow"

        if self.selected_element in self.canvas_element_boxes:
            box = self.canvas_element_boxes[self.selected_element]
            for h_name, (hx, hy) in box["handles"].items():
                if abs(mx - hx) <= 8 and abs(my - hy) <= 8:
                    if h_name in ("tl", "br"):
                        new_cursor = "size_nw_se"
                    else:
                        new_cursor = "size_ne_sw"
                    self.preview_canvas.configure(cursor=new_cursor)
                    return

            x0, y0, x1, y1 = box["rect"]
            if x0 <= mx <= x1 and y0 <= my <= y1:
                new_cursor = "fleur"
                self.preview_canvas.configure(cursor=new_cursor)
                return

        for elem_id, box in self.canvas_element_boxes.items():
            x0, y0, x1, y1 = box["rect"]
            if x0 <= mx <= x1 and y0 <= my <= y1:
                new_cursor = "fleur"
                break

        self.preview_canvas.configure(cursor=new_cursor)

    # ----------------------------------------------------
    # Live Canvas Renderer
    # ----------------------------------------------------
    def _update_preview(self):
        if not hasattr(self, "preview_canvas") or not self.preview_canvas.winfo_exists():
            return

        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()
        if cw < 60:
            cw = 760
        if ch < 50:
            ch = 230

        self.preview_canvas.delete("all")
        self.canvas_element_boxes = {}

        # Dark base canvas background
        self.preview_canvas.create_rectangle(0, 0, cw, ch, fill="#0d1117", outline="")

        # Compute aspect ratio dimensions
        ratio_key = self.aspect_ratio_var.get()
        fit_mode = self.fit_mode_var.get()

        if ratio_key == "9:16":
            target_aspect = 9 / 16
        elif ratio_key == "1:1":
            target_aspect = 1.0
        elif ratio_key == "4:5":
            target_aspect = 4 / 5
        elif ratio_key == "4:3":
            target_aspect = 4 / 3
        else:
            target_aspect = 16 / 9

        pad_y = 12
        box_h = ch - (pad_y * 2)
        box_w = int(box_h * target_aspect)
        if box_w > cw - 30:
            box_w = cw - 30
            box_h = int(box_w / target_aspect)

        bx0 = (cw - box_w) // 2
        by0 = (ch - box_h) // 2
        bx1 = bx0 + box_w
        by1 = by0 + box_h
        self._canvas_video_box = (bx0, by0, bx1, by1)

        # Draw Video Frame container
        if fit_mode == "blur" and ratio_key != "16:9" and ratio_key != "original":
            # Blurred background simulation
            self.preview_canvas.create_rectangle(bx0, by0, bx1, by1, fill="#1c2533", outline="#30363d", width=2)
            fg_h = int(box_w / (16 / 9))
            fg_y0 = by0 + (box_h - fg_h) // 2
            fg_y1 = fg_y0 + fg_h
            self.preview_canvas.create_rectangle(bx0, fg_y0, bx1, fg_y1, fill="#2b3a4e", outline="#44556b", width=1)
            self.preview_canvas.create_text((bx0 + bx1) // 2, (fg_y0 + fg_y1) // 2, text="🎥 Original Video", fill="#8b949e", font=("Segoe UI", 9))
        else:
            self.preview_canvas.create_rectangle(bx0, by0, bx1, by1, fill="#161b22", outline="#30363d", width=2)
            self.preview_canvas.create_text((bx0 + bx1) // 2, (by0 + by1) // 2, text="🎥 Video Content", fill="#57606a", font=("Segoe UI", 9))

        # Ratio badge
        ratio_label_txt = ratio_key.upper() if ratio_key != "original" else "ORIGINAL"
        self.preview_canvas.create_text(bx0 + 8, by0 + 8, text=f"[{ratio_label_txt}]", anchor="nw", fill="#58a6ff", font=("Segoe UI", 8, "bold"))

        # Render Multiple Text Overlays
        for idx, item in enumerate(self.text_items):
            if not item.get("enabled", True):
                continue
            raw_text = item.get("text", "").strip() or ("نص تجريبي" if self.is_ar else "Sample Text")
            bg_key = item.get("bg_color", "black")
            fg_key = item.get("text_color", "white")
            bg_info = BANNER_BG_COLORS.get(bg_key, BANNER_BG_COLORS["black"])
            fg_hex = BANNER_TEXT_COLORS.get(fg_key, BANNER_TEXT_COLORS["white"])["hex"]
            is_transparent = (bg_key == "transparent")

            f_size = max(8, min(24, int(item.get("font_size", 34) * (box_w / 350.0))))

            # Measure text on canvas
            approx_tw = max(30, int(len(raw_text) * (f_size * 0.6)))
            approx_th = max(18, int(f_size * 1.5))

            item_x_pct = float(item.get("x", 0.5))
            item_y_pct = float(item.get("y", 0.1))

            cx = bx0 + int(box_w * item_x_pct)
            cy = by0 + int(box_h * item_y_pct)

            tx0 = cx - (approx_tw // 2)
            ty0 = cy - (approx_th // 2)
            tx1 = tx0 + approx_tw
            ty1 = ty0 + approx_th

            # Draw card background if not transparent
            if not is_transparent:
                bg_hex = bg_info.get("hex", "#141414")
                self.preview_canvas.create_rectangle(tx0, ty0, tx1, ty1, fill=bg_hex, outline="#30363d", width=1)

            # Draw text
            canvas_text = prepare_arabic_for_rendering(raw_text)
            self.preview_canvas.create_text(cx, cy, text=canvas_text, fill=fg_hex, font=("Segoe UI", f_size, "bold"))

            elem_id = f"text_{idx}"
            self.canvas_element_boxes[elem_id] = {
                "rect": (tx0, ty0, tx1, ty1),
                "handles": {
                    "tl": (tx0, ty0),
                    "tr": (tx1, ty0),
                    "bl": (tx0, ty1),
                    "br": (tx1, ty1),
                }
            }

        # Render Logo Watermark (if enabled)
        if self.logo_enabled_var.get():
            l_scale = float(self.logo_scale_var.get())
            lw = max(24, min(int(box_w * 0.9), int(box_w * l_scale)))
            lh = max(16, int(lw * 0.55))

            lx0 = bx0 + int(box_w * self.logo_x)
            ly0 = by0 + int(box_h * self.logo_y)
            lx1 = lx0 + lw
            ly1 = ly0 + lh

            # Draw Logo box with badge
            self.preview_canvas.create_rectangle(lx0, ly0, lx1, ly1, fill="#e5534b", outline="#ffffff", width=1)
            self.preview_canvas.create_text((lx0 + lx1) // 2, (ly0 + ly1) // 2, text="LOGO", fill="#ffffff", font=("Segoe UI", 8, "bold"))

            self.canvas_element_boxes["logo"] = {
                "rect": (lx0, ly0, lx1, ly1),
                "handles": {
                    "tl": (lx0, ly0),
                    "tr": (lx1, ly0),
                    "bl": (lx0, ly1),
                    "br": (lx1, ly1),
                }
            }

        # Draw Subtitles Sample (if enabled)
        if self.burn_subs_var.get():
            sub_y = by1 - 22
            sub_col_key = getattr(self.app, "subtitle_style", {}).get("text_color", "yellow")
            col_hex = "#FFE600" if sub_col_key == "yellow" else "#FFFFFF"
            sub_sample = self.app.text("branding_subs_sample")

            tw = len(sub_sample) * 6
            self.preview_canvas.create_rectangle(
                (bx0 + bx1) // 2 - tw // 2 - 8,
                sub_y - 8,
                (bx0 + bx1) // 2 + tw // 2 + 8,
                sub_y + 8,
                fill="#161b22",
                outline="#30363d",
                width=1,
            )
            canvas_sub = prepare_arabic_for_rendering(sub_sample)
            self.preview_canvas.create_text((bx0 + bx1) // 2, sub_y, text=canvas_sub, fill=col_hex, font=("Segoe UI", 8, "bold"))

        # ----------------------------------------------------
        # Draw White Bounding Box & Corner Handles on Active Item
        # ----------------------------------------------------
        if self.selected_element in self.canvas_element_boxes:
            box = self.canvas_element_boxes[self.selected_element]
            rx0, ry0, rx1, ry1 = box["rect"]

            # Crisp white dashed/solid bounding box
            self.preview_canvas.create_rectangle(
                rx0 - 2, ry0 - 2, rx1 + 2, ry1 + 2,
                outline="#FFFFFF",
                width=2,
                dash=(5, 3),
            )

            # 4 White corner resize square handles
            hs = 4  # half handle size
            for hx, hy in box["handles"].values():
                self.preview_canvas.create_rectangle(
                    hx - hs, hy - hs, hx + hs, hy + hs,
                    fill="#FFFFFF",
                    outline="#000000",
                    width=1,
                )

    def _save_and_apply(self):
        # Format text_items while preserving NLE timing, rotation, opacity, and font_name
        clean_texts = []
        for item in self.text_items:
            t = str(item.get("text", "")).strip()
            if t:
                entry = dict(item)
                xv = float(item.get("x", item.get("x_pct", 0.5)))
                yv = float(item.get("y", item.get("y_pct", 0.1)))
                entry.update({
                    "id": item.get("id", f"v3_{len(clean_texts) + 1}"),
                    "text": t,
                    "x": xv,
                    "y": yv,
                    "x_pct": xv,
                    "y_pct": yv,
                    "font_size": int(item.get("font_size", 34)),
                    "font_name": str(item.get("font_name", "Segoe UI")),
                    "bg_color": str(item.get("bg_color", "black")),
                    "text_color": str(item.get("text_color", "white")),
                    "opacity": float(item.get("opacity", 1.0)),
                    "rotation": float(item.get("rotation", 0.0)),
                    "full_duration": bool(item.get("full_duration", True)),
                    "start_sec": float(item.get("start_sec", 0.0)),
                    "end_sec": float(item.get("end_sec", 5.0)),
                    "enabled": bool(item.get("enabled", True)),
                })
                clean_texts.append(entry)

        # Start from existing config so DaVinci zoom/pan_x/pan_y/flip_h/media_items/logo_items/color_config are preserved!
        cfg = dict(getattr(self.app, "video_branding_config", {}) or {})
        cfg.update({
            "aspect_ratio": self.aspect_ratio_var.get(),
            "fit_mode": self.fit_mode_var.get(),
            "logo_enabled": bool(self.logo_enabled_var.get()),
            "logo_path": self.logo_path_var.get().strip(),
            "logo_x": float(self.logo_x),
            "logo_y": float(self.logo_y),
            "logo_scale": float(self.logo_scale_var.get()),
            "logo_opacity": float(self.logo_opacity_var.get()),
            "text_items": clean_texts,
            "burn_subtitles": bool(self.burn_subs_var.get()),
        })

        # Keep legacy title_text sync for backward compatibility
        if clean_texts:
            cfg["title_enabled"] = any(it.get("enabled", True) for it in clean_texts)
            cfg["title_text"] = clean_texts[0]["text"]
            cfg["title_bg"] = clean_texts[0]["bg_color"]
            cfg["title_color"] = clean_texts[0]["text_color"]
        else:
            cfg["title_enabled"] = False
            cfg["title_text"] = ""

        # Sync NLE tracks if NLEProjectState exists on main window
        if hasattr(self.app, "nle_project"):
            self.app.nle_project.text_items = [dict(it) for it in clean_texts]
            lp = cfg["logo_path"]
            if lp:
                if self.app.nle_project.logo_items:
                    self.app.nle_project.logo_items[0].update({
                        "path": lp,
                        "x": cfg["logo_x"],
                        "y": cfg["logo_y"],
                        "scale": cfg["logo_scale"],
                        "opacity": cfg["logo_opacity"],
                        "enabled": cfg["logo_enabled"],
                    })
                else:
                    self.app.nle_project.logo_items.append({
                        "id": self.app.nle_project.next_id("v4"),
                        "path": lp,
                        "x": cfg["logo_x"],
                        "y": cfg["logo_y"],
                        "anchor": "top_left",
                        "scale": cfg["logo_scale"],
                        "opacity": cfg["logo_opacity"],
                        "rotation": 0.0,
                        "full_duration": True,
                        "start_sec": 0.0,
                        "end_sec": max(5.0, self.app.nle_project.total_duration),
                        "enabled": cfg["logo_enabled"],
                    })

        self.app.video_branding_config = cfg
        self.app.settings["video_branding_config"] = cfg
        self.app._save_settings()

        # Sync controls in main window
        if hasattr(self.app, "trim_aspect_var"):
            self.app.trim_aspect_var.set(cfg["aspect_ratio"])
        if hasattr(self.app, "trim_aspect_combo_var"):
            self.app.trim_aspect_combo_var.set(self.ratio_rev.get(cfg["aspect_ratio"], ""))
        if hasattr(self.app, "fit_mode_combo_var") and hasattr(self.app, "fit_mode_rev"):
            self.app.fit_mode_combo_var.set(self.app.fit_mode_rev.get(cfg["fit_mode"], ""))
        if hasattr(self.app, "trim_burn_subs_var"):
            self.app.trim_burn_subs_var.set(cfg["burn_subtitles"])
        if hasattr(self.app, "trim_logo_var"):
            self.app.trim_logo_var.set(cfg["logo_enabled"])
        if hasattr(self.app, "trim_title_var"):
            self.app.trim_title_var.set(bool(clean_texts and cfg["title_enabled"]))
        if hasattr(self.app, "_refresh_master_export_summary"):
            self.app._refresh_master_export_summary()
        if hasattr(self.app, "apply_video_aspect_ratio"):
            self.app.apply_video_aspect_ratio()

        messagebox.showinfo(self.app.text("app_title"), self.app.text("sub_edits_saved"), parent=self)
        self.destroy()

    def _reset_defaults(self):
        self.aspect_ratio_var.set("original")
        self.fit_mode_var.set("crop")
        self.logo_enabled_var.set(False)
        self.logo_path_var.set("")
        self.logo_x = 0.82
        self.logo_y = 0.04
        self.logo_scale_var.set(0.16)
        self.logo_opacity_var.set(0.85)
        self.burn_subs_var.set(True)
        self.text_items = [{
            "id": "t_1",
            "text": "عنوان الفيديو الرئيسي",
            "x": 0.5,
            "y": 0.08,
            "font_size": 34,
            "bg_color": "black",
            "text_color": "white",
            "enabled": False,
        }]
        self.current_text_index = 0
        self.selected_element = None

        self.ratio_combo_var.set(self.ratio_rev.get("original", ""))
        self.fit_combo_var.set(self.fit_rev.get("crop", ""))
        self._refresh_text_selector_combo()
        self._update_preview()
