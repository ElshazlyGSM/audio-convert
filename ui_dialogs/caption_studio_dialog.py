import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import convert
from .subtitle_style_dialog import SubtitleStyleDialog


class CaptionStudioDialog(tk.Toplevel):
    def __init__(self, parent, initial_source=None, initial_output_dir=None, media_files=None):
        super().__init__(parent)
        self.parent = parent
        self.title(parent.text("caption_studio_title"))
        if hasattr(parent, "_apply_theme_to_toplevel"):
            parent._apply_theme_to_toplevel(self)
        self.geometry("900x680")
        self.minsize(800, 580)
        self.transient(parent)

        self.source_path = Path(initial_source).resolve() if initial_source else None
        self.media_files = list(media_files) if media_files else ([self.source_path] if self.source_path else [])
        if self.source_path:
            base_dir = self.source_path.parent if self.source_path.is_file() else self.source_path
            self.output_dir = Path(initial_output_dir).resolve() if initial_output_dir else (base_dir / "output")
        else:
            self.output_dir = Path(initial_output_dir).resolve() if initial_output_dir else convert.OUTPUT_DIR

        self.transcribe_thread = None
        self.cancel_event = threading.Event()
        self.current_result = None
        self.segments_accumulated = []

        is_ar = parent.language_var.get() == "العربية"
        self.is_ar = is_ar

        self.model_options = [
            ("small", "Small (465 MB) - موصى به: متوازن ودقة عالية" if is_ar else "Small (465 MB) - Recommended: High Accuracy & Balanced"),
            ("base", "Base (140 MB) - خفيف وسريع" if is_ar else "Base (140 MB) - Fast & Lightweight"),
            ("turbo", "Turbo (1.5 GB) - أعلى دقة واحترافي (NoteGPT/CapCut)" if is_ar else "Turbo (1.5 GB) - Max Accuracy / Professional (CapCut style)"),
            ("tiny", "Tiny (75 MB) - فائق السرعة (دقة منخفضة)" if is_ar else "Tiny (75 MB) - Ultra Fast (Low Accuracy)"),
            ("medium", "Medium (1.5 GB) - دقة عالية جداً" if is_ar else "Medium (1.5 GB) - Very High Accuracy"),
        ]

        self.lang_options = [
            ("auto", "كشف تلقائي للغة" if is_ar else "Auto Detect"),
            ("ar", "العربية (Arabic)"),
            ("en", "الإنجليزية (English)"),
            ("fr", "الفرنسية (French)"),
            ("es", "الإسبانية (Spanish)"),
            ("de", "الألمانية (German)"),
            ("it", "الإيطالية (Italian)"),
            ("tr", "التركية (Turkish)"),
            ("ru", "الروسية (Russian)"),
            ("zh", "الصينية (Chinese)"),
            ("ja", "اليابانية (Japanese)"),
            ("ko", "الكورية (Korean)"),
            ("ur", "الأوردو (Urdu)"),
        ]

        self.translate_options = [
            ("none", "نفس لغة الصوت الأصلية (بدون ترجمة)" if is_ar else "Original Audio Language (No Translation)"),
            ("ar", "العربية (Arabic)"),
            ("en", "الإنجليزية (English)"),
            ("fr", "الفرنسية (French)"),
            ("es", "الإسبانية (Spanish)"),
            ("de", "الألمانية (German)"),
            ("it", "الإيطالية (Italian)"),
            ("tr", "التركية (Turkish)"),
            ("ru", "الروسية (Russian)"),
            ("zh-CN", "الصينية (Chinese)"),
            ("ja", "اليابانية (Japanese)"),
            ("ko", "الكورية (Korean)"),
        ]

        saved_model = parent.settings.get("caption_model", "small")
        default_model_str = self.model_options[0][1]
        for mid, mlabel in self.model_options:
            if mid == saved_model:
                default_model_str = mlabel
                break

        saved_lang = parent.settings.get("caption_lang", "auto")
        default_lang_str = self.lang_options[0][1]
        for lid, llabel in self.lang_options:
            if lid == saved_lang:
                default_lang_str = llabel
                break

        self.source_info_var = tk.StringVar()
        self.model_var = tk.StringVar(value=default_model_str)
        self.lang_var = tk.StringVar(value=default_lang_str)
        self.translate_var = tk.StringVar(value=self.translate_options[0][1])
        self.export_srt_var = tk.BooleanVar(value=True)
        self.export_vtt_var = tk.BooleanVar(value=True)
        self.export_txt_var = tk.BooleanVar(value=True)
        self.burn_video_var = tk.BooleanVar(value=False)
        self.view_mode_var = tk.StringVar(value="text")
        self.status_var = tk.StringVar(value=parent.text("caption_ready"))
        self.progress_val_var = tk.DoubleVar(value=0)

        self._build_ui()
        self._refresh_source_info()
        self.protocol("WM_DELETE_WINDOW", self.close_dialog)

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

        header = ttk.Frame(container)
        header.pack(fill="x", pady=(0, 10))

        title_lbl = ttk.Label(
            header,
            text=self.parent.text("caption_studio_title"),
            font=("Segoe UI", 13, "bold"),
        )
        title_lbl.pack(side="left" if not self.is_ar else "right", pady=(0, 4))

        src_frame = ttk.LabelFrame(container, text=self.parent.text("caption_group"), padding=(10, 8))
        src_frame.pack(fill="x", pady=(0, 10))
        src_frame.columnconfigure(1, weight=1)

        ttk.Label(src_frame, text=self.parent.text("caption_source_label"), font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w" if not self.is_ar else "e", padx=(0, 8)
        )
        self.source_entry = ttk.Entry(src_frame, textvariable=self.source_info_var, state="readonly")
        self.source_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        browse_btn = ttk.Button(src_frame, text=self.parent.text("choose_file"), command=self._choose_file)
        browse_btn.grid(row=0, column=2, sticky="e" if not self.is_ar else "w")

        settings_frame = ttk.Frame(container)
        settings_frame.pack(fill="x", pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1)
        settings_frame.columnconfigure(3, weight=1)

        ttk.Label(settings_frame, text=self.parent.text("caption_model_label")).grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.model_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.model_var,
            values=[opt[1] for opt in self.model_options],
            state="readonly",
            width=42,
        )
        self.model_combo.grid(row=0, column=1, sticky="ew", padx=(0, 16))
        self.model_combo.bind("<<ComboboxSelected>>", self._update_model_status)

        self.model_status_var = tk.StringVar(value="")
        model_status_box = ttk.Frame(settings_frame)
        model_status_box.grid(row=1, column=1, sticky="ew", pady=(2, 0))
        self.model_status_label = ttk.Label(model_status_box, textvariable=self.model_status_var, font=("Segoe UI", 8, "bold"))
        self.model_status_label.pack(side="left", padx=(0, 6))
        self.download_model_btn = ttk.Button(
            model_status_box,
            text=self.parent.text("caption_download_model_btn"),
            command=self.download_current_model,
            style="Player.TButton",
        )
        self.download_model_btn.pack(side="left")

        ttk.Label(settings_frame, text=self.parent.text("caption_lang_label")).grid(row=0, column=2, sticky="w", padx=(0, 6))
        self.lang_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.lang_var,
            values=[opt[1] for opt in self.lang_options],
            state="readonly",
            width=20,
        )
        self.lang_combo.grid(row=0, column=3, sticky="w")

        ttk.Label(settings_frame, text=self.parent.text("caption_translate_label")).grid(row=2, column=0, sticky="w", padx=(0, 6), pady=(6, 0))
        self.translate_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.translate_var,
            values=[opt[1] for opt in self.translate_options],
            state="readonly",
            width=28,
        )
        self.translate_combo.grid(row=2, column=1, sticky="w", padx=(0, 16), pady=(6, 0))

        dir_frame = ttk.Frame(container)
        dir_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(dir_frame, text=self.parent.text("caption_models_dir"), font=("Segoe UI", 8)).pack(side="left", padx=(0, 4))
        models_dir = convert.get_whisper_models_dir()
        ttk.Label(dir_frame, text=str(models_dir), foreground="#555555", font=("Segoe UI", 8)).pack(side="left", padx=(0, 8))
        ttk.Button(
            dir_frame,
            text=self.parent.text("caption_open_models_dir"),
            command=lambda: self.parent.open_folder(models_dir),
            style="Player.TButton",
        ).pack(side="left")

        self._update_model_status()

        chk_frame = ttk.Frame(container)
        chk_frame.pack(fill="x", pady=(0, 10))

        self.srt_check = ttk.Checkbutton(chk_frame, text=self.parent.text("caption_export_srt"), variable=self.export_srt_var)
        self.srt_check.pack(side="left", padx=(0, 14))

        self.vtt_check = ttk.Checkbutton(chk_frame, text=self.parent.text("caption_export_vtt"), variable=self.export_vtt_var)
        self.vtt_check.pack(side="left", padx=(0, 14))

        self.txt_check = ttk.Checkbutton(chk_frame, text=self.parent.text("caption_export_txt"), variable=self.export_txt_var)
        self.txt_check.pack(side="left", padx=(0, 14))

        self.burn_check = ttk.Checkbutton(
            chk_frame,
            text=self.parent.text("caption_burn_video"),
            variable=self.burn_video_var,
        )
        self.burn_check.pack(side="left", padx=(0, 14))

        ctrl_frame = ttk.Frame(container)
        ctrl_frame.pack(fill="x", pady=(0, 10))
        ctrl_frame.columnconfigure(3, weight=1)

        self.start_btn = ttk.Button(
            ctrl_frame,
            text=self.parent.text("caption_start"),
            command=self.start_transcription,
            style="PrimaryPlayer.TButton",
            width=18,
        )
        self.start_btn.grid(row=0, column=0, sticky="w", padx=(0, 6))

        self.stop_btn = ttk.Button(
            ctrl_frame,
            text=self.parent.text("caption_stop"),
            command=self.cancel_transcription,
            state="disabled",
            width=8,
        )
        self.stop_btn.grid(row=0, column=1, sticky="w", padx=(0, 6))

        self.import_capcut_btn = ttk.Button(
            ctrl_frame,
            text=self.parent.text("caption_import_capcut"),
            command=self.import_from_capcut,
        )
        self.import_capcut_btn.grid(row=0, column=2, sticky="w", padx=(0, 10))

        self.prog_bar = ttk.Progressbar(ctrl_frame, variable=self.progress_val_var, maximum=100)
        self.prog_bar.grid(row=0, column=3, sticky="ew")

        status_lbl = ttk.Label(container, textvariable=self.status_var, font=("Segoe UI", 9), foreground="#333333")
        status_lbl.pack(fill="x", pady=(0, 6))

        res_header = ttk.Frame(container)
        res_header.pack(fill="x", pady=(2, 4))

        title_res = "📝 " + ("Extracted Transcript" if not self.is_ar else "النص المستخرج")
        ttk.Label(res_header, text=title_res, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 14))

        self.radio_txt = ttk.Radiobutton(
            res_header,
            text=self.parent.text("caption_tab_text"),
            variable=self.view_mode_var,
            value="text",
            command=self._view_mode_changed,
        )
        self.radio_txt.pack(side="left", padx=(0, 10))

        self.radio_srt = ttk.Radiobutton(
            res_header,
            text=self.parent.text("caption_tab_srt"),
            variable=self.view_mode_var,
            value="srt",
            command=self._view_mode_changed,
        )
        self.radio_srt.pack(side="left")

        text_frame = ttk.Frame(container)
        text_frame.pack(fill="both", expand=True, pady=(0, 10))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        is_dark = getattr(getattr(self, "parent", None), "theme_var", None) and self.parent.theme_var.get() == "dark"
        self.text_widget = tk.Text(
            text_frame,
            wrap="word",
            font=("Segoe UI", 10),
            padx=8,
            pady=8,
            bg="#12151a" if is_dark else "#ffffff",
            fg="#c9d1d9" if is_dark else "#000000",
            insertbackground="#58a6ff" if is_dark else "#000000",
        )
        self.text_widget.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.text_widget.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.text_widget.configure(yscrollcommand=scrollbar.set)
        self._attach_text_context_menu(self.text_widget)

        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill="x")

        self.copy_btn = ttk.Button(btn_bar, text="📋 " + self.parent.text("caption_copy"), command=self.copy_text)
        self.copy_btn.pack(side="left", padx=(0, 8))

        self.save_btn = ttk.Button(btn_bar, text="💾 " + self.parent.text("caption_save_as"), command=self.save_as)
        self.save_btn.pack(side="left", padx=(0, 8))

        self.burn_btn = ttk.Button(btn_bar, text="🎬 " + self.parent.text("caption_burn_now"), command=self.burn_subtitles_now)
        self.burn_btn.pack(side="left", padx=(0, 8))

        self.style_btn = ttk.Button(btn_bar, text=self.parent.text("caption_style_btn"), command=self.open_subtitle_style_dialog, style="Player.TButton")
        self.style_btn.pack(side="left", padx=(0, 8))

        self.branding_btn = ttk.Button(btn_bar, text=self.parent.text("branding_btn"), command=self.open_video_branding_dialog, style="Player.TButton")
        self.branding_btn.pack(side="left", padx=(0, 8))

        self.trans_btn = ttk.Button(btn_bar, text=self.parent.text("caption_translate_btn"), command=self.translate_current_text)
        self.trans_btn.pack(side="left", padx=(0, 8))

        self.folder_btn = ttk.Button(btn_bar, text="📂 " + self.parent.text("caption_open_folder"), command=self.open_output_folder)
        self.folder_btn.pack(side="left", padx=(0, 8))

        self.close_btn = ttk.Button(btn_bar, text=self.parent.text("close"), command=self.close_dialog)
        self.close_btn.pack(side="right")

    def open_subtitle_style_dialog(self):
        dlg = SubtitleStyleDialog(self)
        dlg.grab_set()

    def open_video_branding_dialog(self):
        from .video_branding_dialog import VideoBrandingDialog
        dlg = VideoBrandingDialog(self)
        dlg.grab_set()

    def _refresh_source_info(self):
        if self.source_path and self.source_path.is_file():
            dur_str = ""
            try:
                sec = convert.get_media_duration(self.source_path)
                if sec:
                    dur_str = f" ({self.parent._format_time(sec)})"
            except Exception:
                pass
            self.source_info_var.set(f"{self.source_path.name}{dur_str}")
        elif self.media_files and len(self.media_files) > 1:
            self.source_info_var.set(self.parent.text("caption_folder_label", count=len(self.media_files)))
        else:
            self.source_info_var.set(self.parent.text("source_empty"))

        has_media = bool(self.source_path and self.source_path.is_file())
        has_subs = bool(self.current_result and (self.current_result.get("srt_path") or self.current_result.get("segments")))
        if has_media:
            self.burn_check.configure(state="normal")
        else:
            self.burn_video_var.set(False)
            self.burn_check.configure(state="disabled")
        self.burn_btn.configure(state="normal" if has_subs else "disabled")

    def _is_current_video(self):
        if not self.source_path or not self.source_path.is_file():
            return False
        return self.source_path.suffix.lower() in convert.VIDEO_EXTS

    def _choose_file(self):
        filetypes = [
            (self.parent.text("media_files"), " ".join(f"*{ext}" for ext in sorted(convert.MEDIA_EXTS))),
            (self.parent.text("audio_files"), " ".join(f"*{ext}" for ext in sorted(convert.AUDIO_EXTS))),
            (self.parent.text("video_files"), " ".join(f"*{ext}" for ext in sorted(convert.VIDEO_EXTS))),
            (self.parent.text("all_files"), "*.*"),
        ]
        init_dir = (
            (self.source_path.parent if self.source_path and self.source_path.is_file() else None)
            or self.parent.last_media_dir
            or (self.parent.input_path.parent if self.parent.input_path else None)
            or self.output_dir
        )
        selected = filedialog.askopenfilename(
            title=self.parent.text("file_title"),
            initialdir=self.parent._dialog_dir(init_dir),
            filetypes=filetypes,
        )
        if selected:
            self.source_path = Path(selected).resolve()
            self.media_files = [self.source_path]
            self.output_dir = self.source_path.parent / "output"
            self.current_result = None
            self.segments_accumulated = []
            self.text_widget.delete("1.0", "end")
            self._refresh_source_info()
            self.status_var.set(self.parent.text("caption_ready"))
            self.progress_val_var.set(0)

    def _get_model_id(self):
        val = self.model_var.get()
        for mid, label in self.model_options:
            if label == val:
                return mid
        return "turbo"

    def _get_selected_model_id(self):
        return self._get_model_id()

    def _get_lang_code(self):
        val = self.lang_var.get()
        for lid, label in self.lang_options:
            if label == val:
                return None if lid == "auto" else lid
        return None

    def _get_translate_code(self):
        val = self.translate_var.get()
        for tid, label in self.translate_options:
            if label == val:
                return None if tid == "none" else tid
        return None

    def translate_current_text(self):
        target_lang = self._get_translate_code()
        if not target_lang:
            messagebox.showinfo(self.parent.text("app_title"), self.parent.text("caption_translate_label"))
            return
        if not self.current_result and not self.segments_accumulated:
            return

        def worker():
            try:
                self.after(0, lambda: self.status_var.set(self.parent.text("caption_translating", target=target_lang)))
                orig_segments = self.current_result["segments"] if self.current_result else self.segments_accumulated
                translated = convert.translate_segments(orig_segments, target_lang=target_lang)
                if self.current_result:
                    self.current_result["segments"] = translated
                    self.current_result["text"] = "\n".join(s["text"] for s in translated)
                self.segments_accumulated = translated
                self.after(0, self._refresh_text_display)
                self.after(0, lambda: self.status_var.set(self.parent.text("caption_translate_done", target=target_lang)))
            except Exception as exc:
                self.after(0, lambda: self.status_var.set(f"Translation error: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def _view_mode_changed(self):
        self._refresh_text_display()

    def _refresh_text_display(self):
        mode = self.view_mode_var.get()
        self.text_widget.delete("1.0", "end")
        if self.current_result:
            if mode == "text":
                self.text_widget.insert("1.0", self.current_result["text"])
            else:
                self.text_widget.insert("1.0", convert.generate_srt_content(self.current_result["segments"]))
        elif self.segments_accumulated:
            if mode == "text":
                txt = " ".join(s["text"] for s in self.segments_accumulated)
                self.text_widget.insert("1.0", txt)
            else:
                self.text_widget.insert("1.0", convert.generate_srt_content(self.segments_accumulated))

    def _attach_text_context_menu(self, widget):
        def show_menu(event):
            menu = tk.Menu(widget, tearoff=False)
            menu.add_command(label=self.parent.text("copy"), command=self.copy_text)
            menu.add_command(label=self.parent.text("select_all"), command=lambda: widget.tag_add("sel", "1.0", "end"))
            menu.tk_popup(event.x_root, event.y_root)

        widget.bind("<Button-3>", show_menu)

    def start_transcription(self):
        if self.transcribe_thread and self.transcribe_thread.is_alive():
            return

        if not convert.whisper_available():
            messagebox.showerror(
                self.parent.text("app_title"),
                "faster-whisper is not installed.\nPlease run: py -3.12 -m pip install faster-whisper",
            )
            return

        if not self.source_path and not self.media_files:
            messagebox.showwarning(self.parent.text("app_title"), self.parent.text("caption_no_source"))
            return

        # Save chosen settings
        model_id = self._get_model_id()
        lang_code = self._get_lang_code()
        translate_code = self._get_translate_code()
        self.parent.settings["caption_model"] = model_id
        self.parent.settings["caption_lang"] = lang_code or "auto"
        self.parent._save_settings()

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.burn_btn.configure(state="disabled")
        self.progress_val_var.set(0)
        self.status_var.set(self.parent.text("caption_loading"))
        self.cancel_event.clear()
        self.segments_accumulated = []
        self.current_result = None
        self.text_widget.delete("1.0", "end")

        is_folder = (self.source_path and self.source_path.is_dir()) or len(self.media_files) > 1

        self.transcribe_thread = threading.Thread(
            target=self._run_transcription,
            args=(
                self.source_path,
                is_folder,
                self.media_files,
                model_id,
                lang_code,
                translate_code,
                self.export_srt_var.get(),
                self.export_vtt_var.get(),
                self.export_txt_var.get(),
                self.burn_video_var.get(),
            ),
            daemon=True,
        )
        self.transcribe_thread.start()

    def _run_transcription(
        self,
        source_path,
        is_folder,
        media_files,
        model_id,
        lang_code,
        translate_code,
        export_srt,
        export_vtt,
        export_txt,
        burn_video,
    ):
        try:
            self.start_time = time.monotonic()
            if is_folder and len(media_files) > 1:
                total_files = len(media_files)
                for idx, fpath in enumerate(media_files):
                    if self.cancel_event.is_set():
                        raise convert.CancelledError("Operation canceled")

                    def _seg_cb(pct, seg_text, start, end, dur):
                        self.after(0, lambda p=pct, t=seg_text, s=start, e=end: self._on_segment(p, t, s, e, dur))

                    convert.transcribe_media(
                        source_path=fpath,
                        output_dir=self.output_dir,
                        model_size=model_id,
                        language=lang_code,
                        translate_to=translate_code,
                        export_srt=export_srt,
                        export_vtt=export_vtt,
                        export_txt=export_txt,
                        burn_to_video=burn_video,
                        progress_callback=_seg_cb,
                        cancel_callback=lambda: self.cancel_event.is_set(),
                    )
                self.after(0, lambda: self._on_finished(None, is_batch=True))
            else:
                target_file = source_path or (media_files[0] if media_files else None)
                if not target_file:
                    raise FileNotFoundError("No source file selected")

                def _seg_cb(pct, seg_text, start, end, dur):
                    self.after(0, lambda p=pct, t=seg_text, s=start, e=end: self._on_segment(p, t, s, e, dur))

                res = convert.transcribe_media(
                    source_path=target_file,
                    output_dir=self.output_dir,
                    model_size=model_id,
                    language=lang_code,
                    translate_to=translate_code,
                    export_srt=export_srt,
                    export_vtt=export_vtt,
                    export_txt=export_txt,
                    burn_to_video=burn_video,
                    progress_callback=_seg_cb,
                    cancel_callback=lambda: self.cancel_event.is_set(),
                )
                self.after(0, lambda: self._on_finished(res, is_batch=False))
        except convert.CancelledError:
            self.after(0, self._on_cancelled)
        except Exception as exc:
            self.after(0, lambda: self._on_error(str(exc)))

    def _update_model_status(self, _e=None):
        mid = self._get_selected_model_id()
        status = convert.get_whisper_model_status(mid)
        if status["is_downloaded"]:
            self.model_status_var.set(self.parent.text("caption_model_status_ready"))
            if hasattr(self, "model_status_label"):
                self.model_status_label.configure(foreground="#008800")
            if hasattr(self, "download_model_btn"):
                self.download_model_btn.configure(state="disabled", text=self.parent.text("caption_model_ready_btn"))
        else:
            self.model_status_var.set(
                self.parent.text("caption_model_status_needs_download", size=int(status["estimated_mb"]))
            )
            if hasattr(self, "model_status_label"):
                self.model_status_label.configure(foreground="#cc6600")
            if hasattr(self, "download_model_btn"):
                self.download_model_btn.configure(state="normal", text=self.parent.text("caption_download_model_btn"))

    def download_current_model(self):
        mid = self._get_selected_model_id()
        status = convert.get_whisper_model_status(mid)
        if status["is_downloaded"]:
            messagebox.showinfo(self.parent.text("app_title"), self.parent.text("caption_model_status_ready"))
            return

        self.cancel_event.clear()
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        if hasattr(self, "download_model_btn"):
            self.download_model_btn.configure(state="disabled")
        self.model_combo.configure(state="disabled")
        self.progress_bar.configure(mode="determinate", value=0)

        def prog_cb(pct, dl_bytes, tot_bytes, fname, speed, eta, tdir):
            dl_mb = dl_bytes / (1024 * 1024)
            tot_mb = tot_bytes / (1024 * 1024)
            eta_part = f" - {eta}" if eta else ""
            msg = self.parent.text(
                "caption_downloading_model",
                model=mid,
                dl_mb=dl_mb,
                tot_mb=tot_mb,
                pct=pct,
                speed=speed,
                eta_part=eta_part,
            )
            self.after(0, lambda: self.status_var.set(msg))
            self.after(0, lambda: self.progress_val_var.set(pct))

        def worker():
            try:
                convert.download_whisper_model(
                    model_size=mid,
                    progress_callback=prog_cb,
                    cancel_callback=self.cancel_event.is_set,
                )
                if self.cancel_event.is_set():
                    self.after(0, self._on_cancelled)
                    return
                self.after(0, lambda: self._on_model_download_done(mid))
            except convert.CancelledError:
                self.after(0, self._on_cancelled)
            except Exception as exc:
                if self.cancel_event.is_set() or "cancel" in str(exc).lower():
                    self.after(0, self._on_cancelled)
                    return
                self.after(0, lambda: self._on_error(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_model_download_done(self, model_id):
        self.progress_val_var.set(100)
        self.status_var.set(self.parent.text("caption_download_complete", model=model_id))
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.model_combo.configure(state="readonly")
        self._update_model_status()
        messagebox.showinfo(
            self.parent.text("app_title"),
            self.parent.text("caption_download_complete", model=model_id),
        )

    def _on_segment(self, percent, seg_text, start, end, duration):
        if not seg_text:
            return
        self.progress_val_var.set(percent)
        if seg_text.startswith("Downloading AI model") or seg_text.startswith("جاري تحميل") or "Loading Whisper" in seg_text:
            self.status_var.set(seg_text)
            return

        self.segments_accumulated.append({"start": start, "end": end, "text": seg_text})
        preview_text = seg_text if len(seg_text) < 35 else seg_text[:32] + "..."

        is_ar = self.parent.language_var.get() == "العربية"
        elapsed_str = ""
        eta_str = ""
        if hasattr(self, "start_time") and self.start_time:
            wall_elapsed = time.monotonic() - self.start_time
            elapsed_str = self.parent._format_seconds(wall_elapsed)
            if percent > 0:
                eta_sec = (wall_elapsed / percent) * (100 - percent)
                eta_str = self.parent._format_seconds(eta_sec)
            else:
                eta_str = self.parent.text("estimating")

        pos_str = ""
        if duration and duration > 0:
            pos_str = f" ({self.parent._format_seconds(end)} / {self.parent._format_seconds(duration)})"

        if is_ar:
            status = f"جاري التفريغ: {percent}%{pos_str}"
            if elapsed_str:
                status += f" | المنقضي: {elapsed_str} | المتبقي: ~{eta_str}"
        else:
            status = f"Transcribing: {percent}%{pos_str}"
            if elapsed_str:
                status += f" | Elapsed: {elapsed_str} | Remaining: ~{eta_str}"

        self.status_var.set(f"{status}: {preview_text}")

        mode = self.view_mode_var.get()
        if mode == "text":
            self.text_widget.insert("end", f"{seg_text} ")
        else:
            ts = convert.format_timestamp_srt(start)
            self.text_widget.insert("end", f"[{ts}] {seg_text}\n")
        self.text_widget.see("end")

    def _on_finished(self, result, is_batch=False):
        self.current_result = result
        self.progress_val_var.set(100)
        self.status_var.set(self.parent.text("caption_done"))
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.burn_btn.configure(state="normal")
        self._update_model_status()

        if result:
            self._refresh_text_display()
            self._refresh_source_info()
            fname = self.source_path.name if self.source_path else "file"
            self.parent._append_log(f"\n[Auto Caption] Done transcribing {fname}\n")
            if result.get("srt_path"):
                self.parent._append_log(f"[Auto Caption] Saved SRT: {result['srt_path']}\n")
            if result.get("burned_video"):
                self.parent._append_log(f"[Auto Caption] Captioned video: {result['burned_video']}\n")
                messagebox.showinfo(
                    self.parent.text("app_title"),
                    self.parent.text("caption_burned_success", filename=Path(result["burned_video"]).name),
                )
            self.text_widget.see("1.0")
        elif is_batch:
            self.text_widget.delete("1.0", "end")
            msg = f"Batch transcription completed for {len(self.media_files)} files.\nSaved to: {self.output_dir}"
            self.text_widget.insert("1.0", msg)
            self.parent._append_log(f"\n[Auto Caption] Batch completed for {len(self.media_files)} files.\n")

    def _on_cancelled(self):
        self.status_var.set(self.parent.text("canceled"))
        self.progress_val_var.set(0)
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.burn_btn.configure(state="normal")
        self.model_combo.configure(state="readonly")
        self._update_model_status()
        self._refresh_source_info()
        self.parent._append_log("\n[Auto Caption] Operation canceled.\n")

    def _on_error(self, err_msg):
        self.status_var.set(self.parent.text("caption_error", error=err_msg))
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.model_combo.configure(state="readonly")
        self._update_model_status()
        self._refresh_source_info()
        messagebox.showerror(self.parent.text("app_title"), self.parent.text("caption_error", error=err_msg))

    def cancel_transcription(self):
        self.cancel_event.set()
        convert.abort_whisper_download()
        self.status_var.set(self.parent.text("canceling"))
        self.stop_btn.configure(state="disabled")

    def copy_text(self):
        content = self.text_widget.get("1.0", "end-1c").strip()
        if not content:
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        orig = self.copy_btn.cget("text")
        self.copy_btn.configure(text=f"✓ {self.parent.text('copied')}")
        self.after(1400, lambda: self.copy_btn.configure(text=orig))

    def save_as(self):
        content = self.text_widget.get("1.0", "end-1c").strip()
        if not content:
            return
        mode = self.view_mode_var.get()
        ext = ".srt" if mode == "srt" else ".txt"
        base_name = f"{self.source_path.stem if self.source_path else 'transcript'}{ext}"
        init_dir = str(self.output_dir if self.output_dir.exists() else convert.APP_DIR)
        selected = filedialog.asksaveasfilename(
            title=self.parent.text("caption_save_as"),
            initialdir=init_dir,
            initialfile=base_name,
            filetypes=[("Text file", "*.txt"), ("SRT Subtitle", "*.srt"), ("All files", "*.*")],
            defaultextension=ext,
        )
        if selected:
            Path(selected).write_text(content, encoding="utf-8")
            messagebox.showinfo(self.parent.text("app_title"), self.parent.text("caption_saved"))

    def burn_subtitles_now(self):
        target_media = None
        capcut_hint = self.current_result.get("video_path") if self.current_result else None
        if self.source_path and self.source_path.is_file():
            if convert.has_video_stream(self.source_path):
                target_media = self.source_path
            else:
                matching = convert.find_matching_video(self.source_path, hint_path=capcut_hint)
                if matching:
                    if "_trim_" in self.source_path.stem:
                        a_dur = convert.get_media_duration(self.source_path) or 0
                        v_dur = convert.get_media_duration(matching) or 0
                        if abs(a_dur - v_dur) > 10:
                            target_media = self.source_path
                        else:
                            target_media = matching
                    else:
                        target_media = matching
                else:
                    target_media = self.source_path
        elif capcut_hint and Path(capcut_hint).is_file():
            target_media = Path(capcut_hint).resolve()

        if not target_media:
            init_dir = (
                (self.source_path.parent if self.source_path and self.source_path.is_file() else None)
                or self.output_dir
                or self.parent.last_media_dir
            )
            filetypes = [
                (self.parent.text("media_files"), " ".join(f"*{ext}" for ext in sorted(convert.MEDIA_EXTS))),
                (self.parent.text("video_files"), " ".join(f"*{ext}" for ext in sorted(convert.VIDEO_EXTS))),
                (self.parent.text("audio_files"), " ".join(f"*{ext}" for ext in sorted(convert.AUDIO_EXTS))),
                (self.parent.text("all_files"), "*.*"),
            ]
            chosen = filedialog.askopenfilename(
                title=self.parent.text("caption_select_video_to_burn"),
                initialdir=self.parent._dialog_dir(init_dir),
                filetypes=filetypes,
            )
            if not chosen:
                return
            target_media = Path(chosen).resolve()

        self.source_path = target_media
        self._refresh_source_info()

        if self.current_result and self.current_result.get("srt_path") and Path(self.current_result["srt_path"]).exists():
            srt_path = Path(self.current_result["srt_path"])
        else:
            srt_path = self.output_dir / f"{self.source_path.stem}.srt"
            if not srt_path.exists():
                if self.current_result and self.current_result.get("segments"):
                    srt_path.write_text(convert.generate_srt_content(self.current_result["segments"]), encoding="utf-8-sig")
                else:
                    messagebox.showwarning(self.parent.text("app_title"), "Please transcribe or import subtitles first.")
                    return

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.burn_btn.configure(state="disabled")
        self.status_var.set(f"{self.parent.text('caption_burning')} (0%)")
        self.progress_val_var.set(0)
        self.cancel_event.clear()
        burn_start_time = time.monotonic()

        def _worker():
            try:
                def _prog(pct, msg, cur, dur, tot):
                    self.after(0, lambda: self._on_burn_progress(pct, msg, cur, tot, burn_start_time))

                out_vid = convert.burn_subtitles_to_video(
                    video_path=self.source_path,
                    srt_path=srt_path,
                    output_dir=self.output_dir,
                    style_config=getattr(self.parent, "subtitle_style", None),
                    cancel_callback=lambda: self.cancel_event.is_set(),
                    progress_callback=_prog,
                )
                if self.cancel_event.is_set():
                    self.after(0, self._on_cancelled)
                    return
                self.after(0, lambda: self._on_burn_done(out_vid))
            except convert.CancelledError:
                self.after(0, self._on_cancelled)
            except Exception as exc:
                if self.cancel_event.is_set() or "cancel" in str(exc).lower():
                    self.after(0, self._on_cancelled)
                    return
                self.after(0, lambda: self._on_error(str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_burn_progress(self, percent, msg, cur=0, tot=0, start_time=None):
        self.progress_val_var.set(percent)
        is_ar = self.parent.language_var.get() == "العربية"
        elapsed_str = ""
        eta_str = ""
        if start_time:
            wall_elapsed = time.monotonic() - start_time
            elapsed_str = self.parent._format_seconds(wall_elapsed)
            if percent > 0:
                eta_sec = (wall_elapsed / percent) * (100 - percent)
                eta_str = self.parent._format_seconds(eta_sec)
            else:
                eta_str = self.parent.text("estimating")

        pos_str = ""
        if tot and tot > 0:
            pos_str = f" ({self.parent._format_seconds(cur)} / {self.parent._format_seconds(tot)})"

        if is_ar:
            status = f"جاري دمج الترجمة: {percent}%{pos_str}"
            if elapsed_str:
                status += f" | المنقضي: {elapsed_str} | المتبقي: ~{eta_str}"
        else:
            status = f"Burning subtitles: {percent}%{pos_str}"
            if elapsed_str:
                status += f" | Elapsed: {elapsed_str} | Remaining: ~{eta_str}"

        self.status_var.set(status)

    def _on_burn_done(self, out_vid):
        self.progress_val_var.set(100)
        self.status_var.set(self.parent.text("caption_done"))
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.burn_btn.configure(state="normal")
        self.parent._append_log(f"\n[Auto Caption] Burned subtitles video: {out_vid.name}\n")
        messagebox.showinfo(
            self.parent.text("app_title"),
            self.parent.text("caption_burned_success", filename=out_vid.name),
        )

    def open_output_folder(self):
        folder = self.output_dir
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)
        self.parent.open_folder(folder)

    def import_from_capcut(self):
        drafts = convert.get_capcut_drafts()
        if not drafts:
            messagebox.showinfo(
                self.parent.text("app_title"),
                self.parent.text("caption_no_capcut_drafts"),
            )
            return

        chosen_draft = drafts[0]
        if len(drafts) > 1:
            dlg = tk.Toplevel(self)
            dlg.title(self.parent.text("caption_capcut_dialog_title"))
            if hasattr(self.parent, "_apply_theme_to_toplevel"):
                self.parent._apply_theme_to_toplevel(dlg)
            dlg.geometry("520x340")
            dlg.transient(self)
            dlg.grab_set()
            dlg.resizable(False, False)

            lbl = ttk.Label(
                dlg,
                text=self.parent.text("caption_capcut_select"),
                font=("Segoe UI", 10, "bold"),
            )
            lbl.pack(anchor="e" if self.is_ar else "w", padx=16, pady=(16, 8))

            listbox_frame = ttk.Frame(dlg)
            listbox_frame.pack(fill="both", expand=True, padx=16, pady=4)
            scrollbar = ttk.Scrollbar(listbox_frame)
            scrollbar.pack(side="right" if not self.is_ar else "left", fill="y")
            is_dark = getattr(getattr(self, "parent", None), "theme_var", None) and self.parent.theme_var.get() == "dark"
            lb = tk.Listbox(
                listbox_frame,
                yscrollcommand=scrollbar.set,
                font=("Segoe UI", 10),
                selectmode="browse",
                exportselection=False,
                justify="right" if self.is_ar else "left",
                bg="#12151a" if is_dark else "#ffffff",
                fg="#c9d1d9" if is_dark else "#000000",
                selectbackground="#1f6feb" if is_dark else "#0078d7",
                selectforeground="#ffffff",
            )
            lb.pack(side="left" if not self.is_ar else "right", fill="both", expand=True)
            scrollbar.config(command=lb.yview)

            for d in drafts:
                sub_txt = f"{d['subtitle_count']} مقطع" if self.is_ar else f"{d['subtitle_count']} segments"
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
            import_txt = "استيراد الترجمة" if self.is_ar else "Import Subtitles"
            ttk.Button(btn_box, text=import_txt, command=on_ok, style="Action.TButton").pack(side="left" if not self.is_ar else "right", padx=4)
            ttk.Button(btn_box, text=self.parent.text("close"), command=on_cancel).pack(side="right" if not self.is_ar else "left", padx=4)
            dlg.wait_window()

            if cancelled[0]:
                return
            chosen_draft = drafts[selected_idx[0]]

        out_dir = self.output_dir or Path.home()
        res = convert.extract_subtitles_from_capcut(chosen_draft["path"], output_dir=out_dir)
        if not res["segments"]:
            messagebox.showwarning(self.parent.text("app_title"), self.parent.text("caption_no_capcut_drafts"))
            return

        if res.get("video_path") and Path(res["video_path"]).exists():
            if not self.source_path or not self.source_path.is_file():
                self.source_path = Path(res["video_path"])
                self._refresh_source_info()

        self._on_finished(res, is_batch=False)
        self.text_widget.see("1.0")
        messagebox.showinfo(
            self.parent.text("app_title"),
            self.parent.text("caption_capcut_imported", count=len(res["segments"]), project=chosen_draft["name"]),
        )

    def close_dialog(self):
        if self.transcribe_thread and self.transcribe_thread.is_alive():
            if not messagebox.askyesno(self.parent.text("app_title"), self.parent.text("close_running")):
                return
            self.cancel_event.set()
            convert.abort_whisper_download()
        convert.abort_whisper_download()
        self.destroy()


