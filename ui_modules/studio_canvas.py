"""
Studio Canvas Controller Mixin
Handles interactive player canvas rendering, pan/zoom transformations,
overlay manipulation (gizmo, handles, dragging), HUD drawing, and fullscreen/theater mode.
"""

import math
import sys
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

from video_studio.aspect_ratios import (
    ASPECT_RATIOS,
    clamp_pan_for_transform,
    render_transformed_pil_frame,
)
from video_studio.color_grading import apply_color_to_image, is_color_neutral, extract_video_sample_frame
from video_studio.branding import (
    render_text_card_pil,
    apply_opacity_and_rotation,
)
from video_studio.arabic_support import prepare_arabic_for_rendering
from video_studio.icons_library import ICON_PRESETS, render_media_overlay_pil
from ui_dialogs.icon_picker_dialog import IconPickerDialog
import convert


def evaluate_item_animation(item: dict, current_tl_sec: float, ref_box_w: int = 1080, ref_box_h: int = 1920) -> tuple:
    """
    Evaluates in/out animation for an overlay item at a given timeline time.
    Returns (opacity_mult, offset_x_px, offset_y_px, scale_mult).
    """
    anim_in = str(item.get("anim_in", "none") or "none").lower()
    anim_out = str(item.get("anim_out", "none") or "none").lower()
    anim_dur = max(0.1, min(3.0, float(item.get("anim_dur", 0.4) or 0.4)))

    if item.get("full_duration", False):
        return (1.0, 0, 0, 1.0)

    s = float(item.get("start_sec", 0.0) or 0.0)
    e = float(item.get("end_sec", s + 5.0) or (s + 5.0))
    t = float(current_tl_sec)

    opacity = 1.0
    off_x = 0
    off_y = 0
    scale = 1.0

    # In-animation
    if anim_in != "none" and s <= t < s + anim_dur:
        p = max(0.0, min(1.0, (t - s) / anim_dur))
        ease = p * p * (3.0 - 2.0 * p)
        if anim_in == "fade":
            opacity *= ease
        elif anim_in in ("slide_up", "slide_bottom"):
            off_y += int((1.0 - ease) * (ref_box_h * 0.15))
            opacity *= ease
        elif anim_in in ("slide_down", "slide_top"):
            off_y -= int((1.0 - ease) * (ref_box_h * 0.15))
            opacity *= ease
        elif anim_in in ("slide_left",):
            off_x += int((1.0 - ease) * (ref_box_w * 0.20))
            opacity *= ease
        elif anim_in in ("slide_right",):
            off_x -= int((1.0 - ease) * (ref_box_w * 0.20))
            opacity *= ease
        elif anim_in in ("pop", "zoom"):
            scale *= (0.2 + 0.8 * ease)
            opacity *= ease

    # Out-animation
    if anim_out != "none" and e - anim_dur < t <= e:
        p = max(0.0, min(1.0, (e - t) / anim_dur))
        ease = p * p * (3.0 - 2.0 * p)
        if anim_out == "fade":
            opacity *= ease
        elif anim_out in ("slide_down", "slide_bottom"):
            off_y += int((1.0 - ease) * (ref_box_h * 0.15))
            opacity *= ease
        elif anim_out in ("slide_up", "slide_top"):
            off_y -= int((1.0 - ease) * (ref_box_h * 0.15))
            opacity *= ease
        elif anim_out in ("shrink", "zoom"):
            scale *= (0.2 + 0.8 * ease)
            opacity *= ease

    return (opacity, off_x, off_y, scale)


