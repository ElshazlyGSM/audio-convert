"""
Professional Video Transitions Library Dialog
Provides a DaVinci Resolve / CapCut style transition browser with:
- 45+ categorized cinematic transitions (Fades, Motion Slides, Zooms, Wipes, Trendy Glitch)
- Real-time interactive animated preview canvas simulating the motion live in GUI
- Duration control with quick social/cinematic presets (0.3s, 0.5s, 1.0s)
- Audio crossfade toggle
- Per-cut or apply-to-all scope selection
- Bilingual Arabic / English support

Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

import copy
import math
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw

from video_studio.transitions import (
    DEFAULT_TRANSITIONS_CONFIG,
    TRANSITION_PRESETS,
    TRANSITION_CATEGORIES,
    get_transition_info,
    list_transitions_by_category,
    render_simulated_transition_frame,
)


class VideoTransitionDialog(tk.Toplevel):
    def __init__(self, parent, target_cut_index: Optional[int] = None):
        super().__init__(parent)
        self.parent = parent
        self.app = getattr(parent, "parent", parent)
        self.is_ar = getattr(self.app, "language_var", tk.StringVar(value="English")).get() == "العربية"
        self.target_cut_index = target_cut_index

        dlg_title = "✨ مكتبة انتقالات الفيديو السينمائية" if self.is_ar else "✨ Cinematic Video Transitions Library"
        self.title(dlg_title)
        if hasattr(self.app, "_apply_theme_to_toplevel"):
            self.app._apply_theme_to_toplevel(self)

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        target_w = min(1020, max(840, int(screen_w * 0.88)))
        target_h = min(860, max(680, int(screen_h * 0.88)))
        self.geometry(f"{target_w}x{target_h}")
        self.minsize(min(840, target_w), min(640, target_h))
        self.transient(parent)
        self.resizable(True, True)

        # Load existing transition config or default
        branding_cfg = getattr(self.app, "video_branding_config", {})
        saved_trans = branding_cfg.get("transitions_config", {})
        self.current_config = dict(DEFAULT_TRANSITIONS_CONFIG)
        if isinstance(saved_trans, dict):
            self.current_config.update(saved_trans)

        # State Variables
        self.enabled_var = tk.BooleanVar(value=bool(self.current_config.get("enabled", True)))
        self.selected_key_var = tk.StringVar(value=str(self.current_config.get("default_transition", "smoothleft")))
        self.duration_var = tk.DoubleVar(value=float(self.current_config.get("default_duration", 0.5)))
        self.audio_crossfade_var = tk.BooleanVar(value=bool(self.current_config.get("audio_crossfade", True)))
        self.apply_to_all_var = tk.BooleanVar(value=bool(self.current_config.get("apply_to_all", True)))
        self.active_category_var = tk.StringVar(value="all")
        self.search_query_var = tk.StringVar(value="")

        # Interactive Preview State
        self.anim_t: float = 0.0
        self.anim_dir: float = 1.0
        self.anim_running: bool = True
        self.anim_job: Optional[str] = None
        self.photo_preview: Optional[ImageTk.PhotoImage] = None

        self._init_sample_images()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

        self._build_ui()
        self._start_preview_loop()

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

    def _init_sample_images(self):
        """Prepares two distinct 16:9 sample images for the animated transition preview."""
        pw, ph = 320, 180
        # Frame A: Deep Midnight Blue with Scene A graphic
        img_a = Image.new("RGB", (pw, ph), (18, 32, 58))
        draw_a = ImageDraw.Draw(img_a)
        # Background subtle gradient
        for y in range(ph):
            draw_a.line([(0, y), (pw, y)], fill=(15 + y // 10, 28 + y // 12, 52 + y // 8))
        draw_a.rectangle([24, 24, pw - 24, ph - 24], outline=(56, 120, 200), width=2)
        draw_a.text((pw // 2 - 40, ph // 2 - 12), "SCENE A (المشهد الأول)", fill=(230, 240, 255))
        self.sample_img_a = img_a

        # Frame B: Rich Warm Golden Emerald with Scene B graphic
        img_b = Image.new("RGB", (pw, ph), (22, 60, 42))
        draw_b = ImageDraw.Draw(img_b)
        for y in range(ph):
            draw_b.line([(0, y), (pw, y)], fill=(20 + y // 8, 55 + y // 10, 38 + y // 12))
        draw_b.rectangle([24, 24, pw - 24, ph - 24], outline=(72, 185, 125), width=2)
        draw_b.text((pw // 2 - 40, ph // 2 - 12), "SCENE B (المشهد الثاني)", fill=(230, 255, 235))
        self.sample_img_b = img_b

    def _build_ui(self):
        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        # ------------------ Row 0: Header & Enable Switch ------------------
        header_card = ttk.Frame(container)
        header_card.pack(fill="x", pady=(0, 6))

        title_txt = "✨ " + ("مكتبة حركات وانتقالات الفيديو السينمائية" if self.is_ar else "Cinematic Video Transitions Library")
        lbl_title = ttk.Label(header_card, text=title_txt, font=("Segoe UI", 13, "bold"))
        lbl_title.pack(side="left")

        chk_en = ttk.Checkbutton(
            header_card,
            text=("تفعيل الانتقالات بين المقاطع" if self.is_ar else "Enable Video Transitions"),
            variable=self.enabled_var,
        )
        chk_en.pack(side="right")

        # ------------------ Row 1: Interactive Preview & Selected Controls ------------------
        top_split = ttk.LabelFrame(
            container,
            text="🎬 " + ("المعاينة الحية وإعدادات الانتقال" if self.is_ar else "Live Preview & Transition Settings"),
            padding=(10, 8),
        )
        top_split.pack(fill="x", pady=(0, 8))

        # Preview Canvas (Left)
        prev_box = ttk.Frame(top_split)
        prev_box.pack(side="left", padx=(0, 16))

        self.canvas_preview = tk.Canvas(prev_box, width=320, height=180, bg="#0d1117", highlightthickness=1, highlightbackground="#30363d")
        self.canvas_preview.pack(side="top")

        # Preview Animation Play/Pause & Scrub Bar
        anim_bar = ttk.Frame(prev_box)
        anim_bar.pack(fill="x", pady=(4, 0))

        self.btn_play_pause = ttk.Button(
            anim_bar,
            text="⏸️",
            width=3,
            command=self._toggle_anim,
            style="Player.TButton",
        )
        self.btn_play_pause.pack(side="left")

        self.lbl_anim_t = ttk.Label(anim_bar, text="50%", font=("Segoe UI", 8), width=5)
        self.lbl_anim_t.pack(side="left", padx=4)

        btn_replay = ttk.Button(
            anim_bar,
            text=("↺ إعادة العرض" if self.is_ar else "↺ Replay"),
            command=self._replay_anim,
            style="Player.TButton",
        )
        btn_replay.pack(side="right")

        # Controls & Properties (Right)
        ctrl_box = ttk.Frame(top_split)
        ctrl_box.pack(side="left", fill="both", expand=True)

        # Selected Transition Title & Description
        self.lbl_sel_title = ttk.Label(
            ctrl_box,
            text="",
            font=("Segoe UI", 11, "bold"),
            foreground="#58a6ff",
        )
        self.lbl_sel_title.pack(anchor="w", pady=(0, 2))

        self.lbl_sel_desc = ttk.Label(
            ctrl_box,
            text="",
            font=("Segoe UI", 8),
            wraplength=520,
            foreground="#8b949e",
        )
        self.lbl_sel_desc.pack(anchor="w", pady=(0, 8))

        # Duration Slider
        dur_frame = ttk.Frame(ctrl_box)
        dur_frame.pack(fill="x", pady=(0, 6))

        ttk.Label(
            dur_frame,
            text=("⏱️ مدة الانتقال:" if self.is_ar else "⏱️ Transition Duration:"),
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left")

        self.lbl_dur_val = ttk.Label(dur_frame, text="0.50 ثانية", font=("Segoe UI", 9, "bold"), foreground="#2ea043")
        self.lbl_dur_val.pack(side="right")

        self.scale_dur = ttk.Scale(
            ctrl_box,
            from_=0.10,
            to=2.00,
            variable=self.duration_var,
            command=self._on_duration_slider,
        )
        self.scale_dur.pack(fill="x", pady=(0, 4))

        # Quick Duration Buttons
        quick_btn_box = ttk.Frame(ctrl_box)
        quick_btn_box.pack(fill="x", pady=(0, 8))

        ttk.Button(
            quick_btn_box,
            text=("⚡ 0.3s ريلز وسريع" if self.is_ar else "⚡ 0.3s Reels/Fast"),
            command=lambda: self._set_duration(0.30),
            style="Player.TButton",
        ).pack(side="left", padx=(0, 4))

        ttk.Button(
            quick_btn_box,
            text=("🎬 0.5s متوازن كلاسيكي" if self.is_ar else "🎬 0.5s Standard"),
            command=lambda: self._set_duration(0.50),
            style="Player.TButton",
        ).pack(side="left", padx=4)

        ttk.Button(
            quick_btn_box,
            text=("🌊 1.0s سينمائي ناعم" if self.is_ar else "🌊 1.0s Cinematic"),
            command=lambda: self._set_duration(1.00),
            style="Player.TButton",
        ).pack(side="left", padx=4)

        # Options: Audio Crossfade & Scope & Target Cut Selection
        opt_box = ttk.Frame(ctrl_box)
        opt_box.pack(fill="x", pady=(2, 0))

        ttk.Checkbutton(
            opt_box,
            text=("🔊 تفعيل التلاشي الصوتي المتناسق بين المقاطع (Audio Crossfade)" if self.is_ar else "🔊 Smooth Audio Crossfade"),
            variable=self.audio_crossfade_var,
        ).pack(anchor="w", pady=(0, 2))

        clips = getattr(getattr(self.app, "nle_project", None), "clips", [])
        n_cuts = max(0, len(clips) - 1)

        if n_cuts <= 0:
            lbl_no_cuts = ttk.Label(
                opt_box,
                text=("⚠️ لا توجد تقطيعات في التايم لاين حالياً (مقطع واحد فقط). قسّم الفيديو بـ Ctrl+B أولاً لإضافة انتقال." if self.is_ar else "⚠️ No cuts in video (1 continuous clip). Split video with Ctrl+B first to add transitions."),
                foreground="#ff7b72",
                font=("Segoe UI", 8, "bold"),
                wraplength=480,
            )
            lbl_no_cuts.pack(anchor="w", pady=(2, 2))
        else:
            cut_sel_frame = ttk.Frame(opt_box)
            cut_sel_frame.pack(fill="x", pady=(2, 2))
            ttk.Label(
                cut_sel_frame,
                text=("🎯 موضع التطبيق:" if self.is_ar else "🎯 Target Cut:"),
                font=("Segoe UI", 8, "bold"),
            ).pack(side="left", padx=(0, 6))

            cut_options = [
                ("all", f"🌐 تطبيق على جميع التقطيعات ({n_cuts} قطع)" if self.is_ar else f"🌐 Apply to ALL cuts ({n_cuts} cuts)")
            ]
            for c_i in range(n_cuts):
                c_end = clips[c_i].get("tl_end", 0.0)
                cut_options.append(
                    (str(c_i), f"🎬 القطع #{c_i+1}: بين المقطع {c_i+1} و {c_i+2} (عند {c_end:.2f}s)" if self.is_ar else f"🎬 Cut #{c_i+1}: clips {c_i+1} & {c_i+2} (@{c_end:.2f}s)")
                )

            self._cut_options_map = {opt_text: opt_val for opt_val, opt_text in cut_options}
            self._cut_options_rev = {opt_val: opt_text for opt_val, opt_text in cut_options}

            init_opt = "all"
            if self.target_cut_index is not None and str(self.target_cut_index) in self._cut_options_rev:
                init_opt = str(self.target_cut_index)
                self.apply_to_all_var.set(False)

            self.target_cut_combo_var = tk.StringVar(value=self._cut_options_rev.get(init_opt, cut_options[0][1]))
            self.combo_target_cut = ttk.Combobox(
                cut_sel_frame,
                textvariable=self.target_cut_combo_var,
                values=[opt_text for _, opt_text in cut_options],
                state="readonly",
                width=38,
            )
            self.combo_target_cut.pack(side="left")

            def _on_target_cut_changed(_e=None):
                sel_text = self.target_cut_combo_var.get()
                val = self._cut_options_map.get(sel_text, "all")
                if val == "all":
                    self.apply_to_all_var.set(True)
                    self.target_cut_index = None
                else:
                    self.apply_to_all_var.set(False)
                    self.target_cut_index = int(val)

            self.combo_target_cut.bind("<<ComboboxSelected>>", _on_target_cut_changed)

        # ------------------ Row 2: Search & Category Filter ------------------
        filter_bar = ttk.Frame(container)
        filter_bar.pack(fill="x", pady=(0, 6))

        # Category Tabs
        cat_box = ttk.Frame(filter_bar)
        cat_box.pack(side="left", fill="x", expand=True)

        self.cat_btns: Dict[str, ttk.Button] = {}
        for c_key, c_info in TRANSITION_CATEGORIES.items():
            txt = c_info["label_ar"] if self.is_ar else c_info["label_en"]
            btn = ttk.Button(
                cat_box,
                text=txt,
                command=lambda k=c_key: self._on_category_clicked(k),
                style="Player.TButton",
            )
            btn.pack(side="left", padx=(0, 4))
            self.cat_btns[c_key] = btn

        # Search Entry
        search_box = ttk.Frame(filter_bar)
        search_box.pack(side="right")
        ttk.Label(search_box, text="🔍", font=("Segoe UI", 9)).pack(side="left", padx=(0, 2))
        self.ent_search = ttk.Entry(search_box, textvariable=self.search_query_var, width=18)
        self.ent_search.pack(side="left")
        self.search_query_var.trace_add("write", lambda *_: self._refresh_gallery_cards())

        # ------------------ Row 3: Scrollable Cards Gallery ------------------
        gallery_frame = ttk.LabelFrame(
            container,
            text=("📂 قائمة الانتقالات المتاحة (انقر على أي حركة لمعاينتها فوراً)" if self.is_ar else "📂 Available Transitions (Click to preview)"),
            padding=(6, 6),
        )
        gallery_frame.pack(fill="both", expand=True, pady=(0, 8))

        canvas_cards = tk.Canvas(gallery_frame, bg="#161b22", highlightthickness=0)
        v_scroll = ttk.Scrollbar(gallery_frame, orient="vertical", command=canvas_cards.yview)
        self.cards_inner = ttk.Frame(canvas_cards)

        self.cards_inner.bind(
            "<Configure>",
            lambda e: canvas_cards.configure(scrollregion=canvas_cards.bbox("all"))
        )
        cards_window = canvas_cards.create_window((0, 0), window=self.cards_inner, anchor="nw")

        def _on_canvas_configure(event):
            canvas_cards.itemconfig(cards_window, width=event.width)
        canvas_cards.bind("<Configure>", _on_canvas_configure)
        canvas_cards.configure(yscrollcommand=v_scroll.set)

        # Mousewheel scrolling (safely scoped: only active when mouse is over canvas_cards!)
        def _on_mousewheel(event):
            canvas_cards.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        def _bind_mousewheel(e=None):
            canvas_cards.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(e=None):
            canvas_cards.unbind_all("<MouseWheel>")

        canvas_cards.bind("<Enter>", _bind_mousewheel)
        canvas_cards.bind("<Leave>", _unbind_mousewheel)
        self.bind("<Destroy>", lambda e: _unbind_mousewheel() if e.widget == self else None)

        canvas_cards.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")
        self.canvas_cards = canvas_cards

        # ------------------ Row 4: Bottom Action Bar ------------------
        bottom_box = ttk.Frame(container)
        bottom_box.pack(fill="x", pady=(4, 0))

        btn_remove = ttk.Button(
            bottom_box,
            text=("↺ إزالة كل الانتقالات (Hard Cut)" if self.is_ar else "↺ Remove All Transitions"),
            command=self.remove_all_transitions,
            style="Player.TButton",
        )
        btn_remove.pack(side="left")

        if self.target_cut_index is not None:
            btn_remove_cut = ttk.Button(
                bottom_box,
                text=(f"❌ إزالة من القطع #{self.target_cut_index+1} فقط" if self.is_ar else f"❌ Remove from Cut #{self.target_cut_index+1} only"),
                command=self.remove_target_cut_transition,
                style="Player.TButton",
            )
            btn_remove_cut.pack(side="left", padx=4)

        btn_cancel = ttk.Button(
            bottom_box,
            text=("❌ إلغاء" if self.is_ar else "❌ Cancel"),
            command=self.on_cancel,
            style="Player.TButton",
        )
        btn_cancel.pack(side="right", padx=(6, 0))

        btn_save = ttk.Button(
            bottom_box,
            text=("💾 حفظ وتطبيق الانتقالات" if self.is_ar else "💾 Save & Apply"),
            command=self.save_and_apply,
            style="Action.TButton",
        )
        btn_save.pack(side="right")

        self._update_selected_info_card()
        self._refresh_gallery_cards()

    def _on_category_clicked(self, cat_key: str):
        self.active_category_var.set(cat_key)
        self._refresh_gallery_cards()

    def _set_duration(self, dur: float):
        self.duration_var.set(round(dur, 2))
        self._on_duration_slider()

    def _on_duration_slider(self, _v=None):
        val = round(self.duration_var.get(), 2)
        unit = "ثانية" if self.is_ar else "sec"
        self.lbl_dur_val.configure(text=f"{val:.2f} {unit}")

    def _update_selected_info_card(self):
        key = self.selected_key_var.get()
        info = get_transition_info(key)
        icon = info.get("icon", "✨")
        title = info.get("label_ar") if self.is_ar else info.get("label_en")
        desc = info.get("desc_ar") if self.is_ar else info.get("desc_en")
        pop_badge = " [⭐ الأكثر شعبية / موصى به]" if info.get("is_popular") else ""
        self.lbl_sel_title.configure(text=f"{icon} {title}{pop_badge}")
        self.lbl_sel_desc.configure(text=desc)

    def select_transition(self, trans_key: str):
        self.selected_key_var.set(trans_key)
        info = get_transition_info(trans_key)
        def_dur = float(info.get("default_duration", 0.5))
        # Keep user duration if adjusted or adopt preset default
        if abs(self.duration_var.get() - 0.5) < 0.01:
            self.duration_var.set(def_dur)
            self._on_duration_slider()

        self._update_selected_info_card()
        self._replay_anim()
        self._highlight_selected_card()

    def _refresh_gallery_cards(self):
        for widget in self.cards_inner.winfo_children():
            widget.destroy()

        cat = self.active_category_var.get()
        query = self.search_query_var.get().strip().lower()
        presets = list_transitions_by_category(cat)

        if query:
            filtered = []
            for p in presets:
                name_ar = p.get("label_ar", "").lower()
                name_en = p.get("label_en", "").lower()
                desc_ar = p.get("desc_ar", "").lower()
                desc_en = p.get("desc_en", "").lower()
                key = p.get("key", "").lower()
                if (query in name_ar or query in name_en or query in desc_ar or query in desc_en or query in key):
                    filtered.append(p)
            presets = filtered

        # Multi-column grid layout (3 columns for cards)
        n_cols = 3
        for col_i in range(n_cols):
            self.cards_inner.columnconfigure(col_i, weight=1, uniform="c_card")

        current_key = self.selected_key_var.get()
        self.card_frames: Dict[str, ttk.Frame] = {}

        for idx, p in enumerate(presets):
            k = p["key"]
            r_idx = idx // n_cols
            c_idx = idx % n_cols

            is_sel = (k == current_key)
            card = ttk.Frame(
                self.cards_inner,
                padding=(8, 6),
                style="SelectedCard.TFrame" if is_sel else "NormalCard.TFrame",
            )
            card.grid(row=r_idx, column=c_idx, sticky="ew", padx=4, pady=4)
            self.card_frames[k] = card

            # Card Header: Icon + Title
            title_txt = p["label_ar"] if self.is_ar else p["label_en"]
            icon = p.get("icon", "✨")
            lbl_name = ttk.Label(
                card,
                text=f"{icon} {title_txt}",
                font=("Segoe UI", 9, "bold"),
                foreground="#58a6ff" if is_sel else "#c9d1d9",
            )
            lbl_name.pack(anchor="w")

            # Card Description
            desc_txt = p.get("desc_ar") if self.is_ar else p.get("desc_en")
            lbl_desc = ttk.Label(
                card,
                text=desc_txt,
                font=("Segoe UI", 7),
                wraplength=280,
                foreground="#8b949e",
            )
            lbl_desc.pack(anchor="w", pady=(2, 4))

            # Bottom Bar: Popular Badge + Select Button
            card_bot = ttk.Frame(card)
            card_bot.pack(fill="x")

            if p.get("is_popular"):
                ttk.Label(
                    card_bot,
                    text=("⭐ شائع" if self.is_ar else "⭐ Popular"),
                    font=("Segoe UI", 7, "bold"),
                    foreground="#f0883e",
                ).pack(side="left")

            btn_sel = ttk.Button(
                card_bot,
                text=("اختيار" if self.is_ar else "Select"),
                command=lambda key=k: self.select_transition(key),
                style="Action.TButton" if is_sel else "Player.TButton",
                width=8,
            )
            btn_sel.pack(side="right")

            # Make card clickable
            def _bind_click(widget, target_k=k):
                widget.bind("<Button-1>", lambda _e: self.select_transition(target_k))
            _bind_click(card)
            _bind_click(lbl_name)
            _bind_click(lbl_desc)

    def _highlight_selected_card(self):
        current_key = self.selected_key_var.get()
        self._refresh_gallery_cards()

    # ------------------ Interactive Preview Loop ------------------
    def _toggle_anim(self):
        self.anim_running = not self.anim_running
        self.btn_play_pause.configure(text="▶️" if not self.anim_running else "⏸️")

    def _replay_anim(self):
        self.anim_t = 0.0
        self.anim_dir = 1.0
        self.anim_running = True
        self.btn_play_pause.configure(text="⏸️")

    def _start_preview_loop(self):
        step_dt_ms = 40  # ~25 FPS animation loop

        def _step():
            if not self.winfo_exists():
                return
            if self.anim_running:
                dur = max(0.2, self.duration_var.get())
                # Advance t based on duration
                dt = (step_dt_ms / 1000.0) / dur
                self.anim_t += dt * self.anim_dir
                if self.anim_t >= 1.0:
                    self.anim_t = 1.0
                    self.anim_dir = -1.0  # bounce back or pause
                elif self.anim_t <= 0.0:
                    self.anim_t = 0.0
                    self.anim_dir = 1.0

                key = self.selected_key_var.get()
                sim_frame = render_simulated_transition_frame(
                    self.sample_img_a,
                    self.sample_img_b,
                    key,
                    self.anim_t,
                )
                self.photo_preview = ImageTk.PhotoImage(sim_frame)
                self.canvas_preview.delete("all")
                self.canvas_preview.create_image(160, 90, image=self.photo_preview)
                self.lbl_anim_t.configure(text=f"{int(self.anim_t * 100)}%")

            self.anim_job = self.after(step_dt_ms, _step)

        _step()

    # ------------------ Action Handlers ------------------
    def remove_all_transitions(self):
        """Disables all transitions across the project (hard cut)."""
        self.enabled_var.set(False)
        self.current_config["enabled"] = False
        self.current_config["default_transition"] = "none"
        self.current_config["clip_transitions"] = {}
        self.app.video_branding_config["transitions_config"] = self.current_config
        if hasattr(self.app, "_save_settings"):
            self.app._save_settings()
        if hasattr(self.app, "refresh_video_transitions_panel"):
            self.app.refresh_video_transitions_panel()
        if hasattr(self.app, "_render_player_studio_canvas"):
            self.app._render_player_studio_canvas()

        msg = "تمت إزالة الانتقالات والعودة للقطع المباشر." if self.is_ar else "Transitions removed, using direct hard cut."
        messagebox.showinfo(self.title(), msg)
        self.destroy()

    def remove_target_cut_transition(self):
        if self.target_cut_index is not None:
            tc = self.current_config
            clip_map = tc.get("clip_transitions", {})
            if str(self.target_cut_index) in clip_map:
                del clip_map[str(self.target_cut_index)]
            if int(self.target_cut_index) in clip_map:
                del clip_map[int(self.target_cut_index)]
            if not clip_map and not tc.get("apply_to_all", False):
                tc["enabled"] = False
            self.app.video_branding_config["transitions_config"] = tc
            if hasattr(self.app, "_save_settings"):
                self.app._save_settings()
            if hasattr(self.app, "refresh_video_transitions_panel"):
                self.app.refresh_video_transitions_panel()
            if hasattr(self.app, "_render_player_studio_canvas"):
                self.app._render_player_studio_canvas()
            msg = f"تمت إزالة الانتقال من القطع #{self.target_cut_index+1}" if self.is_ar else f"Removed transition from cut #{self.target_cut_index+1}"
            messagebox.showinfo(self.title(), msg)
            self.destroy()

    def save_and_apply(self):
        """Saves transition configuration to app state and refreshes timeline/inspector."""
        clips = getattr(getattr(self.app, "nle_project", None), "clips", [])
        n_cuts = max(0, len(clips) - 1)
        enabled = bool(self.enabled_var.get())

        if enabled and n_cuts <= 0:
            msg = (
                "⚠️ لا يمكن تفعيل أو إضافة انتقالات لعدم وجود تقطيعات في الفيديو!\n\n"
                "يرجى تقسيم الفيديو أولاً (بالمقص أو بالضغط على Ctrl+B عند الموضع المطلوب) لتتمكن من إضافة حركة انتقال بين المقطعين."
                if self.is_ar
                else "⚠️ Cannot add transitions because there are no cuts in the video!\n\nPlease split the video first (press Ctrl+B or use Blade tool) to add transitions between clips."
            )
            messagebox.showwarning(self.title(), msg)
            self.enabled_var.set(False)
            return

        key = self.selected_key_var.get()
        dur = round(self.duration_var.get(), 2)
        audio_xfade = bool(self.audio_crossfade_var.get())
        apply_all = bool(self.apply_to_all_var.get())

        cfg = {
            "enabled": enabled,
            "default_transition": key,
            "default_duration": dur,
            "audio_crossfade": audio_xfade,
            "apply_to_all": apply_all,
            "clip_transitions": copy.deepcopy(self.current_config.get("clip_transitions", {})),
        }

        # If a specific cut index was targeted and apply_to_all is false:
        if self.target_cut_index is not None and not apply_all:
            cfg["clip_transitions"][str(self.target_cut_index)] = {
                "transition": key,
                "duration": dur,
            }

        self.app.video_branding_config["transitions_config"] = cfg

        if hasattr(self.app, "push_app_undo"):
            p_info = get_transition_info(key)
            t_name = p_info.get("label_ar") if self.is_ar else p_info.get("label_en")
            self.app.push_app_undo(f"تطبيق حركة انتقال: {t_name}", f"Apply Transition: {key}")

        if hasattr(self.app, "_save_settings"):
            self.app._save_settings()
        if hasattr(self.app, "refresh_video_transitions_panel"):
            self.app.refresh_video_transitions_panel()
        if hasattr(self.app, "_render_player_studio_canvas"):
            self.app._render_player_studio_canvas()

        self.destroy()

    def on_cancel(self):
        if self.anim_job:
            try:
                self.after_cancel(self.anim_job)
            except Exception:
                pass
        self.destroy()
