"""
Master Video Filter Compositor & Multi-Track DaVinci NLE Exporter
Combines Aspect Ratio (9:16 Reels/Shorts), DaVinci Free Pan/Zoom Transform, Multi-Clip Timeline Cuts,
Blur Background, Pro Icons & Custom Images (V2), Text+ Cards (V3), Logo Watermarks (V4),
Color Grading, Silence Removal, and Subtitles into a unified FFmpeg pipeline.
Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_HW_ENCODER_CACHE: Dict[Tuple[str, bool], str] = {}


def detect_best_video_encoder(
    ffmpeg_exe: str = "ffmpeg",
    is_hevc: bool = False,
    user_codec: Optional[str] = "auto",
) -> str:
    """
    Auto-detects the fastest available hardware-accelerated video encoder supported
    by the user's GPU and FFmpeg binary.
    Prioritizes:
      1. Windows Media Foundation GPU (h264_mf) - zero overhead, instant start
      2. Intel QuickSync (h264_qsv / hevc_qsv)
      3. NVIDIA NVENC (h264_nvenc / hevc_nvenc)
      4. AMD AMF (h264_amf / hevc_amf)
      5. Fallback: Optimized CPU (libx264 / libx265 with veryfast)
    """
    if user_codec and user_codec not in ("auto", "default", None):
        return user_codec

    cache_key = (str(ffmpeg_exe), bool(is_hevc))
    if cache_key in _HW_ENCODER_CACHE:
        return _HW_ENCODER_CACHE[cache_key]

    candidates = (
        ["hevc_qsv", "hevc_nvenc", "hevc_amf", "hevc_mf"]
        if is_hevc
        else ["h264_mf", "h264_qsv", "h264_nvenc", "h264_amf"]
    )

    detected_enc = None
    for cand in candidates:
        try:
            test_cmd = [
                str(ffmpeg_exe),
                "-y",
                "-hide_banner",
                "-loglevel", "error",
                "-nostdin",
                "-f", "lavfi",
                "-i", "nullsrc=s=128x128:d=0.04",
                "-c:v", cand,
                "-frames:v", "1",
                "-f", "null", "-",
            ]
            res = subprocess.run(
                test_cmd,
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if res.returncode == 0:
                detected_enc = cand
                break
        except Exception:
            continue

    if not detected_enc:
        detected_enc = "libx265" if is_hevc else "libx264"

    _HW_ENCODER_CACHE[cache_key] = detected_enc
    logger.info("Export video encoder selected: %s (is_hevc=%s)", detected_enc, is_hevc)
    return detected_enc

from PIL import Image

from .aspect_ratios import build_aspect_ratio_filter, get_aspect_ratio_dimensions
from .branding import (
    generate_text_overlay_image,
    build_logo_overlay_filter,
    build_free_logo_overlay_filter,
    build_timed_rgba_overlay_filter,
)
from .icons_library import (
    apply_opacity_and_rotation,
    render_media_overlay_pil,
)
from .subtitle_style import build_subtitle_style_string
from .color_grading import (
    build_ffmpeg_color_filter,
    is_color_neutral,
)
from .transitions import build_xfade_filter_chains
from .silence_remover import (
    build_silence_filter_expressions,
    detect_silences,
    parse_and_remap_srt_file,
)
try:
    from convert import CancelledError
except ImportError:
    class CancelledError(Exception):
        pass



def _build_atempo_chain(speed: float) -> str:
    spd = max(0.25, min(4.0, float(speed or 1.0)))
    if abs(spd - 1.0) <= 0.01:
        return ""
    parts = []
    rem = spd
    while rem > 2.0:
        parts.append("atempo=2.0")
        rem /= 2.0
    while rem < 0.5:
        parts.append("atempo=0.5")
        rem /= 0.5
    parts.append(f"atempo={rem:.4f}")
    return ",".join(parts)


def _append_post_transform_overlays(
    cur_label: str,
    step: int,
    canvas_w: int,
    canvas_h: int,
    color_config: Optional[Dict[str, Any]],
    media_overlays: Optional[List[Dict[str, Any]]],
    title_config: Optional[Dict[str, Any]],
    logo_config: Optional[Dict[str, Any]],
    logo_items: Optional[List[Dict[str, Any]]],
    subtitle_config: Optional[Dict[str, Any]],
    active_keep_intervals: Optional[List[Any]],
    sil_mode: str,
    sil_speed: int,
    t_dir: Path,
    is_ar: bool = True,
):
    """
    Appends Color Grading, V2 Media Overlays (Icons & Images), V3 Text+ Overlays,
    V4 Logo Watermarks, and Burned Subtitles onto cur_label.
    Returns: (filter_chains_list, final_cur_label, next_step, temp_files_list)
    """
    chains: List[str] = []
    temp_files: List[Path] = []
    stamp = int(time.time() * 1000)

    # 1. Color Correction & Grading
    if color_config and not is_color_neutral(color_config):
        next_label = f"v_cur_{step}"
        c_filter = build_ffmpeg_color_filter(
            config=color_config,
            input_label=cur_label,
            output_label=next_label,
        )
        chains.append(c_filter)
        cur_label = next_label
        step += 1

    # 2. Track V2: Media Overlays (Built-in Pro Icons, Badges & Custom Images)
    if media_overlays:
        for m_idx, m_item in enumerate(media_overlays):
            if not m_item.get("enabled", True):
                continue
            pil_ov = render_media_overlay_pil(m_item, canvas_w, canvas_h, is_ar=is_ar)
            if pil_ov is None:
                continue
            ov_png = t_dir / f"v2_media_{m_idx}_{stamp}_{step}.png"
            pil_ov.save(str(ov_png), "PNG")
            temp_files.append(ov_png)

            next_label = f"v_cur_{step}"
            ov_filter = build_timed_rgba_overlay_filter(
                image_path=ov_png,
                x_pct=float(m_item.get("x", 0.5)),
                y_pct=float(m_item.get("y", 0.5)),
                video_w=canvas_w,
                video_h=canvas_h,
                img_w=pil_ov.width,
                img_h=pil_ov.height,
                anchor="center",
                start_sec=m_item.get("start_sec"),
                end_sec=m_item.get("end_sec"),
                full_duration=bool(m_item.get("full_duration", False)),
                stream_id=f"ov_m_{step}",
                input_label=cur_label,
                output_label=next_label,
            )
            chains.append(ov_filter)
            cur_label = next_label
            step += 1

    # 3. Track V3: Text+ Overlays
    items_to_render = []
    if title_config:
        if "text_items" in title_config and isinstance(title_config["text_items"], list):
            items_to_render = [
                item for item in title_config["text_items"]
                if item.get("enabled", True) and str(item.get("text", "")).strip()
            ]
        elif title_config.get("enabled") and str(title_config.get("text", "")).strip():
            items_to_render = [{
                "text": title_config.get("text"),
                "x": title_config.get("x_pct", 0.5),
                "y": 0.08 if title_config.get("position", "top") == "top" else 0.88,
                "bg_color": title_config.get("bg_color", "black"),
                "text_color": title_config.get("text_color", "white"),
                "font_size": title_config.get("font_size", 34),
                "font_name": title_config.get("font_name", "Segoe UI"),
                "opacity": 1.0,
                "rotation": 0.0,
                "full_duration": True,
            }]

    for idx, t_item in enumerate(items_to_render):
        banner_png = t_dir / f"v3_text_{idx}_{stamp}_{step}.png"
        gen_ok, cw, ch = generate_text_overlay_image(
            text=t_item.get("text"),
            output_path=banner_png,
            bg_color_key=t_item.get("bg_color", "black"),
            text_color_key=t_item.get("text_color", "white"),
            font_size=t_item.get("font_size", 34),
            font_name=t_item.get("font_name", "Segoe UI"),
            video_w=canvas_w,
            video_h=canvas_h,
            opacity=t_item.get("opacity", 1.0),
            rotation=t_item.get("rotation", 0.0),
        )
        if gen_ok and banner_png.exists():
            temp_files.append(banner_png)
            next_label = f"v_cur_{step}"
            b_filter = build_timed_rgba_overlay_filter(
                image_path=banner_png,
                x_pct=float(t_item.get("x_pct", t_item.get("x", 0.5))),
                y_pct=float(t_item.get("y_pct", t_item.get("y", 0.1))),
                video_w=canvas_w,
                video_h=canvas_h,
                img_w=cw,
                img_h=ch,
                anchor="center",
                start_sec=t_item.get("start_sec"),
                end_sec=t_item.get("end_sec"),
                full_duration=bool(t_item.get("full_duration", True)),
                stream_id=f"ov_t_{step}",
                input_label=cur_label,
                output_label=next_label,
            )
            chains.append(b_filter)
            cur_label = next_label
            step += 1

    # 4. Track V4: Logo Watermarks (supports timeline logo_items list OR legacy logo_config)
    rendered_any_logo_item = False
    if logo_items:
        for l_idx, l_item in enumerate(logo_items):
            if not l_item.get("enabled", True):
                continue
            lp = Path(str(l_item.get("path", "")).strip())
            if not lp.is_file():
                continue
            try:
                scale_r = max(0.03, min(0.95, float(l_item.get("scale", 0.16))))
                tw = max(28, int(round(canvas_w * scale_r)))
                with Image.open(lp) as lim:
                    ow, oh = lim.size
                    th = max(16, int(round(tw * (oh / max(1, ow)))))
                    l_rgba = lim.convert("RGBA").resize((tw, th), Image.Resampling.LANCZOS)
                l_final = apply_opacity_and_rotation(
                    l_rgba,
                    opacity=float(l_item.get("opacity", 0.85)),
                    rotation_deg=float(l_item.get("rotation", 0.0)),
                )
                l_png = t_dir / f"v4_logo_{l_idx}_{stamp}_{step}.png"
                l_final.save(str(l_png), "PNG")
                temp_files.append(l_png)

                next_label = f"v_cur_{step}"
                anchor_mode = l_item.get("anchor", "nw")
                lf = build_timed_rgba_overlay_filter(
                    image_path=l_png,
                    x_pct=float(l_item.get("x", l_item.get("x_pct", 0.82))),
                    y_pct=float(l_item.get("y", l_item.get("y_pct", 0.04))),
                    video_w=canvas_w,
                    video_h=canvas_h,
                    img_w=l_final.width,
                    img_h=l_final.height,
                    anchor=anchor_mode,
                    start_sec=l_item.get("start_sec"),
                    end_sec=l_item.get("end_sec"),
                    full_duration=bool(l_item.get("full_duration", True)),
                    stream_id=f"ov_l_{step}",
                    input_label=cur_label,
                    output_label=next_label,
                )
                chains.append(lf)
                cur_label = next_label
                step += 1
                rendered_any_logo_item = True
            except Exception:
                pass

    if not rendered_any_logo_item and logo_config and logo_config.get("enabled") and logo_config.get("path"):
        l_path = Path(logo_config["path"])
        if l_path.exists():
            next_label = f"v_cur_{step}"
            rot = float(logo_config.get("rotation", 0.0))
            if abs(rot) > 0.25:
                try:
                    scale_r = max(0.03, min(0.95, float(logo_config.get("scale", 0.15))))
                    tw = max(28, int(round(canvas_w * scale_r)))
                    with Image.open(l_path) as lim:
                        ow, oh = lim.size
                        th = max(16, int(round(tw * (oh / max(1, ow)))))
                        l_rgba = lim.convert("RGBA").resize((tw, th), Image.Resampling.LANCZOS)
                    l_final = apply_opacity_and_rotation(l_rgba, opacity=float(logo_config.get("opacity", 0.85)), rotation_deg=rot)
                    l_png = t_dir / f"v4_logo_rot_{stamp}_{step}.png"
                    l_final.save(str(l_png), "PNG")
                    temp_files.append(l_png)
                    l_filter = build_timed_rgba_overlay_filter(
                        image_path=l_png,
                        x_pct=float(logo_config.get("x_pct", 0.85)),
                        y_pct=float(logo_config.get("y_pct", 0.05)),
                        video_w=canvas_w,
                        video_h=canvas_h,
                        img_w=l_final.width,
                        img_h=l_final.height,
                        anchor="nw",
                        start_sec=logo_config.get("start_sec"),
                        end_sec=logo_config.get("end_sec"),
                        full_duration=bool(logo_config.get("full_duration", True)),
                        stream_id=f"ov_lr_{step}",
                        input_label=cur_label,
                        output_label=next_label,
                    )
                except Exception:
                    l_filter = f"[{cur_label}]null[{next_label}]"
            elif "x_pct" in logo_config and "y_pct" in logo_config:
                l_filter = build_free_logo_overlay_filter(
                    logo_path=l_path,
                    x_pct=logo_config.get("x_pct", 0.85),
                    y_pct=logo_config.get("y_pct", 0.05),
                    scale_ratio=logo_config.get("scale", 0.15),
                    opacity=logo_config.get("opacity", 0.85),
                    video_w=canvas_w,
                    video_h=canvas_h,
                    input_label=cur_label,
                    output_label=next_label,
                    start_sec=logo_config.get("start_sec"),
                    end_sec=logo_config.get("end_sec"),
                    full_duration=bool(logo_config.get("full_duration", True)),
                )
            else:
                l_filter = build_logo_overlay_filter(
                    logo_path=l_path,
                    position=logo_config.get("position", "top_right"),
                    scale_ratio=logo_config.get("scale", 0.15),
                    opacity=logo_config.get("opacity", 0.85),
                    margin=logo_config.get("margin", 30),
                    video_w=canvas_w,
                    video_h=canvas_h,
                    input_label=cur_label,
                    output_label=next_label,
                )
            chains.append(l_filter)
            cur_label = next_label
            step += 1

    # 5. Subtitle Burning (if enabled)
    if subtitle_config and subtitle_config.get("enabled") and subtitle_config.get("srt_path"):
        s_path = Path(subtitle_config["srt_path"])
        if s_path.exists() and s_path.stat().st_size > 0:
            if active_keep_intervals and sil_mode in ("remove", "fast_forward"):
                remapped_srt = t_dir / f"remapped_subs_{stamp}.srt"
                s_path = parse_and_remap_srt_file(
                    srt_path=s_path,
                    keep_intervals=active_keep_intervals,
                    output_srt_path=remapped_srt,
                    mode=sil_mode,
                    speed_factor=sil_speed,
                )
                if remapped_srt.exists():
                    temp_files.append(remapped_srt)
            srt_esc = str(s_path).replace("\\", "/").replace(":", r"\:")
            style_dict = subtitle_config.get("style") if isinstance(subtitle_config.get("style"), dict) else subtitle_config
            style_str = build_subtitle_style_string(
                font_name=style_dict.get("font_name", "Segoe UI"),
                font_size=style_dict.get("font_size", None),
                text_color=style_dict.get("text_color", "yellow"),
                outline_style=style_dict.get("outline_style", "box_semi"),
                bold=style_dict.get("bold", True),
                italic=style_dict.get("italic", False),
                position_v=style_dict.get("position_v", "bottom"),
                position_h=style_dict.get("position_h", "center"),
                margin_v=style_dict.get("margin_v", None),
                video_h=canvas_h,
            )
            next_label = f"v_cur_{step}"
            sub_filter = f"[{cur_label}]subtitles='{srt_esc}':force_style='{style_str}'[{next_label}]"
            chains.append(sub_filter)
            cur_label = next_label
            step += 1

    return chains, cur_label, step, temp_files


def build_composite_video_filter(
    in_w=1920,
    in_h=1080,
    aspect_ratio="original",
    fit_mode="crop",
    video_transform=None,
    color_config=None,
    media_overlays=None,
    logo_config=None,
    logo_items=None,
    title_config=None,
    subtitle_config=None,
    silence_config=None,
    temp_dir=None,
    input_label="0:v",
    final_output_label="outv",
    is_ar=True,
):
    """
    Constructs a complete single-pass FFmpeg filter_complex string.
    Returns: (filter_str, final_w, final_h, temp_files_created)
    """
    filter_chains = []

    t_dir = Path(temp_dir or Path.home())
    t_dir.mkdir(parents=True, exist_ok=True)

    # 0. Silence Cut / Fast-Forward on Video Stream (if enabled)
    active_keep_intervals = None
    sil_mode = "remove"
    sil_speed = 4
    if silence_config and silence_config.get("enabled") and silence_config.get("keep_intervals"):
        active_keep_intervals = silence_config["keep_intervals"]
        sil_mode = silence_config.get("mode", "remove")
        sil_speed = silence_config.get("speed_factor", 4)
        v_sil_expr, _ = build_silence_filter_expressions(
            keep_intervals=active_keep_intervals,
            mode=sil_mode,
            speed_factor=sil_speed,
        )
        if v_sil_expr:
            filter_chains.append(f"[{input_label}]{v_sil_expr}[v_sil_0]")
            input_label = "v_sil_0"

    # 1. Aspect Ratio & DaVinci Transform (Zoom, Pan X/Y, Flip)
    ratio_str, canvas_w, canvas_h = build_aspect_ratio_filter(
        target_ratio=aspect_ratio,
        fit_mode=fit_mode,
        in_w=in_w,
        in_h=in_h,
        input_label=input_label,
        output_label="v_cur_0",
        video_transform=video_transform,
    )
    filter_chains.append(ratio_str)
    cur_label = "v_cur_0"
    step = 1

    post_chains, cur_label, step, temp_files = _append_post_transform_overlays(
        cur_label=cur_label,
        step=step,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        color_config=color_config,
        media_overlays=media_overlays,
        title_config=title_config,
        logo_config=logo_config,
        logo_items=logo_items,
        subtitle_config=subtitle_config,
        active_keep_intervals=active_keep_intervals,
        sil_mode=sil_mode,
        sil_speed=sil_speed,
        t_dir=t_dir,
        is_ar=is_ar,
    )
    filter_chains.extend(post_chains)

    # Ensure standard yuv420p output for universal player & social platform compatibility
    filter_chains.append(f"[{cur_label}]format=yuv420p[{final_output_label}]")

    clean_chains = [c.rstrip(" ;") for c in filter_chains if c and c.strip()]
    composite_filter_str = ";".join(clean_chains)
    return composite_filter_str, canvas_w, canvas_h, temp_files


def export_styled_video(
    video_path,
    output_path=None,
    output_dir=None,
    start_seconds=None,
    end_seconds=None,
    duration_seconds=None,
    aspect_ratio="original",
    fit_mode="crop",
    video_transform=None,
    nle_clips=None,
    media_overlays=None,
    logo_items=None,
    color_config=None,
    transitions_config=None,
    logo_config=None,
    title_config=None,
    subtitle_config=None,
    silence_config=None,
    audio_enhancement_filter=None,
    video_quality="Match Source",
    video_codec="auto",
    ffmpeg_exe=None,
    is_ar=True,
    cancel_callback=None,
    progress_callback=None,
):
    """
    Renders and exports a video applying multi-clip NLE timeline edits (or single trim),
    DaVinci aspect ratio & pan/zoom transformation, color grading, V2 icons/images,
    V3 text+ cards, V4 logos, subtitles, silence removal, and audio enhancement.
    """
    video_path = Path(video_path).resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"Source video not found: {video_path}")

    if output_path is None:
        if output_dir is None:
            output_dir = video_path.parent / "output"
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        suffix = video_path.suffix if video_path.suffix.lower() in (".mp4", ".mkv", ".mov", ".webm") else ".mp4"
        output_path = output_dir / f"{video_path.stem}_styled{suffix}"
    else:
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

    if ffmpeg_exe is None:
        for cand in [
            Path("E:/Songs/tools/ffmpeg-essentials/ffmpeg-8.1.2-essentials_build/bin/ffmpeg.exe"),
            Path("ffmpeg.exe"),
        ]:
            if cand.exists():
                ffmpeg_exe = str(cand)
                break
        if not ffmpeg_exe:
            ffmpeg_exe = "ffmpeg"

    # Probe input dimensions, duration, and audio presence
    in_w, in_h = 1920, 1080
    total_dur = 0.0
    has_audio = True
    try:
        import shutil
        cand_probe = Path(str(ffmpeg_exe)).with_name("ffprobe.exe")
        ffprobe_bin = str(cand_probe) if cand_probe.exists() else (shutil.which("ffprobe") or "ffprobe")
        probe_cmd = [
            ffprobe_bin,
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration:stream_side_data=rotation:stream_tags=rotate",
            "-show_entries", "format=duration",
            "-of", "json",
            str(video_path),
        ]
        p_res = subprocess.run(
            probe_cmd,
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if p_res.returncode == 0 and p_res.stdout.strip():
            try:
                import json
                p_data = json.loads(p_res.stdout)
                streams = p_data.get("streams", [])
                if streams:
                    s0 = streams[0]
                    in_w = int(s0.get("width", in_w))
                    in_h = int(s0.get("height", in_h))
                    rot = 0
                    for sd in s0.get("side_data_list", []):
                        if "rotation" in sd:
                            try:
                                rot = int(round(float(sd["rotation"])))
                                break
                            except (ValueError, TypeError):
                                pass
                    if rot == 0 and "tags" in s0:
                        tag_rot = s0["tags"].get("rotate")
                        if tag_rot is not None:
                            try:
                                rot = int(round(float(tag_rot)))
                            except (ValueError, TypeError):
                                pass
                    if abs(rot) in (90, 270):
                        in_w, in_h = in_h, in_w
                    if "duration" in s0:
                        try:
                            d_val = float(s0["duration"])
                            if d_val > 0:
                                total_dur = d_val
                        except Exception:
                            pass
                fmt = p_data.get("format", {})
                if total_dur <= 0 and "duration" in fmt:
                    try:
                        d_val = float(fmt["duration"])
                        if d_val > 0:
                            total_dur = d_val
                    except Exception:
                        pass
            except Exception:
                pass

        aprobe_cmd = [
            ffprobe_bin,
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            str(video_path),
        ]
        a_res = subprocess.run(
            aprobe_cmd,
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        has_audio = bool(a_res.stdout.strip())
    except Exception:
        pass

    temp_dir = output_path.parent / "_temp_branding"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_files: List[Path] = []

    has_manual_silence_clips = any(str(c.get("name", "")).startswith("🔇") for c in (nle_clips or []))
    is_single_clean_clip = (
        bool(nle_clips and len(nle_clips) == 1)
        and float(nle_clips[0].get("src_start", 0.0)) <= 0.05
        and abs(float(nle_clips[0].get("speed", 1.0) or 1.0) - 1.0) < 0.01
        and not nle_clips[0].get("custom_transform", False)
        and not nle_clips[0].get("muted", False)
    )
    if silence_config and silence_config.get("enabled") and not has_manual_silence_clips:
        if is_single_clean_clip or not nle_clips or len(nle_clips) <= 1:
            use_multi_clip_nle = False
        else:
            use_multi_clip_nle = True
    else:
        use_multi_clip_nle = bool(nle_clips and isinstance(nle_clips, list) and len(nle_clips) > 0 and not is_single_clean_clip)

    cmd = [
        str(ffmpeg_exe),
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-progress", "pipe:1",
        "-nostats",
    ]

    if use_multi_clip_nle:
        # ------------------------------------------------------------------
        # Multi-Clip DaVinci NLE Timeline Export Pipeline (with Gaps & FX)
        # ------------------------------------------------------------------
        import copy as _copy

        canvas_w, canvas_h = get_aspect_ratio_dimensions(aspect_ratio, in_w, in_h)
        working_clips = _copy.deepcopy(nle_clips)

        # Normalize & sort working_clips by tl_start while preserving explicit gaps
        fallback_tl = 0.0
        for wc in working_clips:
            s0 = max(0.0, float(wc.get("src_start", 0.0)))
            s1 = max(s0 + 0.08, float(wc.get("src_end", max(1.0, total_dur))))
            spd = max(0.25, min(4.0, float(wc.get("speed", 1.0) or 1.0)))
            dur_w = (s1 - s0) / spd
            if "tl_start" not in wc or wc.get("tl_start") is None:
                wc["tl_start"] = round(fallback_tl, 3)
            fallback_tl = max(fallback_tl, float(wc["tl_start"])) + dur_w
        working_clips.sort(key=lambda x: float(x.get("tl_start", 0.0)))

        # Optional automatic silence intersection on multi-clip timeline if enabled at export
        if silence_config and silence_config.get("enabled") and not has_manual_silence_clips:
            keep_iv = silence_config.get("keep_intervals")
            if not keep_iv:
                det = detect_silences(
                    media_path=video_path,
                    noise_db=silence_config.get("noise_db", -35.0),
                    min_silence_sec=silence_config.get("min_silence_sec", 0.5),
                    padding_sec=silence_config.get("padding_sec", 0.15),
                    ffmpeg_exe=ffmpeg_exe,
                    cancel_callback=cancel_callback,
                )
                keep_iv = det.get("keep_intervals", [])
            if keep_iv and silence_config.get("mode", "remove") == "remove":
                refined_clips = []
                cur_tl_acc = 0.0
                prev_orig_end = 0.0
                for wc in working_clips:
                    cs0 = max(0.0, float(wc.get("src_start", 0.0)))
                    cs1 = max(cs0 + 0.08, float(wc.get("src_end", max(1.0, total_dur))))
                    spd = max(0.25, min(4.0, float(wc.get("speed", 1.0) or 1.0)))
                    orig_gap = max(0.0, float(wc.get("tl_start", prev_orig_end)) - prev_orig_end)
                    prev_orig_end = float(wc.get("tl_start", prev_orig_end)) + (cs1 - cs0) / spd
                    cur_tl_acc += orig_gap
                    for ks, ke in keep_iv:
                        ov_s = max(cs0, float(ks))
                        ov_e = min(cs1, float(ke))
                        if (ov_e - ov_s) / spd >= 0.08:
                            sub_c = _copy.deepcopy(wc)
                            sub_c["src_start"] = round(ov_s, 3)
                            sub_c["src_end"] = round(ov_e, 3)
                            sub_c["tl_start"] = round(cur_tl_acc, 3)
                            cur_tl_acc += (ov_e - ov_s) / spd
                            refined_clips.append(sub_c)
                if refined_clips:
                    working_clips = refined_clips

        chains: List[str] = []
        concat_inputs: List[str] = []
        seg_durations: List[float] = []
        calc_dur = 0.0
        cursor_tl = 0.0
        input_idx = 0
        seg_idx = 0

        def _append_gap_segment(gap_seconds: float):
            nonlocal seg_idx, calc_dur, cursor_tl
            gd = round(max(0.04, float(gap_seconds)), 3)
            chains.append(
                f"color=c=black:s={canvas_w}x{canvas_h}:r=30:d={gd:.3f},setsar=1,format=yuv420p[v_seg_{seg_idx}]"
            )
            concat_inputs.append(f"[v_seg_{seg_idx}]")
            seg_durations.append(gd)
            if has_audio:
                chains.append(
                    f"anullsrc=channel_layout=stereo:sample_rate=44100,atrim=0:{gd:.3f},asetpts=PTS-STARTPTS,"
                    f"aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a_seg_{seg_idx}]"
                )
                concat_inputs.append(f"[a_seg_{seg_idx}]")
            seg_idx += 1
            calc_dur += gd
            cursor_tl += gd

        for clip in working_clips:
            cs0 = max(0.0, float(clip.get("src_start", 0.0)))
            cs1 = max(cs0 + 0.08, float(clip.get("src_end", max(1.0, total_dur))))
            raw_dur = max(0.08, cs1 - cs0)
            spd = max(0.25, min(4.0, float(clip.get("speed", 1.0) or 1.0)))
            vol = max(0.0, min(3.0, float(clip.get("volume", 1.0) if clip.get("volume") is not None else 1.0)))
            muted = bool(clip.get("muted", False))

            desired_tl_start = max(cursor_tl, float(clip.get("tl_start", cursor_tl)))
            if desired_tl_start - cursor_tl >= 0.04:
                _append_gap_segment(desired_tl_start - cursor_tl)

            cmd.extend(["-ss", f"{cs0:.3f}", "-t", f"{raw_dur:.3f}", "-i", str(video_path)])

            if clip.get("custom_transform", False):
                c_vt = {
                    "zoom": clip.get("zoom", 1.0),
                    "pan_x": clip.get("pan_x", 0.0),
                    "pan_y": clip.get("pan_y", 0.0),
                    "flip_h": clip.get("flip_h", False),
                    "clamp_edges": (video_transform or {}).get("clamp_edges", True),
                }
            else:
                c_vt = video_transform

            ar_str, canvas_w, canvas_h = build_aspect_ratio_filter(
                target_ratio=aspect_ratio,
                fit_mode=fit_mode,
                in_w=in_w,
                in_h=in_h,
                input_label=f"{input_idx}:v",
                output_label=f"v_ar_{input_idx}",
                video_transform=c_vt,
            )
            chains.append(ar_str)

            v_pts = "setpts=PTS-STARTPTS"
            if abs(spd - 1.0) > 0.01:
                v_pts += f",setpts={1.0 / spd:.5f}*PTS"
            chains.append(f"[v_ar_{input_idx}]{v_pts},fps=30,setsar=1,format=yuv420p[v_seg_{seg_idx}]")
            concat_inputs.append(f"[v_seg_{seg_idx}]")

            if has_audio:
                a_ops = ["asetpts=PTS-STARTPTS"]
                atempo_s = _build_atempo_chain(spd)
                if atempo_s:
                    a_ops.append(atempo_s)
                if muted or vol <= 0.001:
                    a_ops.append("volume=0.0")
                elif abs(vol - 1.0) > 0.01:
                    a_ops.append(f"volume={vol:.3f}")
                a_ops.append("aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo")
                chains.append(f"[{input_idx}:a]{','.join(a_ops)}[a_seg_{seg_idx}]")
                concat_inputs.append(f"[a_seg_{seg_idx}]")

            clip_tl_dur = raw_dur / spd
            calc_dur += clip_tl_dur
            cursor_tl += clip_tl_dur
            seg_durations.append(clip_tl_dur)
            input_idx += 1
            seg_idx += 1

        # Extend timeline with trailing black/silent segment if any timed overlay ends after last clip
        max_ov_end = cursor_tl
        for ov_list in (
            media_overlays or [],
            (title_config or {}).get("text_items", []) if isinstance(title_config, dict) else [],
            logo_items or [],
        ):
            for ov_it in ov_list:
                if ov_it.get("enabled", True) and not ov_it.get("full_duration", False):
                    max_ov_end = max(max_ov_end, float(ov_it.get("end_sec", 0.0) or 0.0))
        if max_ov_end - cursor_tl >= 0.05:
            _append_gap_segment(max_ov_end - cursor_tl)

        n_segs = seg_idx
        if n_segs == 1:
            chains.append("[v_seg_0]null[v_tl_base]")
            if has_audio:
                chains.append("[a_seg_0]anull[a_tl_base]")
        else:
            if transitions_config and transitions_config.get("enabled"):
                xfade_chains, xfade_dur = build_xfade_filter_chains(
                    n_segs=n_segs,
                    seg_durations=seg_durations,
                    transitions_config=transitions_config,
                    has_audio=has_audio,
                    v_seg_prefix="v_seg_",
                    a_seg_prefix="a_seg_",
                    v_out_label="v_tl_base",
                    a_out_label="a_tl_base",
                )
                chains.extend(xfade_chains)
                calc_dur = xfade_dur
            else:
                if has_audio:
                    chains.append(f"{''.join(concat_inputs)}concat=n={n_segs}:v=1:a=1[v_tl_base][a_tl_base]")
                else:
                    chains.append(f"{''.join(concat_inputs)}concat=n={n_segs}:v=1:a=0[v_tl_base]")

        cur_v = "v_tl_base"
        cur_a = "a_tl_base" if has_audio else None

        # Post-concat overlays (Color Grading, V2 Icons/Images, V3 Texts, V4 Logos, Subtitles)
        post_chains, cur_v, _step, ov_temps = _append_post_transform_overlays(
            cur_label=cur_v,
            step=100,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            color_config=color_config,
            media_overlays=media_overlays,
            title_config=title_config,
            logo_config=logo_config,
            logo_items=logo_items,
            subtitle_config=subtitle_config,
            active_keep_intervals=None,
            sil_mode="remove",
            sil_speed=4,
            t_dir=temp_dir,
            is_ar=is_ar,
        )
        temp_files.extend(ov_temps)
        chains.extend(post_chains)
        chains.append(f"[{cur_v}]format=yuv420p[outv]")

        use_custom_audio_map = False
        if has_audio and cur_a:
            if audio_enhancement_filter and str(audio_enhancement_filter).strip():
                chains.append(f"[{cur_a}]{audio_enhancement_filter}[outa]")
            else:
                chains.append(f"[{cur_a}]anull[outa]")
            use_custom_audio_map = True

        clean_chains = [c.rstrip(" ;") for c in chains if c and c.strip()]
        filter_complex_str = ";".join(clean_chains)

    else:
        # ------------------------------------------------------------------
        # Single-Stream Fast Export Pipeline
        # ------------------------------------------------------------------
        active_silence_cfg = None
        a_sil_expr = None
        if silence_config and silence_config.get("enabled"):
            active_silence_cfg = dict(silence_config)
            keep_iv = active_silence_cfg.get("keep_intervals")
            if not keep_iv:
                det = detect_silences(
                    media_path=video_path,
                    noise_db=active_silence_cfg.get("noise_db", -35.0),
                    min_silence_sec=active_silence_cfg.get("min_silence_sec", 0.5),
                    padding_sec=active_silence_cfg.get("padding_sec", 0.15),
                    ffmpeg_exe=ffmpeg_exe,
                    start_seconds=start_seconds,
                    duration_seconds=duration_seconds,
                    cancel_callback=cancel_callback,
                )
                keep_iv = det.get("keep_intervals", [])
            else:
                if start_seconds is not None and float(start_seconds) > 0:
                    s_off = float(start_seconds)
                    e_lim = (s_off + float(duration_seconds)) if duration_seconds is not None else (float(end_seconds) if end_seconds is not None else total_dur)
                    shifted = []
                    for ks, ke in keep_iv:
                        ns = max(ks, s_off) - s_off
                        ne = min(ke, e_lim) - s_off
                        if ne - ns >= 0.08:
                            shifted.append((round(ns, 3), round(ne, 3)))
                    keep_iv = shifted if shifted else [(0.0, max(0.5, e_lim - s_off))]
                elif duration_seconds is not None:
                    e_lim = float(duration_seconds)
                    shifted = [(ks, min(ke, e_lim)) for ks, ke in keep_iv if min(ke, e_lim) - ks >= 0.08]
                    keep_iv = shifted if shifted else [(0.0, max(0.5, e_lim))]

            active_silence_cfg["keep_intervals"] = keep_iv
            _, a_sil_expr = build_silence_filter_expressions(
                keep_intervals=keep_iv,
                mode=active_silence_cfg.get("mode", "remove"),
                speed_factor=active_silence_cfg.get("speed_factor", 4),
                total_duration=total_dur,
            )

        filter_complex_str, _out_w, _out_h, ov_temps = build_composite_video_filter(
            in_w=in_w,
            in_h=in_h,
            aspect_ratio=aspect_ratio,
            fit_mode=fit_mode,
            video_transform=video_transform,
            color_config=color_config,
            media_overlays=media_overlays,
            logo_config=logo_config,
            logo_items=logo_items,
            title_config=title_config,
            subtitle_config=subtitle_config,
            silence_config=active_silence_cfg,
            temp_dir=temp_dir,
            input_label="0:v",
            final_output_label="outv",
            is_ar=is_ar,
        )
        temp_files.extend(ov_temps)

        a_filters = [f for f in (a_sil_expr, audio_enhancement_filter) if f and str(f).strip()]
        use_custom_audio_map = False
        if has_audio and a_filters:
            a_chain = ",".join(a_filters)
            filter_complex_str = f"{filter_complex_str};[0:a]{a_chain}[outa]"
            use_custom_audio_map = True

        calc_dur = total_dur
        if active_silence_cfg and active_silence_cfg.get("keep_intervals"):
            speech_sum = sum(max(0.0, e - s) for s, e in active_silence_cfg["keep_intervals"])
            smode = active_silence_cfg.get("mode", "remove")
            if smode == "remove" and speech_sum > 0:
                calc_dur = speech_sum
            elif smode == "fast_forward" and speech_sum > 0:
                sf = max(2, int(active_silence_cfg.get("speed_factor", 4)))
                calc_dur = speech_sum + max(0.0, total_dur - speech_sum) / sf
        elif start_seconds is not None:
            start_s = max(0.0, float(start_seconds))
            if duration_seconds is not None:
                calc_dur = float(duration_seconds)
            elif end_seconds is not None:
                calc_dur = max(0.1, float(end_seconds) - start_s)
            elif total_dur > start_s:
                calc_dur = total_dur - start_s
        elif duration_seconds is not None:
            calc_dur = float(duration_seconds)

        if start_seconds is not None:
            cmd.extend(["-ss", f"{max(0.0, float(start_seconds)):.3f}"])
        if duration_seconds is not None:
            cmd.extend(["-t", f"{max(0.1, float(duration_seconds)):.3f}"])
        elif end_seconds is not None and start_seconds is not None:
            dur = max(0.1, float(end_seconds) - max(0.0, float(start_seconds)))
            cmd.extend(["-t", f"{dur:.3f}"])

        cmd.extend(["-i", str(video_path)])

    out_ext = output_path.suffix.lower()
    is_hevc = (video_codec in ("libx265", "hevc", "h265")) or (out_ext == ".mp4_hevc")
    if out_ext == ".mp4_hevc":
        output_path = output_path.with_suffix(".mp4")
        out_ext = ".mp4"

    is_audio_only_ext = out_ext in {".mp3", ".m4a", ".wav", ".flac", ".ogg"}
    if is_audio_only_ext:
        filter_complex_str = filter_complex_str + ";[outv]nullsink"

    # Attach filter_complex (via script file if long)
    if len(filter_complex_str) > 4500:
        fc_script = temp_dir / f"fc_{int(time.time() * 1000)}.txt"
        fc_script.write_text(filter_complex_str, encoding="utf-8")
        temp_files.append(fc_script)
        cmd.extend(["-filter_complex_script", str(fc_script)])
    else:
        cmd.extend(["-filter_complex", filter_complex_str])

    if is_audio_only_ext:
        if use_custom_audio_map:
            cmd.extend(["-map", "[outa]"])
        else:
            cmd.extend(["-map", "0:a"])
    elif use_custom_audio_map:
        cmd.extend(["-map", "[outv]", "-map", "[outa]"])
    elif not use_multi_clip_nle:
        cmd.extend(["-map", "[outv]", "-map", "0:a?"])
    else:
        cmd.extend(["-map", "[outv]"])

    # Quality / Source-Size Matching & Multi-Format Codec Selection
    crf_val = "23" if not is_hevc else "24"
    matched_v_kbps = None
    preset_speed = "medium"
    audio_bitrate = "128k"

    if video_quality in ("Match Source", "Original"):
        try:
            fsize = video_path.stat().st_size
            if fsize > 0 and total_dur > 0.2:
                tot_kbps = (fsize * 8.0 / 1000.0) / max(total_dur, 0.2)
                matched_v_kbps = max(350, min(45000, int(round(tot_kbps - (192 if has_audio else 0)))))
        except Exception:
            matched_v_kbps = None
        crf_val = "19" if not is_hevc else "21"
        preset_speed = "medium"
        audio_bitrate = "192k"
    elif video_quality in ("Smart Compress", "smart_compress"):
        # Smart compression: massive reduction in DaVinci export size while preserving crisp quality
        crf_val = "23" if not is_hevc else "24"
        preset_speed = "veryfast"
        audio_bitrate = "128k"
    elif video_quality in ("High Compress", "high_compress", "Small", "small"):
        # Strong compression: smallest file size for instant sharing (WhatsApp, Telegram, etc.)
        crf_val = "28" if not is_hevc else "28"
        preset_speed = "veryfast"
        audio_bitrate = "96k"
    elif video_quality == "Very High":
        crf_val = "18" if not is_hevc else "20"
        preset_speed = "fast"
        audio_bitrate = "192k"
    elif video_quality == "High":
        crf_val = "21" if not is_hevc else "23"
        preset_speed = "fast"
        audio_bitrate = "160k"
    elif video_quality == "Medium":
        crf_val = "26" if not is_hevc else "26"
        preset_speed = "veryfast"
        audio_bitrate = "128k"

    temp_part = output_path.with_name(f"{output_path.stem}_part{output_path.suffix}")
    if is_audio_only_ext:
        if out_ext == ".mp3":
            cmd.extend(["-vn", "-c:a", "libmp3lame", "-b:a", audio_bitrate, str(temp_part)])
        elif out_ext == ".wav":
            cmd.extend(["-vn", "-c:a", "pcm_s16le", str(temp_part)])
        elif out_ext == ".flac":
            cmd.extend(["-vn", "-c:a", "flac", str(temp_part)])
        elif out_ext == ".ogg":
            cmd.extend(["-vn", "-c:a", "libvorbis", "-q:a", "5", str(temp_part)])
        else:
            cmd.extend(["-vn", "-c:a", "aac", "-b:a", audio_bitrate, "-movflags", "+faststart", str(temp_part)])
    elif out_ext == ".webm":
        if matched_v_kbps:
            v_rate_args = ["-b:v", f"{matched_v_kbps}k", "-maxrate", f"{int(matched_v_kbps * 1.25)}k", "-bufsize", f"{int(matched_v_kbps * 2)}k"]
        else:
            vp9_crf = {"18": "24", "19": "25", "20": "26", "21": "28", "22": "29", "23": "30", "24": "31", "26": "34", "28": "37", "30": "38"}.get(crf_val, "30")
            v_rate_args = ["-crf", vp9_crf, "-b:v", "0"]
        cmd.extend([
            "-c:v", "libvpx-vp9",
            "-deadline", "good",
            "-cpu-used", "2",
            *v_rate_args,
            "-c:a", "libopus",
            "-b:a", audio_bitrate,
            str(temp_part),
        ])
    else:
        # MP4, MKV, MOV, AVI
        is_explicit_hevc = bool(video_codec in ("libx265", "hevc", "h265")) or is_hevc
        v_codec = detect_best_video_encoder(
            ffmpeg_exe=ffmpeg_exe,
            is_hevc=is_explicit_hevc,
            user_codec=video_codec if video_codec not in ("auto", "default") else None,
        )

        extra_v_args = ["-pix_fmt", "yuv420p"]
        preset_args = []

        if "qsv" in v_codec:
            extra_v_args = ["-pix_fmt", "nv12"]
            preset_args = ["-preset", "veryfast"]
            if matched_v_kbps:
                v_rate_args = ["-b:v", f"{matched_v_kbps}k", "-maxrate", f"{int(matched_v_kbps * 1.25)}k"]
            else:
                v_rate_args = ["-global_quality", str(crf_val)]
        elif "nvenc" in v_codec:
            extra_v_args = ["-pix_fmt", "yuv420p"]
            preset_args = ["-preset", "p4"]
            if matched_v_kbps:
                v_rate_args = ["-b:v", f"{matched_v_kbps}k", "-maxrate", f"{int(matched_v_kbps * 1.25)}k"]
            else:
                v_rate_args = ["-cq", str(crf_val), "-rc", "vbr"]
        elif "amf" in v_codec:
            extra_v_args = ["-pix_fmt", "yuv420p"]
            preset_args = ["-quality", "speed"]
            if matched_v_kbps:
                v_rate_args = ["-b:v", f"{matched_v_kbps}k"]
            else:
                v_rate_args = ["-rc", "cqp", "-qp_i", str(crf_val), "-qp_p", str(crf_val)]
        elif "mf" in v_codec:
            extra_v_args = ["-pix_fmt", "yuv420p"]
            target_rate = matched_v_kbps if matched_v_kbps else (
                12000 if video_quality in ("Very High", "Original", "Match Source") else
                7500 if video_quality in ("High", "Smart Compress") else
                4500
            )
            v_rate_args = ["-b:v", f"{target_rate}k"]
        else:
            # Fallback CPU (libx264 / libx265): optimize medium to veryfast to prevent multi-hour CPU freezes
            eff_preset = "veryfast" if preset_speed == "medium" else preset_speed
            preset_args = ["-preset", eff_preset]
            if matched_v_kbps:
                v_rate_args = ["-b:v", f"{matched_v_kbps}k", "-maxrate", f"{int(matched_v_kbps * 1.25)}k", "-bufsize", f"{int(matched_v_kbps * 2)}k"]
            else:
                v_rate_args = ["-crf", str(crf_val)]

        if is_explicit_hevc and "-tag:v" not in extra_v_args:
            extra_v_args.extend(["-tag:v", "hvc1"])

        # Smart Audio Optimization: Copy stream without re-encoding when untouched
        can_copy_audio = (
            has_audio
            and not use_custom_audio_map
            and not use_multi_clip_nle
            and start_seconds is None
            and duration_seconds is None
            and end_seconds is None
            and out_ext in {".mp4", ".mov", ".mkv", ".m4v"}
        )
        if can_copy_audio:
            a_codec_args = ["-c:a", "copy"]
        else:
            a_codec_args = ["-c:a", "libmp3lame", "-b:a", audio_bitrate] if out_ext == ".avi" else ["-c:a", "aac", "-b:a", audio_bitrate]

        mux_args = ["-movflags", "+faststart"] if out_ext in {".mp4", ".mov", ".m4v"} else []
        cmd.extend([
            "-c:v", v_codec,
            *preset_args,
            *extra_v_args,
            *v_rate_args,
            *a_codec_args,
            *mux_args,
            str(temp_part),
        ])

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        while True:
            if cancel_callback and cancel_callback():
                try:
                    proc.kill()
                    proc.wait(timeout=1.0)
                except Exception:
                    pass
                raise CancelledError("Export canceled by user")

            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                time.sleep(0.05)
                continue

            line = line.strip()
            if line.startswith("out_time_us="):
                try:
                    out_time_us = int(line.split("=")[1])
                    cur_sec = out_time_us / 1_000_000.0
                    pct = min(99, int((cur_sec / max(calc_dur, 0.1)) * 100)) if calc_dur > 0 else 50
                    if progress_callback:
                        progress_callback(pct, cur_sec, calc_dur)
                except Exception:
                    pass

        returncode = proc.wait()
        if cancel_callback and cancel_callback():
            try:
                if temp_part.exists():
                    temp_part.unlink(missing_ok=True)
                if output_path.exists():
                    output_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise CancelledError("Export canceled by user")

        if returncode != 0:
            if cancel_callback and cancel_callback():
                try:
                    if temp_part.exists():
                        temp_part.unlink(missing_ok=True)
                    if output_path.exists():
                        output_path.unlink(missing_ok=True)
                except Exception:
                    pass
                raise CancelledError("Export canceled by user")
            err = proc.stderr.read()
            raise RuntimeError(f"FFmpeg export failed (code {returncode}): {err}")

        if temp_part.exists():
            final_target = output_path
            moved = False
            for _attempt in range(5):
                try:
                    if final_target.exists():
                        final_target.unlink()
                    temp_part.rename(final_target)
                    moved = True
                    break
                except (PermissionError, OSError):
                    time.sleep(0.3)
            if not moved:
                stem = output_path.stem
                counter = 1
                while True:
                    candidate = output_path.with_name(f"{stem}_{counter}{output_path.suffix}")
                    if not candidate.exists():
                        final_target = candidate
                        break
                    counter += 1
                try:
                    temp_part.rename(final_target)
                except Exception:
                    import shutil
                    shutil.copy2(temp_part, final_target)
                    try:
                        temp_part.unlink()
                    except Exception:
                        pass
            output_path = final_target

        if progress_callback:
            progress_callback(100, calc_dur, calc_dur)

        return output_path

    finally:
        for tf in temp_files:
            try:
                if tf.exists():
                    tf.unlink()
            except Exception:
                pass
        try:
            if temp_dir.exists():
                temp_dir.rmdir()
        except Exception:
            pass
