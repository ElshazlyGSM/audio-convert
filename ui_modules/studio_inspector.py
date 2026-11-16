"""
Studio Inspector Controller Mixin
Manages inspector tabs, dynamic context panels, advanced color grading,
silence threshold auto-calibration, timeline silence splitting, and overlay properties.
"""

from pathlib import Path
import threading
from typing import Optional, Dict, Any
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from video_studio.color_grading import (
    DEFAULT_COLOR_CONFIG,
    COLOR_PRESETS,
    is_color_neutral,
    auto_analyze_and_correct,
    extract_video_sample_frame,
    analyze_video_multi_frame,
)
from video_studio.transitions import (
    DEFAULT_TRANSITIONS_CONFIG,
    TRANSITION_PRESETS,
    TRANSITION_CATEGORIES,
    get_transition_info,
    list_transitions_by_category,
)
from ui_dialogs.video_transition_dialog import VideoTransitionDialog
import convert


class StudioInspectorMixin:
    """Provides inspector panel management and controls for MediaAudioStudioApp."""

    # -------------------------------------------------------------------------
    # Dynamic Context Switcher
    # -------------------------------------------------------------------------
    def _show_inspector_context(self, ctx_name: str):
        if not hasattr(self, "dynamic_inspector_host"):
            return
        ctx_frames = {
            "video": getattr(self, "ctx_frame_video", None),
            "overlay": getattr(self, "item_prop_card", None),
            "color": getattr(self, "ctx_frame_color", None),
            "transition": getattr(self, "ctx_frame_transition", None),
            "silence": getattr(self, "ctx_frame_silence", None),
            "audio": getattr(self, "ctx_frame_audio", None),
            "subs": getattr(self, "ctx_frame_subs", None),
            "export": getattr(self, "ctx_frame_export", None),
        }
        if ctx_name not in ctx_frames or ctx_frames[ctx_name] is None:
            ctx_name = "video"
        if ctx_name != "export":
            self._last_inspector_context_before_export = ctx_name
        self.active_inspector_context = ctx_name

        for k, frm in ctx_frames.items():
            if frm is not None:
                if k == ctx_name:
                    frm.grid(row=0, column=0, sticky="nsew")
                else:
                    frm.grid_remove()

        if ctx_name == "export":
            if hasattr(self, "add_palette"):
                self.add_palette.grid_remove()
            if hasattr(self, "ctx_bar"):
                self.ctx_bar.grid_remove()
        else:
            if hasattr(self, "add_palette"):
                self.add_palette.grid(row=0, column=0, sticky="ew", pady=(0, 3))
            if hasattr(self, "ctx_bar"):
                self.ctx_bar.grid(row=1, column=0, sticky="ew", pady=(0, 4))

        btn_map = {
            "video": getattr(self, "btn_ctx_video", None),
            "color": getattr(self, "btn_ctx_color", None),
            "transition": getattr(self, "btn_ctx_transition", None),
            "silence": getattr(self, "btn_ctx_silence", None),
            "audio": getattr(self, "btn_ctx_audio", None),
            "subs": getattr(self, "btn_ctx_subs", None),
        }
        for k, btn in btn_map.items():
            if btn is not None:
                btn.configure(style="PrimaryPlayer.TButton" if k == ctx_name else "Player.TButton")

        if hasattr(self, "btn_export_mode") and self.btn_export_mode:
            is_ar = hasattr(self, "language_var") and self.language_var.get() == "العربية"
            if ctx_name == "export":
                self.btn_export_mode.configure(
                    style="PrimaryPlayer.TButton",
                    text="⬅ عودة للإعدادات" if is_ar else "⬅ Back to Settings",
                )
            else:
                self.btn_export_mode.configure(
                    style="Action.TButton",
                    text="🚀 تصدير الفيديو" if is_ar else "🚀 Export Video",
                )
            try:
                self.btn_export_mode.lift()
            except Exception:
                pass

        if ctx_name == "color":
            self._sync_studio_color_controls()
        elif ctx_name == "transition":
            self.refresh_video_transitions_panel()
        elif ctx_name == "video":
            self._sync_transform_sliders_from_state()
        elif ctx_name == "overlay":
            self._update_inspector_properties()
        elif ctx_name == "export":
            if hasattr(self, "_refresh_master_export_summary"):
                self._refresh_master_export_summary()

        if hasattr(self, "inspector_canvas") and hasattr(self, "dynamic_inspector_host"):
            self.inspector_canvas.yview_moveto(0.0)
            self.dynamic_inspector_host.update_idletasks()
            self.inspector_canvas.configure(scrollregion=self.inspector_canvas.bbox("all"))

    def _toggle_export_context(self):
        if hasattr(self, "notebook") and hasattr(self, "tab_player"):
            try:
                self.notebook.select(self.tab_player)
            except Exception:
                pass
        if getattr(self, "active_inspector_context", None) == "export":
            prev = getattr(self, "_last_inspector_context_before_export", "video")
            self._show_inspector_context(prev if prev != "export" else "video")
        else:
            self._last_inspector_context_before_export = getattr(self, "active_inspector_context", "video")
            self._show_inspector_context("export")

    def _back_from_export(self):
        prev = getattr(self, "_last_inspector_context_before_export", "video")
        self._show_inspector_context(prev if prev != "export" else "video")

    # -------------------------------------------------------------------------
    # Color Grading Controls
    # -------------------------------------------------------------------------
    def _sync_studio_color_controls(self):
        if not hasattr(self, "col_bright_var"):
            return
        self._updating_col_ui = True
        try:
            cc = self.video_branding_config.get("color_config", {})
            if not isinstance(cc, dict):
                cc = dict(DEFAULT_COLOR_CONFIG)
            br = round(float(cc.get("brightness", 0.0)) * 100.0, 1)
            ct = round(float(cc.get("contrast", 1.0)) * 100.0, 1)
            st = round(float(cc.get("saturation", 1.0)) * 100.0, 1)
            tp = round(float(cc.get("temperature", 0.0)) * 100.0, 1)
            self.col_bright_var.set(br)
            self.col_contrast_var.set(ct)
            self.col_sat_var.set(st)
            self.col_temp_var.set(tp)
            self.col_bright_spin_var.set(f"{int(round(br))}")
            self.col_contrast_spin_var.set(f"{int(round(ct))}")
            self.col_sat_spin_var.set(f"{int(round(st))}")
            self.col_temp_spin_var.set(f"{int(round(tp))}")
        finally:
            self._updating_col_ui = False

    def _apply_studio_color_values(
        self,
        br_pct: float,
        ct_pct: float,
        st_pct: float,
        tp_pct: float,
        preset_key: str = "custom",
        extra_cfg: Optional[Dict[str, Any]] = None,
    ):
        cc = self.video_branding_config.get("color_config")
        if not isinstance(cc, dict):
            cc = dict(DEFAULT_COLOR_CONFIG)
            self.video_branding_config["color_config"] = cc
        cc["brightness"] = round(max(-0.50, min(0.50, br_pct / 100.0)), 3)
        cc["contrast"] = round(max(0.50, min(2.00, ct_pct / 100.0)), 3)
        cc["saturation"] = round(max(0.00, min(2.50, st_pct / 100.0)), 3)
        cc["temperature"] = round(max(-0.50, min(0.50, tp_pct / 100.0)), 3)
        if extra_cfg and isinstance(extra_cfg, dict):
            for k in ("gamma", "red", "green", "blue"):
                if k in extra_cfg:
                    cc[k] = round(float(extra_cfg[k]), 3)
        cc["preset"] = preset_key
        non_neutral = not is_color_neutral(cc)
        cc["enabled"] = non_neutral or bool(self.trim_color_var.get())
        if non_neutral:
            self.trim_color_var.set(True)
            cc["enabled"] = True
        self._ready_composed_video = None
        self._save_settings()
        self._refresh_master_export_summary()
        self._render_player_studio_canvas()

    def _on_studio_auto_color_clicked(self):
        is_ar = self.language_var.get() == "العربية"
        mode_disp = getattr(self, "_studio_color_mode_var", tk.StringVar()).get()
        mode_key = getattr(self, "_studio_color_mode_map", {}).get(mode_disp, "balanced")

        target_img = getattr(self, "player_studio_raw_frame", None)
        video_p = getattr(self, "input_path", None)

        if video_p and Path(video_p).is_file():
            suggested_cfg, s_ar, s_en, diag_ar, diag_en = analyze_video_multi_frame(
                video_p,
                num_samples=5,
                intensity=mode_key,
                ffmpeg_exe=str(convert.ffmpeg_executable()),
                fallback_image=target_img,
            )
        elif target_img is not None:
            suggested_cfg, s_ar, s_en, diag_ar, diag_en = auto_analyze_and_correct(target_img, intensity=mode_key)
        else:
            messagebox.showwarning(
                self.text("app_title"),
                "يرجى فتح ملف فيديو وتحديد لقطة لمعاينتها أولاً." if is_ar else "Please open a video and select a frame first."
            )
            return

        br = float(suggested_cfg.get("brightness", 0.0)) * 100.0
        ct = float(suggested_cfg.get("contrast", 1.0)) * 100.0
        st = float(suggested_cfg.get("saturation", 1.0)) * 100.0
        tp = float(suggested_cfg.get("temperature", 0.0)) * 100.0
        self.push_app_undo(f"تعديل ألوان ذكي ({mode_disp})", f"Smart Auto Color ({mode_key})")
        self._apply_studio_color_values(br, ct, st, tp, preset_key=f"auto_{mode_key}", extra_cfg=suggested_cfg)
        self._sync_studio_color_controls()

        diag_list = diag_ar if is_ar else diag_en
        summary_txt = " • ".join(diag_list[:3]) if diag_list else (s_ar if is_ar else s_en)
        if hasattr(self, "lbl_studio_color_diag"):
            self.lbl_studio_color_diag.configure(text="✅ " + summary_txt)
        self._async_extract_studio_frame(force=True)

    def _on_studio_color_preset_selected(self, _e=None):
        disp = self._studio_color_preset_var.get()
        pkey = self._studio_color_preset_map.get(disp, "original")
        preset_info = COLOR_PRESETS.get(pkey, COLOR_PRESETS.get("original", {}))
        cfg_dict = preset_info.get("config", {})
        if pkey == "original":
            self.trim_color_var.set(False)
        else:
            self.trim_color_var.set(True)
        self.push_app_undo(f"تطبيق قالب ألوان: {disp}", f"Color Preset: {disp}")
        self._apply_studio_color_values(
            float(cfg_dict.get("brightness", 0.0)) * 100.0,
            float(cfg_dict.get("contrast", 1.0)) * 100.0,
            float(cfg_dict.get("saturation", 1.0)) * 100.0,
            float(cfg_dict.get("temperature", 0.0)) * 100.0,
            preset_key=pkey,
        )
        self._sync_studio_color_controls()
        self._async_extract_studio_frame(force=True)

    def _on_studio_color_slider(self, _v=None):
        if getattr(self, "_updating_col_ui", False):
            return
        if not getattr(self, "_col_slider_drag_undo_recorded", False):
            self.push_app_undo("تعديل يدوي للألوان", "Manual Color Adjust")
            self._col_slider_drag_undo_recorded = True
            self.after(1400, lambda: setattr(self, "_col_slider_drag_undo_recorded", False))
        br = float(self.col_bright_var.get())
        ct = float(self.col_contrast_var.get())
        st = float(self.col_sat_var.get())
        tp = float(self.col_temp_var.get())
        self._updating_col_ui = True
        try:
            self.col_bright_spin_var.set(f"{int(round(br))}")
            self.col_contrast_spin_var.set(f"{int(round(ct))}")
            self.col_sat_spin_var.set(f"{int(round(st))}")
            self.col_temp_spin_var.set(f"{int(round(tp))}")
        finally:
            self._updating_col_ui = False
        self._apply_studio_color_values(br, ct, st, tp)

    def _on_studio_color_spin(self, _e=None):
        if getattr(self, "_updating_col_ui", False):
            return
        try:
            br = max(-50.0, min(50.0, float(self.col_bright_spin_var.get().strip())))
            ct = max(50.0, min(200.0, float(self.col_contrast_spin_var.get().strip())))
            st = max(0.0, min(250.0, float(self.col_sat_spin_var.get().strip())))
            tp = max(-50.0, min(50.0, float(self.col_temp_spin_var.get().strip())))
        except ValueError:
            self._sync_studio_color_controls()
            return
        self._apply_studio_color_values(br, ct, st, tp)
        self._sync_studio_color_controls()

    def _reset_studio_color_grading(self):
        self.trim_color_var.set(False)
        self.video_branding_config["color_config"] = {
            "enabled": False,
            "brightness": 0.0,
            "contrast": 1.0,
            "saturation": 1.0,
            "temperature": 0.0,
            "gamma": 1.0,
            "preset": "original",
        }
        self._ready_composed_video = None
        self._sync_studio_color_controls()
        if hasattr(self, "studio_color_preset_combo") and self.studio_color_preset_combo["values"]:
            self._studio_color_preset_var.set(self.studio_color_preset_combo["values"][0])
        if hasattr(self, "lbl_studio_color_diag"):
            self.lbl_studio_color_diag.configure(text="")
        self._save_settings()
        self._refresh_master_export_summary()
        self._async_extract_studio_frame(force=True)

    # -------------------------------------------------------------------------
    # Silence Controls & Auto dB Calibration
    # -------------------------------------------------------------------------
    def start_auto_detect_silence_db(self):
        target_file = self.input_path if (self.input_path and self.input_path.is_file()) else (self.media_files[0] if self.media_files else None)
        if not target_file or not target_file.is_file():
            messagebox.showwarning(self.text("app_title"), self.text("choose_single_trim"))
            return
        is_ar = self.language_var.get() == "العربية"
        msg_scanning = "⏳ جاري فحص مستوى الصوت واكتشاف حد السكتات..." if is_ar else "⏳ Detecting volume & silence threshold..."
        self.silence_summary_var.set(msg_scanning)
        self.status_var.set(msg_scanning)
        if hasattr(self, "lbl_sil_auto_diag"):
            self.lbl_sil_auto_diag.configure(text=msg_scanning, foreground="#58a6ff")

        def worker():
            try:
                res = convert.auto_suggest_silence_threshold(target_file)
                sug_db = res.get("suggested_noise_db", -35.0)
                mean_db = res.get("mean_volume", -20.0)
                def _apply():
                    self.silence_noise_db_var.set(sug_db)
                    self._on_silence_noise_changed()
                    msg = (
                        f"✓ تم ضبط حد السكتات تلقائياً: {sug_db:.1f} dB (متوسط الصوت: {mean_db:.1f} dB)"
                        if is_ar
                        else f"✓ Auto-set threshold: {sug_db:.1f} dB (mean: {mean_db:.1f} dB)"
                    )
                    self.silence_summary_var.set(msg)
                    self.status_var.set(msg)
                    if hasattr(self, "lbl_sil_auto_diag"):
                        self.lbl_sil_auto_diag.configure(text=msg, foreground="#56d364")
                self.after(0, _apply)
            except Exception as exc:
                err_msg = f"خطأ: {exc}" if is_ar else f"Error: {exc}"
                self.after(0, lambda: self.silence_summary_var.set(err_msg))
                self.after(0, lambda: self.status_var.set(err_msg))
                if hasattr(self, "lbl_sil_auto_diag"):
                    self.after(0, lambda: self.lbl_sil_auto_diag.configure(text=err_msg, foreground="#f85149"))

        threading.Thread(target=worker, daemon=True).start()

    def _split_silences_onto_nle_timeline(self, remove_silences: bool = True):
        is_ar = self.language_var.get() == "العربية"
        if not self._single_media_file_selected():
            messagebox.showwarning(self.text("app_title"), self.text("choose_single_trim"))
            return
        if getattr(self, "_silence_split_busy", False):
            return
        self._silence_split_busy = True

        noise_db, min_dur, padding, _mode = self._get_silence_params()
        target_path = self.input_path
        msg_wait = "⚡ جاري فحص الصوت وفصل السكتات على التايم لاين..." if is_ar else "⚡ Analyzing audio & splitting silences on timeline..."
        self.status_var.set(msg_wait)
        if hasattr(self, "btn_live_cut_silences"):
            self.btn_live_cut_silences.configure(state="disabled")
        if hasattr(self, "btn_live_mark_silences"):
            self.btn_live_mark_silences.configure(state="disabled")

        def _worker():
            try:
                res = convert.detect_silences(
                    media_path=target_path,
                    noise_db=noise_db,
                    min_silence_sec=min_dur,
                    padding_sec=padding,
                    ffmpeg_exe=str(convert.ffmpeg_executable()),
                )

                def _apply_on_ui():
                    self._silence_split_busy = False
                    if hasattr(self, "btn_live_cut_silences"):
                        self.btn_live_cut_silences.configure(state="normal")
                    if hasattr(self, "btn_live_mark_silences"):
                        self.btn_live_mark_silences.configure(state="normal")

                    self.silence_analysis_result = res
                    sil_list = res.get("silences", [])
                    keep_iv = res.get("keep_intervals", [])
                    if not sil_list:
                        info_m = "لم يتم العثور على سكتات بهذا الحد (جرّب رفع حد dB مثلاً إلى -30dB)." if is_ar else "No silences detected at this threshold (try raising dB e.g. to -30dB)."
                        self.status_var.set(info_m)
                        messagebox.showinfo(self.text("app_title"), info_m)
                        return

                    self.nle_project.apply_silence_cuts_to_timeline(
                        keep_iv,
                        remove_silences=bool(remove_silences),
                        is_ar=is_ar,
                    )
                    if hasattr(self, "export_opt_timeline_var"):
                        self.export_opt_timeline_var.set(True)
                    if remove_silences and hasattr(self, "trim_remove_silence_var"):
                        self.trim_remove_silence_var.set(False)
                        self.video_branding_config["remove_silence"] = False

                    if hasattr(self, "davinci_timeline"):
                        self.davinci_timeline.selected_ref = ("clip", 0)
                        self.davinci_timeline.redraw()
                    self._on_nle_timeline_modified()

                    saved_s = float(res.get("saved_duration", 0.0))
                    succ_m = (
                        f"✅ تم بنجاح تقسيم التايم لاين إلى {len(keep_iv)} مقطع كلام (تم توفير {saved_s:.1f} ثانية)"
                        if is_ar
                        else f"✅ Timeline successfully split into {len(keep_iv)} speech clips (saved {saved_s:.1f}s)"
                    )
                    self.status_var.set(succ_m)
                    if hasattr(self, "lbl_sil_auto_diag"):
                        self.lbl_sil_auto_diag.configure(text=succ_m, foreground="#56d364")

                self.after(0, _apply_on_ui)
            except Exception as exc:
                def _fail():
                    self._silence_split_busy = False
                    if hasattr(self, "btn_live_cut_silences"):
                        self.btn_live_cut_silences.configure(state="normal")
                    if hasattr(self, "btn_live_mark_silences"):
                        self.btn_live_mark_silences.configure(state="normal")
                    self.status_var.set(f"خطأ: {exc}" if is_ar else f"Error: {exc}")
                self.after(0, _fail)

        threading.Thread(target=_worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # Video Transitions Panel Management
    # -------------------------------------------------------------------------
    def open_video_transitions_dialog(self, target_cut_index: Optional[int] = None):
        """Opens the full 46+ Video Transitions Library Dialog."""
        clips = getattr(getattr(self, "nle_project", None), "clips", [])
        n_cuts = max(0, len(clips) - 1)
        if n_cuts <= 0:
            is_ar = getattr(self, "language_var", tk.StringVar(value="English")).get() == "العربية"
            msg = (
                "⚠️ لا توجد تقطيعات في الفيديو حالياً (مقطع واحد فقط)!\n\n"
                "يرجى تقسيم الفيديو أولاً (بالمقص أو بالضغط على Ctrl+B عند الموضع المطلوب) لتتمكن من إضافة حركة انتقال بين المقاطع."
                if is_ar
                else "⚠️ No cuts in video (1 continuous clip)!\n\nPlease split video first (Ctrl+B) to add transitions."
            )
            messagebox.showwarning(self.title(), msg)
            return

        self._save_settings()
        dlg = VideoTransitionDialog(self, target_cut_index=target_cut_index)
        if hasattr(self, "_apply_theme_to_toplevel"):
            self._apply_theme_to_toplevel(dlg)
        dlg.wait_window()
        self.refresh_video_transitions_panel()
        self._refresh_master_export_summary()
        if hasattr(self, "_render_player_studio_canvas"):
            self._render_player_studio_canvas()

    def refresh_video_transitions_panel(self):
        """Syncs inspector transition controls from video_branding_config."""
        if not hasattr(self, "trans_enable_var"):
            return
        is_ar = getattr(self, "language_var", tk.StringVar(value="English")).get() == "العربية"
        tc = self.video_branding_config.get("transitions_config")
        if not isinstance(tc, dict):
            tc = dict(DEFAULT_TRANSITIONS_CONFIG)
            self.video_branding_config["transitions_config"] = tc

        enabled = bool(tc.get("enabled", False))
        def_k = str(tc.get("default_transition", "smoothleft"))
        dur = float(tc.get("default_duration", 0.5))
        xfade_a = bool(tc.get("audio_crossfade", True))

        self.trans_enable_var.set(enabled)
        self.trans_dur_var.set(round(dur, 2))
        self.trans_audio_var.set(xfade_a)

        # Update combo selection
        info = get_transition_info(def_k)
        disp_txt = info.get("label_ar") if is_ar else info.get("label_en")
        icon = info.get("icon", "✨")
        if hasattr(self, "trans_preset_var"):
            self.trans_preset_var.set(f"{icon} {disp_txt}")

        unit = "ثانية" if is_ar else "s"
        if hasattr(self, "lbl_trans_dur_val"):
            self.lbl_trans_dur_val.configure(text=f"{dur:.2f} {unit}")

        # Update status of cuts on timeline
        clips = getattr(getattr(self, "nle_project", None), "clips", [])
        n_cuts = max(0, len(clips) - 1)
        if hasattr(self, "lbl_trans_status"):
            if n_cuts <= 0:
                txt = "🎬 مقطع واحد فقط (قسّم الفيديو بـ Ctrl+B لإضافة انتقالات)" if is_ar else "🎬 1 clip (Split video with Ctrl+B to add transitions)"
            else:
                txt = f"🎬 يوجد {len(clips)} مقاطع و {n_cuts} انتقالات على التايم لاين" if is_ar else f"🎬 {len(clips)} clips & {n_cuts} cut transitions on timeline"
            self.lbl_trans_status.configure(text=txt)

    def _on_studio_trans_selected(self, _e=None):
        clips = getattr(getattr(self, "nle_project", None), "clips", [])
        n_cuts = max(0, len(clips) - 1)
        if n_cuts <= 0:
            is_ar = getattr(self, "language_var", tk.StringVar(value="English")).get() == "العربية"
            msg = (
                "⚠️ لا يمكن تفعيل الانتقالات لعدم وجود تقطيعات في الفيديو!\n\n"
                "يرجى تقسيم الفيديو أولاً (Ctrl+B) عند الموضع المطلوب لإضافة حركة انتقال."
                if is_ar
                else "⚠️ No cuts in video! Please split video first (Ctrl+B) to add transitions."
            )
            messagebox.showwarning(self.title(), msg)
            return

        disp = self.trans_preset_var.get()
        k = getattr(self, "_studio_trans_map", {}).get(disp, "smoothleft")
        tc = self.video_branding_config.get("transitions_config")
        if not isinstance(tc, dict):
            tc = dict(DEFAULT_TRANSITIONS_CONFIG)
            self.video_branding_config["transitions_config"] = tc
        tc["default_transition"] = k
        tc["enabled"] = True
        self.trans_enable_var.set(True)
        self.push_app_undo(f"تغيير حركة الانتقال: {disp}", f"Change Transition: {k}")
        self._save_settings()
        self._refresh_master_export_summary()
        self.refresh_video_transitions_panel()
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.redraw()

    def _on_studio_trans_slider(self, _v=None):
        dur = round(self.trans_dur_var.get(), 2)
        tc = self.video_branding_config.get("transitions_config")
        if not isinstance(tc, dict):
            tc = dict(DEFAULT_TRANSITIONS_CONFIG)
            self.video_branding_config["transitions_config"] = tc
        tc["default_duration"] = dur
        is_ar = getattr(self, "language_var", tk.StringVar(value="English")).get() == "العربية"
        unit = "ثانية" if is_ar else "s"
        if hasattr(self, "lbl_trans_dur_val"):
            self.lbl_trans_dur_val.configure(text=f"{dur:.2f} {unit}")
        self._save_settings()

    def _on_studio_trans_toggle(self):
        clips = getattr(getattr(self, "nle_project", None), "clips", [])
        n_cuts = max(0, len(clips) - 1)
        en = bool(self.trans_enable_var.get())

        if en and n_cuts <= 0:
            self.trans_enable_var.set(False)
            is_ar = getattr(self, "language_var", tk.StringVar(value="English")).get() == "العربية"
            msg = (
                "⚠️ لا يمكن تفعيل أو إضافة انتقالات لعدم وجود تقطيعات في الفيديو!\n\n"
                "يرجى تقسيم الفيديو أولاً (بالمقص أو بالضغط على Ctrl+B عند الموضع المطلوب) لتتمكن من إضافة حركة انتقال بين المقطعين."
                if is_ar
                else "⚠️ Cannot enable transitions because there are no cuts in the video!\n\nPlease split the video first (press Ctrl+B or use Blade tool) to add transitions between clips."
            )
            messagebox.showwarning(self.title(), msg)
            return

        tc = self.video_branding_config.get("transitions_config")
        if not isinstance(tc, dict):
            tc = dict(DEFAULT_TRANSITIONS_CONFIG)
            self.video_branding_config["transitions_config"] = tc
        tc["enabled"] = en
        self.push_app_undo("تفعيل الانتقالات" if en else "تعطيل الانتقالات", "Toggle Transitions")
        self._save_settings()
        self._refresh_master_export_summary()
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.redraw()

    def _set_studio_trans_quick_duration(self, dur: float):
        self.trans_dur_var.set(round(dur, 2))
        self._on_studio_trans_slider()

    def _apply_studio_quick_trans(self, key: str):
        clips = getattr(getattr(self, "nle_project", None), "clips", [])
        n_cuts = max(0, len(clips) - 1)
        if n_cuts <= 0:
            is_ar = getattr(self, "language_var", tk.StringVar(value="English")).get() == "العربية"
            msg = (
                "⚠️ لا يمكن إضافة انتقالات لعدم وجود تقطيعات في الفيديو!\n\n"
                "يرجى تقسيم الفيديو أولاً (بالمقص أو بالضغط على Ctrl+B عند الموضع المطلوب) لإضافة حركة انتقال."
                if is_ar
                else "⚠️ No cuts in video! Please split video first (Ctrl+B) to add transitions."
            )
            messagebox.showwarning(self.title(), msg)
            return

        tc = self.video_branding_config.get("transitions_config")
        if not isinstance(tc, dict):
            tc = dict(DEFAULT_TRANSITIONS_CONFIG)
            self.video_branding_config["transitions_config"] = tc
        tc["default_transition"] = key
        tc["enabled"] = True
        self.trans_enable_var.set(True)
        info = get_transition_info(key)
        is_ar = getattr(self, "language_var", tk.StringVar(value="English")).get() == "العربية"
        t_name = info.get("label_ar") if is_ar else info.get("label_en")
        self.push_app_undo(f"تطبيق انتقال: {t_name}", f"Apply Transition: {key}")
        self._save_settings()
        self._refresh_master_export_summary()
        self.refresh_video_transitions_panel()
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.redraw()

    # -------------------------------------------------------------------------
    # Drag & Drop Hand Placement & Wand Tool
    # -------------------------------------------------------------------------
    def _on_start_trans_drag(self, event):
        clips = getattr(getattr(self, "nle_project", None), "clips", [])
        n_cuts = max(0, len(clips) - 1)
        is_ar = getattr(self, "language_var", tk.StringVar(value="English")).get() == "العربية"

        if n_cuts <= 0:
            msg = (
                "⚠️ لا توجد تقطيعات في التايم لاين حالياً!\n\n"
                "يرجى تقسيم الفيديو أولاً (بالمقص أو Ctrl+B عند الموضع المطلوب) لتتمكن من وضع حركة انتقال بين المقطعين."
                if is_ar
                else "⚠️ No cuts on timeline! Please split video first (Ctrl+B) to add transitions."
            )
            messagebox.showwarning(self.title(), msg)
            return

        disp_txt = self.trans_preset_var.get()
        key = getattr(self, "_studio_trans_map", {}).get(disp_txt, "smoothleft")
        dur = round(float(self.trans_dur_var.get()), 2)
        info = get_transition_info(key)
        icon = info.get("icon", "✨")

        ghost = tk.Toplevel(self)
        ghost.overrideredirect(True)
        ghost.attributes("-topmost", True)
        g_lbl = tk.Label(
            ghost,
            text=f"{icon} {disp_txt} ({dur}s)",
            bg="#1f6feb",
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=5,
            relief="solid",
            bd=1,
        )
        g_lbl.pack()
        ghost.geometry(f"+{event.x_root + 15}+{event.y_root + 15}")
        self._trans_ghost = ghost
        self._trans_drag_info = (key, dur)

        def _on_motion(e):
            if hasattr(self, "_trans_ghost") and self._trans_ghost and self._trans_ghost.winfo_exists():
                self._trans_ghost.geometry(f"+{e.x_root + 15}+{e.y_root + 15}")
                if hasattr(self, "davinci_timeline"):
                    self.davinci_timeline.on_external_trans_drag_hover(e.x_root, e.y_root, key, dur)

        def _on_release(e):
            self.unbind_all("<B1-Motion>")
            self.unbind_all("<ButtonRelease-1>")
            if hasattr(self, "_trans_ghost") and self._trans_ghost:
                try:
                    self._trans_ghost.destroy()
                except Exception:
                    pass
                self._trans_ghost = None
            if hasattr(self, "davinci_timeline"):
                self.davinci_timeline.on_external_trans_drag_drop(e.x_root, e.y_root, key, dur)
            self.refresh_video_transitions_panel()

        self.bind_all("<B1-Motion>", _on_motion)
        self.bind_all("<ButtonRelease-1>", _on_release)

    def _toggle_transition_placement_tool(self):
        clips = getattr(getattr(self, "nle_project", None), "clips", [])
        n_cuts = max(0, len(clips) - 1)
        is_ar = getattr(self, "language_var", tk.StringVar(value="English")).get() == "العربية"

        if n_cuts <= 0:
            msg = (
                "⚠️ لا توجد تقطيعات في التايم لاين حالياً!\n\n"
                "يرجى تقسيم الفيديو أولاً (بالمقص أو Ctrl+B عند الموضع المطلوب) لتتمكن من وضع حركة انتقال بين المقطعين."
                if is_ar
                else "⚠️ No cuts on timeline! Please split video first (Ctrl+B) to add transitions."
            )
            messagebox.showwarning(self.title(), msg)
            return

        if not hasattr(self, "davinci_timeline"):
            return

        cur_mode = getattr(self.davinci_timeline, "tool_mode", "select")
        if cur_mode == "transition_place":
            self.davinci_timeline.set_tool_mode("select")
            if hasattr(self, "btn_place_trans_wand"):
                self.btn_place_trans_wand.configure(style="Player.TButton")
            self.davinci_timeline.show_hud_toast("تم إلغاء أداة وضع الانتقال" if is_ar else "Transition placement canceled")
        else:
            self.davinci_timeline.set_tool_mode("transition_place")
            if hasattr(self, "btn_place_trans_wand"):
                self.btn_place_trans_wand.configure(style="PrimaryPlayer.TButton")
            self.davinci_timeline.show_hud_toast("🪄 انقر على أي قطع في التايم لاين لوضع الانتقال المختار" if is_ar else "🪄 Click any timeline cut to place selected transition")

