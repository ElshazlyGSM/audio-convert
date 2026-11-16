"""
Subtitles and AI Captions Manager Mixin
Handles Whisper AI captioning, translation, subtitle bubble editor, CapCut import, and burning subtitles.
"""

import os
import sys
import queue
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import convert
from ui_dialogs.subtitle_style_dialog import SubtitleStyleDialog


class SubtitlesMixin:
    """Provides AI Captioning, subtitle bubbles, CapCut import, and burn-in controls."""

    def _dispatch_caption_ui(self, fn):
        """Thread-safe dispatch of UI updates to the main Tkinter thread."""
        if not hasattr(self, "_caption_ui_queue"):
            self._caption_ui_queue = queue.Queue()
        self._caption_ui_queue.put(fn)

    def _poll_caption_queue(self):
        """Drains the caption UI queue on the Tkinter main thread."""
        if hasattr(self, "_caption_ui_queue"):
            while True:
                try:
                    fn = self._caption_ui_queue.get_nowait()
                except queue.Empty:
                    break
                try:
                    fn()
                except Exception as exc:
                    print(f"[Caption UI Callback Error] {exc}")
        try:
            self.after(30, self._poll_caption_queue)
        except Exception:
            pass

    def _build_tab_caption(self, parent):
        if not hasattr(self, "_caption_ui_queue"):
            self._caption_ui_queue = queue.Queue()
        try:
            self.after(30, self._poll_caption_queue)
        except Exception:
            pass

        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        # Settings Card
        settings_box = ttk.LabelFrame(parent, padding=12)
        settings_box.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        settings_box.columnconfigure(0, weight=1)
        self.i18n_widgets["caption_settings_group"] = settings_box

        # Row 0: Three clean columns (Model, Audio Language, Translation)
        row0_frame = ttk.Frame(settings_box)
        row0_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        row0_frame.columnconfigure(0, weight=3)
        row0_frame.columnconfigure(1, weight=2)
        row0_frame.columnconfigure(2, weight=2)

        # Col 0: AI Model
        grp_model = ttk.Frame(row0_frame)
        grp_model.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.i18n_widgets["caption_model_label"] = ttk.Label(
            grp_model, text=self.text("caption_model_label"), font=("Segoe UI", 9, "bold")
        )
        self.i18n_widgets["caption_model_label"].pack(anchor="w", pady=(0, 3))
        model_ctrl_row = ttk.Frame(grp_model)
        model_ctrl_row.pack(fill="x")
        self.caption_model_combo = ttk.Combobox(
            model_ctrl_row, textvariable=self.caption_model_var, state="readonly", width=25
        )
        self.caption_model_combo.pack(side="left", padx=(0, 6))
        self.caption_model_combo.bind("<<ComboboxSelected>>", lambda _e: self._update_caption_model_status())

        self.caption_model_status_label = ttk.Label(
            model_ctrl_row, textvariable=self.caption_model_status_var, font=("Segoe UI", 8, "bold")
        )
        self.caption_model_status_label.pack(side="left", padx=(0, 6))

        self.caption_download_model_button = ttk.Button(
            model_ctrl_row,
            text=self.text("caption_download_model_btn"),
            command=self.download_selected_caption_model,
            style="Player.TButton",
        )
        self.caption_download_model_button.pack(side="left")

        # Col 1: Audio Language
        grp_lang = ttk.Frame(row0_frame)
        grp_lang.grid(row=0, column=1, sticky="nsew", padx=(0, 12))
        self.i18n_widgets["caption_lang_label"] = ttk.Label(
            grp_lang, text=self.text("caption_lang_label"), font=("Segoe UI", 9, "bold")
        )
        self.i18n_widgets["caption_lang_label"].pack(anchor="w", pady=(0, 3))
        self.caption_lang_combo = ttk.Combobox(
            grp_lang, textvariable=self.caption_lang_var, state="readonly", width=20
        )
        self.caption_lang_combo.pack(fill="x")

        # Col 2: Subtitle Translation
        grp_trans = ttk.Frame(row0_frame)
        grp_trans.grid(row=0, column=2, sticky="nsew")
        self.i18n_widgets["caption_translate_label"] = ttk.Label(
            grp_trans, text=self.text("caption_translate_label"), font=("Segoe UI", 9, "bold")
        )
        self.i18n_widgets["caption_translate_label"].pack(anchor="w", pady=(0, 3))
        self.caption_translate_combo = ttk.Combobox(
            grp_trans, textvariable=self.caption_translate_var, state="readonly", width=22
        )
        self.caption_translate_combo.pack(fill="x")

        # Row 1: Models Directory
        models_dir_row = ttk.Frame(settings_box)
        models_dir_row.grid(row=1, column=0, sticky="ew", pady=(2, 6))

        self.i18n_widgets["caption_models_dir"] = ttk.Label(
            models_dir_row, text=self.text("caption_models_dir"), font=("Segoe UI", 8)
        )
        self.i18n_widgets["caption_models_dir"].pack(side="left", padx=(0, 6))
        self.caption_models_dir_path_label = ttk.Label(
            models_dir_row, textvariable=self.caption_models_dir_var, foreground="#555555", font=("Segoe UI", 8), wraplength=450
        )
        self.caption_models_dir_path_label.pack(side="left", padx=(0, 8))
        self.caption_open_models_button = ttk.Button(
            models_dir_row,
            text=self.text("caption_open_models_dir"),
            command=self.open_models_folder,
            style="Player.TButton",
        )
        self.caption_open_models_button.pack(side="left")

        # Row 2: Checkboxes
        check_row = ttk.Frame(settings_box)
        check_row.grid(row=2, column=0, sticky="w", pady=(4, 8))
        self.caption_export_srt_check = ttk.Checkbutton(
            check_row, text=self.text("caption_export_srt"), variable=self.caption_export_srt_var
        )
        self.caption_export_srt_check.pack(side="left", padx=(0, 12))
        self.caption_export_vtt_check = ttk.Checkbutton(
            check_row, text=self.text("caption_export_vtt"), variable=self.caption_export_vtt_var
        )
        self.caption_export_vtt_check.pack(side="left", padx=(0, 12))
        self.caption_export_txt_check = ttk.Checkbutton(
            check_row, text=self.text("caption_export_txt"), variable=self.caption_export_txt_var
        )
        self.caption_export_txt_check.pack(side="left", padx=(0, 12))
        self.caption_burn_check = ttk.Checkbutton(
            check_row, text=self.text("caption_burn_video"), variable=self.caption_burn_var
        )
        self.caption_burn_check.pack(side="left")

        # Row 3: Actions Bar
        act_row = ttk.Frame(settings_box)
        act_row.grid(row=3, column=0, sticky="ew")
        act_row.columnconfigure(4, weight=1)

        self.caption_start_button = ttk.Button(
            act_row, text=self.text("caption_start"), command=self.start_embedded_caption, style="Action.TButton"
        )
        self.caption_start_button.grid(row=0, column=0, padx=(0, 8), sticky="w")

        self.caption_stop_button = ttk.Button(
            act_row, text=self.text("caption_stop"), command=self.cancel_embedded_caption, state="disabled"
        )
        self.caption_stop_button.grid(row=0, column=1, padx=(0, 8), sticky="w")

        self.caption_import_capcut_button = ttk.Button(
            act_row, text=self.text("caption_import_capcut"), command=self.import_from_capcut
        )
        self.caption_import_capcut_button.grid(row=0, column=2, padx=(0, 12), sticky="w")

        self.caption_progress_bar = ttk.Progressbar(act_row, mode="determinate", length=140)
        self.caption_progress_bar.grid(row=0, column=3, padx=(0, 12), sticky="w")

        self.caption_status_label = ttk.Label(act_row, textvariable=self.caption_status_var, font=("Segoe UI", 9, "bold"), foreground="#0066cc")
        self.caption_status_label.grid(
            row=0, column=4, sticky="w"
        )

        # Output Card
        output_box = ttk.LabelFrame(parent, padding=12)
        output_box.grid(row=1, column=0, sticky="nsew")
        output_box.columnconfigure(0, weight=1)
        output_box.rowconfigure(1, weight=1)
        self.i18n_widgets["caption_output_group"] = output_box

        # View Mode switcher
        view_switch = ttk.Frame(output_box)
        view_switch.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self.caption_rb_bubbles = ttk.Radiobutton(
            view_switch,
            text=self.text("caption_tab_bubbles"),
            variable=self.caption_view_mode_var,
            value="bubbles",
            command=self._caption_view_mode_changed,
        )
        self.caption_rb_bubbles.pack(side="left", padx=(0, 14))

        self.caption_rb_text = ttk.Radiobutton(
            view_switch,
            text=self.text("caption_tab_text"),
            variable=self.caption_view_mode_var,
            value="text",
            command=self._caption_view_mode_changed,
        )
        self.caption_rb_text.pack(side="left", padx=(0, 14))

        self.caption_rb_srt = ttk.Radiobutton(
            view_switch,
            text=self.text("caption_tab_srt"),
            variable=self.caption_view_mode_var,
            value="srt",
            command=self._caption_view_mode_changed,
        )
        self.caption_rb_srt.pack(side="left")

        self.caption_style_btn = ttk.Button(
            view_switch,
            text=self.text("caption_style_btn"),
            command=self.open_subtitle_style_dialog,
            style="Player.TButton",
        )
        self.caption_style_btn.pack(side="right")

        # 1. Text View Container (For Plain Text & SRT)
        self.caption_text_container = ttk.Frame(output_box)
        self.caption_text_container.columnconfigure(0, weight=1)
        self.caption_text_container.rowconfigure(0, weight=1)

        self.caption_text_view = tk.Text(
            self.caption_text_container, wrap="word", height=6, font=("Segoe UI", 10), state="disabled", bg="#fafafa"
        )
        self.caption_text_view.grid(row=0, column=0, sticky="nsew")
        txt_scroll = ttk.Scrollbar(self.caption_text_container, orient="vertical", command=self.caption_text_view.yview)
        txt_scroll.grid(row=0, column=1, sticky="ns")
        self.caption_text_view.configure(yscrollcommand=txt_scroll.set)

        # 2. Interactive Segment Bubbles Container (Default)
        self.caption_bubbles_container = ttk.Frame(output_box)
        self.caption_bubbles_container.columnconfigure(0, weight=1)
        self.caption_bubbles_container.rowconfigure(1, weight=1)

        # Toolbar for Bubbles
        bubble_bar = ttk.Frame(self.caption_bubbles_container)
        bubble_bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        is_ar = self.language_var.get() == "العربية"
        ttk.Label(bubble_bar, text="🔍").pack(side="left" if not is_ar else "right", padx=(0, 4))
        self.bubble_search_entry = ttk.Entry(bubble_bar, textvariable=self.bubble_search_var, width=22)
        self.bubble_search_entry.pack(side="left" if not is_ar else "right", padx=(0, 6))
        self._attach_entry_context_menu(self.bubble_search_entry)

        self.bubble_clear_btn = ttk.Button(
            bubble_bar, text="✖", width=3, command=lambda: self.bubble_search_var.set(""), style="Player.TButton"
        )
        self.bubble_clear_btn.pack(side="left" if not is_ar else "right", padx=(0, 10))

        self.bubble_add_btn = ttk.Button(
            bubble_bar,
            text="➕ " + self.text("sub_add_segment"),
            command=self._add_new_bubble_segment,
            style="Player.TButton",
        )
        self.bubble_add_btn.pack(side="left" if not is_ar else "right", padx=(0, 12))

        self.bubble_count_label = ttk.Label(bubble_bar, text="", font=("Segoe UI", 9, "bold"), foreground="#0969da")
        self.bubble_count_label.pack(side="left" if not is_ar else "right", padx=(0, 12))

        # Pagination Controls
        pag_side = "right" if not is_ar else "left"
        self.bubble_btn_last = ttk.Button(bubble_bar, text="⏭", width=3, command=self._bubble_page_last, style="Player.TButton")
        self.bubble_btn_last.pack(side=pag_side, padx=1)

        self.bubble_btn_next = ttk.Button(bubble_bar, text="▶" if not is_ar else "◀", width=3, command=self._bubble_page_next, style="Player.TButton")
        self.bubble_btn_next.pack(side=pag_side, padx=1)

        self.bubble_page_label = ttk.Label(bubble_bar, text="1 / 1", font=("Segoe UI", 9, "bold"))
        self.bubble_page_label.pack(side=pag_side, padx=6)

        self.bubble_btn_prev = ttk.Button(bubble_bar, text="◀" if not is_ar else "▶", width=3, command=self._bubble_page_prev, style="Player.TButton")
        self.bubble_btn_prev.pack(side=pag_side, padx=1)

        self.bubble_btn_first = ttk.Button(bubble_bar, text="⏮", width=3, command=self._bubble_page_first, style="Player.TButton")
        self.bubble_btn_first.pack(side=pag_side, padx=1)

        # Scrollable Canvas for Cards
        canvas_box = ttk.Frame(self.caption_bubbles_container)
        canvas_box.grid(row=1, column=0, sticky="nsew")
        canvas_box.columnconfigure(0, weight=1)
        canvas_box.rowconfigure(0, weight=1)

        self.bubble_canvas = tk.Canvas(canvas_box, bg="#f6f8fa", highlightthickness=1, highlightbackground="#e1e4e8")
        self.bubble_canvas.grid(row=0, column=0, sticky="nsew")

        self.bubble_scrollbar = ttk.Scrollbar(canvas_box, orient="vertical", command=self.bubble_canvas.yview)
        self.bubble_scrollbar.grid(row=0, column=1, sticky="ns")
        self.bubble_canvas.configure(yscrollcommand=self.bubble_scrollbar.set)

        self.bubble_inner = ttk.Frame(self.bubble_canvas)
        self.bubble_inner_id = self.bubble_canvas.create_window((0, 0), window=self.bubble_inner, anchor="nw")

        def _on_canvas_configure(event):
            self.bubble_canvas.itemconfig(self.bubble_inner_id, width=event.width)

        self.bubble_canvas.bind("<Configure>", _on_canvas_configure)
        self.bubble_inner.bind("<Configure>", lambda _e: self.bubble_canvas.configure(scrollregion=self.bubble_canvas.bbox("all")))

        def _on_bubble_mousewheel(event):
            if hasattr(event, "delta") and event.delta:
                self.bubble_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.bubble_canvas.bind_all("<MouseWheel>", _on_bubble_mousewheel)

        # Empty state message
        self.bubble_empty_label = ttk.Label(
            self.bubble_inner,
            text=self.text("sub_no_segments"),
            foreground="#666666",
            font=("Segoe UI", 10),
            padding=(20, 30),
        )
        self.bubble_empty_label.pack(fill="x", pady=20)

        # Grid default view (bubbles)
        self.caption_bubbles_container.grid(row=1, column=0, sticky="nsew")

        # Action Buttons
        tools_row = ttk.Frame(output_box)
        tools_row.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        self.caption_copy_button = ttk.Button(
            tools_row, text=self.text("caption_copy"), command=self.copy_embedded_caption, style="Player.TButton"
        )
        self.caption_copy_button.pack(side="left", padx=(0, 8))

        self.caption_save_button = ttk.Button(
            tools_row, text=self.text("caption_save_as"), command=self.save_embedded_caption_as, style="Player.TButton"
        )
        self.caption_save_button.pack(side="left", padx=(0, 8))

        self.caption_burn_button = ttk.Button(
            tools_row, text=self.text("caption_burn_now"), command=self.burn_embedded_caption, style="Player.TButton"
        )
        self.caption_burn_button.pack(side="left", padx=(0, 8))

        self.caption_burn_cancel_button = ttk.Button(
            tools_row,
            text=self.text("caption_stop"),
            command=self.cancel_embedded_caption,
            state="disabled",
            style="Player.TButton",
        )
        self.caption_burn_cancel_button.pack(side="left", padx=(0, 8))

        self.caption_translate_button = ttk.Button(
            tools_row,
            text=self.text("caption_translate_btn"),
            command=self.translate_embedded_caption_text,
            style="Player.TButton",
        )
        self.caption_translate_button.pack(side="left", padx=(0, 8))

        self.caption_burn_status_label = ttk.Label(
            tools_row,
            textvariable=self.caption_status_var,
            font=("Segoe UI", 9, "bold"),
            foreground="#0066cc",
        )
        self.caption_burn_status_label.pack(side="left", padx=(8, 8))

        self.caption_open_folder_button = ttk.Button(
            tools_row,
            text=self.text("caption_open_folder"),
            command=lambda: self.open_folder(self.output_dir),
            style="Player.TButton",
        )
        self.caption_open_folder_button.pack(side="right")

    def _refresh_caption_options(self):
        is_ar = self.language_var.get() == "العربية"
        models = [
            "Small (⚡ حوالي 465MB - موصى به: توازن ممتاز ودقة عالية)" if is_ar else "Small (⚡ ~465MB - Recommended: High Accuracy & Balanced)",
            "Base (🚀 حوالي 140MB - خفيف وسريع)" if is_ar else "Base (🚀 ~140MB - Fast & Lightweight)",
            "Turbo (💎 حوالي 1.5GB - أعلى دقة مثل CapCut و NoteGPT)" if is_ar else "Turbo (💎 ~1.5GB - Max Accuracy / CapCut & NoteGPT)",
            "Tiny (⚠️ حوالي 75MB - فائق السرعة / دقة منخفضة)" if is_ar else "Tiny (⚠️ ~75MB - Ultra Fast, Low Accuracy)",
            "Medium (💎 حوالي 1.5GB - دقة عالية جداً)" if is_ar else "Medium (~1.5GB - Very High Accuracy)",
        ]
        self.caption_model_combo.configure(values=models)
        cur_m = self.caption_model_var.get().lower()
        if "tiny" in cur_m:
            self.caption_model_var.set(models[3])
        elif "base" in cur_m:
            self.caption_model_var.set(models[1])
        elif "turbo" in cur_m:
            self.caption_model_var.set(models[2])
        elif "medium" in cur_m:
            self.caption_model_var.set(models[4])
        else:
            self.caption_model_var.set(models[0])

        langs = [
            "كشف تلقائي للغة" if is_ar else "Auto Detect",
            "العربية (Arabic)",
            "الإنجليزية (English)",
            "الفرنسية (French)",
            "الإسبانية (Spanish)",
            "الألمانية (German)",
            "الإيطالية (Italian)",
            "التركية (Turkish)",
            "الروسية (Russian)",
            "الصينية (Chinese)",
            "اليابانية (Japanese)",
            "الكورية (Korean)",
            "الأوردو (Urdu)",
        ]
        self.caption_lang_combo.configure(values=langs)
        if not self.caption_lang_var.get() or self.caption_lang_var.get() in {"auto", "Auto Detect", "كشف تلقائي للغة"}:
            self.caption_lang_var.set(langs[0])

        trans_langs = [
            "نفس لغة الصوت الأصلية (بدون ترجمة)" if is_ar else "Original Audio Language (No Translation)",
            "العربية (Arabic)",
            "الإنجليزية (English)",
            "الفرنسية (French)",
            "الإسبانية (Spanish)",
            "الألمانية (German)",
            "الإيطالية (Italian)",
            "التركية (Turkish)",
            "الروسية (Russian)",
            "الصينية (Chinese)",
            "اليابانية (Japanese)",
            "الكورية (Korean)",
        ]
        if hasattr(self, "caption_translate_combo"):
            self.caption_translate_combo.configure(values=trans_langs)
            if not self.caption_translate_var.get():
                self.caption_translate_var.set(trans_langs[0])

        self._update_caption_model_status()

    def open_models_folder(self):
        models_dir = convert.get_whisper_models_dir()
        self.open_folder(models_dir)

    def _get_current_caption_model_id(self):
        chosen_m = self.caption_model_var.get().lower()
        if "tiny" in chosen_m:
            return "tiny"
        elif "base" in chosen_m:
            return "base"
        elif "small" in chosen_m:
            return "small"
        elif "medium" in chosen_m:
            return "medium"
        return "turbo"

    def _update_caption_model_status(self):
        model_name = self._get_current_caption_model_id()
        status = convert.get_whisper_model_status(model_name)
        if status["is_downloaded"]:
            self.caption_model_status_var.set(self.text("caption_model_status_ready"))
            if hasattr(self, "caption_model_status_label"):
                self.caption_model_status_label.configure(foreground="#008800")
            if hasattr(self, "caption_download_model_button"):
                self.caption_download_model_button.configure(state="disabled", text=self.text("caption_model_ready_btn"))
        else:
            self.caption_model_status_var.set(
                self.text("caption_model_status_needs_download", size=int(status["estimated_mb"]))
            )
            if hasattr(self, "caption_model_status_label"):
                self.caption_model_status_label.configure(foreground="#cc6600")
            if hasattr(self, "caption_download_model_button"):
                self.caption_download_model_button.configure(state="normal", text=self.text("caption_download_model_btn"))

    def download_selected_caption_model(self):
        chosen_m = self.caption_model_var.get().lower()
        if "tiny" in chosen_m:
            model_name = "tiny"
        elif "base" in chosen_m:
            model_name = "base"
        elif "small" in chosen_m:
            model_name = "small"
        elif "medium" in chosen_m:
            model_name = "medium"
        else:
            model_name = "turbo"

        status = convert.get_whisper_model_status(model_name)
        if status["is_downloaded"]:
            messagebox.showinfo(self.text("app_title"), self.text("caption_model_status_ready"))
            return

        self.caption_cancel_event.clear()
        self.caption_start_button.configure(state="disabled")
        self.caption_stop_button.configure(state="normal")
        if hasattr(self, "caption_download_model_button"):
            self.caption_download_model_button.configure(state="disabled")
        self.caption_model_combo.configure(state="disabled")
        self.caption_progress_bar.configure(mode="determinate", value=0)

        def prog_cb(pct, dl_bytes, tot_bytes, fname, speed, eta, tdir):
            dl_mb = dl_bytes / (1024 * 1024)
            tot_mb = tot_bytes / (1024 * 1024)
            eta_part = f" - {eta}" if eta else ""
            msg = self.text(
                "caption_downloading_model",
                model=model_name,
                dl_mb=dl_mb,
                tot_mb=tot_mb,
                pct=pct,
                speed=speed,
                eta_part=eta_part,
            )
            self.after(0, lambda: self.caption_status_var.set(msg))
            self.after(0, lambda: self.caption_progress_bar.configure(value=pct))

        def worker():
            try:
                convert.download_whisper_model(
                    model_size=model_name,
                    progress_callback=prog_cb,
                    cancel_callback=self.caption_cancel_event.is_set,
                )
                if self.caption_cancel_event.is_set():
                    self.after(0, self._on_embedded_caption_cancel)
                    return
                self.after(0, lambda: self._on_caption_model_download_done(model_name))
            except convert.CancelledError:
                self.after(0, self._on_embedded_caption_cancel)
            except Exception as exc:
                if self.caption_cancel_event.is_set() or "cancel" in str(exc).lower():
                    self.after(0, self._on_embedded_caption_cancel)
                    return
                self.after(0, lambda: self._on_embedded_caption_error(exc))

        self.caption_download_thread = threading.Thread(target=worker, daemon=True)
        self.caption_download_thread.start()

    def _on_caption_model_download_done(self, model_name):
        self.caption_progress_bar.configure(value=100)
        self.caption_status_var.set(self.text("caption_download_complete", model=model_name))
        self.caption_start_button.configure(state="normal")
        self.caption_stop_button.configure(state="disabled")
        self.caption_model_combo.configure(state="readonly")
        self._update_caption_model_status()
        messagebox.showinfo(
            self.text("app_title"),
            self.text("caption_download_complete", model=model_name),
        )

    def open_subtitle_style_dialog(self):
        dlg = SubtitleStyleDialog(self)
        self._apply_theme_to_toplevel(dlg)
        dlg.grab_set()

    def _caption_view_mode_changed(self):
        mode = self.caption_view_mode_var.get()
        if mode == "bubbles":
            if hasattr(self, "caption_text_container"):
                self.caption_text_container.grid_remove()
            if hasattr(self, "caption_bubbles_container"):
                self.caption_bubbles_container.grid(row=1, column=0, sticky="nsew")
            self._refresh_bubbles_ui()
        else:
            if hasattr(self, "caption_bubbles_container"):
                self.caption_bubbles_container.grid_remove()
            if hasattr(self, "caption_text_container"):
                self.caption_text_container.grid(row=1, column=0, sticky="nsew")
            self.caption_text_view.configure(state="normal")
            self.caption_text_view.delete("1.0", "end")
            if self.caption_current_result:
                content = self.caption_current_result.get("text", "") if mode == "text" else self.caption_current_result.get("srt", "")
                self.caption_text_view.insert("end", content)
                self.caption_text_view.tag_configure("rtl", justify="right")
                self.caption_text_view.tag_configure("ltr", justify="left")
                has_ar = any("\u0600" <= c <= "\u06ff" for c in content)
                self.caption_text_view.tag_add("rtl" if (has_ar and mode == "text") else "ltr", "1.0", "end")
            self.caption_text_view.configure(state="disabled")

    def _on_bubble_search_changed(self):
        self.bubble_current_page = 0
        self._refresh_bubbles_ui()

    def _bubble_page_first(self):
        self.bubble_current_page = 0
        self._refresh_bubbles_ui()

    def _bubble_page_prev(self):
        if self.bubble_current_page > 0:
            self.bubble_current_page -= 1
            self._refresh_bubbles_ui()

    def _bubble_page_next(self):
        segments = self.caption_current_result.get("segments", []) if self.caption_current_result else []
        q = self.bubble_search_var.get().strip().lower()
        if q:
            filtered_count = sum(1 for s in segments if q in s.get("text", "").lower())
        else:
            filtered_count = len(segments)
        import math
        total_pages = max(1, math.ceil(filtered_count / self.bubble_page_size))
        if self.bubble_current_page < total_pages - 1:
            self.bubble_current_page += 1
            self._refresh_bubbles_ui()

    def _bubble_page_last(self):
        segments = self.caption_current_result.get("segments", []) if self.caption_current_result else []
        q = self.bubble_search_var.get().strip().lower()
        if q:
            filtered_count = sum(1 for s in segments if q in s.get("text", "").lower())
        else:
            filtered_count = len(segments)
        import math
        total_pages = max(1, math.ceil(filtered_count / self.bubble_page_size))
        self.bubble_current_page = max(0, total_pages - 1)
        self._refresh_bubbles_ui()

    def _refresh_bubbles_ui(self):
        if not hasattr(self, "bubble_inner"):
            return

        for child in self.bubble_inner.winfo_children():
            child.destroy()

        segments = self.caption_current_result.get("segments", []) if self.caption_current_result else []
        if not segments:
            empty_lbl = ttk.Label(
                self.bubble_inner,
                text=self.text("sub_no_segments"),
                foreground="#666666",
                font=("Segoe UI", 10),
                padding=(20, 24),
            )
            empty_lbl.pack(fill="x", pady=20)
            self.bubble_page_label.configure(text="1 / 1")
            self.bubble_count_label.configure(text="")
            self.bubble_btn_prev.configure(state="disabled")
            self.bubble_btn_next.configure(state="disabled")
            self.bubble_btn_first.configure(state="disabled")
            self.bubble_btn_last.configure(state="disabled")
            return

        q = self.bubble_search_var.get().strip().lower()
        if q:
            filtered = [(idx, seg) for idx, seg in enumerate(segments) if q in seg.get("text", "").lower()]
        else:
            filtered = [(idx, seg) for idx, seg in enumerate(segments)]

        import math
        total_items = len(filtered)
        total_pages = max(1, math.ceil(total_items / self.bubble_page_size))
        self.bubble_current_page = max(0, min(self.bubble_current_page, total_pages - 1))

        start_idx = self.bubble_current_page * self.bubble_page_size
        end_idx = min(start_idx + self.bubble_page_size, total_items)
        page_items = filtered[start_idx:end_idx]

        self.bubble_page_label.configure(text=f"{self.bubble_current_page + 1} / {total_pages}")
        self.bubble_btn_first.configure(state="normal" if self.bubble_current_page > 0 else "disabled")
        self.bubble_btn_prev.configure(state="normal" if self.bubble_current_page > 0 else "disabled")
        self.bubble_btn_next.configure(state="normal" if self.bubble_current_page < total_pages - 1 else "disabled")
        self.bubble_btn_last.configure(state="normal" if self.bubble_current_page < total_pages - 1 else "disabled")

        is_ar = self.language_var.get() == "العربية"
        if q:
            cnt_txt = f"{self.text('sub_total_segments', count=total_items)} (فلترة من {len(segments)})" if is_ar else f"{total_items} segments (filtered from {len(segments)})"
        else:
            cnt_txt = self.text("sub_total_segments", count=len(segments))
        range_str = f"[{start_idx + 1}-{end_idx}]" if total_items > 0 else "[0-0]"
        self.bubble_count_label.configure(text=f"📊 {cnt_txt} {range_str}")

        is_dark = getattr(self, "theme_var", None) and self.theme_var.get() == "dark"
        card_bg = "#21262d" if is_dark else "#ffffff"
        txt_bg = "#161b22" if is_dark else "#fafbfc"
        txt_fg = "#e6edf3" if is_dark else "#1f2328"
        idx_fg = "#58a6ff" if is_dark else "#0969da"
        ts_fg = "#8b949e" if is_dark else "#57606a"

        for orig_idx, seg in page_items:
            card = tk.Frame(self.bubble_inner, bg=card_bg, bd=1, relief="solid", padx=8, pady=6)
            card.pack(fill="x", padx=8, pady=4)

            # Header row
            hdr = tk.Frame(card, bg=card_bg)
            hdr.pack(fill="x", pady=(0, 4))

            idx_lbl = tk.Label(hdr, text=f"#{orig_idx + 1}", font=("Segoe UI", 9, "bold"), fg=idx_fg, bg=card_bg)
            idx_lbl.pack(side="left" if not is_ar else "right", padx=(0, 8))

            s_sec = seg.get("start", 0)
            e_sec = seg.get("end", 0)
            s_ts = convert.format_timestamp_srt(s_sec)[:8] + "." + str(int((s_sec % 1) * 100)).zfill(2)
            e_ts = convert.format_timestamp_srt(e_sec)[:8] + "." + str(int((e_sec % 1) * 100)).zfill(2)
            ts_lbl = tk.Label(hdr, text=f"⏱ {s_ts} ➔ {e_ts}", font=("Segoe UI", 8), fg=ts_fg, bg=card_bg)
            ts_lbl.pack(side="left" if not is_ar else "right", padx=(0, 8))

            btn_side = "right" if not is_ar else "left"

            del_btn = ttk.Button(hdr, text="🗑 " + self.text("sub_del_segment"), width=8, style="Player.TButton", command=lambda i=orig_idx: self._delete_bubble_segment(i))
            del_btn.pack(side=btn_side, padx=2)

            ins_btn = ttk.Button(hdr, text="➕", width=3, style="Player.TButton", command=lambda i=orig_idx: self._insert_bubble_segment_after(i))
            ins_btn.pack(side=btn_side, padx=2)

            if self.input_path and self.input_path.is_file():
                play_btn = ttk.Button(hdr, text="▶", width=3, style="Player.TButton", command=lambda s=s_sec, e=e_sec: self._play_bubble_segment(s, e))
                play_btn.pack(side=btn_side, padx=2)

            # Text Box with automatic RTL/LTR alignment
            txt_box = tk.Text(card, wrap="word", height=2, font=("Segoe UI", 10), bg=txt_bg, bd=1, relief="solid", fg=txt_fg, insertbackground="#58a6ff" if is_dark else "#000000")
            txt_box.tag_configure("rtl", justify="right")
            txt_box.tag_configure("ltr", justify="left")
            seg_text = seg.get("text", "")
            txt_box.pack(fill="x")
            txt_box.insert("1.0", seg_text)
            has_ar = any("\u0600" <= c <= "\u06ff" for c in seg_text)
            txt_box.tag_add("rtl" if has_ar else "ltr", "1.0", "end")
            self._attach_text_context_menu(txt_box)

            def _on_key(event, idx=orig_idx, widget=txt_box):
                cur_t = widget.get("1.0", "end-1c")
                is_rtl = any("\u0600" <= c <= "\u06ff" for c in cur_t)
                widget.tag_remove("rtl", "1.0", "end")
                widget.tag_remove("ltr", "1.0", "end")
                widget.tag_add("rtl" if is_rtl else "ltr", "1.0", "end")
                self._on_bubble_text_edited(idx, widget)

            txt_box.bind("<KeyRelease>", _on_key)
            txt_box.bind("<FocusOut>", _on_key)

        self.bubble_canvas.yview_moveto(0.0)
        self.bubble_canvas.update_idletasks()
        self.bubble_canvas.configure(scrollregion=self.bubble_canvas.bbox("all"))

    def _on_bubble_text_edited(self, orig_idx, widget):
        if not self.caption_current_result or "segments" not in self.caption_current_result:
            return
        segments = self.caption_current_result["segments"]
        if 0 <= orig_idx < len(segments):
            new_text = widget.get("1.0", "end-1c").strip()
            segments[orig_idx]["text"] = new_text
            self.caption_current_result["text"] = "\n".join(s.get("text", "") for s in segments)
            self.caption_current_result["srt"] = convert.generate_srt_content(segments)
            if "vtt" in self.caption_current_result:
                self.caption_current_result["vtt"] = convert.generate_vtt_content(segments)

    def _delete_bubble_segment(self, orig_idx):
        if not self.caption_current_result or "segments" not in self.caption_current_result:
            return
        segments = self.caption_current_result["segments"]
        if 0 <= orig_idx < len(segments):
            is_ar = self.language_var.get() == "العربية"
            msg = f"هل أنت متأكد من حذف المقطع #{orig_idx + 1}؟" if is_ar else f"Delete segment #{orig_idx + 1}?"
            if messagebox.askyesno(self.text("app_title"), msg, parent=self):
                segments.pop(orig_idx)
                self.caption_current_result["text"] = "\n".join(s.get("text", "") for s in segments)
                self.caption_current_result["srt"] = convert.generate_srt_content(segments)
                self._refresh_bubbles_ui()

    def _insert_bubble_segment_after(self, orig_idx):
        if not self.caption_current_result or "segments" not in self.caption_current_result:
            return
        segments = self.caption_current_result["segments"]
        if 0 <= orig_idx < len(segments):
            prev_seg = segments[orig_idx]
            new_start = prev_seg.get("end", 0) + 0.1
            new_end = new_start + 2.5
            new_seg = {"start": round(new_start, 3), "end": round(new_end, 3), "text": "نص جديد..." if self.language_var.get() == "العربية" else "New text..."}
            segments.insert(orig_idx + 1, new_seg)
            self.caption_current_result["text"] = "\n".join(s.get("text", "") for s in segments)
            self.caption_current_result["srt"] = convert.generate_srt_content(segments)
            self._refresh_bubbles_ui()

    def _add_new_bubble_segment(self):
        if not self.caption_current_result:
            self.caption_current_result = {"segments": [], "text": "", "srt": ""}
        if "segments" not in self.caption_current_result:
            self.caption_current_result["segments"] = []

        segments = self.caption_current_result["segments"]
        last_end = segments[-1].get("end", 0) if segments else 0.0
        new_start = last_end + 0.2
        new_end = new_start + 3.0
        is_ar = self.language_var.get() == "العربية"
        new_seg = {"start": round(new_start, 3), "end": round(new_end, 3), "text": "نص مقطع إضافي" if is_ar else "Additional subtitle segment"}
        segments.append(new_seg)
        self.caption_current_result["text"] = "\n".join(s.get("text", "") for s in segments)
        self.caption_current_result["srt"] = convert.generate_srt_content(segments)
        self._bubble_page_last()

    def _play_bubble_segment(self, start_sec, end_sec):
        if self.input_path and self.input_path.is_file():
            self._start_media_from(max(0, start_sec - 0.2))
            dur_ms = max(500, int((end_sec - start_sec + 0.5) * 1000))
            self.after(dur_ms, lambda: self.stop_playback(reset_position=False) if self._is_playing() else None)

    def translate_embedded_caption_text(self):
        trans_val = self.caption_translate_var.get()
        trans_code = None
        if "عرب" in trans_val or "arabic" in trans_val.lower():
            trans_code = "ar"
        elif "إنجل" in trans_val or "english" in trans_val.lower():
            trans_code = "en"
        elif "فرنس" in trans_val or "french" in trans_val.lower():
            trans_code = "fr"
        elif "إسبان" in trans_val or "spanish" in trans_val.lower():
            trans_code = "es"
        elif "ألمان" in trans_val or "german" in trans_val.lower():
            trans_code = "de"
        elif "ترك" in trans_val or "turkish" in trans_val.lower():
            trans_code = "tr"
        elif "روس" in trans_val or "russian" in trans_val.lower():
            trans_code = "ru"
        elif "صين" in trans_val or "chinese" in trans_val.lower():
            trans_code = "zh-CN"
        elif "يابان" in trans_val or "japanese" in trans_val.lower():
            trans_code = "ja"
        elif "كور" in trans_val or "korean" in trans_val.lower():
            trans_code = "ko"

        if not trans_code:
            messagebox.showinfo(self.text("app_title"), self.text("caption_translate_label"))
            return
        if not self.caption_current_result and not self.caption_segments_accumulated:
            return

        def worker():
            try:
                self.after(0, lambda: self.caption_status_var.set(self.text("caption_translating", target=trans_code)))
                orig_segments = self.caption_current_result["segments"] if self.caption_current_result else self.caption_segments_accumulated
                translated = convert.translate_segments(orig_segments, target_lang=trans_code)
                if self.caption_current_result:
                    self.caption_current_result["segments"] = translated
                    self.caption_current_result["text"] = "\n".join(s["text"] for s in translated)
                    self.caption_current_result["srt"] = convert.generate_srt_content(translated)
                self.caption_segments_accumulated = translated
                self.after(0, self._caption_view_mode_changed)
                self.after(0, lambda: self.caption_status_var.set(self.text("caption_translate_done", target=trans_code)))
            except Exception as exc:
                self.after(0, lambda: self.caption_status_var.set(f"Translation error: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def start_embedded_caption(self):
        if not convert.whisper_available():
            messagebox.showerror(
                self.text("app_title"),
                "faster-whisper is not installed.\nPlease run: pip install faster-whisper",
            )
            return

        if hasattr(self, "caption_thread") and self.caption_thread and self.caption_thread.is_alive():
            self.caption_cancel_event.set()
            convert.stop_all_active_processes()

        target_file = None
        if hasattr(self, "input_path") and self.input_path and Path(self.input_path).is_file():
            target_file = Path(self.input_path)
        elif self.media_files:
            target_file = Path(self.media_files[0])

        if not target_file or not target_file.exists():
            messagebox.showwarning(self.text("app_title"), self.text("choose_single_trim"))
            return

        chosen_m = self.caption_model_var.get().lower()
        if "tiny" in chosen_m:
            model_name = "tiny"
        elif "small" in chosen_m:
            model_name = "small"
        elif "medium" in chosen_m:
            model_name = "medium"
        elif "base" in chosen_m:
            model_name = "base"
        else:
            model_name = "turbo"

        lang_val = self.caption_lang_var.get()
        lang_code = None
        for code, name in convert.WHISPER_LANGUAGES.items():
            if name.lower() in lang_val.lower():
                lang_code = code
                break
        if "عرب" in lang_val or "arabic" in lang_val.lower():
            lang_code = "ar"
        elif "إنجل" in lang_val or "english" in lang_val.lower():
            lang_code = "en"

        trans_val = self.caption_translate_var.get()
        trans_code = None
        if "عرب" in trans_val or "arabic" in trans_val.lower():
            trans_code = "ar"
        elif "إنجل" in trans_val or "english" in trans_val.lower():
            trans_code = "en"
        elif "فرنس" in trans_val or "french" in trans_val.lower():
            trans_code = "fr"
        elif "إسبان" in trans_val or "spanish" in trans_val.lower():
            trans_code = "es"
        elif "ألمان" in trans_val or "german" in trans_val.lower():
            trans_code = "de"
        elif "ترك" in trans_val or "turkish" in trans_val.lower():
            trans_code = "tr"
        elif "روس" in trans_val or "russian" in trans_val.lower():
            trans_code = "ru"
        elif "صين" in trans_val or "chinese" in trans_val.lower():
            trans_code = "zh-CN"
        elif "يابان" in trans_val or "japanese" in trans_val.lower():
            trans_code = "ja"
        elif "كور" in trans_val or "korean" in trans_val.lower():
            trans_code = "ko"

        self.caption_active_op_id = time.monotonic()
        current_op_id = self.caption_active_op_id
        if hasattr(self, "_caption_ui_queue"):
            while not self._caption_ui_queue.empty():
                try:
                    self._caption_ui_queue.get_nowait()
                except Exception:
                    break
        self.caption_cancel_event.clear()
        self.caption_current_result = None
        self.caption_segments_accumulated = []

        is_ar = (self.language_var.get() == "العربية")
        self.caption_start_button.configure(state="disabled")
        self.caption_stop_button.configure(state="normal")
        if hasattr(self, "btn_studio_transcribe"):
            self.btn_studio_transcribe.configure(
                state="disabled",
                text="⏳ جاري التفريغ بالذكاء الاصطناعي..." if is_ar else "⏳ Transcribing..."
            )
        if hasattr(self, "btn_cancel_progress"):
            self.btn_cancel_progress.grid()
        if hasattr(self, "progress"):
            self.progress.configure(mode="indeterminate")
            self.progress.start(10)

        self.caption_text_view.configure(state="normal")
        self.caption_text_view.delete("1.0", "end")
        self.caption_text_view.configure(state="disabled")
        if hasattr(self, "_refresh_bubbles_ui"):
            self._refresh_bubbles_ui()

        init_msg = self.text("caption_loading")
        self.caption_status_var.set(init_msg)
        self.status_var.set(f"🎙️ {init_msg}")
        self.caption_progress_bar.configure(mode="indeterminate")
        self.caption_progress_bar.start(10)

        def worker():
            try:
                def prog_cb(pct, text, s, e, dur):
                    if getattr(self, "caption_active_op_id", None) != current_op_id or self.caption_cancel_event.is_set():
                        return
                    self._dispatch_caption_ui(lambda: self._on_embedded_caption_segment(pct, text, s, e, dur, op_id=current_op_id))

                res = convert.transcribe_media(
                    target_file,
                    model_size=model_name,
                    language=lang_code,
                    translate_to=trans_code,
                    progress_callback=prog_cb,
                    cancel_callback=self.caption_cancel_event.is_set,
                )
                if getattr(self, "caption_active_op_id", None) != current_op_id or self.caption_cancel_event.is_set():
                    self._dispatch_caption_ui(lambda: self._on_embedded_caption_cancel(op_id=current_op_id))
                    return

                self._dispatch_caption_ui(lambda: self._on_embedded_caption_done(res, op_id=current_op_id))
            except convert.CancelledError:
                if getattr(self, "caption_active_op_id", None) == current_op_id:
                    self._dispatch_caption_ui(lambda: self._on_embedded_caption_cancel(op_id=current_op_id))
            except Exception as exc:
                if getattr(self, "caption_active_op_id", None) != current_op_id or self.caption_cancel_event.is_set() or "cancel" in str(exc).lower():
                    self._dispatch_caption_ui(lambda: self._on_embedded_caption_cancel(op_id=current_op_id))
                    return
                self._dispatch_caption_ui(lambda: self._on_embedded_caption_error(exc, op_id=current_op_id))

        self.caption_transcribe_start_time = time.monotonic()
        self.caption_thread = threading.Thread(target=worker, daemon=True)
        self.caption_thread.start()

    def _on_embedded_caption_segment(self, pct, text, start, end, dur, op_id=None):
        if op_id is not None and getattr(self, "caption_active_op_id", None) != op_id:
            return
        # Filter out system and extraction status messages
        if (
            text.startswith("Downloading")
            or text.startswith("جاري تحميل")
            or text.startswith("جاري تحضير")
            or text.startswith("جاري استخراج")
            or text.startswith("جاري التفريغ الصوتي")
            or text.startswith("Preparing")
            or text.startswith("Extracting")
            or text.startswith("Transcribing speech")
            or "Whisper" in text
            or "الذاكرة" in text
            or "memory" in text.lower()
        ):
            self.caption_status_var.set(text)
            self.status_var.set(f"🎙️ {text}")
            return

        if self.caption_progress_bar["mode"] == "indeterminate":
            self.caption_progress_bar.stop()
            self.caption_progress_bar.configure(mode="determinate", maximum=100)
        self.caption_progress_bar.configure(value=pct)

        if hasattr(self, "progress"):
            if self.progress["mode"] == "indeterminate":
                self.progress.stop()
                self.progress.configure(mode="determinate", maximum=100)
            self.progress.configure(value=pct)

        is_ar = self.language_var.get() == "العربية"
        elapsed_str = ""
        eta_str = ""
        if hasattr(self, "caption_transcribe_start_time") and self.caption_transcribe_start_time:
            wall_elapsed = time.monotonic() - self.caption_transcribe_start_time
            elapsed_str = self._format_seconds(wall_elapsed)
            if pct > 0:
                eta_sec = (wall_elapsed / pct) * (100 - pct)
                eta_str = self._format_seconds(eta_sec)
            else:
                eta_str = self.text("estimating")

        pos_str = ""
        if dur and dur > 0:
            pos_str = f" ({self._format_seconds(end)} / {self._format_seconds(dur)})"

        if is_ar:
            status = f"جاري التفريغ: {pct}%{pos_str}"
            if elapsed_str:
                status += f" | المنقضي: {elapsed_str} | المتبقي: {eta_str}"
        else:
            status = f"Transcribing: {pct}%{pos_str}"
            if elapsed_str:
                status += f" | Elapsed: {elapsed_str} | Remaining: {eta_str}"

        self.caption_status_var.set(status)
        self.status_var.set(f"🎙️ {status}")

        self.caption_segments_accumulated.append({"start": start, "end": end, "text": text})
        self.caption_text_view.configure(state="normal")
        if self.caption_view_mode_var.get() == "text":
            self.caption_text_view.insert("end", text + " ")
            has_ar = any("\u0600" <= c <= "\u06ff" for c in text)
            self.caption_text_view.tag_configure("rtl", justify="right")
            if has_ar:
                self.caption_text_view.tag_add("rtl", "1.0", "end")
        else:
            idx = len(self.caption_segments_accumulated)
            s_str = convert.format_timestamp_srt(start)
            e_str = convert.format_timestamp_srt(end)
            self.caption_text_view.insert("end", f"{idx}\n{s_str} --> {e_str}\n{text}\n\n")
        self.caption_text_view.see("end")
        self.caption_text_view.configure(state="disabled")

        if self.caption_view_mode_var.get() == "bubbles":
            if not self.caption_current_result:
                self.caption_current_result = {"segments": self.caption_segments_accumulated}
            else:
                self.caption_current_result["segments"] = self.caption_segments_accumulated
            if hasattr(self, "_refresh_bubbles_ui"):
                self._refresh_bubbles_ui()

    def _on_embedded_caption_done(self, res, op_id=None):
        if op_id is not None and getattr(self, "caption_active_op_id", None) != op_id:
            return
        if threading.current_thread() is not threading.main_thread():
            self._dispatch_caption_ui(lambda: self._on_embedded_caption_done(res, op_id=op_id))
            return
        is_ar = (self.language_var.get() == "العربية")
        self.caption_progress_bar.stop()
        self.caption_progress_bar.configure(mode="determinate", value=100)
        if hasattr(self, "progress"):
            self.progress.stop()
            self.progress.configure(mode="determinate", value=100)
        if hasattr(self, "btn_cancel_progress"):
            self.btn_cancel_progress.grid_remove()

        self.caption_status_var.set(self.text("caption_done"))
        self.status_var.set(self.text("caption_done"))
        self.caption_start_button.configure(state="normal")
        if hasattr(self, "btn_studio_transcribe"):
            self.btn_studio_transcribe.configure(
                state="normal",
                text="🎙️ تفريغ بالذكاء الاصطناعي الآن" if is_ar else "🎙️ Transcribe Audio Now"
            )
        self.caption_stop_button.configure(state="disabled")
        self.caption_model_combo.configure(state="readonly")
        self.caption_current_result = res
        if "srt" not in res and "segments" in res:
            res["srt"] = convert.generate_srt_content(res["segments"])
        if "vtt" not in res and "segments" in res:
            res["vtt"] = convert.generate_vtt_content(res["segments"])
        self._caption_view_mode_changed()
        self._update_caption_model_status()

        target_file = self.media_files[0] if self.media_files else (Path(self.input_path) if self.input_path else None)
        base_name = target_file.stem if target_file else "captions"
        out_dir = self.output_dir or convert.OUTPUT_DIR
        out_dir.mkdir(parents=True, exist_ok=True)

    def import_from_capcut(self):
        drafts = convert.get_capcut_drafts()
        if not drafts:
            messagebox.showinfo(
                self.text("app_title"),
                self.text("caption_no_capcut_drafts"),
            )
            return

        chosen_draft = drafts[0]
        if len(drafts) > 1:
            dlg = tk.Toplevel(self)
            dlg.title(self.text("caption_capcut_dialog_title"))
            self._apply_theme_to_toplevel(dlg)
            dlg.geometry("520x340")
            dlg.transient(self)
            dlg.grab_set()
            dlg.resizable(False, False)

            is_ar = self.language_var.get() == "العربية"
            lbl = ttk.Label(
                dlg,
                text=self.text("caption_capcut_select"),
                font=("Segoe UI", 10, "bold"),
            )
            lbl.pack(anchor="e" if is_ar else "w", padx=16, pady=(16, 8))

            listbox_frame = ttk.Frame(dlg)
            listbox_frame.pack(fill="both", expand=True, padx=16, pady=4)
            scrollbar = ttk.Scrollbar(listbox_frame)
            scrollbar.pack(side="right" if not is_ar else "left", fill="y")
            is_dark = self.theme_var.get() == "dark"
            lb = tk.Listbox(
                listbox_frame,
                yscrollcommand=scrollbar.set,
                font=("Segoe UI", 10),
                selectmode="browse",
                exportselection=False,
                justify="right" if is_ar else "left",
                bg="#12151a" if is_dark else "#ffffff",
                fg="#c9d1d9" if is_dark else "#000000",
                selectbackground="#1f6feb" if is_dark else "#0078d7",
                selectforeground="#ffffff",
            )
            lb.pack(side="left" if not is_ar else "right", fill="both", expand=True)
            scrollbar.config(command=lb.yview)

            for d in drafts:
                sub_txt = f"{d['subtitle_count']} مقطع" if is_ar else f"{d['subtitle_count']} segments"
                lb.insert("end", f"📅 {d['date']} | 📝 {sub_txt} | {d['name']}")
            lb.selection_set(0)

            selected_idx = [0]
            cancelled = [False]

            def on_ok():
                sel = lb.curselection()
                if sel:
                    selected_idx[0] = sel[0]
                dlg.destroy()

            def on_cancel():
                cancelled[0] = True
                dlg.destroy()

            lb.bind("<Double-Button-1>", lambda _e: on_ok())
            dlg.bind("<Return>", lambda _e: on_ok())
            dlg.bind("<Escape>", lambda _e: on_cancel())
            dlg.protocol("WM_DELETE_WINDOW", on_cancel)

            btn_box = ttk.Frame(dlg)
            btn_box.pack(fill="x", padx=16, pady=12)
            import_txt = "استيراد الترجمة" if is_ar else "Import Subtitles"
            ttk.Button(btn_box, text=import_txt, command=on_ok, style="Action.TButton").pack(side="left" if not is_ar else "right", padx=4)
            ttk.Button(btn_box, text=self.text("close"), command=on_cancel).pack(side="right" if not is_ar else "left", padx=4)
            dlg.wait_window()

            if cancelled[0]:
                return
            chosen_draft = drafts[selected_idx[0]]

        out_dir = self.output_dir or (Path(self.media_files[0]).parent if self.media_files else Path.home())
        res = convert.extract_subtitles_from_capcut(chosen_draft["path"], output_dir=out_dir)
        if not res["segments"]:
            messagebox.showwarning(self.text("app_title"), self.text("caption_no_capcut_drafts"))
            return

        if res.get("video_path") and Path(res["video_path"]).exists():
            if not self.input_path or not self.input_path.is_file():
                self.set_source(Path(res["video_path"]))

        self._on_embedded_caption_done(res)
        self.caption_text_view.see("1.0")
        messagebox.showinfo(
            self.text("app_title"),
            self.text("caption_capcut_imported", count=len(res["segments"]), project=chosen_draft["name"]),
        )

    def _on_embedded_caption_cancel(self, op_id=None):
        if op_id is not None and getattr(self, "caption_active_op_id", None) != op_id and getattr(self, "caption_active_op_id", None) != 0:
            return
        if threading.current_thread() is not threading.main_thread():
            self._dispatch_caption_ui(lambda: self._on_embedded_caption_cancel(op_id=op_id))
            return
        is_ar = (self.language_var.get() == "العربية")
        self.caption_progress_bar.stop()
        self.caption_progress_bar.configure(mode="determinate", value=0)
        if hasattr(self, "progress"):
            self.progress.stop()
            self.progress.configure(mode="determinate", value=0)
        if hasattr(self, "btn_cancel_progress"):
            self.btn_cancel_progress.grid_remove()

        self.caption_status_var.set(self.text("canceled"))
        self.status_var.set(self.text("canceled"))
        self.caption_start_button.configure(state="normal")
        if hasattr(self, "btn_studio_transcribe"):
            self.btn_studio_transcribe.configure(
                state="normal",
                text="🎙️ تفريغ بالذكاء الاصطناعي الآن" if is_ar else "🎙️ Transcribe Audio Now"
            )
        self.caption_stop_button.configure(state="disabled")
        self.caption_burn_button.configure(state="normal")
        if hasattr(self, "caption_burn_cancel_button"):
            self.caption_burn_cancel_button.configure(state="disabled")
        self.caption_import_capcut_button.configure(state="normal")
        self.caption_model_combo.configure(state="readonly")
        self._update_caption_model_status()
        self._append_log(f"\n[Auto Caption] {self.text('canceled')}\n")

    def _on_embedded_caption_error(self, exc, op_id=None):
        if op_id is not None and getattr(self, "caption_active_op_id", None) != op_id:
            return
        if threading.current_thread() is not threading.main_thread():
            self._dispatch_caption_ui(lambda: self._on_embedded_caption_error(exc, op_id=op_id))
            return
        is_ar = (self.language_var.get() == "العربية")
        self.caption_progress_bar.stop()
        self.caption_progress_bar.configure(mode="determinate", value=0)
        if hasattr(self, "progress"):
            self.progress.stop()
            self.progress.configure(mode="determinate", value=0)
        if hasattr(self, "btn_cancel_progress"):
            self.btn_cancel_progress.grid_remove()

        self.caption_status_var.set(self.text("caption_error", error=str(exc)))
        self.status_var.set(self.text("caption_error", error=str(exc)))
        self.caption_start_button.configure(state="normal")
        if hasattr(self, "btn_studio_transcribe"):
            self.btn_studio_transcribe.configure(
                state="normal",
                text="🎙️ تفريغ بالذكاء الاصطناعي الآن" if is_ar else "🎙️ Transcribe Audio Now"
            )
        self.caption_stop_button.configure(state="disabled")
        self.caption_burn_button.configure(state="normal")
        if hasattr(self, "caption_burn_cancel_button"):
            self.caption_burn_cancel_button.configure(state="disabled")
        self.caption_import_capcut_button.configure(state="normal")
        self.caption_model_combo.configure(state="readonly")
        self._update_caption_model_status()
        self._append_log(f"\n[Auto Caption] Error: {exc}\n")
        messagebox.showerror(self.text("app_title"), self.text("caption_error", error=str(exc)))

    def cancel_embedded_caption(self):
        self.caption_cancel_event.set()
        self.caption_active_op_id = 0
        convert.abort_whisper_download()
        convert.stop_all_active_processes()
        self._on_embedded_caption_cancel()

    def copy_embedded_caption(self):
        txt = self.caption_text_view.get("1.0", "end-1c")
        if txt.strip():
            self.clipboard_clear()
            self.clipboard_append(txt)
            messagebox.showinfo(self.text("app_title"), self.text("caption_saved"))

    def save_embedded_caption_as(self):
        txt = self.caption_text_view.get("1.0", "end-1c")
        if not txt.strip():
            return
        is_srt = self.caption_view_mode_var.get() == "srt"
        def_ext = ".srt" if is_srt else ".txt"
        types = (
            [("Subtitles (.srt)", "*.srt"), ("All files", "*.*")]
            if is_srt
            else [("Text file (.txt)", "*.txt"), ("All files", "*.*")]
        )
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=def_ext,
            filetypes=types,
            initialdir=self._dialog_dir(self.output_dir),
        )
        if path:
            Path(path).write_text(txt, encoding="utf-8")
            messagebox.showinfo(self.text("app_title"), self.text("caption_saved"))

    def burn_embedded_caption(self):
        if not self.caption_current_result or not (self.caption_current_result.get("srt") or self.caption_current_result.get("segments")):
            messagebox.showwarning(self.text("app_title"), "No subtitles available to burn.")
            return

        active_candidate = self.input_path or (self.media_files[0] if self.media_files else None)
        capcut_hint = self.caption_current_result.get("video_path")

        target_video = None
        if active_candidate and Path(active_candidate).is_file():
            active_p = Path(active_candidate).resolve()
            if convert.has_video_stream(active_p):
                target_video = active_p
            else:
                matching = convert.find_matching_video(active_p, hint_path=capcut_hint)
                if matching:
                    if "_trim_" in active_p.stem:
                        a_dur = convert.get_media_duration(active_p) or 0
                        v_dur = convert.get_media_duration(matching) or 0
                        if abs(a_dur - v_dur) > 10:
                            target_video = active_p
                            self._append_log(f"\n[Auto Caption] Using trimmed audio clip: {active_p.name}\n")
                        else:
                            target_video = matching
                            self._append_log(f"\n[Auto Caption] Matched source video: {matching.name}\n")
                    else:
                        target_video = matching
                        self._append_log(f"\n[Auto Caption] Matched source video: {matching.name}\n")
                else:
                    target_video = active_p
                    self._append_log(f"\n[Auto Caption] Creating video from audio: {active_p.name}\n")
        elif capcut_hint and Path(capcut_hint).is_file():
            target_video = Path(capcut_hint).resolve()

        if not target_video:
            init_dir = (
                (self.input_path.parent if self.input_path and self.input_path.is_file() else None)
                or self.last_media_dir
                or self.output_dir
            )
            filetypes = [
                (self.text("media_files"), " ".join(f"*{ext}" for ext in sorted(convert.MEDIA_EXTS))),
                (self.text("video_files"), " ".join(f"*{ext}" for ext in sorted(convert.VIDEO_EXTS))),
                (self.text("audio_files"), " ".join(f"*{ext}" for ext in sorted(convert.AUDIO_EXTS))),
                (self.text("all_files"), "*.*"),
            ]
            chosen = filedialog.askopenfilename(
                title=self.text("caption_select_video_to_burn"),
                initialdir=self._dialog_dir(init_dir),
                filetypes=filetypes,
            )
            if not chosen:
                return
            target_video = Path(chosen).resolve()
            self.set_source(target_video)
            self.media_files = [target_video]

        out_dir = self.output_dir or convert.OUTPUT_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        srt_file = out_dir / f"{target_video.stem}_subtitles.srt"
        srt_content = self.caption_current_result.get("srt") or convert.generate_srt_content(self.caption_current_result["segments"])
        srt_file.write_text(srt_content, encoding="utf-8-sig")

        self.caption_cancel_event.clear()
        self.caption_start_button.configure(state="disabled")
        self.caption_stop_button.configure(state="normal")
        self.caption_burn_button.configure(state="disabled")
        if hasattr(self, "caption_burn_cancel_button"):
            self.caption_burn_cancel_button.configure(state="normal")
        self.caption_import_capcut_button.configure(state="disabled")
        self.caption_progress_bar.stop()
        self.caption_progress_bar.configure(mode="determinate", maximum=100, value=0)
        burn_start_time = time.monotonic()
        self.caption_status_var.set(f"{self.text('caption_burning')} (0%)")
        self._append_log(f"\n[Auto Caption] Burning subtitles to video: {target_video.name}\n")

        def worker():
            try:
                def prog_cb(pct, msg, cur, dur, tot):
                    self.after(0, lambda: self._on_embedded_burn_progress(pct, cur, tot, burn_start_time))

                out_vid = convert.burn_subtitles_to_video(
                    target_video,
                    srt_file,
                    output_dir=out_dir,
                    style_config=self.subtitle_style,
                    cancel_callback=self.caption_cancel_event.is_set,
                    progress_callback=prog_cb,
                )
                if self.caption_cancel_event.is_set():
                    self.after(0, self._on_embedded_caption_cancel)
                    return
                self.after(0, lambda: self._on_embedded_burn_done(out_vid))
            except convert.CancelledError:
                self.after(0, self._on_embedded_caption_cancel)
            except Exception as exc:
                if self.caption_cancel_event.is_set() or "cancel" in str(exc).lower():
                    self.after(0, self._on_embedded_caption_cancel)
                    return
                self.after(0, lambda: self._on_embedded_caption_error(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_embedded_burn_progress(self, percent, cur=0, tot=0, start_time=None):
        self.caption_progress_bar.configure(value=percent)
        is_ar = self.language_var.get() == "العربية"
        elapsed_str = ""
        eta_str = ""
        if start_time:
            wall_elapsed = time.monotonic() - start_time
            elapsed_str = self._format_seconds(wall_elapsed)
            if percent > 0:
                eta_sec = (wall_elapsed / percent) * (100 - percent)
                eta_str = self._format_seconds(eta_sec)
            else:
                eta_str = self.text("estimating")

        pos_str = ""
        if tot and tot > 0:
            pos_str = f" ({self._format_seconds(cur)} / {self._format_seconds(tot)})"

        if is_ar:
            status = f"جاري دمج الترجمة: {percent}%{pos_str}"
            if elapsed_str:
                status += f" | المنقضي: {elapsed_str} | المتبقي: {eta_str}"
        else:
            status = f"Burning subtitles: {percent}%{pos_str}"
            if elapsed_str:
                status += f" | Elapsed: {elapsed_str} | Remaining: {eta_str}"

        self.caption_status_var.set(status)

    def _on_embedded_burn_done(self, out_vid):
        self.caption_progress_bar.configure(value=100)
        self.caption_start_button.configure(state="normal")
        self.caption_stop_button.configure(state="disabled")
        self.caption_burn_button.configure(state="normal")
        if hasattr(self, "caption_burn_cancel_button"):
            self.caption_burn_cancel_button.configure(state="disabled")
        self.caption_import_capcut_button.configure(state="normal")
        self.caption_model_combo.configure(state="readonly")
        self._update_caption_model_status()
        msg = self.text("caption_burned_success", filename=out_vid.name)
        self.caption_status_var.set(msg)
        self._append_log(f"\n[Auto Caption] Captioned video created: {out_vid.name}\n")
        messagebox.showinfo(self.text("app_title"), msg)
