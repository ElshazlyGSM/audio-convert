"""
DaVinci Resolve-Style Multi-Track NLE Timeline Widget
Provides 5 interactive tracks (V4 Logo, V3 Text+, V2 Icons/Images, V1 Video Clips, A1 Green Audio Waveform),
O(1) Zero-Lag Playhead Scrubbing/Playback, Extreme Frame/Syllable Zoom (up to 300 px/sec),
Free Clip Separation with Gaps, Live Silence Splitting, Per-Track [+] Element Creation,
Razor/Blade Split Tool, Ripple/Lift Delete, Edge Trimming, Magnetic Snapping, and Undo/Redo.
Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

import copy
import math
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional, Tuple

from video_studio.arabic_support import prepare_arabic_for_rendering
from video_studio.icons_library import ICON_PRESETS
from video_studio.transitions import DEFAULT_TRANSITIONS_CONFIG, get_transition_info


class DaVinciTimelinePanel(ttk.Frame):
    HEADER_W = 144
    RULER_H = 24
    TRACK_SPECS = [
        ("V4", 31, "#1b4d6e", "#266b99", "🛡️ اللوجو", "🛡️ Logo", "+"),
        ("V3", 31, "#8f7549", "#ad8f5b", "📝 النصوص", "📝 Text+", "+"),
        ("V2", 31, "#55359e", "#6d46c7", "⭐ أيقونات/صور", "⭐ Icons/Img", "+"),
        ("V1", 40, "#27476e", "#356094", "🎬 الفيديو V1", "🎬 Video V1", "✂"),
        ("A1", 44, "#1b5933", "#257845", "🔊 الصوت A1", "🔊 Audio A1", "⚡"),
    ]

    def __init__(
        self,
        parent,
        nle_state,
        is_ar_fn: Callable[[], bool],
        on_scrub: Callable[[float, bool], None],
        on_select: Callable[[Optional[Tuple[str, int]]], None],
        on_modified: Callable[[], None],
        on_add_element: Callable[[str, Optional[float]], None],
        on_split_silences: Optional[Callable[[bool], None]] = None,
        on_export_clip: Optional[Callable[[int], None]] = None,
    ):
        super().__init__(parent)
        self.nle = nle_state
        self.is_ar_fn = is_ar_fn
        self.on_scrub = on_scrub                  # (tl_sec, is_final_release)
        self.on_select = on_select                # (("clip"|"V2"|"V3"|"V4", idx) or None)
        self.on_modified = on_modified
        self.on_add_element = on_add_element      # ("text"|"icon"|"image"|"logo", at_tl_sec)
        self.on_split_silences = on_split_silences  # (remove_silences: bool) -> None
        self.on_export_clip = on_export_clip      # (clip_idx: int) -> None

        self.playhead_sec: float = 0.0
        self.tool_mode: str = "select"            # "select" or "blade"
        self.zoom_factor: float = 1.0             # 1.0 = fit full timeline, up to _max_zoom() (~300 px/sec)
        self.scroll_px: float = 0.0
        self.selected_ref: Optional[Tuple[str, int]] = None
        self.waveform_peaks: Optional[List[float]] = None
        self.silence_intervals: Optional[List[Dict[str, Any]]] = None

        # Fast O(1) canvas item IDs & cached geometry for zero-lag playback/hover
        self._playhead_line_id: Optional[int] = None
        self._playhead_cap_id: Optional[int] = None
        self._tc_text_id: Optional[int] = None
        self._blade_line_id: Optional[int] = None
        self._blade_box_id: Optional[int] = None
        self._blade_txt_id: Optional[int] = None
        self._cached_metrics: Optional[Tuple[float, float, float, int, int]] = None
        self._syncing_zoom_slider: bool = False

        # Drag / hover state
        self._drag_action: Optional[str] = None
        self._drag_target: Optional[Tuple[str, int]] = None
        self._drag_start_x: int = 0
        self._drag_orig_s: float = 0.0
        self._drag_orig_e: float = 0.0
        self._drag_orig_tl_s: float = 0.0
        self._drag_ref_tot_dur: float = 10.0
        self._drag_ref_tot_px: float = 600.0
        self._drag_moved: bool = False
        self._undo_pushed_for_drag: bool = False
        self._hover_blade_sec: Optional[float] = None
        self._snap_guide_sec: Optional[float] = None
        self._item_hit_boxes: List[Tuple[str, int, float, float, float, float]] = []
        self._gap_hit_boxes: List[Tuple[float, float, float, float]] = []
        self._cut_hit_boxes: List[Tuple[int, float, float, float, float, bool, str, float]] = []
        self._trans_guide_ids: List[int] = []

        self._build_ui()

    def _is_ar(self) -> bool:
        try:
            return bool(self.is_ar_fn())
        except Exception:
            return True

    @property
    def total_canvas_height(self) -> int:
        return self.RULER_H + sum(t[1] for t in self.TRACK_SPECS) + 2

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # ---------------- Row 0: DaVinci Resolve Edit Toolbar ----------------
        bar = tk.Frame(self, bg="#161920", padx=5, pady=3, highlightthickness=1, highlightbackground="#2b313d")
        bar.grid(row=0, column=0, sticky="ew")

        self.btn_tool_select = tk.Button(
            bar,
            command=lambda: self.set_tool_mode("select"),
            relief="flat",
            bd=0,
            padx=7,
            pady=2,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        )
        self.btn_tool_select.pack(side="left", padx=(0, 2))

        self.btn_tool_blade = tk.Button(
            bar,
            command=lambda: self.set_tool_mode("blade"),
            relief="flat",
            bd=0,
            padx=7,
            pady=2,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        )
        self.btn_tool_blade.pack(side="left", padx=(0, 4))

        tk.Frame(bar, bg="#30363d", width=1, height=18).pack(side="left", padx=3)

        self.btn_split_now = self._mk_bar_btn(bar, self.split_at_playhead, fg="#ffd700")
        self.btn_delete_sel = self._mk_bar_btn(bar, self.delete_selected, fg="#ff7b72")
        self.btn_dup_sel = self._mk_bar_btn(bar, self.duplicate_selected)
        self.btn_close_gaps = self._mk_bar_btn(bar, self.close_all_gaps_action, bg="#1d2f42", fg="#79c0ff")
        self.btn_split_silence = self._mk_bar_btn(bar, self._show_silence_split_menu, bg="#1d3829", fg="#56d364")
        self.btn_undo = self._mk_bar_btn(bar, self.do_undo)
        self.btn_redo = self._mk_bar_btn(bar, self.do_redo)

        self.ripple_var = tk.BooleanVar(value=True)
        self.chk_ripple = tk.Checkbutton(
            bar,
            variable=self.ripple_var,
            command=self._on_ripple_toggle,
            bg="#161920",
            fg="#c9d1d9",
            selectcolor="#1f6feb",
            activebackground="#161920",
            activeforeground="#ffffff",
            font=("Segoe UI", 8),
            cursor="hand2",
        )
        self.chk_ripple.pack(side="left", padx=(3, 4))

        tk.Frame(bar, bg="#30363d", width=1, height=18).pack(side="left", padx=3)

        # Quick Insert Buttons at Playhead
        self.btn_add_txt = self._mk_bar_btn(bar, lambda: self.on_add_element("text", self.playhead_sec), bg="#3b3222", fg="#f8e3a1")
        self.btn_add_ico = self._mk_bar_btn(bar, lambda: self.on_add_element("icon", self.playhead_sec), bg="#2d224c", fg="#d2a8ff")
        self.btn_add_img = self._mk_bar_btn(bar, lambda: self.on_add_element("image", self.playhead_sec), bg="#22354c", fg="#79c0ff")
        self.btn_add_lgo = self._mk_bar_btn(bar, lambda: self.on_add_element("logo", self.playhead_sec), bg="#1d3b3a", fg="#56d364")

        self.lbl_hud_toast = tk.Label(bar, text="", bg="#161920", fg="#58a6ff", font=("Segoe UI", 8, "bold"))
        self.lbl_hud_toast.pack(side="left", padx=8)

        # Right side: Precision Zoom controls (Fit + Zoom-to-Cut + Exponential Slider up to 300 px/sec)
        self.btn_zoom_fit = tk.Button(
            bar,
            command=self.zoom_fit,
            bg="#232834",
            fg="#c9d1d9",
            activebackground="#303846",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=6,
            pady=2,
            font=("Segoe UI", 8),
            cursor="hand2",
        )
        self.btn_zoom_fit.pack(side="right", padx=(2, 0))

        self.btn_zoom_cut = tk.Button(
            bar,
            command=self.zoom_to_cut,
            bg="#2a223d",
            fg="#d2a8ff",
            activebackground="#3b2f57",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=6,
            pady=2,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        )
        self.btn_zoom_cut.pack(side="right", padx=2)

        self._mk_small_zoom_btn(bar, "➕", lambda: self.step_zoom(1.45)).pack(side="right", padx=1)
        self.zoom_scale = ttk.Scale(
            bar,
            from_=0.0,
            to=100.0,
            value=0.0,
            orient="horizontal",
            length=92,
            command=self._on_zoom_slider,
        )
        self.zoom_scale.pack(side="right", padx=2)
        self._mk_small_zoom_btn(bar, "➖", lambda: self.step_zoom(1.0 / 1.45)).pack(side="right", padx=1)
        self.lbl_zoom = tk.Label(bar, text="🔍 1x", bg="#161920", fg="#8b949e", font=("Consolas", 8))
        self.lbl_zoom.pack(side="right", padx=(3, 2))

        # ---------------- Row 1: Multi-Track Canvas ----------------
        self.canvas = tk.Canvas(
            self,
            height=self.total_canvas_height,
            bg="#11141a",
            highlightthickness=1,
            highlightbackground="#2b313d",
        )
        self.canvas.grid(row=1, column=0, sticky="nsew")

        # ---------------- Row 2: Horizontal Scrollbar ----------------
        self.h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self._on_hscroll)
        self.h_scroll.grid(row=2, column=0, sticky="ew")

        # Bindings
        self.canvas.bind("<Configure>", lambda _e: self.redraw())
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Motion>", self._on_hover)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Alt-MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Control-MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Key>", self._on_canvas_key)

        self.apply_language()
        self._refresh_tool_buttons()

    def _mk_bar_btn(self, parent, cmd, bg="#232834", fg="#e6edf3"):
        b = tk.Button(
            parent,
            command=cmd,
            bg=bg,
            fg=fg,
            activebackground="#343c4d",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=6,
            pady=2,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        )
        b.pack(side="left", padx=1)
        return b

    def _mk_small_zoom_btn(self, parent, txt, cmd):
        return tk.Button(
            parent,
            text=txt,
            command=cmd,
            bg="#232834",
            fg="#e6edf3",
            activebackground="#343c4d",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=5,
            pady=1,
            font=("Segoe UI", 8),
            cursor="hand2",
        )

    def apply_language(self):
        ar = self._is_ar()
        self.btn_tool_select.configure(text="🖱️ تحديد (A)" if ar else "🖱️ Select (A)")
        self.btn_tool_blade.configure(text="✂️ مقص (B)" if ar else "✂️ Blade (B)")
        self.btn_split_now.configure(text="✂️ قص (S)" if ar else "✂️ Split (S)")
        self.btn_delete_sel.configure(text="🗑️ حذف" if ar else "🗑️ Delete")
        self.btn_dup_sel.configure(text="📋 تكرار" if ar else "📋 Dup")
        self.btn_close_gaps.configure(text="🧲 ضم الفجوات" if ar else "🧲 Close Gaps")
        self.btn_split_silence.configure(text="⚡ فصل السكتات" if ar else "⚡ Split Silences")
        self.btn_undo.configure(text="↩️" if ar else "↩️ Undo")
        self.btn_redo.configure(text="↪️" if ar else "↪️ Redo")
        self.chk_ripple.configure(text="ضم تلقائي" if ar else "Ripple")
        self.btn_add_txt.configure(text="+ نص" if ar else "+ Text")
        self.btn_add_ico.configure(text="+ أيقونة" if ar else "+ Icon")
        self.btn_add_img.configure(text="+ صورة" if ar else "+ Image")
        self.btn_add_lgo.configure(text="+ لوجو" if ar else "+ Logo")
        self.btn_zoom_cut.configure(text="🎯 زوم دقيق" if ar else "🎯 Fine Zoom")
        self.btn_zoom_fit.configure(text="احتواء" if ar else "Fit")
        self.redraw()

    def set_tool_mode(self, mode: str):
        self.tool_mode = mode if mode in ("select", "blade", "transition_place") else "select"
        self._hover_blade_sec = None
        self._clear_trans_guides()
        self._refresh_tool_buttons()
        self.redraw()

    def _refresh_tool_buttons(self):
        if self.tool_mode == "select":
            self.btn_tool_select.configure(bg="#1f6feb", fg="#ffffff")
            self.btn_tool_blade.configure(bg="#232834", fg="#c9d1d9")
        elif self.tool_mode == "blade":
            self.btn_tool_select.configure(bg="#232834", fg="#c9d1d9")
            self.btn_tool_blade.configure(bg="#da3633", fg="#ffffff")
        else:
            self.btn_tool_select.configure(bg="#232834", fg="#c9d1d9")
            self.btn_tool_blade.configure(bg="#232834", fg="#c9d1d9")

    def _on_ripple_toggle(self):
        self.nle.ripple_mode = bool(self.ripple_var.get())

    def close_all_gaps_action(self):
        if self.nle.close_all_gaps():
            self.on_modified()
            self.redraw()

    def _show_silence_split_menu(self):
        if not self.on_split_silences:
            return
        ar = self._is_ar()
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(
            label="⚡ " + ("فصل وحذف السكتات تلقائياً في التايم لاين" if ar else "Auto-Cut & Remove Silences on Timeline"),
            command=lambda: self.on_split_silences(True),
        )
        menu.add_command(
            label="🔇 " + ("تقسيم السكتات كمقاطع صامتة للمراجعة اليدوية" if ar else "Split Silences as Muted Clips for Review"),
            command=lambda: self.on_split_silences(False),
        )
        try:
            bx = self.btn_split_silence.winfo_rootx()
            by = self.btn_split_silence.winfo_rooty() + self.btn_split_silence.winfo_height()
            menu.tk_popup(bx, by)
        finally:
            menu.grab_release()

    # ------------------------------------------------------------------
    # O(1) Fast Playhead & Hover Updates (Zero Lag at 30-60 FPS!)
    # ------------------------------------------------------------------
    def _update_playhead_fast(self) -> bool:
        if (
            self._cached_metrics is None
            or self._playhead_line_id is None
            or self._playhead_cap_id is None
            or self._tc_text_id is None
            or not self.canvas.winfo_exists()
        ):
            return False
        tot_dur, tot_px, cached_scroll, cw, tracks_bottom_y = self._cached_metrics
        if abs(cached_scroll - self.scroll_px) > 0.5 or tot_dur <= 0:
            return False

        c = self.canvas
        px = self.HEADER_W + (self.playhead_sec / tot_dur) * tot_px - cached_scroll
        c.itemconfigure(self._tc_text_id, text=self._fmt_tc(self.playhead_sec, "tenth"))
        if self.HEADER_W <= px <= cw:
            c.coords(self._playhead_line_id, px, 12, px, tracks_bottom_y)
            c.coords(
                self._playhead_cap_id,
                px - 7, 1, px + 7, 1, px + 7, 10, px, 17, px - 7, 10,
            )
            c.itemconfigure(self._playhead_line_id, state="normal")
            c.itemconfigure(self._playhead_cap_id, state="normal")
        else:
            c.itemconfigure(self._playhead_line_id, state="hidden")
            c.itemconfigure(self._playhead_cap_id, state="hidden")
        return True

    def _update_blade_preview_fast(self) -> bool:
        if (
            self._cached_metrics is None
            or self._blade_line_id is None
            or self._blade_box_id is None
            or self._blade_txt_id is None
            or not self.canvas.winfo_exists()
        ):
            return False
        tot_dur, tot_px, cached_scroll, cw, tracks_bottom_y = self._cached_metrics
        c = self.canvas
        if self.tool_mode != "blade" or self._hover_blade_sec is None or tot_dur <= 0:
            c.itemconfigure(self._blade_line_id, state="hidden")
            c.itemconfigure(self._blade_box_id, state="hidden")
            c.itemconfigure(self._blade_txt_id, state="hidden")
            return True

        bx = self.HEADER_W + (self._hover_blade_sec / tot_dur) * tot_px - cached_scroll
        if self.HEADER_W <= bx <= cw:
            prec = "hundredth" if (tot_px / tot_dur) >= 140 else "tenth"
            tc_str = f"✂️ {self._fmt_tc(self._hover_blade_sec, prec)}"
            box_w = max(72, len(tc_str) * 7 + 8)
            c.coords(self._blade_line_id, bx, self.RULER_H, bx, tracks_bottom_y)
            c.coords(self._blade_box_id, bx + 4, self.RULER_H + 2, bx + 4 + box_w, self.RULER_H + 19)
            c.coords(self._blade_txt_id, bx + 8, self.RULER_H + 10)
            c.itemconfigure(self._blade_txt_id, text=tc_str, state="normal")
            c.itemconfigure(self._blade_line_id, state="normal")
            c.itemconfigure(self._blade_box_id, state="normal")
        else:
            c.itemconfigure(self._blade_line_id, state="hidden")
            c.itemconfigure(self._blade_box_id, state="hidden")
            c.itemconfigure(self._blade_txt_id, state="hidden")
        return True

    def set_playhead(self, tl_sec: float, auto_follow: bool = False):
        tot = max(0.1, self.nle.total_duration)
        self.playhead_sec = max(0.0, min(tot, float(tl_sec or 0.0)))
        scrolled = False
        if auto_follow:
            vw, tot_px = self._viewport_metrics()
            px = (self.playhead_sec / tot) * tot_px
            if px < self.scroll_px or px > self.scroll_px + vw - 20:
                new_sc = max(0.0, min(max(0.0, tot_px - vw), px - vw * 0.20))
                if abs(new_sc - self.scroll_px) > 0.5:
                    self.scroll_px = new_sc
                    scrolled = True
        if scrolled or not self._update_playhead_fast():
            self.redraw()

    # ------------------------------------------------------------------
    # Extreme Precision Zoom & Scroll Geometry (Up to 300 px/sec!)
    # ------------------------------------------------------------------
    def _max_zoom(self) -> float:
        cw = max(360, self.canvas.winfo_width())
        vw = max(180.0, float(cw - self.HEADER_W - 12))
        tot_dur = max(5.0, float(self.nle.total_duration or 10.0))
        # Guarantee up to ~300 pixels per second even on 1-2 hour videos!
        return max(100.0, min(5000.0, (tot_dur * 300.0) / vw))

    def _slider_to_zoom(self, s_val: float) -> float:
        s = max(0.0, min(100.0, float(s_val)))
        if s <= 0.2:
            return 1.0
        return max(1.0, self._max_zoom() ** (s / 100.0))

    def _zoom_to_slider(self, z_val: float) -> float:
        if z_val <= 1.02:
            return 0.0
        mz = self._max_zoom()
        return max(0.0, min(100.0, 100.0 * math.log(min(mz, z_val)) / max(1e-6, math.log(mz))))

    def _sync_zoom_ui_indicator(self):
        if hasattr(self, "lbl_zoom"):
            if self.zoom_factor < 10.0:
                z_txt = f"🔍{self.zoom_factor:.1f}x"
            else:
                z_txt = f"🔍{int(round(self.zoom_factor))}x"
            self.lbl_zoom.configure(text=z_txt)
        if hasattr(self, "zoom_scale") and not self._syncing_zoom_slider:
            self._syncing_zoom_slider = True
            try:
                self.zoom_scale.set(self._zoom_to_slider(self.zoom_factor))
            finally:
                self._syncing_zoom_slider = False

    def _viewport_metrics(self) -> Tuple[float, float]:
        cw = max(240, self.canvas.winfo_width())
        vw = max(100.0, float(cw - self.HEADER_W - 12))
        tot_px = max(vw, vw * float(self.zoom_factor))
        max_scroll = max(0.0, tot_px - vw)
        if self.scroll_px > max_scroll:
            self.scroll_px = max_scroll
        return vw, tot_px

    def _sec_to_x(self, sec: float, tot_dur: float, tot_px: float) -> float:
        if tot_dur <= 0:
            return float(self.HEADER_W)
        return self.HEADER_W + (float(sec) / tot_dur) * tot_px - self.scroll_px

    def _x_to_sec(self, x: float) -> float:
        tot_dur = max(0.1, self.nle.total_duration)
        _vw, tot_px = self._viewport_metrics()
        rel_px = max(0.0, min(tot_px, (float(x) - self.HEADER_W) + self.scroll_px))
        return (rel_px / tot_px) * tot_dur

    def _on_zoom_slider(self, val):
        if self._syncing_zoom_slider:
            return
        new_z = self._slider_to_zoom(float(val))
        self._syncing_zoom_slider = True
        try:
            self._apply_zoom_around(new_z, self.playhead_sec)
        finally:
            self._syncing_zoom_slider = False
        if hasattr(self, "lbl_zoom"):
            self.lbl_zoom.configure(
                text=f"🔍{self.zoom_factor:.1f}x" if self.zoom_factor < 10.0 else f"🔍{int(round(self.zoom_factor))}x"
            )

    def step_zoom(self, factor: float):
        mz = self._max_zoom()
        new_z = max(1.0, min(mz, self.zoom_factor * factor))
        self._apply_zoom_around(new_z, self.playhead_sec)
        self._sync_zoom_ui_indicator()

    def zoom_to_cut(self):
        """Instant 1-click deep syllable/frame zoom (~200 px/sec) centered directly on the red playhead!"""
        tot_dur = max(0.5, self.nle.total_duration)
        vw, _ = self._viewport_metrics()
        target_z = min(self._max_zoom(), max(4.0, (tot_dur * 200.0) / max(120.0, vw)))
        self.zoom_factor = target_z
        new_tot_px = max(vw, vw * self.zoom_factor)
        playhead_px = (self.playhead_sec / tot_dur) * new_tot_px
        self.scroll_px = max(0.0, min(max(0.0, new_tot_px - vw), playhead_px - vw * 0.45))
        self._sync_zoom_ui_indicator()
        self.redraw()

    def zoom_fit(self):
        self.zoom_factor = 1.0
        self.scroll_px = 0.0
        self._sync_zoom_ui_indicator()
        self.redraw()

    def _apply_zoom_around(self, new_z: float, anchor_sec: float):
        tot_dur = max(0.1, self.nle.total_duration)
        vw, old_tot_px = self._viewport_metrics()
        anchor_screen_x = self._sec_to_x(anchor_sec, tot_dur, old_tot_px)
        self.zoom_factor = max(1.0, min(self._max_zoom(), new_z))
        new_tot_px = max(vw, vw * self.zoom_factor)
        desired_scroll = (anchor_sec / tot_dur) * new_tot_px - (anchor_screen_x - self.HEADER_W)
        self.scroll_px = max(0.0, min(max(0.0, new_tot_px - vw), desired_scroll))
        self.redraw()

    def _on_hscroll(self, *args):
        vw, tot_px = self._viewport_metrics()
        max_sc = max(0.0, tot_px - vw)
        if not args:
            return
        if args[0] == "moveto":
            frac = max(0.0, min(1.0, float(args[1])))
            self.scroll_px = min(max_sc, frac * tot_px)
        elif args[0] == "scroll":
            amt = int(args[1])
            kind = args[2] if len(args) > 2 else "units"
            step = vw * 0.6 if kind == "pages" else 55.0
            self.scroll_px = max(0.0, min(max_sc, self.scroll_px + amt * step))
        self.redraw()

    def _is_zoom_wheel(self, event) -> bool:
        state = getattr(event, "state", 0)
        # Ctrl is 0x0004
        # Alt on Windows Tkinter: 0x20000 (131072), 0x0008 (Mod1), 0x0020 (Mod2), 0x0080
        is_ctrl = bool(state & 0x0004)
        is_alt = bool((state & 0x20000) or (state & 0x0008) or (state & 0x0020) or (state & 0x0080))
        is_ruler = (getattr(event, "y", 999) <= self.RULER_H and getattr(event, "x", -1) >= self.HEADER_W)
        return is_ctrl or is_alt or is_ruler

    def _on_mousewheel(self, event):
        # Zoom around mouse cursor on Alt+Wheel, Ctrl+Wheel, OR plain Wheel over Timecode Ruler!
        if self._is_zoom_wheel(event):
            anchor_s = self._x_to_sec(max(self.HEADER_W, event.x))
            factor = 1.28 if event.delta > 0 else (1.0 / 1.28)
            new_z = max(1.0, min(self._max_zoom(), self.zoom_factor * factor))
            self._apply_zoom_around(new_z, anchor_s)
            self._sync_zoom_ui_indicator()
        else:
            vw, tot_px = self._viewport_metrics()
            max_sc = max(0.0, tot_px - vw)
            delta_px = -65.0 if event.delta > 0 else 65.0
            self.scroll_px = max(0.0, min(max_sc, self.scroll_px + delta_px))
            self.redraw()

    def _on_canvas_key(self, event):
        k = (event.keysym or "").lower()
        kc = getattr(event, "keycode", 0)
        ctrl = bool(event.state & 0x0004)
        is_b = (kc == 66) or (k in ("b", "arabic_laa", "arabic_lam_alef", "\u0644\u0627", "\u0644"))
        is_s = (kc == 83) or (k in ("s", "arabic_seen", "seen", "\u0633"))
        is_a = (kc == 65) or (k in ("a", "arabic_sheen", "sheen", "\u0634"))

        if (ctrl and is_b) or is_s:
            self.split_at_playhead()
            return "break"
        if not ctrl and is_b:
            self.set_tool_mode("blade")
            return "break"
        if not ctrl and is_a:
            self.set_tool_mode("select")
            return "break"
        if k in ("delete", "backspace") or kc in (46, 8):
            self.delete_selected()
            return "break"

    # ------------------------------------------------------------------
    # Actions: Split, Delete, Duplicate, Undo, Redo
    # ------------------------------------------------------------------
    def split_at_playhead(self):
        if self.selected_ref and self.selected_ref[0] in ("V2", "V3", "V4"):
            tk_key, idx = self.selected_ref
            new_idx = self.nle.split_overlay_at(tk_key, idx, self.playhead_sec)
            if new_idx is not None:
                self.selected_ref = (tk_key, new_idx)
                self.on_select(self.selected_ref)
                self.on_modified()
                self.redraw()
                return

        new_c = self.nle.split_clip_at(self.playhead_sec)
        if new_c is not None:
            self.selected_ref = ("clip", new_c)
            self.on_select(self.selected_ref)
            self.on_modified()
            self.redraw()

    def delete_selected(self):
        if not self.selected_ref:
            return
        kind, idx = self.selected_ref
        if kind == "clip":
            if self.nle.delete_clip(idx):
                new_idx = min(idx, len(self.nle.clips) - 1)
                self.selected_ref = ("clip", new_idx) if self.nle.clips else None
                self.playhead_sec = min(self.playhead_sec, self.nle.total_duration)
                self.on_select(self.selected_ref)
                self.on_modified()
                self.redraw()
        elif kind in ("V2", "V3", "V4"):
            t_list = self.nle.get_track_list(kind)
            if 0 <= idx < len(t_list):
                self.nle.push_undo()
                t_list.pop(idx)
                self.selected_ref = None
                self.on_select(None)
                self.on_modified()
                self.redraw()

    def duplicate_selected(self):
        if not self.selected_ref:
            return
        kind, idx = self.selected_ref
        if kind == "clip":
            new_i = self.nle.duplicate_clip(idx)
            if new_i is not None:
                self.selected_ref = ("clip", new_i)
                self.on_select(self.selected_ref)
                self.on_modified()
                self.redraw()
        elif kind in ("V2", "V3", "V4"):
            t_list = self.nle.get_track_list(kind)
            if 0 <= idx < len(t_list):
                self.nle.push_undo()
                orig = t_list[idx]
                dup = copy.deepcopy(orig)
                dup["id"] = self.nle.next_id(kind.lower())
                if dup.get("full_duration", False):
                    dup["full_duration"] = False
                    dup["start_sec"] = round(self.playhead_sec, 2)
                    dup["end_sec"] = round(self.playhead_sec + 5.0, 2)
                else:
                    dur = max(0.8, float(dup.get("end_sec", 5.0)) - float(dup.get("start_sec", 0.0)))
                    ns = float(dup.get("end_sec", 5.0)) + 0.2
                    dup["start_sec"] = round(ns, 2)
                    dup["end_sec"] = round(ns + dur, 2)
                dup["y"] = min(0.92, float(dup.get("y", 0.5)) + 0.05)
                t_list.append(dup)
                self.selected_ref = (kind, len(t_list) - 1)
                self.on_select(self.selected_ref)
                self.on_modified()
                self.redraw()

    def do_undo(self):
        if hasattr(self, "on_undo_request") and callable(self.on_undo_request):
            if self.on_undo_request():
                return
        if self.nle.undo():
            self.selected_ref = ("clip", 0) if self.nle.clips else None
            self.playhead_sec = min(self.playhead_sec, self.nle.total_duration)
            self.on_select(self.selected_ref)
            self.on_modified()
            self.redraw()

    def do_redo(self):
        if hasattr(self, "on_redo_request") and callable(self.on_redo_request):
            if self.on_redo_request():
                return
        if self.nle.redo():
            self.selected_ref = ("clip", 0) if self.nle.clips else None
            self.playhead_sec = min(self.playhead_sec, self.nle.total_duration)
            self.on_select(self.selected_ref)
            self.on_modified()
            self.redraw()

    def show_hud_toast(self, text: str):
        if hasattr(self, "lbl_hud_toast"):
            self.lbl_hud_toast.configure(text=text)
            self.after(2600, lambda: self.lbl_hud_toast.configure(text="") if hasattr(self, "lbl_hud_toast") else None)

    # ------------------------------------------------------------------
    # Transition Placement & Drag/Drop Engine
    # ------------------------------------------------------------------
    def _get_app(self):
        curr = self
        for _ in range(8):
            if hasattr(curr, "video_branding_config") and hasattr(curr, "push_app_undo"):
                return curr
            curr = getattr(curr, "parent", getattr(curr, "master", None))
            if curr is None:
                break
        return None

    def _get_transitions_config(self) -> Dict[str, Any]:
        app = self._get_app()
        if app and hasattr(app, "video_branding_config"):
            tc = app.video_branding_config.get("transitions_config")
            if not isinstance(tc, dict):
                tc = dict(DEFAULT_TRANSITIONS_CONFIG)
                app.video_branding_config["transitions_config"] = tc
            return tc
        return {}

    def _sync_and_redraw_transitions(self):
        app = self._get_app()
        if app:
            if hasattr(app, "_save_settings"):
                app._save_settings()
            if hasattr(app, "refresh_video_transitions_panel"):
                app.refresh_video_transitions_panel()
            if hasattr(app, "_refresh_master_export_summary"):
                app._refresh_master_export_summary()
        self.redraw()

    def _hit_test_cut_seam(self, mx: float, my: float, tol: float = 16.0) -> Optional[Tuple[int, float, bool, str, float]]:
        """Returns (cut_idx, cut_x, has_cut_trans, t_key, t_dur) or None."""
        for cut_idx, cut_x, v1_y0, v1_y1, a1_y1, has_trans, t_key, t_dur in self._cut_hit_boxes:
            if (v1_y0 - 4) <= my <= (a1_y1 + 4) and abs(mx - cut_x) <= tol:
                return (cut_idx, cut_x, has_trans, t_key, t_dur)
        return None

    def _find_nearest_cut_seam(self, mx: float, my: float, tolerance_px: float = 32.0) -> Optional[int]:
        v1_y0, _ = self._track_y_bounds("V1")
        _, a1_y1 = self._track_y_bounds("A1")
        if not (v1_y0 - 15 <= my <= a1_y1 + 15):
            return None
        best_d = tolerance_px
        best_idx = None
        for cut_idx, cut_x, *_rest in self._cut_hit_boxes:
            d = abs(mx - cut_x)
            if d < best_d:
                best_d = d
                best_idx = cut_idx
        return best_idx

    def _clear_trans_guides(self):
        if self._trans_guide_ids:
            for gid in self._trans_guide_ids:
                try:
                    self.canvas.delete(gid)
                except Exception:
                    pass
            self._trans_guide_ids.clear()

    def assign_transition_to_cut(self, cut_idx: int, trans_key: str, dur: float):
        if len(self.nle.clips) <= 1:
            ar = self._is_ar()
            self.show_hud_toast("⚠️ لا توجد تقطيعات في الفيديو (قسّم الفيديو بـ Ctrl+B أولاً)" if ar else "⚠️ No cuts in video (split with Ctrl+B first)")
            return
        tc = self._get_transitions_config()
        tc["enabled"] = True
        tc["apply_to_all"] = False
        if "clip_transitions" not in tc or not isinstance(tc["clip_transitions"], dict):
            tc["clip_transitions"] = {}
        tc["clip_transitions"][str(cut_idx)] = {
            "transition": trans_key,
            "duration": round(float(dur), 2)
        }
        app = self._get_app()
        if app and hasattr(app, "push_app_undo"):
            info = get_transition_info(trans_key)
            name = info.get("label_ar") if self._is_ar() else info.get("label_en")
            app.push_app_undo(f"وضع انتقال {name} على القطع #{cut_idx+1}", f"Set transition on cut #{cut_idx+1}")
        self._sync_and_redraw_transitions()

    def remove_transition_from_cut(self, cut_idx: int):
        tc = self._get_transitions_config()
        clip_map = tc.get("clip_transitions", {})
        if str(cut_idx) in clip_map:
            del clip_map[str(cut_idx)]
        if int(cut_idx) in clip_map:
            del clip_map[int(cut_idx)]
        if not clip_map and not tc.get("apply_to_all", False):
            tc["enabled"] = False
        app = self._get_app()
        if app and hasattr(app, "push_app_undo"):
            app.push_app_undo(f"إزالة الانتقال من القطع #{cut_idx+1}", f"Remove transition from cut #{cut_idx+1}")
        self._sync_and_redraw_transitions()
        msg = f"تمت إزالة الانتقال من القطع #{cut_idx+1} (قطع مباشر)" if self._is_ar() else f"Transition removed from cut #{cut_idx+1}"
        self.show_hud_toast(msg)

    def _show_cut_transition_menu(self, event, cut_idx: int, has_trans: bool, t_key: str, t_dur: float):
        ar = self._is_ar()
        menu = tk.Menu(self, tearoff=0)
        app = self._get_app()
        cur_k = "smoothleft"
        cur_dur = 0.5
        if app and hasattr(app, "_studio_trans_map") and hasattr(app, "trans_preset_var"):
            cur_disp = app.trans_preset_var.get()
            cur_k = app._studio_trans_map.get(cur_disp, "smoothleft")
            try:
                cur_dur = float(app.trans_dur_var.get())
            except Exception:
                cur_dur = 0.5

        if has_trans:
            info = get_transition_info(t_key)
            name = info.get("label_ar") if ar else info.get("label_en")
            icon = info.get("icon", "✨")
            menu.add_command(
                label=f"{icon} {name} ({t_dur:.2f}s) - " + (f"القطع #{cut_idx+1}" if ar else f"Cut #{cut_idx+1}"),
                state="disabled",
            )
            menu.add_separator()
            menu.add_command(
                label="📂 " + ("تغيير نوع الانتقال لهذا القطع..." if ar else "Change Transition for this cut..."),
                command=lambda: self._open_trans_dialog_for_cut(cut_idx),
            )
            menu.add_command(
                label="⚡ " + ("ضبط المدة: 0.3s (سريع)" if ar else "Set Duration: 0.3s (Fast)"),
                command=lambda: self.assign_transition_to_cut(cut_idx, t_key, 0.30),
            )
            menu.add_command(
                label="🎬 " + ("ضبط المدة: 0.5s (متوازن)" if ar else "Set Duration: 0.5s (Standard)"),
                command=lambda: self.assign_transition_to_cut(cut_idx, t_key, 0.50),
            )
            menu.add_command(
                label="🌊 " + ("ضبط المدة: 1.0s (سينمائي)" if ar else "Set Duration: 1.0s (Cinematic)"),
                command=lambda: self.assign_transition_to_cut(cut_idx, t_key, 1.00),
            )
            menu.add_separator()
            menu.add_command(
                label="❌ " + ("إزالة الانتقال من هذا القطع فقط (قطع مباشر)" if ar else "Remove Transition from this cut"),
                command=lambda: self.remove_transition_from_cut(cut_idx),
            )
            menu.add_command(
                label="🌐 " + ("تطبيق هذا الانتقال على جميع تقطيعات الفيديو" if ar else "Apply this transition to ALL cuts"),
                command=lambda: self._apply_trans_to_all_cuts(t_key, t_dur),
            )
        else:
            cur_info = get_transition_info(cur_k)
            c_name = cur_info.get("label_ar") if ar else cur_info.get("label_en")
            c_icon = cur_info.get("icon", "✨")
            menu.add_command(
                label="🎬 " + (f"القطع #{cut_idx+1}" if ar else f"Cut #{cut_idx+1}"),
                state="disabled",
            )
            menu.add_separator()
            menu.add_command(
                label=f"✨ " + (f"وضع الانتقال الحالي ({c_icon} {c_name}) هنا" if ar else f"Place Selected Transition ({c_name}) Here"),
                command=lambda: self.assign_transition_to_cut(cut_idx, cur_k, cur_dur),
            )
            menu.add_command(
                label="📂 " + ("اختيار انتقال من المكتبة (46+ حركة)..." if ar else "Choose from Transitions Library..."),
                command=lambda: self._open_trans_dialog_for_cut(cut_idx),
            )

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _open_trans_dialog_for_cut(self, cut_idx: int):
        app = self._get_app()
        if app and hasattr(app, "open_video_transitions_dialog"):
            app.open_video_transitions_dialog(target_cut_index=cut_idx)
        else:
            from ui_dialogs.video_transition_dialog import VideoTransitionDialog
            dlg = VideoTransitionDialog(self, target_cut_index=cut_idx)
            dlg.wait_window()
            self._sync_and_redraw_transitions()

    def _apply_trans_to_all_cuts(self, trans_key: str, dur: float):
        tc = self._get_transitions_config()
        tc["enabled"] = True
        tc["default_transition"] = trans_key
        tc["default_duration"] = round(float(dur), 2)
        tc["apply_to_all"] = True
        tc["clip_transitions"] = {}
        app = self._get_app()
        if app and hasattr(app, "push_app_undo"):
            app.push_app_undo("تطبيق الانتقال على كل التقطيعات", "Apply transition to all cuts")
        self._sync_and_redraw_transitions()
        msg = "تم تطبيق الانتقال على جميع تقطيعات التايم لاين" if self._is_ar() else "Applied transition to all cuts"
        self.show_hud_toast(msg)

    def on_external_trans_drag_hover(self, root_x: int, root_y: int, key: str, dur: float):
        if not self.canvas.winfo_exists():
            return
        cx = root_x - self.canvas.winfo_rootx()
        cy = root_y - self.canvas.winfo_rooty()
        cw = max(240, self.canvas.winfo_width())
        ch = max(self.total_canvas_height, self.canvas.winfo_height())

        self._clear_trans_guides()
        if cx < self.HEADER_W or cx > cw or cy < self.RULER_H or cy > ch:
            return

        cut_idx = self._find_nearest_cut_seam(cx, cy, tolerance_px=36.0)
        c = self.canvas
        v1_y0, _ = self._track_y_bounds("V1")
        _, a1_y1 = self._track_y_bounds("A1")

        if cut_idx is not None:
            cut_x = None
            for idx, kx, *_ in self._cut_hit_boxes:
                if idx == cut_idx:
                    cut_x = kx
                    break
            if cut_x is not None:
                lid = c.create_line(cut_x, self.RULER_H, cut_x, a1_y1, fill="#00e5ff", width=3)
                lbl_txt = f"🟢 إفلات لوضع الانتقال على القطع #{cut_idx+1}" if self._is_ar() else f"🟢 Drop on Cut #{cut_idx+1}"
                bid = c.create_rectangle(cut_x - 72, v1_y0 + 6, cut_x + 72, v1_y0 + 26, fill="#0d2d1f", outline="#00e5ff", width=2)
                tid = c.create_text(cut_x, v1_y0 + 16, text=lbl_txt, fill="#b7f5cb", font=("Segoe UI", 8, "bold"))
                self._trans_guide_ids.extend([lid, bid, tid])
        else:
            lid = c.create_line(cx, v1_y0, cx, a1_y1, fill="#ff4d4f", width=2, dash=(4, 2))
            lbl_txt = "🚫 لا يوجد قطع هنا" if self._is_ar() else "🚫 No cut here"
            bid = c.create_rectangle(cx - 52, v1_y0 + 6, cx + 52, v1_y0 + 26, fill="#381014", outline="#ff4d4f", width=1)
            tid = c.create_text(cx, v1_y0 + 16, text=lbl_txt, fill="#ffa39e", font=("Segoe UI", 8, "bold"))
            self._trans_guide_ids.extend([lid, bid, tid])

    def on_external_trans_drag_drop(self, root_x: int, root_y: int, key: str, dur: float):
        self._clear_trans_guides()
        if not self.canvas.winfo_exists():
            return
        cx = root_x - self.canvas.winfo_rootx()
        cy = root_y - self.canvas.winfo_rooty()
        cw = max(240, self.canvas.winfo_width())
        ch = max(self.total_canvas_height, self.canvas.winfo_height())
        ar = self._is_ar()

        if len(self.nle.clips) <= 1:
            msg = "⚠️ لا توجد تقطيعات في التايم لاين حالياً!\nيجب تقسيم الفيديو أولاً (Ctrl+B) لإضافة انتقال." if ar else "⚠️ No cuts on timeline! Split video first with Ctrl+B."
            self.show_hud_toast(msg)
            return

        if cx < self.HEADER_W or cx > cw or cy < self.RULER_H or cy > ch:
            msg = "⚠️ تم الإفلات خارج التايم لاين - لم يتم إضافة شيء" if ar else "⚠️ Dropped outside timeline - nothing added"
            self.show_hud_toast(msg)
            return

        cut_idx = self._find_nearest_cut_seam(cx, cy, tolerance_px=36.0)
        if cut_idx is not None:
            self.assign_transition_to_cut(cut_idx, key, dur)
            info = get_transition_info(key)
            t_name = info.get("label_ar") if ar else info.get("label_en")
            self.show_hud_toast(f"✅ تم وضع انتقال ({t_name}) بنجاح على القطع #{cut_idx+1}!")
        else:
            msg = "⚠️ لم يتم العثور على قطع في هذا المكان! لا يمكن إضافة انتقال إلا عند فواصل التقطيع (قسّم بـ Ctrl+B أولاً)." if ar else "⚠️ No cut seam found here! Transitions require a cut point (split with Ctrl+B first)."
            self.show_hud_toast(msg)

    # ------------------------------------------------------------------
    # Formatting Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _fmt_tc(seconds: float, precision: Any = "sec") -> str:
        s = max(0.0, float(seconds or 0.0))
        whole = int(s)
        frac = s - whole
        m, sec = divmod(whole, 60)
        h, m = divmod(m, 60)
        base = f"{h:02d}:{m:02d}:{sec:02d}" if h > 0 else f"{m:02d}:{sec:02d}"
        if precision is True or precision == "tenth":
            return f"{base}.{int(frac * 10)}"
        if precision == "hundredth":
            return f"{base}.{int(round(frac * 100)) % 100:02d}"
        return base

    def _track_y_bounds(self, track_key: str) -> Tuple[int, int]:
        y = self.RULER_H
        for tkey, th, *_ in self.TRACK_SPECS:
            if tkey == track_key:
                return y, y + th
            y += th
        return y, y + 32

    def _y_to_track(self, y: float) -> Optional[str]:
        if y < self.RULER_H:
            return "RULER"
        cur_y = self.RULER_H
        for tkey, th, *_ in self.TRACK_SPECS:
            if cur_y <= y < cur_y + th:
                return tkey
            cur_y += th
        return None

    # ------------------------------------------------------------------
    # Rendering (DaVinci Resolve Style)
    # ------------------------------------------------------------------
    def redraw(self):
        if not self.canvas.winfo_exists():
            return
        c = self.canvas
        c.delete("all")
        self._item_hit_boxes.clear()
        self._gap_hit_boxes.clear()
        self._cut_hit_boxes.clear()
        self._clear_trans_guides()

        cw = max(240, c.winfo_width())
        ch = max(self.total_canvas_height, c.winfo_height())
        ar = self._is_ar()

        self.nle.recompute_timeline()
        tot_dur = max(0.3, self.nle.total_duration)
        vw, tot_px = self._viewport_metrics()

        # Sync scrollbar thumb
        lo_frac = self.scroll_px / max(1.0, tot_px)
        hi_frac = min(1.0, (self.scroll_px + vw) / max(1.0, tot_px))
        self.h_scroll.set(lo_frac, hi_frac)

        # Update undo/redo & gaps visual state
        can_u = self.can_undo_fn() if (hasattr(self, "can_undo_fn") and callable(self.can_undo_fn)) else self.nle.can_undo()
        can_r = self.can_redo_fn() if (hasattr(self, "can_redo_fn") and callable(self.can_redo_fn)) else self.nle.can_redo()
        self.btn_undo.configure(fg="#e6edf3" if can_u else "#555d69")
        self.btn_redo.configure(fg="#e6edf3" if can_r else "#555d69")
        has_gaps = bool(self.nle.get_timeline_gaps())
        self.btn_close_gaps.configure(fg="#79c0ff" if has_gaps else "#555d69")

        # 1. Background Track Lanes
        c.create_rectangle(0, 0, cw, self.RULER_H, fill="#181c24", outline="")
        cur_y = self.RULER_H
        for idx, (tkey, th, *_rest) in enumerate(self.TRACK_SPECS):
            lane_bg = "#13171f" if idx % 2 == 0 else "#161b24"
            if not self.nle.track_enabled.get(tkey, True):
                lane_bg = "#0d0f13"
            c.create_rectangle(self.HEADER_W, cur_y, cw, cur_y + th, fill=lane_bg, outline="")
            c.create_line(0, cur_y + th, cw, cur_y + th, fill="#242a35", width=1)
            cur_y += th

        # 2. Adaptive High-Zoom Timecode Ruler Ticks & Vertical Grid Lines
        px_per_sec = tot_px / tot_dur
        nice_steps = [0.05, 0.1, 0.2, 0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900]
        major_step = nice_steps[-1]
        for st in nice_steps:
            if st * px_per_sec >= 66:
                major_step = st
                break
        minor_step = major_step / 5.0

        start_vis_s = max(0.0, (self.scroll_px / tot_px) * tot_dur)
        end_vis_s = min(tot_dur, ((self.scroll_px + vw + 24) / tot_px) * tot_dur)

        first_tick = math.floor(start_vis_s / minor_step) * minor_step
        t_val = first_tick
        tc_prec = "hundredth" if major_step < 0.1 else ("tenth" if major_step < 1.0 else "sec")
        tick_guard = 0
        while t_val <= end_vis_s + 1e-6 and tick_guard < 450:
            tick_guard += 1
            tx = self._sec_to_x(t_val, tot_dur, tot_px)
            if self.HEADER_W <= tx <= cw:
                is_major = abs(round(t_val / major_step) * major_step - t_val) < (minor_step * 0.20)
                if is_major:
                    c.create_line(tx, self.RULER_H - 9, tx, self.RULER_H, fill="#8b949e", width=1)
                    c.create_line(tx, self.RULER_H, tx, cur_y, fill="#1d222c", width=1)
                    c.create_text(
                        tx + 3, 4,
                        text=self._fmt_tc(t_val, tc_prec),
                        anchor="nw",
                        fill="#9ca3af",
                        font=("Consolas", 8),
                    )
                else:
                    c.create_line(tx, self.RULER_H - 4, tx, self.RULER_H, fill="#484f58", width=1)
            t_val += minor_step
        c.create_line(0, self.RULER_H, cw, self.RULER_H, fill="#30363d", width=1)

        # 3. Draw Overlay Tracks: V4 (Logo), V3 (Text+), V2 (Icons & Images)
        for tkey, _th, col_body, col_hdr, *_ in self.TRACK_SPECS[:3]:
            y0, y1 = self._track_y_bounds(tkey)
            items = self.nle.get_track_list(tkey)
            track_on = self.nle.track_enabled.get(tkey, True)
            for idx, it in enumerate(items):
                if not it.get("enabled", True):
                    continue
                is_full = bool(it.get("full_duration", False))
                s_sec = 0.0 if is_full else max(0.0, float(it.get("start_sec", 0.0)))
                e_sec = tot_dur if is_full else max(s_sec + 0.15, float(it.get("end_sec", min(tot_dur, s_sec + 5.0))))
                x0 = self._sec_to_x(s_sec, tot_dur, tot_px)
                x1 = max(x0 + 10, self._sec_to_x(e_sec, tot_dur, tot_px))
                if x1 < self.HEADER_W or x0 > cw:
                    continue

                dx0 = max(self.HEADER_W, x0)
                dx1 = min(cw, x1)
                is_sel = (self.selected_ref == (tkey, idx))
                fill_c = col_body if track_on else "#252932"
                hdr_c = col_hdr if track_on else "#303540"
                out_c = "#ff5533" if is_sel else "#424a57"

                c.create_rectangle(dx0, y0 + 3, dx1, y1 - 3, fill=fill_c, outline=out_c, width=2 if is_sel else 1)
                c.create_rectangle(dx0 + 1, y0 + 4, dx1 - 1, y0 + 10, fill=hdr_c, outline="")

                lbl = self._overlay_display_label(tkey, it, ar)
                if is_full:
                    lbl = f"∞ {lbl}"
                avail_w = dx1 - dx0 - 10
                if avail_w > 22:
                    max_chars = max(3, int(avail_w / 6.5))
                    c.create_text(dx0 + 6, (y0 + y1) // 2 + 1, text=lbl[:max_chars], anchor="w", fill="#f0f6fc", font=("Segoe UI", 8, "bold"))

                if is_sel:
                    c.create_rectangle(dx0, y0 + 3, min(dx1, dx0 + 4), y1 - 3, fill="#ffffff", outline="")
                    c.create_rectangle(max(dx0, dx1 - 4), y0 + 3, dx1, y1 - 3, fill="#ffffff", outline="")

                self._item_hit_boxes.append((tkey, idx, x0, y0 + 2, x1, y1 - 2))

        # 4. Draw Track V1 (Video Clips + Visual Gaps) & Track A1 (Green Audio Waveform!)
        v1_y0, v1_y1 = self._track_y_bounds("V1")
        a1_y0, a1_y1 = self._track_y_bounds("A1")
        src_total = max(0.5, float(self.nle.source_duration or tot_dur))
        a1_track_on = self.nle.track_enabled.get("A1", True)

        # 4a. Draw Timeline Gaps between separated clips
        for gs, ge in self.nle.get_timeline_gaps():
            gx0 = self._sec_to_x(gs, tot_dur, tot_px)
            gx1 = self._sec_to_x(ge, tot_dur, tot_px)
            if gx1 < self.HEADER_W or gx0 > cw:
                continue
            dgx0 = max(self.HEADER_W, gx0)
            dgx1 = min(cw, gx1)
            if dgx1 - dgx0 >= 3:
                c.create_rectangle(
                    dgx0, v1_y0 + 3, dgx1, a1_y1 - 3,
                    fill="#0b0e14", outline="#30363d", dash=(3, 3), width=1,
                )
                g_dur = ge - gs
                if dgx1 - dgx0 >= 48:
                    g_lbl = f"↔ فجوة {g_dur:.1f}s" if ar else f"↔ Gap {g_dur:.1f}s"
                    c.create_text(
                        (dgx0 + dgx1) / 2.0,
                        (v1_y0 + a1_y1) / 2.0,
                        text=g_lbl,
                        fill="#6e7681",
                        font=("Segoe UI", 7, "italic"),
                    )
                self._gap_hit_boxes.append((gs, ge, gx0, gx1))

        # 4b. Draw V1 & A1 Clips
        if not self.nle.clips:
            empty_msg = "🎬 اسحب وأفلت فيديو هنا أو اختر ملفاً للبدء" if ar else "🎬 Drag & drop video here or choose a file to begin"
            c.create_text(
                (self.HEADER_W + cw) / 2.0,
                (v1_y0 + a1_y1) / 2.0,
                text=empty_msg,
                fill="#555d6b",
                font=("Segoe UI", 9, "bold"),
            )
        for idx, clip in enumerate(self.nle.clips):
            tl_s = clip["tl_start"]
            tl_e = clip["tl_end"]
            x0 = self._sec_to_x(tl_s, tot_dur, tot_px)
            x1 = max(x0 + 6, self._sec_to_x(tl_e, tot_dur, tot_px))
            if x1 < self.HEADER_W or x0 > cw:
                continue

            dx0 = max(self.HEADER_W, x0)
            dx1 = min(cw, x1)
            is_sel = (self.selected_ref == ("clip", idx))
            is_sil_clip = str(clip.get("name", "")).startswith("🔇")
            out_c = "#ff5533" if is_sel else "#11141a"
            out_w = 2 if is_sel else 1

            v_fill = "#3a2528" if is_sil_clip else "#28486e"
            v_hdr = "#543237" if is_sil_clip else "#366194"
            c.create_rectangle(dx0, v1_y0 + 2, dx1 - 1, v1_y1 - 2, fill=v_fill, outline=out_c, width=out_w)
            c.create_rectangle(dx0 + 1, v1_y0 + 3, dx1 - 2, v1_y0 + 15, fill=v_hdr, outline="")

            badges = []
            if clip.get("custom_transform"):
                badges.append(f"🔍{float(clip.get('zoom', 1.0)):.1f}x")
            if abs(float(clip.get("speed", 1.0)) - 1.0) > 0.02:
                badges.append(f"⚡{float(clip.get('speed', 1.0)):.2g}x")
            title_str = f"{clip.get('name', f'Clip {idx+1}')}  {' '.join(badges)}".strip()
            avail_w = dx1 - dx0 - 10
            if avail_w > 28:
                c.create_text(
                    dx0 + 6,
                    v1_y0 + 9,
                    text=title_str[: max(4, int(avail_w / 6.5))],
                    anchor="w",
                    fill="#ffffff",
                    font=("Segoe UI", 8, "bold"),
                )
                dur_lbl = f"@{tl_s:.1f}s | {self._fmt_tc(clip['src_start'], 'tenth')}→{self._fmt_tc(clip['src_end'], 'tenth')}"
                if avail_w > 76:
                    c.create_text(
                        dx0 + 6,
                        v1_y0 + 27,
                        text=dur_lbl[: max(6, int(avail_w / 5.8))],
                        anchor="w",
                        fill="#b6d4fe",
                        font=("Consolas", 7),
                    )

            if is_sel:
                c.create_rectangle(dx0, v1_y0 + 2, min(dx1, dx0 + 4), v1_y1 - 2, fill="#ffffff", outline="")
                c.create_rectangle(max(dx0, dx1 - 5), v1_y0 + 2, dx1 - 1, v1_y1 - 2, fill="#ffffff", outline="")

            # --- A1 Green Audio Clip Block + High-Density Waveform ---
            clip_muted = (not a1_track_on) or bool(clip.get("muted", False)) or float(clip.get("volume", 1.0)) <= 0.01
            a_fill = "#1f2924" if clip_muted else "#1b5933"
            a_hdr = "#2b3831" if clip_muted else "#257845"
            c.create_rectangle(dx0, a1_y0 + 2, dx1 - 1, a1_y1 - 2, fill=a_fill, outline=out_c, width=out_w)
            c.create_rectangle(dx0 + 1, a1_y0 + 3, dx1 - 2, a1_y0 + 12, fill=a_hdr, outline="")

            wf_top = a1_y0 + 13
            wf_bot = a1_y1 - 3
            wf_mid = (wf_top + wf_bot) / 2.0
            wf_half = max(3.0, (wf_bot - wf_top) / 2.0 - 1.0)
            bar_col = "#56695e" if clip_muted else "#b7f5cb"

            px_span = int(dx1 - dx0 - 4)
            if px_span >= 4:
                step_px = 3
                peaks = self.waveform_peaks
                n_peaks = len(peaks) if peaks else 0
                cs0 = float(clip["src_start"])
                cs1 = float(clip["src_end"])
                c_span = max(0.05, cs1 - cs0)
                full_clip_w = max(1.0, x1 - x0)
                vol_mul = min(1.4, float(clip.get("volume", 1.0)))

                for bx in range(int(dx0 + 2), int(dx1 - 2), step_px):
                    rel_frac = (bx - x0) / full_clip_w
                    src_t = cs0 + rel_frac * c_span
                    if n_peaks > 0 and src_total > 0:
                        f_pos = max(0.0, min(float(n_peaks - 1), (src_t / src_total) * n_peaks))
                        i0 = int(f_pos)
                        i1 = min(n_peaks - 1, i0 + 1)
                        frac_p = f_pos - i0
                        amp = peaks[i0] * (1.0 - frac_p) + peaks[i1] * frac_p
                    else:
                        amp = 0.25 + 0.35 * abs(math.sin(src_t * 3.7) * math.cos(src_t * 1.3))
                    bh = max(1.5, min(wf_half, amp * vol_mul * wf_half))
                    c.create_line(bx, wf_mid - bh, bx, wf_mid + bh, fill=bar_col, width=2)

            if avail_w > 48:
                a_lbl = "🔇 صامت" if (clip_muted and ar) else ("🔇 Muted" if clip_muted else f"🔗 {clip.get('name', 'Audio')[:18]}")
                c.create_text(dx0 + 5, a1_y0 + 7, text=a_lbl, anchor="w", fill="#dcffe4", font=("Segoe UI", 7))

            if idx > 0 and self.HEADER_W <= x0 <= cw:
                c.create_line(x0, v1_y0, x0, a1_y1, fill="#090b0f", width=2)

            self._item_hit_boxes.append(("clip", idx, x0, v1_y0 + 2, x1, a1_y1 - 2))

            # 4c. Draw transition indicator badge and register cut hit boxes
            if idx < len(self.nle.clips) - 1:
                cut_idx = idx
                cut_x = x1
                tc = self._get_transitions_config()
                en = bool(tc.get("enabled", False))
                apply_all = bool(tc.get("apply_to_all", True))
                clip_map = tc.get("clip_transitions", {})

                cut_data = clip_map.get(str(cut_idx), clip_map.get(cut_idx, None))
                has_cut_trans = False
                t_key = "none"
                t_dur = float(tc.get("default_duration", 0.5))

                if en:
                    if cut_data is not None:
                        if isinstance(cut_data, dict):
                            t_key = cut_data.get("transition", "none")
                            t_dur = float(cut_data.get("duration", t_dur))
                        elif isinstance(cut_data, str):
                            t_key = cut_data
                        has_cut_trans = (t_key not in ("none", "", None))
                    elif apply_all:
                        t_key = tc.get("default_transition", "smoothleft")
                        has_cut_trans = (t_key not in ("none", "", None))

                self._cut_hit_boxes.append((cut_idx, cut_x, v1_y0, v1_y1, a1_y1, has_cut_trans, t_key, t_dur))

                if self.HEADER_W + 6 <= cut_x <= cw - 6:
                    if has_cut_trans:
                        t_info = get_transition_info(t_key)
                        t_icon = t_info.get("icon", "✨")
                        c.create_rectangle(
                            cut_x - 11, v1_y0 + 5, cut_x + 11, v1_y0 + 25,
                            fill="#1f6feb", outline="#58a6ff", width=1
                        )
                        c.create_text(cut_x, v1_y0 + 15, text=t_icon, font=("Segoe UI", 8))
                        # Small duration badge below icon
                        c.create_text(
                            cut_x, v1_y0 + 32,
                            text=f"{t_dur:.1f}s",
                            fill="#79c0ff",
                            font=("Consolas", 6, "bold"),
                        )
                    else:
                        # Subtle seam marker that invites adding transition
                        c.create_polygon(
                            [cut_x - 4, v1_y0 + 2, cut_x + 4, v1_y0 + 2, cut_x, v1_y0 + 8],
                            fill="#6e7681", outline=""
                        )

        # 5. Magnetic Snap Guide Line
        if self._snap_guide_sec is not None:
            sx = self._sec_to_x(self._snap_guide_sec, tot_dur, tot_px)
            if self.HEADER_W <= sx <= cw:
                c.create_line(sx, self.RULER_H, sx, cur_y, fill="#00e5ff", width=1, dash=(4, 2))

        # 6. Hover Blade / Razor Split Preview Items (kept persistent for O(1) hover updates)
        self._blade_line_id = c.create_line(0, self.RULER_H, 0, cur_y, fill="#ffd700", width=2, dash=(5, 3), state="hidden")
        self._blade_box_id = c.create_rectangle(0, 0, 10, 10, fill="#2b2300", outline="#ffd700", state="hidden")
        self._blade_txt_id = c.create_text(0, 0, text="", anchor="w", fill="#ffd700", font=("Consolas", 8, "bold"), state="hidden")

        # 7. Pinned Left Track Headers Column + Per-Track [+] Action Buttons
        c.create_rectangle(0, 0, self.HEADER_W, ch, fill="#191d26", outline="")
        c.create_line(self.HEADER_W, 0, self.HEADER_W, ch, fill="#343b48", width=1)

        # Top-Left Timecode Box
        c.create_rectangle(2, 2, self.HEADER_W - 3, self.RULER_H - 2, fill="#101319", outline="#2b313d")
        self._tc_text_id = c.create_text(
            self.HEADER_W // 2,
            self.RULER_H // 2,
            text=self._fmt_tc(self.playhead_sec, "tenth"),
            fill="#ff5533",
            font=("Consolas", 9, "bold"),
        )

        hy = self.RULER_H
        for tkey, th, col_body, col_hdr, lbl_ar, lbl_en, act_sym in self.TRACK_SPECS:
            en = self.nle.track_enabled.get(tkey, True)
            c.create_rectangle(0, hy, self.HEADER_W, hy + th, fill="#1a1f29" if en else "#12151c", outline="")
            c.create_rectangle(0, hy + 1, 4, hy + th - 1, fill=col_body if en else "#30363d", outline="")
            c.create_line(0, hy + th, self.HEADER_W, hy + th, fill="#282f3c", width=1)

            # Eye / Speaker toggle box (x: 7..25)
            toggle_icon = ("🔊" if en else "🔇") if tkey == "A1" else ("👁" if en else "🚫")
            c.create_rectangle(7, hy + (th // 2) - 9, 25, hy + (th // 2) + 9, fill="#242b38", outline="#384152")
            c.create_text(16, hy + th // 2, text=toggle_icon, fill="#e6edf3" if en else "#6e7681", font=("Segoe UI", 8))

            # Track title
            t_label = lbl_ar if ar else lbl_en
            c.create_text(29, hy + th // 2, text=t_label, anchor="w", fill="#e6edf3" if en else "#6e7681", font=("Segoe UI", 8, "bold"))

            # Per-Track Quick Add / Split Button (x: HEADER_W-24 .. HEADER_W-5)
            bx0, bx1 = self.HEADER_W - 24, self.HEADER_W - 5
            by0, by1 = hy + (th // 2) - 9, hy + (th // 2) + 9
            c.create_rectangle(bx0, by0, bx1, by1, fill=col_hdr if en else "#252a34", outline="#485266")
            c.create_text((bx0 + bx1) // 2, hy + th // 2, text=act_sym, fill="#ffffff", font=("Segoe UI", 8, "bold"))
            hy += th

        # 8. DaVinci Resolve Red Playhead (persistent IDs for O(1) playback updates)
        self._playhead_line_id = c.create_line(0, 12, 0, cur_y, fill="#ff2e2e", width=2, state="hidden")
        self._playhead_cap_id = c.create_polygon(
            [0, 1, 14, 1, 14, 10, 7, 17, 0, 10],
            fill="#ff2e2e",
            outline="#ffffff",
            width=1,
            state="hidden",
        )
        self._cached_metrics = (tot_dur, tot_px, self.scroll_px, cw, cur_y)
        self._update_playhead_fast()
        self._update_blade_preview_fast()

    def _overlay_display_label(self, tkey: str, item: Dict[str, Any], ar: bool) -> str:
        if tkey == "V3":
            raw = str(item.get("text", "")).strip() or ("نص" if ar else "Text")
            return f"T+ {prepare_arabic_for_rendering(raw)}"
        if tkey == "V4":
            p = str(item.get("path", "")).strip()
            nm = Path(p).name if p else ("الشعار" if ar else "Logo")
            return f"🛡️ {nm}"
        if item.get("type") == "image":
            p = str(item.get("path", "")).strip()
            return f"🖼️ {Path(p).name if p else 'Image'}"
        ikey = item.get("icon_key", "subscribe_ar")
        info = ICON_PRESETS.get(ikey, {})
        return info.get("label_ar" if ar else "label_en", ikey)

    # ------------------------------------------------------------------
    # Mouse Interactions (Free Clip Dragging, Edge Trimming, Track [+] Buttons)
    # ------------------------------------------------------------------
    def _hit_test(self, mx: float, my: float) -> Tuple[Optional[Tuple[str, int]], str]:
        for kind, idx, x0, y0, x1, y1 in reversed(self._item_hit_boxes):
            if y0 <= my <= y1 and (x0 - 4) <= mx <= (x1 + 4):
                if kind in ("V2", "V3", "V4"):
                    if (x1 - x0) >= 14:
                        if abs(mx - x0) <= 6:
                            return (kind, idx), "left"
                        if abs(mx - x1) <= 6:
                            return (kind, idx), "right"
                elif kind == "clip" and (x1 - x0) >= 16:
                    if abs(mx - x0) <= 6:
                        return (kind, idx), "left"
                    if abs(mx - x1) <= 6:
                        return (kind, idx), "right"
                return (kind, idx), "body"
        return None, "none"

    def _snap_time(self, raw_sec: float, ignore_ref: Optional[Tuple[str, int]] = None) -> Tuple[float, Optional[float]]:
        tot_dur = max(0.3, self.nle.total_duration)
        _vw, tot_px = self._viewport_metrics()
        thresh_sec = 6.5 * (tot_dur / max(1.0, tot_px))

        candidates = [0.0, tot_dur, self.playhead_sec]
        for idx, c in enumerate(self.nle.clips):
            if ignore_ref == ("clip", idx):
                continue
            candidates.append(c["tl_start"])
            candidates.append(c["tl_end"])

        best_d = thresh_sec
        snapped = raw_sec
        guide = None
        for cand in candidates:
            d = abs(raw_sec - cand)
            if d < best_d:
                best_d = d
                snapped = cand
                guide = cand
        return snapped, guide

    def _handle_header_click(self, event, tkey: str):
        mx = event.x
        # Clicked Per-Track [+] / Action button on right side of track header
        if mx >= self.HEADER_W - 26:
            if tkey == "V4":
                self.on_add_element("logo", self.playhead_sec)
            elif tkey == "V3":
                self.on_add_element("text", self.playhead_sec)
            elif tkey == "V2":
                ar = self._is_ar()
                m = tk.Menu(self, tearoff=0)
                m.add_command(
                    label="⭐ " + ("إضافة أيقونة أو شارة عند المؤشر" if ar else "Add Pro Icon / Badge at Playhead"),
                    command=lambda: self.on_add_element("icon", self.playhead_sec),
                )
                m.add_command(
                    label="🖼️ " + ("إضافة صورة خارجية عند المؤشر" if ar else "Add Custom Image at Playhead"),
                    command=lambda: self.on_add_element("image", self.playhead_sec),
                )
                try:
                    m.tk_popup(event.x_root, event.y_root)
                finally:
                    m.grab_release()
            elif tkey == "V1":
                self.split_at_playhead()
            elif tkey == "A1":
                self._show_silence_split_menu()
            return

        # Clicked Visibility / Mute toggle (left side of track header)
        self.nle.track_enabled[tkey] = not self.nle.track_enabled.get(tkey, True)
        self.on_modified()
        self.redraw()

    def _on_press(self, event):
        self.canvas.focus_set()
        mx, my = event.x, event.y
        self._drag_moved = False
        self._undo_pushed_for_drag = False
        self._snap_guide_sec = None

        # 1. Left Track Headers (Visibility/Mute or Per-Track [+] Add Button)
        if mx < self.HEADER_W:
            tkey = self._y_to_track(my)
            if tkey and tkey != "RULER":
                self._handle_header_click(event, tkey)
            return

        tot_dur = max(0.3, self.nle.total_duration)
        _vw, tot_px = self._viewport_metrics()
        self._drag_ref_tot_dur = tot_dur
        self._drag_ref_tot_px = tot_px
        px = self._sec_to_x(self.playhead_sec, tot_dur, tot_px)

        # 2. Ruler or Playhead Cap -> Scrub Playhead (O(1) update)
        if my <= self.RULER_H or (my <= self.RULER_H + 6 and abs(mx - px) <= 9):
            self._drag_action = "scrub"
            sec = self._x_to_sec(mx)
            self.playhead_sec = sec
            if not self._update_playhead_fast():
                self.redraw()
            self.on_scrub(sec, False)
            return

        # 3. Transition Placement Tool Mode
        if self.tool_mode == "transition_place":
            cut_hit = self._hit_test_cut_seam(mx, my, tol=26.0)
            if cut_hit is not None:
                cut_idx, cut_x, has_cut_trans, t_key, t_dur = cut_hit
                app = self._get_app()
                cur_k = "smoothleft"
                cur_dur = 0.5
                if app and hasattr(app, "_studio_trans_map") and hasattr(app, "trans_preset_var"):
                    cur_disp = app.trans_preset_var.get()
                    cur_k = app._studio_trans_map.get(cur_disp, "smoothleft")
                    try:
                        cur_dur = float(app.trans_dur_var.get())
                    except Exception:
                        cur_dur = 0.5
                self.assign_transition_to_cut(cut_idx, cur_k, cur_dur)
                info = get_transition_info(cur_k)
                lbl = info.get("label_ar") if self._is_ar() else info.get("label_en")
                self.show_hud_toast(f"✅ تم وضع انتقال ({lbl}) على القطع #{cut_idx+1}")
            else:
                ar = self._is_ar()
                self.show_hud_toast("⚠️ لم يتم العثور على قطع هنا! (قسّم الفيديو بـ Ctrl+B أولاً)" if ar else "⚠️ No cut seam found here! (Split with Ctrl+B first)")
            return

        # 4. Blade / Razor Mode -> Immediate Frame-Accurate Split on Any Track!
        if self.tool_mode == "blade":
            sec = self._x_to_sec(mx)
            hit_ref, _ = self._hit_test(mx, my)
            if hit_ref and hit_ref[0] in ("V2", "V3", "V4"):
                new_i = self.nle.split_overlay_at(hit_ref[0], hit_ref[1], sec)
                if new_i is not None:
                    self.selected_ref = (hit_ref[0], new_i)
                    self.on_select(self.selected_ref)
                    self.on_modified()
            else:
                new_c = self.nle.split_clip_at(sec)
                if new_c is not None:
                    self.selected_ref = ("clip", new_c)
                    self.on_select(self.selected_ref)
                    self.on_modified()
            self.playhead_sec = sec
            self.on_scrub(sec, True)
            self.redraw()
            return

        # 5. Direct click on cut seam or transition badge
        cut_hit = self._hit_test_cut_seam(mx, my, tol=14.0)
        if cut_hit is not None:
            cut_idx, cut_x, has_cut_trans, t_key, t_dur = cut_hit
            self._show_cut_transition_menu(event, cut_idx, has_cut_trans, t_key, t_dur)
            return

        # 6. Select Mode -> Hit test clips & overlays
        hit_ref, part = self._hit_test(mx, my)
        if hit_ref is not None:
            self.selected_ref = hit_ref
            self.on_select(hit_ref)
            self._drag_target = hit_ref
            self._drag_start_x = mx
            kind, idx = hit_ref

            if kind in ("V2", "V3", "V4"):
                it = self.nle.get_track_list(kind)[idx]
                s0 = 0.0 if it.get("full_duration") else float(it.get("start_sec", 0.0))
                e0 = tot_dur if it.get("full_duration") else float(it.get("end_sec", tot_dur))
                self._drag_orig_s = s0
                self._drag_orig_e = e0
                if part == "left":
                    self._drag_action = "trim_ov_left"
                elif part == "right":
                    self._drag_action = "trim_ov_right"
                else:
                    self._drag_action = "move_ov"
            elif kind == "clip":
                cl = self.nle.clips[idx]
                self._drag_orig_s = float(cl["src_start"])
                self._drag_orig_e = float(cl["src_end"])
                self._drag_orig_tl_s = float(cl["tl_start"])
                if part == "left":
                    self._drag_action = "trim_clip_left"
                elif part == "right":
                    self._drag_action = "trim_clip_right"
                else:
                    self._drag_action = "move_or_click_clip"
            self.redraw()
        else:
            # Clicked empty lane or gap -> move playhead & select video context
            self.selected_ref = None
            self.on_select(None)
            self._drag_action = "scrub"
            sec = self._x_to_sec(mx)
            self.playhead_sec = sec
            self.redraw()
            self.on_scrub(sec, False)

    def _on_drag(self, event):
        if not self._drag_action:
            return
        mx = event.x
        dx_px = mx - self._drag_start_x
        if abs(dx_px) > 3:
            self._drag_moved = True

        if self._drag_action == "scrub":
            sec = self._x_to_sec(max(self.HEADER_W, mx))
            self.playhead_sec = sec
            if not self._update_playhead_fast():
                self.redraw()
            self.on_scrub(sec, False)
            return

        if not self._drag_target:
            return
        kind, idx = self._drag_target
        dt_sec = (dx_px / max(1.0, self._drag_ref_tot_px)) * self._drag_ref_tot_dur

        if kind in ("V2", "V3", "V4"):
            t_list = self.nle.get_track_list(kind)
            if not (0 <= idx < len(t_list)):
                return
            it = t_list[idx]
            if it.get("full_duration", False) and self._drag_action == "move_ov" and abs(dx_px) < 6:
                return
            if not self._undo_pushed_for_drag:
                self.nle.push_undo()
                self._undo_pushed_for_drag = True
            it["full_duration"] = False

            if self._drag_action == "move_ov":
                span = max(0.2, self._drag_orig_e - self._drag_orig_s)
                raw_s = max(0.0, self._drag_orig_s + dt_sec)
                snapped_s, guide = self._snap_time(raw_s, self._drag_target)
                if guide is None:
                    snapped_e, guide_e = self._snap_time(raw_s + span, self._drag_target)
                    if guide_e is not None:
                        snapped_s = max(0.0, snapped_e - span)
                        guide = guide_e
                self._snap_guide_sec = guide
                it["start_sec"] = round(snapped_s, 2)
                it["end_sec"] = round(snapped_s + span, 2)

            elif self._drag_action == "trim_ov_left":
                raw_s = max(0.0, min(self._drag_orig_e - 0.2, self._drag_orig_s + dt_sec))
                snapped_s, guide = self._snap_time(raw_s, self._drag_target)
                snapped_s = min(self._drag_orig_e - 0.2, snapped_s)
                self._snap_guide_sec = guide
                it["start_sec"] = round(snapped_s, 2)
                it["end_sec"] = round(self._drag_orig_e, 2)

            elif self._drag_action == "trim_ov_right":
                raw_e = max(self._drag_orig_s + 0.2, self._drag_orig_e + dt_sec)
                snapped_e, guide = self._snap_time(raw_e, self._drag_target)
                snapped_e = max(self._drag_orig_s + 0.2, snapped_e)
                self._snap_guide_sec = guide
                it["start_sec"] = round(self._drag_orig_s, 2)
                it["end_sec"] = round(snapped_e, 2)

            self.redraw()

        elif kind == "clip" and 0 <= idx < len(self.nle.clips):
            cl = self.nle.clips[idx]
            spd = max(0.25, float(cl.get("speed", 1.0)))
            src_max = max(1.0, float(self.nle.source_duration or self._drag_ref_tot_dur))

            if self._drag_action == "trim_clip_left":
                if not self._undo_pushed_for_drag:
                    self.nle.push_undo()
                    self._undo_pushed_for_drag = True
                new_s = max(0.0, min(self._drag_orig_e - 0.12, self._drag_orig_s + dt_sec * spd))
                delta_tl = (new_s - self._drag_orig_s) / spd
                cl["src_start"] = round(new_s, 3)
                if not self.nle.ripple_mode:
                    cl["tl_start"] = round(max(0.0, self._drag_orig_tl_s + delta_tl), 3)
                self.nle.recompute_timeline(pack_gaps=False)
                self.redraw()

            elif self._drag_action == "trim_clip_right":
                if not self._undo_pushed_for_drag:
                    self.nle.push_undo()
                    self._undo_pushed_for_drag = True
                new_e = max(self._drag_orig_s + 0.12, min(src_max, self._drag_orig_e + dt_sec * spd))
                cl["src_end"] = round(new_e, 3)
                self.nle.recompute_timeline(pack_gaps=False)
                self.redraw()

            elif self._drag_action == "move_or_click_clip" and abs(dx_px) > 4:
                if not self._undo_pushed_for_drag:
                    self.nle.push_undo()
                    self._undo_pushed_for_drag = True
                raw_tl_s = max(0.0, self._drag_orig_tl_s + dt_sec)
                snapped_tl_s, guide = self._snap_time(raw_tl_s, ignore_ref=("clip", idx))
                self._snap_guide_sec = guide
                new_idx = self.nle.move_clip_to_time(idx, snapped_tl_s, push_undo=False)
                self._drag_target = ("clip", new_idx)
                self.selected_ref = ("clip", new_idx)
                self.redraw()

    def _on_release(self, event):
        act = self._drag_action
        self._drag_action = None
        self._snap_guide_sec = None

        if act == "scrub":
            sec = self._x_to_sec(max(self.HEADER_W, event.x))
            self.playhead_sec = sec
            self.redraw()
            self.on_scrub(sec, True)
        elif act == "move_or_click_clip" and not self._drag_moved:
            sec = self._x_to_sec(max(self.HEADER_W, event.x))
            self.playhead_sec = sec
            self.redraw()
            self.on_scrub(sec, True)
        elif act:
            self.on_modified()
            if self.selected_ref:
                self.on_select(self.selected_ref)
            self.redraw()

    def _on_hover(self, event):
        mx, my = event.x, event.y
        if mx < self.HEADER_W:
            self.canvas.configure(cursor="hand2")
            if self._hover_blade_sec is not None:
                self._hover_blade_sec = None
                if not self._update_blade_preview_fast():
                    self.redraw()
            return

        if my <= self.RULER_H:
            self.canvas.configure(cursor="hand2")
            return

        if self.tool_mode == "transition_place":
            self.canvas.configure(cursor="hand2")
            cut_idx = self._find_nearest_cut_seam(mx, my, tolerance_px=28.0)
            self._clear_trans_guides()
            if cut_idx is not None:
                c = self.canvas
                v1_y0, _ = self._track_y_bounds("V1")
                _, a1_y1 = self._track_y_bounds("A1")
                cut_x = None
                for idx, kx, *_ in self._cut_hit_boxes:
                    if idx == cut_idx:
                        cut_x = kx
                        break
                if cut_x is not None:
                    lid = c.create_line(cut_x, self.RULER_H, cut_x, a1_y1, fill="#00e5ff", width=2)
                    lbl_txt = f"🪄 انقر لوضع الانتقال على القطع #{cut_idx+1}" if self._is_ar() else f"🪄 Click to Place on Cut #{cut_idx+1}"
                    bid = c.create_rectangle(cut_x - 72, v1_y0 + 6, cut_x + 72, v1_y0 + 26, fill="#0d2d1f", outline="#00e5ff", width=2)
                    tid = c.create_text(cut_x, v1_y0 + 16, text=lbl_txt, fill="#b7f5cb", font=("Segoe UI", 8, "bold"))
                    self._trans_guide_ids.extend([lid, bid, tid])
            return

        if self.tool_mode == "blade":
            self.canvas.configure(cursor="crosshair")
            self._hover_blade_sec = self._x_to_sec(mx)
            if not self._update_blade_preview_fast():
                self.redraw()
            return

        cut_hit = self._hit_test_cut_seam(mx, my, tol=14.0)
        if cut_hit is not None:
            self.canvas.configure(cursor="hand2")
            return

        hit_ref, part = self._hit_test(mx, my)
        if hit_ref:
            if part in ("left", "right"):
                self.canvas.configure(cursor="sb_h_double_arrow")
            else:
                self.canvas.configure(cursor="fleur")
        else:
            self.canvas.configure(cursor="arrow")

    def _on_leave(self, _e):
        self._clear_trans_guides()
        if self._hover_blade_sec is not None:
            self._hover_blade_sec = None
            if not self._update_blade_preview_fast():
                self.redraw()

    def _close_single_gap(self, gs: float, ge: float):
        gap_dur = ge - gs
        if gap_dur <= 0.02 or not self.nle.clips:
            return
        self.nle.push_undo()
        for c in self.nle.clips:
            if float(c.get("tl_start", 0.0)) >= ge - 0.03:
                c["tl_start"] = round(max(0.0, float(c["tl_start"]) - gap_dur), 3)
        self.nle.recompute_timeline(pack_gaps=False)
        self.on_modified()
        self.redraw()

    def _on_right_click(self, event):
        mx, my = event.x, event.y
        if mx < self.HEADER_W:
            return
        cut_hit = self._hit_test_cut_seam(mx, my, tol=16.0)
        if cut_hit is not None:
            cut_idx, cut_x, has_cut_trans, t_key, t_dur = cut_hit
            self._show_cut_transition_menu(event, cut_idx, has_cut_trans, t_key, t_dur)
            return
        click_sec = self._x_to_sec(mx)
        hit_ref, _ = self._hit_test(mx, my)
        if hit_ref:
            self.selected_ref = hit_ref
            self.on_select(hit_ref)
            self.redraw()

        ar = self._is_ar()
        menu = tk.Menu(self, tearoff=0)

        # Check if right-clicked inside a Timeline Gap
        clicked_gap = None
        for gs, ge, gx0, gx1 in self._gap_hit_boxes:
            if gx0 <= mx <= gx1:
                clicked_gap = (gs, ge)
                break
        if clicked_gap is not None:
            gs, ge = clicked_gap
            menu.add_command(
                label="🧲 " + (f"إغلاق هذه الفجوة ({ge - gs:.1f}s)" if ar else f"Close This Gap ({ge - gs:.1f}s)"),
                command=lambda: self._close_single_gap(gs, ge),
            )
            menu.add_command(
                label="🧲 " + ("ضم جميع الفجوات في الشريط" if ar else "Close All Timeline Gaps"),
                command=self.close_all_gaps_action,
            )
            menu.add_separator()

        menu.add_command(
            label="✂️ " + ("قص وتقسيم العنصر/المقطع هنا" if ar else "Split Clip / Overlay Here"),
            command=lambda: self._split_at_exact(click_sec, hit_ref),
        )
        menu.add_command(
            label="🎯 " + ("زوم مكبر دقيق حول هذه النقطة" if ar else "Deep Precision Zoom Here"),
            command=lambda: self._zoom_deep_at(click_sec),
        )
        if self.selected_ref:
            menu.add_command(
                label="📋 " + ("تكرار المحدد" if ar else "Duplicate Selected"),
                command=self.duplicate_selected,
            )
            if self.selected_ref[0] == "clip":
                c_idx = self.selected_ref[1]
                if 0 <= c_idx < len(self.nle.clips):
                    is_m = self.nle.clips[c_idx].get("muted", False)
                    m_lbl = ("🔊 تشغيل صوت هذا المقطع" if is_m else "🔇 كتم صوت هذا المقطع") if ar else ("🔊 Unmute Clip" if is_m else "🔇 Mute Clip")
                    menu.add_command(label=m_lbl, command=lambda: self._toggle_clip_mute(c_idx))
                    menu.add_command(
                        label="✨ " + ("تعديل حركة الانتقال (Transitions)..." if ar else "Edit Video Transition..."),
                        command=lambda ci=c_idx: self._open_transition_editor(ci),
                    )
                    if self.on_export_clip:
                        menu.add_command(
                            label="🚀 " + ("تصدير هذا المقطع المحدد فقط" if ar else "Export This Selected Clip Only"),
                            command=lambda ci=c_idx: self.on_export_clip(ci),
                        )
            menu.add_command(
                label="🗑️ " + ("حذف المحدد" if ar else "Delete Selected"),
                command=self.delete_selected,
            )
        if self.on_split_silences:
            menu.add_separator()
            menu.add_command(
                label="⚡ " + ("فصل وحذف السكتات تلقائياً في الشريط" if ar else "Auto-Split & Remove Silences"),
                command=lambda: self.on_split_silences(True),
            )
            menu.add_command(
                label="🔇 " + ("تقسيم السكتات كمقاطع صامتة للمراجعة" if ar else "Split Silences as Muted Clips"),
                command=lambda: self.on_split_silences(False),
            )
        menu.add_separator()
        menu.add_command(
            label="📝 " + ("إضافة نص هنا (V3)" if ar else "Add Text+ Here (V3)"),
            command=lambda: self.on_add_element("text", click_sec),
        )
        menu.add_command(
            label="⭐ " + ("إضافة أيقونة أو شارة هنا (V2)" if ar else "Add Pro Icon Here (V2)"),
            command=lambda: self.on_add_element("icon", click_sec),
        )
        menu.add_command(
            label="🖼️ " + ("إضافة صورة خارجية هنا (V2)" if ar else "Add Image Here (V2)"),
            command=lambda: self.on_add_element("image", click_sec),
        )
        menu.add_command(
            label="🛡️ " + ("إضافة لوجو هنا (V4)" if ar else "Add Logo Here (V4)"),
            command=lambda: self.on_add_element("logo", click_sec),
        )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _zoom_deep_at(self, sec: float):
        self.playhead_sec = sec
        self.on_scrub(sec, True)
        self.zoom_to_cut()

    def _split_at_exact(self, sec: float, hit_ref: Optional[Tuple[str, int]]):
        if hit_ref and hit_ref[0] in ("V2", "V3", "V4"):
            ni = self.nle.split_overlay_at(hit_ref[0], hit_ref[1], sec)
            if ni is not None:
                self.selected_ref = (hit_ref[0], ni)
                self.on_select(self.selected_ref)
                self.on_modified()
                self.redraw()
                return
        nc = self.nle.split_clip_at(sec)
        if nc is not None:
            self.selected_ref = ("clip", nc)
            self.on_select(self.selected_ref)
            self.on_modified()
            self.redraw()

    def _toggle_clip_mute(self, c_idx: int):
        if 0 <= c_idx < len(self.nle.clips):
            self.nle.push_undo()
            self.nle.clips[c_idx]["muted"] = not self.nle.clips[c_idx].get("muted", False)
            self.on_modified()
            self.redraw()

    def _open_transition_editor(self, clip_idx: int):
        app = getattr(self, "parent", None)
        if app and not hasattr(app, "open_video_transitions_dialog"):
            app = getattr(app, "parent", None)
        if app and hasattr(app, "open_video_transitions_dialog"):
            app.open_video_transitions_dialog(target_cut_index=clip_idx)