class StudioCanvasMixin:
    """Provides interactive Studio Canvas and Video Transform methods for MediaAudioStudioApp."""

    # -------------------------------------------------------------------------
    # Surface & Fullscreen Management
    # -------------------------------------------------------------------------
    def _show_vlc_surface(self):
        if hasattr(self, "player_studio_canvas"):
            self.player_studio_canvas.grid_remove()
        if hasattr(self, "video_surface"):
            self.video_surface.grid(row=1, column=0, sticky="nsew")
            self.video_surface.tk.call("raise", self.video_surface._w)
        if hasattr(self, "studio_toggle_btn"):
            is_ar = self.language_var.get() == "العربية"
            self.studio_toggle_btn.configure(text="🎨 استوديو المونتاج" if is_ar else "🎨 Studio Preview")
        if getattr(self, "media_player", None) and hasattr(self, "_attach_video_surface"):
            self._attach_video_surface()
            self.apply_video_aspect_ratio()
            self.apply_video_color_adjustments()

    def _show_studio_canvas(self):
        self.studio_live_preview_mode = True
        if hasattr(self, "video_surface"):
            self.video_surface.grid_remove()
        if hasattr(self, "player_studio_canvas"):
            self.player_studio_canvas.grid(row=1, column=0, sticky="nsew")
            self.player_studio_canvas.tk.call("raise", self.player_studio_canvas._w)
            self._render_player_studio_canvas()
        if hasattr(self, "studio_toggle_btn"):
            is_ar = self.language_var.get() == "العربية"
            if getattr(self, "studio_live_preview_mode", False):
                self.studio_toggle_btn.configure(text="📺 المعاينة المباشرة" if is_ar else "📺 Direct Preview")
            else:
                self.studio_toggle_btn.configure(text="🎨 استوديو المونتاج" if is_ar else "🎨 Studio Preview")

    def toggle_studio_view(self):
        if getattr(self, "studio_live_preview_mode", False) and hasattr(self, "player_studio_canvas") and self.player_studio_canvas.winfo_ismapped():
            self.studio_live_preview_mode = False
            self._show_vlc_surface()
        else:
            self.studio_live_preview_mode = True
            self._show_studio_canvas()
            tl_sec = self._current_timeline_seconds()
            _idx, _c, src_sec = self.nle_project.timeline_to_source(tl_sec) if hasattr(self, "nle_project") else (0, None, tl_sec)
            self._request_fast_preview_frame(src_sec, force=True)

    def toggle_video_size(self):
        th_dlg = getattr(self, "_theater_dialog", None)
        if getattr(self, "video_expanded", False) or (th_dlg is not None and th_dlg.winfo_exists()):
            self._exit_video_fullscreen()
        else:
            self._enter_video_fullscreen()

    def _enter_video_fullscreen(self):
        th_dlg = getattr(self, "_theater_dialog", None)
        if th_dlg is not None and th_dlg.winfo_exists():
            th_dlg.lift()
            th_dlg.focus_set()
            return

        from ui_dialogs.video_theater_dialog import VideoTheaterDialog
        self._theater_dialog = VideoTheaterDialog(self)
        self.video_expanded = True
        is_ar = (self.language_var.get() == "العربية") if hasattr(self, "language_var") else True
        if hasattr(self, "expand_video_button"):
            self.expand_video_button.configure(text="✕ تصغير" if is_ar else "✕ Exit Full")

    def _exit_video_fullscreen(self):
        th_dlg = getattr(self, "_theater_dialog", None)
        if th_dlg is not None and th_dlg.winfo_exists():
            try:
                th_dlg.close()
                return
            except Exception:
                pass
        self._theater_dialog = None
        self.video_expanded = False
        is_ar = (self.language_var.get() == "العربية") if hasattr(self, "language_var") else True
        if hasattr(self, "expand_video_button"):
            self.expand_video_button.configure(text="⛶ تكبير" if is_ar else "⛶ Fullscreen")
        if getattr(self, "studio_live_preview_mode", False):
            self._show_studio_canvas()
        else:
            self._show_vlc_surface()
            self._attach_video_surface()
            self.apply_video_aspect_ratio()
            self.apply_video_color_adjustments()
        self.after(50, self._sync_live_video_overlay)

    # -------------------------------------------------------------------------
    # Frame Extraction & Off-Thread Composition
    # -------------------------------------------------------------------------
    def _present_studio_frame_fast(self):
        self._studio_paint_pending = False
        try:
            self._render_player_studio_canvas()
            th_dlg = getattr(self, "_theater_dialog", None)
            if th_dlg is not None and th_dlg.winfo_exists():
                th_dlg.refresh_preview()
        except Exception:
            pass

    def _request_fast_preview_frame(self, src_timestamp_sec: float, force: bool = False):
        if not self.input_path or not self.input_path.is_file():
            self._cached_player_frame = None
            self._ready_composed_video = None
            self._render_player_studio_canvas()
            return
        if self.input_path.suffix.lower() not in convert.VIDEO_EXTS:
            self._cached_player_frame = None
            self._ready_composed_video = None
            self._render_player_studio_canvas()
            return

        ts = max(0.0, float(src_timestamp_sec or 0.0))
        if (
            not force
            and self._cached_player_frame_path == self.input_path
            and abs(self._cached_player_frame_ts - ts) < 0.022
            and self._cached_player_frame is not None
        ):
            self._render_player_studio_canvas()
            return

        self._pending_preview_ts = (ts, force)
        if getattr(self, "_preview_decode_busy", False):
            return
        self._preview_decode_busy = True

        def _decode_loop():
            try:
                while True:
                    req = getattr(self, "_pending_preview_ts", None)
                    if req is None:
                        break
                    self._pending_preview_ts = None
                    req_ts, _req_force = req
                    vpath = self.input_path
                    if not vpath or not vpath.is_file():
                        break
                    frame = self.fast_preview.get_frame(vpath, req_ts, max_dim=1280)
                    if frame is not None and vpath == self.input_path:
                        self._cached_player_frame = frame
                        self._cached_player_frame_ts = req_ts
                        self._cached_player_frame_path = vpath

                        try:
                            vx0, vy0, vx1, vy1 = getattr(self, "_player_canvas_video_box", (0, 0, 0, 0))
                            bw = max(24, int(vx1 - vx0))
                            bh = max(24, int(vy1 - vy0))
                            if bw >= 40 and bh >= 40:
                                fit_m = self.video_branding_config.get("fit_mode", "crop")
                                c_idx = getattr(self, "active_playback_clip_idx", 0)
                                xf = self._get_effective_video_transform(c_idx)
                                color_cfg = self.video_branding_config.get("color_config", {})
                                color_on = bool(
                                    isinstance(color_cfg, dict)
                                    and color_cfg.get("enabled", True)
                                    and not is_color_neutral(color_cfg)
                                )
                                work_im = apply_color_to_image(frame, color_cfg) if color_on else frame
                                comp_im = render_transformed_pil_frame(
                                    work_im,
                                    bw,
                                    bh,
                                    fit_mode=fit_m,
                                    zoom=xf["zoom"],
                                    pan_x=xf["pan_x"],
                                    pan_y=xf["pan_y"],
                                    flip_h=xf["flip_h"],
                                    clamp_edges=xf["clamp_edges"],
                                )
                                comp_key = (
                                    id(frame), bw, bh, fit_m,
                                    round(xf["zoom"], 3), round(xf["pan_x"], 4), round(xf["pan_y"], 4),
                                    bool(xf["flip_h"]), bool(xf["clamp_edges"]),
                                    color_on,
                                    round(float(color_cfg.get("brightness", 0.0)), 3) if color_on else 0.0,
                                    round(float(color_cfg.get("contrast", 1.0)), 3) if color_on else 1.0,
                                    round(float(color_cfg.get("saturation", 1.0)), 3) if color_on else 1.0,
                                    round(float(color_cfg.get("temperature", 0.0)), 3) if color_on else 0.0,
                                    round(float(color_cfg.get("gamma", 1.0)), 3) if color_on else 1.0,
                                    round(float(color_cfg.get("red", 1.0)), 3) if color_on else 1.0,
                                    round(float(color_cfg.get("green", 1.0)), 3) if color_on else 1.0,
                                    round(float(color_cfg.get("blue", 1.0)), 3) if color_on else 1.0,
                                )
                                self._ready_composed_video = (comp_key, comp_im)
                        except Exception:
                            pass

                        if not getattr(self, "_studio_paint_pending", False):
                            self._studio_paint_pending = True
                            self.after(0, self._present_studio_frame_fast)
            except Exception:
                pass
            finally:
                self._preview_decode_busy = False

        threading.Thread(target=_decode_loop, daemon=True).start()

    def _async_extract_studio_frame(self, timestamp=None, force=False):
        if timestamp is None:
            tl_sec = self._current_timeline_seconds()
            _idx, _c, ts = self.nle_project.timeline_to_source(tl_sec) if hasattr(self, "nle_project") else (0, None, tl_sec)
        else:
            ts = float(timestamp)
        self._request_fast_preview_frame(ts, force=force)

    # -------------------------------------------------------------------------
    # Video Transform Engine (Pan X / Pan Y / Zoom / Flip)
    # -------------------------------------------------------------------------
    def _get_selected_or_active_clip_idx(self) -> int:
        if not hasattr(self, "nle_project") or not self.nle_project.clips:
            return 0
        sel = getattr(self, "player_canvas_selected", None)
        if isinstance(sel, tuple) and sel[0] == "clip" and 0 <= sel[1] < len(self.nle_project.clips):
            return sel[1]
        c_idx, _c, _src = self.nle_project.timeline_to_source(getattr(self, "nle_playhead_sec", 0.0))
        return max(0, min(len(self.nle_project.clips) - 1, c_idx))

    def _get_effective_video_transform(self, clip_idx=None) -> dict:
        if clip_idx is None:
            clip_idx = self._get_selected_or_active_clip_idx()
        clip = None
        if hasattr(self, "nle_project") and 0 <= clip_idx < len(self.nle_project.clips):
            clip = self.nle_project.clips[clip_idx]
        clamp_edges = bool(self.video_branding_config.get("video_clamp_edges", True))
        if clip and clip.get("custom_transform", False):
            return {
                "zoom": float(clip.get("zoom", 1.0)),
                "pan_x": float(clip.get("pan_x", 0.0)),
                "pan_y": float(clip.get("pan_y", 0.0)),
                "flip_h": bool(clip.get("flip_h", False)),
                "clamp_edges": clamp_edges,
            }
        return {
            "zoom": float(self.video_branding_config.get("video_zoom", 1.0)),
            "pan_x": float(self.video_branding_config.get("video_pan_x", 0.0)),
            "pan_y": float(self.video_branding_config.get("video_pan_y", 0.0)),
            "flip_h": bool(self.video_branding_config.get("video_flip_h", False)),
            "clamp_edges": clamp_edges,
        }

    def _get_source_and_canvas_dims_for_clamp(self):
        if self._cached_player_frame is not None:
            in_w, in_h = self._cached_player_frame.size
        elif getattr(self, "media_width", 0) and getattr(self, "media_height", 0):
            in_w, in_h = int(self.media_width), int(self.media_height)
        else:
            in_w, in_h = 1920, 1080
        ratio_key = self.trim_aspect_var.get() if hasattr(self, "trim_aspect_var") else "original"
        preset = ASPECT_RATIOS.get(ratio_key)
        if preset and preset.get("w") and preset.get("h"):
            cw, ch = preset["w"], preset["h"]
        else:
            cw, ch = in_w, in_h
        return in_w, in_h, cw, ch

    def _set_effective_video_transform(self, zoom=None, pan_x=None, pan_y=None, flip_h=None, clamp_edges=None):
        c_idx = self._get_selected_or_active_clip_idx()
        clip = self.nle_project.clips[c_idx] if (hasattr(self, "nle_project") and 0 <= c_idx < len(self.nle_project.clips)) else None
        cur = self._get_effective_video_transform(c_idx)

        new_z = max(0.25, min(4.0, float(zoom if zoom is not None else cur["zoom"])))
        raw_px = float(pan_x if pan_x is not None else cur["pan_x"])
        raw_py = float(pan_y if pan_y is not None else cur["pan_y"])
        new_flip = bool(flip_h if flip_h is not None else cur["flip_h"])
        new_clamp = bool(clamp_edges if clamp_edges is not None else cur["clamp_edges"])
        self.video_branding_config["video_clamp_edges"] = new_clamp

        in_w, in_h, cw, ch = self._get_source_and_canvas_dims_for_clamp()
        fit_mode = self.video_branding_config.get("fit_mode", "crop")
        clamped_px, clamped_py = clamp_pan_for_transform(
            in_w, in_h, cw, ch, fit_mode, new_z, raw_px, raw_py, clamp_edges=new_clamp
        )

        if clip and clip.get("custom_transform", False):
            clip["zoom"] = round(new_z, 3)
            clip["pan_x"] = round(clamped_px, 4)
            clip["pan_y"] = round(clamped_py, 4)
            clip["flip_h"] = new_flip
        else:
            self.video_branding_config["video_zoom"] = round(new_z, 3)
            self.video_branding_config["video_pan_x"] = round(clamped_px, 4)
            self.video_branding_config["video_pan_y"] = round(clamped_py, 4)
            self.video_branding_config["video_flip_h"] = new_flip

    def _sync_transform_sliders_from_state(self):
        if not hasattr(self, "vid_zoom_var"):
            return
        self._updating_xf_ui = True
        try:
            c_idx = self._get_selected_or_active_clip_idx()
            clip = self.nle_project.clips[c_idx] if (hasattr(self, "nle_project") and 0 <= c_idx < len(self.nle_project.clips)) else None
            is_custom = bool(clip and clip.get("custom_transform", False))
            self.clip_override_var.set(is_custom)

            xf = self._get_effective_video_transform(c_idx)
            z = float(xf["zoom"])
            px = float(xf["pan_x"])
            py = float(xf["pan_y"])
            self.vid_zoom_var.set(z)
            self.vid_panx_var.set(px)
            self.vid_pany_var.set(py)
            self.vid_flip_var.set(bool(xf["flip_h"]))
            self.vid_clamp_var.set(bool(xf["clamp_edges"]))

            z_pct = int(round(z * 100))
            px_pct = int(round(px * 100))
            py_pct = int(round(py * 100))
            if hasattr(self, "vid_zoom_spin_var"):
                self.vid_zoom_spin_var.set(f"{z_pct}")
            if hasattr(self, "vid_panx_spin_var"):
                self.vid_panx_spin_var.set(f"{px_pct}")
            if hasattr(self, "vid_pany_spin_var"):
                self.vid_pany_spin_var.set(f"{py_pct}")

            if hasattr(self, "vid_zoom_val_lbl"):
                self.vid_zoom_val_lbl.configure(text=f"{z:.2f}x")
            if hasattr(self, "vid_panx_val_lbl"):
                self.vid_panx_val_lbl.configure(text=f"{px_pct:+d}%" if px_pct != 0 else "0%")
            if hasattr(self, "vid_pany_val_lbl"):
                self.vid_pany_val_lbl.configure(text=f"{py_pct:+d}%" if py_pct != 0 else "0%")

            if clip is not None:
                spd = float(clip.get("speed", 1.0))
                vol_pct = int(round(float(clip.get("volume", 1.0)) * 100))
                muted = bool(clip.get("muted", False))
                if hasattr(self, "clip_tl_pos_var"):
                    self.clip_tl_pos_var.set(f"{float(clip.get('tl_start', 0.0)):.2f}")
                if hasattr(self, "clip_in_var"):
                    self.clip_in_var.set(f"{float(clip.get('src_start', 0.0)):.2f}")
                if hasattr(self, "clip_out_var"):
                    self.clip_out_var.set(f"{float(clip.get('src_end', 0.0)):.2f}")
                if hasattr(self, "clip_speed_combo_var"):
                    self.clip_speed_combo_var.set(f"{spd:.2f}")
                if hasattr(self, "clip_vol_var"):
                    self.clip_vol_var.set(float(vol_pct))
                if hasattr(self, "clip_vol_spin_var"):
                    self.clip_vol_spin_var.set(f"{vol_pct}")
                if hasattr(self, "clip_mute_var"):
                    self.clip_mute_var.set(muted)
                if hasattr(self, "clip_vol_lbl"):
                    self.clip_vol_lbl.configure(text="MUTE" if muted else f"{vol_pct}%")
                if hasattr(self, "clip_fade_in_var"):
                    self.clip_fade_in_var.set(f"{float(clip.get('audio_fade_in', 0.0) or 0.0):.2f}")
                if hasattr(self, "clip_fade_out_var"):
                    self.clip_fade_out_var.set(f"{float(clip.get('audio_fade_out', 0.0) or 0.0):.2f}")
                if hasattr(self, "clip_denoise_var"):
                    self.clip_denoise_var.set(bool(clip.get("audio_denoise", False)))
        finally:
            self._updating_xf_ui = False

    def _quick_set_aspect_ratio(self, ratio_key: str):
        if ratio_key not in ASPECT_RATIOS:
            ratio_key = "original"
        prev_ratio = self.video_branding_config.get("aspect_ratio", "original")
        if ratio_key != prev_ratio:
            self.push_app_undo(f"تغيير أبعاد الفيديو إلى {ratio_key}", f"Change Aspect Ratio to {ratio_key}")
        self.trim_aspect_var.set(ratio_key)
        self.video_branding_config["aspect_ratio"] = ratio_key
        if hasattr(self, "export_opt_framing_var"):
            self.export_opt_framing_var.set(True)
        if hasattr(self, "trim_aspect_combo_var") and hasattr(self, "trim_aspect_rev"):
            disp = self.trim_aspect_rev.get(ratio_key)
            if disp:
                self.trim_aspect_combo_var.set(disp)

        if ratio_key in ("9:16", "4:5", "1:1") and self.video_branding_config.get("fit_mode") == "pad":
            self.video_branding_config["fit_mode"] = "crop"
            if hasattr(self, "fit_mode_combo_var") and hasattr(self, "fit_mode_rev"):
                f_disp = self.fit_mode_rev.get("crop")
                if f_disp:
                    self.fit_mode_combo_var.set(f_disp)

        self._ready_composed_video = None
        self._set_effective_video_transform()
        self._sync_transform_sliders_from_state()
        self._save_settings()
        self._refresh_master_export_summary()
        self._show_studio_canvas()

    def _toggle_safe_grid(self):
        cur = bool(self.video_branding_config.get("show_safe_grid", False))
        self.video_branding_config["show_safe_grid"] = not cur
        self._save_settings()
        self._render_player_studio_canvas()

    def _reset_video_transform(self):
        c_idx = self._get_selected_or_active_clip_idx()
        clip = self.nle_project.clips[c_idx] if (hasattr(self, "nle_project") and 0 <= c_idx < len(self.nle_project.clips)) else None
        if clip and clip.get("custom_transform"):
            self.push_app_undo("إعادة تعيين أبعاد وموضع الفيديو", "Reset Video Transform")
            self.nle_project.push_undo()
        self._ready_composed_video = None
        self._set_effective_video_transform(zoom=1.0, pan_x=0.0, pan_y=0.0, flip_h=False)
        self._sync_transform_sliders_from_state()
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.redraw()
        self._save_settings()
        self._refresh_master_export_summary()
        self._render_player_studio_canvas()

    def _on_fit_mode_combo_changed(self, _e=None):
        disp = self.fit_mode_combo_var.get()
        fkey = self.fit_mode_map.get(disp, "crop")
        if fkey != self.video_branding_config.get("fit_mode"):
            self.push_app_undo(f"تغيير نمط الإطار إلى {disp}", f"Change Fit Mode to {disp}")
        self.video_branding_config["fit_mode"] = fkey
        if hasattr(self, "export_opt_framing_var"):
            self.export_opt_framing_var.set(True)
        self._ready_composed_video = None
        self._set_effective_video_transform()
        self._sync_transform_sliders_from_state()
        self._save_settings()
        self._refresh_master_export_summary()
        self._render_player_studio_canvas()

    def _on_clip_override_toggled(self):
        if getattr(self, "_updating_xf_ui", False):
            return
        c_idx = self._get_selected_or_active_clip_idx()
        if not hasattr(self, "nle_project") or not (0 <= c_idx < len(self.nle_project.clips)):
            return
        self.nle_project.push_undo()
        clip = self.nle_project.clips[c_idx]
        en = bool(self.clip_override_var.get())
        clip["custom_transform"] = en
        if en:
            clip["zoom"] = float(self.video_branding_config.get("video_zoom", 1.0))
            clip["pan_x"] = float(self.video_branding_config.get("video_pan_x", 0.0))
            clip["pan_y"] = float(self.video_branding_config.get("video_pan_y", 0.0))
            clip["flip_h"] = bool(self.video_branding_config.get("video_flip_h", False))
        self._ready_composed_video = None
        self._sync_transform_sliders_from_state()
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.redraw()
        self._refresh_master_export_summary()
        self._render_player_studio_canvas()

    def _on_vid_transform_slider(self, _val=None):
        if getattr(self, "_updating_xf_ui", False):
            return
        z = float(self.vid_zoom_var.get())
        px = float(self.vid_panx_var.get())
        py = float(self.vid_pany_var.get())
        self._ready_composed_video = None
        self._set_effective_video_transform(zoom=z, pan_x=px, pan_y=py)
        xf = self._get_effective_video_transform()
        self._updating_xf_ui = True
        try:
            if hasattr(self, "vid_zoom_spin_var"):
                self.vid_zoom_spin_var.set(f"{int(round(xf['zoom'] * 100))}")
            if hasattr(self, "vid_panx_spin_var"):
                self.vid_panx_spin_var.set(f"{int(round(xf['pan_x'] * 100))}")
            if hasattr(self, "vid_pany_spin_var"):
                self.vid_pany_spin_var.set(f"{int(round(xf['pan_y'] * 100))}")
        finally:
            self._updating_xf_ui = False
        if hasattr(self, "export_opt_framing_var"):
            self.export_opt_framing_var.set(True)
        self._show_studio_canvas()
        self._render_player_studio_canvas()

    def _on_vid_transform_spin(self, _e=None):
        if getattr(self, "_updating_xf_ui", False):
            return
        try:
            z = max(0.25, min(4.00, float(self.vid_zoom_spin_var.get().replace("%", "").strip()) / 100.0))
            px = max(-1.00, min(1.00, float(self.vid_panx_spin_var.get().replace("%", "").strip()) / 100.0))
            py = max(-1.00, min(1.00, float(self.vid_pany_spin_var.get().replace("%", "").strip()) / 100.0))
        except ValueError:
            self._sync_transform_sliders_from_state()
            return
        if hasattr(self, "export_opt_framing_var"):
            self.export_opt_framing_var.set(True)
        self._ready_composed_video = None
        self._set_effective_video_transform(zoom=z, pan_x=px, pan_y=py)
        self._sync_transform_sliders_from_state()
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.redraw()
        self._save_settings()
        self._refresh_master_export_summary()
        self._show_studio_canvas()
        self._render_player_studio_canvas()

    def _nudge_transform(self, zoom=None, pan_x=None, pan_y=None):
        self._ready_composed_video = None
        self._set_effective_video_transform(zoom=zoom, pan_x=pan_x, pan_y=pan_y)
        self._sync_transform_sliders_from_state()
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.redraw()
        self._save_settings()
        self._refresh_master_export_summary()
        self._render_player_studio_canvas()

    def _on_flip_toggled(self):
        if getattr(self, "_updating_xf_ui", False):
            return
        self._ready_composed_video = None
        self._set_effective_video_transform(
            flip_h=bool(self.vid_flip_var.get()),
            clamp_edges=bool(self.vid_clamp_var.get()),
        )
        self._sync_transform_sliders_from_state()
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.redraw()
        self._save_settings()
        self._refresh_master_export_summary()
        self._render_player_studio_canvas()

    # -------------------------------------------------------------------------
    # Canvas Paint Engine
    # -------------------------------------------------------------------------
    def _retry_render_studio_canvas(self):
        self._studio_retry_pending = False
        self._render_player_studio_canvas()

    def _render_player_studio_canvas(self):
        if not hasattr(self, "player_studio_canvas"):
            return

        cw = self.player_studio_canvas.winfo_width()
        ch = self.player_studio_canvas.winfo_height()
        if cw < 40 or ch < 40:
            if not getattr(self, "_studio_retry_pending", False):
                self._studio_retry_pending = True
                self.after(50, self._retry_render_studio_canvas)
            return

        is_ar = self.language_var.get() == "العربية"
        self.player_studio_canvas.delete("all")
        self.player_canvas_element_boxes.clear()
        self._overlay_photo_refs.clear()

        # 1. Cinema Dark Surrounding Stage
        self.player_studio_canvas.create_rectangle(0, 0, cw, ch, fill="#07090d", outline="")

        # 2. Target Aspect Ratio & Active Box Calculations
        ratio_key = self.trim_aspect_var.get() if hasattr(self, "trim_aspect_var") else "original"
        has_frame = self._cached_player_frame is not None
        if has_frame:
            orig_w, orig_h = self._cached_player_frame.size
            src_aspect = orig_w / max(1, orig_h)
        elif getattr(self, "media_width", 0) and getattr(self, "media_height", 0):
            src_aspect = float(self.media_width) / max(1.0, float(self.media_height))
        else:
            src_aspect = 16.0 / 9.0

        aspect_Lookup = {
            "9:16": 9.0 / 16.0,
            "1:1": 1.0,
            "4:5": 4.0 / 5.0,
            "4:3": 4.0 / 3.0,
            "16:9": 16.0 / 9.0,
        }
        target_aspect = aspect_Lookup.get(ratio_key, src_aspect)

        pad_y = 14
        pad_x = 14
        avail_h = max(40, ch - (pad_y * 2) - 10)
        avail_w = max(40, cw - (pad_x * 2))
        box_h = avail_h
        box_w = max(24, int(round(box_h * target_aspect)))
        if box_w > avail_w:
            box_w = avail_w
            box_h = max(24, int(round(box_w / target_aspect)))

        vx0 = (cw - box_w) // 2
        vy0 = (ch - 12 - box_h) // 2
        vx1 = vx0 + box_w
        vy1 = vy0 + box_h
        self._player_canvas_video_box = (vx0, vy0, vx1, vy1)

        # 3. Outer Matte Surround
        if vx0 > 0:
            self.player_studio_canvas.create_rectangle(0, 0, vx0, ch, fill="#05070b", outline="")
        if vx1 < cw:
            self.player_studio_canvas.create_rectangle(vx1, 0, cw, ch, fill="#05070b", outline="")
        if vy0 > 0:
            self.player_studio_canvas.create_rectangle(vx0, 0, vx1, vy0, fill="#05070b", outline="")
        if vy1 < ch:
            self.player_studio_canvas.create_rectangle(vx0, vy1, vx1, ch, fill="#05070b", outline="")

        # 4. Render Video Frame with Pan / Zoom / Fit / Color Grading (Track V1)
        fit_mode = self.video_branding_config.get("fit_mode", "crop")
        tl_now = float(getattr(self, "nle_playhead_sec", 0.0))
        c_idx, cur_clip, _src_now = self.nle_project.timeline_to_source(tl_now) if hasattr(self, "nle_project") else (0, None, tl_now)
        xf = self._get_effective_video_transform(c_idx)
        v1_enabled = self.nle_project.track_enabled.get("V1", True) if hasattr(self, "nle_project") else True
        in_gap = bool(hasattr(self, "nle_project") and self.nle_project.clips and cur_clip is None)

        if in_gap:
            self.player_studio_canvas.create_rectangle(vx0, vy0, vx1, vy1, fill="#000000", outline="")
            gap_badge = "↔ فجوة صامتة" if is_ar else "↔ Timeline Gap"
            self.player_studio_canvas.create_text(
                (vx0 + vx1) // 2, (vy0 + vy1) // 2,
                text=gap_badge, fill="#388bfd", font=("Segoe UI", max(9, min(14, box_w // 24)), "bold")
            )
        elif has_frame and v1_enabled:
            try:
                final_im = None
                color_cfg = self.video_branding_config.get("color_config", {})
                color_on = isinstance(color_cfg, dict) and color_cfg.get("enabled", True) and not is_color_neutral(color_cfg)
                cur_comp_key = (
                    id(self._cached_player_frame), box_w, box_h, fit_mode,
                    round(xf["zoom"], 3), round(xf["pan_x"], 4), round(xf["pan_y"], 4),
                    bool(xf["flip_h"]), bool(xf["clamp_edges"]),
                    color_on,
                    round(float(color_cfg.get("brightness", 0.0)), 3) if color_on else 0.0,
                    round(float(color_cfg.get("contrast", 1.0)), 3) if color_on else 1.0,
                    round(float(color_cfg.get("saturation", 1.0)), 3) if color_on else 1.0,
                    round(float(color_cfg.get("temperature", 0.0)), 3) if color_on else 0.0,
                    round(float(color_cfg.get("gamma", 1.0)), 3) if color_on else 1.0,
                    round(float(color_cfg.get("red", 1.0)), 3) if color_on else 1.0,
                    round(float(color_cfg.get("green", 1.0)), 3) if color_on else 1.0,
                    round(float(color_cfg.get("blue", 1.0)), 3) if color_on else 1.0,
                )
                comp_item = getattr(self, "_ready_composed_video", None)
                if comp_item is not None:
                    c_key, c_im = comp_item
                    if c_key == cur_comp_key:
                        final_im = c_im

                if final_im is None:
                    frame_to_draw = self._cached_player_frame
                    if color_on:
                        frame_to_draw = apply_color_to_image(frame_to_draw, color_cfg)

                    final_im = render_transformed_pil_frame(
                        frame_to_draw,
                        box_w,
                        box_h,
                        fit_mode=fit_mode,
                        zoom=xf["zoom"],
                        pan_x=xf["pan_x"],
                        pan_y=xf["pan_y"],
                        flip_h=xf["flip_h"],
                        clamp_edges=xf["clamp_edges"],
                    )
                self._player_photo_image = ImageTk.PhotoImage(final_im)
                self.player_studio_canvas.create_image(vx0, vy0, anchor="nw", image=self._player_photo_image)
            except Exception:
                self.player_studio_canvas.create_rectangle(vx0, vy0, vx1, vy1, fill="#141922", outline="")
        elif has_frame and not v1_enabled:
            self.player_studio_canvas.create_rectangle(vx0, vy0, vx1, vy1, fill="#000000", outline="")
        else:
            self.player_studio_canvas.create_rectangle(vx0, vy0, vx1, vy1, fill="#121721", outline="")
            if getattr(self, "input_path", None) and self.input_path.is_file() and self.input_path.suffix.lower() in convert.VIDEO_EXTS:
                msg = "⏳ جاري تجهيز معاينة الفيديو..." if is_ar else "⏳ Loading video preview..."
                if not getattr(self, "_preview_decode_busy", False) and self._cached_player_frame is None:
                    self.after(20, lambda: self._request_fast_preview_frame(0.0, force=True))
            else:
                msg = "🎬 اختر فيديو للبدء في المونتاج الاحترافي" if is_ar else "🎬 Load a video to start DaVinci editing"
            self.player_studio_canvas.create_text(
                (vx0 + vx1) // 2, (vy0 + vy1) // 2,
                text=msg, fill="#8b949e", font=("Segoe UI", max(9, min(12, box_w // 26)), "bold")
            )

        # 5. Rule-of-Thirds Safe Grid + Drag Snap Guides
        if self.video_branding_config.get("show_safe_grid", False):
            for frac in (1.0 / 3.0, 2.0 / 3.0):
                gx = vx0 + int(box_w * frac)
                gy = vy0 + int(box_h * frac)
                self.player_studio_canvas.create_line(gx, vy0, gx, vy1, fill="#484f58", dash=(3, 3))
                self.player_studio_canvas.create_line(vx0, gy, vx1, gy, fill="#484f58", dash=(3, 3))
            self.player_studio_canvas.create_line((vx0 + vx1) // 2 - 10, (vy0 + vy1) // 2, (vx0 + vx1) // 2 + 10, (vy0 + vy1) // 2, fill="#58a6ff")
            self.player_studio_canvas.create_line((vx0 + vx1) // 2, (vy0 + vy1) // 2 - 10, (vx0 + vx1) // 2, (vy0 + vy1) // 2 + 10, fill="#58a6ff")

        if getattr(self, "_snap_guide_x", False):
            self.player_studio_canvas.create_line((vx0 + vx1) // 2, vy0, (vx0 + vx1) // 2, vy1, fill="#00e5ff", width=1, dash=(4, 2))
        if getattr(self, "_snap_guide_y", False):
            self.player_studio_canvas.create_line(vx0, (vy0 + vy1) // 2, vx1, (vy0 + vy1) // 2, fill="#00e5ff", width=1, dash=(4, 2))

        # 6. Track V2: Icons, Social Badges & Custom Images
        if hasattr(self, "nle_project") and self.nle_project.track_enabled.get("V2", True):
            for idx, m_item in enumerate(self.nle_project.media_items):
                if not self.nle_project.is_item_visible_at("V2", m_item, tl_now):
                    continue
                v2_ck = (
                    "V2", idx, m_item.get("type"), m_item.get("icon_key"), m_item.get("text"),
                    str(m_item.get("path")), box_w, box_h,
                    round(float(m_item.get("scale", 0.2)), 3),
                    round(float(m_item.get("opacity", 1.0)), 2),
                    round(float(m_item.get("rotation", 0.0)), 1),
                )
                ov_im = self._overlay_pil_cache.get(v2_ck)
                if ov_im is None:
                    ov_im = render_media_overlay_pil(m_item, box_w, box_h, is_ar=is_ar)
                    if ov_im is not None:
                        if len(self._overlay_pil_cache) > 64:
                            self._overlay_pil_cache.clear()
                        self._overlay_pil_cache[v2_ck] = ov_im
                if ov_im is None:
                    continue
                photo = ImageTk.PhotoImage(ov_im)
                self._overlay_photo_refs.append(photo)
                _op_m, off_x, off_y, _sc_m = evaluate_item_animation(m_item, tl_now, box_w, box_h)
                cx = vx0 + int(round(box_w * float(m_item.get("x", 0.5)))) + off_x
                cy = vy0 + int(round(box_h * float(m_item.get("y", 0.5)))) + off_y
                iw, ih = ov_im.size
                ix0, iy0 = cx - iw // 2, cy - ih // 2
                ix1, iy1 = ix0 + iw, iy0 + ih
                self.player_studio_canvas.create_image(ix0, iy0, anchor="nw", image=photo)
                self.player_canvas_element_boxes[("V2", idx)] = {
                    "rect": (ix0, iy0, ix1, iy1),
                    "center": (cx, cy),
                    "handles": {
                        "tl": (ix0, iy0),
                        "tr": (ix1, iy0),
                        "bl": (ix0, iy1),
                        "br": (ix1, iy1),
                        "rot": ((ix0 + ix1) // 2, max(vy0 + 4, iy0 - 18)),
                    },
                }

        # 7. Track V3: Text+ Cards
        if hasattr(self, "nle_project") and self.nle_project.track_enabled.get("V3", True) and (not hasattr(self, "trim_title_var") or self.trim_title_var.get()):
            for idx, t_item in enumerate(self.nle_project.text_items):
                if not self.nle_project.is_item_visible_at("V3", t_item, tl_now):
                    continue
                raw_text = str(t_item.get("text", "")).strip() or ("نص تجريبي" if is_ar else "Sample Text")
                v3_ck = (
                    "V3", idx, raw_text, t_item.get("bg_color"), t_item.get("text_color"),
                    int(t_item.get("font_size", 34)), t_item.get("font_name"), box_w, box_h,
                    round(float(t_item.get("opacity", 1.0)), 2),
                    round(float(t_item.get("rotation", 0.0)), 1),
                )
                card_im = self._overlay_pil_cache.get(v3_ck)
                if card_im is None:
                    card_im = render_text_card_pil(
                        text=raw_text,
                        bg_color_key=t_item.get("bg_color", "black"),
                        text_color_key=t_item.get("text_color", "white"),
                        font_size=int(t_item.get("font_size", 34)),
                        font_name=t_item.get("font_name", "Segoe UI"),
                        video_w=box_w,
                        video_h=box_h,
                        opacity=float(t_item.get("opacity", 1.0)),
                        rotation=float(t_item.get("rotation", 0.0)),
                    )
                    if card_im is not None:
                        if len(self._overlay_pil_cache) > 64:
                            self._overlay_pil_cache.clear()
                        self._overlay_pil_cache[v3_ck] = card_im
                if card_im is None:
                    continue
                photo = ImageTk.PhotoImage(card_im)
                self._overlay_photo_refs.append(photo)
                _op_m, off_x, off_y, _sc_m = evaluate_item_animation(t_item, tl_now, box_w, box_h)
                cx = vx0 + int(round(box_w * float(t_item.get("x", 0.5)))) + off_x
                cy = vy0 + int(round(box_h * float(t_item.get("y", 0.12)))) + off_y
                tw, th = card_im.size
                tx0, ty0 = cx - tw // 2, cy - th // 2
                tx1, ty1 = tx0 + tw, ty0 + th
                self.player_studio_canvas.create_image(tx0, ty0, anchor="nw", image=photo)
                self.player_canvas_element_boxes[("V3", idx)] = {
                    "rect": (tx0, ty0, tx1, ty1),
                    "center": (cx, cy),
                    "handles": {
                        "tl": (tx0, ty0),
                        "tr": (tx1, ty0),
                        "bl": (tx0, ty1),
                        "br": (tx1, ty1),
                        "rot": ((tx0 + tx1) // 2, max(vy0 + 4, ty0 - 18)),
                    },
                }

        # 8. Track V4: Logo Watermarks
        if hasattr(self, "nle_project") and self.nle_project.track_enabled.get("V4", True) and (not hasattr(self, "trim_logo_var") or self.trim_logo_var.get()):
            for idx, l_item in enumerate(self.nle_project.logo_items):
                if not self.nle_project.is_item_visible_at("V4", l_item, tl_now):
                    continue
                logo_p = str(l_item.get("path", "")).strip()
                l_scale = max(0.04, min(0.85, float(l_item.get("scale", 0.16))))
                lw = max(24, int(round(box_w * l_scale)))
                lx_pct = float(l_item.get("x", 0.80))
                ly_pct = float(l_item.get("y", 0.04))
                anchor_mode = l_item.get("anchor", "nw")

                v4_ck = (
                    "V4", idx, logo_p, lw,
                    round(float(l_item.get("opacity", 0.85)), 2),
                    round(float(l_item.get("rotation", 0.0)), 1),
                )
                l_im_final = self._overlay_pil_cache.get(v4_ck)
                if l_im_final is None and logo_p and Path(logo_p).is_file():
                    try:
                        with Image.open(logo_p) as lim:
                            ow, oh = lim.size
                            lh = max(14, int(round(lw * (oh / max(1, ow)))))
                            l_rgba = lim.convert("RGBA").resize((lw, lh), Image.Resampling.LANCZOS)
                        l_im_final = apply_opacity_and_rotation(
                            l_rgba,
                            opacity=float(l_item.get("opacity", 0.85)),
                            rotation_deg=float(l_item.get("rotation", 0.0)),
                        )
                        if l_im_final is not None:
                            if len(self._overlay_pil_cache) > 64:
                                self._overlay_pil_cache.clear()
                            self._overlay_pil_cache[v4_ck] = l_im_final
                    except Exception:
                        l_im_final = None

                if l_im_final is not None:
                    photo = ImageTk.PhotoImage(l_im_final)
                    self._overlay_photo_refs.append(photo)
                    fw, fh = l_im_final.size
                    _op_m, off_x, off_y, _sc_m = evaluate_item_animation(l_item, tl_now, box_w, box_h)
                    if anchor_mode == "center":
                        lx0 = vx0 + int(round(box_w * lx_pct)) - fw // 2 + off_x
                        ly0 = vy0 + int(round(box_h * ly_pct)) - fh // 2 + off_y
                    else:
                        lx0 = vx0 + int(round(box_w * lx_pct)) + off_x
                        ly0 = vy0 + int(round(box_h * ly_pct)) + off_y
                    self.player_studio_canvas.create_image(lx0, ly0, anchor="nw", image=photo)
                    lx1, ly1 = lx0 + fw, ly0 + fh
                else:
                    fw, fh = lw, max(20, int(lw * 0.5))
                    _op_m, off_x, off_y, _sc_m = evaluate_item_animation(l_item, tl_now, box_w, box_h)
                    lx0 = vx0 + int(round(box_w * lx_pct)) + off_x
                    ly0 = vy0 + int(round(box_h * ly_pct)) + off_y
                    lx1, ly1 = lx0 + fw, ly0 + fh
                    self.player_studio_canvas.create_rectangle(lx0, ly0, lx1, ly1, fill="#e5534b", outline="#ffffff", width=1)
                    self.player_studio_canvas.create_text((lx0 + lx1) // 2, (ly0 + ly1) // 2, text="LOGO", fill="#ffffff", font=("Segoe UI", 8, "bold"))

                self.player_canvas_element_boxes[("V4", idx)] = {
                    "rect": (lx0, ly0, lx1, ly1),
                    "center": ((lx0 + lx1) // 2, (ly0 + ly1) // 2),
                    "handles": {
                        "tl": (lx0, ly0),
                        "tr": (lx1, ly0),
                        "bl": (lx0, ly1),
                        "br": (lx1, ly1),
                        "rot": ((lx0 + lx1) // 2, max(vy0 + 4, ly0 - 18)),
                    },
                }

        # 9. Live Subtitle Preview at Playhead
        if hasattr(self, "trim_burn_subs_var") and self.trim_burn_subs_var.get():
            live_sub = self._get_live_subtitle_at(tl_now)
            sub_txt = live_sub or (self.text("branding_subs_sample") if not self._is_playing() else "")
            if sub_txt:
                sub_y = vy1 - max(18, int(box_h * 0.065))
                sub_col_key = getattr(self, "subtitle_style", {}).get("text_color", "yellow")
                col_hex = "#FFE600" if sub_col_key == "yellow" else "#FFFFFF"
                shaped_sub = prepare_arabic_for_rendering(sub_txt)
                f_sz = max(8, min(14, box_w // 34))
                stw = min(box_w - 12, max(60, len(shaped_sub) * (f_sz - 2) + 20))
                self.player_studio_canvas.create_rectangle(
                    (vx0 + vx1) // 2 - stw // 2, sub_y - f_sz - 3,
                    (vx0 + vx1) // 2 + stw // 2, sub_y + f_sz + 3,
                    fill="#0d1117", outline="#30363d", width=1,
                )
                self.player_studio_canvas.create_text(
                    (vx0 + vx1) // 2, sub_y,
                    text=shaped_sub, fill=col_hex, font=("Segoe UI", f_sz, "bold"),
                )

        # 10. Framing Border & Margins
        border_col = "#30363d" if ratio_key in ("9:16", "1:1", "4:5") else "#161b22"
        self.player_studio_canvas.create_rectangle(vx0, vy0, vx1, vy1, outline=border_col, width=1)

        hud_parts = [ratio_key.upper() if ratio_key != "original" else ("الأصلي" if is_ar else "ORIG")]
        if abs(xf["zoom"] - 1.0) > 0.01 or abs(xf["pan_x"]) > 0.005 or abs(xf["pan_y"]) > 0.005:
            hud_parts.append(f"🔍{xf['zoom']:.2f}x  X:{int(round(xf['pan_x']*100)):+d}% Y:{int(round(xf['pan_y']*100)):+d}%")
        if len(self.nle_project.clips) > 1:
            hud_parts.append(f"Clip {c_idx + 1}/{len(self.nle_project.clips)}")
        hud_txt = " | ".join(hud_parts)
        if vy0 >= 20:
            self.player_studio_canvas.create_text((vx0 + vx1) // 2, vy0 - 10, text=hud_txt, fill="#6e7681", font=("Segoe UI", 8))

        # 11. Selection Gizmo
        sel_norm = self._normalize_selection_ref(self.player_canvas_selected)
        if sel_norm in self.player_canvas_element_boxes:
            box = self.player_canvas_element_boxes[sel_norm]
            rx0, ry0, rx1, ry1 = box["rect"]
            self.player_studio_canvas.create_rectangle(
                rx0 - 2, ry0 - 2, rx1 + 2, ry1 + 2,
                outline="#FFFFFF", width=2, dash=(5, 3),
            )
            rot_hx, rot_hy = box["handles"]["rot"]
            self.player_studio_canvas.create_line((rx0 + rx1) // 2, ry0 - 2, rot_hx, rot_hy, fill="#3fb950", width=2)
            self.player_studio_canvas.create_oval(rot_hx - 5, rot_hy - 5, rot_hx + 5, rot_hy + 5, fill="#3fb950", outline="#ffffff", width=1.5)
            hs = 5
            for h_key in ("tl", "tr", "bl", "br"):
                hx, hy = box["handles"][h_key]
                self.player_studio_canvas.create_rectangle(
                    hx - hs, hy - hs, hx + hs, hy + hs,
                    fill="#FFFFFF", outline="#0d1117", width=1.5,
                )

        # 12. Bottom Hint Bar
        hint_text = (
            "🖱️ اسحب داخل الفيديو لتحريك الكادر | عجلة الماوس للزوم | انقر على أي عنصر لتحريكه وتكبيره وتدويره"
            if is_ar
            else "🖱️ Drag video to Pan X/Y | Scroll Wheel to Zoom | Click any overlay to Move, Resize, or Rotate"
        )
        self.player_studio_canvas.create_text(cw // 2, ch - 7, text=hint_text, fill="#6e7681", font=("Segoe UI", 8))

    # -------------------------------------------------------------------------
    # Mouse & Interactive Events
    # -------------------------------------------------------------------------
    def _normalize_selection_ref(self, sel):
        if sel == "logo":
            return ("V4", 0) if (hasattr(self, "nle_project") and self.nle_project.logo_items) else None
        if isinstance(sel, str) and sel.startswith("text_"):
            try:
                return ("V3", int(sel.split("_")[1]))
            except ValueError:
                return None
        if isinstance(sel, tuple) and len(sel) == 2:
            return sel
        return None

    def _on_player_canvas_press(self, event):
        mx, my = event.x, event.y
        self.player_canvas_drag_start = (mx, my)
        self._drag_undo_recorded = False
        sel_norm = self._normalize_selection_ref(self.player_canvas_selected)

        # 1. Check Handles of Selected Overlay
        if sel_norm in self.player_canvas_element_boxes:
            box = self.player_canvas_element_boxes[sel_norm]
            for h_name, (hx, hy) in box["handles"].items():
                if abs(mx - hx) <= 8 and abs(my - hy) <= 8:
                    self.player_canvas_drag_mode = h_name
                    tkey, idx = sel_norm
                    tlist = self.nle_project.get_track_list(tkey)
                    if 0 <= idx < len(tlist):
                        it = tlist[idx]
                        self.player_canvas_drag_orig_scale = float(it.get("font_size", 34) if tkey == "V3" else it.get("scale", 0.20))
                        self.player_canvas_drag_orig_rot = float(it.get("rotation", 0.0))
                    return

        # 2. Hit-test Overlays
        clicked_elem = None
        for elem_ref, box in reversed(list(self.player_canvas_element_boxes.items())):
            x0, y0, x1, y1 = box["rect"]
            if x0 <= mx <= x1 and y0 <= my <= y1:
                clicked_elem = elem_ref
                break

        if clicked_elem is not None:
            self.player_canvas_selected = clicked_elem
            self.player_canvas_drag_mode = "move"
            tkey, idx = clicked_elem
            tlist = self.nle_project.get_track_list(tkey)
            if 0 <= idx < len(tlist):
                it = tlist[idx]
                self.player_canvas_drag_orig_pos = (float(it.get("x", 0.5)), float(it.get("y", 0.5)))
            if hasattr(self, "davinci_timeline"):
                self.davinci_timeline.selected_ref = clicked_elem
                self.davinci_timeline.redraw()
            self._render_player_studio_canvas()
            self._update_inspector_properties()
            return

        # 3. Direct Video Pan Drag
        vx0, vy0, vx1, vy1 = self._player_canvas_video_box
        c_idx = self._get_selected_or_active_clip_idx()
        self.player_canvas_selected = ("clip", c_idx)
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.selected_ref = ("clip", c_idx)
            self.davinci_timeline.redraw()

        if vx0 <= mx <= vx1 and vy0 <= my <= vy1:
            self.player_canvas_drag_mode = "pan_video"
            xf = self._get_effective_video_transform(c_idx)
            self.player_canvas_drag_orig_pos = (xf["pan_x"], xf["pan_y"])
            self.player_studio_canvas.configure(cursor="fleur")
        else:
            self.player_canvas_drag_mode = None

        self._sync_transform_sliders_from_state()
        self._render_player_studio_canvas()
        self._update_inspector_properties()

    def _on_player_canvas_drag(self, event):
        if not self.player_canvas_drag_mode:
            return

        vx0, vy0, vx1, vy1 = self._player_canvas_video_box
        vw = max(1.0, float(vx1 - vx0))
        vh = max(1.0, float(vy1 - vy0))
        dx = event.x - self.player_canvas_drag_start[0]
        dy = event.y - self.player_canvas_drag_start[1]

        if self.player_canvas_drag_mode == "pan_video":
            orig_px, orig_py = self.player_canvas_drag_orig_pos
            new_px = orig_px + (dx / vw)
            new_py = orig_py + (dy / vh)
            self._set_effective_video_transform(pan_x=new_px, pan_y=new_py)
            self._sync_transform_sliders_from_state()
            self._render_player_studio_canvas()
            return

        sel_norm = self._normalize_selection_ref(self.player_canvas_selected)
        if not sel_norm or sel_norm[0] not in ("V2", "V3", "V4"):
            return
        tkey, idx = sel_norm
        tlist = self.nle_project.get_track_list(tkey)
        if not (0 <= idx < len(tlist)):
            return
        if not getattr(self, "_drag_undo_recorded", False) and (abs(dx) > 2 or abs(dy) > 2):
            self.nle_project.push_undo()
            self._drag_undo_recorded = True
        item = tlist[idx]

        if self.player_canvas_drag_mode == "move":
            orig_x, orig_y = self.player_canvas_drag_orig_pos
            nx = max(0.0, min(0.98, orig_x + dx / vw))
            ny = max(0.0, min(0.98, orig_y + dy / vh))

            self._snap_guide_x = False
            self._snap_guide_y = False
            if tkey in ("V2", "V3") or item.get("anchor") == "center":
                if abs(nx - 0.50) < 0.022:
                    nx = 0.50
                    self._snap_guide_x = True
                if abs(ny - 0.50) < 0.022:
                    ny = 0.50
                    self._snap_guide_y = True

            item["x"] = round(nx, 4)
            item["y"] = round(ny, 4)
            if tkey == "V4" and idx == 0:
                self.video_branding_config["logo_x"] = item["x"]
                self.video_branding_config["logo_y"] = item["y"]
            self._render_player_studio_canvas()

        elif self.player_canvas_drag_mode == "rot":
            box = self.player_canvas_element_boxes.get(sel_norm)
            if box:
                cx, cy = box["center"]
                angle_deg = math.degrees(math.atan2(event.y - cy, event.x - cx)) + 90.0
                while angle_deg > 180.0:
                    angle_deg -= 360.0
                while angle_deg < -180.0:
                    angle_deg += 360.0
                for snap_a in (-180.0, -90.0, -45.0, 0.0, 45.0, 90.0, 180.0):
                    if abs(angle_deg - snap_a) < 3.5:
                        angle_deg = snap_a
                        break
                item["rotation"] = round(angle_deg, 1)
                self._render_player_studio_canvas()

        elif self.player_canvas_drag_mode in ("tl", "tr", "bl", "br"):
            dist_delta = (dx + dy) / 2.0
            if self.player_canvas_drag_mode in ("tl", "bl"):
                dist_delta = (-dx + dy) / 2.0 if self.player_canvas_drag_mode == "bl" else (-dx - dy) / 2.0
            elif self.player_canvas_drag_mode == "tr":
                dist_delta = (dx - dy) / 2.0

            if tkey == "V3":
                new_fs = max(14, min(110, int(round(self.player_canvas_drag_orig_scale + dist_delta * 0.35))))
                item["font_size"] = new_fs
            else:
                new_sc = max(0.05, min(0.95, self.player_canvas_drag_orig_scale + (dist_delta / vw)))
                item["scale"] = round(new_sc, 3)
                if tkey == "V4" and idx == 0:
                    self.video_branding_config["logo_scale"] = item["scale"]
            self._render_player_studio_canvas()

    def _on_player_canvas_release(self, _e):
        self._snap_guide_x = False
        self._snap_guide_y = False
        if self.player_canvas_drag_mode:
            if hasattr(self, "davinci_timeline"):
                self.davinci_timeline.redraw()
            self._save_settings()
            self._refresh_master_export_summary()
            self._update_inspector_properties()
            self._render_player_studio_canvas()
        self.player_canvas_drag_mode = None

    def _on_player_canvas_mousewheel(self, event):
        """MouseWheel on Viewer zooms video frame smoothly (or scales overlay with Shift)."""
        step = 1 if event.delta > 0 else -1
        shift_held = bool(event.state & 0x0001)
        sel_norm = self._normalize_selection_ref(self.player_canvas_selected)

        if shift_held and sel_norm and sel_norm[0] in ("V2", "V3", "V4"):
            tkey, idx = sel_norm
            tlist = self.nle_project.get_track_list(tkey)
            if 0 <= idx < len(tlist):
                it = tlist[idx]
                if tkey == "V3":
                    it["font_size"] = max(14, min(110, int(it.get("font_size", 34)) + step * 3))
                else:
                    it["scale"] = round(max(0.05, min(0.95, float(it.get("scale", 0.2)) + step * 0.02)), 3)
                self._update_inspector_properties()
                self._render_player_studio_canvas()
            return

        xf = self._get_effective_video_transform()
        factor = 1.08 if step > 0 else (1.0 / 1.08)
        new_z = max(0.25, min(4.0, xf["zoom"] * factor))
        if abs(new_z - 1.0) < 0.03:
            new_z = 1.0
        self._ready_composed_video = None
        self._set_effective_video_transform(zoom=new_z)
        self._sync_transform_sliders_from_state()
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.redraw()
        if hasattr(self, "export_opt_framing_var"):
            self.export_opt_framing_var.set(True)
        self._save_settings()
        self._show_studio_canvas()
        self._render_player_studio_canvas()

    def _on_player_canvas_hover(self, event):
        mx, my = event.x, event.y
        sel_norm = self._normalize_selection_ref(self.player_canvas_selected)

        if sel_norm in self.player_canvas_element_boxes:
            box = self.player_canvas_element_boxes[sel_norm]
            for h_name, (hx, hy) in box["handles"].items():
                if abs(mx - hx) <= 8 and abs(my - hy) <= 8:
                    if h_name == "rot":
                        self.player_studio_canvas.configure(cursor="exchange")
                    else:
                        self.player_studio_canvas.configure(cursor="size_nw_se" if h_name in ("tl", "br") else "size_ne_sw")
                    return
            x0, y0, x1, y1 = box["rect"]
            if x0 <= mx <= x1 and y0 <= my <= y1:
                self.player_studio_canvas.configure(cursor="fleur")
                return

        for _ref, box in self.player_canvas_element_boxes.items():
            x0, y0, x1, y1 = box["rect"]
            if x0 <= mx <= x1 and y0 <= my <= y1:
                self.player_studio_canvas.configure(cursor="hand2")
                return

        vx0, vy0, vx1, vy1 = getattr(self, "_player_canvas_video_box", (0, 0, 0, 0))
        if vx0 <= mx <= vx1 and vy0 <= my <= vy1 and self._cached_player_frame is not None:
            self.player_studio_canvas.configure(cursor="fleur")
        else:
            self.player_studio_canvas.configure(cursor="arrow")

    def _on_player_canvas_double_click(self, event):
        mx, my = event.x, event.y
        for elem_ref, box in reversed(list(self.player_canvas_element_boxes.items())):
            x0, y0, x1, y1 = box["rect"]
            if x0 <= mx <= x1 and y0 <= my <= y1:
                self.player_canvas_selected = elem_ref
                self._update_inspector_properties()
                if elem_ref[0] == "V2" and self.nle_project.media_items[elem_ref[1]].get("type") != "image":
                    it = self.nle_project.media_items[elem_ref[1]]
                    dlg = IconPickerDialog(self, initial_key=it.get("icon_key", "subscribe_ar"), initial_text=it.get("text", ""))
                    self.wait_window(dlg)
                    if dlg.result:
                        it["icon_key"] = dlg.result["icon_key"]
                        it["text"] = dlg.result.get("text", "")
                        self._render_player_studio_canvas()
                        self._update_inspector_properties()
                return
        # Safely deselect active item and refresh properties without triggering fullscreen
        self.player_canvas_selected = None
        self._sync_transform_sliders_from_state()
        self._update_inspector_properties()
        self._render_player_studio_canvas()

    def _show_player_canvas_context_menu(self, event):
        menu = tk.Menu(self, tearoff=0)
        is_ar = self.language_var.get() == "العربية"
        menu.add_command(
            label="📝 " + ("إضافة نص جديد هنا" if is_ar else "Add New Text+ Here"),
            command=lambda: self._quick_add_text_at(event.x, event.y),
        )
        menu.add_command(
            label="⭐ " + ("إضافة أيقونة أو شارة احترافية..." if is_ar else "Add Pro Icon / Badge..."),
            command=lambda: self._nle_add_element("icon", self.nle_playhead_sec),
        )
        menu.add_command(
            label="🖼️ " + ("إضافة صورة فوق الفيديو..." if is_ar else "Add Image Overlay..."),
            command=lambda: self._nle_add_element("image", self.nle_playhead_sec),
        )
        menu.add_command(
            label="🛡️ " + ("إضافة / تغيير اللوجو..." if is_ar else "Add / Change Logo..."),
            command=lambda: self._nle_add_element("logo", self.nle_playhead_sec),
        )
        sel_norm = self._normalize_selection_ref(self.player_canvas_selected)
        if sel_norm and sel_norm[0] in ("V2", "V3", "V4"):
            menu.add_separator()
            menu.add_command(
                label="🗑️ " + ("حذف العنصر المحدد" if is_ar else "Delete Selected Overlay"),
                command=self._quick_delete_selected_text,
            )
        menu.add_separator()
        menu.add_command(
            label="📱 " + ("تحويل لريلز 9:16 (ملء الشاشة)" if is_ar else "Set 9:16 Reels (Smart Fill)"),
            command=lambda: self._quick_set_aspect_ratio("9:16"),
        )
        menu.add_command(
            label="↺ " + ("إعادة توسيط الكادر والزوم (1.0x)" if is_ar else "Reset Video Pan & Zoom (1.0x)"),
            command=self._reset_video_transform,
        )
        menu.add_command(
            label="🎨 " + ("تصحيح وتدرج الألوان..." if is_ar else "Color Grading Dialog..."),
            command=self.open_video_color_dialog,
        )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _quick_add_text_at(self, mx, my):
        vx0, vy0, vx1, vy1 = self._player_canvas_video_box
        vw = max(1, vx1 - vx0)
        vh = max(1, vy1 - vy0)
        nx = max(0.08, min(0.92, (mx - vx0) / vw))
        ny = max(0.05, min(0.95, (my - vy0) / vh))

        is_ar = self.language_var.get() == "العربية"
        self.nle_project.push_undo()
        tot = max(5.0, self._edited_total_duration() or 60.0)
        s_sec = getattr(self, "nle_playhead_sec", 0.0)
        e_sec = min(tot, s_sec + 5.0)

        new_item = {
            "id": self.nle_project.next_id("v3"),
            "text": "نص جديد" if is_ar else "New Text+",
            "x": round(nx, 4),
            "y": round(ny, 4),
            "font_size": 34,
            "font_name": "Segoe UI",
            "bg_color": "black",
            "text_color": "white",
            "opacity": 1.0,
            "rotation": 0.0,
            "full_duration": False,
            "start_sec": s_sec,
            "end_sec": e_sec,
            "enabled": True,
        }
        self.nle_project.text_items.append(new_item)
        self.nle_project.track_enabled["V3"] = True
        self.trim_title_var.set(True)
        if hasattr(self, "export_opt_overlays_var"):
            self.export_opt_overlays_var.set(True)
        self._overlay_pil_cache.clear()
        self.player_canvas_selected = ("V3", len(self.nle_project.text_items) - 1)
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.selected_ref = self.player_canvas_selected
            self.davinci_timeline.redraw()
        self._save_settings()
        self._refresh_master_export_summary()
        self._show_inspector_context("overlay")
        self._render_player_studio_canvas()

    def compose_full_res_snapshot_frame(self, target_w: int = None, target_h: int = None) -> Image.Image:
        """
        Renders a full-resolution composite cover snapshot (including transformed video frame,
        aspect ratio crop/letterbox, color grading, V2 media/icons, V3 text+ cards, V4 logo watermarks,
        and in/out animation states at the current playhead).
        """
        if not getattr(self, "input_path", None) or not Path(self.input_path).is_file():
            return None

        # 1. Determine target resolution
        ratio_key = self.trim_aspect_var.get() if hasattr(self, "trim_aspect_var") else "original"
        aspect_lookup = {
            "9:16": (1080, 1920),
            "1:1": (1080, 1080),
            "4:5": (1080, 1350),
            "4:3": (1440, 1080),
            "16:9": (1920, 1080),
        }

        if target_w and target_h:
            box_w, box_h = int(target_w), int(target_h)
        elif ratio_key in aspect_lookup:
            box_w, box_h = aspect_lookup[ratio_key]
        elif getattr(self, "media_width", 0) and getattr(self, "media_height", 0):
            box_w = int(self.media_width)
            box_h = int(self.media_height)
        else:
            box_w, box_h = (1920, 1080)

        tl_now = float(getattr(self, "nle_playhead_sec", 0.0))
        c_idx, cur_clip, src_now = self.nle_project.timeline_to_source(tl_now) if hasattr(self, "nle_project") else (0, None, tl_now)

        # 2. Extract or use cached high-res frame
        raw_frame = None
        try:
            raw_frame = extract_video_sample_frame(self.input_path, src_now, max_w=max(box_w, 1920))
        except Exception:
            pass
        if raw_frame is None:
            raw_frame = getattr(self, "_cached_player_frame", None)
        if raw_frame is None:
            raw_frame = Image.new("RGBA", (box_w, box_h), (10, 14, 20, 255))

        # 3. Apply color grading
        color_cfg = self.video_branding_config.get("color_config", {})
        color_on = isinstance(color_cfg, dict) and color_cfg.get("enabled", True) and not is_color_neutral(color_cfg)
        if color_on:
            raw_frame = apply_color_to_image(raw_frame, color_cfg)

        # 4. Transform / Crop / Fit to target aspect ratio
        xf = self._get_effective_video_transform(c_idx)
        fit_mode = self.video_branding_config.get("fit_mode", "crop")
        v1_enabled = self.nle_project.track_enabled.get("V1", True) if hasattr(self, "nle_project") else True

        if v1_enabled:
            comp_base = render_transformed_pil_frame(
                raw_frame,
                box_w,
                box_h,
                fit_mode=fit_mode,
                zoom=xf["zoom"],
                pan_x=xf["pan_x"],
                pan_y=xf["pan_y"],
                flip_h=xf["flip_h"],
                clamp_edges=xf["clamp_edges"],
            )
        else:
            comp_base = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 255))

        if comp_base.mode != "RGBA":
            comp_base = comp_base.convert("RGBA")

        is_ar = (self.language_var.get() == "العربية") if hasattr(self, "language_var") else True

        # 5. Track V2: Icons, Badges & Custom Images
        if hasattr(self, "nle_project") and self.nle_project.track_enabled.get("V2", True):
            for idx, m_item in enumerate(self.nle_project.media_items):
                if not self.nle_project.is_item_visible_at("V2", m_item, tl_now):
                    continue
                ov_im = render_media_overlay_pil(m_item, box_w, box_h, is_ar=is_ar)
                if ov_im is None:
                    continue
                op_mult, off_x, off_y, sc_mult = evaluate_item_animation(m_item, tl_now, box_w, box_h)
                if op_mult < 0.01:
                    continue
                if abs(sc_mult - 1.0) > 0.02:
                    nw = max(10, int(ov_im.width * sc_mult))
                    nh = max(10, int(ov_im.height * sc_mult))
                    ov_im = ov_im.resize((nw, nh), Image.Resampling.LANCZOS)
                if op_mult < 0.99:
                    ov_im = apply_opacity_and_rotation(ov_im, opacity=op_mult, rotation_deg=0.0)

                cx = int(round(box_w * float(m_item.get("x", 0.5)))) + off_x
                cy = int(round(box_h * float(m_item.get("y", 0.5)))) + off_y
                ix0 = cx - ov_im.width // 2
                iy0 = cy - ov_im.height // 2
                comp_base.alpha_composite(ov_im, (ix0, iy0))

        # 6. Track V3: Text+ Cards
        if hasattr(self, "nle_project") and self.nle_project.track_enabled.get("V3", True) and (not hasattr(self, "trim_title_var") or self.trim_title_var.get()):
            for idx, t_item in enumerate(self.nle_project.text_items):
                if not self.nle_project.is_item_visible_at("V3", t_item, tl_now):
                    continue
                raw_text = str(t_item.get("text", "")).strip() or ("نص تجريبي" if is_ar else "Sample Text")
                card_im = render_text_card_pil(
                    text=raw_text,
                    bg_color_key=t_item.get("bg_color", "black"),
                    text_color_key=t_item.get("text_color", "white"),
                    font_size=int(t_item.get("font_size", 34)),
                    font_name=t_item.get("font_name", "Segoe UI"),
                    video_w=box_w,
                    video_h=box_h,
                    opacity=float(t_item.get("opacity", 1.0)),
                    rotation=float(t_item.get("rotation", 0.0)),
                )
                if card_im is None:
                    continue
                op_mult, off_x, off_y, sc_mult = evaluate_item_animation(t_item, tl_now, box_w, box_h)
                if op_mult < 0.01:
                    continue
                if abs(sc_mult - 1.0) > 0.02:
                    nw = max(10, int(card_im.width * sc_mult))
                    nh = max(10, int(card_im.height * sc_mult))
                    card_im = card_im.resize((nw, nh), Image.Resampling.LANCZOS)
                if op_mult < 0.99:
                    card_im = apply_opacity_and_rotation(card_im, opacity=op_mult, rotation_deg=0.0)

                cx = int(round(box_w * float(t_item.get("x", 0.5)))) + off_x
                cy = int(round(box_h * float(t_item.get("y", 0.12)))) + off_y
                tx0 = cx - card_im.width // 2
                ty0 = cy - card_im.height // 2
                comp_base.alpha_composite(card_im, (tx0, ty0))

        # 7. Track V4: Logo Watermarks
        if hasattr(self, "nle_project") and self.nle_project.track_enabled.get("V4", True) and (not hasattr(self, "trim_logo_var") or self.trim_logo_var.get()):
            for idx, l_item in enumerate(self.nle_project.logo_items):
                if not self.nle_project.is_item_visible_at("V4", l_item, tl_now):
                    continue
                logo_p = str(l_item.get("path", "")).strip()
                if not logo_p or not Path(logo_p).is_file():
                    continue
                l_scale = max(0.04, min(0.85, float(l_item.get("scale", 0.16))))
                lw = max(32, int(round(box_w * l_scale)))
                try:
                    with Image.open(logo_p) as lim:
                        ow, oh = lim.size
                        lh = max(14, int(round(lw * (oh / max(1, ow)))))
                        l_rgba = lim.convert("RGBA").resize((lw, lh), Image.Resampling.LANCZOS)
                    l_final = apply_opacity_and_rotation(
                        l_rgba,
                        opacity=float(l_item.get("opacity", 0.85)),
                        rotation_deg=float(l_item.get("rotation", 0.0)),
                    )
                    _op_m, off_x, off_y, _sc_m = evaluate_item_animation(l_item, tl_now, box_w, box_h)
                    cx = int(round(box_w * float(l_item.get("x", 0.80)))) + off_x
                    cy = int(round(box_h * float(l_item.get("y", 0.04)))) + off_y
                    comp_base.alpha_composite(l_final, (cx, cy))
                except Exception:
                    pass

        return comp_base

