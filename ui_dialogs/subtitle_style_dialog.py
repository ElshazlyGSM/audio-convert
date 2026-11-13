"""
Subtitle Style & Position Dialog
Interactive font family, font size, text color, outline styles, alignment, margins and live canvas preview.
Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
from video_studio.arabic_support import prepare_arabic_for_rendering


class SubtitleStyleDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.app = getattr(parent, "parent", parent)
        is_ar = self.app.language_var.get() == "العربية"
        self.is_ar = is_ar
        self.title(self.app.text("subtitle_style_title"))
        if hasattr(self.app, "_apply_theme_to_toplevel"):
            self.app._apply_theme_to_toplevel(self)
        self.geometry("680x640")
        self.minsize(620, 580)
        self.transient(parent)
        self.resizable(True, True)

        cur_style = dict(getattr(self.app, "subtitle_style", {}))

        self.tkfont = tkfont
        system_fonts = []
        try:
            system_fonts = [f for f in tkfont.families() if not f.startswith("@") and not f.startswith("System")]
        except Exception:
            pass
        curated_fonts = [
            "Segoe UI", "Arial", "Cairo", "Tahoma", "Calibri", "Impact",
            "Times New Roman", "Comic Sans MS", "Verdana", "Trebuchet MS",
            "Dubai", "Traditional Arabic"
        ]
        self.font_families = []
        for f in curated_fonts:
            if f not in self.font_families:
                self.font_families.append(f)
        for f in sorted(system_fonts):
            if f not in self.font_families and len(self.font_families) < 40:
                self.font_families.append(f)

        self.font_sizes = [
            ("auto", self.app.text("sub_font_auto")),
            ("18", "18 px (صغير / Small)"),
            ("20", "20 px"),
            ("22", "22 px"),
            ("24", "24 px (افتراضي / Default)"),
            ("26", "26 px (واضح / Clear)"),
            ("28", "28 px (كبير / Large)"),
            ("32", "32 px (بارز / Prominent)"),
            ("36", "36 px"),
            ("40", "40 px"),
            ("48", "48 px (فائق الضخامة / Extra Large)"),
            ("56", "56 px"),
        ]

        self.color_options = [
            ("yellow", "أصفر (Yellow)" if is_ar else "Yellow (أصفر)"),
            ("white", "أبيض (White)" if is_ar else "White (أبيض)"),
            ("lime", "أخضر ليموني (Lime)" if is_ar else "Lime Green (أخضر ليموني)"),
            ("cyan", "سماوي (Cyan)" if is_ar else "Cyan (سماوي)"),
            ("orange", "برتقالي (Orange)" if is_ar else "Orange (برتقالي)"),
            ("pink", "وردي (Pink)" if is_ar else "Pink (وردي)"),
            ("red", "أحمر (Red)" if is_ar else "Red (أحمر)"),
            ("black", "أسود (Black)" if is_ar else "Black (أسود)"),
        ]

        self.outline_options = [
            ("box_semi", "بالونة كبسولة خلفية نصف شفافة (شبه CapCut)" if is_ar else "Semi-transparent Bubble/Box (CapCut Style)"),
            ("thick_black", "إطار أسود عريض وبارز" if is_ar else "Thick Black Outline"),
            ("medium_black", "إطار أسود متوسط" if is_ar else "Medium Black Outline"),
            ("thin_black", "إطار أسود خفيف" if is_ar else "Thin Black Outline"),
            ("box_black", "صندوق خلفية أسود داكن" if is_ar else "Solid Black Box"),
            ("box_navy", "صندوق خلفية كحلي داكن" if is_ar else "Solid Navy Blue Box"),
            ("none", "نص عادي بدون إطار أو خلفية" if is_ar else "Plain Text (No Outline/Box)"),
        ]

        self.pos_v_options = [
            ("bottom", self.app.text("sub_pos_bottom")),
            ("middle", self.app.text("sub_pos_middle")),
            ("top", self.app.text("sub_pos_top")),
        ]

        self.pos_h_options = [
            ("center", self.app.text("sub_align_center")),
            ("left", self.app.text("sub_align_left")),
            ("right", self.app.text("sub_align_right")),
        ]

        saved_font = cur_style.get("font_name", "Segoe UI")
        if saved_font not in self.font_families:
            self.font_families.insert(0, saved_font)
        self.font_name_var = tk.StringVar(value=saved_font)

        saved_size = str(cur_style.get("font_size", "26"))
        self.font_size_var = tk.StringVar()
        for s_code, s_lbl in self.font_sizes:
            if s_code == saved_size:
                self.font_size_var.set(s_lbl)
                break
        if not self.font_size_var.get():
            self.font_size_var.set(self.font_sizes[5][1])

        saved_color = cur_style.get("text_color", cur_style.get("color", "yellow"))
        self.color_var = tk.StringVar()
        for c_code, c_lbl in self.color_options:
            if c_code == saved_color:
                self.color_var.set(c_lbl)
                break
        if not self.color_var.get():
            self.color_var.set(self.color_options[0][1])

        saved_outline = cur_style.get("outline_style", cur_style.get("outline", "box_semi"))
        self.outline_var = tk.StringVar()
        for o_code, o_lbl in self.outline_options:
            if o_code == saved_outline:
                self.outline_var.set(o_lbl)
                break
        if not self.outline_var.get():
            self.outline_var.set(self.outline_options[0][1])

        self.bold_var = tk.BooleanVar(value=cur_style.get("bold", True))
        self.italic_var = tk.BooleanVar(value=cur_style.get("italic", False))

        saved_pv = cur_style.get("position_v", "bottom")
        self.pos_v_var = tk.StringVar()
        for v_code, v_lbl in self.pos_v_options:
            if v_code == saved_pv:
                self.pos_v_var.set(v_lbl)
                break
        if not self.pos_v_var.get():
            self.pos_v_var.set(self.pos_v_options[0][1])

        saved_ph = cur_style.get("position_h", "center")
        self.pos_h_var = tk.StringVar()
        for h_code, h_lbl in self.pos_h_options:
            if h_code == saved_ph:
                self.pos_h_var.set(h_lbl)
                break
        if not self.pos_h_var.get():
            self.pos_h_var.set(self.pos_h_options[0][1])

        try:
            saved_mv = int(cur_style.get("margin_v", 35))
        except Exception:
            saved_mv = 35
        self.margin_v_var = tk.IntVar(value=saved_mv)

        self._build_ui()
        self.after(50, self._update_preview)

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
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        f_card = ttk.LabelFrame(container, text="🖋️ " + ("الخط والمظهر واللون" if self.is_ar else "Font & Color Appearance"), padding=(12, 10))
        f_card.pack(fill="x", pady=(0, 10))
        f_card.columnconfigure(1, weight=1)
        f_card.columnconfigure(3, weight=1)

        ttk.Label(f_card, text=self.app.text("sub_font_name")).grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
        self.combo_font = ttk.Combobox(f_card, textvariable=self.font_name_var, values=self.font_families, state="readonly", width=18)
        self.combo_font.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=4)
        self.combo_font.bind("<<ComboboxSelected>>", lambda _e: self._update_preview())

        ttk.Label(f_card, text=self.app.text("sub_font_size")).grid(row=0, column=2, sticky="w", padx=(0, 6), pady=4)
        self.combo_size = ttk.Combobox(f_card, textvariable=self.font_size_var, values=[s[1] for s in self.font_sizes], state="readonly", width=18)
        self.combo_size.grid(row=0, column=3, sticky="ew", pady=4)
        self.combo_size.bind("<<ComboboxSelected>>", lambda _e: self._update_preview())

        ttk.Label(f_card, text=self.app.text("sub_text_color")).grid(row=1, column=0, sticky="w", padx=(0, 6), pady=4)
        self.combo_color = ttk.Combobox(f_card, textvariable=self.color_var, values=[c[1] for c in self.color_options], state="readonly", width=18)
        self.combo_color.grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=4)
        self.combo_color.bind("<<ComboboxSelected>>", lambda _e: self._update_preview())

        ttk.Label(f_card, text=self.app.text("sub_outline_style")).grid(row=1, column=2, sticky="w", padx=(0, 6), pady=4)
        self.combo_outline = ttk.Combobox(f_card, textvariable=self.outline_var, values=[o[1] for o in self.outline_options], state="readonly", width=24)
        self.combo_outline.grid(row=1, column=3, sticky="ew", pady=4)
        self.combo_outline.bind("<<ComboboxSelected>>", lambda _e: self._update_preview())

        style_row = ttk.Frame(f_card)
        style_row.grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))
        self.chk_bold = ttk.Checkbutton(style_row, text=self.app.text("sub_bold"), variable=self.bold_var, command=self._update_preview)
        self.chk_bold.pack(side="left", padx=(0, 16))
        self.chk_italic = ttk.Checkbutton(style_row, text=self.app.text("sub_italic"), variable=self.italic_var, command=self._update_preview)
        self.chk_italic.pack(side="left")

        pos_card = ttk.LabelFrame(container, text="📍 " + ("مكان الترجمة على شاشة الفيديو" if self.is_ar else "Subtitle Position on Video"), padding=(12, 10))
        pos_card.pack(fill="x", pady=(0, 10))
        pos_card.columnconfigure(1, weight=1)
        pos_card.columnconfigure(3, weight=1)

        ttk.Label(pos_card, text=self.app.text("sub_pos_v")).grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
        self.combo_pv = ttk.Combobox(pos_card, textvariable=self.pos_v_var, values=[v[1] for v in self.pos_v_options], state="readonly", width=18)
        self.combo_pv.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=4)
        self.combo_pv.bind("<<ComboboxSelected>>", lambda _e: self._update_preview())

        ttk.Label(pos_card, text=self.app.text("sub_pos_h")).grid(row=0, column=2, sticky="w", padx=(0, 6), pady=4)
        self.combo_ph = ttk.Combobox(pos_card, textvariable=self.pos_h_var, values=[h[1] for h in self.pos_h_options], state="readonly", width=18)
        self.combo_ph.grid(row=0, column=3, sticky="ew", pady=4)
        self.combo_ph.bind("<<ComboboxSelected>>", lambda _e: self._update_preview())

        ttk.Label(pos_card, text=self.app.text("sub_margin_v")).grid(row=1, column=0, sticky="w", padx=(0, 6), pady=4)
        slider_frame = ttk.Frame(pos_card)
        slider_frame.grid(row=1, column=1, columnspan=3, sticky="ew", pady=4)
        slider_frame.columnconfigure(0, weight=1)

        self.scale_margin = ttk.Scale(slider_frame, from_=10, to=120, variable=self.margin_v_var, orient="horizontal", command=lambda _v: self._on_margin_slider())
        self.scale_margin.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.lbl_margin_val = ttk.Label(slider_frame, text=f"{self.margin_v_var.get()} px", width=8)
        self.lbl_margin_val.grid(row=0, column=1, sticky="w")

        prev_card = ttk.LabelFrame(container, text="🎬 " + self.app.text("sub_preview_label"), padding=(8, 8))
        prev_card.pack(fill="both", expand=True, pady=(0, 12))

        self.preview_canvas = tk.Canvas(prev_card, bg="#14181f", height=140, highlightthickness=1, highlightbackground="#2d333b")
        self.preview_canvas.pack(fill="both", expand=True)
        self.preview_canvas.bind("<Configure>", lambda _e: self._update_preview())

        btn_box = ttk.Frame(container)
        btn_box.pack(fill="x")

        self.btn_save = ttk.Button(btn_box, text="💾 " + self.app.text("sub_save_apply"), command=self._save_and_apply, style="Action.TButton")
        self.btn_save.pack(side="left" if not self.is_ar else "right", padx=(0, 8))

        self.btn_reset = ttk.Button(btn_box, text="🔄 " + self.app.text("sub_reset_defaults"), command=self._reset_defaults, style="Player.TButton")
        self.btn_reset.pack(side="left" if not self.is_ar else "right", padx=(0, 8))

        self.btn_close = ttk.Button(btn_box, text=self.app.text("close"), command=self.destroy, style="Player.TButton")
        self.btn_close.pack(side="right" if not self.is_ar else "left")

    def _on_margin_slider(self):
        val = int(self.margin_v_var.get())
        self.lbl_margin_val.configure(text=f"{val} px")
        self._update_preview()

    def _get_selected_size_code(self):
        txt = self.font_size_var.get()
        for s_code, s_lbl in self.font_sizes:
            if s_lbl == txt:
                return s_code
        return "26"

    def _get_selected_color_code(self):
        txt = self.color_var.get()
        for c_code, c_lbl in self.color_options:
            if c_lbl == txt:
                return c_code
        return "yellow"

    def _get_selected_outline_code(self):
        txt = self.outline_var.get()
        for o_code, o_lbl in self.outline_options:
            if o_lbl == txt:
                return o_code
        return "box_semi"

    def _get_selected_pos_v_code(self):
        txt = self.pos_v_var.get()
        for v_code, v_lbl in self.pos_v_options:
            if v_lbl == txt:
                return v_code
        return "bottom"

    def _get_selected_pos_h_code(self):
        txt = self.pos_h_var.get()
        for h_code, h_lbl in self.pos_h_options:
            if h_lbl == txt:
                return h_code
        return "center"

    def _update_preview(self):
        if not hasattr(self, "preview_canvas") or not self.preview_canvas.winfo_exists():
            return

        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()
        if cw < 60:
            cw = 620
        if ch < 40:
            ch = 140

        self.preview_canvas.delete("all")

        self.preview_canvas.create_rectangle(0, 0, cw, ch, fill="#12161c", outline="#262c36", width=1)
        self.preview_canvas.create_text(
            cw - 12 if not self.is_ar else 12,
            12,
            text="1080p FULL HD • 16:9",
            anchor="ne" if not self.is_ar else "nw",
            font=("Segoe UI", 7, "bold"),
            fill="#485261",
        )

        font_name = self.font_name_var.get().strip() or "Segoe UI"
        size_code = self._get_selected_size_code()
        color_code = self._get_selected_color_code()
        outline_code = self._get_selected_outline_code()
        pv = self._get_selected_pos_v_code()
        ph = self._get_selected_pos_h_code()
        mv = int(self.margin_v_var.get())
        bold = self.bold_var.get()
        italic = self.italic_var.get()

        if size_code == "auto":
            sim_size = 14
        else:
            try:
                sim_size = max(11, min(22, int(int(size_code) * 0.58)))
            except Exception:
                sim_size = 14

        weight_str = "bold" if bold else "normal"
        slant_str = "italic" if italic else "roman"
        try:
            prev_font = self.tkfont.Font(family=font_name, size=sim_size, weight=weight_str, slant=slant_str)
        except Exception:
            prev_font = self.tkfont.Font(family="Segoe UI", size=sim_size, weight=weight_str, slant=slant_str)

        HEX_COLORS = {
            "yellow": "#FFE600",
            "white": "#FFFFFF",
            "lime": "#39FF14",
            "cyan": "#00F0FF",
            "orange": "#FF8C00",
            "pink": "#FF69B4",
            "red": "#FF3B30",
            "black": "#000000",
        }
        text_color_hex = HEX_COLORS.get(color_code, "#FFE600")

        scaled_mv = max(10, min(50, int(mv * 0.35)))
        if pv == "top":
            y = scaled_mv + 12
        elif pv == "middle":
            y = ch // 2
        else:
            y = ch - scaled_mv - 12

        if ph == "left":
            x = 24
            anchor = "w"
        elif ph == "right":
            x = cw - 24
            anchor = "e"
        else:
            x = cw // 2
            anchor = "center"

        sample_txt = prepare_arabic_for_rendering(self.app.text("sub_preview_sample"))
        t_width = prev_font.measure(sample_txt)
        t_height = prev_font.metrics("linespace")

        if outline_code == "box_semi":
            bg_fill = "#1d232c"
            bg_border = "#3a4454"
        elif outline_code == "box_black":
            bg_fill = "#000000"
            bg_border = "#1a1a1a"
        elif outline_code == "box_navy":
            bg_fill = "#0b192e"
            bg_border = "#1b3a6b"
        else:
            bg_fill = None

        if bg_fill:
            pad_x = 10
            pad_y = 4
            if anchor == "center":
                bx0 = x - t_width // 2 - pad_x
                bx1 = x + t_width // 2 + pad_x
            elif anchor == "w":
                bx0 = x - pad_x
                bx1 = x + t_width + pad_x
            else:
                bx0 = x - t_width - pad_x
                bx1 = x + pad_x
            by0 = y - t_height // 2 - pad_y
            by1 = y + t_height // 2 + pad_y
            self.preview_canvas.create_rectangle(bx0, by0, bx1, by1, fill=bg_fill, outline=bg_border, width=1)

        if outline_code in ("thick_black", "medium_black", "thin_black"):
            off = 2 if outline_code == "thick_black" else 1
            for dx, dy in [(-off, 0), (off, 0), (0, -off), (0, off), (-off, -off), (off, -off), (-off, off), (off, off)]:
                self.preview_canvas.create_text(
                    x + dx, y + dy, text=sample_txt, font=prev_font, fill="#000000", anchor=anchor
                )

        self.preview_canvas.create_text(
            x, y, text=sample_txt, font=prev_font, fill=text_color_hex, anchor=anchor
        )

    def _save_and_apply(self):
        cfg = {
            "font_name": self.font_name_var.get().strip() or "Segoe UI",
            "font_size": self._get_selected_size_code(),
            "text_color": self._get_selected_color_code(),
            "outline_style": self._get_selected_outline_code(),
            "bold": bool(self.bold_var.get()),
            "italic": bool(self.italic_var.get()),
            "position_v": self._get_selected_pos_v_code(),
            "position_h": self._get_selected_pos_h_code(),
            "margin_v": int(self.margin_v_var.get()),
        }
        self.app.subtitle_style = cfg
        self.app.settings["subtitle_style"] = cfg
        self.app._save_settings()
        messagebox.showinfo(
            self.app.text("app_title"),
            self.app.text("sub_edits_saved"),
            parent=self,
        )
        self.destroy()

    def _reset_defaults(self):
        self.font_name_var.set("Segoe UI")
        self.font_size_var.set(self.font_sizes[5][1])
        self.color_var.set(self.color_options[0][1])
        self.outline_var.set(self.outline_options[0][1])
        self.bold_var.set(True)
        self.italic_var.set(False)
        self.pos_v_var.set(self.pos_v_options[0][1])
        self.pos_h_var.set(self.pos_h_options[0][1])
        self.margin_v_var.set(35)
        self.lbl_margin_val.configure(text="35 px")
        self._update_preview()
