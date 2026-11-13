"""
Subtitle Styling and ASS String Generation
Supports ASS force_style attributes: FontName, FontSize, PrimaryColour, BackColour, BorderStyle, Outline, Shadow, Alignment, MarginV.
Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

# Subtitle styling constants
# ASS colors are encoded in BGR hex format: &HAABBGGRR (Alpha, Blue, Green, Red)
SUBTITLE_COLORS = {
    "yellow": "&H0000FFFF",  # Bright modern yellow (CapCut default)
    "white": "&H00FFFFFF",   # Crisp white
    "cyan": "&H00FFFF00",    # Cyan / Sky blue
    "lime": "&H0000FF00",    # Lime green
    "orange": "&H000080FF",  # Warm orange
    "pink": "&H00CBC0FF",    # Pastel pink
    "red": "&H000000FF",     # Bold red
    "black": "&H00000000",   # Pure black
}

# Outline and background box configurations for ASS
SUBTITLE_OUTLINES = {
    "thick_black": {"w": 2.8, "sh": 1.5, "c": "&H00000000", "style": 1, "back": "&H80000000"},
    "medium_black": {"w": 1.8, "sh": 1.0, "c": "&H00000000", "style": 1, "back": "&H80000000"},
    "thin_black": {"w": 1.0, "sh": 0.0, "c": "&H00000000", "style": 1, "back": "&H80000000"},
    "thick_white": {"w": 2.5, "sh": 1.0, "c": "&H00FFFFFF", "style": 1, "back": "&H80000000"},
    "none": {"w": 0.0, "sh": 0.0, "c": "&H00000000", "style": 1, "back": "&H80000000"},
    "box_semi": {"w": 2.0, "sh": 0.0, "c": "&H00000000", "style": 3, "back": "&H80000000"},
    "box_dark": {"w": 2.0, "sh": 0.0, "c": "&H00000000", "style": 3, "back": "&H80000000"},
    "box_black": {"w": 2.0, "sh": 0.0, "c": "&H00000000", "style": 3, "back": "&H00000000"},
    "box_solid": {"w": 2.0, "sh": 0.0, "c": "&H00000000", "style": 3, "back": "&H00000000"},
    "box_navy": {"w": 2.0, "sh": 0.0, "c": "&H00000000", "style": 3, "back": "&H40501000"},
    "box_blue": {"w": 2.0, "sh": 0.0, "c": "&H00000000", "style": 3, "back": "&H60802010"},
}

# ASS alignment standard (Numpad layout)
SUBTITLE_ALIGNMENTS = {
    ("bottom", "center"): 2,
    ("bottom", "left"): 1,
    ("bottom", "right"): 3,
    ("middle", "center"): 5,
    ("middle", "left"): 4,
    ("middle", "right"): 6,
    ("top", "center"): 8,
    ("top", "left"): 7,
    ("top", "right"): 9,
}


def build_subtitle_style_string(
    font_name="Segoe UI",
    font_size=None,
    text_color="yellow",
    outline_style="box_semi",
    bold=True,
    italic=False,
    position_v="bottom",
    position_h="center",
    margin_v=None,
    video_h=1080,
):
    """
    Builds a formatted ASS force_style string for FFmpeg's subtitles filter.
    """
    if font_size in (None, "", "auto", "Auto"):
        calc_font_size = max(18, int(video_h * 0.034))
    else:
        try:
            calc_font_size = int(font_size)
        except Exception:
            calc_font_size = max(18, int(video_h * 0.034))

    calc_margin_v = margin_v if (margin_v and margin_v != "auto") else max(25, int(video_h * 0.055))
    try:
        calc_margin_v = int(calc_margin_v)
    except Exception:
        calc_margin_v = 35

    prim_col = SUBTITLE_COLORS.get(text_color, text_color if str(text_color).startswith("&H") else "&H0000FFFF")
    out_info = SUBTITLE_OUTLINES.get(outline_style, SUBTITLE_OUTLINES["box_semi"])
    align_val = SUBTITLE_ALIGNMENTS.get((position_v, position_h), 2)
    b_val = 1 if bold else 0
    it_val = 1 if italic else 0

    oc = out_info["c"]
    ob = out_info["back"]
    ost = out_info["style"]
    ow = out_info["w"]
    osh = out_info["sh"]

    return (
        f"FontName={font_name},"
        f"FontSize={calc_font_size},"
        f"Bold={b_val},"
        f"Italic={it_val},"
        f"PrimaryColour={prim_col},"
        f"OutlineColour={oc},"
        f"BackColour={ob},"
        f"BorderStyle={ost},"
        f"Outline={ow},"
        f"Shadow={osh},"
        f"Alignment={align_val},"
        f"MarginV={calc_margin_v}"
    )
