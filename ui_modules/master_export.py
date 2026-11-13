"""
Master Export Controller Mixin
Handles selective modular export orchestration, branding configs, silence options, and export execution.
"""

import copy
import re
import sys
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, filedialog

from video_studio.aspect_ratios import ASPECT_RATIOS
from video_studio.color_grading import is_color_neutral
from video_studio.transitions import get_transition_info
import convert


class MasterExportMixin:
    """Provides master video and audio export methods for MediaAudioStudioApp."""

    def _set_all_export_toggles(self, state: bool):
        val = bool(state)
        for v_attr in (
            "export_opt_framing_var",
            "export_opt_timeline_var",
            "export_opt_overlays_var",
            "trim_color_var",
            "trim_remove_silence_var",
            "export_opt_audio_fx_var",
            "trim_burn_subs_var",
            "export_opt_transcript_files_var",
        ):
            if hasattr(self, v_attr):
                getattr(self, v_attr).set(val)
        self._on_trim_branding_toggle()

    def _refresh_modular_export_combos(self):
        if not hasattr(self, "export_format_combo"):
            return
        is_ar = self.language_var.get() == "العربية"
        fmt_items = [
            ("same", "نفس الصيغة الأصلية" if is_ar else "Same as Source"),
            (".mp4", "MP4 (H.264 متوافق شامل)" if is_ar else "MP4 (H.264 Universal)"),
            (".mp4_hevc", "MP4 (H.265 ضغط فائق)" if is_ar else "MP4 (H.265 / HEVC Ultra Compress)"),
            (".mkv", "MKV"),
            (".mov", "MOV"),
            (".webm", "WebM (VP9)"),
            (".avi", "AVI"),
            (".mp3", "MP3 (صوت فقط)" if is_ar else "MP3 (Audio Only)"),
        ]
        self._exp_fmt_map = {disp: k for k, disp in fmt_items}
        self._exp_fmt_rev = {k: disp for k, disp in fmt_items}
        self.export_format_combo.configure(values=[disp for _, disp in fmt_items])
        cur_fk = getattr(self, "export_format_key", "same")
        self.export_format_combo_var.set(self._exp_fmt_rev.get(cur_fk, fmt_items[0][1]))

        sz_items = [
            ("Match Source", "🎯 نفس جودة وحجم المصدر" if is_ar else "🎯 Match Source (Original Size)"),
            ("Smart Compress", "⚡ ضغط ذكي ممتاز (تقليل الحجم مع حفظ الجودة)" if is_ar else "⚡ Smart Compress (Crisp Quality, Small Size)"),
            ("High Compress", "🗜️ ضغط قوي (أصغر حجم ممكن للمشاركة)" if is_ar else "🗜️ High Compression (Smallest Size)"),
            ("Very High", "جودة فائقة (CRF 18)" if is_ar else "Ultra Quality (CRF 18)"),
            ("High", "جودة عالية متوازنة (CRF 21)" if is_ar else "High Quality (CRF 21)"),
            ("Medium", "جودة متوسطة مضغوطة (CRF 26)" if is_ar else "Medium Quality (CRF 26)"),
        ]
        self._exp_sz_map = {disp: k for k, disp in sz_items}
        self._exp_sz_rev = {k: disp for k, disp in sz_items}
        self.export_size_combo.configure(values=[disp for _, disp in sz_items])
        cur_sk = getattr(self, "export_size_key", "Match Source")
        self.export_size_combo_var.set(self._exp_sz_rev.get(cur_sk, sz_items[0][1]))

    def _on_export_format_or_size_changed(self, _e=None):
        if hasattr(self, "_exp_fmt_map"):
            self.export_format_key = self._exp_fmt_map.get(self.export_format_combo_var.get(), "same")
        if hasattr(self, "_exp_sz_map"):
            self.export_size_key = self._exp_sz_map.get(self.export_size_combo_var.get(), "Match Source")
        self._refresh_master_export_summary()

    def _on_export_scope_changed(self):
        self._refresh_master_export_summary()

    def export_selected_clip_only(self, clip_idx=None):
        if clip_idx is None:
            sel = getattr(self, "player_canvas_selected", None)
            if isinstance(sel, tuple) and sel[0] == "clip":
                clip_idx = sel[1]
            elif hasattr(self, "davinci_timeline") and self.davinci_timeline.selected_ref and self.davinci_timeline.selected_ref[0] == "clip":
                clip_idx = self.davinci_timeline.selected_ref[1]
            else:
                clip_idx = 0

        if not hasattr(self, "nle_project") or not (0 <= clip_idx < len(self.nle_project.clips)):
            is_ar = self.language_var.get() == "العربية"
            messagebox.showwarning(self.text("app_title"), "يرجى تحديد مقطع من شريط التايم لاين لتصديره." if is_ar else "Please select a clip on the timeline first.")
            return

        self.player_canvas_selected = ("clip", clip_idx)
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.selected_ref = ("clip", clip_idx)
            self.davinci_timeline.redraw()

        if hasattr(self, "export_scope_var"):
            self.export_scope_var.set("selected")

        c = self.nle_project.clips[clip_idx]
        self.trim_start_var.set(self._format_time(float(c.get("src_start", 0.0))))
        self.trim_end_var.set(self._format_time(float(c.get("src_end", 0.0))))

        self._refresh_master_export_summary()
        self.start_master_export()

    def _refresh_master_export_summary(self):
        if not hasattr(self, "master_export_summary_var"):
            return
        is_ar = self.language_var.get() == "العربية"

        # Modular selection states
        inc_framing = bool(self.export_opt_framing_var.get()) if hasattr(self, "export_opt_framing_var") else True
        inc_timeline = bool(self.export_opt_timeline_var.get()) if hasattr(self, "export_opt_timeline_var") else True
        inc_overlays = bool(self.export_opt_overlays_var.get()) if hasattr(self, "export_opt_overlays_var") else True
        inc_color = bool(self.trim_color_var.get()) if hasattr(self, "trim_color_var") else False
        inc_silence = bool(self.trim_remove_silence_var.get()) if hasattr(self, "trim_remove_silence_var") else False
        inc_audio = bool(self.export_opt_audio_fx_var.get()) if hasattr(self, "export_opt_audio_fx_var") else True
        inc_subs = bool(self.trim_burn_subs_var.get()) if hasattr(self, "trim_burn_subs_var") else False
        inc_transcript = bool(self.export_opt_transcript_files_var.get()) if hasattr(self, "export_opt_transcript_files_var") else False

        ratio = self.trim_aspect_var.get() if hasattr(self, "trim_aspect_var") else "original"
        ratio_name = ASPECT_RATIOS.get(ratio, {}).get("label_ar" if is_ar else "label_en", ratio)

        has_nle = hasattr(self, "nle_project")
        v4_on = (not has_nle) or self.nle_project.track_enabled.get("V4", True)
        v3_on = (not has_nle) or self.nle_project.track_enabled.get("V3", True)
        v2_on = (not has_nle) or self.nle_project.track_enabled.get("V2", True)

        media_count = len(self.nle_project.media_items) if (has_nle and inc_overlays and v2_on) else 0
        text_count = len(self.nle_project.text_items) if (has_nle and inc_overlays and v3_on) else (1 if (inc_overlays and v3_on and self.video_branding_config.get("title_text")) else 0)
        has_logo = bool(inc_overlays and v4_on and ((has_nle and self.nle_project.logo_items) or self.video_branding_config.get("logo_path")))

        export_scope = self.export_scope_var.get() if hasattr(self, "export_scope_var") else "all"
        is_clip_only = (export_scope == "selected")

        selected_clip_idx = None
        if has_nle:
            sel_ref = getattr(self, "player_canvas_selected", None)
            if isinstance(sel_ref, tuple) and sel_ref[0] == "clip":
                selected_clip_idx = sel_ref[1]
            elif hasattr(self, "davinci_timeline") and self.davinci_timeline.selected_ref and self.davinci_timeline.selected_ref[0] == "clip":
                selected_clip_idx = self.davinci_timeline.selected_ref[1]

        clip_count = len(self.nle_project.clips) if has_nle else 1

        parts = []
        if is_clip_only and has_nle and selected_clip_idx is not None and 0 <= selected_clip_idx < len(self.nle_project.clips):
            c_info = self.nle_project.clips[selected_clip_idx]
            dur_c = (float(c_info.get("src_end", 0.0)) - float(c_info.get("src_start", 0.0))) / max(0.25, float(c_info.get("speed", 1.0) or 1.0))
            parts.append(f"🎞️ المقطع المحدد (#{selected_clip_idx + 1} - {dur_c:.1f}ث)" if is_ar else f"🎞️ Selected Clip (#{selected_clip_idx + 1} - {dur_c:.1f}s)")
            if hasattr(self, "btn_master_export") and self.btn_master_export:
                self.btn_master_export.configure(text=f"🚀 تصدير المقطع المحدد فقط (#{selected_clip_idx + 1})" if is_ar else f"🚀 Export Selected Clip Only (#{selected_clip_idx + 1})")
        else:
            has_clip_edits = has_nle and inc_timeline and (self.nle_project.has_timeline_cuts_or_clip_fx() or clip_count > 1)
            if has_clip_edits:
                parts.append(f"🎬 {clip_count} مقاطع (كامل الشريط)" if is_ar else f"🎬 {clip_count} clips (full sequence)")
            elif not inc_timeline:
                parts.append("🎬 ملف كامل بدون تقطيع" if is_ar else "🎬 Full uncut file")
            if hasattr(self, "btn_master_export") and self.btn_master_export:
                self.btn_master_export.configure(text=self.text("master_export_btn"))

        if inc_framing:
            parts.append(f"📐 {ratio_name}")
        else:
            parts.append("📐 أبعاد المصدر" if is_ar else "📐 Original Ratio")

        if inc_silence:
            parts.append("✂️ قص السكتات" if is_ar else "✂️ Silence Cut")
        tc = self.video_branding_config.get("transitions_config")
        if tc and tc.get("enabled"):
            t_info = get_transition_info(tc.get("default_transition", "smoothleft"))
            t_lbl = t_info.get("label_ar") if is_ar else t_info.get("label_en")
            parts.append(f"✨ {t_lbl}")
        if inc_color:
            parts.append("🎨 ألوان" if is_ar else "🎨 Color")
        if media_count > 0:
            parts.append(f"⭐ {media_count} أيقونة/صورة" if is_ar else f"⭐ {media_count} icons")
        if text_count > 0:
            parts.append(f"📝 {text_count} نصوص" if is_ar else f"📝 {text_count} texts")
        if has_logo:
            parts.append("🛡️ لوجو" if is_ar else "🛡️ Logo")
        if inc_audio:
            parts.append("🔊 صوت" if is_ar else "🔊 Audio")
        if inc_subs:
            parts.append("💬 دمج ترجمة" if is_ar else "💬 Burn Subs")
        if inc_transcript:
            parts.append("📄 تفريغ نصي" if is_ar else "📄 Transcript")

        self.master_export_summary_var.set(" | ".join(parts))

    def _build_silence_config(self):
        if not hasattr(self, "trim_remove_silence_var") or not self.trim_remove_silence_var.get():
            return None
        noise_db, min_dur, padding, mode = self._get_silence_params()
        cfg = {
            "enabled": True,
            "noise_db": noise_db,
            "min_silence_sec": min_dur,
            "padding_sec": padding,
            "mode": mode,
            "speed_factor": 4,
            "sync_subtitles": bool(self.silence_sync_subs_var.get() if hasattr(self, "silence_sync_subs_var") else True),
        }
        if getattr(self, "silence_analysis_result", None) and self.silence_analysis_result.get("keep_intervals"):
            cfg["keep_intervals"] = self.silence_analysis_result["keep_intervals"]
        return cfg

    def _build_branding_configs(self, remap_subs_to_nle: bool = False):
        """
        Builds complete DaVinci transform, V2/V3/V4 multi-track overlays, color grading,
        and timeline-synchronized subtitle configs for FFmpeg export.
        """
        aspect_ratio = self.trim_aspect_var.get() if hasattr(self, "trim_aspect_var") else "original"
        fit_mode = self.video_branding_config.get("fit_mode", "crop")
        video_transform = {
            "zoom": float(self.video_branding_config.get("video_zoom", 1.0)),
            "pan_x": float(self.video_branding_config.get("video_pan_x", 0.0)),
            "pan_y": float(self.video_branding_config.get("video_pan_y", 0.0)),
            "flip_h": bool(self.video_branding_config.get("video_flip_h", False)),
            "clamp_edges": bool(self.video_branding_config.get("video_clamp_edges", True)),
        }

        has_nle = hasattr(self, "nle_project")
        logo_cfg = None
        logo_items = None
        title_cfg = None
        media_overlays = None
        sub_cfg = None

        # 1. V2 Media Overlays
        if has_nle and self.nle_project.track_enabled.get("V2", True):
            valid_v2 = [
                dict(it) for it in self.nle_project.media_items
                if it.get("enabled", True) and (it.get("type") != "image" or (it.get("path") and Path(str(it["path"])).is_file()))
            ]
            if valid_v2:
                media_overlays = valid_v2

        # 2. V4 Logo Watermarks
        v4_on = (not has_nle) or self.nle_project.track_enabled.get("V4", True)
        if hasattr(self, "trim_logo_var") and self.trim_logo_var.get() and v4_on:
            if has_nle and self.nle_project.logo_items:
                valid_v4 = [
                    dict(it) for it in self.nle_project.logo_items
                    if it.get("enabled", True) and it.get("path") and Path(str(it["path"])).is_file()
                ]
                if valid_v4:
                    logo_items = valid_v4
            if not logo_items:
                logo_p = self.video_branding_config.get("logo_path", "").strip()
                if logo_p and Path(logo_p).is_file():
                    logo_cfg = {
                        "enabled": True,
                        "path": logo_p,
                        "x_pct": float(self.video_branding_config.get("logo_x", 0.82)),
                        "y_pct": float(self.video_branding_config.get("logo_y", 0.04)),
                        "position": self.video_branding_config.get("logo_position", "top_right"),
                        "scale": float(self.video_branding_config.get("logo_scale", 0.16)),
                        "opacity": float(self.video_branding_config.get("logo_opacity", 0.85)),
                    }
                else:
                    is_clip_scope = hasattr(self, "export_scope_var") and self.export_scope_var.get() == "selected"
                    if not is_clip_scope and getattr(self, "_allow_interactive_prompts", True):
                        is_ar = self.language_var.get() == "العربية"
                        ask_msg = (
                            "خيار اللوجو مفعل ولكن لم يتم اختيار صورة شعار بعد.\nهل تريد اختيار صورة لوجو الآن؟ (اضغط 'لا' للتصدير بدون لوجو)"
                            if is_ar else
                            "Logo watermark is enabled, but no logo file is selected.\nWould you like to choose a logo image now? (Click 'No' to export without logo)"
                        )
                        if messagebox.askyesno(self.text("app_title"), ask_msg):
                            self._nle_add_element("logo", self.nle_playhead_sec)
                            if has_nle and self.nle_project.logo_items:
                                valid_v4 = [
                                    dict(it) for it in self.nle_project.logo_items
                                    if it.get("enabled", True) and it.get("path") and Path(str(it["path"])).is_file()
                                ]
                                if valid_v4:
                                    logo_items = valid_v4

        # 3. V3 Text+ Overlays
        v3_on = (not has_nle) or self.nle_project.track_enabled.get("V3", True)
        if hasattr(self, "trim_title_var") and self.trim_title_var.get() and v3_on:
            raw_items = self.nle_project.text_items if has_nle else self.video_branding_config.get("text_items", [])
            valid_items = [
                dict(it) for it in raw_items
                if it.get("enabled", True) and str(it.get("text", "")).strip()
            ]
            if valid_items:
                title_cfg = {
                    "enabled": True,
                    "text_items": valid_items,
                }
            elif self.video_branding_config.get("title_text", "").strip():
                title_cfg = {
                    "enabled": True,
                    "text": self.video_branding_config.get("title_text").strip(),
                    "position": self.video_branding_config.get("title_position", "top"),
                    "bg_color": self.video_branding_config.get("title_bg", "black"),
                    "text_color": self.video_branding_config.get("title_color", "white"),
                }

        # 4. Subtitles
        if hasattr(self, "trim_burn_subs_var") and self.trim_burn_subs_var.get():
            srt_path = None
            raw_segments = None
            if getattr(self, "caption_current_result", None) and (self.caption_current_result.get("srt") or self.caption_current_result.get("segments")):
                raw_segments = self.caption_current_result.get("segments")
                if not raw_segments and self.caption_current_result.get("srt"):
                    from video_studio.arabic_support import parse_srt_segments
                    raw_segments = parse_srt_segments(self.caption_current_result["srt"])
                if remap_subs_to_nle and has_nle and raw_segments and self.nle_project.has_timeline_cuts_or_clip_fx():
                    srt_content = convert.generate_srt_content(self.nle_project.remap_srt_segments_to_timeline(raw_segments))
                else:
                    srt_content = self.caption_current_result.get("srt") or convert.generate_srt_content(raw_segments or [])
                cache_dir = getattr(convert, "CACHE_DIR", convert.APP_DIR / ".cache")
                cache_dir.mkdir(parents=True, exist_ok=True)
                sub_tmp = cache_dir / f"trim_subs_{int(time.time() * 1000)}.srt"
                sub_tmp.write_text(srt_content, encoding="utf-8-sig")
                srt_path = sub_tmp
            elif self.input_path and self.input_path.with_suffix(".srt").exists():
                srt_path = self.input_path.with_suffix(".srt")
            else:
                is_clip_scope = hasattr(self, "export_scope_var") and self.export_scope_var.get() == "selected"
                if not is_clip_scope and getattr(self, "_allow_interactive_prompts", True):
                    is_ar = self.language_var.get() == "العربية"
                    ask_msg = "خيار دمج الترجمة مفعل ولكن لم يتم استخراج ترجمة لهذا الفيديو بعد.\nهل تريد اختيار ملف ترجمة خارجي (.srt) لدمجه؟" if is_ar else "Subtitle burning is enabled, but no subtitles were generated yet.\nWould you like to select an external (.srt) file?"
                    if messagebox.askyesno(self.text("app_title"), ask_msg):
                        dlg_title = "اختر ملف الترجمة (.srt)" if is_ar else "Select Subtitle file (.srt)"
                        chosen_srt = filedialog.askopenfilename(
                            parent=self,
                            title=dlg_title,
                            filetypes=[("Subtitle files", "*.srt *.vtt *.ass"), ("All files", "*.*")],
                        )
                        if chosen_srt:
                            srt_path = Path(chosen_srt)

            if srt_path and srt_path.is_file() and raw_segments is None and remap_subs_to_nle and has_nle and self.nle_project.has_timeline_cuts_or_clip_fx():
                if srt_path.suffix.lower() == ".srt":
                    try:
                        from video_studio.arabic_support import parse_srt_segments
                        parsed_ext = parse_srt_segments(srt_path.read_text(encoding="utf-8-sig", errors="replace"))
                        if parsed_ext:
                            remapped_ext = self.nle_project.remap_srt_segments_to_timeline(parsed_ext)
                            cache_dir = getattr(convert, "CACHE_DIR", convert.APP_DIR / ".cache")
                            cache_dir.mkdir(parents=True, exist_ok=True)
                            sub_tmp = cache_dir / f"nle_remapped_subs_{int(time.time() * 1000)}.srt"
                            sub_tmp.write_text(convert.generate_srt_content(remapped_ext), encoding="utf-8-sig")
                            srt_path = sub_tmp
                    except Exception:
                        pass

            if srt_path and srt_path.is_file():
                sub_cfg = {
                    "enabled": True,
                    "srt_path": srt_path,
                    "style": getattr(self, "subtitle_style", {}),
                }

        # 5. Color Grading
        color_cfg = None
        if hasattr(self, "trim_color_var") and self.trim_color_var.get():
            raw_c = self.video_branding_config.get("color_config", {})
            if isinstance(raw_c, dict) and not is_color_neutral(raw_c):
                color_cfg = dict(raw_c)
                color_cfg["enabled"] = True

        return {
            "aspect_ratio": aspect_ratio,
            "fit_mode": fit_mode,
            "video_transform": video_transform,
            "color_cfg": color_cfg,
            "logo_cfg": logo_cfg,
            "logo_items": logo_items,
            "title_cfg": title_cfg,
            "media_overlays": media_overlays,
            "sub_cfg": sub_cfg,
        }

    def start_master_export(self):
        if self.worker and self.worker.is_alive():
            return
        if not self.input_path or not self.input_path.is_file() or not convert.has_video_stream(self.input_path):
            messagebox.showwarning(self.text("app_title"), self.text("video_required"))
            return

        # Read Selective Modular Export options
        inc_framing = bool(self.export_opt_framing_var.get()) if hasattr(self, "export_opt_framing_var") else True
        inc_timeline = bool(self.export_opt_timeline_var.get()) if hasattr(self, "export_opt_timeline_var") else True
        inc_overlays = bool(self.export_opt_overlays_var.get()) if hasattr(self, "export_opt_overlays_var") else True
        inc_color = bool(self.trim_color_var.get()) if hasattr(self, "trim_color_var") else False
        inc_silence = bool(self.trim_remove_silence_var.get()) if hasattr(self, "trim_remove_silence_var") else False
        inc_audio = bool(self.export_opt_audio_fx_var.get()) if hasattr(self, "export_opt_audio_fx_var") else True
        inc_burn_subs = bool(self.trim_burn_subs_var.get()) if hasattr(self, "trim_burn_subs_var") else False
        inc_transcript = bool(self.export_opt_transcript_files_var.get()) if hasattr(self, "export_opt_transcript_files_var") else False

        # Check export scope: All Timeline Sequence vs Selected Clip Only
        export_scope = self.export_scope_var.get() if hasattr(self, "export_scope_var") else "all"
        is_clip_only = (export_scope == "selected")

        has_nle = hasattr(self, "nle_project") and bool(self.nle_project.clips)
        selected_clip = None
        selected_clip_idx = None
        if has_nle:
            sel_ref = getattr(self, "player_canvas_selected", None)
            if isinstance(sel_ref, tuple) and sel_ref[0] == "clip":
                c_idx = sel_ref[1]
                if 0 <= c_idx < len(self.nle_project.clips):
                    selected_clip = self.nle_project.clips[c_idx]
                    selected_clip_idx = c_idx
            elif hasattr(self, "davinci_timeline") and self.davinci_timeline.selected_ref and self.davinci_timeline.selected_ref[0] == "clip":
                c_idx = self.davinci_timeline.selected_ref[1]
                if 0 <= c_idx < len(self.nle_project.clips):
                    selected_clip = self.nle_project.clips[c_idx]
                    selected_clip_idx = c_idx

        if is_clip_only and selected_clip is None and has_nle:
            selected_clip = self.nle_project.clips[0]
            selected_clip_idx = 0

        # Determine time range and clips
        if is_clip_only and selected_clip is not None:
            c_s0 = float(selected_clip.get("src_start", 0.0))
            c_s1 = float(selected_clip.get("src_end", 0.0))
            c_spd = max(0.25, float(selected_clip.get("speed", 1.0) or 1.0))
            start_seconds = c_s0
            dur_seconds = max(0.1, (c_s1 - c_s0) / c_spd)
            use_nle_clips = True
            sel_copy = copy.deepcopy(selected_clip)
            sel_copy["tl_start"] = 0.0
            sel_copy["tl_dur"] = dur_seconds
            sel_copy["tl_end"] = dur_seconds
            nle_clips = [sel_copy]
            scope_tag = f"clip{selected_clip_idx + 1}"
        else:
            scope_tag = ""
            start_seconds = 0.0
            dur_seconds = None
            s_raw = self.trim_start_var.get().strip()
            e_raw = self.trim_end_var.get().strip()
            try:
                s_val = convert.parse_time_seconds(s_raw)
                e_val = convert.parse_time_seconds(e_raw)
                if e_val > s_val and (s_val > 0 or (self.media_duration and e_val < self.media_duration - 1)):
                    start_seconds = s_val
                    dur_seconds = e_val - s_val
            except Exception:
                start_seconds = 0.0
                dur_seconds = None

            has_manual_trim = (start_seconds > 0) or (dur_seconds is not None)
            a1_muted = has_nle and (not self.nle_project.track_enabled.get("A1", True))
            use_nle_clips = inc_timeline and (not has_manual_trim) and has_nle and (self.nle_project.has_timeline_cuts_or_clip_fx() or a1_muted)
            nle_clips = None
            if use_nle_clips:
                self.nle_project.recompute_timeline()
                nle_clips = copy.deepcopy(self.nle_project.clips)
                if a1_muted:
                    for cl in nle_clips:
                        cl["muted"] = True

        try:
            configs = self._build_branding_configs(remap_subs_to_nle=use_nle_clips)
        except Exception as exc:
            messagebox.showerror(self.text("app_title"), f"Error preparing branding: {exc}")
            return
        if configs is None:
            return

        # Modular Framing & Video Transform
        if inc_framing:
            aspect_ratio = configs["aspect_ratio"]
            fit_mode = configs["fit_mode"]
            video_transform = configs["video_transform"]
        else:
            aspect_ratio = "original"
            fit_mode = "fit"
            video_transform = {"zoom": 1.0, "pan_x": 0.0, "pan_y": 0.0, "flip_h": False, "flip_v": False}

        if is_clip_only and selected_clip and selected_clip.get("custom_transform"):
            video_transform = {
                "zoom": selected_clip.get("zoom", 1.0),
                "pan_x": selected_clip.get("pan_x", 0.0),
                "pan_y": selected_clip.get("pan_y", 0.0),
                "flip_h": selected_clip.get("flip_h", False),
                "clamp_edges": True,
            }

        # Modular Overlays
        if inc_overlays:
            logo_cfg = configs["logo_cfg"]
            logo_items = configs["logo_items"]
            title_cfg = configs["title_cfg"]
            media_overlays = configs["media_overlays"]
        else:
            logo_cfg = None
            logo_items = None
            title_cfg = None
            media_overlays = None

        if is_clip_only and selected_clip is not None:
            c_tl_start = float(selected_clip.get("tl_start", 0.0))
            c_tl_end = float(selected_clip.get("tl_end", c_tl_start + dur_seconds))

            def _filter_and_shift(items_list):
                if not items_list:
                    return None
                shifted = []
                for it in items_list:
                    if not it.get("enabled", True):
                        continue
                    if it.get("full_duration", False):
                        shifted.append(copy.deepcopy(it))
                        continue
                    s = float(it.get("start_sec", 0.0) or 0.0)
                    e = float(it.get("end_sec", 0.0) or (s + 5.0))
                    if e > c_tl_start and s < c_tl_end:
                        new_it = copy.deepcopy(it)
                        new_it["start_sec"] = max(0.0, s - c_tl_start)
                        new_it["end_sec"] = min(dur_seconds, e - c_tl_start)
                        shifted.append(new_it)
                return shifted if shifted else None

            if media_overlays:
                media_overlays = _filter_and_shift(media_overlays)
            if logo_items:
                logo_items = _filter_and_shift(logo_items)
            if title_cfg and "text_items" in title_cfg and isinstance(title_cfg["text_items"], list):
                shifted_texts = _filter_and_shift(title_cfg["text_items"])
                if shifted_texts:
                    title_cfg = {"enabled": True, "text_items": shifted_texts}
                else:
                    title_cfg = None

        color_cfg = configs["color_cfg"] if inc_color else None
        silence_cfg = self._build_silence_config() if inc_silence else None

        if inc_audio:
            enhancement = self.selected_enhancement()
            boost_gain = self.boost_gain_var.get() if hasattr(self, "boost_gain_var") else 0
            audio_fx_filter = convert.ffmpeg_audio_filter_str(enhancement)
            if boost_gain != 0:
                gain_str = f"volume={boost_gain}dB"
                audio_fx_filter = f"{audio_fx_filter},{gain_str}" if audio_fx_filter else gain_str
        else:
            audio_fx_filter = None

        sub_cfg = configs["sub_cfg"] if inc_burn_subs else None
        if is_clip_only and selected_clip is not None and inc_burn_subs and sub_cfg and sub_cfg.get("srt_path"):
            try:
                from video_studio.arabic_support import parse_srt_segments
                s_orig = Path(sub_cfg["srt_path"])
                if s_orig.is_file():
                    parsed = parse_srt_segments(s_orig.read_text(encoding="utf-8-sig", errors="replace"))
                    if parsed:
                        c_s0 = float(selected_clip.get("src_start", 0.0))
                        c_s1 = float(selected_clip.get("src_end", 0.0))
                        c_spd = max(0.25, float(selected_clip.get("speed", 1.0) or 1.0))
                        clip_subs = []
                        for seg in parsed:
                            ss = float(seg.get("start", 0.0))
                            se = float(seg.get("end", 0.0))
                            ov_s = max(c_s0, ss)
                            ov_e = min(c_s1, se)
                            if ov_e - ov_s >= 0.12:
                                clip_subs.append({
                                    "start": round((ov_s - c_s0) / c_spd, 3),
                                    "end": round((ov_e - c_s0) / c_spd, 3),
                                    "text": seg.get("text", ""),
                                })
                        if clip_subs:
                            cache_dir = getattr(convert, "CACHE_DIR", convert.APP_DIR / ".cache")
                            cache_dir.mkdir(parents=True, exist_ok=True)
                            sub_clip_tmp = cache_dir / f"clip_subs_{int(time.time() * 1000)}.srt"
                            sub_clip_tmp.write_text(convert.generate_srt_content(clip_subs), encoding="utf-8-sig")
                            sub_cfg = dict(sub_cfg)
                            sub_cfg["srt_path"] = sub_clip_tmp
                        else:
                            sub_cfg = None
            except Exception:
                pass

        fmt_key = getattr(self, "export_format_key", "same")
        video_codec = "auto"
        if fmt_key == "same":
            target_ext = self.input_path.suffix.lower()
            if target_ext not in {".mp4", ".mkv", ".mov", ".webm", ".avi", ".mp3", ".m4a", ".wav"}:
                target_ext = ".mp4"
        elif fmt_key == ".mp4_hevc":
            target_ext = ".mp4"
            video_codec = "libx265"
        else:
            target_ext = fmt_key.lower()

        size_key = getattr(self, "export_size_key", "Match Source")
        quality = size_key

        is_ar = self.language_var.get() == "العربية"
        self._clear_log()
        self._begin_operation("master_export", self.btn_master_export)
        self._append_log("[Master Export] " + self.text("master_export_desc") + "\n")

        active_tags = []
        if inc_framing and aspect_ratio != "original":
            active_tags.append(f"كادر {aspect_ratio}" if is_ar else f"Framing {aspect_ratio}")
        if inc_timeline and nle_clips:
            active_tags.append(f"تايم لاين ({len(nle_clips)} مقطع)" if is_ar else f"Timeline ({len(nle_clips)} clips)")
        if inc_color and color_cfg:
            active_tags.append("تعديل ألوان" if is_ar else "Color Grading")
        if inc_silence and silence_cfg:
            active_tags.append("قص السكتات" if is_ar else "Silence Removal")
        if inc_overlays and (logo_cfg or logo_items or title_cfg or media_overlays):
            active_tags.append("لوجو وعناصر" if is_ar else "Overlays & Logos")
        if inc_audio and audio_fx_filter:
            active_tags.append("تحسين الصوت" if is_ar else "Audio FX")
        if inc_burn_subs:
            active_tags.append("دمج ترجمة" if is_ar else "Burn Subs")
        if inc_transcript:
            active_tags.append("تفريغ نصي AI" if is_ar else "AI Transcript")

        tags_msg = " + ".join(active_tags) if active_tags else ("تصدير قياسي" if is_ar else "Standard Export")
        codec_tag = " (H.265 / HEVC)" if video_codec == "libx265" else ""
        self._append_log(f"[Mod Export] {'التعديلات النشطة' if is_ar else 'Active Edits'}: {tags_msg}\n")
        self._append_log(f"[Target] {'الصيغة' if is_ar else 'Format'}: {target_ext}{codec_tag} | {'الضغط/الجودة' if is_ar else 'Compression/Quality'}: {quality}\n")

        self.status_var.set(self.text("master_export_btn"))
        self._set_busy(True)
        self.progress.configure(mode="determinate", maximum=100, value=0)
        self.progress_var.set(self.text("progress_detail", current=0, total=1, file_percent=0, overall_percent=0, remaining_percent=100, elapsed="00:00", eta=self.text("estimating")))

        self.worker = threading.Thread(
            target=self._run_master_export,
            args=(
                start_seconds,
                dur_seconds,
                quality,
                target_ext,
                audio_fx_filter,
                aspect_ratio,
                fit_mode,
                color_cfg,
                logo_cfg,
                title_cfg,
                sub_cfg,
                silence_cfg,
                video_transform,
                media_overlays,
                logo_items,
                nle_clips,
                inc_transcript,
                inc_burn_subs,
                video_codec,
                scope_tag,
                is_ar,
            ),
            daemon=True,
        )
        self.worker.start()

    def _run_master_export(
        self,
        start_seconds,
        dur_seconds,
        quality,
        target_ext,
        audio_fx_filter,
        aspect_ratio,
        fit_mode,
        color_cfg,
        logo_cfg,
        title_cfg,
        sub_cfg,
        silence_cfg=None,
        video_transform=None,
        media_overlays=None,
        logo_items=None,
        nle_clips=None,
        inc_transcript=False,
        inc_burn_subs=False,
        video_codec="auto",
        scope_tag="",
        is_ar=True,
    ):
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        from gui import QueueWriter
        writer = QueueWriter(self.messages)
        sys.stdout = writer
        sys.stderr = writer

        out_dir = self.output_dir or self.input_path.parent / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = self.input_path.stem

        # 1. AI Audio Transcription (Faster-Whisper) only if requested
        active_sub_cfg = copy.deepcopy(sub_cfg) if sub_cfg else None
        existing_srt = None
        if active_sub_cfg and active_sub_cfg.get("srt_path"):
            p = Path(active_sub_cfg["srt_path"])
            if p.is_file():
                existing_srt = p
        if not existing_srt and self.input_path and self.input_path.with_suffix(".srt").is_file():
            existing_srt = self.input_path.with_suffix(".srt")

        if inc_transcript:
            if convert.whisper_available():
                self.messages.put("[AI Whisper] " + ("جاري استخراج التفريغ الصوتي بالذكاء الاصطناعي..." if is_ar else "Generating AI Speech-to-Text Transcription...") + "\n")
                try:
                    def _wh_prog(pct, cur_txt, *extra):
                        if self._progress_request:
                            self._progress_request(0, 1, self.input_path, min(95, int(pct * 0.4)))

                    trans_res = convert.transcribe_media(
                        source_path=self.input_path,
                        output_dir=out_dir,
                        model_size="small",
                        export_srt=True,
                        export_txt=True,
                        cancel_callback=self._operation_canceled,
                        progress_callback=_wh_prog,
                    )
                    if trans_res and trans_res.get("srt_path"):
                        existing_srt = Path(trans_res["srt_path"])
                        if inc_transcript and trans_res.get("txt_path"):
                            self.messages.put(f"[Transcript] Saved: {Path(trans_res['txt_path']).name}\n")
                except convert.CancelledError:
                    raise
                except Exception as w_exc:
                    self.messages.put(f"[Whisper Warning] Transcription error: {w_exc}\n")
            else:
                self.messages.put("[Whisper] faster-whisper not installed; run: py -3.12 -m pip install faster-whisper\n")

        if inc_burn_subs and existing_srt:
            if not active_sub_cfg:
                active_sub_cfg = {"enabled": True, "style": "Default"}
            active_sub_cfg["srt_path"] = str(existing_srt)

        # 2. Output file naming
        mod_tags = []
        if scope_tag:
            mod_tags.append(scope_tag)
        if aspect_ratio != "original":
            mod_tags.append(aspect_ratio.replace(":", "x"))
        if (not scope_tag) and nle_clips and len(nle_clips) > 1:
            mod_tags.append(f"{len(nle_clips)}clips")
        if silence_cfg and silence_cfg.get("enabled"):
            mod_tags.append("silence_cut")
        trans_cfg = self.video_branding_config.get("transitions_config")
        if trans_cfg and trans_cfg.get("enabled"):
            mod_tags.append("transitions")
        if color_cfg and not is_color_neutral(color_cfg):
            mod_tags.append("color")
        if media_overlays or logo_cfg or logo_items or title_cfg:
            mod_tags.append("styled")
        if active_sub_cfg and active_sub_cfg.get("enabled"):
            mod_tags.append("subs")
        if inc_transcript:
            mod_tags.append("transcript")
        if video_codec == "libx265":
            mod_tags.append("hevc")
        if quality in ("Smart Compress", "smart_compress"):
            mod_tags.append("compressed")
        elif quality in ("High Compress", "high_compress"):
            mod_tags.append("mini")

        tag_str = "_" + "_".join(mod_tags) if mod_tags else "_export"
        if dur_seconds is not None:
            tag_str += f"_{convert.format_time_label(start_seconds)}_to_{convert.format_time_label(start_seconds + dur_seconds)}"

        name = f"{stem}{tag_str}{target_ext}"
        output_path = convert.unique_output_path(out_dir / name)

        try:
            _last_render_playhead_sync = [0.0]
            _render_tl_base = float(start_seconds or 0.0)

            def _prog(pct, cur_s, tot_s):
                if self._progress_request:
                    base_off = 20 if (inc_transcript or inc_burn_subs) else 0
                    eff_pct = base_off + int(pct * ((100 - base_off) / 100.0))
                    self._progress_request(0, 1, self.input_path, eff_pct)

                # Zero-lag live timeline playhead visual follower during export
                now_wall = time.monotonic()
                if now_wall - _last_render_playhead_sync[0] >= 0.12:  # max ~8 updates/sec
                    _last_render_playhead_sync[0] = now_wall
                    target_tl_sec = _render_tl_base + float(cur_s or 0.0)
                    try:
                        self.after(0, lambda s=target_tl_sec: self._sync_render_playhead_safe(s))
                    except Exception:
                        pass

            result = convert.export_styled_video(
                video_path=self.input_path,
                output_path=output_path,
                start_seconds=start_seconds if start_seconds > 0 else None,
                duration_seconds=dur_seconds,
                aspect_ratio=aspect_ratio,
                fit_mode=fit_mode,
                video_transform=video_transform,
                color_config=color_cfg,
                transitions_config=trans_cfg,
                logo_config=logo_cfg,
                logo_items=logo_items,
                title_config=title_cfg,
                media_overlays=media_overlays,
                subtitle_config=active_sub_cfg,
                silence_config=silence_cfg,
                nle_clips=nle_clips,
                audio_enhancement_filter=audio_fx_filter,
                video_quality=quality,
                video_codec=video_codec,
                ffmpeg_exe=str(convert.ffmpeg_executable()),
                cancel_callback=self._operation_canceled,
                progress_callback=_prog,
                is_ar=is_ar,
            )
            if result:
                self.messages.put(f"\n[Master Export] Saved: {result}\n")
                self.messages.put("\n__DONE__")
            else:
                if self._operation_canceled() or (hasattr(self, "cancel_event") and self.cancel_event.is_set()):
                    if output_path and output_path.exists():
                        output_path.unlink(missing_ok=True)
                    self.messages.put("\n[Master Export] " + ("تم إلغاء التصدير بنجاح." if is_ar else "Export canceled by user.") + "\n")
                    self.messages.put("\n__CANCELED__")
                else:
                    self.messages.put("\n__FAILED__")
        except convert.CancelledError:
            if output_path and output_path.exists():
                output_path.unlink(missing_ok=True)
            self.messages.put("\n[Master Export] " + ("تم إلغاء التصدير بنجاح." if is_ar else "Export canceled by user.") + "\n")
            self.messages.put("\n__CANCELED__")
        except Exception as exc:
            is_canceled = (
                self._operation_canceled()
                or (hasattr(self, "cancel_event") and self.cancel_event.is_set())
                or "cancel" in type(exc).__name__.lower()
                or "cancel" in str(exc).lower()
                or "stopped" in str(exc).lower()
            )
            if is_canceled:
                if output_path and output_path.exists():
                    output_path.unlink(missing_ok=True)
                self.messages.put("\n[Master Export] " + ("تم إلغاء التصدير بنجاح." if is_ar else "Export canceled by user.") + "\n")
                self.messages.put("\n__CANCELED__")
            else:
                self.messages.put(f"\n[Master Export] Error: {exc}\n")
                self.messages.put("\n__FAILED__")
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
