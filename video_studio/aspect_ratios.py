"""
Aspect Ratio, Canvas Dimensions & DaVinci-Style Transform Engine
Supports Reels/Shorts (9:16), Landscape (16:9), Square (1:1), Portrait (4:5), and Classic (4:3),
with full interactive Zoom, Position X (Left/Right), Position Y (Up/Down), and Horizontal Flip.
Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

from PIL import Image

ASPECT_RATIOS = {
    "original": {
        "label_en": "Keep Original",
        "label_ar": "نفس أبعاد ونسبة الفيديو الأصلي",
        "w": None,
        "h": None,
        "ratio": None,
    },
    "9:16": {
        "label_en": "9:16 (Reels / TikTok / Shorts - 1080x1920)",
        "label_ar": "9:16 (ريلز / تيك توك / شورتس - 1080×1920)",
        "w": 1080,
        "h": 1920,
        "ratio": 9 / 16,
    },
    "16:9": {
        "label_en": "16:9 (YouTube / Widescreen - 1920x1080)",
        "label_ar": "16:9 (يوتيوب وشاشات العرض - 1920×1080)",
        "w": 1920,
        "h": 1080,
        "ratio": 16 / 9,
    },
    "1:1": {
        "label_en": "1:1 (Instagram / Facebook Square - 1080x1080)",
        "label_ar": "1:1 (مربع إنستغرام وفيسبوك - 1080×1080)",
        "w": 1080,
        "h": 1080,
        "ratio": 1.0,
    },
    "4:5": {
        "label_en": "4:5 (Instagram Portrait Feed - 1080x1350)",
        "label_ar": "4:5 (عمودي إنستغرام بورتريت - 1080×1350)",
        "w": 1080,
        "h": 1350,
        "ratio": 4 / 5,
    },
    "4:3": {
        "label_en": "4:3 (Standard Classic - 1440x1080)",
        "label_ar": "4:3 (كلاسيكي تقليدي - 1440×1080)",
        "w": 1440,
        "h": 1080,
        "ratio": 4 / 3,
    },
}

FIT_MODES = {
    "crop": {
        "label_en": "Fill & Crop",
        "label_ar": "ملء وتعبئة الكادر (Fill / Crop)",
    },
    "blur": {
        "label_en": "Blur Background",
        "label_ar": "خلفية ضبابية (Blur)",
    },
    "pad": {
        "label_en": "Fit / Letterbox",
        "label_ar": "احتواء كامل (Fit / Letterbox)",
    },
}


def _even(val: int, minimum: int = 2) -> int:
    v = max(minimum, int(round(val)))
    return v - (v % 2) if v > minimum else minimum


def get_aspect_ratio_dimensions(target_ratio="original", in_w=1920, in_h=1080):
    """
    Returns (out_w, out_h) for target aspect ratio based on input dimensions.
    """
    try:
        in_w = int(in_w) if in_w else 1920
        in_h = int(in_h) if in_h else 1080
    except (ValueError, TypeError):
        in_w, in_h = 1920, 1080

    if target_ratio not in ASPECT_RATIOS or target_ratio == "original":
        return _even(in_w), _even(in_h)

    preset = ASPECT_RATIOS[target_ratio]
    pref_w = preset["w"]
    pref_h = preset["h"]

    # Adapt resolution if input is lower resolution (e.g. 720p or 480p)
    if in_h and in_h < 800 and pref_h > 1280:
        scale_down = max(0.5, in_h / 1080.0)
        out_w = _even(pref_w * scale_down)
        out_h = _even(pref_h * scale_down)
        return out_w, out_h

    return pref_w, pref_h


def compute_video_transform_geometry(
    in_w: float,
    in_h: float,
    canvas_w: float,
    canvas_h: float,
    fit_mode: str = "crop",
    zoom: float = 1.0,
    pan_x: float = 0.0,
    pan_y: float = 0.0,
    clamp_edges: bool = True,
    force_even: bool = False,
):
    """
    Computes exact transformed foreground video dimensions and top-left placement
    on (canvas_w, canvas_h).
    - zoom = 1.0 in 'crop' mode fills the entire canvas cleanly (like DaVinci Resolve).
    - pan_x, pan_y are normalized offsets relative to canvas_w, canvas_h
      (+pan_x shifts image right, -pan_x shifts image left; +pan_y shifts down, -pan_y shifts up).
    Returns: (scaled_w, scaled_h, vid_x, vid_y)
    """
    in_w = max(2.0, float(in_w or 1920))
    in_h = max(2.0, float(in_h or 1080))
    canvas_w = max(2.0, float(canvas_w or 1080))
    canvas_h = max(2.0, float(canvas_h or 1920))
    zoom = max(0.15, min(5.0, float(zoom if zoom is not None else 1.0)))
    pan_x = float(pan_x if pan_x is not None else 0.0)
    pan_y = float(pan_y if pan_y is not None else 0.0)

    if fit_mode == "crop":
        base_scale = max(canvas_w / in_w, canvas_h / in_h)
    else:
        base_scale = min(canvas_w / in_w, canvas_h / in_h)

    eff_scale = base_scale * zoom
    raw_sw = in_w * eff_scale
    raw_sh = in_h * eff_scale

    if force_even:
        scaled_w = _even(raw_sw, 2)
        scaled_h = _even(raw_sh, 2)
    else:
        scaled_w = max(2.0, raw_sw)
        scaled_h = max(2.0, raw_sh)

    vid_x = (canvas_w - scaled_w) / 2.0 + (pan_x * canvas_w)
    vid_y = (canvas_h - scaled_h) / 2.0 + (pan_y * canvas_h)

    # Smart edge clamping in DaVinci fill mode so panning doesn't accidentally reveal black bars
    if clamp_edges and fit_mode == "crop":
        if scaled_w >= canvas_w:
            vid_x = max(canvas_w - scaled_w, min(0.0, vid_x))
        if scaled_h >= canvas_h:
            vid_y = max(canvas_h - scaled_h, min(0.0, vid_y))

    if force_even:
        return int(scaled_w), int(scaled_h), int(round(vid_x)), int(round(vid_y))
    return scaled_w, scaled_h, vid_x, vid_y


def clamp_pan_for_transform(
    in_w: float,
    in_h: float,
    canvas_w: float,
    canvas_h: float,
    fit_mode: str,
    zoom: float,
    pan_x: float,
    pan_y: float,
    clamp_edges: bool = True,
):
    """
    Returns (clamped_pan_x, clamped_pan_y) so UI sliders and mouse drag stay within clean bounds.
    """
    pan_x = max(-1.5, min(1.5, float(pan_x)))
    pan_y = max(-1.5, min(1.5, float(pan_y)))
    if not clamp_edges or fit_mode != "crop":
        return round(pan_x, 4), round(pan_y, 4)

    in_w = max(2.0, float(in_w or 1920))
    in_h = max(2.0, float(in_h or 1080))
    canvas_w = max(2.0, float(canvas_w or 1080))
    canvas_h = max(2.0, float(canvas_h or 1920))
    zoom = max(0.15, min(5.0, float(zoom or 1.0)))

    base_scale = max(canvas_w / in_w, canvas_h / in_h)
    sw = in_w * base_scale * zoom
    sh = in_h * base_scale * zoom

    if sw >= canvas_w:
        max_px = (sw - canvas_w) / (2.0 * canvas_w)
        pan_x = max(-max_px, min(max_px, pan_x))
    if sh >= canvas_h:
        max_py = (sh - canvas_h) / (2.0 * canvas_h)
        pan_y = max(-max_py, min(max_py, pan_y))

    return round(pan_x, 4), round(pan_y, 4)


def render_transformed_pil_frame(
    pil_img: Image.Image,
    box_w: int,
    box_h: int,
    fit_mode: str = "crop",
    zoom: float = 1.0,
    pan_x: float = 0.0,
    pan_y: float = 0.0,
    flip_h: bool = False,
    clamp_edges: bool = True,
) -> Image.Image:
    """
    Ultra-fast sub-pixel accurate Pillow renderer for the Studio Viewer Canvas.
    Matches FFmpeg export framing pixel-for-pixel.
    """
    box_w = max(2, int(box_w))
    box_h = max(2, int(box_h))
    src = pil_img.convert("RGB") if pil_img.mode != "RGB" else pil_img
    if flip_h:
        src = src.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    orig_w, orig_h = src.size
    scaled_w, scaled_h, vid_x, vid_y = compute_video_transform_geometry(
        orig_w,
        orig_h,
        box_w,
        box_h,
        fit_mode=fit_mode,
        zoom=zoom,
        pan_x=pan_x,
        pan_y=pan_y,
        clamp_edges=clamp_edges,
        force_even=False,
    )

    ix0 = int(max(0, round(vid_x)))
    iy0 = int(max(0, round(vid_y)))
    ix1 = int(min(box_w, round(vid_x + scaled_w)))
    iy1 = int(min(box_h, round(vid_y + scaled_h)))

    # Prepare base canvas if foreground does not cover 100%
    covers_all = (ix0 <= 0 and iy0 <= 0 and ix1 >= box_w and iy1 >= box_h)
    if not covers_all:
        if fit_mode == "blur":
            bg_scale = max(box_w / max(1, orig_w), box_h / max(1, orig_h))
            bw = orig_w * bg_scale
            bh = orig_h * bg_scale
            bx0 = max(0.0, (bw - box_w) / 2.0) * (orig_w / bw)
            by0 = max(0.0, (bh - box_h) / 2.0) * (orig_h / bh)
            bx1 = bx0 + box_w * (orig_w / bw)
            by1 = by0 + box_h * (orig_h / bh)
            tiny_w = max(14, box_w // 12)
            tiny_h = max(14, box_h // 12)
            bg_tiny = src.transform(
                (tiny_w, tiny_h),
                Image.Transform.EXTENT,
                (bx0, by0, bx1, by1),
                resample=Image.Resampling.BILINEAR,
            )
            canvas = bg_tiny.resize((box_w, box_h), Image.Resampling.BILINEAR)
        else:
            canvas = Image.new("RGB", (box_w, box_h), (0, 0, 0))
    else:
        canvas = None

    if ix1 > ix0 and iy1 > iy0:
        out_vis_w = ix1 - ix0
        out_vis_h = iy1 - iy0
        sx0 = (ix0 - vid_x) * (orig_w / scaled_w)
        sy0 = (iy0 - vid_y) * (orig_h / scaled_h)
        sx1 = (ix1 - vid_x) * (orig_w / scaled_w)
        sy1 = (iy1 - vid_y) * (orig_h / scaled_h)
        fg_patch = src.transform(
            (out_vis_w, out_vis_h),
            Image.Transform.EXTENT,
            (sx0, sy0, sx1, sy1),
            resample=Image.Resampling.BILINEAR,
        )
        if covers_all:
            return fg_patch
        canvas.paste(fg_patch, (ix0, iy0))

    return canvas if canvas is not None else Image.new("RGB", (box_w, box_h), (0, 0, 0))


def build_aspect_ratio_filter(
    target_ratio="original",
    fit_mode="crop",
    in_w=1920,
    in_h=1080,
    input_label="0:v",
    output_label="v_ratio",
    video_transform=None,
):
    """
    Constructs an FFmpeg filtergraph segment to convert video to target aspect ratio
    with full DaVinci Transform support (zoom, pan_x, pan_y, flip_h, clamp_edges).
    Returns: (filter_str, out_w, out_h)
    """
    try:
        in_w = int(in_w) if in_w else 1920
        in_h = int(in_h) if in_h else 1080
    except (ValueError, TypeError):
        in_w, in_h = 1920, 1080

    out_w, out_h = get_aspect_ratio_dimensions(target_ratio, in_w, in_h)

    vt = video_transform or {}
    zoom = float(vt.get("zoom", 1.0) if vt.get("zoom") is not None else 1.0)
    pan_x = float(vt.get("pan_x", 0.0) if vt.get("pan_x") is not None else 0.0)
    pan_y = float(vt.get("pan_y", 0.0) if vt.get("pan_y") is not None else 0.0)
    flip_h = bool(vt.get("flip_h", False))
    clamp_edges = bool(vt.get("clamp_edges", True))

    has_custom_transform = (
        abs(zoom - 1.0) > 0.005
        or abs(pan_x) > 0.002
        or abs(pan_y) > 0.002
        or flip_h
    )

    same_aspect = bool(in_w and in_h and abs((in_w / in_h) - (out_w / out_h)) < 0.01)

    # Fast path when no aspect change and no custom pan/zoom/flip
    if (target_ratio == "original" or same_aspect) and not has_custom_transform:
        if in_w == out_w and in_h == out_h:
            return f"[{input_label}]setsar=1[{output_label}]", out_w, out_h
        return f"[{input_label}]scale={out_w}:{out_h},setsar=1[{output_label}]", out_w, out_h

    # Compute exact pixel placement matching Pillow preview
    eff_fit = "crop" if (target_ratio == "original" and has_custom_transform and fit_mode not in ("blur", "pad")) else fit_mode
    scaled_w, scaled_h, vid_x, vid_y = compute_video_transform_geometry(
        in_w,
        in_h,
        out_w,
        out_h,
        fit_mode=eff_fit,
        zoom=zoom,
        pan_x=pan_x,
        pan_y=pan_y,
        clamp_edges=clamp_edges,
        force_even=True,
    )

    flip_prefix = "hflip," if flip_h else ""

    # Compute visible intersection on [0, out_w] x [0, out_h]
    ix0 = max(0, min(out_w - 2, vid_x))
    iy0 = max(0, min(out_h - 2, vid_y))
    ix1 = max(ix0 + 2, min(out_w, vid_x + scaled_w))
    iy1 = max(iy0 + 2, min(out_h, vid_y + scaled_h))

    vis_w = _even(ix1 - ix0, 2)
    vis_h = _even(iy1 - iy0, 2)
    if ix0 + vis_w > out_w:
        ix0 = max(0, out_w - vis_w)
    if iy0 + vis_h > out_h:
        iy0 = max(0, out_h - vis_h)

    crop_x = max(0, min(max(0, scaled_w - vis_w), ix0 - vid_x))
    crop_y = max(0, min(max(0, scaled_h - vis_h), iy0 - vid_y))

    covers_full_canvas = (vis_w == out_w and vis_h == out_h and ix0 == 0 and iy0 == 0)

    if covers_full_canvas:
        filter_str = (
            f"[{input_label}]{flip_prefix}scale={scaled_w}:{scaled_h},"
            f"crop={out_w}:{out_h}:{crop_x}:{crop_y},setsar=1[{output_label}]"
        )
    elif eff_fit == "blur":
        uid = output_label.replace("[", "").replace("]", "")
        filter_str = (
            f"[{input_label}]{flip_prefix}split=2[bg_in_{uid}][fg_in_{uid}];"
            f"[bg_in_{uid}]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
            f"crop={out_w}:{out_h},boxblur=20:5[bg_{uid}];"
            f"[fg_in_{uid}]scale={scaled_w}:{scaled_h},"
            f"crop={vis_w}:{vis_h}:{crop_x}:{crop_y}[fg_{uid}];"
            f"[bg_{uid}][fg_{uid}]overlay={ix0}:{iy0},setsar=1[{output_label}]"
        )
    else:
        filter_str = (
            f"[{input_label}]{flip_prefix}scale={scaled_w}:{scaled_h},"
            f"crop={vis_w}:{vis_h}:{crop_x}:{crop_y},"
            f"pad={out_w}:{out_h}:{ix0}:{iy0}:color=black,setsar=1[{output_label}]"
        )

    return filter_str, out_w, out_h
