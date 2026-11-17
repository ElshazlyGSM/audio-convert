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
from video_studio.tooltip import add_tooltip


class _CanvasTooltipHelper:
    """Floating tooltip for canvas items based on hover coordinates with debounce."""

    def __init__(self, canvas: tk.Canvas, is_ar_fn: Callable[[], bool]):
        self.canvas = canvas
        self.is_ar_fn = is_ar_fn
        self._tip_window: Optional[tk.Toplevel] = None
        self._after_id: Optional[str] = None
        self._current_text: str = ""
        self._last_x: int = 0
        self._last_y: int = 0

    def show(self, text_ar: str, text_en: str, root_x: int, root_y: int):
        txt = text_ar if self.is_ar_fn() else (text_en or text_ar)
        if not txt:
            self.hide()
            return
        if txt == self._current_text and self._tip_window and self._tip_window.winfo_exists():
            return
        self._cancel()
        self._current_text = txt
        self._last_x = root_x
        self._last_y = root_y
        self._after_id = self.canvas.after(350, self._render_tip)

    def _cancel(self):
        if self._after_id:
            try:
                self.canvas.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _render_tip(self):
        self._after_id = None
        if not self.canvas.winfo_exists() or not self._current_text:
            return
        if self._tip_window:
            try:
                self._tip_window.destroy()
            except Exception:
                pass
            self._tip_window = None

        self._tip_window = tw = tk.Toplevel(self.canvas)
        tw.wm_overrideredirect(True)
        try:
            tw.attributes("-topmost", True)
        except Exception:
            pass

        card = tk.Frame(tw, bg="#388bfd", bd=1, relief="solid")
        card.pack(fill="both", expand=True)

        inner = tk.Frame(card, bg="#161b22", padx=8, pady=4)
        inner.pack(fill="both", expand=True)

        lbl = tk.Label(
            inner,
            text=self._current_text,
            bg="#161b22",
            fg="#f0f6fc",
            font=("Segoe UI", 9),
            justify="center",
            wraplength=340,
        )
        lbl.pack()

        tw.update_idletasks()
        req_w = tw.winfo_reqwidth()
        req_h = tw.winfo_reqheight()
        sw = self.canvas.winfo_screenwidth()
        sh = self.canvas.winfo_screenheight()

        x = self._last_x + 12
        y = self._last_y + 18
        if x + req_w > sw - 12:
            x = max(10, sw - req_w - 12)
        if y + req_h > sh - 36:
            y = max(10, self._last_y - req_h - 10)

        tw.wm_geometry(f"+{int(x)}+{int(y)}")

    def hide(self):
        self._cancel()
        self._current_text = ""
        if self._tip_window:
            try:
                self._tip_window.destroy()
            except Exception:
                pass
            self._tip_window = None


