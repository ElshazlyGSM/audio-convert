"""
Arabic Text Shaping & Bidirectional Support Module
Ensures 100% accurate, connected, right-to-left Arabic rendering in Pillow, Tkinter Canvas, and Video Compositing.
Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

import re
from typing import Optional

# Arabic Unicode Ranges
ARABIC_CHAR_PATTERN = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)

# Built-in contextual reshaping table (Presentation Forms-B)
# [isolated, final, initial, medial]
# None or isolated if form doesn't exist
ARABIC_GLYPHS = {
    0x0621: (0xFE80, 0xFE80, 0xFE80, 0xFE80),  # HAMZA
    0x0622: (0xFE81, 0xFE82, 0xFE81, 0xFE82),  # ALEF WITH MADDA
    0x0623: (0xFE83, 0xFE84, 0xFE83, 0xFE84),  # ALEF WITH HAMZA ABOVE
    0x0624: (0xFE85, 0xFE86, 0xFE85, 0xFE86),  # WAW WITH HAMZA ABOVE
    0x0625: (0xFE87, 0xFE88, 0xFE87, 0xFE88),  # ALEF WITH HAMZA BELOW
    0x0626: (0xFE89, 0xFE8A, 0xFE8B, 0xFE8C),  # YEH WITH HAMZA ABOVE
    0x0627: (0xFE8D, 0xFE8E, 0xFE8D, 0xFE8E),  # ALEF
    0x0628: (0xFE8F, 0xFE90, 0xFE91, 0xFE92),  # BEH
    0x0629: (0xFE93, 0xFE94, 0xFE93, 0xFE94),  # TEH MARBUTA
    0x062A: (0xFE95, 0xFE96, 0xFE97, 0xFE98),  # TEH
    0x062B: (0xFE99, 0xFE9A, 0xFE9B, 0xFE9C),  # THEH
    0x062C: (0xFE9D, 0xFE9E, 0xFE9F, 0xFEA0),  # JEEM
    0x062D: (0xFEA1, 0xFEA2, 0xFEA3, 0xFEA4),  # HAH
    0x062E: (0xFEA5, 0xFEA6, 0xFEA7, 0xFEA8),  # KHAH
    0x062F: (0xFEA9, 0xFEAA, 0xFEA9, 0xFEAA),  # DAL
    0x0630: (0xFEAB, 0xFEAC, 0xFEAB, 0xFEAC),  # THAL
    0x0631: (0xFEAD, 0xFEAE, 0xFEAD, 0xFEAE),  # REH
    0x0632: (0xFEAF, 0xFEB0, 0xFEAF, 0xFEB0),  # ZAIN
    0x0633: (0xFEB1, 0xFEB2, 0xFEB3, 0xFEB4),  # SEEN
    0x0634: (0xFEB5, 0xFEB6, 0xFEB7, 0xFEB8),  # SHEEN
    0x0635: (0xFEB9, 0xFEBA, 0xFEBB, 0xFEBC),  # SAD
    0x0636: (0xFEBD, 0xFEBE, 0xFEBF, 0xFEC0),  # DAD
    0x0637: (0xFEC1, 0xFEC2, 0xFEC3, 0xFEC4),  # TAH
    0x0638: (0xFEC5, 0xFEC6, 0xFEC7, 0xFEC8),  # ZAH
    0x0639: (0xFEC9, 0xFECA, 0xFECB, 0xFECC),  # AIN
    0x063A: (0xFECD, 0xFECE, 0xFECF, 0xFED0),  # GHAIN
    0x0641: (0xFED1, 0xFED2, 0xFED3, 0xFED4),  # FEH
    0x0642: (0xFED5, 0xFED6, 0xFED7, 0xFED8),  # QAF
    0x0643: (0xFED9, 0xFEDA, 0xFEDB, 0xFEDC),  # KAF
    0x0644: (0xFEDD, 0xFEDE, 0xFEDF, 0xFEE0),  # LAM
    0x0645: (0xFEE1, 0xFEE2, 0xFEE3, 0xFEE4),  # MEEM
    0x0646: (0xFEE5, 0xFEE6, 0xFEE7, 0xFEE8),  # NOON
    0x0647: (0xFEE9, 0xFEEA, 0xFEEB, 0xFEEC),  # HEH
    0x0648: (0xFEED, 0xFEEE, 0xFEED, 0xFEEE),  # WAW
    0x0649: (0xFEEF, 0xFEF0, 0xFEBF, 0xFEF0),  # ALEF MAKSURA
    0x064A: (0xFEF1, 0xFEF2, 0xFEF3, 0xFEF4),  # YEH
    0x067E: (0xFB56, 0xFB57, 0xFB58, 0xFB59),  # PEH
    0x0686: (0xFB7A, 0xFB7B, 0xFB7C, 0xFB7D),  # TCHEH
    0x0698: (0xFB8A, 0xFB8B, 0xFB8A, 0xFB8B),  # JEH
    0x06AF: (0xFB92, 0xFB93, 0xFB94, 0xFB95),  # GAF
}

# Lam-Alef Ligatures: (isolated, final)
LAM_ALEF_LIGATURES = {
    0x0622: (0xFEF5, 0xFEF6),  # LAM + ALEF WITH MADDA
    0x0623: (0xFEF7, 0xFEF8),  # LAM + ALEF WITH HAMZA ABOVE
    0x0625: (0xFEF9, 0xFEFA),  # LAM + ALEF WITH HAMZA BELOW
    0x0627: (0xFEFB, 0xFEFC),  # LAM + ALEF
}

# Letters that connect ONLY to the right (never to the left / forward)
RIGHT_JOINING_ONLY = {
    0x0621, 0x0622, 0x0623, 0x0624, 0x0625, 0x0627, 0x0629,
    0x062F, 0x0630, 0x0631, 0x0632, 0x0648, 0x0649, 0x0698,
}

# Diacritics (Harakat) to ignore during connection analysis
ARABIC_HARAKAT = set(range(0x064B, 0x0653)) | {0x0670}


def has_arabic(text: Optional[str]) -> bool:
    """Checks whether the text contains any Arabic characters."""
    if not text:
        return False
    return bool(ARABIC_CHAR_PATTERN.search(text))


def _builtin_reshape(text: str) -> str:
    """
    Pure Python fallback Arabic contextual reshaper.
    Connects Arabic letters into proper Initial/Medial/Final/Isolated forms and handles Lam-Alef.
    """
    if not text:
        return ""

    chars = list(text)
    n = len(chars)
    result = []
    i = 0

    while i < n:
        code = ord(chars[i])

        # Skip Harakat / non-joining
        if code in ARABIC_HARAKAT:
            result.append(chars[i])
            i += 1
            continue

        # Check for Lam-Alef ligature
        if code == 0x0644 and (i + 1) < n:
            next_code = ord(chars[i + 1])
            if next_code in LAM_ALEF_LIGATURES:
                prev_connected = False
                if result:
                    prev_c = ord(result[-1])
                    prev_connected = (prev_c in ARABIC_GLYPHS) and (prev_c not in RIGHT_JOINING_ONLY)
                lig = LAM_ALEF_LIGATURES[next_code][1] if prev_connected else LAM_ALEF_LIGATURES[next_code][0]
                result.append(chr(lig))
                i += 2
                continue

        if code not in ARABIC_GLYPHS:
            result.append(chars[i])
            i += 1
            continue

        # Look back to see if connected on the right
        prev_connected = False
        k = i - 1
        while k >= 0 and ord(chars[k]) in ARABIC_HARAKAT:
            k -= 1
        if k >= 0:
            prev_code = ord(chars[k])
            if prev_code in ARABIC_GLYPHS and prev_code not in RIGHT_JOINING_ONLY:
                prev_connected = True

        # Look forward to see if connected on the left
        next_connected = False
        if code not in RIGHT_JOINING_ONLY:
            k = i + 1
            while k < n and ord(chars[k]) in ARABIC_HARAKAT:
                k += 1
            if k < n:
                next_code = ord(chars[k])
                if next_code in ARABIC_GLYPHS:
                    next_connected = True

        # Choose form: 0=isolated, 1=final, 2=initial, 3=medial
        if prev_connected and next_connected:
            form = 3
        elif prev_connected:
            form = 1
        elif next_connected:
            form = 2
        else:
            form = 0

        shaped_code = ARABIC_GLYPHS[code][form]
        result.append(chr(shaped_code))
        i += 1

    return "".join(result)


def _builtin_bidi(text: str) -> str:
    """
    Pure Python fallback bidirectional reordering for visual LTR engines.
    Reverses Arabic word runs while keeping numbers and Latin words in proper order.
    """
    if not text:
        return ""

    tokens = re.split(r"(\s+|[0-9]+|[a-zA-Z]+|[^\w\s\u0600-\u06FF])", text)
    tokens = [t for t in tokens if t]

    # Reorder Arabic segments right-to-left
    out_tokens = []
    arabic_run = []

    for tok in tokens:
        if has_arabic(tok):
            arabic_run.append(tok[::-1])
        elif tok.isspace():
            if arabic_run:
                arabic_run.append(tok)
            else:
                out_tokens.append(tok)
        else:
            if arabic_run:
                out_tokens.extend(reversed(arabic_run))
                arabic_run = []
            out_tokens.append(tok)

    if arabic_run:
        out_tokens.extend(reversed(arabic_run))

    return "".join(out_tokens)


def reshape_arabic(text: str) -> str:
    """Reshapes Arabic characters to their contextual presentation forms."""
    if not text or not has_arabic(text):
        return text

    try:
        import arabic_reshaper
        return arabic_reshaper.reshape(text)
    except Exception:
        return _builtin_reshape(text)


def bidi_reorder(text: str) -> str:
    """Applies bidirectional visual reordering for LTR rendering engines."""
    if not text or not has_arabic(text):
        return text

    try:
        from bidi.algorithm import get_display
        return get_display(text)
    except Exception:
        return _builtin_bidi(text)


def prepare_arabic_for_rendering(text: str) -> str:
    """
    Complete solution for rendering Arabic in Pillow, Tkinter Canvas, or FFmpeg overlays.
    1. Checks if string contains Arabic characters.
    2. Reshapes characters to connected presentation glyphs.
    3. Reorders bidirectional text into visual layout.
    """
    if not text or not has_arabic(text):
        return text

    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        reshaped = _builtin_reshape(text)
        return _builtin_bidi(reshaped)
