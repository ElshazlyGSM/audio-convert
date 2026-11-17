"""
Playback Synchronization Controller Mixin
Handles VLC media player instance, hardware audio equalizer, volume boost,
real-time timeline synchronization, gap playback, and playhead auto-follow.
"""

import sys
import time
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

try:
    import vlc
except Exception:
    vlc = None

import convert


class PlaybackSyncMixin:
    """Provides VLC playback and timeline synchronization methods for MediaAudioStudioApp."""

    def _is_playing(self):
        return bool(getattr(self, "_in_gap_playback", False) or (self.media_player and self.media_player.is_playing()))

    def _refresh_play_button(self):
        if not hasattr(self, "play_button"):
            return
        self.play_button.configure(text="||" if self._is_playing() else "▶")

    def _ensure_vlc_player(self):
        if vlc is None:
            return
        if self.vlc_instance is None:
            try:
                self.vlc_instance = vlc.Instance(
                    "--no-video-title-show",
                    "--no-plugins-cache",
                    "--quiet",
                    "--no-stats",
                    "--no-mouse-events",
                    "--avcodec-hw=any",
                    "--avcodec-threads=0",
                    "--file-caching=1500",
                    "--network-caching=1500",
                    "--disc-caching=1500",
                    "--drop-late-frames",
                    "--skip-frames",
                )
            except Exception:
                self.vlc_instance = None
                return
        if self.media_player is None and self.vlc_instance:
            try:
                self.media_player = self.vlc_instance.media_player_new()
            except Exception:
                self.media_player = None
                return
        self._attach_video_surface()

    def _attach_video_surface(self):
        if not self.media_player:
            return
        self.update_idletasks()
        surface = self.video_surface
        if sys.platform.startswith("win"):
            self.media_player.set_hwnd(surface.winfo_id())
        elif sys.platform == "darwin":
            self.media_player.set_nsobject(surface.winfo_id())
        else:
            self.media_player.set_xwindow(surface.winfo_id())
        # If paused, refresh frame on HWND so it never stays black
        try:
            if not self._is_playing():
                cur_ms = self.media_player.get_time()
                if cur_ms >= 0:
                    self.media_player.set_time(cur_ms)
        except Exception:
            pass

    def selected_playback_speed(self):
        try:
            return float(self.speed_var.get().replace("x", ""))
        except ValueError:
            return 1.0

    def toggle_play_pause(self):
        if self.loaded_media_path == self.input_path and self._is_playing():
            self.pause_playback()
            return
        self.play_source_file()

    def _apply_active_clip_playback_fx(self, clip=None):
        if not self.media_player:
            return
        if clip is None and hasattr(self, "nle_project") and 0 <= getattr(self, "active_playback_clip_idx", 0) < len(self.nle_project.clips):
            clip = self.nle_project.clips[self.active_playback_clip_idx]
        base_spd = self.selected_playback_speed()
        clip_spd = float(clip.get("speed", 1.0)) if clip else 1.0
        eff_spd = max(0.25, min(4.0, base_spd * clip_spd))
        try:
            self.media_player.set_rate(eff_spd)
        except Exception:
            pass

        a1_on = self.nle_project.track_enabled.get("A1", True) if hasattr(self, "nle_project") else True
        clip_muted = bool(clip and clip.get("muted", False))
        base_vol = float(self.volume_var.get())
        clip_vol = float(clip.get("volume", 1.0)) if clip else 1.0
        is_muted = (not a1_on) or clip_muted or (clip_vol <= 0.01)

        gain_db = 0.0
        try:
            gain_db = float(self.boost_gain_var.get())
        except Exception:
            gain_db = 0.0

        # Real-time hardware Equalizer & Preamp in VLC
        try:
            if vlc is not None and hasattr(vlc, "AudioEqualizer"):
                eq = vlc.AudioEqualizer()
                preamp = max(-20.0, min(20.0, gain_db))
                eq.set_preamp(preamp)

                enh_name = str(self.enhancement_var.get() if hasattr(self, "enhancement_var") else "Off").lower()
                if "clearer" in enh_name or "louder" in enh_name or "podcast" in enh_name or "وضوح" in enh_name:
                    eq.set_amp_at_index(0, -2.0)
                    eq.set_amp_at_index(4, 3.0)
                    eq.set_amp_at_index(5, 5.0)
                    eq.set_amp_at_index(6, 4.0)
                elif "bass" in enh_name or "ضخام" in enh_name:
                    eq.set_amp_at_index(0, 6.0)
                    eq.set_amp_at_index(1, 5.0)
                elif "noise" in enh_name or "clean" in enh_name or "ضوضاء" in enh_name or "تنقية" in enh_name:
                    eq.set_amp_at_index(0, -4.0)
                    eq.set_amp_at_index(9, -7.0)
                elif "echo" in enh_name or "صدى" in enh_name:
                    eq.set_amp_at_index(0, -5.0)
                    eq.set_amp_at_index(2, -3.0)

                self.media_player.set_equalizer(eq)
        except Exception:
            pass

        # VLC Volume with acoustic gain curve & definitive hardware mute
        if is_muted:
            eff_vol = 0
            try:
                self.media_player.audio_set_mute(True)
            except Exception:
                pass
        else:
            try:
                self.media_player.audio_set_mute(False)
            except Exception:
                pass
            gain_mult = min(2.5, max(0.1, 10.0 ** (gain_db / 20.0))) if abs(gain_db) > 0.1 else 1.0
            scale_factor = gain_mult if gain_mult < 1.0 else (1.0 + (gain_mult - 1.0) * 0.4)
            eff_vol = int(max(0, min(200, round(base_vol * clip_vol * scale_factor))))

        try:
            self.media_player.audio_set_volume(eff_vol)
        except Exception:
            pass

        # Real-time hardware audio delay / advance in VLC
        try:
            if clip and clip.get("audio_tl_start") is not None:
                offset_s = float(clip["audio_tl_start"]) - float(clip.get("tl_start", 0.0))
                # VLC audio delay: positive value delays audio, negative advances audio (microseconds)
                self.media_player.audio_set_delay(int(offset_s * 1_000_000))
            else:
                self.media_player.audio_set_delay(0)
        except Exception:
            pass

    def play_source_file(self):
        if not self.input_path or not self.input_path.is_file():
            messagebox.showwarning(self.text("app_title"), self.text("choose_single_trim"))
            return
        if vlc is None:
            messagebox.showwarning(self.text("app_title"), self.text("vlc_missing"))
            return

        tot_tl = self._edited_total_duration()
        tl_sec = self._current_timeline_seconds()
        if tot_tl > 0 and tl_sec >= tot_tl - 0.25:
            tl_sec = 0.0
            self.nle_playhead_sec = 0.0
            self.timeline_var.set(0.0)
            if hasattr(self, "davinci_timeline"):
                self.davinci_timeline.set_playhead(0.0)

        c_idx, clip, src_sec = self.nle_project.timeline_to_source(tl_sec) if hasattr(self, "nle_project") else (0, None, tl_sec)
        self.active_playback_clip_idx = c_idx

        if self.media_player and self.loaded_media_path == self.input_path:
            state = self.media_player.get_state()
            if self._is_playing():
                self._refresh_play_button()
                return
            if state not in {vlc.State.Ended, vlc.State.Error, vlc.State.Stopped}:
                if getattr(self, "studio_live_preview_mode", False) and self.input_path.suffix.lower() in convert.VIDEO_EXTS:
                    self._show_studio_canvas()
                else:
                    self._show_vlc_surface()
                if clip is None:
                    self._in_gap_playback = True
                    self._gap_last_wall_ts = time.monotonic()
                else:
                    self._in_gap_playback = False
                    self.media_player.set_time(int(max(0.0, src_sec) * 1000))
                    self.media_player.play()
                    self._apply_active_clip_playback_fx(clip)
                    self.after(50, lambda c=clip: self._apply_active_clip_playback_fx(c))
                    self.after(160, lambda c=clip: self._apply_active_clip_playback_fx(c))
                self.apply_video_aspect_ratio()
                self.apply_video_color_adjustments()
                self._attach_vlc_subtitles_if_available()
                self._schedule_playback_tick()
                self._update_run_state()
                self._refresh_play_button()
                return

        self._start_media_from(tl_sec, is_timeline_time=True)

    def _start_media_from(self, start_seconds=0, is_timeline_time=False):
        self.stop_playback(reset_position=False)
        self._ensure_vlc_player()
        if not self.vlc_instance or not self.media_player:
            return

        if is_timeline_time and hasattr(self, "nle_project") and self.nle_project.clips:
            c_idx, clip, src_sec = self.nle_project.timeline_to_source(start_seconds)
            self.active_playback_clip_idx = c_idx
            self.nle_playhead_sec = float(start_seconds)
        else:
            src_sec = max(0.0, float(start_seconds))
            if hasattr(self, "nle_project") and self.nle_project.clips:
                c_idx, tl_mapped = self.nle_project.source_to_timeline(src_sec)
                self.active_playback_clip_idx = c_idx
                self.nle_playhead_sec = tl_mapped
                clip = self.nle_project.clips[c_idx]
            else:
                clip = None
                self.nle_playhead_sec = src_sec

        self._attach_video_surface()
        if getattr(self, "studio_live_preview_mode", False) and self.input_path and self.input_path.suffix.lower() in convert.VIDEO_EXTS:
            self._show_studio_canvas()
        else:
            self._show_vlc_surface()

        media = self.vlc_instance.media_new(str(self.input_path))
        self.media_player.set_media(media)
        self.loaded_media_path = self.input_path

        if clip is None and is_timeline_time and hasattr(self, "nle_project") and self.nle_project.clips:
            self._in_gap_playback = True
            self._gap_last_wall_ts = time.monotonic()
        else:
            self._in_gap_playback = False
            self.media_player.play()
            self._seek_loaded_player(src_sec * 1000)
            self._apply_active_clip_playback_fx(clip)
            self.after(50, lambda c=clip: self._apply_active_clip_playback_fx(c))
            self.after(160, lambda c=clip: self._apply_active_clip_playback_fx(c))

        self.play_started_at = time.monotonic()
        self.apply_video_aspect_ratio()
        self.apply_video_color_adjustments()
        self._attach_vlc_subtitles_if_available()
        self._update_run_state()
        self._schedule_playback_tick()
        self._sync_live_video_overlay()
        self._refresh_play_button()

    def _seek_loaded_player(self, target_ms):
        if self.media_player and self.loaded_media_path == self.input_path and target_ms >= 0:
            self.media_player.set_time(int(target_ms))

    def pause_playback(self):
        self._in_gap_playback = False
        if self.media_player and self.media_player.is_playing():
            self.media_player.pause()
        if getattr(self, "aux_audio_player", None):
            try:
                self.aux_audio_player.pause()
            except Exception:
                pass
        self._cancel_playback_tick()
        self._update_run_state()
        self._refresh_play_button()
        self._sync_live_video_overlay()

    def stop_playback(self, reset_position=True):
        self._in_gap_playback = False
        self._cancel_playback_tick()
        if self.media_player:
            self.media_player.stop()
        if getattr(self, "aux_audio_player", None):
            try:
                self.aux_audio_player.stop()
                self._aux_loaded_path = None
            except Exception:
                pass
        if reset_position:
            self.nle_playhead_sec = 0.0
            self.timeline_var.set(0.0)
            if hasattr(self, "davinci_timeline"):
                self.davinci_timeline.set_playhead(0.0)
            self._refresh_timeline_text()
        self._update_run_state()
        self._refresh_play_button()
        if hasattr(self, "input_path") and self.input_path and self.input_path.is_file() and self.input_path.suffix.lower() in convert.VIDEO_EXTS:
            self._show_studio_canvas()
            tl_sec = self._current_timeline_seconds()
            _idx, _c, src_sec = self.nle_project.timeline_to_source(tl_sec) if hasattr(self, "nle_project") else (0, None, tl_sec)
            self._request_fast_preview_frame(src_sec, force=True)

    def _cancel_playback_tick(self):
        if self.playback_tick:
            self.after_cancel(self.playback_tick)
            self.playback_tick = None

    def _schedule_playback_tick(self):
        if not self.media_player:
            return

        # 1. Seamless Gap Playback Handling
        if getattr(self, "_in_gap_playback", False):
            now = time.monotonic()
            dt = (now - getattr(self, "_gap_last_wall_ts", now)) * self.selected_playback_speed()
            self._gap_last_wall_ts = now
            new_tl = self.nle_playhead_sec + dt
            tot_tl = self._edited_total_duration() or 0.0

            c_idx, next_clip, src_sec = (
                self.nle_project.timeline_to_source(new_tl)
                if hasattr(self, "nle_project")
                else (0, None, new_tl)
            )
            if next_clip is not None:
                self._in_gap_playback = False
                self.active_playback_clip_idx = c_idx
                self.nle_playhead_sec = new_tl
                self.timeline_var.set(new_tl)
                if hasattr(self, "davinci_timeline"):
                    self.davinci_timeline.set_playhead(new_tl, auto_follow=True)
                self.media_player.set_time(int(max(0.0, src_sec) * 1000))
                self.media_player.play()
                self._apply_active_clip_playback_fx(next_clip)
                self._render_player_studio_canvas()
                self._refresh_timeline_text()
                self.playback_tick = self.after(33, self._schedule_playback_tick)
                return
            elif new_tl >= tot_tl and tot_tl > 0:
                self._in_gap_playback = False
                self.nle_playhead_sec = tot_tl
                self.timeline_var.set(tot_tl)
                if hasattr(self, "davinci_timeline"):
                    self.davinci_timeline.set_playhead(tot_tl)
                self.pause_playback()
                return
            else:
                self.nle_playhead_sec = new_tl
                self.timeline_var.set(new_tl)
                if hasattr(self, "davinci_timeline"):
                    self.davinci_timeline.set_playhead(new_tl, auto_follow=True)
                self._render_player_studio_canvas()
                self._refresh_timeline_text()
                self.playback_tick = self.after(33, self._schedule_playback_tick)
                return

        state = self.media_player.get_state()
        if state in {vlc.State.Ended, vlc.State.Error, vlc.State.Stopped}:
            if state == vlc.State.Stopped and self.play_started_at and time.monotonic() - self.play_started_at < 5:
                self.playback_tick = self.after(120, self._schedule_playback_tick)
                return
            if state == vlc.State.Ended:
                tot = self._edited_total_duration()
                if tot > 0:
                    self.nle_playhead_sec = tot
                    self.timeline_var.set(tot)
                    if hasattr(self, "davinci_timeline"):
                        self.davinci_timeline.set_playhead(tot)
                    self._refresh_timeline_text()
            self._update_run_state()
            self._refresh_play_button()
            self._sync_live_video_overlay()
            return

        duration_ms = self.media_player.get_length()
        if duration_ms > 0 and self.media_duration <= 0:
            self.media_duration = duration_ms / 1000.0
            if hasattr(self, "nle_project") and not self.nle_project.clips:
                self.nle_project.init_from_source(self.media_duration, filename=self.input_path.name if self.input_path else "")
                self._refresh_modular_export_combos()
            self.timeline_scale.configure(to=self._edited_total_duration() or self.media_duration)

        current_ms = self.media_player.get_time()
        if current_ms >= 0:
            src_now = current_ms / 1000.0
            if hasattr(self, "nle_project") and self.nle_project.clips:
                c_idx = getattr(self, "active_playback_clip_idx", 0)
                if not (0 <= c_idx < len(self.nle_project.clips)):
                    c_idx = 0
                    self.active_playback_clip_idx = 0
                cur_c = self.nle_project.clips[c_idx]

                if src_now >= cur_c["src_end"] - 0.05:
                    if c_idx + 1 < len(self.nle_project.clips):
                        nxt_c = self.nle_project.clips[c_idx + 1]
                        gap = nxt_c["tl_start"] - cur_c["tl_end"]
                        if gap >= 0.04:
                            self.active_playback_clip_idx = c_idx + 1
                            self._in_gap_playback = True
                            self._gap_last_wall_ts = time.monotonic()
                            self.nle_playhead_sec = cur_c["tl_end"]
                            self.timeline_var.set(self.nle_playhead_sec)
                            if hasattr(self, "davinci_timeline"):
                                self.davinci_timeline.set_playhead(self.nle_playhead_sec, auto_follow=True)
                            self.media_player.pause()
                            self._render_player_studio_canvas()
                            self._refresh_timeline_text()
                            self.playback_tick = self.after(33, self._schedule_playback_tick)
                            return
                        else:
                            self.active_playback_clip_idx = c_idx + 1
                            if abs(nxt_c["src_start"] - src_now) > 0.11:
                                self.media_player.set_time(int(nxt_c["src_start"] * 1000))
                            self._apply_active_clip_playback_fx(nxt_c)
                            self._sync_transform_sliders_from_state()
                            src_now = nxt_c["src_start"]
                            tl_now = nxt_c["tl_start"]
                    else:
                        tot_tl = self.nle_project.total_duration
                        self.nle_playhead_sec = tot_tl
                        self.timeline_var.set(tot_tl)
                        if hasattr(self, "davinci_timeline"):
                            self.davinci_timeline.set_playhead(tot_tl)
                        self.pause_playback()
                        return
                else:
                    spd = max(0.25, float(cur_c.get("speed", 1.0)))
                    tl_now = min(cur_c["tl_end"], cur_c["tl_start"] + max(0.0, src_now - cur_c["src_start"]) / spd)
            else:
                tl_now = src_now

            self.nle_playhead_sec = tl_now
            self.timeline_var.set(tl_now)
            if hasattr(self, "davinci_timeline"):
                self.davinci_timeline.set_playhead(tl_now, auto_follow=True)

            self._sync_aux_audio_playback(tl_now, True)

            th_dlg = getattr(self, "_theater_dialog", None)
            if th_dlg is not None and th_dlg.winfo_exists():
                tot_d = self._edited_total_duration() or getattr(self, "media_duration", 0) or 1.0
                th_dlg.update_playback_transport(tl_now, tot_d)

            if getattr(self, "studio_live_preview_mode", False) and hasattr(self, "player_studio_canvas") and self.player_studio_canvas.winfo_ismapped():
                self._request_fast_preview_frame(src_now)

        self._refresh_timeline_text(playhead_only=True)
        self._refresh_play_button()
        th_dlg = getattr(self, "_theater_dialog", None)
        is_th_open = (th_dlg is not None and th_dlg.winfo_exists())
        if not is_th_open and getattr(self, "video_expanded", False):
            self.video_expanded = False
            if hasattr(self, "expand_video_button"):
                is_ar = (self.language_var.get() == "العربية") if hasattr(self, "language_var") else True
                self.expand_video_button.configure(text="⛶ تكبير" if is_ar else "⛶ Fullscreen")
        tick_ms = 33 if (getattr(self, "studio_live_preview_mode", False) and self.input_path and self.input_path.suffix.lower() in convert.VIDEO_EXTS) else 80
        self.playback_tick = self.after(tick_ms, self._schedule_playback_tick)

    def _sync_aux_audio_playback(self, tl_sec: float, is_playing: bool):
        if not vlc or not getattr(self, "vlc_instance", None):
            return
        if not hasattr(self, "aux_audio_player") or self.aux_audio_player is None:
            try:
                self.aux_audio_player = self.vlc_instance.media_player_new()
                self._aux_loaded_path = None
            except Exception:
                self.aux_audio_player = None
                return

        if not is_playing or not hasattr(self, "nle_project"):
            if self.aux_audio_player and self.aux_audio_player.is_playing():
                try:
                    self.aux_audio_player.pause()
                except Exception:
                    pass
            return

        a2_on = self.nle_project.track_enabled.get("A2", True)
        audio_items = getattr(self.nle_project, "audio_items", [])
        if not a2_on or not audio_items:
            if self.aux_audio_player and self.aux_audio_player.is_playing():
                try:
                    self.aux_audio_player.pause()
                except Exception:
                    pass
            return

        # Find active audio item at tl_sec
        active_item = None
        for it in audio_items:
            if not it.get("enabled", True) or it.get("muted", False):
                continue
            s = float(it.get("start_sec", 0.0))
            e = float(it.get("end_sec", s + 10.0))
            if s <= tl_sec < e:
                active_item = it
                break

        if not active_item:
            if self.aux_audio_player and self.aux_audio_player.is_playing():
                try:
                    self.aux_audio_player.pause()
                except Exception:
                    pass
            return

        p = str(active_item.get("audio_path", "")).strip()
        if not p or not Path(p).is_file():
            if self.aux_audio_player and self.aux_audio_player.is_playing():
                try:
                    self.aux_audio_player.pause()
                except Exception:
                    pass
            return

        s_sec = float(active_item.get("start_sec", 0.0))
        offset_ms = int(max(0.0, tl_sec - s_sec) * 1000)
        base_v = float(self.volume_var.get()) if hasattr(self, "volume_var") else 100.0
        item_v = float(active_item.get("volume", 1.0))
        vol_pct = max(0, min(200, int(round(base_v * item_v))))

        try:
            if getattr(self, "_aux_loaded_path", None) != p:
                media = self.vlc_instance.media_new(p)
                self.aux_audio_player.set_media(media)
                self._aux_loaded_path = p
                self.aux_audio_player.play()
                self.aux_audio_player.set_time(offset_ms)
            else:
                cur_t = self.aux_audio_player.get_time()
                if abs(cur_t - offset_ms) > 300:
                    self.aux_audio_player.set_time(offset_ms)
                if not self.aux_audio_player.is_playing():
                    self.aux_audio_player.play()
            self.aux_audio_player.audio_set_volume(vol_pct)
        except Exception:
            pass