class DaVinciTimelinePanel(ttk.Frame):
    HEADER_W = 144
    RULER_H = 24
    DEFAULT_TRACK_SPECS = [
        ("V4", 30, "#1b4d6e", "#266b99", "🛡️ اللوجو", "🛡️ Logo", "+", "logo"),
        ("V3", 30, "#8f7549", "#ad8f5b", "📝 النصوص", "📝 Text+", "+", "text"),
        ("V2", 30, "#55359e", "#6d46c7", "⭐ أيقونات/صور", "⭐ Icons/Img", "+", "media"),
        ("V1", 40, "#27476e", "#356094", "🎬 الفيديو V1", "🎬 Video V1", "✂", "video"),
        ("A1", 42, "#1b5933", "#257845", "🔊 الصوت A1", "🔊 Audio A1", "⚡", "audio"),
        ("A2", 36, "#134e5e", "#1b6d85", "🎵 مسار صوت A2", "🎵 Audio Track A2", "+", "audio_item"),
    ]
    TRACK_SPECS = DEFAULT_TRACK_SPECS  # Backward-compatibility alias

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
        on_export_all_clips: Optional[Callable[[], None]] = None,
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
        self.on_export_all_clips = on_export_all_clips  # () -> None

        self.playhead_sec: float = 0.0
        self.tool_mode: str = "select"            # "select" or "blade"
        self.linked_selection: bool = True       # When True: V1 video and A1 audio are linked together; when False: independent
        self.zoom_factor: float = 1.0             # 1.0 = fit full timeline, up to _max_zoom() (~300 px/sec)
        self.scroll_px: float = 0.0

        # Dynamic Tracks & Height Scaling
        self.track_specs: List[List[Any]] = [list(t) for t in self.DEFAULT_TRACK_SPECS]
        self.track_height_scale: float = 1.0     # 0.55 = compact, 1.0 = normal, up to 1.8
        self.is_compact_tracks: bool = False

        # Multi-Item Selection & Geometry
        self.selected_items: set = set()          # set of (kind, idx) e.g. ("clip", 0), ("V3", 1)
        self.selected_ref: Optional[Tuple[str, int]] = None
        self.selected_clip_indices: set = set()
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

        # Drag / hover / rubber-band marquee state
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
        self._marquee_start_x: int = 0
        self._marquee_start_y: int = 0
        self._drag_multi_origins: Dict[Tuple[str, int], Any] = {}
        self._hover_blade_sec: Optional[float] = None
        self._snap_guide_sec: Optional[float] = None
        self._item_hit_boxes: List[Tuple[str, int, float, float, float, float]] = []
        self._gap_hit_boxes: List[Tuple[float, float, float, float]] = []
        self._cut_hit_boxes: List[Tuple[int, float, float, float, float, bool, str, float]] = []
        self._trans_guide_ids: List[int] = []
        self._clipboard_items: List[Dict[str, Any]] = []
        self._clipboard_base_start: float = 0.0

        self._build_ui()

    def _is_ar(self) -> bool:
        try:
            return bool(self.is_ar_fn())
        except Exception:
            return True

    def _get_track_height(self, tspec) -> int:
        base_h = tspec[1]
        scale = getattr(self, "track_height_scale", 1.0)
        return max(18, int(round(base_h * scale)))

    @property
    def total_canvas_height(self) -> int:
        return self.RULER_H + sum(self._get_track_height(t) for t in self.track_specs) + 2

    def _track_y_bounds(self, track_key: str) -> Tuple[int, int]:
        y = self.RULER_H
        for tspec in self.track_specs:
            th = self._get_track_height(tspec)
            if tspec[0] == track_key:
                return y, y + th
            y += th
        return y, y + 24

    def _y_to_track(self, y: float) -> Optional[str]:
        if y < self.RULER_H:
            return "RULER"
        cur_y = self.RULER_H
        for tspec in self.track_specs:
            th = self._get_track_height(tspec)
            if cur_y <= y < cur_y + th:
                return tspec[0]
            cur_y += th
        return None

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
        self.btn_tool_blade.pack(side="left", padx=(0, 2))

        self.btn_link_toggle = tk.Button(
            bar,
            command=self.toggle_linked_selection,
            relief="flat",
            bd=0,
            padx=7,
            pady=2,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        )
        self.btn_link_toggle.pack(side="left", padx=(0, 4))
        self._update_link_button()

        tk.Frame(bar, bg="#30363d", width=1, height=18).pack(side="left", padx=3)

        self.btn_split_now = self._mk_bar_btn(bar, self.split_at_playhead, fg="#ffd700")
        self.btn_delete_sel = self._mk_bar_btn(bar, self.delete_selected, fg="#ff7b72")
        self.btn_dup_sel = self._mk_bar_btn(bar, self.duplicate_selected)
        self.btn_copy = self._mk_bar_btn(bar, self.copy_selected, bg="#1a2d3b", fg="#79c0ff")
        self.btn_paste = self._mk_bar_btn(bar, self.paste_at_playhead, bg="#1b382b", fg="#7ee787")
        self.btn_close_gaps = self._mk_bar_btn(bar, self.close_all_gaps_action, bg="#1d2f42", fg="#79c0ff")
        self.btn_split_silence = self._mk_bar_btn(bar, self._show_silence_split_menu, bg="#1d3829", fg="#56d364")
        self.btn_undo = self._mk_bar_btn(bar, self.do_undo)
        self.btn_redo = self._mk_bar_btn(bar, self.do_redo)
        self.btn_shortcuts = self._mk_bar_btn(bar, self.open_shortcuts_guide, bg="#212638", fg="#a5d6ff")

        tk.Frame(bar, bg="#30363d", width=1, height=18).pack(side="left", padx=3)

        # Dynamic Tracks & Vertical Scale
        self.btn_add_track = self._mk_bar_btn(bar, self._show_add_track_menu, bg="#1d3042", fg="#79c0ff")
        self.btn_compact_tracks = self._mk_bar_btn(bar, self.toggle_compact_tracks, bg="#232834", fg="#c9d1d9")
        self.btn_th_minus = self._mk_small_zoom_btn(bar, "↕️-", lambda: self.step_track_height(-0.15))
        self.btn_th_minus.pack(side="left", padx=1)
        self.btn_th_plus = self._mk_small_zoom_btn(bar, "↕️+", lambda: self.step_track_height(0.15))
        self.btn_th_plus.pack(side="left", padx=1)
        self.lbl_track_h = tk.Label(bar, text="↕️ 100%", bg="#161920", fg="#8b949e", font=("Consolas", 8))
        self.lbl_track_h.pack(side="left", padx=(1, 3))

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
        self.btn_add_aud = self._mk_bar_btn(bar, lambda: self.add_audio_file_dialog(self.playhead_sec), bg="#134e5e", fg="#7ee787")

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

        # Tooltips for all toolbar buttons
        add_tooltip(self.btn_tool_select, "أداة التحديد والتحريك (مفتاح A)", "Select Tool (Key A)")
        add_tooltip(self.btn_tool_blade, "أداة شفرة المقص لتقطيع المقاطع بالفأرة (مفتاح B)", "Blade Tool (Key B)")
        add_tooltip(self.btn_link_toggle, "ربط/فصل مسارات الفيديو والصوت (تحديد مدمج أو تحكم مستقل لكل مسار)", "Link/Unlink Video & Audio Selection")
        add_tooltip(self.btn_split_now, "قص وتقسيم عند موضع المؤشر الحالي (Ctrl+B أو S)", "Split at Playhead (Ctrl+B)")
        add_tooltip(self.btn_delete_sel, "حذف المقطع أو العنصر المحدد (Delete)", "Delete Selected (Delete)")
        add_tooltip(self.btn_dup_sel, "تكرار العنصر المحدد", "Duplicate Selected")
        add_tooltip(self.btn_copy, "نسخ العنصر المحدد (Ctrl+C)", "Copy Selected (Ctrl+C)")
        add_tooltip(self.btn_paste, "لصق عند موضع المؤشر (Ctrl+V)", "Paste at Playhead (Ctrl+V)")
        add_tooltip(self.btn_close_gaps, "ضم وإغلاق جميع الفراغات بين المقاطع", "Close All Timeline Gaps")
        add_tooltip(self.btn_split_silence, "كشف وتقسيم السكتات في الصوت تلقائياً", "Auto Silence Detection & Split")
        add_tooltip(self.btn_undo, "تراجع عن آخر خطوة (Ctrl+Z)", "Undo (Ctrl+Z)")
        add_tooltip(self.btn_redo, "إعادة الخطوة السابقة (Ctrl+Y)", "Redo (Ctrl+Y)")
        add_tooltip(self.btn_shortcuts, "دليل اختصارات الكيبورد والتحكم", "Keyboard Shortcuts Guide")
        add_tooltip(self.btn_add_track, "إضافة مسار إضافي جديد", "Add Timeline Track")
        add_tooltip(self.btn_compact_tracks, "تبديل وضع العرض المضغوط / الموسع للطبقات", "Toggle Compact / Expanded Tracks")
        add_tooltip(self.btn_th_minus, "تصغير ارتفاع المسارات عمودياً", "Compact Track Height Vertically")
        add_tooltip(self.btn_th_plus, "تكبير ارتفاع المسارات عمودياً", "Expand Track Height Vertically")
        add_tooltip(self.chk_ripple, "تفعيل/تعطيل الضم التلقائي للمقاطع عند الحذف (Ripple)", "Toggle Ripple Delete")
        add_tooltip(self.btn_add_txt, "إضافة نص جديد عند المؤشر", "Add Text at Playhead")
        add_tooltip(self.btn_add_ico, "إضافة أيقونة أو شارة عند المؤشر", "Add Icon at Playhead")
        add_tooltip(self.btn_add_img, "إضافة صورة خارجية عند المؤشر", "Add Image at Playhead")
        add_tooltip(self.btn_add_lgo, "إضافة أو تغيير اللوجو للتايم لاين", "Add Logo at Playhead")
        add_tooltip(self.btn_add_aud, "إضافة ملف صوت جديد إلى مسار A2", "Add Audio File to Track A2")
        add_tooltip(self.btn_zoom_fit, "ملاءمة كامل التايم لاين لعرضه بالكامل داخل الشاشة", "Fit Entire Timeline to View")
        add_tooltip(self.btn_zoom_cut, "تكبير زوم فائق على موضع المؤشر للتدقيق", "Fine Zoom to Playhead / Cut")

        self.btn_zoom_in = self._mk_small_zoom_btn(bar, "➕", lambda: self.step_zoom(1.45))
        self.btn_zoom_in.pack(side="right", padx=1)
        add_tooltip(self.btn_zoom_in, "تكبير الخط الزمني (Zoom In)", "Zoom In Timeline")

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
        add_tooltip(self.zoom_scale, "شريط تكبير وتصغير التايم لاين", "Timeline Zoom Slider")

        self.btn_zoom_out = self._mk_small_zoom_btn(bar, "➖", lambda: self.step_zoom(1.0 / 1.45))
        self.btn_zoom_out.pack(side="right", padx=1)
        add_tooltip(self.btn_zoom_out, "تصغير الخط الزمني (Zoom Out)", "Zoom Out Timeline")

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
        self._canvas_tip = _CanvasTooltipHelper(self.canvas, self._is_ar)

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
        self.canvas.bind("<MouseWheel>", self._on_plain_mousewheel)
        self.canvas.bind("<Alt-MouseWheel>", self._on_zoom_mousewheel)
        self.canvas.bind("<Control-MouseWheel>", self._on_zoom_mousewheel)
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

    def toggle_linked_selection(self):
        self.linked_selection = not getattr(self, "linked_selection", True)
        self._update_link_button()
        ar = self._is_ar()
        if self.linked_selection:
            self.show_hud_toast("🔗 تم تفعيل ربط مسارات الفيديو والصوت (التحكم مدمج)" if ar else "🔗 Linked Selection ON (Video & Audio linked)")
        else:
            self.show_hud_toast("⛓️ تم فصل ارتباط الفيديو عن الصوت (تحكم مستقل لكل مسار)" if ar else "⛓️ Linked Selection OFF (Independent Video & Audio control)")
        self.redraw()

    def _update_link_button(self):
        if not hasattr(self, "btn_link_toggle"):
            return
        ar = self._is_ar()
        is_linked = getattr(self, "linked_selection", True)
        if is_linked:
            self.btn_link_toggle.configure(
                text="🔗 " + ("مرتبط" if ar else "Linked"),
                bg="#1f3b2d",
                fg="#7ee787",
                activebackground="#294e3c",
                activeforeground="#ffffff",
            )
        else:
            self.btn_link_toggle.configure(
                text="⛓️ " + ("مفصول" if ar else "Unlinked"),
                bg="#482222",
                fg="#ff7b72",
                activebackground="#602d2d",
                activeforeground="#ffffff",
            )

    def apply_language(self):
        ar = self._is_ar()
        self.btn_tool_select.configure(text="🖱️ تحديد (A)" if ar else "🖱️ Select (A)")
        self.btn_tool_blade.configure(text="✂️ مقص (B)" if ar else "✂️ Blade (B)")
        self._update_link_button()
        self.btn_split_now.configure(text="✂️ قص (S)" if ar else "✂️ Split (S)")
        self.btn_delete_sel.configure(text="🗑️ حذف" if ar else "🗑️ Delete")
        self.btn_dup_sel.configure(text="📋 تكرار" if ar else "📋 Dup")
        if hasattr(self, "btn_copy"):
            self.btn_copy.configure(text="📄 نسخ" if ar else "📄 Copy")
        if hasattr(self, "btn_paste"):
            self.btn_paste.configure(text="📌 لصق" if ar else "📌 Paste")
        self.btn_close_gaps.configure(text="🧲 ضم الفجوات" if ar else "🧲 Close Gaps")
        self.btn_split_silence.configure(text="⚡ فصل السكتات" if ar else "⚡ Split Silences")
        self.btn_undo.configure(text="↩️" if ar else "↩️ Undo")
        self.btn_redo.configure(text="↪️" if ar else "↪️ Redo")
        if hasattr(self, "btn_shortcuts"):
            self.btn_shortcuts.configure(text="💡 الاختصارات" if ar else "💡 Shortcuts")
        if hasattr(self, "btn_add_track"):
            self.btn_add_track.configure(text="➕ إضافة طبقة" if ar else "➕ Add Layer")
        if hasattr(self, "btn_compact_tracks"):
            if self.is_compact_tracks:
                self.btn_compact_tracks.configure(text="📐 تكبير الطبقات" if ar else "📐 Expand Tracks", bg="#3b2d18", fg="#ffd700")
            else:
                self.btn_compact_tracks.configure(text="📐 تصغير الطبقات" if ar else "📐 Compact Tracks", bg="#232834", fg="#c9d1d9")
        self.chk_ripple.configure(text="ضم تلقائي" if ar else "Ripple")
        self.btn_add_txt.configure(text="+ نص" if ar else "+ Text")
        self.btn_add_ico.configure(text="+ أيقونة" if ar else "+ Icon")
        self.btn_add_img.configure(text="+ صورة" if ar else "+ Image")
        self.btn_add_lgo.configure(text="+ لوجو" if ar else "+ Logo")
        if hasattr(self, "btn_add_aud"):
            self.btn_add_aud.configure(text="+ 🎵 صوت" if ar else "+ 🎵 Audio")
        self.btn_zoom_cut.configure(text="🎯 زوم دقيق" if ar else "🎯 Fine Zoom")
        self.btn_zoom_fit.configure(text="احتواء" if ar else "Fit")
        self.redraw()

    # ------------------------------------------------------------------
    # Dynamic Tracks Management & Vertical Height Scaling
    # ------------------------------------------------------------------
    def add_audio_file_dialog(self, at_tl_sec: Optional[float] = None):
        """Open a file dialog to select an audio file and add it to timeline track A2."""
        from tkinter import filedialog
        ar = self._is_ar()
        filetypes = [
            ("ملفات الصوت / Audio Files" if ar else "Audio Files", "*.mp3 *.wav *.aac *.m4a *.flac *.ogg *.wma *.opus"),
            ("MP3 Audio", "*.mp3"),
            ("WAV Audio", "*.wav"),
            ("M4A / AAC Audio", "*.m4a *.aac"),
            ("All files", "*.*"),
        ]
        chosen = filedialog.askopenfilename(
            title="اختيار ملف صوتي أو موسيقى خلفية" if ar else "Select Audio File / Background Music",
            filetypes=filetypes,
        )
        if not chosen:
            return
        insert_sec = self.playhead_sec if at_tl_sec is None else max(0.0, float(at_tl_sec))
        new_item = self.nle.add_audio_item(chosen, start_sec=insert_sec)
        self.on_modified()
        self.redraw()
        # Auto-select the newly added audio item
        idx = len(self.nle.audio_items) - 1
        self.selected_items.clear()
        self.selected_items.add(("A2", idx))
        self._sync_selection_refs()
        self.redraw()
        nm = Path(chosen).name
        self.show_hud_toast(f"🎵 تم إضافة الصوت '{nm}' بنجاح" if ar else f"🎵 Audio '{nm}' added successfully")

    def _show_add_track_menu(self):
        ar = self._is_ar()
        m = tk.Menu(self, tearoff=0)
        m.add_command(
            label="🎵 " + ("إضافة ملف صوتي / موسيقى (مسار A2)" if ar else "Add Audio File / Music (Track A2)"),
            command=lambda: self.add_audio_file_dialog(self.playhead_sec),
        )
        m.add_separator()
        m.add_command(
            label="📝 " + ("طبقة نصوص إضافية (Text Track)" if ar else "Add Text Track"),
            command=lambda: self.add_extra_track("text"),
        )
        m.add_command(
            label="⭐ " + ("طبقة وسائط / أيقونات (Media Track)" if ar else "Add Media/Icon Track"),
            command=lambda: self.add_extra_track("media"),
        )
        m.add_command(
            label="🛡️ " + ("طبقة لوجو إضافية (Logo Track)" if ar else "Add Logo Track"),
            command=lambda: self.add_extra_track("logo"),
        )
        try:
            x = self.btn_add_track.winfo_rootx()
            y = self.btn_add_track.winfo_rooty() + self.btn_add_track.winfo_height()
            m.tk_popup(x, y)
        finally:
            m.grab_release()

    def add_extra_track(self, track_type: str = "text"):
        ar = self._is_ar()
        existing = [t for t in self.track_specs if len(t) > 7 and t[7] == track_type]
        num = len(existing) + 1
        pfx_map = {"text": "TXT", "media": "MED", "logo": "LOG", "video": "VID"}
        pfx = pfx_map.get(track_type, track_type[:3].upper())
        tkey = f"{pfx}_{len(self.track_specs) + 1}"
        if track_type == "text":
            spec = [tkey, 30, "#8f7549", "#ad8f5b", f"📝 نصوص {num}", f"📝 Text {num}", "+", "text"]
        elif track_type == "media":
            spec = [tkey, 30, "#55359e", "#6d46c7", f"⭐ وسائط {num}", f"⭐ Media {num}", "+", "media"]
        elif track_type == "logo":
            spec = [tkey, 30, "#1b4d6e", "#266b99", f"🛡️ لوجو {num}", f"🛡️ Logo {num}", "+", "logo"]
        else:
            spec = [tkey, 30, "#27476e", "#356094", f"🎬 طبقة {num}", f"🎬 Track {num}", "+", track_type]

        # Insert above V1
        v1_idx = 0
        for i, t in enumerate(self.track_specs):
            if t[0] == "V1":
                v1_idx = i
                break
        self.track_specs.insert(v1_idx, spec)
        self.nle.add_track(tkey, track_type)
        self.nle.track_enabled[tkey] = True
        self.canvas.configure(height=self.total_canvas_height)
        self.on_modified()
        self.redraw()
        self.show_hud_toast("✅ تمت إضافة طبقة جديدة بنجاح" if ar else "✅ New layer added successfully")

    def delete_track(self, track_key: str):
        ar = self._is_ar()
        if track_key in ("V1", "A1", "A2"):
            self.show_hud_toast("⚠️ لا يمكن حذف مسارات المشروع الأساسية" if ar else "⚠️ Cannot delete primary project tracks")
            return
        idx = next((i for i, t in enumerate(self.track_specs) if t[0] == track_key), None)
        if idx is None:
            return
        self.nle.delete_track(track_key)
        self.track_specs.pop(idx)
        self.selected_items = {it for it in self.selected_items if it[0] != track_key}
        self._sync_selection_refs()
        self.canvas.configure(height=self.total_canvas_height)
        self.on_modified()
        self.redraw()
        self.show_hud_toast("🗑️ تم حذف الطبقة بنجاح" if ar else "🗑️ Layer deleted successfully")

    def move_track_up(self, track_key: str):
        idx = next((i for i, t in enumerate(self.track_specs) if t[0] == track_key), None)
        if idx is None or idx <= 0:
            return
        target_idx = idx - 1
        self.track_specs[idx], self.track_specs[target_idx] = self.track_specs[target_idx], self.track_specs[idx]
        self.redraw()
        ar = self._is_ar()
        tspec = self.track_specs[target_idx]
        lbl = tspec[4] if ar else tspec[5]
        self.show_hud_toast(f"⬆️ تم تحريك مسار ({lbl}) للأعلى" if ar else f"⬆️ Moved track ({lbl}) Up")

    def move_track_down(self, track_key: str):
        idx = next((i for i, t in enumerate(self.track_specs) if t[0] == track_key), None)
        if idx is None or idx >= len(self.track_specs) - 1:
            return
        target_idx = idx + 1
        self.track_specs[idx], self.track_specs[target_idx] = self.track_specs[target_idx], self.track_specs[idx]
        self.redraw()
        ar = self._is_ar()
        tspec = self.track_specs[target_idx]
        lbl = tspec[4] if ar else tspec[5]
        self.show_hud_toast(f"⬇️ تم تحريك مسار ({lbl}) للأسفل" if ar else f"⬇️ Moved track ({lbl}) Down")

    def reset_default_track_order(self):
        default_keys = [t[0] for t in self.DEFAULT_TRACK_SPECS]
        existing_by_key = {t[0]: t for t in self.track_specs}
        new_specs = []
        for t in self.DEFAULT_TRACK_SPECS:
            if t[0] in existing_by_key:
                new_specs.append(existing_by_key[t[0]])
            else:
                new_specs.append(list(t))
        for t in self.track_specs:
            if t[0] not in default_keys:
                new_specs.append(t)
        self.track_specs = new_specs
        self.redraw()
        ar = self._is_ar()
        self.show_hud_toast("🔄 تم إعادة الترتيب الافتراضي للمسارات" if ar else "🔄 Reset to default track order")

    def _draw_reorder_indicator(self, cur_y: float, dest_tkey: Optional[str]):
        self.canvas.delete("reorder_guide")
        if not dest_tkey or dest_tkey == "RULER":
            return
        y0, y1 = self._track_y_bounds(dest_tkey)
        line_y = y0 if cur_y < (y0 + y1) / 2 else y1
        cw = max(self.canvas.winfo_width(), 800)
        self.canvas.create_line(0, line_y, cw, line_y, fill="#00e5ff", width=3, tags="reorder_guide")

    def _reorder_track_to(self, src_key: str, dest_key: str, drop_y: float = 0.0):
        if src_key == dest_key or not src_key or not dest_key:
            return
        src_idx = next((i for i, t in enumerate(self.track_specs) if t[0] == src_key), None)
        dest_idx = next((i for i, t in enumerate(self.track_specs) if t[0] == dest_key), None)
        if src_idx is None or dest_idx is None:
            return
        y0, y1 = self._track_y_bounds(dest_key)
        if drop_y > (y0 + y1) / 2 and dest_idx < src_idx:
            dest_idx += 1
        spec = self.track_specs.pop(src_idx)
        self.track_specs.insert(dest_idx, spec)
        self.redraw()
        ar = self._is_ar()
        lbl = spec[4] if ar else spec[5]
        self.show_hud_toast(f"↕️ تم نقل مسار ({lbl}) بنجاح" if ar else f"↕️ Reordered track ({lbl}) successfully")

    def toggle_compact_tracks(self):
        if self.track_height_scale < 0.90:
            self.track_height_scale = 1.0
            self.is_compact_tracks = False
        else:
            self.track_height_scale = 0.58
            self.is_compact_tracks = True
        self._on_track_height_changed()

    def step_track_height(self, delta: float):
        new_scale = max(0.45, min(1.80, self.track_height_scale + delta))
        self.track_height_scale = round(new_scale, 2)
        self.is_compact_tracks = (self.track_height_scale <= 0.65)
        self._on_track_height_changed()

    def _on_track_height_changed(self):
        self.canvas.configure(height=self.total_canvas_height)
        pct = int(round(self.track_height_scale * 100))
        if hasattr(self, "lbl_track_h"):
            self.lbl_track_h.configure(text=f"↕️ {pct}%")
        if hasattr(self, "btn_compact_tracks"):
            ar = self._is_ar()
            if self.is_compact_tracks:
                self.btn_compact_tracks.configure(text="📐 " + ("تكبير الطبقات" if ar else "Expand Tracks"), bg="#3b2d18", fg="#ffd700")
            else:
                self.btn_compact_tracks.configure(text="📐 " + ("تصغير الطبقات" if ar else "Compact Tracks"), bg="#232834", fg="#c9d1d9")
        self.redraw()

    def _sync_selection_refs(self):
        self.selected_clip_indices = {idx for (kind, idx) in self.selected_items if kind in ("clip", "V1_clip", "A1_clip")}
        if self.selected_items:
            if self.selected_ref not in self.selected_items:
                self.selected_ref = next(iter(self.selected_items))
        else:
            self.selected_ref = None
        self.on_select(self.selected_ref)

    def select_all_items(self):
        self.selected_items.clear()
        for i in range(len(self.nle.clips)):
            self.selected_items.add(("clip", i))
        for tspec in self.track_specs:
            tkey = tspec[0]
            ttype = tspec[7] if len(tspec) > 7 else "text"
            if ttype in ("video", "audio") or tkey in ("V1", "A1"):
                continue
            items = self.nle.get_track_list(tkey)
            for i, it in enumerate(items):
                if it.get("enabled", True):
                    self.selected_items.add((tkey, i))
        self._sync_selection_refs()
        self.redraw()
        ar = self._is_ar()
        self.show_hud_toast(f"✅ تم تحديد الكل ({len(self.selected_items)} عنصر)" if ar else f"✅ All items selected ({len(self.selected_items)} items)")

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
        # Alt on Windows Tkinter: 0x20000 (131072) or 0x0080
        # NOTE: Do NOT use 0x0008 (NumLock) or 0x0020 (ScrollLock)!
        is_ctrl = bool(state & 0x0004)
        is_alt = bool((state & 0x20000) or (state & 0x0080))
        return is_ctrl or is_alt

    def _on_zoom_mousewheel(self, event):
        anchor_s = self._x_to_sec(max(self.HEADER_W, event.x))
        factor = 1.28 if event.delta > 0 else (1.0 / 1.28)
        new_z = max(1.0, min(self._max_zoom(), self.zoom_factor * factor))
        self._apply_zoom_around(new_z, anchor_s)
        self._sync_zoom_ui_indicator()

    def _on_plain_mousewheel(self, event):
        if self._is_zoom_wheel(event):
            self._on_zoom_mousewheel(event)
        else:
            vw, tot_px = self._viewport_metrics()
            max_sc = max(0.0, tot_px - vw)
            delta_px = -65.0 if event.delta > 0 else 65.0
            self.scroll_px = max(0.0, min(max_sc, self.scroll_px + delta_px))
            self.redraw()

    def _on_mousewheel(self, event):
        self._on_plain_mousewheel(event)

    def _on_canvas_key(self, event):
        k = (event.keysym or "").lower()
        kc = getattr(event, "keycode", 0)
        ctrl = bool(event.state & 0x0004)
        is_b = (kc == 66) or (k in ("b", "arabic_laa", "arabic_lam_alef", "\u0644\u0627", "\u0644"))
        is_s = (kc == 83) or (k in ("s", "arabic_seen", "seen", "\u0633"))
        is_a = (kc == 65) or (k in ("a", "arabic_sheen", "sheen", "\u0634"))
        is_c = (kc == 67) or (k in ("c", "arabic_hamza_on_ya", "hamza_on_ya", "\u0626"))
        is_v = (kc == 86) or (k in ("v", "arabic_ra", "ra", "\u0631"))

        if ctrl and is_c:
            self.copy_selected()
            return "break"
        if ctrl and is_v:
            self.paste_at_playhead()
            return "break"
        if ctrl and is_a:
            self.select_all_items()
            return "break"
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
        ar = self._is_ar()
        if self.selected_ref and (self.selected_ref[0] in ("V2", "V3", "V4") or self.selected_ref[0].startswith(("TXT", "MED", "LOG"))):
            tk_key, idx = self.selected_ref
            if bool(hasattr(self.nle, "is_track_locked") and self.nle.is_track_locked(tk_key)):
                self.show_hud_toast("🔒 المسار مقفول ضد التقسيم (إلغاء القفل أولاً)" if ar else "🔒 Track is locked against splitting")
                return
            new_idx = self.nle.split_overlay_at(tk_key, idx, self.playhead_sec)
            if new_idx is not None:
                self.selected_ref = (tk_key, new_idx)
                self.selected_items = {self.selected_ref}
                self.on_select(self.selected_ref)
                self.on_modified()
                self.redraw()
                return

        if bool(hasattr(self.nle, "is_track_locked") and self.nle.is_track_locked("V1")):
            self.show_hud_toast("🔒 مسار الفيديو الرئيسي مقفول (إلغاء القفل أولاً للقص)" if ar else "🔒 Video track is locked (unlock first to split)")
            return

        new_c = self.nle.split_clip_at(self.playhead_sec)
        if new_c is not None:
            self.selected_ref = ("clip", new_c)
            self.selected_items = {self.selected_ref}
            self.on_select(self.selected_ref)
            self.on_modified()
            self.redraw()

    def delete_selected(self):
        targets = set(self.selected_items) if self.selected_items else (set([self.selected_ref]) if self.selected_ref else set())
        if not targets:
            return
        ar = self._is_ar()
        unlocked_targets = {it for it in targets if not self._is_item_track_locked(it)}
        if not unlocked_targets:
            self.show_hud_toast("🔒 لا يمكن الحذف: كافة العناصر المحددة تقع ضمن مسارات مقفولة" if ar else "🔒 Cannot delete: selected items are on locked tracks")
            return
        targets = unlocked_targets

        self.nle.push_undo()
        by_track: Dict[str, List[int]] = {}
        clip_indices: List[int] = []
        for kind, idx in targets:
            if kind in ("clip", "V1_clip"):
                clip_indices.append(idx)
            elif kind == "A1_clip":
                if 0 <= idx < len(self.nle.clips):
                    self.nle.clips[idx]["muted"] = True
                    self.nle.clips[idx]["volume"] = 0.0
                    self.show_hud_toast("🔇 تم كتم/حذف صوت المقطع المحدد" if ar else "🔇 Muted/deleted audio for selected clip")
            else:
                by_track.setdefault(kind, []).append(idx)

        # Delete overlays from highest index to lowest
        for tkey, idx_list in by_track.items():
            t_list = self.nle.get_track_list(tkey)
            for idx in sorted(set(idx_list), reverse=True):
                if 0 <= idx < len(t_list):
                    t_list.pop(idx)

        # Delete clips from highest index to lowest
        for c_idx in sorted(set(clip_indices), reverse=True):
            if 0 <= c_idx < len(self.nle.clips):
                if len(self.nle.clips) > 1:
                    removed = self.nle.clips.pop(c_idx)
                    removed_dur = float(removed.get("tl_dur", 0.0))
                    if self.nle.ripple_mode and removed_dur > 0:
                        for j in range(c_idx, len(self.nle.clips)):
                            self.nle.clips[j]["tl_start"] = round(max(0.0, float(self.nle.clips[j].get("tl_start", 0.0)) - removed_dur), 3)

        self.nle.recompute_timeline(pack_gaps=False)
        self.selected_items.clear()
        self.selected_clip_indices.clear()
        self.selected_ref = ("clip", 0) if self.nle.clips else None
        self.playhead_sec = min(self.playhead_sec, self.nle.total_duration)
        self.on_select(self.selected_ref)
        self.on_modified()
        self.redraw()

    def duplicate_selected(self):
        targets = set(self.selected_items) if self.selected_items else (set([self.selected_ref]) if self.selected_ref else set())
        if not targets:
            return
        self.nle.push_undo()
        new_targets = set()
        # Duplicate overlay items
        for kind, idx in sorted(targets, key=lambda x: (x[0], -x[1])):
            if kind not in ("clip", "V1_clip", "A1_clip"):
                t_list = self.nle.get_track_list(kind)
                if 0 <= idx < len(t_list):
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
                    t_list.append(dup)
                    new_targets.add((kind, len(t_list) - 1))
            else:
                new_i = self.nle.duplicate_clip(idx)
                if new_i is not None:
                    new_targets.add((kind, new_i))

        if new_targets:
            self.selected_items = new_targets
            self._sync_selection_refs()
        self.on_modified()
        self.redraw()

    def copy_selected(self):
        """Copies all currently selected clips and overlay items into internal clipboard."""
        targets = set(self.selected_items) if self.selected_items else (set([self.selected_ref]) if self.selected_ref else set())
        if not targets:
            self.show_hud_toast("⚠️ لا يوجد عناصر محددة لنسخها" if self._is_ar() else "⚠️ No items selected to copy")
            return
        items = []
        for kind, idx in sorted(targets, key=lambda x: (x[0], x[1])):
            if kind in ("clip", "V1_clip", "A1_clip"):
                if 0 <= idx < len(self.nle.clips):
                    c = copy.deepcopy(self.nle.clips[idx])
                    s = float(c.get("tl_start", 0.0))
                    e = float(c.get("tl_end", s + 1.0))
                    items.append({"kind": kind, "orig_idx": idx, "start": s, "end": e, "data": c})
            else:
                t_list = self.nle.get_track_list(kind)
                if 0 <= idx < len(t_list):
                    it = copy.deepcopy(t_list[idx])
                    s = float(it.get("start_sec", 0.0))
                    e = float(it.get("end_sec", s + 3.0))
                    items.append({"kind": kind, "orig_idx": idx, "start": s, "end": e, "data": it})
        if not items:
            return
        self._clipboard_base_start = min(it["start"] for it in items)
        self._clipboard_items = items
        ar = self._is_ar()
        cnt = len(items)
        self.show_hud_toast(f"📋 تم نسخ {cnt} عنصر (اضغط Ctrl+V للصق عند المؤشر)" if ar else f"📋 Copied {cnt} item(s) (Press Ctrl+V to paste at playhead)")

    def paste_at_playhead(self):
        """Pastes clipboard clips and overlays starting at the current playhead position preserving relative timing."""
        if not getattr(self, "_clipboard_items", None):
            self.show_hud_toast("⚠️ الحافظة فارغة! حدد عنصراً واضغط Ctrl+C أولاً" if self._is_ar() else "⚠️ Clipboard is empty! Select an item and press Ctrl+C first")
            return
        # Check locked tracks
        v1_locked = bool(hasattr(self.nle, "is_track_locked") and self.nle.is_track_locked("V1"))
        valid_items = [it for it in self._clipboard_items if not (it["kind"] in ("clip", "V1_clip", "A1_clip") and v1_locked) and not (it["kind"] not in ("clip", "V1_clip", "A1_clip") and hasattr(self.nle, "is_track_locked") and self.nle.is_track_locked(it["kind"]))]
        if not valid_items:
            self.show_hud_toast("🔒 لا يمكن اللصق: كافة المسارات المستهدفة مقفولة" if self._is_ar() else "🔒 Cannot paste: destination tracks are locked")
            return

        self.nle.push_undo()
        dest_time = max(0.0, round(self.playhead_sec, 3))
        new_targets = set()

        # 1. Paste clips (if V1 not locked)
        clip_copies = [it for it in self._clipboard_items if it["kind"] in ("clip", "V1_clip", "A1_clip")] if not v1_locked else []
        for it in clip_copies:
            c_data = copy.deepcopy(it["data"])
            c_data["id"] = self.nle.next_id("clip") if hasattr(self.nle, "next_id") else f"c_{len(self.nle.clips) + 1}"
            b_name = c_data.get("name", "Clip").split(" #")[0].replace(" (Copy)", "")
            c_data["name"] = f"{b_name} (Copy)"
            rel_s = it["start"] - self._clipboard_base_start
            want_s = max(0.0, round(dest_time + rel_s, 3))
            dur = max(0.08, float(it["end"] - it["start"]))
            c_data["tl_start"] = want_s
            c_data["tl_dur"] = dur
            c_data["tl_end"] = round(want_s + dur, 3)

            others = list(self.nle.clips)
            insert_pos = 0
            for oc in others:
                oc_mid = float(oc.get("tl_start", 0.0)) + float(oc.get("tl_dur", 1.0)) * 0.5
                if want_s > oc_mid:
                    insert_pos += 1
                else:
                    break
            new_order = others[:insert_pos] + [c_data] + others[insert_pos:]
            running_end = round(want_s + dur, 3)
            for j in range(insert_pos + 1, len(new_order)):
                nc = new_order[j]
                ns = float(nc.get("tl_start", 0.0))
                nd = float(nc.get("tl_dur", 1.0))
                if ns < running_end:
                    nc["tl_start"] = round(running_end, 3)
                    running_end = round(running_end + nd, 3)
                else:
                    running_end = round(ns + nd, 3)
            self.nle.clips = new_order
            self.nle.recompute_timeline(pack_gaps=False)

            for ci, cl in enumerate(self.nle.clips):
                if cl["id"] == c_data["id"]:
                    new_targets.add(("clip", ci))
                    break

        # 2. Paste overlay items (skip locked tracks)
        for it in self._clipboard_items:
            kind = it["kind"]
            if kind in ("clip", "V1_clip", "A1_clip") or (hasattr(self.nle, "is_track_locked") and self.nle.is_track_locked(kind)):
                continue
            data = copy.deepcopy(it["data"])
            data["id"] = self.nle.next_id(kind.lower()) if hasattr(self.nle, "next_id") else f"{kind}_{len(self.nle.get_track_list(kind)) + 1}"
            rel_s = it["start"] - self._clipboard_base_start
            dur = max(0.2, float(it["end"] - it["start"]))
            new_s = max(0.0, round(dest_time + rel_s, 2))
            data["start_sec"] = new_s
            data["end_sec"] = round(new_s + dur, 2)
            if data.get("full_duration", False):
                data["full_duration"] = False
            t_list = self.nle.get_track_list(kind)
            t_list.append(data)
            new_targets.add((kind, len(t_list) - 1))

        if new_targets:
            self.selected_items = new_targets
            self._sync_selection_refs()

        self.on_modified()
        self.redraw()
        ar = self._is_ar()
        cnt = len(new_targets)
        self.show_hud_toast(f"📋 تم لصق {cnt} عنصر عند المؤشر ({dest_time:.1f}s)" if ar else f"📋 Pasted {cnt} item(s) at playhead ({dest_time:.1f}s)")
        app = getattr(self, "parent", None)
        while app and not hasattr(app, "_refresh_master_export_summary"):
            app = getattr(app, "parent", None)
        if app and hasattr(app, "_refresh_master_export_summary"):
            app._refresh_master_export_summary()

    def open_shortcuts_guide(self):
        """Opens the comprehensive shortcuts & app instructions modal dialog."""
        app = getattr(self, "parent", None)
        while app and not hasattr(app, "open_shortcuts_guide_dialog"):
            app = getattr(app, "parent", None)
        if app and hasattr(app, "open_shortcuts_guide_dialog"):
            app.open_shortcuts_guide_dialog()
        else:
            from ui_dialogs.shortcuts_guide_dialog import ShortcutsGuideDialog
            ShortcutsGuideDialog(self.winfo_toplevel(), is_ar=self._is_ar())

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
        for tspec in self.track_specs:
            th = self._get_track_height(tspec)
            if tspec[0] == track_key:
                return y, y + th
            y += th
        return y, y + 32

    def _y_to_track(self, y: float) -> Optional[str]:
        if y < self.RULER_H:
            return "RULER"
        cur_y = self.RULER_H
        for tspec in self.track_specs:
            th = self._get_track_height(tspec)
            if cur_y <= y < cur_y + th:
                return tspec[0]
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
        for idx, tspec in enumerate(self.track_specs):
            th = self._get_track_height(tspec)
            tkey = tspec[0]
            is_locked = bool(hasattr(self.nle, "is_track_locked") and self.nle.is_track_locked(tkey))
            lane_bg = "#13171f" if idx % 2 == 0 else "#161b24"
            if not self.nle.track_enabled.get(tkey, True):
                lane_bg = "#0d0f13"
            elif is_locked:
                lane_bg = "#19150f"
            c.create_rectangle(self.HEADER_W, cur_y, cw, cur_y + th, fill=lane_bg, outline="")
            if is_locked:
                c.create_text(cw - 12, cur_y + th // 2, text="🔒", fill="#e3b341", anchor="e", font=("Segoe UI", 8))
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

        # 3. Draw Overlay Tracks (V4, V3, V2, and any dynamic extra tracks)
        for tspec in self.track_specs:
            tkey = tspec[0]
            ttype = tspec[7] if len(tspec) > 7 else "text"
            if ttype in ("video", "audio") or tkey in ("V1", "A1"):
                continue
            col_body = tspec[2]
            col_hdr = tspec[3]
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
                is_sel = ((tkey, idx) in self.selected_items) or (self.selected_ref == (tkey, idx))
                fill_c = col_body if track_on else "#252932"
                hdr_c = col_hdr if track_on else "#303540"
                out_c = "#ffd700" if is_sel else ("#64b5f6" if is_sel else "#424a57")

                c.create_rectangle(dx0, y0 + 2, dx1, y1 - 2, fill=fill_c, outline=out_c, width=2 if is_sel else 1)
                if (y1 - y0) >= 22:
                    c.create_rectangle(dx0 + 1, y0 + 3, dx1 - 1, y0 + 8, fill=hdr_c, outline="")

                if ttype == "audio_item" or tkey == "A2" or tkey.startswith("AUD"):
                    item_w = dx1 - dx0
                    if item_w > 20:
                        mid_y = (y0 + y1) // 2
                        bar_step = 6
                        num_bars = int(item_w // bar_step)
                        for b_i in range(min(num_bars, 120)):
                            bx = dx0 + 4 + b_i * bar_step
                            if bx + 2 >= dx1 - 4:
                                break
                            bh = int((((b_i * 7 + idx * 11) % 9) + 3) * (0.6 if (y1 - y0) < 28 else 0.85))
                            c.create_line(bx, mid_y - bh, bx, mid_y + bh, fill="#2dd4bf" if track_on else "#4b5563", width=2)

                lbl = self._overlay_display_label(tkey, it, ar)
                if is_full:
                    lbl = f"∞ {lbl}"
                avail_w = dx1 - dx0 - 10
                if avail_w > 18:
                    max_chars = max(3, int(avail_w / 6.0))
                    f_sz = 7 if (y1 - y0) < 24 else 8
                    if ttype == "audio_item" or tkey == "A2" or tkey.startswith("AUD"):
                        c.create_text(dx0 + 6, (y0 + y1) // 2 + 1, text=lbl[:max_chars], anchor="w", fill="#071b18", font=("Segoe UI", f_sz, "bold"))
                    c.create_text(dx0 + 5, (y0 + y1) // 2, text=lbl[:max_chars], anchor="w", fill="#ffffff" if is_sel else "#f0f6fc", font=("Segoe UI", f_sz, "bold"))

                if is_sel:
                    c.create_rectangle(dx0, y0 + 2, min(dx1, dx0 + 4), y1 - 2, fill="#ffffff", outline="")
                    c.create_rectangle(max(dx0, dx1 - 4), y0 + 2, dx1, y1 - 2, fill="#ffffff", outline="")

                self._item_hit_boxes.append((tkey, idx, x0, y0 + 1, x1, y1 - 1))

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
            tl_s = float(clip["tl_start"])
            tl_e = float(clip["tl_end"])
            v_tl_s = tl_s
            v_tl_e = tl_e
            vx0 = self._sec_to_x(v_tl_s, tot_dur, tot_px)
            vx1 = max(vx0 + 6, self._sec_to_x(v_tl_e, tot_dur, tot_px))

            a_tl_s = float(clip["audio_tl_start"]) if clip.get("audio_tl_start") is not None else v_tl_s
            a_tl_dur = float(clip.get("audio_tl_dur", v_tl_e - v_tl_s))
            a_tl_e = a_tl_s + a_tl_dur
            ax0 = self._sec_to_x(a_tl_s, tot_dur, tot_px)
            ax1 = max(ax0 + 6, self._sec_to_x(a_tl_e, tot_dur, tot_px))

            v_visible = not (vx1 < self.HEADER_W or vx0 > cw)
            a_visible = not (ax1 < self.HEADER_W or ax0 > cw)
            if not v_visible and not a_visible:
                continue

            v_dx0 = max(self.HEADER_W, vx0)
            v_dx1 = min(cw, vx1)
            a_dx0 = max(self.HEADER_W, ax0)
            a_dx1 = min(cw, ax1)

            is_v_sel = (self.selected_ref in (("clip", idx), ("V1_clip", idx))) or (("clip", idx) in getattr(self, "selected_items", set())) or (("V1_clip", idx) in getattr(self, "selected_items", set()))
            is_a_sel = (self.selected_ref in (("clip", idx), ("A1_clip", idx))) or (("clip", idx) in getattr(self, "selected_items", set())) or (("A1_clip", idx) in getattr(self, "selected_items", set()))
            is_sil_clip = str(clip.get("name", "")).startswith("🔇")
            is_compound = bool(clip.get("sub_clips"))
            v_out_c = "#ffd700" if is_v_sel else "#11141a"
            v_out_w = 2 if is_v_sel else 1
            a_out_c = "#ffd700" if is_a_sel else "#11141a"
            a_out_w = 2 if is_a_sel else 1

            # --- V1 Blue Video Clip Block ---
            if v_visible and v_dx1 > v_dx0:
                v_fill = "#3a2528" if is_sil_clip else ("#1e3d4f" if is_compound else "#28486e")
                v_hdr = "#543237" if is_sil_clip else ("#2a5a73" if is_compound else "#366194")
                c.create_rectangle(v_dx0, v1_y0 + 2, v_dx1 - 1, v1_y1 - 2, fill=v_fill, outline=v_out_c, width=v_out_w)

                badges = []
                if is_compound:
                    badges.append(f"🔗{len(clip['sub_clips'])} " + ("أجزاء" if ar else "parts"))
                if clip.get("custom_transform"):
                    badges.append(f"🔍{float(clip.get('zoom', 1.0)):.1f}x")
                if abs(float(clip.get("speed", 1.0)) - 1.0) > 0.02:
                    badges.append(f"⚡{float(clip.get('speed', 1.0)):.2g}x")
                title_str = f"{clip.get('name', f'Clip {idx+1}')}  {' '.join(badges)}".strip()
                avail_vw = v_dx1 - v_dx0 - 10
                if avail_vw > 28:
                    c.create_text(
                        v_dx0 + 6,
                        v1_y1 - 10,
                        text=title_str[: max(4, int(avail_vw / 6.5))],
                        anchor="w",
                        fill="#ffffff",
                        font=("Segoe UI", 8, "bold"),
                    )
                    dur_lbl = f"@{v_tl_s:.1f}s | {self._fmt_tc(clip['src_start'], 'tenth')}→{self._fmt_tc(clip['src_end'], 'tenth')}"
                    if avail_vw > 76:
                        c.create_text(
                            v_dx0 + 6,
                            v1_y0 + 10,
                            text=dur_lbl[: max(6, int(avail_vw / 5.8))],
                            anchor="w",
                            fill="#9ec5fe",
                            font=("Consolas", 7),
                        )

                if is_v_sel:
                    c.create_rectangle(v_dx0, v1_y0 + 2, min(v_dx1, v_dx0 + 4), v1_y1 - 2, fill="#ffffff", outline="")
                    c.create_rectangle(max(v_dx0, v_dx1 - 5), v1_y0 + 2, v_dx1 - 1, v1_y1 - 2, fill="#ffffff", outline="")

            # --- A1 Green Audio Clip Block + High-Density Waveform ---
            if a_visible and a_dx1 > a_dx0:
                clip_muted = (not a1_track_on) or bool(clip.get("muted", False)) or float(clip.get("volume", 1.0)) <= 0.01
                a_fill = "#1d2922" if clip_muted else "#2c643b"
                c.create_rectangle(a_dx0, a1_y0 + 2, a_dx1 - 1, a1_y1 - 2, fill=a_fill, outline=a_out_c, width=a_out_w)

                wf_mid = (a1_y0 + a1_y1) / 2.0
                wf_half = max(3.0, (a1_y1 - a1_y0) / 2.0 - 5.0)
                center_line_col = "#3d5747" if clip_muted else "#5bb87e"
                wave_fill = "#56695e" if clip_muted else "#e2faeb"

                px_span = int(a_dx1 - a_dx0 - 2)
                if px_span >= 2:
                    peaks = self.waveform_peaks
                    n_peaks = len(peaks) if peaks else 0
                    cs0 = float(clip.get("audio_src_start", clip["src_start"]))
                    cs1 = float(clip.get("audio_src_end", clip["src_end"]))
                    c_span = max(0.05, cs1 - cs0)
                    full_clip_w = max(1.0, ax1 - ax0)
                    vol_mul = min(1.5, float(clip.get("volume", 1.0)))

                    step_px = 1 if px_span <= 1800 else 2
                    top_pts = []
                    bot_pts = []

                    for bx in range(int(a_dx0 + 1), int(a_dx1 - 1), step_px):
                        rel_frac0 = max(0.0, min(1.0, (bx - ax0) / full_clip_w))
                        rel_frac1 = max(0.0, min(1.0, (bx + step_px - ax0) / full_clip_w))
                        t0 = cs0 + rel_frac0 * c_span
                        t1 = cs0 + rel_frac1 * c_span
                        if t1 < t0:
                            t0, t1 = t1, t0

                        if n_peaks > 0 and src_total > 0:
                            p0 = int((t0 / src_total) * n_peaks)
                            p1 = int((t1 / src_total) * n_peaks)
                            if p1 <= p0:
                                idx_p = min(n_peaks - 1, max(0, p0))
                                amp = peaks[idx_p]
                            else:
                                sub = peaks[max(0, p0): min(n_peaks, p1 + 1)]
                                amp = max(sub) if sub else 0.0
                        else:
                            amp = 0.0

                        amp = min(1.0, max(0.0, amp * vol_mul))
                        if amp <= 0.005:
                            bh = 0.0
                        else:
                            bh = max(1.2, min(wf_half, amp * wf_half))

                        top_pts.append((bx, wf_mid - bh))
                        bot_pts.append((bx, wf_mid + bh))

                    if top_pts and bot_pts:
                        poly_pts = []
                        for px, py in top_pts:
                            poly_pts.extend((px, py))
                        for px, py in reversed(bot_pts):
                            poly_pts.extend((px, py))
                        c.create_polygon(poly_pts, fill=wave_fill, outline="")

                    # Horizontal baseline drawn across the entire clip length
                    c.create_line(a_dx0 + 1, wf_mid, a_dx1 - 1, wf_mid, fill=center_line_col, width=1)

                if is_a_sel:
                    c.create_rectangle(a_dx0, a1_y0 + 2, min(a_dx1, a_dx0 + 4), a1_y1 - 2, fill="#ffffff", outline="")
                    c.create_rectangle(max(a_dx0, a_dx1 - 5), a1_y0 + 2, a_dx1 - 1, a1_y1 - 2, fill="#ffffff", outline="")

                avail_aw = a_dx1 - a_dx0 - 10
                if avail_aw > 36:
                    a_lbl = "🔇 صامت" if (clip_muted and ar) else ("🔇 Muted" if clip_muted else f"{clip.get('name', 'Audio')}")
                    # Subtle dark text shadow for high contrast readability against waveform
                    c.create_text(a_dx0 + 7, a1_y1 - 8, text=a_lbl[: max(4, int(avail_aw / 6.5))], anchor="w", fill="#0d1b11", font=("Segoe UI", 8, "bold"))
                    c.create_text(a_dx0 + 6, a1_y1 - 9, text=a_lbl[: max(4, int(avail_aw / 6.5))], anchor="w", fill="#ffffff", font=("Segoe UI", 8, "bold"))

            if idx > 0:
                if self.HEADER_W <= vx0 <= cw:
                    c.create_line(vx0, v1_y0, vx0, v1_y1, fill="#090b0f", width=2)
                if self.HEADER_W <= ax0 <= cw:
                    c.create_line(ax0, a1_y0, ax0, a1_y1, fill="#090b0f", width=2)

            if getattr(self, "linked_selection", True):
                self._item_hit_boxes.append(("clip", idx, min(vx0, ax0), v1_y0 + 2, max(vx1, ax1), a1_y1 - 2))
            else:
                self._item_hit_boxes.append(("V1_clip", idx, vx0, v1_y0 + 2, vx1, v1_y1 - 2))
                self._item_hit_boxes.append(("A1_clip", idx, ax0, a1_y0 + 2, ax1, a1_y1 - 2))

            # 4c. Draw transition indicator badge and register cut hit boxes
            if idx < len(self.nle.clips) - 1:
                cut_idx = idx
                cut_x = vx1
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
        for tspec in self.track_specs:
            tkey = tspec[0]
            th = self._get_track_height(tspec)
            col_body = tspec[2]
            col_hdr = tspec[3]
            lbl_ar = tspec[4]
            lbl_en = tspec[5]
            act_sym = tspec[6]
            en = self.nle.track_enabled.get(tkey, True)
            c.create_rectangle(0, hy, self.HEADER_W, hy + th, fill="#1a1f29" if en else "#12151c", outline="")
            c.create_rectangle(0, hy + 1, 4, hy + th - 1, fill=col_body if en else "#30363d", outline="")
            c.create_line(0, hy + th, self.HEADER_W, hy + th, fill="#282f3c", width=1)

            # Eye / Speaker toggle box (x: 6..34) - Much larger, vibrant, and ultra-visible!
            is_audio_t = (tkey in ("A1", "A2") or tkey.startswith("AUD"))
            toggle_icon = ("🔊" if en else "🔇") if is_audio_t else ("👁" if en else "🚫")
            bh = min(22, max(14, th - 4))
            box_x0, box_x1 = 6, 34
            box_y0, box_y1 = hy + (th // 2) - bh // 2, hy + (th // 2) + bh // 2
            
            if is_audio_t:
                box_bg = "#153a22" if en else "#5c1d1d"
                box_border = "#2ea043" if en else "#f85149"
                icon_fg = "#3fb950" if en else "#ffffff"
            else:
                box_bg = "#1c2838" if en else "#441c1c"
                box_border = "#388bfd" if en else "#da3633"
                icon_fg = "#58a6ff" if en else "#ff7b72"

            c.create_rectangle(box_x0, box_y0, box_x1, box_y1, fill=box_bg, outline=box_border, width=1)
            c.create_text((box_x0 + box_x1) // 2, hy + th // 2, text=toggle_icon, fill=icon_fg, font=("Segoe UI Emoji", 9 if th < 26 else 10, "bold"))

            # Track title
            t_label = lbl_ar if ar else lbl_en
            f_sz = 7 if th < 24 else 8
            c.create_text(38, hy + th // 2, text=t_label, anchor="w", fill="#e6edf3" if en else "#8b949e", font=("Segoe UI", f_sz, "bold"))

            # Lock / Unlock toggle box (x: HEADER_W - 44 .. HEADER_W - 24)
            is_locked = bool(hasattr(self.nle, "is_track_locked") and self.nle.is_track_locked(tkey))
            lx0, lx1 = self.HEADER_W - 44, self.HEADER_W - 24
            ly0, ly1 = hy + (th // 2) - bh // 2, hy + (th // 2) + bh // 2
            c.create_rectangle(lx0, ly0, lx1, ly1, fill="#382b14" if is_locked else "#202530", outline="#e3b341" if is_locked else "#384152")
            c.create_text((lx0 + lx1) // 2, hy + th // 2, text="🔒" if is_locked else "🔓", fill="#ffd700" if is_locked else "#6e7681", font=("Segoe UI", 7 if th < 24 else 8))

            # Per-Track Quick Add / Split Button (x: HEADER_W-22 .. HEADER_W-5)
            bx0, bx1 = self.HEADER_W - 22, self.HEADER_W - 5
            by0, by1 = hy + (th // 2) - bh // 2, hy + (th // 2) + bh // 2
            c.create_rectangle(bx0, by0, bx1, by1, fill=col_hdr if en else "#252a34", outline="#485266")
            c.create_text((bx0 + bx1) // 2, hy + th // 2, text=act_sym, fill="#ffffff", font=("Segoe UI", f_sz, "bold"))
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
        if tkey == "A2" or tkey.startswith("AUD") or item.get("audio_path"):
            p = str(item.get("audio_path", "")).strip()
            nm = Path(p).name if p else ("صوت" if ar else "Audio")
            vol = int(round(float(item.get("volume", 1.0)) * 100))
            mut = " 🔇" if item.get("muted") else ""
            return f"🎵 {nm} ({vol}%){mut}"
        if tkey.startswith("TXT") or tkey == "V3":
            raw = str(item.get("text", "")).strip() or ("نص" if ar else "Text")
            return f"T+ {prepare_arabic_for_rendering(raw)}"
        if tkey.startswith("LOG") or tkey == "V4":
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
        # 1. Overlay tracks (V4, V3, V2, and extra tracks)
        for kind, idx, x0, y0, x1, y1 in reversed(self._item_hit_boxes):
            if kind not in ("clip", "V1_clip", "A1_clip") and y0 <= my <= y1 and (x0 - 5) <= mx <= (x1 + 5):
                if (x1 - x0) >= 12:
                    if abs(mx - x0) <= 7:
                        return (kind, idx), "left"
                    if abs(mx - x1) <= 7:
                        return (kind, idx), "right"
                return (kind, idx), "body"

        # 2. Video & Audio Clips (Track V1 / A1)
        clip_boxes = [box for box in self._item_hit_boxes if box[0] in ("clip", "V1_clip", "A1_clip")]
        if not clip_boxes:
            return None, "none"

        matching_y = [box for box in clip_boxes if (box[3] - 4 <= my <= box[5] + 4)]
        if matching_y:
            clip_boxes = matching_y
        else:
            v_min = min(b[3] for b in clip_boxes)
            v_max = max(b[5] for b in clip_boxes)
            if not (v_min - 4 <= my <= v_max + 4):
                return None, "none"

        clip_boxes.sort(key=lambda b: b[1])
        num_clips = len(clip_boxes)
        EDGE_TOL = 8.0

        # Step 2a: Check EDGES across all clips with priority to boundaries
        for i, (_k, idx, x0, _y0, x1, _y1) in enumerate(clip_boxes):
            # Check RIGHT edge of clip idx (at x1)
            if abs(mx - x1) <= EDGE_TOL:
                if i < num_clips - 1:
                    next_k = clip_boxes[i + 1][0]
                    next_idx = clip_boxes[i + 1][1]
                    next_x0 = clip_boxes[i + 1][2]
                    if abs(next_x0 - x1) <= 3:
                        # Adjacent cut seam between clip i and clip i+1
                        if self.selected_ref == (_k, idx):
                            return (_k, idx), "right"
                        elif self.selected_ref == (next_k, next_idx):
                            return (next_k, next_idx), "left"
                        elif mx <= x1:
                            return (_k, idx), "right"
                        else:
                            return (next_k, next_idx), "left"
                return (_k, idx), "right"

            # Check LEFT edge of clip idx (at x0)
            if abs(mx - x0) <= EDGE_TOL:
                if i == 0 or abs(clip_boxes[i - 1][4] - x0) > 3:
                    return (_k, idx), "left"
                else:
                    prev_k = clip_boxes[i - 1][0]
                    prev_idx = clip_boxes[i - 1][1]
                    if self.selected_ref == (_k, idx):
                        return (_k, idx), "left"
                    elif self.selected_ref == (prev_k, prev_idx):
                        return (prev_k, prev_idx), "right"
                    elif mx >= x0:
                        return (_k, idx), "left"
                    else:
                        return (prev_k, prev_idx), "right"

        # Step 2b: If no edge matched, check which clip BODY contains mx
        for _k, idx, x0, _y0, x1, _y1 in clip_boxes:
            if x0 <= mx <= x1:
                return (_k, idx), "body"

        return None, "none"

    def _snap_time(self, raw_sec: float, ignore_ref: Optional[Tuple[str, int]] = None) -> Tuple[float, Optional[float]]:
        tot_dur = max(0.3, self.nle.total_duration)
        _vw, tot_px = self._viewport_metrics()
        thresh_sec = 6.5 * (tot_dur / max(1.0, tot_px))

        candidates = [0.0, tot_dur, self.playhead_sec]
        for idx, c in enumerate(self.nle.clips):
            if ignore_ref in (("clip", idx), ("V1_clip", idx)):
                pass
            else:
                candidates.append(float(c.get("tl_start", 0.0)))
                candidates.append(float(c.get("tl_end", float(c.get("tl_start", 0.0)) + 1.0)))

            if ignore_ref in (("clip", idx), ("A1_clip", idx)):
                pass
            else:
                if c.get("audio_tl_start") is not None:
                    a_s = float(c["audio_tl_start"])
                    a_dur = float(c.get("audio_tl_dur", c.get("tl_dur", 1.0)))
                    candidates.append(a_s)
                    candidates.append(a_s + a_dur)

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

    def _is_item_track_locked(self, target: Optional[Tuple[str, int]]) -> bool:
        if not target or not isinstance(target, tuple):
            return False
        kind, _ = target
        tkey = "V1" if kind in ("clip", "V1_clip") else ("A1" if kind == "A1_clip" else kind)
        return bool(hasattr(self.nle, "is_track_locked") and self.nle.is_track_locked(tkey))

    def _handle_header_click(self, event, tkey: str):
        mx = event.x
        # Clicked Per-Track [+] / Action button on right side of track header
        if mx >= self.HEADER_W - 23:
            tspec = next((t for t in self.track_specs if t[0] == tkey), None)
            ttype = tspec[7] if (tspec and len(tspec) > 7) else ("text" if tkey.startswith("TXT") or tkey == "V3" else ("media" if tkey.startswith("MED") or tkey == "V2" else ("logo" if tkey.startswith("LOG") or tkey == "V4" else "video")))
            if ttype == "audio_item" or tkey == "A2" or tkey.startswith("AUD"):
                self.add_audio_file_dialog(self.playhead_sec)
            elif ttype == "logo" or tkey == "V4":
                self.on_add_element("logo", self.playhead_sec)
            elif ttype == "text" or tkey == "V3":
                self.on_add_element("text", self.playhead_sec)
            elif ttype == "media" or tkey == "V2":
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

        # Clicked Lock toggle (x: HEADER_W - 44 .. HEADER_W - 24)
        if self.HEADER_W - 45 <= mx < self.HEADER_W - 23:
            new_locked = self.nle.toggle_track_lock(tkey)
            self.on_modified()
            self.redraw()
            ar = self._is_ar()
            if new_locked:
                self.show_hud_toast("🔒 تم قفل المسار لمنع التعديل والقص" if ar else "🔒 Track locked against edits & cuts")
            else:
                self.show_hud_toast("🔓 تم إلغاء قفل المسار" if ar else "🔓 Track unlocked")
            return

        # Clicked Visibility / Mute toggle (left side of track header)
        self._toggle_track_visibility(tkey)

    def _toggle_track_visibility(self, tkey: str):
        self.nle.track_enabled[tkey] = not self.nle.track_enabled.get(tkey, True)
        self.on_modified()
        self.redraw()
        ar = self._is_ar()
        is_on = self.nle.track_enabled.get(tkey, True)
        app = self._get_app()
        if app and hasattr(app, "_apply_active_clip_playback_fx"):
            app._apply_active_clip_playback_fx()
            if hasattr(app, "_refresh_audio_inspector_status"):
                app._refresh_audio_inspector_status()
        if tkey == "A1":
            self.show_hud_toast("🔊 تم تفعيل صوت الفيديو الأصلي" if is_on else "🔇 تم كتم صوت الفيديو الأصلي بالكامل" if ar else ("🔊 Original video audio enabled" if is_on else "🔇 Original video audio muted"))
        elif tkey == "A2" or tkey.startswith("AUD"):
            self.show_hud_toast("🎵 تم تفعيل مسار الصوت المضاف" if is_on else "🔇 تم كتم مسار الصوت المضاف" if ar else ("🎵 Added audio track enabled" if is_on else "🔇 Added audio track muted"))
        elif tkey == "V1":
            self.show_hud_toast("👁️ تم إظهار مسار الفيديو" if is_on else "🚫 تم إخفاء مسار الفيديو" if ar else ("👁️ Video track shown" if is_on else "🚫 Video track hidden"))

    def _on_press(self, event):
        self.canvas.focus_set()
        if hasattr(self, "_canvas_tip"):
            self._canvas_tip.hide()
        mx, my = event.x, event.y
        self._drag_moved = False
        self._undo_pushed_for_drag = False
        self._snap_guide_sec = None

        # 1. Left Track Headers (Visibility/Mute, Lock, [+] Button, or Drag Reorder)
        if mx < self.HEADER_W:
            tkey = self._y_to_track(my)
            if tkey and tkey != "RULER":
                if 6 <= mx <= 35:
                    self._toggle_track_visibility(tkey)
                elif self.HEADER_W - 45 <= mx < self.HEADER_W - 23:
                    new_locked = self.nle.toggle_track_lock(tkey)
                    self.on_modified()
                    self.redraw()
                    ar = self._is_ar()
                    if new_locked:
                        self.show_hud_toast("🔒 تم قفل المسار لمنع التعديل والقص" if ar else "🔒 Track locked against edits & cuts")
                    else:
                        self.show_hud_toast("🔓 تم إلغاء قفل المسار" if ar else "🔓 Track unlocked")
                elif mx >= self.HEADER_W - 23:
                    self._handle_header_click(event, tkey)
                else:
                    self._drag_action = "reorder_track"
                    self._drag_track_key = tkey
                    self._drag_start_y = my
                    self._drag_start_x = mx
                    self.canvas.configure(cursor="sb_v_double_arrow")
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
            ar = self._is_ar()
            if hit_ref and self._is_item_track_locked(hit_ref):
                self.show_hud_toast("🔒 المسار مقفول ضد القص (قم بإلغاء القفل أولاً)" if ar else "🔒 Track is locked against cutting")
                return
            if (not hit_ref or hit_ref[0] in ("clip", "V1_clip", "A1_clip")) and self.nle.is_track_locked("V1"):
                self.show_hud_toast("🔒 مسار الفيديو الرئيسي مقفول ضد القص" if ar else "🔒 Video track is locked against cutting")
                return
            if hit_ref and hit_ref[0] not in ("clip", "V1_clip", "A1_clip"):
                new_i = self.nle.split_overlay_at(hit_ref[0], hit_ref[1], sec)
                if new_i is not None:
                    self.selected_ref = (hit_ref[0], new_i)
                    self.selected_items = {self.selected_ref}
                    self.on_select(self.selected_ref)
                    self.on_modified()
            else:
                new_c = self.nle.split_clip_at(sec)
                if new_c is not None:
                    target_kind = hit_ref[0] if (hit_ref and hit_ref[0] in ("V1_clip", "A1_clip")) else "clip"
                    self.selected_ref = (target_kind, new_c)
                    self.selected_items = {self.selected_ref}
                    self.on_select(self.selected_ref)
                    self.on_modified()
            self.playhead_sec = sec
            self.on_scrub(sec, True)
            self.redraw()
            return

        # 5. Select Mode -> Hit test clips & overlays
        hit_ref, part = self._hit_test(mx, my)
        if hit_ref is not None:
            kind, idx = hit_ref
            is_mod = bool(event.state & 0x0001 or event.state & 0x0004)
            if is_mod:
                if hit_ref in self.selected_items:
                    self.selected_items.remove(hit_ref)
                else:
                    self.selected_items.add(hit_ref)
            else:
                if hit_ref not in self.selected_items:
                    self.selected_items = {hit_ref}

            self._sync_selection_refs()
            self._drag_target = hit_ref
            self._drag_start_x = mx

            # Record origins for multi-drag
            self._drag_multi_origins.clear()
            self._drag_multi_audio_origins = {}
            for sel_k, sel_i in self.selected_items:
                if sel_k in ("clip", "V1_clip", "A1_clip"):
                    if 0 <= sel_i < len(self.nle.clips):
                        cl = self.nle.clips[sel_i]
                        if sel_k == "A1_clip":
                            self._drag_multi_origins[(sel_k, sel_i)] = float(cl.get("audio_tl_start", cl["tl_start"]))
                        else:
                            self._drag_multi_origins[(sel_k, sel_i)] = float(cl["tl_start"])
                            if cl.get("audio_tl_start") is not None:
                                self._drag_multi_audio_origins[(sel_k, sel_i)] = float(cl["audio_tl_start"])
                else:
                    t_list = self.nle.get_track_list(sel_k)
                    if 0 <= sel_i < len(t_list):
                        it = t_list[sel_i]
                        s0 = 0.0 if it.get("full_duration") else float(it.get("start_sec", 0.0))
                        e0 = tot_dur if it.get("full_duration") else float(it.get("end_sec", tot_dur))
                        self._drag_multi_origins[(sel_k, sel_i)] = (s0, e0)

            has_locked = any(self._is_item_track_locked(it) for it in self.selected_items)
            if has_locked:
                self._drag_action = "locked"
            elif len(self.selected_items) == 1:
                if kind not in ("clip", "V1_clip", "A1_clip"):
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
                else:
                    cl = self.nle.clips[idx]
                    if kind == "A1_clip":
                        self._drag_orig_s = float(cl.get("audio_src_start", cl["src_start"]))
                        self._drag_orig_e = float(cl.get("audio_src_end", cl["src_end"]))
                        self._drag_orig_tl_s = float(cl.get("audio_tl_start", cl["tl_start"]))
                        self._drag_orig_audio_tl_s = self._drag_orig_tl_s
                    else:
                        self._drag_orig_s = float(cl["src_start"])
                        self._drag_orig_e = float(cl["src_end"])
                        self._drag_orig_tl_s = float(cl["tl_start"])
                        self._drag_orig_audio_tl_s = float(cl.get("audio_tl_start", cl["tl_start"]))
                    if part == "left":
                        self._drag_action = "trim_clip_left"
                        self._drag_multi_origins = {("clip", j): float(self.nle.clips[j]["tl_start"]) for j in range(len(self.nle.clips))}
                    elif part == "right":
                        self._drag_action = "trim_clip_right"
                        self._drag_multi_origins = {("clip", j): float(self.nle.clips[j]["tl_start"]) for j in range(len(self.nle.clips))}
                    else:
                        self._drag_action = "move_or_click_clip"
            else:
                self._drag_action = "move_multi"
            self.redraw()
        else:
            # Clicked empty lane or gap -> Rubber-band Marquee Selection start!
            is_mod = bool(event.state & 0x0001 or event.state & 0x0004)
            if not is_mod:
                self.selected_items.clear()
                self._sync_selection_refs()
            self._drag_action = "marquee"
            self._marquee_start_x = mx
            self._marquee_start_y = my
            self._drag_start_x = mx
            sec = self._x_to_sec(max(self.HEADER_W, mx))
            self.redraw()
            self.on_scrub(sec, False)

    def _on_drag(self, event):
        if not self._drag_action or self._drag_action == "locked":
            if self._drag_action == "locked" and abs(event.x - getattr(self, "_drag_start_x", event.x)) > 5:
                ar = self._is_ar()
                self.show_hud_toast("🔒 المسار مقفول (قم بإلغاء القفل أولاً للتحريك أو التعديل)" if ar else "🔒 Track is locked (unlock to move or trim)")
            return
        mx = event.x
        dx_px = mx - self._drag_start_x
        if abs(dx_px) > 3 or abs(event.y - getattr(self, "_drag_start_y", event.y)) > 3:
            self._drag_moved = True

        if self._drag_action == "reorder_track":
            dest_tkey = self._y_to_track(event.y)
            self._draw_reorder_indicator(event.y, dest_tkey)
            return

        if self._drag_action == "marquee":
            c = self.canvas
            c.delete("marquee_box")
            x0 = min(self._marquee_start_x, mx)
            y0 = min(self._marquee_start_y, event.y)
            x1 = max(self._marquee_start_x, mx)
            y1 = max(self._marquee_start_y, event.y)
            c.create_rectangle(
                x0, y0, x1, y1,
                fill="#1f6feb",
                outline="#58a6ff",
                width=1.5,
                stipple="gray25",
                tags="marquee_box",
            )
            # Find all items intersecting marquee box
            box_sel = set()
            for kind, idx, bx0, by0, bx1, by1 in self._item_hit_boxes:
                if not (bx1 < x0 or bx0 > x1 or by1 < y0 or by0 > y1):
                    box_sel.add((kind, idx))
            is_mod = bool(event.state & 0x0001 or event.state & 0x0004)
            if is_mod:
                self.selected_items.update(box_sel)
            else:
                self.selected_items = box_sel
            self._sync_selection_refs()
            return

        if self._drag_action == "scrub":
            sec = self._x_to_sec(max(self.HEADER_W, mx))
            self.playhead_sec = sec
            if not self._update_playhead_fast():
                self.redraw()
            self.on_scrub(sec, False)
            return

        dt_sec = (dx_px / max(1.0, self._drag_ref_tot_px)) * self._drag_ref_tot_dur

        if self._drag_action == "move_multi" and abs(dx_px) > 3:
            if not self._undo_pushed_for_drag:
                self.nle.push_undo()
                self._undo_pushed_for_drag = True
            for sel_k, sel_i in self.selected_items:
                if sel_k in ("clip", "V1_clip", "A1_clip"):
                    if 0 <= sel_i < len(self.nle.clips):
                        cl = self.nle.clips[sel_i]
                        if sel_k == "A1_clip":
                            orig_a_tl = self._drag_multi_origins.get((sel_k, sel_i), float(cl.get("audio_tl_start", cl["tl_start"])))
                            cl["audio_tl_start"] = round(max(0.0, orig_a_tl + dt_sec), 3)
                            if "audio_tl_dur" not in cl:
                                cl["audio_tl_dur"] = float(cl.get("tl_dur", cl["src_end"] - cl["src_start"]))
                        elif sel_k == "V1_clip":
                            if cl.get("audio_tl_start") is None:
                                cl["audio_tl_start"] = float(cl["tl_start"])
                                cl["audio_tl_dur"] = float(cl.get("tl_dur", cl["src_end"] - cl["src_start"]))
                                cl["audio_src_start"] = float(cl["src_start"])
                                cl["audio_src_end"] = float(cl["src_end"])
                            orig_tl = self._drag_multi_origins.get((sel_k, sel_i), float(cl["tl_start"]))
                            cl["tl_start"] = round(max(0.0, orig_tl + dt_sec), 3)
                        else:  # "clip" (linked)
                            orig_tl = self._drag_multi_origins.get((sel_k, sel_i), float(cl["tl_start"]))
                            cl["tl_start"] = round(max(0.0, orig_tl + dt_sec), 3)
                            if cl.get("audio_tl_start") is not None:
                                orig_a_tl = getattr(self, "_drag_multi_audio_origins", {}).get((sel_k, sel_i), float(cl["audio_tl_start"]))
                                cl["audio_tl_start"] = round(max(0.0, orig_a_tl + dt_sec), 3)
                else:
                    t_list = self.nle.get_track_list(sel_k)
                    if 0 <= sel_i < len(t_list):
                        it = t_list[sel_i]
                        orig_pair = self._drag_multi_origins.get((sel_k, sel_i))
                        if orig_pair:
                            s0, e0 = orig_pair
                            span = max(0.2, e0 - s0)
                            new_s = max(0.0, s0 + dt_sec)
                            it["full_duration"] = False
                            it["start_sec"] = round(new_s, 2)
                            it["end_sec"] = round(new_s + span, 2)
            self.nle.recompute_timeline(pack_gaps=False)
            self.redraw()
            return

        if not self._drag_target:
            return
        kind, idx = self._drag_target

        if kind not in ("clip", "V1_clip", "A1_clip"):
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

        elif kind in ("clip", "V1_clip", "A1_clip") and 0 <= idx < len(self.nle.clips):
            cl = self.nle.clips[idx]
            spd = max(0.25, float(cl.get("speed", 1.0)))
            src_max = max(1.0, float(self.nle.source_duration or self._drag_ref_tot_dur))

            if self._drag_action == "trim_clip_left":
                if not self._undo_pushed_for_drag:
                    self.nle.push_undo()
                    self._undo_pushed_for_drag = True
                new_s = max(0.0, min(self._drag_orig_e - 0.12, self._drag_orig_s + dt_sec * spd))
                delta_tl = (new_s - self._drag_orig_s) / spd
                if kind == "A1_clip":
                    cl["audio_src_start"] = round(new_s, 3)
                    if "audio_src_end" not in cl:
                        cl["audio_src_end"] = float(cl["src_end"])
                    cl["audio_tl_start"] = round(max(0.0, self._drag_orig_audio_tl_s + delta_tl), 3)
                    cl["audio_tl_dur"] = round(max(0.1, (float(cl["audio_src_end"]) - new_s) / spd), 3)
                    self.redraw()
                elif kind == "V1_clip":
                    if cl.get("audio_tl_start") is None:
                        cl["audio_tl_start"] = float(cl["tl_start"])
                        cl["audio_tl_dur"] = float(cl.get("tl_dur", cl["src_end"] - cl["src_start"]))
                        cl["audio_src_start"] = float(cl["src_start"])
                        cl["audio_src_end"] = float(cl["src_end"])
                    cl["src_start"] = round(new_s, 3)
                    if not self.nle.ripple_mode:
                        cl["tl_start"] = round(max(0.0, self._drag_orig_tl_s + delta_tl), 3)
                    self.nle.recompute_timeline(pack_gaps=False)
                    self.redraw()
                else:  # kind == "clip"
                    cl["src_start"] = round(new_s, 3)
                    if cl.get("audio_tl_start") is not None:
                        cl["audio_src_start"] = round(new_s, 3)
                        cl["audio_tl_start"] = round(max(0.0, self._drag_orig_audio_tl_s + delta_tl), 3)
                        cl["audio_tl_dur"] = round(max(0.1, (float(cl.get("audio_src_end", cl["src_end"])) - new_s) / spd), 3)
                    if not self.nle.ripple_mode:
                        cl["tl_start"] = round(max(0.0, self._drag_orig_tl_s + delta_tl), 3)
                    self.nle.recompute_timeline(pack_gaps=False)
                    self.redraw()

            elif self._drag_action == "trim_clip_right":
                if not self._undo_pushed_for_drag:
                    self.nle.push_undo()
                    self._undo_pushed_for_drag = True
                new_e = max(self._drag_orig_s + 0.12, min(src_max, self._drag_orig_e + dt_sec * spd))
                if kind == "A1_clip":
                    cl["audio_src_end"] = round(new_e, 3)
                    if "audio_src_start" not in cl:
                        cl["audio_src_start"] = float(cl["src_start"])
                    if "audio_tl_start" not in cl:
                        cl["audio_tl_start"] = float(cl["tl_start"])
                    cl["audio_tl_dur"] = round(max(0.1, (new_e - float(cl["audio_src_start"])) / spd), 3)
                    self.redraw()
                elif kind == "V1_clip":
                    if cl.get("audio_tl_start") is None:
                        cl["audio_tl_start"] = float(cl["tl_start"])
                        cl["audio_tl_dur"] = float(cl.get("tl_dur", cl["src_end"] - cl["src_start"]))
                        cl["audio_src_start"] = float(cl["src_start"])
                        cl["audio_src_end"] = float(cl["src_end"])
                    cl["src_end"] = round(new_e, 3)
                    if self.nle.ripple_mode and idx < len(self.nle.clips) - 1:
                        delta_tl = (new_e - self._drag_orig_e) / spd
                        for j in range(idx + 1, len(self.nle.clips)):
                            orig_start = self._drag_multi_origins.get(("clip", j), float(self.nle.clips[j]["tl_start"]))
                            self.nle.clips[j]["tl_start"] = round(max(0.0, orig_start + delta_tl), 3)
                    self.nle.recompute_timeline(pack_gaps=False)
                    self.redraw()
                else:  # kind == "clip"
                    cl["src_end"] = round(new_e, 3)
                    if cl.get("audio_tl_start") is not None:
                        cl["audio_src_end"] = round(new_e, 3)
                        cl["audio_tl_dur"] = round(max(0.1, (new_e - float(cl.get("audio_src_start", cl["src_start"]))) / spd), 3)
                    if self.nle.ripple_mode and idx < len(self.nle.clips) - 1:
                        delta_tl = (new_e - self._drag_orig_e) / spd
                        for j in range(idx + 1, len(self.nle.clips)):
                            orig_start = self._drag_multi_origins.get(("clip", j), float(self.nle.clips[j]["tl_start"]))
                            self.nle.clips[j]["tl_start"] = round(max(0.0, orig_start + delta_tl), 3)
                    self.nle.recompute_timeline(pack_gaps=False)
                    self.redraw()

            elif self._drag_action == "move_or_click_clip" and abs(dx_px) > 4:
                if not self._undo_pushed_for_drag:
                    self.nle.push_undo()
                    self._undo_pushed_for_drag = True
                if kind == "A1_clip":
                    raw_a_s = max(0.0, self._drag_orig_audio_tl_s + dt_sec)
                    snapped_a_s, guide = self._snap_time(raw_a_s, ignore_ref=("A1_clip", idx))
                    self._snap_guide_sec = guide
                    v_s = float(cl.get("tl_start", 0.0))
                    if abs(snapped_a_s - v_s) <= 0.04:
                        cl.pop("audio_tl_start", None)
                        cl.pop("audio_tl_dur", None)
                        cl.pop("audio_src_start", None)
                        cl.pop("audio_src_end", None)
                    else:
                        cl["audio_tl_start"] = round(snapped_a_s, 3)
                        if "audio_tl_dur" not in cl:
                            cl["audio_tl_dur"] = round(float(cl.get("tl_dur", cl["src_end"] - cl["src_start"])), 3)
                        if "audio_src_start" not in cl:
                            cl["audio_src_start"] = float(cl["src_start"])
                        if "audio_src_end" not in cl:
                            cl["audio_src_end"] = float(cl["src_end"])
                    self.redraw()
                elif kind == "V1_clip":
                    if cl.get("audio_tl_start") is None:
                        cl["audio_tl_start"] = float(cl["tl_start"])
                        cl["audio_tl_dur"] = float(cl.get("tl_dur", cl["src_end"] - cl["src_start"]))
                        cl["audio_src_start"] = float(cl["src_start"])
                        cl["audio_src_end"] = float(cl["src_end"])
                    raw_tl_s = max(0.0, self._drag_orig_tl_s + dt_sec)
                    snapped_tl_s, guide = self._snap_time(raw_tl_s, ignore_ref=("V1_clip", idx))
                    self._snap_guide_sec = guide
                    new_idx = self.nle.move_clip_to_time(idx, snapped_tl_s, push_undo=False)
                    self._drag_target = (kind, new_idx)
                    self.selected_ref = (kind, new_idx)
                    self._sync_selection_refs()
                    self.redraw()
                else:  # kind == "clip" (linked)
                    raw_tl_s = max(0.0, self._drag_orig_tl_s + dt_sec)
                    snapped_tl_s, guide = self._snap_time(raw_tl_s, ignore_ref=("clip", idx))
                    self._snap_guide_sec = guide
                    new_idx = self.nle.move_clip_to_time(idx, snapped_tl_s, push_undo=False)
                    if self.nle.clips[new_idx].get("audio_tl_start") is not None:
                        self.nle.clips[new_idx]["audio_tl_start"] = round(max(0.0, self._drag_orig_audio_tl_s + dt_sec), 3)
                    self._drag_target = (kind, new_idx)
                    self.selected_ref = (kind, new_idx)
                    self._sync_selection_refs()
                    self.redraw()

    def _on_release(self, event):
        act = self._drag_action
        self._drag_action = None
        self._snap_guide_sec = None

        if act == "reorder_track":
            self.canvas.delete("reorder_guide")
            self.canvas.configure(cursor="arrow")
            if self._drag_moved:
                dest_tkey = self._y_to_track(event.y)
                if dest_tkey and dest_tkey != "RULER":
                    self._reorder_track_to(self._drag_track_key, dest_tkey, event.y)
            return
        elif act == "marquee":
            self.canvas.delete("marquee_box")
            if not self._drag_moved:
                sec = self._x_to_sec(max(self.HEADER_W, event.x))
                self.playhead_sec = sec
                self.redraw()
                self.on_scrub(sec, True)
            else:
                self.redraw()
            return
        elif act == "move_multi":
            self.nle.recompute_timeline(pack_gaps=False)
            self.on_modified()
            self._sync_selection_refs()
            self.redraw()
            return
        elif act == "scrub":
            sec = self._x_to_sec(max(self.HEADER_W, event.x))
            self.playhead_sec = sec
            self.redraw()
            self.on_scrub(sec, True)
        elif act == "move_or_click_clip" and not self._drag_moved:
            sec = self._x_to_sec(max(self.HEADER_W, event.x))
            self.playhead_sec = sec
            self.redraw()
            self.on_scrub(sec, True)
            if self.selected_ref:
                self.on_select(self.selected_ref)
        elif act:
            self.on_modified()
            if self.selected_ref:
                self.on_select(self.selected_ref)
            self.redraw()

    def _on_hover(self, event):
        mx, my = event.x, event.y
        ar = self._is_ar()
        tip = getattr(self, "_canvas_tip", None)

        # 1. Left Track Headers Area
        if mx < self.HEADER_W:
            if self._hover_blade_sec is not None:
                self._hover_blade_sec = None
                if not self._update_blade_preview_fast():
                    self.redraw()
            tkey = self._y_to_track(my)
            if not tkey or tkey == "RULER":
                self.canvas.configure(cursor="arrow")
                if tip:
                    tip.hide()
                return

            tspec = next((t for t in self.track_specs if t[0] == tkey), None)
            lbl = (tspec[4] if ar else tspec[5]) if tspec else tkey
            en = self.nle.track_enabled.get(tkey, True)
            is_locked = bool(hasattr(self.nle, "is_track_locked") and self.nle.is_track_locked(tkey))

            if 6 <= mx <= 35:
                # Eye / Mute toggle
                self.canvas.configure(cursor="hand2")
                if tkey == "A1":
                    txt_ar = "🔊 انقر لكتم صوت الفيديو الأصلي (A1)" if en else "🔇 انقر لتفعيل وتشغيل صوت الفيديو الأصلي (A1)"
                    txt_en = "🔊 Click to Mute Original Audio (A1)" if en else "🔇 Click to Unmute Original Audio (A1)"
                elif tkey in ("A2", "AUD") or tkey.startswith("AUD"):
                    txt_ar = f"🔊 انقر لكتم مسار الصوت ({lbl})" if en else f"🔇 انقر لتفعيل مسار الصوت ({lbl})"
                    txt_en = f"🔊 Click to Mute Audio Track ({lbl})" if en else f"🔇 Click to Unmute Audio Track ({lbl})"
                elif tkey == "V1":
                    txt_ar = "👁️ انقر لإخفاء مسار الفيديو (V1)" if en else "🚫 انقر لإظهار مسار الفيديو (V1)"
                    txt_en = "👁️ Click to Hide Video Track (V1)" if en else "🚫 Click to Show Video Track (V1)"
                else:
                    txt_ar = f"👁️ انقر لإخفاء طبقة ({lbl})" if en else f"🚫 انقر لإظهار طبقة ({lbl})"
                    txt_en = f"👁️ Click to Hide Track ({lbl})" if en else f"🚫 Click to Show Track ({lbl})"
                if tip:
                    tip.show(txt_ar, txt_en, event.x_root, event.y_root)
            elif self.HEADER_W - 45 <= mx < self.HEADER_W - 23:
                # Lock toggle
                self.canvas.configure(cursor="hand2")
                txt_ar = f"🔒 مسار ({lbl}) مقفول ضد التعديل والقص\n💡 انقر لإلغاء القفل" if is_locked else f"🔓 مسار ({lbl}) مفتوح للتعديل\n💡 انقر لقفل المسار لمنع التعديل والقص بالخطأ"
                txt_en = f"🔒 Track ({lbl}) is Locked against edits\n💡 Click to unlock" if is_locked else f"🔓 Track ({lbl}) is Unlocked\n💡 Click to lock track"
                if tip:
                    tip.show(txt_ar, txt_en, event.x_root, event.y_root)
            elif mx >= self.HEADER_W - 23:
                # Action [+] button
                self.canvas.configure(cursor="hand2")
                if tkey == "V1":
                    txt_ar = "✂️ تقسيم الفيديو عند المؤشر (Ctrl+B)"
                    txt_en = "✂️ Split video at playhead (Ctrl+B)"
                elif tkey == "A1":
                    txt_ar = "🔇 كتم المقاطع الصامتة تلقائياً أو تقسيم مسار الصوت"
                    txt_en = "🔇 Auto-mute silence or split audio"
                elif tkey == "A2" or tkey.startswith("AUD"):
                    txt_ar = "🎵 إضافة ملف صوتي جديد (موسيقى / مؤثرات)"
                    txt_en = "🎵 Add new audio file (music / SFX)"
                elif tkey == "V2" or tkey.startswith("MED"):
                    txt_ar = "⭐ إضافة أيقونة أو شارة أو صورة خارجية عند المؤشر"
                    txt_en = "⭐ Add icon badge or image at playhead"
                elif tkey == "V3" or tkey.startswith("TXT"):
                    txt_ar = "📝 إضافة نص أو ترجمة متحركة عند المؤشر"
                    txt_en = "📝 Add animated text or subtitle at playhead"
                elif tkey == "V4" or tkey.startswith("LOG"):
                    txt_ar = "🛡️ إضافة شعار أو علامة مائية عند المؤشر"
                    txt_en = "🛡️ Add logo or watermark at playhead"
                else:
                    txt_ar = f"➕ إضافة عنصر جديد إلى مسار ({lbl})"
                    txt_en = f"➕ Add item to track ({lbl})"
                if tip:
                    tip.show(txt_ar, txt_en, event.x_root, event.y_root)
            else:
                # Track header label (reorder drag handle)
                self.canvas.configure(cursor="sb_v_double_arrow")
                txt_ar = f"↕️ اضغط واسحب للأعلى أو للأسفل لتغيير ترتيب مسار ({lbl})\n💡 أو انقر بزر الفأرة الأيمن لخيارات الطبقة"
                txt_en = f"↕️ Click and Drag Up/Down to reorder track ({lbl})\n💡 Or Right-click for track options"
                if tip:
                    tip.show(txt_ar, txt_en, event.x_root, event.y_root)
            return

        # 2. Ruler or Playhead Area
        tot_dur = max(0.3, self.nle.total_duration)
        _vw, tot_px = self._viewport_metrics()
        px = self._sec_to_x(self.playhead_sec, tot_dur, tot_px)

        if my <= self.RULER_H:
            self.canvas.configure(cursor="hand2")
            if abs(mx - px) <= 9:
                txt_ar = f"🔴 مؤشر التشغيل (Playhead: {self._fmt_tc(self.playhead_sec, 'hundredth')})\n💡 اسحب للتمرير والتحرك الدقيق عبر الفيديو"
                txt_en = f"🔴 Playhead ({self._fmt_tc(self.playhead_sec, 'hundredth')})\n💡 Drag to scrub precisely"
            else:
                cur_s = self._x_to_sec(mx)
                txt_ar = f"⏱️ المسطرة الزمنية ({self._fmt_tc(cur_s, 'tenth')})\n💡 انقر للتنقل السريع للمؤشر، أو اسحب للمسح"
                txt_en = f"⏱️ Timeline Ruler ({self._fmt_tc(cur_s, 'tenth')})\n💡 Click or scrub playhead"
            if tip:
                tip.show(txt_ar, txt_en, event.x_root, event.y_root)
            return

        # 3. Transition Placement Tool Mode
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
                    lbl_txt = f"🪄 انقر لوضع الانتقال على القطع #{cut_idx+1}" if ar else f"🪄 Click to Place on Cut #{cut_idx+1}"
                    bid = c.create_rectangle(cut_x - 72, v1_y0 + 6, cut_x + 72, v1_y0 + 26, fill="#0d2d1f", outline="#00e5ff", width=2)
                    tid = c.create_text(cut_x, v1_y0 + 16, text=lbl_txt, fill="#b7f5cb", font=("Segoe UI", 8, "bold"))
                    self._trans_guide_ids.extend([lid, bid, tid])
                if tip:
                    tip.show(f"🪄 انقر لوضع الانتقال المختار على القطع #{cut_idx+1}", f"🪄 Click to place transition on cut #{cut_idx+1}", event.x_root, event.y_root)
            elif tip:
                tip.hide()
            return

        # 4. Blade / Razor Mode
        if self.tool_mode == "blade":
            self.canvas.configure(cursor="crosshair")
            sec = self._x_to_sec(mx)
            self._hover_blade_sec = sec
            if not self._update_blade_preview_fast():
                self.redraw()
            if tip:
                tip.show(f"✂️ شفرة القص الدقيق ({self._fmt_tc(sec, 'hundredth')})\n💡 انقر لقص وتقسيم المقطع هنا فوراً", f"✂️ Razor Blade Tool ({self._fmt_tc(sec, 'hundredth')})\n💡 Click to split clip at this exact frame", event.x_root, event.y_root)
            return

        # 5. Check Cut Seams
        cut_hit = self._hit_test_cut_seam(mx, my, tol=14.0)
        if cut_hit is not None:
            self.canvas.configure(cursor="hand2")
            cut_idx, _kx, has_trans, t_key, t_dur = cut_hit
            if has_trans:
                t_info = get_transition_info(t_key)
                t_lbl = t_info.get("label_ar") if ar else t_info.get("label_en")
                txt_ar = f"✨ انتقال سينمائي ({t_lbl} - {t_dur:.2f}s) على القطع #{cut_idx+1}\n💡 انقر بزر الفأرة الأيمن لتغيير الانتقال أو إزالته"
                txt_en = f"✨ Transition ({t_lbl} - {t_dur:.2f}s) on Cut #{cut_idx+1}\n💡 Right-click to edit or remove"
            else:
                txt_ar = f"✂️ فاصل قطع بين المقاطع #{cut_idx+1}\n💡 انقر بزر الفأرة الأيمن لإضافة انتقال أو اسحب انتقالاً إليه"
                txt_en = f"✂️ Cut seam between clips #{cut_idx+1}\n💡 Right-click to add transition or drag one here"
            if tip:
                tip.show(txt_ar, txt_en, event.x_root, event.y_root)
            return

        # 6. Check Clips and Overlay Items
        hit_ref, part = self._hit_test(mx, my)
        if hit_ref:
            kind, idx = hit_ref
            if part in ("left", "right"):
                self.canvas.configure(cursor="sb_h_double_arrow")
                if part == "left":
                    txt_ar = "↔️ تقليم بداية المقطع (Trim In)\n💡 اضغط واسحب لتغيير بداية المقطع"
                    txt_en = "↔️ Trim Clip Start (Trim In)\n💡 Drag to trim in-point"
                else:
                    txt_ar = "↔️ تقليم نهاية المقطع (Trim Out)\n💡 اضغط واسحب لتغيير نهاية المقطع"
                    txt_en = "↔️ Trim Clip End (Trim Out)\n💡 Drag to trim out-point"
                if tip:
                    tip.show(txt_ar, txt_en, event.x_root, event.y_root)
                return

            self.canvas.configure(cursor="fleur")
            if kind in ("clip", "V1_clip", "A1_clip"):
                cl = self.nle.clips[idx] if (0 <= idx < len(self.nle.clips)) else None
                if cl:
                    tl_s = float(cl.get("tl_start", 0.0))
                    tl_e = float(cl.get("tl_end", tl_s + 1.0))
                    dur = max(0.0, tl_e - tl_s)
                    spd = float(cl.get("speed", 1.0))
                    spd_txt = f" | السرعة: {spd:.2g}x" if abs(spd - 1.0) > 0.02 else ""
                    c_name = cl.get("name", f"Clip #{idx+1}")
                    if kind == "V1_clip":
                        txt_ar = f"🎬 مسار الفيديو الرئيسي V1: {c_name}\n⏱️ البداية: {tl_s:.2f}s | المدة: {dur:.2f}s{spd_txt}\n💡 انقر لتعديل أبعاد أو ألوان الفيديو، أو اسحب للتحريك"
                        txt_en = f"🎬 Video Track V1: {c_name}\n⏱️ Start: {tl_s:.2f}s | Dur: {dur:.2f}s{spd_txt}\n💡 Click to edit crop/color/speed, or drag to move"
                    elif kind == "A1_clip":
                        txt_ar = f"🔊 مسار صوت الفيديو الأصلي A1: {c_name}\n⏱️ البداية: {tl_s:.2f}s | المدة: {dur:.2f}s\n💡 انقر لتعديل الصوت والمؤثرات أو الكتم، أو اسحب للتحريك"
                        txt_en = f"🔊 Video Original Audio A1: {c_name}\n⏱️ Start: {tl_s:.2f}s | Dur: {dur:.2f}s\n💡 Click to edit volume/EQ or mute, or drag to move"
                    else:
                        txt_ar = f"🎬 مقطع فيديو وصوت مرتبطين: {c_name}\n⏱️ البداية: {tl_s:.2f}s | المدة: {dur:.2f}s{spd_txt}\n💡 انقر للتحديد والتعديل، أو افصل الصوت بزر التثبيت بالأعلى"
                        txt_en = f"🎬 Linked Video & Audio Clip: {c_name}\n⏱️ Start: {tl_s:.2f}s | Dur: {dur:.2f}s{spd_txt}\n💡 Click to select, or unlink via toolbar button"
                    if tip:
                        tip.show(txt_ar, txt_en, event.x_root, event.y_root)
                    return
            else:
                t_list = self.nle.get_track_list(kind)
                it = t_list[idx] if (0 <= idx < len(t_list)) else None
                if it:
                    lbl = self._overlay_display_label(kind, it, ar)
                    is_full = bool(it.get("full_duration", False))
                    dur_lbl = ("كامل مدة الفيديو (∞)" if ar else "Full Duration (∞)") if is_full else f"{float(it.get('start_sec', 0.0)):.2f}s → {float(it.get('end_sec', 0.0)):.2f}s"
                    txt_ar = f"📌 {lbl}\n⏱️ التوقيت: {dur_lbl}\n💡 انقر للتحديد والتعديل، أو اسحب للتحريك والتقليم"
                    txt_en = f"📌 {lbl}\n⏱️ Timing: {dur_lbl}\n💡 Click to select/edit, or drag to move/trim"
                    if tip:
                        tip.show(txt_ar, txt_en, event.x_root, event.y_root)
                    return

        # 7. Check Gaps
        for gs, ge, gx0, gx1 in self._gap_hit_boxes:
            if gx0 <= mx <= gx1:
                self.canvas.configure(cursor="hand2")
                g_dur = ge - gs
                txt_ar = f"↔️ فجوة زمنية فارغة ({g_dur:.2f}s)\n💡 انقر بزر الفأرة الأيمن لحذف الفجوة وتقريب المقاطع (Ripple Delete)"
                txt_en = f"↔️ Empty Gap ({g_dur:.2f}s)\n💡 Right-click to ripple delete this gap"
                if tip:
                    tip.show(txt_ar, txt_en, event.x_root, event.y_root)
                return

        # 8. Empty Timeline Canvas Space
        self.canvas.configure(cursor="arrow")
        if tip:
            tip.hide()

    def _on_leave(self, _e):
        if hasattr(self, "_canvas_tip"):
            self._canvas_tip.hide()
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
        ar = self._is_ar()
        if mx < self.HEADER_W:
            tkey = self._y_to_track(my)
            if not tkey or tkey == "RULER":
                return
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(
                label="➕ " + ("إضافة عنصر في هذه الطبقة" if ar else "Add Item to This Track"),
                command=lambda: self._handle_header_click(event, tkey),
            )
            en = self.nle.track_enabled.get(tkey, True)
            menu.add_command(
                label=("🚫 إخفاء هذه الطبقة" if en else "👁️ إظهار هذه الطبقة") if ar else ("🚫 Hide Track" if en else "👁️ Show Track"),
                command=lambda: self._toggle_track_visibility(tkey),
            )
            menu.add_separator()
            menu.add_command(
                label="⬆️ " + ("تحريك الطبقة لأعلى" if ar else "Move Track Up"),
                command=lambda: self.move_track_up(tkey),
            )
            menu.add_command(
                label="⬇️ " + ("تحريك الطبقة لأسفل" if ar else "Move Track Down"),
                command=lambda: self.move_track_down(tkey),
            )
            menu.add_command(
                label="🔄 " + ("إعادة الترتيب الافتراضي للمسارات" if ar else "Reset Default Track Order"),
                command=self.reset_default_track_order,
            )
            if tkey not in ("V1", "A1"):
                menu.add_separator()
                menu.add_command(
                    label="🗑️ " + ("حذف هذه الطبقة" if ar else "Delete This Track"),
                    command=lambda: self.delete_track(tkey),
                )
            menu.add_separator()
            compact_lbl = ("تكبير ارتفاع الطبقات" if self.is_compact_tracks else "تصغير ارتفاع الطبقات (الوضع المضغوط)") if ar else ("Expand Track Heights" if self.is_compact_tracks else "Compact Track Heights")
            menu.add_command(
                label="📐 " + compact_lbl,
                command=self.toggle_compact_tracks,
            )
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
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
        if getattr(self, "_clipboard_items", None):
            menu.add_command(
                label="📌 " + ("لصق عند المؤشر (Ctrl+V)" if ar else "Paste at Playhead (Ctrl+V)"),
                command=self.paste_at_playhead,
            )
        if self.selected_ref or getattr(self, "selected_items", None):
            menu.add_command(
                label="📄 " + ("نسخ المحدد (Ctrl+C)" if ar else "Copy Selected (Ctrl+C)"),
                command=self.copy_selected,
            )
            menu.add_command(
                label="📋 " + ("تكرار المحدد" if ar else "Duplicate Selected"),
                command=self.duplicate_selected,
            )
            if self.selected_ref and self.selected_ref[0] in ("clip", "V1_clip", "A1_clip"):
                c_idx = self.selected_ref[1]
                if 0 <= c_idx < len(self.nle.clips):
                    is_linked = getattr(self, "linked_selection", True)
                    menu.add_command(
                        label="⛓️ " + ("فصل مسار الفيديو عن الصوت" if ar else "Unlink Video & Audio") if is_linked else "🔗 " + ("ربط مسار الفيديو بالصوت" if ar else "Link Video & Audio"),
                        command=self.toggle_linked_selection,
                    )
                    is_m = self.nle.clips[c_idx].get("muted", False)
                    m_lbl = ("🔊 تشغيل صوت هذا المقطع" if is_m else "🔇 كتم صوت هذا المقطع") if ar else ("🔊 Unmute Clip" if is_m else "🔇 Mute Clip")
                    menu.add_command(label=m_lbl, command=lambda: self._toggle_clip_mute(c_idx))

                    has_a_offset = bool(self.nle.clips[c_idx].get("audio_tl_start") is not None)
                    if has_a_offset:
                        menu.add_command(
                            label="🎯 " + ("إعادة محاذاة الصوت مع الفيديو تلقائياً" if ar else "Re-align Audio with Video"),
                            command=lambda ci=c_idx: self._realign_clip_audio(ci),
                        )

                    # Multi-selection merge (when multiple clips are selected via Ctrl/Shift+Click)
                    sel_indices = sorted(list(getattr(self, "selected_clip_indices", set())))
                    if len(sel_indices) > 1 and c_idx in sel_indices:
                        if sel_indices == list(range(sel_indices[0], sel_indices[-1] + 1)):
                            menu.add_command(
                                label="⚡ " + (f"دمج ولحام المقاطع المحددة ({len(sel_indices)} مقاطع)" if ar else f"Merge Selected ({len(sel_indices)} Clips)"),
                                command=lambda: self._join_clips_action(sel_indices),
                            )

                    # Neighbor merge commands
                    if c_idx < len(self.nle.clips) - 1:
                        menu.add_command(
                            label="⚡ " + ("دمج ولحام مع المقطع التالي" if ar else "Merge with Next Clip"),
                            command=lambda ci=c_idx: self._join_clips_action([ci, ci + 1]),
                        )
                    if c_idx > 0:
                        menu.add_command(
                            label="⚡ " + ("دمج ولحام مع المقطع السابق" if ar else "Merge with Previous Clip"),
                            command=lambda ci=c_idx: self._join_clips_action([ci - 1, ci]),
                        )
                    if self.nle.clips[c_idx].get("sub_clips"):
                        menu.add_command(
                            label="⚡ " + ("فك دمج هذا المقطع (استعادة المقاطع منفصلة)" if ar else "Unmerge Compound Clip"),
                            command=lambda ci=c_idx: self._unmerge_clip_action(ci),
                        )

                    menu.add_command(
                        label="✨ " + ("تعديل حركة الانتقال (Transitions)..." if ar else "Edit Video Transition..."),
                        command=lambda ci=c_idx: self._open_transition_editor(ci),
                    )
                    if self.on_export_clip:
                        menu.add_command(
                            label="🚀 " + ("تصدير هذا المقطع المحدد..." if ar else "Export This Selected Clip..."),
                            command=lambda ci=c_idx: self.on_export_clip(ci),
                        )
                    if getattr(self, "on_export_all_clips", None) and hasattr(self, "nle") and len(self.nle.clips) > 1:
                        menu.add_command(
                            label="📂 " + (f"تصدير جميع المقاطع كلٌ في ملف مستقل ({len(self.nle.clips)} مقاطع)..." if ar else f"Export All Clips Separately ({len(self.nle.clips)} clips)..."),
                            command=self.on_export_all_clips,
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
        menu.add_separator()
        menu.add_command(
            label="💡 " + ("دليل الاختصارات والتعليمات الشامل..." if ar else "Shortcuts & Application Guide..."),
            command=self.open_shortcuts_guide,
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

    def _realign_clip_audio(self, clip_idx: int):
        if 0 <= clip_idx < len(self.nle.clips):
            self.nle.push_undo()
            cl = self.nle.clips[clip_idx]
            cl.pop("audio_tl_start", None)
            cl.pop("audio_tl_dur", None)
            cl.pop("audio_src_start", None)
            cl.pop("audio_src_end", None)
            self.on_modified()
            self.redraw()
            ar = self._is_ar()
            self.show_hud_toast("🎯 تم إعادة محاذاة الصوت مع الفيديو بنجاح" if ar else "🎯 Audio re-aligned with video successfully")

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

    def _join_clips_action(self, indices: List[int]):
        ar = self._is_ar()
        res_idx = self.nle.join_clips(indices)
        if res_idx is not None:
            self.selected_clip_indices = {res_idx}
            self.selected_ref = ("clip", res_idx)
            self.on_select(self.selected_ref)
            self.on_modified()
            self.redraw()
            self.show_hud_toast("⚡ تم دمج ولحام المقاطع بنجاح" if ar else "⚡ Clips joined into single clip successfully")
            app = getattr(self, "parent", None)
            while app and not hasattr(app, "_refresh_master_export_summary"):
                app = getattr(app, "parent", None)
            if app and hasattr(app, "_refresh_master_export_summary"):
                app._refresh_master_export_summary()

    def _unmerge_clip_action(self, clip_idx: int):
        ar = self._is_ar()
        if self.nle.unmerge_clip(clip_idx):
            self.selected_clip_indices = {clip_idx}
            self.selected_ref = ("clip", clip_idx)
            self.on_select(self.selected_ref)
            self.on_modified()
            self.redraw()
            self.show_hud_toast("⚡ تم فك دمج المقطع واستعادة المقاطع" if ar else "⚡ Compound clip unmerged successfully")
            app = getattr(self, "parent", None)
            while app and not hasattr(app, "_refresh_master_export_summary"):
                app = getattr(app, "parent", None)
            if app and hasattr(app, "_refresh_master_export_summary"):
                app._refresh_master_export_summary()
