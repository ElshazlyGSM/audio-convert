"""
Pro Icons, Stickers & Social/Lecture Badges Picker Dialog
Displays live rendered thumbnails of built-in vector/Pillow icons with category filtering
and optional custom text for callout/subscribe badges.
Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

from video_studio.icons_library import ICON_PRESETS, render_icon_pil


class IconPickerDialog(tk.Toplevel):
    def __init__(self, parent, initial_key="subscribe_ar", initial_text=""):
        super().__init__(parent)
        self.parent = parent
        self.app = getattr(parent, "app", parent)
        self.is_ar = getattr(self.app, "language_var", tk.StringVar(value="العربية")).get() == "العربية"

        self.title("⭐ مكتبة الأيقونات والشارات الاحترافية" if self.is_ar else "⭐ Pro Icons & Badges Library")
        if hasattr(self.app, "_apply_theme_to_toplevel"):
            self.app._apply_theme_to_toplevel(self)
        self.geometry("760x580")
        self.minsize(660, 480)
        self.transient(parent)
        self.grab_set()

        self.result = None  # Dict {"icon_key": ..., "text": ...} when accepted
        self.selected_key = initial_key if initial_key in ICON_PRESETS else "subscribe_ar"
        self.category_var = tk.StringVar(value="all")
        self.custom_text_var = tk.StringVar(value=initial_text or "")
        self._thumb_refs = {}
        self._preview_photo = None
        self._card_frames = {}

        self._build_ui()
        self._populate_grid()
        self._refresh_preview()

        # Center on parent
        self.update_idletasks()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        dw = self.winfo_width()
        dh = self.winfo_height()
        self.geometry(f"+{max(20, px + (pw - dw) // 2)}+{max(20, py + (ph - dh) // 2)}")

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Top Category Filter Bar
        top_bar = ttk.Frame(self, padding=(12, 10, 12, 6))
        top_bar.grid(row=0, column=0, sticky="ew")

        cats = [
            ("all", "🌟 الكل" if self.is_ar else "🌟 All"),
            ("social", "📱 سوشيال واشتراك" if self.is_ar else "📱 Social & Subscribe"),
            ("lecture", "🕌 دروس ومحاضرات" if self.is_ar else "🕌 Lectures & Podcast"),
            ("shapes", "➡️ أسهم ورموز" if self.is_ar else "➡️ Arrows & Symbols"),
        ]
        for idx, (ckey, clabel) in enumerate(cats):
            rb = ttk.Radiobutton(
                top_bar,
                text=clabel,
                value=ckey,
                variable=self.category_var,
                command=self._populate_grid,
            )
            rb.grid(row=0, column=idx, padx=(0, 12), sticky="w")

        # Main Center Split: Left Scrollable Gallery | Right Live Preview & Custom Badge Text
        center = ttk.Frame(self, padding=(12, 4, 12, 8))
        center.grid(row=1, column=0, sticky="nsew")
        center.columnconfigure(0, weight=3)
        center.columnconfigure(1, weight=2, minsize=230)
        center.rowconfigure(0, weight=1)

        # Scrollable Canvas Grid
        gal_frame = ttk.Frame(center)
        gal_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        gal_frame.columnconfigure(0, weight=1)
        gal_frame.rowconfigure(0, weight=1)

        self.gal_canvas = tk.Canvas(gal_frame, bg="#12161f", highlightthickness=1, highlightbackground="#30363d")
        self.gal_scroll = ttk.Scrollbar(gal_frame, orient="vertical", command=self.gal_canvas.yview)
        self.gal_inner = tk.Frame(self.gal_canvas, bg="#12161f")

        self.gal_inner.bind(
            "<Configure>",
            lambda _e: self.gal_canvas.configure(scrollregion=self.gal_canvas.bbox("all")),
        )
        self._gal_win = self.gal_canvas.create_window((0, 0), window=self.gal_inner, anchor="nw")
        self.gal_canvas.bind(
            "<Configure>",
            lambda e: self.gal_canvas.itemconfigure(self._gal_win, width=e.width),
        )
        self.gal_canvas.configure(yscrollcommand=self.gal_scroll.set)
        self.gal_canvas.grid(row=0, column=0, sticky="nsew")
        self.gal_scroll.grid(row=0, column=1, sticky="ns")
        self.gal_canvas.bind("<MouseWheel>", lambda e: self.gal_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        # Right Live Preview & Badge Text Card
        right_card = ttk.LabelFrame(
            center,
            text="👁️ المعاينة وتخصيص الشارة" if self.is_ar else "👁️ Preview & Customize",
            padding=(10, 10, 10, 10),
        )
        right_card.grid(row=0, column=1, sticky="nsew")
        right_card.columnconfigure(0, weight=1)
        right_card.rowconfigure(0, weight=1)

        self.preview_canvas = tk.Canvas(right_card, bg="#0d1117", height=180, highlightthickness=1, highlightbackground="#30363d")
        self.preview_canvas.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        self.preview_canvas.bind("<Configure>", lambda _e: self._refresh_preview())

        self.sel_name_lbl = ttk.Label(right_card, text="", font=("Segoe UI", 9, "bold"), anchor="center")
        self.sel_name_lbl.grid(row=1, column=0, sticky="ew", pady=(0, 6))

        self.txt_lbl = ttk.Label(
            right_card,
            text="نص الشارة (للشارات النصية):" if self.is_ar else "Badge Text (optional):",
        )
        self.txt_lbl.grid(row=2, column=0, sticky="w", pady=(2, 2))
        self.txt_entry = ttk.Entry(right_card, textvariable=self.custom_text_var)
        self.txt_entry.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        self.custom_text_var.trace_add("write", lambda *_: self._refresh_preview())

        # Bottom Action Buttons
        bot = ttk.Frame(self, padding=(12, 6, 12, 12))
        bot.grid(row=2, column=0, sticky="ew")
        bot.columnconfigure(0, weight=1)

        ttk.Button(
            bot,
            text="إلغاء" if self.is_ar else "Cancel",
            command=self.destroy,
            style="Player.TButton",
            width=12,
        ).grid(row=0, column=1, padx=(0, 6))

        ttk.Button(
            bot,
            text="➕ إضافة للفيديو والشريط الزمني" if self.is_ar else "➕ Add to Video & Timeline",
            command=self._accept,
            style="Action.TButton",
        ).grid(row=0, column=2)

    def _populate_grid(self):
        for w in self.gal_inner.winfo_children():
            w.destroy()
        self._thumb_refs.clear()
        self._card_frames.clear()

        cat = self.category_var.get()
        items = [
            (k, v) for k, v in ICON_PRESETS.items()
            if cat == "all" or v.get("category") == cat
        ]

        cols = 3
        for c in range(cols):
            self.gal_inner.columnconfigure(c, weight=1)

        for idx, (ikey, info) in enumerate(items):
            r, c = divmod(idx, cols)
            is_sel = (ikey == self.selected_key)
            bg_col = "#1f3252" if is_sel else "#1a202c"
            bd_col = "#58a6ff" if is_sel else "#2d3748"

            card = tk.Frame(
                self.gal_inner,
                bg=bg_col,
                highlightthickness=2 if is_sel else 1,
                highlightbackground=bd_col,
                padx=6,
                pady=6,
                cursor="hand2",
            )
            card.grid(row=r, column=c, padx=5, pady=5, sticky="nsew")
            self._card_frames[ikey] = card

            thumb_w = 115 if info.get("kind") == "badge" else 68
            pil_im = render_icon_pil(ikey, target_width=thumb_w, is_ar=self.is_ar)
            if pil_im.height > 68:
                ratio = 68.0 / pil_im.height
                pil_im = pil_im.resize((max(16, int(pil_im.width * ratio)), 68), Image.Resampling.LANCZOS)
            ph_im = ImageTk.PhotoImage(pil_im)
            self._thumb_refs[ikey] = ph_im

            im_lbl = tk.Label(card, image=ph_im, bg=bg_col, cursor="hand2")
            im_lbl.pack(pady=(2, 4))

            title_txt = info.get("label_ar" if self.is_ar else "label_en", ikey)
            tx_lbl = tk.Label(card, text=title_txt, bg=bg_col, fg="#e6edf3", font=("Segoe UI", 8), wraplength=130, cursor="hand2")
            tx_lbl.pack()

            for widget in (card, im_lbl, tx_lbl):
                widget.bind("<Button-1>", lambda _e, k=ikey: self._select_icon(k))
                widget.bind("<Double-Button-1>", lambda _e, k=ikey: self._select_and_accept(k))

    def _select_icon(self, key: str):
        self.selected_key = key
        info = ICON_PRESETS.get(key, {})
        if info.get("kind") == "badge":
            default_t = info.get("default_text_ar" if self.is_ar else "default_text_en", "")
            self.custom_text_var.set(default_t)
            self.txt_entry.configure(state="normal")
        else:
            self.custom_text_var.set("")
            self.txt_entry.configure(state="disabled")

        for k, card in self._card_frames.items():
            is_sel = (k == key)
            bg_col = "#1f3252" if is_sel else "#1a202c"
            bd_col = "#58a6ff" if is_sel else "#2d3748"
            card.configure(bg=bg_col, highlightthickness=2 if is_sel else 1, highlightbackground=bd_col)
            for ch in card.winfo_children():
                ch.configure(bg=bg_col)

        self._refresh_preview()

    def _select_and_accept(self, key: str):
        self._select_icon(key)
        self._accept()

    def _refresh_preview(self):
        self.preview_canvas.delete("all")
        cw = max(120, self.preview_canvas.winfo_width())
        ch = max(100, self.preview_canvas.winfo_height())

        # Checkerboard subtle dark grid
        self.preview_canvas.create_rectangle(0, 0, cw, ch, fill="#0d1117", outline="")
        info = ICON_PRESETS.get(self.selected_key, {})
        self.sel_name_lbl.configure(text=info.get("label_ar" if self.is_ar else "label_en", self.selected_key))

        tw = int(cw * 0.80) if info.get("kind") == "badge" else int(min(cw, ch) * 0.62)
        pil_im = render_icon_pil(
            self.selected_key,
            custom_text=self.custom_text_var.get(),
            target_width=max(48, tw),
            is_ar=self.is_ar,
        )
        if pil_im.height > ch - 24:
            sc = (ch - 24) / float(pil_im.height)
            pil_im = pil_im.resize((max(24, int(pil_im.width * sc)), max(24, int(pil_im.height * sc))), Image.Resampling.LANCZOS)

        self._preview_photo = ImageTk.PhotoImage(pil_im)
        self.preview_canvas.create_image(cw // 2, ch // 2, image=self._preview_photo, anchor="center")

    def _accept(self):
        info = ICON_PRESETS.get(self.selected_key, {})
        txt = self.custom_text_var.get().strip() if info.get("kind") == "badge" else ""
        self.result = {
            "icon_key": self.selected_key,
            "text": txt,
        }
        self.destroy()
