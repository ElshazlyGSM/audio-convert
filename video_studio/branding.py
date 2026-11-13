"""
Video Branding, Text+ Cards & Timed RGBA Overlay Generator
Handles Logo watermarks, Title/Headline Banners, Text+ cards with rotation & opacity,
and time-bound FFmpeg overlay filter generation.
Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
from .arabic_support import prepare_arabic_for_rendering
from .icons_library import apply_opacity_and_rotation

LOGO_POSITIONS = {
    "top_right": {
        "label_en": "Top Right",
        "label_ar": "أعلى اليمين",
        "expr": "W-w-{margin}:{margin}",
    },
    "top_left": {
        "label_en": "Top Left",
        "label_ar": "أعلى اليسار",
        "expr": "{margin}:{margin}",
    },
    "bottom_right": {
        "label_en": "Bottom Right",
        "label_ar": "أسفل اليمين",
        "expr": "W-w-{margin}:H-h-{margin}",
    },
    "bottom_left": {
        "label_en": "Bottom Left",
        "label_ar": "أسفل اليسار",
        "expr": "{margin}:H-h-{margin}",
    },
    "center": {
        "label_en": "Center",
        "label_ar": "في المنتصف",
        "expr": "(W-w)/2:(H-h)/2",
    },
}

BANNER_POSITIONS = {
    "top": {
        "label_en": "Top Banner (Reels Style)",
        "label_ar": "شريط علوي (شكل الريلز والشورتس)",
    },
    "bottom": {
        "label_en": "Bottom Banner",
        "label_ar": "شريط سفلي",
    },
}

BANNER_BG_COLORS = {
    "black": {"label_en": "Dark Black", "label_ar": "أسود داكن", "rgba": (20, 20, 20, 235), "hex": "#141414"},
    "transparent": {"label_en": "Transparent (No bg)", "label_ar": "شفاف (بدون خلفية)", "rgba": (0, 0, 0, 0), "hex": ""},
    "white": {"label_en": "Crisp White", "label_ar": "أبيض ناصع", "rgba": (255, 255, 255, 240), "hex": "#FFFFFF"},
    "navy": {"label_en": "Deep Navy", "label_ar": "كحلي داكن", "rgba": (10, 25, 47, 235), "hex": "#0A192F"},
    "red": {"label_en": "Crimson Red", "label_ar": "أحمر عناب", "rgba": (139, 0, 0, 235), "hex": "#8B0000"},
    "gold": {"label_en": "Royal Gold", "label_ar": "ذهبي ملكي", "rgba": (218, 165, 32, 235), "hex": "#DAA520"},
    "emerald": {"label_en": "Emerald Green", "label_ar": "أخضر زمردي", "rgba": (14, 95, 60, 235), "hex": "#0E5F3C"},
    "gray": {"label_en": "Slate Gray", "label_ar": "رمادي معتم", "rgba": (45, 55, 72, 235), "hex": "#2D3748"},
}

BANNER_TEXT_COLORS = {
    "white": {"label_en": "White", "label_ar": "أبيض", "rgba": (255, 255, 255, 255), "hex": "#FFFFFF"},
    "yellow": {"label_en": "Yellow", "label_ar": "أصفر ذهبي", "rgba": (255, 215, 0, 255), "hex": "#FFD700"},
    "black": {"label_en": "Black", "label_ar": "أسود", "rgba": (0, 0, 0, 255), "hex": "#000000"},
    "lime": {"label_en": "Lime Green", "label_ar": "أخضر ليموني", "rgba": (57, 255, 20, 255), "hex": "#39FF14"},
    "cyan": {"label_en": "Cyan Blue", "label_ar": "أزرق سماوي", "rgba": (0, 220, 255, 255), "hex": "#00DCFF"},
    "orange": {"label_en": "Vibrant Orange", "label_ar": "برتقالي", "rgba": (255, 120, 0, 255), "hex": "#FF7800"},
    "red": {"label_en": "Bright Red", "label_ar": "أحمر ساطع", "rgba": (255, 65, 65, 255), "hex": "#FF4141"},
}

AVAILABLE_FONTS = [
    ("Segoe UI", "segoeuib.ttf"),
    ("Tahoma", "tahomabd.ttf"),
    ("Arial", "arialbd.ttf"),
    ("Traditional Arabic", "tradbdo.ttf"),
    ("Calibri", "calibrib.ttf"),
    ("Impact", "impact.ttf"),
]


def _get_font(font_name="Segoe UI", size=36):
    """
    Attempts to load a bold TrueType font from Windows font directory, falling back cleanly.
    """
    fn_clean = (font_name or "Segoe UI").strip()
    font_map = {k.lower(): v for k, v in AVAILABLE_FONTS}
    mapped_file = font_map.get(fn_clean.lower())

    candidate_paths = []
    if mapped_file:
        candidate_paths.append(Path(f"C:/Windows/Fonts/{mapped_file}"))
    candidate_paths.extend([
        Path(f"C:/Windows/Fonts/{fn_clean.lower().replace(' ', '')}b.ttf"),
        Path(f"C:/Windows/Fonts/{fn_clean.lower().replace(' ', '')}.ttf"),
        Path(f"C:/Windows/Fonts/{fn_clean.lower()}.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/tahomabd.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ])
    for p in candidate_paths:
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size=size)
            except Exception:
                pass
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def generate_title_banner_image(
    text,
    output_path,
    banner_style="top",
    bg_color_key="black",
    text_color_key="white",
    font_name="Segoe UI",
    video_w=1080,
    video_h=1920,
):
    """
    Generates a crystal clear banner image with anti-aliasing, rounded corners and title text.
    Returns: Path to generated PNG.
    """
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    text = (text or "").strip()
    if not text:
        return None

    banner_w = int(video_w * 0.92)
    banner_h = max(70, min(240, int(video_h * 0.075)))

    bg_info = BANNER_BG_COLORS.get(bg_color_key, BANNER_BG_COLORS["black"])
    fg_info = BANNER_TEXT_COLORS.get(text_color_key, BANNER_TEXT_COLORS["white"])
    bg_rgba = bg_info["rgba"]
    fg_rgba = fg_info["rgba"]

    border_rgba = (255, 215, 0, 200) if bg_color_key in ("black", "navy", "emerald") else (0, 0, 0, 100)

    font_size = max(24, min(64, int(banner_h * 0.44)))
    font = _get_font(font_name, font_size)
    display_text = prepare_arabic_for_rendering(text)

    img = Image.new("RGBA", (banner_w, banner_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    radius = min(20, banner_h // 4)
    draw.rounded_rectangle(
        [2, 2, banner_w - 3, banner_h - 3],
        radius=radius,
        fill=bg_rgba,
        outline=border_rgba,
        width=2,
    )

    try:
        bbox = draw.textbbox((0, 0), display_text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except Exception:
        tw = len(display_text) * (font_size // 2)
        th = font_size

    tx = max(10, (banner_w - tw) // 2)
    ty = max(5, (banner_h - th) // 2 - 2)

    shadow_col = (0, 0, 0, 180) if bg_color_key != "black" else (0, 0, 0, 255)
    draw.text((tx + 2, ty + 2), display_text, fill=shadow_col, font=font)
    draw.text((tx, ty), display_text, fill=fg_rgba, font=font)

    img.save(str(output_path), "PNG")
    return output_path


def render_text_card_pil(
    text: str,
    bg_color_key: str = "black",
    text_color_key: str = "white",
    font_size: int = 34,
    font_name: str = "Segoe UI",
    video_w: int = 1080,
    video_h: int = 1920,
    opacity: float = 1.0,
    rotation: float = 0.0,
) -> Optional[Image.Image]:
    """
    Renders a Text+ card as a PIL RGBA Image (used for both live Viewer preview and PNG export).
    """
    text = (text or "").strip()
    if not text:
        return None

    bg_info = BANNER_BG_COLORS.get(bg_color_key, BANNER_BG_COLORS["black"])
    fg_info = BANNER_TEXT_COLORS.get(text_color_key, BANNER_TEXT_COLORS["white"])
    bg_rgba = bg_info["rgba"]
    fg_rgba = fg_info["rgba"]
    is_transparent = (bg_color_key == "transparent" or bg_rgba[3] == 0)

    scale_factor = max(0.22, min(2.8, video_w / 1080.0))
    actual_font_size = max(12, min(160, int(round(float(font_size) * scale_factor))))
    font = _get_font(font_name, actual_font_size)

    # Support multi-line text cleanly
    lines_raw = [ln.strip() for ln in text.splitlines() if ln.strip()] or [text]
    shaped_lines = [prepare_arabic_for_rendering(ln) for ln in lines_raw]

    dummy_draw = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    line_sizes = []
    for sl in shaped_lines:
        try:
            bbox = dummy_draw.textbbox((0, 0), sl, font=font)
            lw = bbox[2] - bbox[0]
            lh = bbox[3] - bbox[1]
            y_off = bbox[1]
        except Exception:
            lw = len(sl) * max(8, actual_font_size // 2)
            lh = actual_font_size
            y_off = 0
        line_sizes.append((sl, lw, lh, y_off))

    max_lw = max(x[1] for x in line_sizes)
    line_gap = max(4, int(actual_font_size * 0.22))
    total_th = sum(x[2] for x in line_sizes) + line_gap * max(0, len(line_sizes) - 1)

    pad_x = max(10, int(26 * scale_factor)) if not is_transparent else max(6, int(10 * scale_factor))
    pad_y = max(7, int(16 * scale_factor)) if not is_transparent else max(4, int(8 * scale_factor))

    card_w = max(32, max_lw + pad_x * 2)
    card_h = max(22, total_th + pad_y * 2)

    img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if not is_transparent:
        border_rgba = (255, 215, 0, 210) if bg_color_key in ("black", "navy", "emerald") else (0, 0, 0, 120)
        bw = max(1, int(round(2 * scale_factor)))
        draw.rounded_rectangle(
            [bw, bw, card_w - bw - 1, card_h - bw - 1],
            radius=min(18, card_h // 4),
            fill=bg_rgba,
            outline=border_rgba,
            width=bw,
        )

    cur_y = (card_h - total_th) // 2
    sh_off = max(1, int(round(2 * scale_factor)))
    for sl, lw, lh, y_off in line_sizes:
        tx = (card_w - lw) // 2
        ty = cur_y - y_off
        if is_transparent:
            # Crisp dark stroke so transparent text is readable on any background
            for ox in (-sh_off, 0, sh_off):
                for oy in (-sh_off, 0, sh_off):
                    if ox or oy:
                        draw.text((tx + ox, ty + oy), sl, fill=(0, 0, 0, 230), font=font)
        else:
            draw.text((tx + sh_off, ty + sh_off), sl, fill=(0, 0, 0, 210), font=font)
        draw.text((tx, ty), sl, fill=fg_rgba, font=font)
        cur_y += lh + line_gap

    return apply_opacity_and_rotation(img, opacity=opacity, rotation_deg=rotation)


def generate_text_overlay_image(
    text,
    output_path,
    bg_color_key="black",
    text_color_key="white",
    font_size=34,
    font_name="Segoe UI",
    video_w=1080,
    video_h=1920,
    opacity=1.0,
    rotation=0.0,
):
    """
    Generates a crystal clear, anti-aliased image card for a text overlay.
    Returns: (output_path, card_w, card_h)
    """
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img = render_text_card_pil(
        text=text,
        bg_color_key=bg_color_key,
        text_color_key=text_color_key,
        font_size=font_size,
        font_name=font_name,
        video_w=video_w,
        video_h=video_h,
        opacity=opacity,
        rotation=rotation,
    )
    if img is None:
        return None, 0, 0
    img.save(str(output_path), "PNG")
    return output_path, img.width, img.height


def build_timed_rgba_overlay_filter(
    image_path: Path,
    x_pct: float,
    y_pct: float,
    video_w: int,
    video_h: int,
    img_w: Optional[int] = None,
    img_h: Optional[int] = None,
    anchor: str = "center",
    start_sec: Optional[float] = None,
    end_sec: Optional[float] = None,
    full_duration: bool = True,
    stream_id: str = "ov_0",
    input_label: str = "v_in",
    output_label: str = "v_out",
) -> str:
    """
    Constructs a collision-free FFmpeg filter segment for any pre-rendered RGBA PNG overlay
    (Text+, Icon, Custom Image, or Logo) with optional timeline [start_sec, end_sec] gating.
    """
    image_path = Path(image_path).resolve()
    if not image_path.exists():
        return f"[{input_label}]null[{output_label}]"

    img_esc = str(image_path).replace("\\", "/").replace(":", r"\:")

    if anchor == "center" and img_w and img_h:
        x_px = int(round(video_w * float(x_pct) - (img_w / 2.0)))
        y_px = int(round(video_h * float(y_pct) - (img_h / 2.0)))
    else:
        x_px = int(round(video_w * float(x_pct)))
        y_px = int(round(video_h * float(y_pct)))

    # Allow partial edge placement without disappearing completely
    if img_w and img_h:
        x_px = max(-img_w + 16, min(video_w - 16, x_px))
        y_px = max(-img_h + 16, min(video_h - 16, y_px))
    else:
        x_px = max(0, min(video_w - 20, x_px))
        y_px = max(0, min(video_h - 20, y_px))

    enable_part = ""
    if not full_duration and start_sec is not None and end_sec is not None:
        s_val = max(0.0, float(start_sec))
        e_val = max(s_val + 0.05, float(end_sec))
        enable_part = f":enable='between(t,{s_val:.3f},{e_val:.3f})'"

    return (
        f"movie='{img_esc}',format=rgba[{stream_id}];"
        f"[{input_label}][{stream_id}]overlay=x={x_px}:y={y_px}{enable_part}[{output_label}]"
    )


def build_logo_overlay_filter(
    logo_path,
    position="top_right",
    scale_ratio=0.15,
    opacity=0.85,
    margin=30,
    video_w=1080,
    video_h=1920,
    input_label="v_in",
    output_label="v_logo",
):
    """
    Constructs FFmpeg filter segment for Logo Watermark overlay.
    """
    logo_path = Path(logo_path).resolve()
    if not logo_path.exists():
        return f"[{input_label}]null[{output_label}]"

    logo_esc = str(logo_path).replace("\\", "/").replace(":", r"\:")
    target_w = max(48, min(400, int(video_w * scale_ratio)))
    pos_info = LOGO_POSITIONS.get(position, LOGO_POSITIONS["top_right"])
    xy_expr = pos_info["expr"].format(margin=margin)
    op_val = max(0.1, min(1.0, float(opacity)))
    sid = f"logo_{output_label}"

    return (
        f"movie='{logo_esc}',scale={target_w}:-1,format=rgba,"
        f"colorchannelmixer=aa={op_val}[{sid}];"
        f"[{input_label}][{sid}]overlay={xy_expr}[{output_label}]"
    )


def build_title_banner_filter(
    banner_image_path,
    position="top",
    margin_y=None,
    video_w=1080,
    video_h=1920,
    input_label="v_in",
    output_label="v_banner",
):
    banner_path = Path(banner_image_path).resolve()
    if not banner_path.exists():
        return f"[{input_label}]null[{output_label}]"

    banner_esc = str(banner_path).replace("\\", "/").replace(":", r"\:")
    if margin_y is None:
        margin_y = max(40, int(video_h * 0.055)) if position == "top" else max(40, int(video_h * 0.075))
    y_expr = f"H-h-{margin_y}" if position == "bottom" else f"{margin_y}"
    sid = f"bnr_{output_label}"

    return (
        f"movie='{banner_esc}',format=rgba[{sid}];"
        f"[{input_label}][{sid}]overlay=(W-w)/2:{y_expr}[{output_label}]"
    )


def build_free_logo_overlay_filter(
    logo_path,
    x_pct=0.85,
    y_pct=0.05,
    scale_ratio=0.15,
    opacity=0.85,
    video_w=1080,
    video_h=1920,
    input_label="v_in",
    output_label="v_logo",
    start_sec=None,
    end_sec=None,
    full_duration=True,
):
    logo_path = Path(logo_path).resolve()
    if not logo_path.exists():
        return f"[{input_label}]null[{output_label}]"

    logo_esc = str(logo_path).replace("\\", "/").replace(":", r"\:")
    target_w = max(32, min(int(video_w * 0.95), int(video_w * float(scale_ratio))))
    op_val = max(0.1, min(1.0, float(opacity)))

    x_px = max(0, min(video_w - target_w, int(video_w * float(x_pct))))
    y_px = max(0, min(video_h - 20, int(video_h * float(y_pct))))
    sid = f"flg_{output_label}"

    enable_part = ""
    if not full_duration and start_sec is not None and end_sec is not None:
        s_val = max(0.0, float(start_sec))
        e_val = max(s_val + 0.05, float(end_sec))
        enable_part = f":enable='between(t,{s_val:.3f},{e_val:.3f})'"

    return (
        f"movie='{logo_esc}',scale={target_w}:-1,format=rgba,"
        f"colorchannelmixer=aa={op_val}[{sid}];"
        f"[{input_label}][{sid}]overlay=x={x_px}:y={y_px}{enable_part}[{output_label}]"
    )


def build_free_text_overlay_filter(
    image_path,
    x_pct=0.5,
    y_pct=0.1,
    video_w=1080,
    video_h=1920,
    card_w=None,
    card_h=None,
    input_label="v_in",
    output_label="v_text",
    start_sec=None,
    end_sec=None,
    full_duration=True,
):
    return build_timed_rgba_overlay_filter(
        image_path=Path(image_path),
        x_pct=x_pct,
        y_pct=y_pct,
        video_w=video_w,
        video_h=video_h,
        img_w=card_w,
        img_h=card_h,
        anchor="center",
        start_sec=start_sec,
        end_sec=end_sec,
        full_duration=full_duration,
        stream_id=f"txt_{output_label}",
        input_label=input_label,
        output_label=output_label,
    )
