"""
Built-in Pro Vector/Pillow Icons, Stickers, Social Badges & Media Overlay Renderer
Generates razor-sharp anti-aliased RGBA overlays (2x supersampled) with zero external file dependencies,
plus custom image/logo opacity & rotation compositing.
Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

import math
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

from .arabic_support import prepare_arabic_for_rendering


ICON_PRESETS: Dict[str, Dict[str, Any]] = {
    "subscribe_ar": {
        "label_ar": "🔴 زر اشترك الآن (يوتيوب)",
        "label_en": "🔴 Subscribe Badge (AR)",
        "category": "social",
        "kind": "badge",
        "bg": (220, 20, 35, 245),
        "border": (255, 255, 255, 220),
        "fg": (255, 255, 255, 255),
        "default_text_ar": "اشترك في القناة",
        "default_text_en": "SUBSCRIBE",
        "symbol": "play",
    },
    "like_badge": {
        "label_ar": "👍 شارة إعجاب / لايك",
        "label_en": "👍 Like Badge",
        "category": "social",
        "kind": "badge",
        "bg": (24, 119, 242, 245),
        "border": (255, 255, 255, 210),
        "fg": (255, 255, 255, 255),
        "default_text_ar": "أعجبني",
        "default_text_en": "LIKE",
        "symbol": "star",
    },
    "bell_badge": {
        "label_ar": "🔔 جرس التنبيهات",
        "label_en": "🔔 Notification Bell",
        "category": "social",
        "kind": "circle_icon",
        "bg": (245, 175, 25, 245),
        "border": (255, 255, 255, 230),
        "fg": (20, 20, 20, 255),
        "symbol": "bell",
    },
    "share_badge": {
        "label_ar": "↗️ شارك المقطع (الدال على الخير)",
        "label_en": "↗️ Share Video Badge",
        "category": "social",
        "kind": "badge",
        "bg": (16, 137, 62, 245),
        "border": (255, 215, 0, 220),
        "fg": (255, 255, 255, 255),
        "default_text_ar": "شارك المقطع",
        "default_text_en": "SHARE",
        "symbol": "share",
    },
    "islamic_star": {
        "label_ar": "🕌 نجمة وزخرفة إسلامية ذهبية",
        "label_en": "🕌 Golden Islamic Star (Rub el Hizb)",
        "category": "lecture",
        "kind": "islamic_star",
        "bg": (14, 77, 52, 240),
        "border": (235, 190, 60, 255),
        "fg": (255, 225, 110, 255),
        "symbol": "rub_el_hizb",
    },
    "important_note": {
        "label_ar": "✨ شارة فائدة هامة / تنبيه علمي",
        "label_en": "✨ Key Highlight Callout",
        "category": "lecture",
        "kind": "badge",
        "bg": (18, 28, 48, 242),
        "border": (235, 190, 60, 255),
        "fg": (255, 220, 90, 255),
        "default_text_ar": "فائدة هامة",
        "default_text_en": "KEY POINT",
        "symbol": "star",
    },
    "podcast_mic": {
        "label_ar": "🎙️ أيقونة ميكروفون صوتي",
        "label_en": "🎙️ Studio Microphone",
        "category": "lecture",
        "kind": "circle_icon",
        "bg": (30, 36, 48, 242),
        "border": (88, 166, 255, 245),
        "fg": (255, 255, 255, 255),
        "symbol": "mic",
    },
    "youtube_icon": {
        "label_ar": "▶️ أيقونة يوتيوب",
        "label_en": "▶️ YouTube Icon",
        "category": "social",
        "kind": "yt_box",
        "bg": (255, 0, 0, 250),
        "border": (255, 255, 255, 200),
        "fg": (255, 255, 255, 255),
        "symbol": "play",
    },
    "whatsapp_icon": {
        "label_ar": "💚 أيقونة واتساب",
        "label_en": "💚 WhatsApp Icon",
        "category": "social",
        "kind": "circle_icon",
        "bg": (37, 211, 102, 248),
        "border": (255, 255, 255, 240),
        "fg": (255, 255, 255, 255),
        "symbol": "phone",
    },
    "facebook_icon": {
        "label_ar": "📘 أيقونة فيسبوك",
        "label_en": "📘 Facebook Icon",
        "category": "social",
        "kind": "circle_icon",
        "bg": (24, 119, 242, 248),
        "border": (255, 255, 255, 230),
        "fg": (255, 255, 255, 255),
        "symbol": "f_letter",
    },
    "instagram_icon": {
        "label_ar": "📸 أيقونة إنستغرام",
        "label_en": "📸 Instagram Icon",
        "category": "social",
        "kind": "insta_box",
        "bg": (214, 41, 118, 248),
        "border": (255, 210, 100, 240),
        "fg": (255, 255, 255, 255),
        "symbol": "camera",
    },
    "tiktok_reels": {
        "label_ar": "🎬 شارة ريلز / شورتس",
        "label_en": "🎬 Reels / Shorts Icon",
        "category": "social",
        "kind": "circle_icon",
        "bg": (18, 18, 24, 245),
        "border": (0, 242, 234, 245),
        "fg": (255, 0, 80, 255),
        "symbol": "play",
    },
    "telegram_icon": {
        "label_ar": "✈️ أيقونة تيليجرام",
        "label_en": "✈️ Telegram Icon",
        "category": "social",
        "kind": "circle_icon",
        "bg": (34, 158, 217, 248),
        "border": (255, 255, 255, 230),
        "fg": (255, 255, 255, 255),
        "symbol": "plane",
    },
    "arrow_right": {
        "label_ar": "➡️ سهم إشارة لليمين",
        "label_en": "➡️ Arrow Right",
        "category": "shapes",
        "kind": "arrow",
        "direction": "right",
        "bg": (255, 195, 0, 255),
        "border": (20, 20, 20, 230),
        "fg": (255, 195, 0, 255),
    },
    "arrow_left": {
        "label_ar": "⬅️ سهم إشارة لليسار",
        "label_en": "⬅️ Arrow Left",
        "category": "shapes",
        "kind": "arrow",
        "direction": "left",
        "bg": (255, 195, 0, 255),
        "border": (20, 20, 20, 230),
        "fg": (255, 195, 0, 255),
    },
    "arrow_down": {
        "label_ar": "⬇️ سهم إشارة لأسفل",
        "label_en": "⬇️ Arrow Down",
        "category": "shapes",
        "kind": "arrow",
        "direction": "down",
        "bg": (255, 75, 75, 255),
        "border": (255, 255, 255, 230),
        "fg": (255, 75, 75, 255),
    },
    "check_mark": {
        "label_ar": "✅ علامة صح (صحيح)",
        "label_en": "✅ Checkmark (Correct)",
        "category": "shapes",
        "kind": "circle_icon",
        "bg": (35, 165, 75, 248),
        "border": (255, 255, 255, 235),
        "fg": (255, 255, 255, 255),
        "symbol": "check",
    },
    "cross_mark": {
        "label_ar": "❌ علامة خطأ",
        "label_en": "❌ Cross Mark (Wrong)",
        "category": "shapes",
        "kind": "circle_icon",
        "bg": (218, 54, 51, 248),
        "border": (255, 255, 255, 235),
        "fg": (255, 255, 255, 255),
        "symbol": "cross",
    },
    "warning_badge": {
        "label_ar": "⚠️ مثلث تنبيه هام",
        "label_en": "⚠️ Warning Sign",
        "category": "shapes",
        "kind": "warning",
        "bg": (255, 185, 0, 250),
        "border": (25, 25, 25, 245),
        "fg": (20, 20, 20, 255),
    },
    "star_gold": {
        "label_ar": "⭐ نجمة ذهبية مضيئة",
        "label_en": "⭐ Golden Star",
        "category": "shapes",
        "kind": "star_shape",
        "bg": (255, 210, 30, 255),
        "border": (180, 120, 0, 240),
        "fg": (255, 245, 180, 255),
    },
    "heart_red": {
        "label_ar": "❤️ قلب أحمر",
        "label_en": "❤️ Red Heart",
        "category": "shapes",
        "kind": "heart_shape",
        "bg": (235, 40, 70, 252),
        "border": (255, 255, 255, 220),
        "fg": (255, 255, 255, 255),
    },
}


def _load_bold_font(size: int):
    for p in (
        Path("C:/Windows/Fonts/segoeuib.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/tahomabd.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ):
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def _star_polygon(cx: float, cy: float, outer_r: float, inner_r: float, points: int = 5, rot_deg: float = -90.0):
    coords = []
    step = math.pi / points
    base = math.radians(rot_deg)
    for i in range(points * 2):
        r = outer_r if i % 2 == 0 else inner_r
        ang = base + i * step
        coords.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return coords


def _draw_symbol(draw: ImageDraw.ImageDraw, symbol: str, cx: float, cy: float, r: float, color):
    if symbol == "play":
        pts = [
            (cx - r * 0.42, cy - r * 0.56),
            (cx - r * 0.42, cy + r * 0.56),
            (cx + r * 0.62, cy),
        ]
        draw.polygon(pts, fill=color)
    elif symbol == "star":
        draw.polygon(_star_polygon(cx, cy, r * 0.72, r * 0.32, 5), fill=color)
    elif symbol == "check":
        pts = [
            (cx - r * 0.52, cy + r * 0.04),
            (cx - r * 0.14, cy + r * 0.44),
            (cx + r * 0.56, cy - r * 0.40),
        ]
        draw.line(pts, fill=color, width=max(6, int(r * 0.28)), joint="curve")
    elif symbol == "cross":
        w = max(6, int(r * 0.26))
        d = r * 0.44
        draw.line([(cx - d, cy - d), (cx + d, cy + d)], fill=color, width=w)
        draw.line([(cx + d, cy - d), (cx - d, cy + d)], fill=color, width=w)
    elif symbol == "bell":
        # Dome + base + clapper
        draw.pieslice([cx - r * 0.55, cy - r * 0.62, cx + r * 0.55, cy + r * 0.45], 180, 360, fill=color)
        draw.rectangle([cx - r * 0.55, cy - r * 0.10, cx + r * 0.55, cy + r * 0.34], fill=color)
        draw.rounded_rectangle([cx - r * 0.72, cy + r * 0.26, cx + r * 0.72, cy + r * 0.46], radius=int(r * 0.1), fill=color)
        draw.ellipse([cx - r * 0.18, cy + r * 0.46, cx + r * 0.18, cy + r * 0.74], fill=color)
    elif symbol == "mic":
        # Capsule + U-stand + base
        draw.rounded_rectangle([cx - r * 0.28, cy - r * 0.68, cx + r * 0.28, cy + r * 0.08], radius=int(r * 0.28), fill=color)
        w = max(4, int(r * 0.14))
        draw.arc([cx - r * 0.50, cy - r * 0.36, cx + r * 0.50, cy + r * 0.36], 0, 180, fill=color, width=w)
        draw.line([(cx, cy + r * 0.36), (cx, cy + r * 0.68)], fill=color, width=w)
        draw.line([(cx - r * 0.34, cy + r * 0.68), (cx + r * 0.34, cy + r * 0.68)], fill=color, width=w)
    elif symbol == "camera":
        w = max(5, int(r * 0.15))
        draw.rounded_rectangle([cx - r * 0.58, cy - r * 0.58, cx + r * 0.58, cy + r * 0.58], radius=int(r * 0.28), outline=color, width=w)
        draw.ellipse([cx - r * 0.30, cy - r * 0.30, cx + r * 0.30, cy + r * 0.30], outline=color, width=w)
        draw.ellipse([cx + r * 0.28, cy - r * 0.44, cx + r * 0.44, cy - r * 0.28], fill=color)
    elif symbol == "f_letter":
        fnt = _load_bold_font(int(r * 1.45))
        draw.text((cx, cy - r * 0.05), "f", fill=color, font=fnt, anchor="mm")
    elif symbol == "phone":
        w = max(5, int(r * 0.17))
        draw.arc([cx - r * 0.56, cy - r * 0.56, cx + r * 0.56, cy + r * 0.56], 25, 245, fill=color, width=w)
        draw.ellipse([cx - r * 0.48, cy - r * 0.48, cx - r * 0.16, cy - r * 0.16], fill=color)
        draw.ellipse([cx + r * 0.16, cy + r * 0.16, cx + r * 0.48, cy + r * 0.48], fill=color)
    elif symbol == "plane":
        pts = [
            (cx - r * 0.62, cy + r * 0.02),
            (cx + r * 0.58, cy - r * 0.50),
            (cx + r * 0.18, cy + r * 0.58),
            (cx - r * 0.08, cy + r * 0.16),
        ]
        draw.polygon(pts, fill=color)
    elif symbol == "share":
        w = max(5, int(r * 0.18))
        draw.line([(cx - r * 0.42, cy + r * 0.38), (cx + r * 0.42, cy - r * 0.42)], fill=color, width=w)
        draw.polygon([(cx + r * 0.48, cy - r * 0.48), (cx + r * 0.02, cy - r * 0.46), (cx + r * 0.46, cy - r * 0.02)], fill=color)


def render_icon_pil(
    icon_key: str,
    custom_text: str = "",
    target_width: int = 220,
    is_ar: bool = True,
) -> Image.Image:
    """
    Renders a crisp, anti-aliased RGBA icon or badge at target_width (2x supersampled).
    """
    preset = ICON_PRESETS.get(icon_key, ICON_PRESETS["star_gold"])
    kind = preset.get("kind", "circle_icon")
    bg = preset.get("bg", (30, 30, 30, 240))
    border = preset.get("border", (255, 255, 255, 220))
    fg = preset.get("fg", (255, 255, 255, 255))
    symbol = preset.get("symbol", "star")

    target_width = max(32, min(1400, int(target_width)))

    if kind == "badge":
        label = (custom_text or "").strip()
        if not label:
            label = preset.get("default_text_ar" if is_ar else "default_text_en", "SUBSCRIBE")
        disp_label = prepare_arabic_for_rendering(label)

        # Supersampled canvas
        ss_h = 180
        fnt = _load_bold_font(62)
        dummy = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        try:
            bb = dummy.textbbox((0, 0), disp_label, font=fnt)
            tw = bb[2] - bb[0]
        except Exception:
            tw = len(disp_label) * 34
        ss_w = max(420, tw + 230)

        im = Image.new("RGBA", (ss_w, ss_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        # Drop shadow
        d.rounded_rectangle([8, 12, ss_w - 4, ss_h - 4], radius=ss_h // 2, fill=(0, 0, 0, 95))
        d.rounded_rectangle([4, 4, ss_w - 10, ss_h - 12], radius=ss_h // 2, fill=bg, outline=border, width=6)

        icon_cx = 86
        icon_cy = (ss_h - 8) // 2
        d.ellipse([icon_cx - 50, icon_cy - 50, icon_cx + 50, icon_cy + 50], fill=(255, 255, 255, 38))
        _draw_symbol(d, symbol, icon_cx, icon_cy, 40, fg)

        text_cx = 152 + (ss_w - 175) // 2
        d.text((text_cx + 3, icon_cy + 3), disp_label, fill=(0, 0, 0, 160), font=fnt, anchor="mm")
        d.text((text_cx, icon_cy), disp_label, fill=fg, font=fnt, anchor="mm")

        out_h = max(20, int(round(target_width * (ss_h / ss_w))))
        return im.resize((target_width, out_h), Image.Resampling.LANCZOS)

    # Square/Icon canvas (2x supersampled 320x320)
    S = 320
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = S / 2.0, S / 2.0

    if kind == "islamic_star":
        # Two overlapping rotated squares (Rub el Hizb 8-pointed star) + center medallion
        pts1 = _star_polygon(cx, cy, 138, 102, points=8, rot_deg=-22.5)
        d.polygon(_star_polygon(cx + 4, cy + 6, 138, 102, points=8, rot_deg=-22.5), fill=(0, 0, 0, 100))
        d.polygon(pts1, fill=bg, outline=border)
        # Bold golden outline
        for i in range(len(pts1)):
            d.line([pts1[i], pts1[(i + 1) % len(pts1)]], fill=border, width=8)
        d.ellipse([cx - 68, cy - 68, cx + 68, cy + 68], fill=(10, 55, 38, 255), outline=border, width=6)
        d.polygon(_star_polygon(cx, cy, 42, 18, points=8, rot_deg=0), fill=fg)

    elif kind == "yt_box":
        h_box = 224
        y0 = (S - h_box) // 2
        d.rounded_rectangle([18, y0 + 8, S - 10, y0 + h_box + 8], radius=54, fill=(0, 0, 0, 95))
        d.rounded_rectangle([14, y0, S - 14, y0 + h_box], radius=54, fill=bg, outline=border, width=5)
        _draw_symbol(d, "play", cx + 6, cy, 68, fg)

    elif kind == "insta_box":
        d.rounded_rectangle([26, 32, S - 18, S - 12], radius=72, fill=(0, 0, 0, 95))
        d.rounded_rectangle([22, 22, S - 22, S - 22], radius=72, fill=bg, outline=border, width=7)
        _draw_symbol(d, "camera", cx, cy, 96, fg)

    elif kind == "arrow":
        direction = preset.get("direction", "right")
        pts = [
            (36, 112),
            (184, 112),
            (184, 52),
            (292, 160),
            (184, 268),
            (184, 208),
            (36, 208),
        ]
        d.polygon([(x + 5, y + 7) for x, y in pts], fill=(0, 0, 0, 110))
        d.polygon(pts, fill=bg)
        for i in range(len(pts)):
            d.line([pts[i], pts[(i + 1) % len(pts)]], fill=border, width=7)
        if direction == "left":
            im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        elif direction == "down":
            im = im.rotate(-90, expand=True)
        elif direction == "up":
            im = im.rotate(90, expand=True)

    elif kind == "warning":
        pts = [(cx, 28), (S - 24, S - 34), (24, S - 34)]
        d.polygon([(x + 4, y + 6) for x, y in pts], fill=(0, 0, 0, 100))
        d.polygon(pts, fill=bg)
        for i in range(3):
            d.line([pts[i], pts[(i + 1) % 3]], fill=border, width=10)
        fnt = _load_bold_font(155)
        d.text((cx, cy + 36), "!", fill=fg, font=fnt, anchor="mm")

    elif kind == "star_shape":
        pts = _star_polygon(cx, cy, 142, 62, points=5)
        d.polygon([(x + 4, y + 6) for x, y in pts], fill=(0, 0, 0, 100))
        d.polygon(pts, fill=bg)
        for i in range(len(pts)):
            d.line([pts[i], pts[(i + 1) % len(pts)]], fill=border, width=6)

    elif kind == "heart_shape":
        # Parametric smooth heart
        pts = []
        for deg in range(0, 360, 4):
            t = math.radians(deg)
            hx = 16 * (math.sin(t) ** 3)
            hy = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
            pts.append((cx + hx * 8.0, cy + hy * 8.0 + 10))
        d.polygon([(x + 4, y + 6) for x, y in pts], fill=(0, 0, 0, 95))
        d.polygon(pts, fill=bg)
        for i in range(len(pts)):
            d.line([pts[i], pts[(i + 1) % len(pts)]], fill=border, width=5)

    else:
        # Default circle_icon
        d.ellipse([26, 32, S - 18, S - 12], fill=(0, 0, 0, 95))
        d.ellipse([22, 22, S - 22, S - 22], fill=bg, outline=border, width=8)
        _draw_symbol(d, symbol, cx, cy, 90, fg)

    return im.resize((target_width, target_width), Image.Resampling.LANCZOS)


def apply_opacity_and_rotation(
    img: Image.Image,
    opacity: float = 1.0,
    rotation_deg: float = 0.0,
) -> Image.Image:
    """
    Applies RGBA alpha multiplier and smooth anti-aliased rotation to any overlay image.
    """
    out = img.convert("RGBA")
    op = max(0.05, min(1.0, float(opacity if opacity is not None else 1.0)))
    if op < 0.995:
        r, g, b, a = out.split()
        a = a.point(lambda p: int(p * op))
        out = Image.merge("RGBA", (r, g, b, a))

    rot = float(rotation_deg if rotation_deg is not None else 0.0)
    if abs(rot) > 0.25:
        out = out.rotate(-rot, expand=True, resample=Image.Resampling.BICUBIC)
    return out


def render_media_overlay_pil(
    item: Dict[str, Any],
    canvas_w: int,
    canvas_h: int,
    is_ar: bool = True,
) -> Optional[Image.Image]:
    """
    Renders either an 'icon' preset or a custom 'image' file item scaled relative to canvas_w,
    with opacity and rotation applied.
    """
    item_type = item.get("type", "icon")
    scale = max(0.03, min(1.5, float(item.get("scale", 0.18))))
    target_w = max(24, int(round(canvas_w * scale)))
    opacity = float(item.get("opacity", 1.0))
    rotation = float(item.get("rotation", 0.0))

    base_im = None
    if item_type == "image":
        img_p = str(item.get("path", "")).strip()
        if img_p and Path(img_p).is_file():
            try:
                with Image.open(img_p) as src:
                    ow, oh = src.size
                    th = max(16, int(round(target_w * (oh / max(1, ow)))))
                    base_im = src.convert("RGBA").resize((target_w, th), Image.Resampling.LANCZOS)
            except Exception:
                base_im = None
    else:
        icon_key = item.get("icon_key", "subscribe_ar")
        custom_text = item.get("text", "")
        base_im = render_icon_pil(icon_key, custom_text=custom_text, target_width=target_w, is_ar=is_ar)

    if base_im is None:
        return None

    return apply_opacity_and_rotation(base_im, opacity=opacity, rotation_deg=rotation)
