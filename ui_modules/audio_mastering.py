"""
Audio Mastering & Volume Booster Mixin
Handles audio analysis, peak normalization, gain adjustment, and batch volume mastering.
"""

import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import convert


class AudioMasteringMixin:
    """Provides volume boost, normalization, and audio mastering controls."""

    def _build_tab_volume(self, parent):
        parent.columnconfigure(0, weight=1)

        # Top Card: Audio Analysis
        analysis_box = ttk.LabelFrame(parent, padding=14)
        analysis_box.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        analysis_box.columnconfigure(0, weight=1)
        self.i18n_widgets["volume_analysis_group"] = analysis_box

        self.boost_stats_label = ttk.Label(
            analysis_box, textvariable=self.boost_stats_var, font=("Segoe UI", 10, "bold"), foreground="#0055aa"
        )
        self.boost_stats_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        btn_row = ttk.Frame(analysis_box)
        btn_row.grid(row=1, column=0, columnspan=2, sticky="w")

        self.detect_volume_button = ttk.Button(
            btn_row, text=self.text("detect_volume"), command=self.start_detect_volume, style="Player.TButton"
        )
        self.detect_volume_button.pack(side="left", padx=(0, 10))

        self.auto_peak_button = ttk.Button(
            btn_row, text=self.text("volume_normalize_peak"), command=self.start_auto_peak_boost, style="Player.TButton"
        )
        self.auto_peak_button.pack(side="left")

        # Bottom Card: Amplification & Mastering Controls
        boost_box = ttk.LabelFrame(parent, padding=14)
        boost_box.grid(row=1, column=0, sticky="nsew")
        boost_box.columnconfigure(1, weight=1)
        self.i18n_widgets["volume_group"] = boost_box

        # Gain Slider Row
        self.i18n_widgets["volume_gain_label"] = ttk.Label(boost_box, font=("Segoe UI", 10, "bold"))
        self.i18n_widgets["volume_gain_label"].grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.boost_gain_scale = ttk.Scale(
            boost_box,
            from_=-12.0,
            to=30.0,
            variable=self.boost_gain_var,
            orient="horizontal",
            command=self._boost_gain_changed,
        )
        self.boost_gain_scale.grid(row=0, column=1, sticky="ew", padx=(10, 14), pady=(0, 10))

        self.boost_gain_display = ttk.Label(
            boost_box, textvariable=self.boost_gain_label_var, font=("Segoe UI", 11, "bold"), foreground="#cc3300", width=18
        )
        self.boost_gain_display.grid(row=0, column=2, sticky="w", pady=(0, 10))

        # Quick Presets Row
        preset_box = ttk.Frame(boost_box)
        preset_box.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        ttk.Label(preset_box, text="⚡ Presets:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 10))
        self.preset_btn_1 = ttk.Button(
            preset_box, text=self.text("volume_preset_light"), command=lambda: self.set_boost_preset(3.0), style="Player.TButton"
        )
        self.preset_btn_1.pack(side="left", padx=(0, 6))

        self.preset_btn_2 = ttk.Button(
            preset_box, text=self.text("volume_preset_double"), command=lambda: self.set_boost_preset(6.0), style="Player.TButton"
        )
        self.preset_btn_2.pack(side="left", padx=(0, 6))

        self.preset_btn_3 = ttk.Button(
            preset_box, text=self.text("volume_preset_high"), command=lambda: self.set_boost_preset(10.0), style="Player.TButton"
        )
        self.preset_btn_3.pack(side="left", padx=(0, 6))

        self.preset_btn_4 = ttk.Button(
            preset_box, text=self.text("volume_preset_extreme"), command=lambda: self.set_boost_preset(15.0), style="Player.TButton"
        )
        self.preset_btn_4.pack(side="left")

        # Anti-Clipping Limiter Checkbox
        self.boost_anti_clip_check = ttk.Checkbutton(
            boost_box, text=self.text("volume_anti_clipping"), variable=self.boost_anti_clip_var
        )
        self.boost_anti_clip_check.grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 10))

        # Consolidated Audio Mastering Row: Output Format + Enhancement Filter + Fade In/Out
        fmt_row = ttk.Frame(boost_box)
        fmt_row.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 14))
        fmt_row.columnconfigure(1, weight=1)
        fmt_row.columnconfigure(3, weight=1)

        self.i18n_widgets["boost_fmt_label"] = ttk.Label(fmt_row)
        self.i18n_widgets["boost_fmt_label"].grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.boost_output_format_combo = ttk.Combobox(
            fmt_row,
            textvariable=self.boost_output_format_var,
            state="readonly",
            width=18,
            values=["auto", ".mp3", ".m4a", ".wav", ".flac"],
        )
        self.boost_output_format_combo.grid(row=0, column=1, sticky="ew", padx=(6, 16), pady=(0, 6))
        self._refresh_boost_format_options()

        self.i18n_widgets["boost_enhance_label"] = ttk.Label(fmt_row, text=self.text("enhance"))
        self.i18n_widgets["boost_enhance_label"].grid(row=0, column=2, sticky="w", pady=(0, 6))
        self.boost_enhancement_combo = ttk.Combobox(
            fmt_row,
            textvariable=self.enhancement_var,
            state="readonly",
            width=18,
        )
        self.boost_enhancement_combo.grid(row=0, column=3, sticky="ew", padx=(6, 0), pady=(0, 6))
        self.boost_enhancement_combo.bind("<<ComboboxSelected>>", lambda _event: self._remember_enhancement_key())

        fade_frame = ttk.Frame(fmt_row)
        fade_frame.grid(row=1, column=0, columnspan=4, sticky="w", pady=(2, 0))

        self.i18n_widgets["fade_in_label"] = ttk.Label(fade_frame, text=self.text("fade_in_label"))
        self.i18n_widgets["fade_in_label"].pack(side="left", padx=(0, 6))
        self.boost_fade_in_combo = ttk.Combobox(
            fade_frame,
            textvariable=self.boost_fade_in_var,
            values=["0.0", "0.5", "1.0", "2.0", "3.0"],
            width=6,
        )
        self.boost_fade_in_combo.pack(side="left", padx=(0, 20))

        self.i18n_widgets["fade_out_label"] = ttk.Label(fade_frame, text=self.text("fade_out_label"))
        self.i18n_widgets["fade_out_label"].pack(side="left", padx=(0, 6))
        self.boost_fade_out_combo = ttk.Combobox(
            fade_frame,
            textvariable=self.boost_fade_out_var,
            values=["0.0", "0.5", "1.0", "2.0", "3.0"],
            width=6,
        )
        self.boost_fade_out_combo.pack(side="left")

        # Action Button
        self.boost_button = ttk.Button(
            boost_box,
            command=self.start_boost_volume,
            style="Action.TButton",
        )
        self.boost_button.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(8, 0))

    def _boost_gain_changed(self, _val=None):
        db = round(self.boost_gain_var.get(), 1)
        ratio = 10.0 ** (db / 20.0)
        pct = int(ratio * 100)
        sign = "+" if db > 0 else ""
        self.boost_gain_label_var.set(f"{sign}{db:.1f} dB ({pct}%)")
        self._apply_active_clip_playback_fx()

    def set_boost_preset(self, db_val):
        self.boost_gain_var.set(db_val)
        self._boost_gain_changed()

    def start_detect_volume(self):
        if not self.media_files:
            messagebox.showwarning(self.text("app_title"), self.text("choose_single_trim"))
            return
        target_file = self.media_files[0]
        self.boost_stats_var.set(self.text("detecting_volume"))

        def worker():
            res = convert.detect_audio_volume(target_file)
            if res:
                mean_db = res.get("mean_volume", -99.0)
                max_db = res.get("max_volume", 0.0)
                suggested = round(max(0.0, -max_db - 0.5), 1)
                msg = (
                    self.text("volume_current_level", mean=mean_db, max=max_db)
                    + " | "
                    + self.text("volume_suggested", gain=suggested)
                )
                self.after(0, lambda: self.boost_stats_var.set(msg))
                self.after(0, lambda: self.set_boost_preset(suggested))
            else:
                self.after(0, lambda: self.boost_stats_var.set(self.text("error_check_log")))

        threading.Thread(target=worker, daemon=True).start()

    def start_auto_peak_boost(self):
        if not self.media_files:
            messagebox.showwarning(self.text("app_title"), self.text("choose_single_trim"))
            return
        target_file = self.media_files[0]
        self.boost_stats_var.set(self.text("detecting_volume"))

        def worker():
            res = convert.detect_audio_volume(target_file)
            if res:
                max_db = res.get("max_volume", 0.0)
                headroom = round(max(0.0, -max_db - 0.5), 1)
                self.after(0, lambda: self.set_boost_preset(headroom))
                self.after(100, self.start_boost_volume)
            else:
                self.after(0, lambda: self.boost_stats_var.set(self.text("error_check_log")))

        threading.Thread(target=worker, daemon=True).start()

    def start_boost_volume(self):
        if self.worker and self.worker.is_alive():
            return
        if not self.input_path or not self.media_files:
            messagebox.showwarning(self.text("app_title"), self.text("no_media"))
            return

        gain_db = round(self.boost_gain_var.get(), 1)
        anti_clip = self.boost_anti_clip_var.get()
        enhancement = self.selected_enhancement()
        try:
            fade_in = max(0.0, float(self.boost_fade_in_var.get()))
        except Exception:
            fade_in = 0.0
        try:
            fade_out = max(0.0, float(self.boost_fade_out_var.get()))
        except Exception:
            fade_out = 0.0

        out_fmt = self.boost_output_format_var.get()
        if out_fmt.startswith("auto") or out_fmt.startswith("Same") or out_fmt.startswith("نفس"):
            out_fmt = None
        else:
            out_fmt = out_fmt.split(" ", 1)[0]

        self._clear_log()
        self._begin_operation("boost", self.boost_button)
        self._append_log(self.text("boosting_volume") + f" (Gain: {gain_db} dB, Enhance: {enhancement})\n")
        self.status_var.set(self.text("boosting_volume"))
        self._set_busy(True)
        self.progress.configure(mode="determinate", maximum=max(len(self.media_files), 1) * 100, value=0)

        def worker():
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            try:
                def prog_cb(curr, tot, path, pct=100, msg=""):
                    fname = path.name if hasattr(path, "name") else str(path)
                    self.messages.put(("progress", curr, tot, fname, pct))

                results = convert.batch_boost_volume(
                    self.media_files,
                    output_dir=self.output_dir,
                    gain_db=gain_db,
                    anti_clipping=anti_clip,
                    output_ext=out_fmt,
                    enhancement=enhancement,
                    fade_in_sec=fade_in,
                    fade_out_sec=fade_out,
                    progress_callback=prog_cb,
                    cancel_callback=self._operation_canceled,
                )
                self.messages.put(f"\nMastering & Boost completed! Saved {len(results)} files in {self.output_dir}\n")
                self.messages.put("\n__DONE__")
            except Exception as exc:
                self.messages.put(f"\nError boosting volume: {exc}\n")
                self.messages.put("\n__FAILED__")
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

        self.worker = threading.Thread(target=worker, daemon=True)
        self.worker.start()

    def _refresh_boost_format_options(self):
        is_ar = self.language_var.get() == "العربية"
        auto_label = "نفس الصيغة الأصلية" if is_ar else "Same as input (Auto)"
        self.boost_output_format_combo.configure(
            values=[auto_label, ".mp3 - MP3", ".m4a - AAC / M4A", ".wav - WAV", ".flac - FLAC"]
        )
        cur = self.boost_output_format_var.get()
        if not cur or cur.startswith("auto") or cur.startswith("Same") or cur.startswith("نفس"):
            self.boost_output_format_var.set(auto_label)
