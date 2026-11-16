"""
Silence Workflow Mixin
Handles Silence Cut Tab UI, detection, preview playback, interactive timeline, and batch silence export.
"""

import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from video_studio.silence_remover import (
    SILENCE_PRESETS,
    SILENCE_MODES,
    SILENCE_QUALITIES,
    SILENCE_FORMATS,
    summarize_silence_analysis,
    remap_subtitles_for_cuts,
)
import convert


class SilenceWorkflowMixin:
    """Provides Smart Silence Detection, Jump Cut tab and export workflows."""

    def _build_tab_silence(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        # Top Card: Smart Silence Detection & Jump-Cut Settings
        settings_box = ttk.LabelFrame(parent, padding=(12, 10, 12, 10))
        settings_box.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        settings_box.columnconfigure(1, weight=1)
        settings_box.columnconfigure(3, weight=1)
        self.i18n_widgets["silence_settings_group"] = settings_box

        # Row 0: Smart Preset & Action Mode
        self.i18n_widgets["silence_preset_label"] = ttk.Label(settings_box, font=("Segoe UI", 9, "bold"))
        self.i18n_widgets["silence_preset_label"].grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.silence_preset_combo = ttk.Combobox(
            settings_box, textvariable=self.silence_preset_var, state="readonly", width=34
        )
        self.silence_preset_combo.grid(row=0, column=1, sticky="ew", padx=(6, 14), pady=(0, 6))
        self.silence_preset_combo.bind("<<ComboboxSelected>>", self._on_silence_preset_changed)

        self.i18n_widgets["silence_mode_label"] = ttk.Label(settings_box, font=("Segoe UI", 9, "bold"))
        self.i18n_widgets["silence_mode_label"].grid(row=0, column=2, sticky="w", pady=(0, 6))
        self.silence_mode_combo = ttk.Combobox(
            settings_box, textvariable=self.silence_mode_var, state="readonly", width=34
        )
        self.silence_mode_combo.grid(row=0, column=3, columnspan=2, sticky="ew", padx=(6, 0), pady=(0, 6))
        self.silence_mode_combo.bind("<<ComboboxSelected>>", self._on_silence_mode_changed)

        # Row 1: Silence Threshold Slider + Auto Detect dB Button
        self.i18n_widgets["silence_threshold_label"] = ttk.Label(settings_box)
        self.i18n_widgets["silence_threshold_label"].grid(row=1, column=0, sticky="w", pady=(0, 6))

        thresh_frame = ttk.Frame(settings_box)
        thresh_frame.grid(row=1, column=1, columnspan=4, sticky="ew", padx=(6, 0), pady=(0, 6))
        thresh_frame.columnconfigure(0, weight=1)

        self.silence_noise_scale = ttk.Scale(
            thresh_frame,
            from_=-55.0,
            to=-18.0,
            variable=self.silence_noise_db_var,
            orient="horizontal",
            command=self._on_silence_noise_changed,
        )
        self.silence_noise_scale.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.silence_noise_display = ttk.Label(
            thresh_frame, textvariable=self.silence_noise_label_var, font=("Segoe UI", 10, "bold"), foreground="#cc3300", width=10
        )
        self.silence_noise_display.grid(row=0, column=1, padx=(0, 10))

        self.silence_auto_db_button = ttk.Button(
            thresh_frame,
            text=self.text("silence_auto_threshold"),
            command=self.start_auto_detect_silence_db,
            style="Player.TButton",
        )
        self.silence_auto_db_button.grid(row=0, column=2, sticky="e")

        # Row 2: Min Silence Duration, Speech Padding & Auto-Sync Subtitles
        params_row = ttk.Frame(settings_box)
        params_row.grid(row=2, column=0, columnspan=5, sticky="ew", pady=(2, 8))

        self.i18n_widgets["silence_min_dur_label"] = ttk.Label(params_row)
        self.i18n_widgets["silence_min_dur_label"].pack(side="left", padx=(0, 6))
        self.silence_min_dur_spin = ttk.Spinbox(
            params_row,
            from_=0.10,
            to=5.00,
            increment=0.05,
            textvariable=self.silence_min_dur_var,
            width=7,
            font=("Consolas", 10, "bold"),
            justify="center",
        )
        self.silence_min_dur_spin.pack(side="left", padx=(0, 16))

        self.i18n_widgets["silence_padding_label"] = ttk.Label(params_row)
        self.i18n_widgets["silence_padding_label"].pack(side="left", padx=(0, 6))
        self.silence_padding_spin = ttk.Spinbox(
            params_row,
            from_=0.00,
            to=2.00,
            increment=0.05,
            textvariable=self.silence_padding_var,
            width=7,
            font=("Consolas", 10, "bold"),
            justify="center",
        )
        self.silence_padding_spin.pack(side="left", padx=(0, 20))
        self.silence_padding_spin.bind("<FocusOut>", lambda _e: self._on_silence_padding_changed())
        self.silence_min_dur_spin.bind("<FocusOut>", lambda _e: self._on_silence_padding_changed())

        self.i18n_widgets["silence_sync_subs_chk"] = ttk.Checkbutton(
            params_row,
            variable=self.silence_sync_subs_var,
            style="Primary.TCheckbutton",
        )
        self.i18n_widgets["silence_sync_subs_chk"].pack(side="left", padx=(0, 10))

        # Row 3: Action Buttons & Export Settings
        action_row = ttk.Frame(settings_box)
        action_row.grid(row=3, column=0, columnspan=5, sticky="ew", pady=(6, 0))

        self.silence_analyze_button = ttk.Button(
            action_row, command=self.start_analyze_silences, style="Action.TButton"
        )
        self.silence_analyze_button.pack(side="left", padx=(0, 8))
        self.i18n_widgets["silence_analyze_btn"] = self.silence_analyze_button

        self.silence_export_button = ttk.Button(
            action_row, command=self.start_silence_export, style="Primary.TButton"
        )
        self.silence_export_button.pack(side="left", padx=(0, 16))
        self.i18n_widgets["silence_export_btn"] = self.silence_export_button

        # Output format & quality next to Export button
        self.i18n_widgets["silence_quality_label"] = ttk.Label(action_row)
        self.i18n_widgets["silence_quality_label"].pack(side="left", padx=(0, 4))
        self.silence_quality_combo = ttk.Combobox(
            action_row, textvariable=self.silence_quality_var, state="readonly", width=30
        )
        self.silence_quality_combo.pack(side="left", padx=(0, 16))
        self.silence_quality_combo.bind("<<ComboboxSelected>>", self._on_silence_quality_changed)

        self.i18n_widgets["silence_format_label"] = ttk.Label(action_row)
        self.i18n_widgets["silence_format_label"].pack(side="left", padx=(0, 4))
        self.silence_format_combo = ttk.Combobox(
            action_row, textvariable=self.silence_format_var, state="readonly", width=24
        )
        self.silence_format_combo.pack(side="left", padx=(0, 8))
        self.silence_format_combo.bind("<<ComboboxSelected>>", self._on_silence_format_changed)

        # Bottom Card: Detected Silences List & Interactive Timeline Bar
        list_box = ttk.LabelFrame(parent, padding=(12, 8, 12, 10))
        list_box.grid(row=1, column=0, sticky="nsew")
        list_box.columnconfigure(0, weight=1)
        list_box.rowconfigure(2, weight=1)
        self.i18n_widgets["silence_list_group"] = list_box

        # Interactive Timeline Bar Canvas
        self.silence_timeline_canvas = tk.Canvas(
            list_box, height=22, bg="#1f242d", highlightthickness=1, highlightbackground="#3d4450", cursor="hand2"
        )
        self.silence_timeline_canvas.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.silence_timeline_canvas.bind("<Configure>", lambda _e: self._draw_silence_timeline_canvas())
        self.silence_timeline_canvas.bind("<Button-1>", self._on_silence_timeline_click)

        # Batch Selection Bar & Summary Label
        list_toolbar = ttk.Frame(list_box)
        list_toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        self.silence_select_all_btn = ttk.Button(
            list_toolbar,
            text=self.text("silence_select_all"),
            command=lambda: self._toggle_all_silences(True),
            style="Player.TButton",
            width=14,
        )
        self.silence_select_all_btn.pack(side="left", padx=(0, 6))
        self.silence_deselect_all_btn = ttk.Button(
            list_toolbar,
            text=self.text("silence_deselect_all"),
            command=lambda: self._toggle_all_silences(False),
            style="Player.TButton",
            width=14,
        )
        self.silence_deselect_all_btn.pack(side="left", padx=(0, 16))

        # Blue summary text showing detected count & saved time
        self.silence_summary_label = ttk.Label(
            list_toolbar, textvariable=self.silence_summary_var, font=("Segoe UI", 9, "bold"), foreground="#0066cc"
        )
        self.silence_summary_label.pack(side="left", fill="x", expand=True)

        # Scrollable List Frame
        list_frame = ttk.Frame(list_box)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.silence_list_canvas = tk.Canvas(list_frame, borderwidth=0, highlightthickness=1)
        self.silence_list_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.silence_list_canvas.yview)
        self.silence_list_canvas.configure(yscrollcommand=self.silence_list_scroll.set)
        self.silence_list_canvas.grid(row=0, column=0, sticky="nsew")
        self.silence_list_scroll.grid(row=0, column=1, sticky="ns")

        self.silence_list_inner = ttk.Frame(self.silence_list_canvas)
        self.silence_list_inner_id = self.silence_list_canvas.create_window((0, 0), window=self.silence_list_inner, anchor="nw")

        self.silence_list_canvas.bind(
            "<Configure>",
            lambda e: self.silence_list_canvas.itemconfig(self.silence_list_inner_id, width=e.width),
        )
        self.silence_list_inner.bind(
            "<Configure>",
            lambda _e: self.silence_list_canvas.configure(scrollregion=self.silence_list_canvas.bbox("all")),
        )

        self._refresh_silence_options()
        self._refresh_silence_ui()

    def _refresh_silence_options(self):
        if not hasattr(self, "silence_preset_combo"):
            return
        is_ar = self.language_var.get() == "العربية"
        preset_items = [
            (k, info["label_ar"] if is_ar else info["label_en"])
            for k, info in SILENCE_PRESETS.items()
        ]
        self.silence_preset_map = {disp: k for k, disp in preset_items}
        self.silence_preset_rev = {k: disp for k, disp in preset_items}
        self.silence_preset_combo.configure(values=[d for _, d in preset_items])
        self.silence_preset_var.set(self.silence_preset_rev.get(self.silence_preset_key, preset_items[0][1]))

        mode_items = [
            (k, info["label_ar"] if is_ar else info["label_en"])
            for k, info in SILENCE_MODES.items()
        ]
        self.silence_mode_map = {disp: k for k, disp in mode_items}
        self.silence_mode_rev = {k: disp for k, disp in mode_items}
        self.silence_mode_combo.configure(values=[d for _, d in mode_items])
        self.silence_mode_var.set(self.silence_mode_rev.get(self.silence_mode_key, mode_items[0][1]))

        quality_items = [
            (k, info["label_ar"] if is_ar else info["label_en"])
            for k, info in SILENCE_QUALITIES.items()
        ]
        self.silence_quality_map = {disp: k for k, disp in quality_items}
        self.silence_quality_rev = {k: disp for k, disp in quality_items}
        if hasattr(self, "silence_quality_combo"):
            self.silence_quality_combo.configure(values=[d for _, d in quality_items])
            self.silence_quality_var.set(self.silence_quality_rev.get(self.silence_quality_key, quality_items[0][1]))

        format_items = [
            (k, info["label_ar"] if is_ar else info["label_en"])
            for k, info in SILENCE_FORMATS.items()
        ]
        self.silence_format_map = {disp: k for k, disp in format_items}
        self.silence_format_rev = {k: disp for k, disp in format_items}
        if hasattr(self, "silence_format_combo"):
            self.silence_format_combo.configure(values=[d for _, d in format_items])
            self.silence_format_var.set(self.silence_format_rev.get(self.silence_format_key, format_items[0][1]))

        if not self.silence_analysis_result:
            self.silence_summary_var.set(self.text("silence_ready_hint"))
        else:
            self._recalculate_silence_summary()

    def _on_silence_quality_changed(self, _e=None):
        disp = self.silence_quality_var.get()
        self.silence_quality_key = self.silence_quality_map.get(disp, "original")
        self._save_settings()

    def _on_silence_format_changed(self, _e=None):
        disp = self.silence_format_var.get()
        self.silence_format_key = self.silence_format_map.get(disp, "same")
        self._save_settings()

    def _on_silence_preset_changed(self, _e=None):
        disp = self.silence_preset_var.get()
        key = self.silence_preset_map.get(disp, "natural")
        self.silence_preset_key = key
        p_info = SILENCE_PRESETS.get(key, SILENCE_PRESETS["natural"])
        self.silence_noise_db_var.set(float(p_info["noise_db"]))
        self._on_silence_noise_changed()
        self.silence_min_dur_var.set(f"{float(p_info['min_silence_sec']):.2f}")
        self.silence_padding_var.set(f"{float(p_info['padding_sec']):.2f}")
        self.silence_mode_key = p_info.get("mode", "remove")
        if hasattr(self, "silence_mode_rev") and self.silence_mode_key in self.silence_mode_rev:
            self.silence_mode_var.set(self.silence_mode_rev[self.silence_mode_key])
        self._save_settings()
        if self.silence_analysis_result:
            self._recalculate_silence_summary()

    def _on_silence_mode_changed(self, _e=None):
        disp = self.silence_mode_var.get()
        self.silence_mode_key = self.silence_mode_map.get(disp, "remove")
        self._save_settings()
        if self.silence_analysis_result:
            self._recalculate_silence_summary()
        self._refresh_master_export_summary()

    def _on_silence_noise_changed(self, _val=None):
        db = round(float(self.silence_noise_db_var.get()), 1)
        self.silence_noise_label_var.set(f"{db:.1f} dB")
        self._save_settings()

    def _on_silence_padding_changed(self):
        self._save_settings()
        if self.silence_analysis_result:
            self._recalculate_silence_summary()

    def _get_silence_params(self):
        noise_db = round(float(self.silence_noise_db_var.get()), 1)
        try:
            min_dur = max(0.1, float(self.silence_min_dur_var.get()))
        except Exception:
            min_dur = 0.50
        try:
            padding = max(0.0, float(self.silence_padding_var.get()))
        except Exception:
            padding = 0.15
        mode = getattr(self, "silence_mode_key", "remove")
        return noise_db, min_dur, padding, mode

    def start_analyze_silences(self):
        if self.worker and self.worker.is_alive():
            return
        if not self.media_files:
            messagebox.showwarning(self.text("app_title"), self.text("choose_single_trim"))
            return
        target_file = self.input_path if (self.input_path and self.input_path.is_file()) else self.media_files[0]
        noise_db, min_dur, padding, _mode = self._get_silence_params()

        self._begin_operation("silence_detect", self.silence_analyze_button)
        self.silence_summary_var.set(self.text("silence_analyzing"))
        self.status_var.set(self.text("silence_analyzing"))
        self._set_busy(True)
        self.progress.configure(mode="determinate", maximum=100, value=0)

        def worker():
            try:
                res = convert.detect_silences(
                    media_path=target_file,
                    noise_db=noise_db,
                    min_silence_sec=min_dur,
                    padding_sec=padding,
                    ffmpeg_exe=str(convert.ffmpeg_executable()),
                    progress_callback=lambda pct: self.after(0, lambda p=pct: self.progress.configure(value=p)),
                    cancel_callback=self._operation_canceled,
                )
                self.after(0, lambda: self._on_silence_analysis_done(res))
            except Exception as exc:
                if self.cancel_event.is_set() or "canceled" in str(exc).lower() or "cancelled" in str(exc).lower():
                    self.after(0, lambda: self.silence_summary_var.set(self.text("canceled")))
                    self.after(0, lambda: self._finish(self.text("canceled"), canceled=True))
                else:
                    self.after(0, lambda: self.silence_summary_var.set(f"Error: {exc}"))
                    self.after(0, lambda: self._finish(self.text("failed"), failed=True))

        self.worker = threading.Thread(target=worker, daemon=True)
        self.worker.start()

    def _on_silence_analysis_done(self, result):
        self._restore_operation_buttons()
        self._set_busy(False)
        self.silence_analysis_result = result
        self.status_var.set(self.text("ready"))
        self.progress.configure(value=100)
        try:
            self._recalculate_silence_summary()
        except Exception as e:
            print(f"[Silence] Error in _recalculate_silence_summary: {e}")
        try:
            self._refresh_silence_ui()
        except Exception as e:
            print(f"[Silence] Error in _refresh_silence_ui: {e}")
        try:
            self._draw_player_visual_timeline()
        except Exception as e:
            print(f"[Silence] Error in _draw_player_visual_timeline: {e}")

    def _recalculate_silence_summary(self):
        if not self.silence_analysis_result:
            return
        noise_db, _min_dur, padding, mode = self._get_silence_params()
        silences = self.silence_analysis_result.get("silences", [])
        tot_dur = float(self.silence_analysis_result.get("total_duration") or self.media_duration or 0.0)
        stats = summarize_silence_analysis(
            total_duration=tot_dur,
            silences=silences,
            padding_sec=padding,
            mode=mode,
            speed_factor=4,
        )
        self.silence_analysis_result.update(stats)
        if not silences:
            try:
                msg = self.text("silence_none_found", db=f"{noise_db:.1f}")
            except Exception:
                msg = f"No silences detected at {noise_db:.1f} dB"
        else:
            count = stats.get("silence_count", stats.get("count", len(silences)))
            orig_str = self._format_time(tot_dur)
            new_dur = stats.get("new_duration", stats.get("final_duration", tot_dur))
            new_str = self._format_time(new_dur)
            saved_sec = stats.get("saved_seconds", stats.get("saved_duration", 0.0))
            pct_val = stats.get("saved_percent", 0.0)
            try:
                msg = self.text(
                    "silence_summary_fmt",
                    count=count,
                    orig=orig_str,
                    new=new_str,
                    saved=f"{saved_sec:.1f}s",
                    pct=f"{pct_val:.1f}",
                )
            except Exception:
                msg = f"✅ Found {count} silences | Saved: {saved_sec:.1f}s ({pct_val:.1f}%)"

        self.silence_summary_var.set(msg)
        if hasattr(self, "davinci_timeline"):
            try:
                self.davinci_timeline.silence_intervals = silences
                self.davinci_timeline.redraw()
            except Exception:
                pass
        try:
            self._refresh_master_export_summary()
        except Exception:
            pass

    def _refresh_silence_ui(self):
        if not hasattr(self, "silence_list_inner"):
            return
        for child in self.silence_list_inner.winfo_children():
            child.destroy()
        self.silence_row_vars = []

        is_dark = getattr(self, "theme_var", None) and self.theme_var.get() == "dark"
        bg_col = "#12151a" if is_dark else "#f6f8fa"
        self.silence_list_canvas.configure(bg=bg_col, highlightbackground="#343b47" if is_dark else "#e1e4e8")

        if not self.silence_analysis_result or not self.silence_analysis_result.get("silences"):
            lbl = ttk.Label(
                self.silence_list_inner,
                text=self.text("silence_empty_list"),
                foreground="#8b949e" if is_dark else "#666666",
                font=("Segoe UI", 10),
                padding=(16, 24),
            )
            lbl.pack(fill="x")
            self._draw_silence_timeline_canvas()
            return

        silences = self.silence_analysis_result["silences"]
        for idx, s_item in enumerate(silences):
            row = ttk.Frame(self.silence_list_inner, padding=(8, 4))
            row.pack(fill="x", padx=4, pady=2)
            row.columnconfigure(1, weight=1)

            var = tk.BooleanVar(value=bool(s_item.get("enabled", True)))
            self.silence_row_vars.append((s_item, var))

            chk = ttk.Checkbutton(
                row,
                text=self.text("silence_cut_chk"),
                variable=var,
                command=lambda item=s_item, v=var: self._on_silence_item_toggled(item, v),
            )
            chk.grid(row=0, column=0, padx=(0, 10), sticky="w")

            info_txt = self.text(
                "silence_item_label",
                idx=s_item.get("index", idx + 1),
                start=f"{self._format_time(s_item['start'])}.{int((s_item['start'] % 1) * 10)}",
                end=f"{self._format_time(s_item['end'])}.{int((s_item['end'] % 1) * 10)}",
                dur=f"{s_item['duration']:.2f}",
            )
            lbl = ttk.Label(row, text=info_txt, font=("Consolas", 9, "bold"))
            lbl.grid(row=0, column=1, sticky="w")

            play_btn = ttk.Button(
                row,
                text=self.text("silence_preview_seg"),
                command=lambda st=max(0.0, s_item["start"] - 0.8), en=s_item["end"] + 0.8: self._play_bubble_segment(st, en),
                style="Player.TButton",
            )
            play_btn.grid(row=0, column=2, padx=(8, 0), sticky="e")

        self._draw_silence_timeline_canvas()

    def _on_silence_item_toggled(self, s_item, var):
        s_item["enabled"] = bool(var.get())
        self._recalculate_silence_summary()

    def _toggle_all_silences(self, enable=True):
        if not self.silence_analysis_result:
            return
        for s_item, var in self.silence_row_vars:
            s_item["enabled"] = bool(enable)
            var.set(bool(enable))
        self._recalculate_silence_summary()

    def _draw_silence_timeline_canvas(self):
        if not hasattr(self, "silence_timeline_canvas"):
            return
        c = self.silence_timeline_canvas
        c.delete("all")
        w = max(10, c.winfo_width())
        h = max(10, c.winfo_height())

        tot = (
            self.silence_analysis_result.get("total_duration", 0.0)
            if self.silence_analysis_result
            else float(self.media_duration or 0.0)
        )
        if tot <= 0:
            c.create_rectangle(0, 0, w, h, fill="#1f242d", outline="")
            return

        # Base speech background (emerald green)
        c.create_rectangle(0, 0, w, h, fill="#238636", outline="")

        if self.silence_analysis_result:
            for s_item in self.silence_analysis_result.get("silences", []):
                x1 = int((s_item["start"] / tot) * w)
                x2 = max(x1 + 2, int((s_item["end"] / tot) * w))
                col = "#da3633" if s_item.get("enabled", True) else "#6e7681"
                c.create_rectangle(x1, 0, x2, h, fill=col, outline="")

    def _on_silence_timeline_click(self, event):
        c = self.silence_timeline_canvas
        w = max(1, c.winfo_width())
        tot = (
            self.silence_analysis_result.get("total_duration", 0.0)
            if self.silence_analysis_result
            else float(self.media_duration or 0.0)
        )
        if tot <= 0:
            return
        target_sec = max(0.0, min(tot, (event.x / w) * tot))
        self._play_bubble_segment(target_sec, min(tot, target_sec + 4.0))

    def save_synced_srt_file(self):
        if not self.caption_current_result or not self.caption_current_result.get("segments"):
            messagebox.showwarning(self.text("app_title"), self.text("sub_no_segments"))
            return
        if not self.silence_analysis_result or not self.silence_analysis_result.get("keep_intervals"):
            messagebox.showwarning(
                self.text("app_title"),
                "يرجى الضغط على '🔍 فحص السكتات الآن' أولاً لحساب التوقيتات الجديدة."
                if self.language_var.get() == "العربية"
                else "Please click '🔍 Analyze Silences' first to compute the new timestamps.",
            )
            return

        _noise_db, _min_dur, _padding, mode = self._get_silence_params()
        remapped_segs = remap_subtitles_for_cuts(
            self.caption_current_result["segments"],
            self.silence_analysis_result["keep_intervals"],
            mode=mode,
            speed_factor=4,
        )
        srt_text = convert.generate_srt_content(remapped_segs)
        default_name = f"{self.input_path.stem}_synced.srt" if self.input_path else "subtitles_synced.srt"
        save_p = filedialog.asksaveasfilename(
            parent=self,
            title=self.text("silence_save_synced_srt"),
            initialdir=str(self.output_dir or Path(".")),
            initialfile=default_name,
            defaultextension=".srt",
            filetypes=[("SubRip Subtitle", "*.srt")],
        )
        if save_p:
            Path(save_p).write_text(srt_text, encoding="utf-8-sig")
            messagebox.showinfo(self.text("app_title"), self.text("caption_saved"))

    def start_silence_export(self):
        if self.worker and self.worker.is_alive():
            return
        if not self.input_path or not self.media_files:
            messagebox.showwarning(self.text("app_title"), self.text("no_media"))
            return

        noise_db, min_dur, padding, mode = self._get_silence_params()
        enhancement = self.selected_enhancement()
        q_key = getattr(self, "silence_quality_key", "original")
        quality = {"original": "Original", "high": "High", "medium": "Medium", "small": "Small"}.get(q_key, "Original")

        f_key = getattr(self, "silence_format_key", "same")
        fmt_info = SILENCE_FORMATS.get(f_key, SILENCE_FORMATS["same"])
        is_audio_only = fmt_info.get("is_audio_only", False)
        chosen_ext = fmt_info.get("ext")

        single_file = len(self.media_files) == 1 and self.input_path.is_file()
        custom_keep_intervals = None
        if single_file and self.silence_analysis_result and self.silence_analysis_result.get("keep_intervals"):
            custom_keep_intervals = self.silence_analysis_result["keep_intervals"]

        self._clear_log()
        self._begin_operation("silence_cut", self.silence_export_button)
        self._append_log(self.text("silence_exporting") + f" (Threshold: {noise_db} dB, Min: {min_dur}s, Mode: {mode}, Quality: {quality}, Format: {f_key})\n")
        self.status_var.set(self.text("silence_exporting"))
        self._set_busy(True)
        self.progress.configure(mode="determinate", maximum=100, value=0)

        def worker():
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            try:
                out_dir = self.output_dir or (self.input_path.parent / "output")
                out_dir.mkdir(parents=True, exist_ok=True)

                if single_file:
                    target = self.media_files[0]
                    is_vid = False if is_audio_only else (convert.has_video_stream(target) or (target.suffix.lower() in convert.VIDEO_EXTS))
                    tag = "nosilence" if mode == "remove" else ("fastsilence" if mode == "fast_forward" else "gated")
                    out_ext = chosen_ext if chosen_ext else target.suffix
                    out_p = convert.unique_output_path(out_dir / f"{target.stem}_{tag}{out_ext}")

                    def _prog(pct, cur_s, tot_s):
                        self._progress_request(0, 1, target, pct)

                    res_path = convert.export_silence_cut_media(
                        media_path=target,
                        output_path=out_p,
                        output_dir=out_dir,
                        keep_intervals=custom_keep_intervals,
                        noise_db=noise_db,
                        min_silence_sec=min_dur,
                        padding_sec=padding,
                        mode=mode,
                        speed_factor=4,
                        audio_enhancement_filter=convert.ffmpeg_audio_filter_str(enhancement),
                        video_quality=quality,
                        has_video=is_vid,
                        ffmpeg_exe=str(convert.ffmpeg_executable()),
                        cancel_callback=self._operation_canceled,
                        progress_callback=_prog,
                    )

                    if self.silence_sync_subs_var.get() and self.caption_current_result and self.caption_current_result.get("segments"):
                        k_iv = custom_keep_intervals
                        if not k_iv and self.silence_analysis_result:
                            k_iv = self.silence_analysis_result.get("keep_intervals")
                        if k_iv:
                            remapped = remap_subtitles_for_cuts(
                                self.caption_current_result["segments"],
                                k_iv,
                                mode=mode,
                                speed_factor=4,
                            )
                            srt_out = res_path.with_suffix(".srt")
                            srt_out.write_text(convert.generate_srt_content(remapped), encoding="utf-8-sig")
                            self.messages.put(f"[Subtitles Synced] {srt_out}\n")

                    self.messages.put("\n" + self.text("silence_done_msg", filename=res_path.name) + "\n")
                else:
                    def _batch_prog(curr, tot, path, pct=0):
                        self._progress_request(curr, tot, path, pct)

                    results = convert.batch_export_silence_cut(
                        media_files=self.media_files,
                        output_dir=out_dir,
                        noise_db=noise_db,
                        min_silence_sec=min_dur,
                        padding_sec=padding,
                        mode=mode,
                        speed_factor=4,
                        enhancement=enhancement,
                        video_quality=quality,
                        chosen_ext=chosen_ext,
                        is_audio_only=is_audio_only,
                        progress_callback=_batch_prog,
                        cancel_callback=self._operation_canceled,
                    )
                    self.messages.put(f"\nCompleted silence removal for {len(results)} files in {out_dir}\n")

                self.messages.put("\n__DONE__")
            except (subprocess.SubprocessError, convert.CancelledError):
                self.messages.put("\n__CANCELED__")
            except Exception as exc:
                if self.cancel_event.is_set() or "canceled" in str(exc).lower() or "cancelled" in str(exc).lower():
                    self.messages.put("\n__CANCELED__")
                else:
                    self.messages.put(f"\n[Silence Cut Error] {exc}\n")
                    self.messages.put("\n__FAILED__")
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

        self.worker = threading.Thread(target=worker, daemon=True)
        self.worker.start()
