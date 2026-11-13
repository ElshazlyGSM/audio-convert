"""
Video Theater Fullscreen Cinema Dialog
Provides an immersive edge-to-edge fullscreen cinema preview player displaying
all active video edits in real-time WYSIWYG fidelity (Color Grading, DaVinci Pan/Zoom/Transform,
Aspect Ratio framing, Text+ cards, Logo watermarks, Icons/Images, and Subtitles).
Features an interactive bottom scrubber, playback transport, auto-hiding controls,
and zero-lag keyboard/mouse controls.

Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

import math
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from typing import Optional

from PIL import Image, ImageTk

from video_studio.aspect_ratios import (
    render_transformed_pil_frame,
)
from video_studio.color_grading import apply_color_to_image, is_color_neutral
from video_studio.branding import (
    render_text_card_pil,
    apply_opacity_and_rotation,
)
from video_studio.arabic_support import prepare_arabic_for_rendering
from video_studio.icons_library import render_media_overlay_pil


class VideoTheaterDialog(tk.Toplevel):
    """
    True Fullscreen Cinema Video Player Dialog.
    Displays 100% pure video across the entire display with floating, auto-hiding controls.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent
        self.is_ar = getattr(self.app, "language_var", tk.StringVar(value="English")).get() == "العربية"

        # Configure Fullscreen Window
        self.title("🎬 شاشة السينما الكاملة - معاينة المونتاج" if self.is_ar else "🎬 Cinema Fullscreen Preview")
        self.configure(bg="#000000")
        self.attributes("-fullscreen", True)

        self._is_scrubbing = False
        self._hide_timer = None
        self._last_mouse_move = time.monotonic()
        self._cached_photo = None
        self._overlay_photos = []
        self._box_coords = (0, 0, 0, 0)
        self._last_rendered_ts = -999.0

        # Create Cinema Video Canvas
        self.canvas = tk.Canvas(self, bg="#000000", highlightthickness=0, cursor="arrow")
        self.canvas.pack(fill="both", expand=True)

        # Build Floating Bottom Control Bar
        self._build_floating_controls()

        # Bind Key and Mouse Events
        self.bind("<Escape>", lambda _e: self.close())
        self.bind("<space>", lambda _e: self._toggle_play())
        self.bind("<Left>", lambda _e: self._seek_relative(-5))
        self.bind("<Right>", lambda _e: self._seek_relative(5))
        self.bind("<Home>", lambda _e: self._seek_to(0.0))
        self.bind("<End>", lambda _e: self._seek_to(self._total_duration()))
        self.bind("f", lambda _e: self.close())
        self.bind("F", lambda _e: self.close())

        self.canvas.bind("<Double-Button-1>", lambda _e: self.close())
        self.canvas.bind("<Button-1>", lambda _e: self._toggle_play())
        self.canvas.bind("<Motion>", self._on_user_activity)
        self.bar.bind("<Motion>", self._on_user_activity)

        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Notify app
        self.app._theater_dialog = self
        self.app.video_expanded = True
        if hasattr(self.app, "expand_video_button"):
            self.app.expand_video_button.configure(text="✕ تصغير" if self.is_ar else "✕ Exit Full")

        # Initial Render
        self.after(50, self.refresh_preview)
        self._schedule_auto_hide_check()

    # -------------------------------------------------------------------------
    # Floating Controls UI
    # -------------------------------------------------------------------------
    def _build_floating_controls(self):
        # Translucent/Dark floating pill bar
        self.bar = tk.Frame(
            self,
            bg="#0d1117",
            highlightbackground="#30363d",
            highlightthickness=1,
            padx=14,
            pady=8,
        )
        self.bar.place(relx=0.5, rely=0.93, anchor="center", relwidth=0.92, height=76)

        # 1. Interactive Timeline Scrubber (Top Row)
        self.scrub_canvas = tk.Canvas(
            self.bar,
            bg="#161b22",
            height=12,
            highlightthickness=0,
            cursor="hand2",
        )
        self.scrub_canvas.pack(fill="x", pady=(0, 6))
        self.scrub_canvas.bind("<ButtonPress-1>", self._on_scrub_start)
        self.scrub_canvas.bind("<B1-Motion>", self._on_scrub_drag)
        self.scrub_canvas.bind("<ButtonRelease-1>", self._on_scrub_end)
        self.scrub_canvas.bind("<Motion>", self._on_scrub_hover)
        self.scrub_canvas.bind("<Leave>", self._on_scrub_leave)

        # 2. Control Buttons & Status Row
        btn_row = tk.Frame(self.bar, bg="#0d1117")
        btn_row.pack(fill="x", expand=True)

        # Transport Buttons (Play, Skip, Rewind, Start, End)
        self.btn_play = tk.Button(
            btn_row,
            text="⏸" if self.app._is_playing() else "▶",
            command=self._toggle_play,
            bg="#238636",
            fg="#ffffff",
            activebackground="#2ea043",
            activeforeground="#ffffff",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=3,
            cursor="hand2",
        )
        self.btn_play.pack(side="left", padx=(0, 6))

        self.btn_rewind = tk.Button(
            btn_row,
            text="⏪ 5s",
            command=lambda: self._seek_relative(-5),
            bg="#21262d",
            fg="#c9d1d9",
            activebackground="#30363d",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=6,
            cursor="hand2",
        )
        self.btn_rewind.pack(side="left", padx=(0, 4))

        self.btn_forward = tk.Button(
            btn_row,
            text="⏩ 5s",
            command=lambda: self._seek_relative(5),
            bg="#21262d",
            fg="#c9d1d9",
            activebackground="#30363d",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=6,
            cursor="hand2",
        )
        self.btn_forward.pack(side="left", padx=(0, 8))

        # Timecode Label
        self.lbl_timecode = tk.Label(
            btn_row,
            text="00:00:00 / 00:00:00",
            bg="#0d1117",
            fg="#58a6ff",
            font=("Consolas", 11, "bold"),
        )
        self.lbl_timecode.pack(side="left", padx=(4, 12))

        # Active Effects Badge Row (Center)
        self.lbl_badges = tk.Label(
            btn_row,
            text=self._get_active_effects_badge_text(),
            bg="#0d1117",
            fg="#7ee787",
            font=("Segoe UI", 9, "bold"),
        )
        self.lbl_badges.pack(side="left", expand=True)

        # Right-side Buttons: Mute/Volume & Exit Fullscreen
        self.btn_exit = tk.Button(
            btn_row,
            text="✕ خروج (Esc)" if self.is_ar else "✕ Exit (Esc)",
            command=self.close,
            bg="#b62324",
            fg="#ffffff",
            activebackground="#cf222e",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            cursor="hand2",
        )
        self.btn_exit.pack(side="right", padx=(6, 0))

        vol_text = "🔊" if float(getattr(self.app, "volume_var", tk.StringVar(value="80")).get() or 80) > 0 else "🔇"
        self.btn_mute = tk.Button(
            btn_row,
            text=vol_text,
            command=self._toggle_mute,
            bg="#21262d",
            fg="#c9d1d9",
            activebackground="#30363d",
            font=("Segoe UI", 10),
            relief="flat",
            padx=6,
            cursor="hand2",
        )
        self.btn_mute.pack(side="right", padx=(0, 6))

    # -------------------------------------------------------------------------
    # Active Effects Badges
    # -------------------------------------------------------------------------
    def _get_active_effects_badge_text(self) -> str:
        parts = []
        is_ar = self.is_ar

        # Aspect Ratio
        ratio = getattr(self.app, "trim_aspect_var", tk.StringVar(value="original")).get()
        if ratio != "original":
            parts.append(f"📐 {ratio}")

        # Color Grading
        cfg = getattr(self.app, "video_branding_config", {}).get("color_config", {})
        if isinstance(cfg, dict) and cfg.get("enabled", True) and not is_color_neutral(cfg):
            parts.append("🎨 " + ("ألوان حية" if is_ar else "Color Grading"))

        # Logo
        if hasattr(self.app, "nle_project") and self.app.nle_project.logo_items:
            parts.append("🏷️ " + ("لوجو" if is_ar else "Logo"))
        elif getattr(self.app, "video_branding_config", {}).get("logo_enabled"):
            parts.append("🏷️ " + ("لوجو" if is_ar else "Logo"))

        # Text+ Cards
        if hasattr(self.app, "nle_project") and self.app.nle_project.text_items:
            parts.append("📝 " + ("نصوص" if is_ar else "Titles"))

        # Icons / Badges
        if hasattr(self.app, "nle_project") and self.app.nle_project.media_items:
            parts.append("🖼️ " + ("أيقونات" if is_ar else "Overlays"))

        # Subtitles
        if getattr(self.app, "trim_burn_subs_var", tk.BooleanVar(value=False)).get():
            parts.append("💬 " + ("ترجمة" if is_ar else "Subtitles"))

        # Clips
        if hasattr(self.app, "nle_project") and len(self.app.nle_project.clips) > 1:
            parts.append(f"✂️ {len(self.app.nle_project.clips)} " + ("مقاطع" if is_ar else "Clips"))

        if not parts:
            return "🎬 " + ("معاينة سينمائية مطابقة 100% للتصدير" if is_ar else "100% WYSIWYG Final Export Preview")
        return " | ".join(parts)

    # -------------------------------------------------------------------------
    # Auto-Hide Behavior
    # -------------------------------------------------------------------------
    def _on_user_activity(self, _event=None):
        self._last_mouse_move = time.monotonic()
        if not self.bar.winfo_ismapped():
            self.bar.place(relx=0.5, rely=0.93, anchor="center", relwidth=0.92, height=76)
            self.canvas.configure(cursor="arrow")

    def _schedule_auto_hide_check(self):
        if not self.winfo_exists():
            return
        now = time.monotonic()
        if (
            self.app._is_playing()
            and not self._is_scrubbing
            and now - self._last_mouse_move >= 2.5
            and self.bar.winfo_ismapped()
        ):
            self.bar.place_forget()
            self.canvas.configure(cursor="none")
        self.after(300, self._schedule_auto_hide_check)

    # -------------------------------------------------------------------------
    # Canvas Geometry & Drawing
    # -------------------------------------------------------------------------
    def _on_canvas_configure(self, _event=None):
        self.refresh_preview()

    def _current_timeline_seconds(self) -> float:
        return float(getattr(self.app, "nle_playhead_sec", 0.0) or 0.0)

    def _total_duration(self) -> float:
        if hasattr(self.app, "_edited_total_duration"):
            tot = self.app._edited_total_duration()
            if tot and tot > 0:
                return float(tot)
        if getattr(self.app, "media_duration", 0) > 0:
            return float(self.app.media_duration)
        return 1.0

    def refresh_preview(self):
        """Paints the current composite video frame onto the theater canvas."""
        if not self.winfo_exists():
            return

        cw = max(100, self.canvas.winfo_width())
        ch = max(100, self.canvas.winfo_height())
        tl_sec = self._current_timeline_seconds()
        tot_dur = max(0.1, self._total_duration())

        # Update Scrubber & Timecode
        self._draw_scrubber(tl_sec, tot_dur)
        self._update_timecode_text(tl_sec, tot_dur)
        self.btn_play.configure(text="⏸" if self.app._is_playing() else "▶")
        self.lbl_badges.configure(text=self._get_active_effects_badge_text())

        # Fetch decoded source frame
        vpath = getattr(self.app, "input_path", None)
        if not vpath or not Path(vpath).is_file():
            self.canvas.delete("all")
            self.canvas.create_text(
                cw // 2, ch // 2,
                text="🎬 لا يوجد فيديو محمل حالياً" if self.is_ar else "🎬 No video loaded",
                fill="#6e7681", font=("Segoe UI", 16, "bold"),
            )
            return

        # Determine target aspect ratio
        ratio_key = getattr(self.app, "trim_aspect_var", tk.StringVar(value="original")).get()
        aspect_Lookup = {
            "9:16": 9.0 / 16.0,
            "1:1": 1.0,
            "4:5": 4.0 / 5.0,
            "4:3": 4.0 / 3.0,
            "16:9": 16.0 / 9.0,
        }

        # Source frame extraction (High resolution 1920 max dim for theater)
        c_idx, cur_clip, src_sec = (
            self.app.nle_project.timeline_to_source(tl_sec)
            if hasattr(self.app, "nle_project")
            else (0, None, tl_sec)
        )
        frame = self.app.fast_preview.get_frame(vpath, src_sec, max_dim=1920) if hasattr(self.app, "fast_preview") else None

        if frame is not None:
            src_aspect = frame.width / max(1, frame.height)
        elif getattr(self.app, "media_width", 0) and getattr(self.app, "media_height", 0):
            src_aspect = float(self.app.media_width) / max(1.0, float(self.app.media_height))
        else:
            src_aspect = 16.0 / 9.0

        target_aspect = aspect_Lookup.get(ratio_key, src_aspect)

        # Calculate bounding box (fill screen preserving aspect ratio)
        box_h = ch
        box_w = max(24, int(round(box_h * target_aspect)))
        if box_w > cw:
            box_w = cw
            box_h = max(24, int(round(box_w / target_aspect)))

        vx0 = (cw - box_w) // 2
        vy0 = (ch - box_h) // 2
        vx1 = vx0 + box_w
        vy1 = vy0 + box_h
        self._box_coords = (vx0, vy0, vx1, vy1)

        self.canvas.delete("all")
        self._overlay_photos.clear()

        # Cinema black background
        self.canvas.create_rectangle(0, 0, cw, ch, fill="#000000", outline="")

        in_gap = bool(hasattr(self.app, "nle_project") and self.app.nle_project.clips and cur_clip is None)
        if in_gap:
            self.canvas.create_rectangle(vx0, vy0, vx1, vy1, fill="#05070a", outline="")
            self.canvas.create_text(
                (vx0 + vx1) // 2, (vy0 + vy1) // 2,
                text="↔ فجوة صامتة" if self.is_ar else "↔ Timeline Gap",
                fill="#388bfd", font=("Segoe UI", 18, "bold"),
            )
            return

        if frame is None:
            self.canvas.create_rectangle(vx0, vy0, vx1, vy1, fill="#0a0e17", outline="")
            self.canvas.create_text(
                (vx0 + vx1) // 2, (vy0 + vy1) // 2,
                text="⏳ جاري تحميل الإطار بالدقة الكاملة..." if self.is_ar else "⏳ Loading full resolution frame...",
                fill="#8b949e", font=("Segoe UI", 14),
            )
            return

        # 1. Video Frame with Color Grading & Pan/Zoom/Transform
        fit_mode = self.app.video_branding_config.get("fit_mode", "crop")
        xf = self.app._get_effective_video_transform(c_idx) if hasattr(self.app, "_get_effective_video_transform") else {
            "zoom": 1.0, "pan_x": 0.0, "pan_y": 0.0, "flip_h": False, "clamp_edges": True
        }
        color_cfg = self.app.video_branding_config.get("color_config", {})
        color_on = bool(
            isinstance(color_cfg, dict)
            and color_cfg.get("enabled", True)
            and not is_color_neutral(color_cfg)
        )

        work_im = apply_color_to_image(frame, color_cfg) if color_on else frame
        comp_im = render_transformed_pil_frame(
            work_im,
            box_w,
            box_h,
            fit_mode=fit_mode,
            zoom=xf["zoom"],
            pan_x=xf["pan_x"],
            pan_y=xf["pan_y"],
            flip_h=xf["flip_h"],
            clamp_edges=xf["clamp_edges"],
        )

        self._cached_photo = ImageTk.PhotoImage(comp_im)
        self.canvas.create_image(vx0, vy0, anchor="nw", image=self._cached_photo)

        # 2. Track V2: Icons & Custom Images
        if hasattr(self.app, "nle_project") and self.app.nle_project.track_enabled.get("V2", True):
            for idx, m_item in enumerate(self.app.nle_project.media_items):
                if not self.app.nle_project.is_item_visible_at("V2", m_item, tl_sec):
                    continue
                try:
                    ov_im = render_media_overlay_pil(m_item, box_w, box_h, is_ar=self.is_ar)
                    if ov_im is not None:
                        photo = ImageTk.PhotoImage(ov_im)
                        self._overlay_photos.append(photo)
                        cx = vx0 + int(round(box_w * float(m_item.get("x", 0.5))))
                        cy = vy0 + int(round(box_h * float(m_item.get("y", 0.5))))
                        iw, ih = ov_im.size
                        self.canvas.create_image(cx - iw // 2, cy - ih // 2, anchor="nw", image=photo)
                except Exception:
                    pass

        # 3. Track V3: Text+ Cards & Titles
        if hasattr(self.app, "nle_project") and self.app.nle_project.track_enabled.get("V3", True):
            for idx, t_item in enumerate(self.app.nle_project.text_items):
                if not self.app.nle_project.is_item_visible_at("V3", t_item, tl_sec):
                    continue
                raw_text = str(t_item.get("text", "")).strip()
                if not raw_text:
                    continue
                try:
                    card_im = render_text_card_pil(
                        text=raw_text,
                        bg_color_key=t_item.get("bg_color", "black"),
                        text_color_key=t_item.get("text_color", "white"),
                        font_size=max(14, int(t_item.get("font_size", 34) * (box_w / 640.0))),
                        font_name=t_item.get("font_name", "Segoe UI"),
                        video_w=box_w,
                        video_h=box_h,
                        opacity=float(t_item.get("opacity", 1.0)),
                        rotation=float(t_item.get("rotation", 0.0)),
                    )
                    if card_im is not None:
                        photo = ImageTk.PhotoImage(card_im)
                        self._overlay_photos.append(photo)
                        cx = vx0 + int(round(box_w * float(t_item.get("x", 0.5))))
                        cy = vy0 + int(round(box_h * float(t_item.get("y", 0.12))))
                        tw, th = card_im.size
                        self.canvas.create_image(cx - tw // 2, cy - th // 2, anchor="nw", image=photo)
                except Exception:
                    pass

        # 4. Track V4: Logo Watermarks
        if hasattr(self.app, "nle_project") and self.app.nle_project.track_enabled.get("V4", True):
            for idx, l_item in enumerate(self.app.nle_project.logo_items):
                if not self.app.nle_project.is_item_visible_at("V4", l_item, tl_sec):
                    continue
                logo_p = str(l_item.get("path", "")).strip()
                if not logo_p or not Path(logo_p).is_file():
                    continue
                try:
                    l_scale = max(0.04, min(0.85, float(l_item.get("scale", 0.16))))
                    lw = max(32, int(round(box_w * l_scale)))
                    with Image.open(logo_p) as lim:
                        ow, oh = lim.size
                        lh = max(18, int(round(lw * (oh / max(1, ow)))))
                        l_rgba = lim.convert("RGBA").resize((lw, lh), Image.Resampling.LANCZOS)
                    l_im_final = apply_opacity_and_rotation(
                        l_rgba,
                        opacity=float(l_item.get("opacity", 0.85)),
                        rotation_deg=float(l_item.get("rotation", 0.0)),
                    )
                    if l_im_final is not None:
                        photo = ImageTk.PhotoImage(l_im_final)
                        self._overlay_photos.append(photo)
                        fw, fh = l_im_final.size
                        anchor_mode = l_item.get("anchor", "nw")
                        lx_pct = float(l_item.get("x", 0.80))
                        ly_pct = float(l_item.get("y", 0.04))
                        if anchor_mode == "center":
                            lx0 = vx0 + int(round(box_w * lx_pct)) - fw // 2
                            ly0 = vy0 + int(round(box_h * ly_pct)) - fh // 2
                        else:
                            lx0 = vx0 + int(round(box_w * lx_pct))
                            ly0 = vy0 + int(round(box_h * ly_pct))
                        self.canvas.create_image(lx0, ly0, anchor="nw", image=photo)
                except Exception:
                    pass

        # 5. Live Burned Subtitles
        if getattr(self.app, "trim_burn_subs_var", tk.BooleanVar(value=False)).get() and hasattr(self.app, "_get_live_subtitle_at"):
            sub_txt = self.app._get_live_subtitle_at(tl_sec)
            if sub_txt:
                try:
                    sub_y = vy1 - max(28, int(box_h * 0.075))
                    sub_col_key = getattr(self.app, "subtitle_style", {}).get("text_color", "yellow")
                    col_hex = "#FFE600" if sub_col_key == "yellow" else "#FFFFFF"
                    shaped_sub = prepare_arabic_for_rendering(sub_txt)
                    f_sz = max(14, min(28, box_w // 40))
                    stw = min(box_w - 24, max(80, len(shaped_sub) * (f_sz - 2) + 24))
                    self.canvas.create_rectangle(
                        (vx0 + vx1) // 2 - stw // 2, sub_y - f_sz - 4,
                        (vx0 + vx1) // 2 + stw // 2, sub_y + f_sz + 4,
                        fill="#0d1117", outline="#30363d", width=1,
                    )
                    self.canvas.create_text(
                        (vx0 + vx1) // 2, sub_y,
                        text=shaped_sub, fill=col_hex, font=("Segoe UI", f_sz, "bold"),
                    )
                except Exception:
                    pass

    # -------------------------------------------------------------------------
    # Scrubber Bar Drawing & Dragging
    # -------------------------------------------------------------------------
    def _draw_scrubber(self, cur_sec: float, tot_sec: float):
        w = max(10, self.scrub_canvas.winfo_width())
        h = max(6, self.scrub_canvas.winfo_height())
        self.scrub_canvas.delete("all")

        # Track background
        track_y = h // 2
        self.scrub_canvas.create_line(0, track_y, w, track_y, fill="#21262d", width=5)

        # Progress fill
        pct = max(0.0, min(1.0, cur_sec / max(0.1, tot_sec)))
        px = int(round(w * pct))
        if px > 0:
            self.scrub_canvas.create_line(0, track_y, px, track_y, fill="#238636", width=5)

        # Scrubber Head
        r = 6
        self.scrub_canvas.create_oval(px - r, track_y - r, px + r, track_y + r, fill="#58a6ff", outline="#ffffff", width=1.5)

    def _on_scrub_start(self, event):
        self._is_scrubbing = True
        self._on_user_activity()
        self._seek_from_mouse_x(event.x)

    def _on_scrub_drag(self, event):
        if self._is_scrubbing:
            self._on_user_activity()
            self._seek_from_mouse_x(event.x)

    def _on_scrub_end(self, event):
        if self._is_scrubbing:
            self._is_scrubbing = False
            self._on_user_activity()
            self._seek_from_mouse_x(event.x)

    def _on_scrub_hover(self, event):
        w = max(10, self.scrub_canvas.winfo_width())
        pct = max(0.0, min(1.0, event.x / float(w)))
        hover_sec = pct * self._total_duration()
        self.scrub_canvas.delete("hover_pip")
        self.scrub_canvas.create_oval(event.x - 3, 3, event.x + 3, 9, fill="#f0883e", outline="", tags="hover_pip")

    def _on_scrub_leave(self, _event=None):
        self.scrub_canvas.delete("hover_pip")

    def _seek_from_mouse_x(self, mx: int):
        w = max(10, self.scrub_canvas.winfo_width())
        pct = max(0.0, min(1.0, float(mx) / float(w)))
        target_s = pct * self._total_duration()
        self._seek_to(target_s)

    # -------------------------------------------------------------------------
    # Playback Controls & Timeline Sync
    # -------------------------------------------------------------------------
    def _toggle_play(self):
        self._on_user_activity()
        if hasattr(self.app, "toggle_play_pause"):
            self.app.toggle_play_pause()
        self.btn_play.configure(text="⏸" if self.app._is_playing() else "▶")
        self.refresh_preview()

    def _seek_relative(self, delta_s: float):
        self._on_user_activity()
        cur = self._current_timeline_seconds()
        self._seek_to(cur + delta_s)

    def _seek_to(self, target_sec: float):
        tot = self._total_duration()
        target_sec = max(0.0, min(tot, float(target_sec)))
        if hasattr(self.app, "seek_timeline_to"):
            self.app.seek_timeline_to(target_sec)
        else:
            self.app.nle_playhead_sec = target_sec
            if hasattr(self.app, "timeline_var"):
                self.app.timeline_var.set(target_sec)
            if hasattr(self.app, "davinci_timeline"):
                self.app.davinci_timeline.set_playhead(target_sec, auto_follow=True)
            if hasattr(self.app, "_request_fast_preview_frame"):
                c_idx, _c, src_s = (
                    self.app.nle_project.timeline_to_source(target_sec)
                    if hasattr(self.app, "nle_project")
                    else (0, None, target_sec)
                )
                self.app._request_fast_preview_frame(src_s, force=True)

        self.refresh_preview()

    def _toggle_mute(self):
        self._on_user_activity()
        cur_vol = float(getattr(self.app, "volume_var", tk.StringVar(value="80")).get() or 80)
        if cur_vol > 0:
            self._prev_vol = cur_vol
            self.app.volume_var.set("0")
            self.btn_mute.configure(text="🔇")
        else:
            prev = getattr(self, "_prev_vol", 80)
            self.app.volume_var.set(str(int(prev)))
            self.btn_mute.configure(text="🔊")
        if hasattr(self.app, "_apply_active_clip_playback_fx"):
            self.app._apply_active_clip_playback_fx()

    def _update_timecode_text(self, cur_s: float, tot_s: float):
        def _fmt(s):
            s = max(0.0, float(s))
            h = int(s // 3600)
            m = int((s % 3600) // 60)
            sec = int(s % 60)
            if h > 0:
                return f"{h:02d}:{m:02d}:{sec:02d}"
            return f"{m:02d}:{sec:02d}"

        self.lbl_timecode.configure(text=f"{_fmt(cur_s)} / {_fmt(tot_s)}")

    # -------------------------------------------------------------------------
    # Close & Return to Editor
    # -------------------------------------------------------------------------
    def close(self):
        """Exits fullscreen cleanly and restores main editor UI."""
        self.app._theater_dialog = None
        self.app.video_expanded = False
        is_ar = self.is_ar
        if hasattr(self.app, "expand_video_button"):
            self.app.expand_video_button.configure(text="⛶ تكبير" if is_ar else "⛶ Fullscreen")
        try:
            self.destroy()
        except Exception:
            pass
        # Refresh main editor view
        if hasattr(self.app, "_show_studio_canvas"):
            self.app._show_studio_canvas()
        if hasattr(self.app, "_sync_live_video_overlay"):
            self.app._sync_live_video_overlay()
