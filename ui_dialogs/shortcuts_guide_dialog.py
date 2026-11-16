"""
Comprehensive Application & Timeline Shortcuts and User Guide Dialog
Provides structured tabs for Keyboard Shortcuts, Mouse Gestures,
Video Studio & NLE Operations, Overlays, and Master Export.
Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional, Tuple


class ShortcutsGuideDialog(tk.Toplevel):
    def __init__(self, parent, is_ar_fn: Optional[Callable[[], bool]] = None, is_ar: Optional[bool] = None):
        super().__init__(parent)
        if is_ar is not None:
            self.is_ar = bool(is_ar)
            self.is_ar_fn = lambda: self.is_ar
        elif callable(is_ar_fn):
            self.is_ar_fn = is_ar_fn
            self.is_ar = bool(is_ar_fn())
        elif isinstance(is_ar_fn, bool):
            self.is_ar = is_ar_fn
            self.is_ar_fn = lambda: self.is_ar
        else:
            self.is_ar = True
            self.is_ar_fn = lambda: True

        title_text = "دليل الاختصارات والتعليمات الشامل للبرنامج" if self.is_ar else "Comprehensive Shortcuts & Application Guide"
        self.title(title_text)
        self.geometry("860x620")
        self.minsize(720, 500)
        self.configure(bg="#12151c")
        self.transient(parent)

        self._build_ui()
        self._center_window(parent)
        try:
            self.grab_set()
        except Exception:
            pass
        try:
            self.focus_set()
        except Exception:
            pass

    def _check_ar(self) -> bool:
        try:
            return bool(self.is_ar_fn())
        except Exception:
            return True

    def _center_window(self, parent):
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        w = self.winfo_width()
        h = self.winfo_height()
        x = max(20, px + (pw - w) // 2)
        y = max(20, py + (ph - h) // 2)
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # ---------------- Header Bar ----------------
        hdr = tk.Frame(self, bg="#1a1f2c", padx=16, pady=12, highlightthickness=1, highlightbackground="#2e384d")
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.columnconfigure(1, weight=1)

        tk.Label(
            hdr,
            text="⌨️",
            font=("Segoe UI", 20),
            bg="#1a1f2c",
            fg="#58a6ff",
        ).pack(side="left" if not self.is_ar else "right", padx=(0, 10) if not self.is_ar else (10, 0))

        title_frame = tk.Frame(hdr, bg="#1a1f2c")
        title_frame.pack(side="left" if not self.is_ar else "right", fill="both", expand=True)

        main_title = "دليل استخدام واختصارات استديو المونتاج والبرنامج" if self.is_ar else "Video Studio & App Shortcuts Guide"
        sub_title = "مرجع سريع لجميع مفاتيح الاختصار، حركات الفأرة، والوظائف الاحترافية" if self.is_ar else "Quick reference for all keyboard shortcuts, mouse gestures, and pro features"

        tk.Label(
            title_frame,
            text=main_title,
            font=("Segoe UI", 12, "bold"),
            bg="#1a1f2c",
            fg="#ffffff",
            anchor="w" if not self.is_ar else "e",
        ).pack(fill="x")

        tk.Label(
            title_frame,
            text=sub_title,
            font=("Segoe UI", 9),
            bg="#1a1f2c",
            fg="#8b949e",
            anchor="w" if not self.is_ar else "e",
        ).pack(fill="x")

        # ---------------- Tabs Container ----------------
        nb = ttk.Notebook(self)
        nb.grid(row=1, column=0, sticky="nsew", padx=14, pady=10)

        # Tab 1: Keyboard Shortcuts
        tab_keys = ttk.Frame(nb, padding=12)
        nb.add(tab_keys, text="⌨️ " + ("اختصارات الكيبورد" if self.is_ar else "Keyboard Shortcuts"))
        self._build_shortcuts_tab(tab_keys)

        # Tab 2: Mouse Gestures & Timeline
        tab_mouse = ttk.Frame(nb, padding=12)
        nb.add(tab_mouse, text="🖱️ " + ("حركات الفأرة والتايم لاين" if self.is_ar else "Mouse & Timeline Controls"))
        self._build_mouse_tab(tab_mouse)

        # Tab 3: Studio & Editing Features
        tab_studio = ttk.Frame(nb, padding=12)
        nb.add(tab_studio, text="🎬 " + ("دليل المونتاج والتقطيع" if self.is_ar else "Editing & Studio Guide"))
        self._build_studio_tab(tab_studio)

        # Tab 4: Overlays & Branding (Text, Media, Logo)
        tab_brand = ttk.Frame(nb, padding=12)
        nb.add(tab_brand, text="🎨 " + ("النصوص والوسائط والشعار" if self.is_ar else "Overlays & Branding"))
        self._build_brand_tab(tab_brand)

        # Tab 5: Silence Detection & Master Export
        tab_export = ttk.Frame(nb, padding=12)
        nb.add(tab_export, text="⚡ " + ("السكتات والتصدير" if self.is_ar else "Silence & Export Guide"))
        self._build_export_tab(tab_export)

        # ---------------- Footer Bar ----------------
        footer = tk.Frame(self, bg="#161a23", padx=16, pady=10, highlightthickness=1, highlightbackground="#2e384d")
        footer.grid(row=2, column=0, sticky="ew")

        btn_close = tk.Button(
            footer,
            text="✖️ " + ("إغلاق الدليل" if self.is_ar else "Close Guide"),
            command=self.destroy,
            bg="#21262d",
            fg="#ffffff",
            activebackground="#30363d",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=16,
            pady=6,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        )
        btn_close.pack(side="right" if not self.is_ar else "left")

        tip_lbl = "💡 نصيحة: يمكنك النقر على Ctrl+C لنسخ أي عنصر محدد ولصقه بـ Ctrl+V عند المؤشر!" if self.is_ar else "💡 Pro Tip: Press Ctrl+C to copy selected clips/overlays, then Ctrl+V to paste at playhead!"
        tk.Label(
            footer,
            text=tip_lbl,
            bg="#161a23",
            fg="#58a6ff",
            font=("Segoe UI", 9),
        ).pack(side="left" if not self.is_ar else "right", padx=8)

    def _create_scrollable_area(self, parent):
        canvas = tk.Canvas(parent, bg="#12151c", highlightthickness=0)
        v_scroll = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg="#12151c")

        content.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        c_win = canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(c_win, width=e.width))

        canvas.configure(yscrollcommand=v_scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")
        return content

    def _render_shortcut_row(self, parent, key_badge: str, title: str, desc: str, bg="#181c26"):
        row = tk.Frame(parent, bg=bg, padx=10, pady=7, highlightthickness=1, highlightbackground="#272d3b")
        row.pack(fill="x", pady=2)
        row.columnconfigure(1, weight=1)

        # Key Badge
        badge = tk.Label(
            row,
            text=f" {key_badge} ",
            bg="#2d333b",
            fg="#58a6ff",
            font=("Consolas", 10, "bold"),
            relief="solid",
            bd=1,
            padx=6,
            pady=2,
        )
        badge.pack(side="left" if not self.is_ar else "right", padx=6)

        txt_frame = tk.Frame(row, bg=bg)
        txt_frame.pack(side="left" if not self.is_ar else "right", fill="both", expand=True, padx=8)

        tk.Label(
            txt_frame,
            text=title,
            font=("Segoe UI", 9, "bold"),
            bg=bg,
            fg="#e6edf3",
            anchor="w" if not self.is_ar else "e",
        ).pack(fill="x")

        tk.Label(
            txt_frame,
            text=desc,
            font=("Segoe UI", 8),
            bg=bg,
            fg="#8b949e",
            anchor="w" if not self.is_ar else "e",
        ).pack(fill="x")

    def _build_shortcuts_tab(self, parent):
        content = self._create_scrollable_area(parent)
        ar = self.is_ar

        shortcuts = [
            ("Ctrl + C", "نسخ العناصر المحددة" if ar else "Copy Selected Items", "نسخ أي مقاطع فيديو، نصوص، صور، أو لوجو محددة في الحافظة" if ar else "Copy any selected clips, text, media, or logo items to clipboard"),
            ("Ctrl + V", "لصق عند مؤشر التشغيل" if ar else "Paste at Playhead", "لصق العناصر المنسوخة عند توقيت المؤشر الحالي مع الحفاظ على المسافات النسبية" if ar else "Paste copied items at current playhead position preserving relative offsets"),
            ("Ctrl + A", "تحديد الكل" if ar else "Select All", "تحديد جميع مقاطع الفيديو وجميع عناصر الطبقات دفعة واحدة" if ar else "Select every single clip, title, and overlay on the timeline simultaneously"),
            ("Delete / Backspace", "حذف المحدد" if ar else "Delete Selected", "حذف كافة العناصر المحددة معاً في خطوة تراجع واحدة" if ar else "Atomically delete all currently selected clips and overlay items with Undo support"),
            ("Ctrl + Z", "تراجع (Undo)" if ar else "Undo", "التراجع عن آخر حركة، قص، حذف، إضافة، أو تعديل" if ar else "Undo the last action (cut, move, trim, delete, layer addition)"),
            ("Ctrl + Y", "إعادة (Redo)" if ar else "Redo", "إعادة تطبيق العملية المتراجع عنها" if ar else "Redo the previously undone action"),
            ("A", "أداة التحديد العادية" if ar else "Select Tool (Arrow)", "الوضع الافتراضي لتحديد وسحب وقص أطراف المقاطع" if ar else "Default mode to click, drag, select, and edge-trim clips"),
            ("B", "أداة المقص السريع (Blade/Razor)" if ar else "Razor / Blade Tool", "تقسيم وقص أي مقطع أو نص مباشرة وبدقة متناهية بمجرد النقر عليه بالفأرة" if ar else "Split any clip or overlay element at the exact frame clicked"),
            ("S  أو  Ctrl + B", "قص عند المؤشر" if ar else "Split at Playhead", "قص وتقسيم المقطع الموجود تحت مؤشر التشغيل الأحمر فوراً" if ar else "Split the active clip or overlay under the red playhead immediately"),
            ("Space (المسافة)", "تشغيل / إيقاف مؤقت" if ar else "Play / Pause", "بدء أو إيقاف معاينة وتشغيل الفيديو مباشرة" if ar else "Play or pause live preview playback of the video"),
            ("Alt + عجلة الفأرة", "زوم فائق ودقيق حول الفأرة" if ar else "Precision Zoom (Alt + Wheel)", "تكبير وتصغير التايم لاين حتى 300 بكسل/ثانية لرؤية أجزاء الثانية والكلمات بدقة" if ar else "Zoom in/out up to 300 px/sec anchored around the mouse cursor position"),
            ("عجلة الفأرة فقط", "تمرير التايم لاين أفقياً" if ar else "Horizontal Scroll (Wheel)", "تحريك شريط التايم لاين يميناً ويساراً بسلاسة تامة" if ar else "Scroll horizontally left and right across the timeline without zooming"),
            ("F11", "ملء الشاشة الكاملة للتطبيق" if ar else "Toggle Fullscreen Mode", "تبديل وضع الشاشة الكاملة الأنيق (المس أسفل الشاشة لإظهار شريط النظام لـ 5 ثوانٍ)" if ar else "Toggle immersive fullscreen mode (hover bottom edge to reveal taskbar for 5s)"),
            ("Esc", "إلغاء أو إغلاق" if ar else "Escape", "إلغاء وضع ملء الشاشة أو إغلاق النوافذ المنبثقة" if ar else "Exit fullscreen preview or close current dialog"),
        ]

        for key, title, desc in shortcuts:
            self._render_shortcut_row(content, key, title, desc)

    def _build_mouse_tab(self, parent):
        content = self._create_scrollable_area(parent)
        ar = self.is_ar

        features = [
            ("📦 مستطيل التحديد (Marquee Box)", "انقر واسحب بالفأرة على أي مساحة فارغة في التايم لاين لتظهر علبة تحديد زرقاء شفافة؛ أي عنصر تلمسه العلبة يتم تحديده فوراً." if ar else "Click and drag on any empty timeline lane to draw a blue marquee box; all clips, texts, and icons intersected are selected."),
            ("🖱️ تحديد متعدد (Ctrl / Shift + Click)", "اضغط باستمرار على Ctrl أو Shift وانقر على أي عنصر لإضافته إلى مجموعة التحديد أو إزالته بحرية." if ar else "Hold Ctrl or Shift while clicking to add or remove individual clips, texts, or logos to/from multi-selection."),
            ("↔️ تحريك متزامن للمحدد", "عند تحديد عدة عناصر، اسحب أي عنصر منها ليتحرك الجميع معاً بنفس المسافة والتوقيت." if ar else "When multiple items are selected, dragging any one of them moves all selected items in lockstep."),
            ("📐 ضبط ارتفاع الطبقات (Compact Mode)", "زر '📐 تصغير الطبقات' يخفض ارتفاع الطبقات بنسبة ~42% لتناسب الشاشة براحة، مع أزرار '↕️-' و '↕️+' للضبط الدقيق." if ar else "Toggle Compact Mode to shrink track heights by ~42% so 8+ layers fit comfortably, plus ↕️- and ↕️+ for granular scaling."),
            ("🧲 المحاذاة المغناطيسية (Magnetic Snapping)", "عند سحب مقطع أو نص، يلتصق تلقائياً ببدايات ونهايات المقاطع الأخرى ومؤشر التشغيل مع خط دليل أحمر." if ar else "Items automatically snap to clip edges and playhead positions with an intuitive red guide line."),
            ("🪄 إدارة الانتقالات بين التقطيعات", "انقر كليك يمين على خط القطع بين أي مقطعين لاختيار ووضع انتقال سينمائي من مكتبة الـ 46 حركة احترافية." if ar else "Right-click any cut seam between clips to assign or change transitions from the 46+ transitions library."),
            ("🧲 إغلاق الفجوات الزمنية (Gaps)", "انقر كليك يمين على أي فجوة زمنية (Gap) في شريط الفيديو لاختيار إغلاقها فوراً أو ضم التايم لاين كاملاً." if ar else "Right-click any timeline gap between clips to instantly close it or close all timeline gaps at once."),
            ("📑 إدارة وتخصيص الطبقات", "انقر كليك يمين على عنوان أي طبقة (V2, V3, إلخ) لتحريكها لأعلى/لأسفل، إخفائها، أو حذفها بالكامل." if ar else "Right-click any track header on the left to move it up/down, toggle visibility, or delete the track."),
        ]

        for title, desc in features:
            self._render_card(content, title, desc)

    def _build_studio_tab(self, parent):
        content = self._create_scrollable_area(parent)
        ar = self.is_ar

        sections = [
            ("🎬 شاشة العرض التفاعلية (Interactive Canvas)", "عرض فوري للقطات مع خطوط إرشادية. يمكنك النقر على النصوص والشعارات لتحريكها وسحبها مباشرة على شاشة العرض." if ar else "Live video preview canvas with overlays. Click and drag text titles and logos directly on the player screen."),
            ("✂️ التقطيع الدقيق والفصل", "قسّم الفيديو بدقة عند أي ثانية باستخدام أداة المقص (B) أو زر القص (S). تظهر المقاطع بوضوح مع تمييز الأجزاء الصامتة." if ar else "Frame-accurate razor splitting using Blade (B) or Split (S). Compound clips preserve inner seam edit history."),
            ("🔗 دمج ولحام المقاطع (Compound Clips)", "حدد مقطعين متجاورين أو أكثر واضغط كليك يمين واختر 'دمج ولحام' لدمجهم في مقطع واحد مع إمكانية فك الدمج لاحقاً." if ar else "Select multiple adjacent clips, right-click and choose 'Merge Clips' into a single Compound Clip with full unmerge support."),
            ("📐 أبعاد ونسب الفيديو (Aspect Ratios)", "تحويل فوري لأبعاد الفيديو بضغطة زر واحدة:\n• 16:9 (يوتيوب وشاشات العرض)\n• 9:16 (تيك توك، ريلز، شورتس)\n• 1:1 (مربع انستجرام وفيسبوك)\n• 4:5 (منشورات البورتريه)" if ar else "Instant 1-click aspect ratio conversion:\n• 16:9 (YouTube & TV Landscape)\n• 9:16 (TikTok, Reels, Shorts Vertical)\n• 1:1 (Square)\n• 4:5 (Portrait Feed)"),
            ("🔊 التحكم في الصوت وموجات الصوت الخضراء (A1)", "عرض موجي فائق الدقة (Waveform) لطبقة الصوت. يمكنك كتم صوت أي مقطع محدد كليك يمين، أو ضبط مستوى الصوت والسرعة." if ar else "High-density green audio waveform track. Right-click any clip to mute/unmute, adjust speed (0.25x-4x), and volume."),
        ]

        for title, desc in sections:
            self._render_card(content, title, desc)

    def _build_brand_tab(self, parent):
        content = self._create_scrollable_area(parent)
        ar = self.is_ar

        sections = [
            ("📝 طبقات النصوص الاحترافية (Text+)", "إضافة عناوين نصوص ديناميكية في أي توقيت. تحكم كامل بالخطوط العربية والإنجليزية، حجم الخط، لون النص، ولون الخلفية والشفافية." if ar else "Add rich dynamic text titles at any playhead timestamp. Full control over fonts, sizes, colors, background box, and opacity."),
            ("⭐ الشارات والأيقونات الجاهزة (Pro Icons)", "مكتبة مدمجة للأيقونات التفاعلية: أزرار الاشتراك (Subscribe)، زر الإعجاب (Like)، جرس التنبيهات، وشارات التواصل الاجتماعي." if ar else "Built-in presets for animated stickers: Subscribe badges, Like buttons, Notification bells, and social icons."),
            ("🖼️ الصور الخارجية والشعارات (Custom Images)", "إمكانية إدراج صور خارجية بصيغة PNG شفافة أو JPG ووضعها فوق الفيديو في أي توقيت أو سحبها لتغطي كامل الفيديو." if ar else "Insert external PNG/JPG images or stickers anywhere on the timeline with custom position and scale."),
            ("🛡️ الشعار والعلامة المائية (Logo Watermark)", "إضافة لوجو القناة في الزوايا مع تثبيته طوال مدة الفيديو تلقائياً أو جعله يظهر في مقاطع محددة فقط." if ar else "Add your channel logo watermark with global full-duration pinning or per-clip timing options."),
            ("➕ إضافة مسارات إضافية ديناميكياً", "يمكنك عبر زر '➕ إضافة طبقة' إنشاء مسارات نصوص إضافية، مسارات وسائط، أو مسارات شعار لتنسيق المشاهد المعقدة." if ar else "Use '➕ Add Layer' button to dynamically spawn multiple independent text, media, or logo tracks."),
        ]

        for title, desc in sections:
            self._render_card(content, title, desc)

    def _build_export_tab(self, parent):
        content = self._create_scrollable_area(parent)
        ar = self.is_ar

        sections = [
            ("⚡ كشف وحذف السكتات تلقائياً (Auto Silence Detection)", "فحص فوري للموجات الصوتية واكتشاف لحظات الصمت والوقفات في الكلام، مع خيارين:\n1. فصل وحذف السكتات تلقائياً لضغط الفيديو وتسريع الكلام.\n2. تقسيم السكتات كمقاطع صامتة للمراجعة اليدوية والتعديل." if ar else "Detect speech vs silences automatically:\n1. Auto-cut & remove silences to tighten speech.\n2. Split silences as muted clips for manual review."),
            ("🎯 نطاقات وأنواع التصدير (Export Scopes)", "زر '🚀 تصدير الفيديو' يتيح لك 3 خيارات احترافية محددة بوضوح:\n• 🎬 تصدير الفيديو كاملاً بجميع التعديلات والطبقات (Full Timeline).\n• ✂️ تصدير هذا المقطع المحدد فقط (Selected Clip Only).\n• 📦 تصدير كل مقطع كفيديو منفصل دفعة واحدة (Batch Separate Clips)." if ar else "Master Export offers 3 dedicated scopes:\n• 🎬 Full Timeline Sequence (All clips & layers merged).\n• ✂️ Selected Clip Only.\n• 📦 Batch Export Every Clip Separately into individual files."),
            ("⚙️ جودة التصدير وسرعة المعالجة (GPU Acceleration)", "دعم المعالجة السريعة عبر كارت الشاشة (NVIDIA NVENC, AMD AMF, Intel QSV, Apple VideoToolbox) أو ترميز CPU عالي الجودة (x264/x265)." if ar else "Hardware-accelerated rendering (NVIDIA NVENC, AMD, Intel QSV) or high-quality CPU encoders (x264, x265, ProRes)."),
        ]

        for title, desc in sections:
            self._render_card(content, title, desc)

    def _render_card(self, parent, title: str, body: str):
        card = tk.Frame(parent, bg="#181c26", padx=12, pady=10, highlightthickness=1, highlightbackground="#272d3b")
        card.pack(fill="x", pady=4)

        tk.Label(
            card,
            text=title,
            font=("Segoe UI", 10, "bold"),
            bg="#181c26",
            fg="#79c0ff",
            anchor="w" if not self.is_ar else "e",
        ).pack(fill="x", pady=(0, 4))

        tk.Label(
            card,
            text=body,
            font=("Segoe UI", 9),
            bg="#181c26",
            fg="#c9d1d9",
            justify="left" if not self.is_ar else "right",
            anchor="w" if not self.is_ar else "e",
            wraplength=760,
        ).pack(fill="x")
