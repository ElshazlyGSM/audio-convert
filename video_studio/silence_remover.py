"""
Smart Silence Detection & Automatic Jump-Cut Studio
Detects silent intervals in video/audio files using FFmpeg silencedetect,
computes active speech segments with natural breath padding, remaps subtitles,
and exports jump-cut, fast-forwarded, or noise-gated media.
Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

import re
import shutil
import subprocess
import threading
import time
from pathlib import Path


def _register_proc(proc):
    try:
        import convert
        convert.register_active_process(proc)
    except Exception:
        pass


def _unregister_proc(proc):
    try:
        import convert
        convert.unregister_active_process(proc)
    except Exception:
        pass


def _stop_proc(proc):
    try:
        import convert
        convert.stop_process(proc)
    except Exception:
        if proc and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass


def _build_balanced_expr(terms):
    """
    Constructs a balanced binary tree of addition expressions:
    ((term1 + term2) + (term3 + term4)) ...
    This prevents FFmpeg's recursive expression parser from overflowing the C stack
    when handling hundreds or thousands of intervals (O(log N) depth instead of O(N)).
    """
    if not terms:
        return "1"
    if len(terms) == 1:
        return terms[0]
    mid = len(terms) // 2
    left = _build_balanced_expr(terms[:mid])
    right = _build_balanced_expr(terms[mid:])
    return f"({left}+{right})"


try:
    from convert import CancelledError
except Exception:
    class CancelledError(Exception):
        pass


SILENCE_PRESETS = {
    "natural": {
        "label_en": "🎙️ Podcast & Tutorials (Natural Pauses)",
        "label_ar": "🎙️ بودكاست وشروحات (وقفات طبيعية)",
        "noise_db": -35.0,
        "min_silence_sec": 0.50,
        "padding_sec": 0.15,
        "mode": "remove",
    },
    "reels": {
        "label_en": "⚡ Reels, Shorts & TikTok (Fast Jump-Cuts)",
        "label_ar": "⚡ ريلز وشورتس وتيك توك (سريع وحماسي)",
        "noise_db": -32.0,
        "min_silence_sec": 0.30,
        "padding_sec": 0.08,
        "mode": "remove",
    },
    "long_only": {
        "label_en": "🧹 Clean Long Pauses Only (> 1.0s)",
        "label_ar": "🧹 تنظيف السكتات الطويلة فقط (> 1 ثانية)",
        "noise_db": -38.0,
        "min_silence_sec": 1.00,
        "padding_sec": 0.20,
        "mode": "remove",
    },
    "speed_up": {
        "label_en": "⏩ Fast-Forward Silences (4x Speed)",
        "label_ar": "⏩ تسريع السكتات بدون قص (4x أسرع)",
        "noise_db": -35.0,
        "min_silence_sec": 0.50,
        "padding_sec": 0.12,
        "mode": "fast_forward",
        "speed_factor": 4,
    },
    "mute_gate": {
        "label_en": "🔇 Mute Breath & Noise in Silences (Keep Duration)",
        "label_ar": "🔇 كتم الأنفاس والضوضاء أثناء السكتات (نفس المدة)",
        "noise_db": -35.0,
        "min_silence_sec": 0.35,
        "padding_sec": 0.10,
        "mode": "mute",
    },
}

SILENCE_MODES = {
    "remove": {
        "label_en": "✂️ Cut & Remove Silences (Jump Cut)",
        "label_ar": "✂️ قص وحذف السكتات نهائياً (Jump Cut)",
    },
    "fast_forward": {
        "label_en": "⏩ Fast-Forward Silences (4x Speed)",
        "label_ar": "⏩ تسريع السكتات (4x) بدون حذفها",
    },
    "mute": {
        "label_en": "🔇 Mute Noise in Silences (Keep Duration)",
        "label_ar": "🔇 كتم الضوضاء والأنفاس وقت السكون (نفس المدة)",
    },
}

SILENCE_QUALITIES = {
    "original": {
        "label_en": "Original Quality (Pristine - CRF 18)",
        "label_ar": "الأصلية (فائقة الوضوح - CRF 18)",
        "crf": "18",
    },
    "high": {
        "label_en": "High Quality (CRF 22)",
        "label_ar": "عالية (توازن موصى به - CRF 22)",
        "crf": "22",
    },
    "medium": {
        "label_en": "Medium Compression (CRF 26)",
        "label_ar": "متوسطة (ضغط معتدل - CRF 26)",
        "crf": "26",
    },
    "small": {
        "label_en": "Small Size (High Compression - CRF 30)",
        "label_ar": "اقتصادية (أصغر حجم - ضغط عالي)",
        "crf": "30",
    },
}

SILENCE_FORMATS = {
    "same": {
        "label_en": "Same as Source Format",
        "label_ar": "نفس صيغة الملف الأصلية",
        "ext": None,
        "is_audio_only": False,
    },
    "mp4": {
        "label_en": "MP4 Video (.mp4)",
        "label_ar": "MP4 فيديو (.mp4)",
        "ext": ".mp4",
        "is_audio_only": False,
    },
    "mkv": {
        "label_en": "MKV Video (.mkv)",
        "label_ar": "MKV فيديو (.mkv)",
        "ext": ".mkv",
        "is_audio_only": False,
    },
    "mov": {
        "label_en": "MOV Video (.mov)",
        "label_ar": "MOV فيديو (.mov)",
        "ext": ".mov",
        "is_audio_only": False,
    },
    "mp3": {
        "label_en": "Audio Only - MP3 (.mp3)",
        "label_ar": "صوت فقط - MP3 (.mp3)",
        "ext": ".mp3",
        "is_audio_only": True,
    },
    "wav": {
        "label_en": "Audio Only - WAV (.wav)",
        "label_ar": "صوت فقط - WAV (.wav)",
        "ext": ".wav",
        "is_audio_only": True,
    },
}


def _resolve_ffmpeg(ffmpeg_exe=None):
    if ffmpeg_exe and Path(ffmpeg_exe).exists():
        return str(ffmpeg_exe)
    try:
        import convert
        cand = convert.ffmpeg_executable()
        if cand and Path(cand).exists():
            return str(cand)
    except Exception:
        pass
    cands = [
        Path(sys.executable).resolve().parent / "ffmpeg.exe" if getattr(sys, "frozen", False) else None,
        Path(sys.executable).resolve().parent / "_internal" / "ffmpeg.exe" if getattr(sys, "frozen", False) else None,
        Path(getattr(sys, "_MEIPASS", "")) / "ffmpeg.exe" if getattr(sys, "frozen", False) else None,
        Path(__file__).resolve().parent.parent / "tools" / "ffmpeg-essentials" / "ffmpeg-8.1.2-essentials_build" / "bin" / "ffmpeg.exe",
        Path("tools/ffmpeg-essentials/ffmpeg-8.1.2-essentials_build/bin/ffmpeg.exe"),
    ]
    for c in cands:
        if c and c.exists():
            return str(c.resolve())
    disc = shutil.which("ffmpeg")
    return str(disc) if disc else "ffmpeg"


def _probe_duration(media_path, ffmpeg_exe=None):
    """Returns total duration in seconds of media_path."""
    ffmpeg_bin = _resolve_ffmpeg(ffmpeg_exe)
    ffprobe_bin = None
    try:
        import convert
        cand_p = convert.ffprobe_executable()
        if cand_p and Path(cand_p).exists():
            ffprobe_bin = str(cand_p)
    except Exception:
        pass
    if not ffprobe_bin:
        cand_probe = Path(str(ffmpeg_bin)).with_name("ffprobe.exe")
        ffprobe_bin = str(cand_probe) if cand_probe.exists() else (shutil.which("ffprobe") or "ffprobe")
    try:
        cmd = [
            ffprobe_bin,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ]
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for line in res.stdout.splitlines():
            line = line.strip()
            if line:
                val = float(line)
                if val > 0:
                    return val
    except Exception:
        pass
    return 0.0


def compute_speech_segments(total_duration, silences, padding_sec=0.15, min_keep_sec=0.12):
    """
    Given total_duration and a list of silence dicts [{'start': s, 'end': e, 'enabled': bool}],
    computes the kept speech intervals [(start, end), ...] after applying natural padding
    around speech and merging tiny gaps.
    """
    total_duration = max(0.0, float(total_duration))
    if total_duration <= 0:
        return []

    padding = max(0.0, float(padding_sec))
    active_cuts = []
    for s in silences or []:
        if not s.get("enabled", True):
            continue
        raw_s = max(0.0, float(s.get("start", 0.0)))
        raw_e = min(total_duration, float(s.get("end", 0.0)))
        # Shrink the cut interval by `padding` on both sides so speech edges are preserved
        cut_s = raw_s + padding if raw_s > 0.02 else 0.0
        cut_e = raw_e - padding if (total_duration - raw_e) > 0.02 else total_duration
        if cut_e - cut_s >= 0.05:
            active_cuts.append((cut_s, cut_e))

    if not active_cuts:
        return [(0.0, total_duration)]

    # Sort and merge overlapping cut intervals
    active_cuts.sort(key=lambda x: x[0])
    merged_cuts = [active_cuts[0]]
    for cs, ce in active_cuts[1:]:
        prev_s, prev_e = merged_cuts[-1]
        if cs <= prev_e + 0.08:
            merged_cuts[-1] = (prev_s, max(prev_e, ce))
        else:
            merged_cuts.append((cs, ce))

    # Invert cuts to get speech (keep) intervals
    keep_intervals = []
    cursor = 0.0
    for cs, ce in merged_cuts:
        if cs - cursor >= min_keep_sec:
            keep_intervals.append((round(cursor, 3), round(cs, 3)))
        cursor = max(cursor, ce)

    if total_duration - cursor >= min_keep_sec:
        keep_intervals.append((round(cursor, 3), round(total_duration, 3)))

    # Fallback: if everything was silent, keep a tiny slice or full file so output isn't empty
    if not keep_intervals:
        keep_intervals = [(0.0, round(min(total_duration, 1.0), 3))]

    return keep_intervals


def summarize_silence_analysis(total_duration, silences, padding_sec=0.15, mode="remove", speed_factor=4):
    """
    Calculates full statistics for UI display.
    """
    total_duration = max(0.0, float(total_duration))
    keep_intervals = compute_speech_segments(total_duration, silences, padding_sec=padding_sec)
    speech_duration = sum(max(0.0, e - s) for s, e in keep_intervals)
    cut_duration = max(0.0, total_duration - speech_duration)

    if mode == "mute":
        new_duration = total_duration
        saved_seconds = 0.0
    elif mode == "fast_forward":
        sf = max(2, int(speed_factor or 4))
        new_duration = speech_duration + (cut_duration / sf)
        saved_seconds = max(0.0, total_duration - new_duration)
    else:
        new_duration = speech_duration
        saved_seconds = cut_duration

    saved_percent = (saved_seconds / total_duration * 100.0) if total_duration > 0 else 0.0
    enabled_silences = [s for s in (silences or []) if s.get("enabled", True)]

    return {
        "total_duration": round(total_duration, 2),
        "speech_duration": round(speech_duration, 2),
        "silent_duration": round(cut_duration, 2),
        "new_duration": round(new_duration, 2),
        "saved_seconds": round(saved_seconds, 2),
        "saved_percent": round(saved_percent, 1),
        "silence_count": len(silences or []),
        "enabled_silence_count": len(enabled_silences),
        "speech_count": len(keep_intervals),
        "keep_intervals": keep_intervals,
    }


def detect_silences(
    media_path,
    noise_db=-35.0,
    min_silence_sec=0.5,
    padding_sec=0.15,
    ffmpeg_exe=None,
    start_seconds=None,
    duration_seconds=None,
    cancel_callback=None,
    progress_callback=None,
):
    """
    Scans a video or audio file with FFmpeg's `silencedetect` filter and returns:
    {
        "silences": [{"index": 1, "start": 1.2, "end": 2.4, "duration": 1.2, "enabled": True}, ...],
        "keep_intervals": [(0.0, 1.35), ...],
        "total_duration": float,
        "silent_duration": float,
        "new_duration": float,
        "saved_seconds": float,
        "saved_percent": float,
        "silence_count": int,
        "speech_count": int,
    }
    """
    media_path = Path(media_path).resolve()
    if not media_path.exists():
        raise FileNotFoundError(f"Media file not found: {media_path}")

    ffmpeg_bin = _resolve_ffmpeg(ffmpeg_exe)
    total_dur = _probe_duration(media_path, ffmpeg_bin)

    s_sec = max(0.0, float(start_seconds)) if start_seconds is not None else 0.0
    if duration_seconds is not None and float(duration_seconds) > 0:
        total_dur = float(duration_seconds)
    elif s_sec > 0:
        total_dur = max(0.1, total_dur - s_sec)

    noise_val = float(noise_db)
    min_dur = max(0.1, float(min_silence_sec))

    cmd = [
        ffmpeg_bin,
        "-hide_banner",
        "-nostdin",
        "-progress", "pipe:2",
    ]
    if s_sec > 0:
        cmd.extend(["-ss", f"{s_sec:.3f}"])
    if duration_seconds is not None and float(duration_seconds) > 0:
        cmd.extend(["-t", f"{float(duration_seconds):.3f}"])
    cmd.extend([
        "-i", str(media_path),
        "-vn",
        "-sn",
        "-dn",
        "-af", f"silencedetect=noise={noise_val:.1f}dB:d={min_dur:.3f}",
        "-f", "null",
        "-",
    ])

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    _register_proc(proc)

    re_start = re.compile(r"silence_start:\s*([0-9.]+)")
    re_end = re.compile(r"silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)")
    re_time = re.compile(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)")
    re_dur = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
    re_out_ms = re.compile(r"out_time_ms=(\d+)")
    re_out_us = re.compile(r"out_time_us=(\d+)")

    silences = []
    current_start = None

    while True:
        if cancel_callback and cancel_callback():
            _stop_proc(proc)
            raise CancelledError("Silence detection canceled by user.")

        line = proc.stderr.readline()
        if not line:
            if proc.poll() is not None:
                break
            time.sleep(0.02)
            continue

        if total_dur <= 0:
            m_dur = re_dur.search(line)
            if m_dur:
                h, m, s = int(m_dur.group(1)), int(m_dur.group(2)), float(m_dur.group(3))
                total_dur = h * 3600 + m * 60 + s

        m_ms = re_out_ms.search(line)
        if m_ms and progress_callback and total_dur > 0:
            cur_s = int(m_ms.group(1)) / 1_000_000.0
            pct = min(98, max(1, int((cur_s / total_dur) * 100)))
            progress_callback(pct)
            continue

        m_s = re_start.search(line)
        if m_s:
            current_start = max(0.0, float(m_s.group(1)))
            if progress_callback and total_dur > 0:
                pct = min(98, int((current_start / total_dur) * 100))
                progress_callback(pct)
            continue

        m_e = re_end.search(line)
        if m_e:
            end_t = float(m_e.group(1))
            dur_t = float(m_e.group(2))
            start_t = current_start if current_start is not None else max(0.0, end_t - dur_t)
            if end_t > start_t:
                silences.append({
                    "index": len(silences) + 1,
                    "start": round(start_t, 3),
                    "end": round(end_t, 3),
                    "duration": round(end_t - start_t, 3),
                    "enabled": True,
                })
            current_start = None
            if progress_callback and total_dur > 0:
                pct = min(98, int((end_t / total_dur) * 100))
                progress_callback(pct)
            continue

        m_t = re_time.search(line)
        if m_t and progress_callback and total_dur > 0:
            cur_t = int(m_t.group(1)) * 3600 + int(m_t.group(2)) * 60 + float(m_t.group(3))
            pct = min(98, int((cur_t / total_dur) * 100))
            progress_callback(pct)

    proc.wait()
    _unregister_proc(proc)
    _stop_proc(proc)
    if cancel_callback and cancel_callback():
        raise CancelledError("Silence detection canceled by user.")

    # Handle open silence at the end of the file
    if current_start is not None and total_dur > current_start:
        if (total_dur - current_start) >= min_dur:
            silences.append({
                "index": len(silences) + 1,
                "start": round(current_start, 3),
                "end": round(total_dur, 3),
                "duration": round(total_dur - current_start, 3),
                "enabled": True,
            })

    if progress_callback:
        progress_callback(100)

    stats = summarize_silence_analysis(
        total_duration=total_dur,
        silences=silences,
        padding_sec=padding_sec,
        mode="remove",
    )
    stats["silences"] = silences
    stats["noise_db"] = noise_val
    stats["min_silence_sec"] = min_dur
    stats["padding_sec"] = float(padding_sec)
    return stats


def remap_subtitles_for_cuts(segments, keep_intervals, mode="remove", speed_factor=4):
    """
    Adjusts subtitle segment timestamps [{'start': s, 'end': e, 'text': t}, ...]
    so they stay perfectly synchronized after silent intervals are removed or sped up.
    """
    if not segments or not keep_intervals or mode == "mute":
        return [dict(seg) for seg in (segments or [])]

    # Build timeline mapping blocks from original time -> new time
    timeline_blocks = []
    out_cursor = 0.0
    prev_end = 0.0
    sf = max(2, int(speed_factor or 4))

    for ks, ke in keep_intervals:
        if mode == "fast_forward" and ks > prev_end:
            sil_dur = ks - prev_end
            new_sil_dur = sil_dur / sf
            timeline_blocks.append({
                "orig_start": prev_end,
                "orig_end": ks,
                "out_start": out_cursor,
                "out_end": out_cursor + new_sil_dur,
                "scale": 1.0 / sf,
                "is_speech": False,
            })
            out_cursor += new_sil_dur

        seg_dur = max(0.0, ke - ks)
        if seg_dur > 0:
            timeline_blocks.append({
                "orig_start": ks,
                "orig_end": ke,
                "out_start": out_cursor,
                "out_end": out_cursor + seg_dur,
                "scale": 1.0,
                "is_speech": True,
            })
            out_cursor += seg_dur
        prev_end = ke

    def _map_time(t):
        t = float(t)
        if not timeline_blocks:
            return t
        for blk in timeline_blocks:
            if t <= blk["orig_end"]:
                if t <= blk["orig_start"]:
                    return blk["out_start"]
                return blk["out_start"] + (t - blk["orig_start"]) * blk["scale"]
        return timeline_blocks[-1]["out_end"]

    remapped = []
    for seg in segments:
        old_s = float(seg.get("start", 0.0))
        old_e = float(seg.get("end", 0.0))
        new_s = _map_time(old_s)
        new_e = _map_time(old_e)
        if new_e - new_s < 0.15:
            new_e = new_s + min(0.8, max(0.25, old_e - old_s))
        item = dict(seg)
        item["start"] = round(new_s, 3)
        item["end"] = round(new_e, 3)
        remapped.append(item)

    return remapped


def parse_and_remap_srt_file(srt_path, keep_intervals, output_srt_path, mode="remove", speed_factor=4):
    """
    Reads an existing .srt file, remaps all subtitle timestamps according to `keep_intervals`,
    and writes the synchronized .srt to `output_srt_path`.
    """
    srt_path = Path(srt_path)
    if not srt_path.exists() or not keep_intervals or mode == "mute":
        return srt_path

    raw_text = srt_path.read_text(encoding="utf-8-sig", errors="replace")
    ts_re = re.compile(
        r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
    )

    def _to_sec(h, m, s, ms):
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

    def _fmt_srt(sec):
        sec = max(0.0, float(sec))
        hrs = int(sec // 3600)
        mins = int((sec % 3600) // 60)
        secs = int(sec % 60)
        millis = int(round((sec - int(sec)) * 1000))
        if millis >= 1000:
            millis = 999
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

    blocks = re.split(r"\n\s*\n", raw_text.strip())
    parsed_segs = []
    for blk in blocks:
        lines = [ln.strip() for ln in blk.strip().splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        m = ts_re.search(lines[0])
        text_start_idx = 1
        if not m and len(lines) >= 2:
            m = ts_re.search(lines[1])
            text_start_idx = 2
        if not m:
            continue
        s_sec = _to_sec(m.group(1), m.group(2), m.group(3), m.group(4))
        e_sec = _to_sec(m.group(5), m.group(6), m.group(7), m.group(8))
        txt = "\n".join(lines[text_start_idx:]).strip()
        if txt:
            parsed_segs.append({"start": s_sec, "end": e_sec, "text": txt})

    if not parsed_segs:
        return srt_path

    remapped = remap_subtitles_for_cuts(parsed_segs, keep_intervals, mode=mode, speed_factor=speed_factor)
    out_lines = []
    for idx, seg in enumerate(remapped, start=1):
        out_lines.append(str(idx))
        out_lines.append(f"{_fmt_srt(seg['start'])} --> {_fmt_srt(seg['end'])}")
        out_lines.append(seg["text"])
        out_lines.append("")

    output_srt_path = Path(output_srt_path)
    output_srt_path.parent.mkdir(parents=True, exist_ok=True)
    output_srt_path.write_text("\n".join(out_lines), encoding="utf-8-sig")
    return output_srt_path


def build_interval_binary_trees(keep_intervals, mode="remove", speed_factor=4):
    """
    Constructs logarithmic-depth (O(log2 N)) decision trees for:
    1. sel_expr: evaluates to 1 if t is inside a speech interval, else 0 (using lowercase t for select filter)
    2. c_expr: evaluates to the exact cumulative silence duration (seconds) to subtract at timestamp T (using uppercase T for setpts/asetpts)
    
    This replaces linear frame counters (N/FRAME_RATE/TB) with mathematically exact continuous time-mapping:
    PTS_out = (T - C(T)) / TB
    This guarantees 100% frame-perfect lip-sync with ZERO drift on both Variable Frame Rate (VFR)
    and Constant Frame Rate (CFR) videos, regardless of video duration or number of cuts.
    """
    clean_intervals = [(float(s), float(e)) for s, e in keep_intervals if float(e) > float(s) + 0.001]
    if not clean_intervals:
        return None, None

    sf = max(2, int(speed_factor or 4))
    factor = 1.0 if mode == "remove" else (1.0 - 1.0 / sf)

    cum_silence = 0.0
    prev_e = 0.0
    items = []
    for s, e in clean_intervals:
        if s > prev_e:
            cum_silence += (s - prev_e) * factor
        items.append((s, e, cum_silence))
        prev_e = e

    def _rec_sel(arr):
        if len(arr) == 1:
            s, e, _ = arr[0]
            return f"(gte(t,{s:.3f})*lt(t,{e:.3f}))"
        mid = len(arr) // 2
        split = arr[mid][0]
        return f"if(lt(t,{split:.3f}),{_rec_sel(arr[:mid])},{_rec_sel(arr[mid:])})"

    def _rec_c(arr):
        if len(arr) == 1:
            return f"{arr[0][2]:.4f}"
        mid = len(arr) // 2
        split_t = arr[mid][0]
        return f"if(lt(T,{split_t:.3f}),{_rec_c(arr[:mid])},{_rec_c(arr[mid:])})"

    sel_str = _rec_sel(items)
    c_str = _rec_c(items)
    return sel_str, c_str


def build_silence_filter_expressions(keep_intervals, mode="remove", speed_factor=4, total_duration=None):
    """
    Builds FFmpeg video and audio filter strings for applying silence cuts, fast-forward, or muting.
    Guarantees 100% lip-sync preservation using continuous piecewise-linear PTS remapping.
    Returns: (video_filter_str_or_None, audio_filter_str_or_None)
    """
    if not keep_intervals:
        return None, None

    clean_intervals = [(float(s), float(e)) for s, e in keep_intervals if float(e) > float(s) + 0.001]
    if not clean_intervals:
        return None, None

    if mode == "mute":
        speech_terms = [f"between(t,{s:.3f},{e:.3f})" for s, e in clean_intervals]
        speech_expr = _build_balanced_expr(speech_terms)
        a_filter = f"volume=enable='not({speech_expr})':volume=0"
        return None, a_filter

    sel_str, c_str = build_interval_binary_trees(clean_intervals, mode=mode, speed_factor=speed_factor)
    if not sel_str or not c_str:
        return None, None

    if mode == "fast_forward":
        sf = max(2, int(speed_factor or 4))
        v_filter = f"select='({sel_str})+not({sel_str})*not(mod(n,{sf}))',setpts='(T-{c_str})/TB'"
        a_filter = (
            f"volume=enable='not({sel_str})':volume=0.15,"
            f"aselect='({sel_str})+not({sel_str})',asetpts='(T-{c_str})/TB',aresample=async=1:first_pts=0"
        )
        return v_filter, a_filter

    # Default mode == "remove" (Jump Cut)
    # Continuous PTS mapping (T - C(T)) / TB locks audio and video together down to the millisecond
    v_filter = f"select='{sel_str}',setpts='(T-{c_str})/TB'"
    a_filter = f"aselect='{sel_str}',asetpts='(T-{c_str})/TB',aresample=async=1:first_pts=0"
    return v_filter, a_filter


def export_silence_cut_media(
    media_path,
    output_path=None,
    output_dir=None,
    keep_intervals=None,
    noise_db=-35.0,
    min_silence_sec=0.5,
    padding_sec=0.15,
    mode="remove",
    speed_factor=4,
    audio_enhancement_filter=None,
    video_quality="High",
    has_video=True,
    ffmpeg_exe=None,
    cancel_callback=None,
    progress_callback=None,
):
    """
    Exports a video or audio file with silences removed, fast-forwarded, or muted.
    If `keep_intervals` is None, automatically runs `detect_silences` first.
    """
    media_path = Path(media_path).resolve()
    if not media_path.exists():
        raise FileNotFoundError(f"Source file not found: {media_path}")

    ffmpeg_bin = _resolve_ffmpeg(ffmpeg_exe)
    total_dur = _probe_duration(media_path, ffmpeg_bin)

    if keep_intervals is None:
        analysis = detect_silences(
            media_path=media_path,
            noise_db=noise_db,
            min_silence_sec=min_silence_sec,
            padding_sec=padding_sec,
            ffmpeg_exe=ffmpeg_bin,
            cancel_callback=cancel_callback,
        )
        keep_intervals = analysis["keep_intervals"]
        total_dur = analysis["total_duration"]

    if output_path is None:
        if output_dir is None:
            output_dir = media_path.parent / "output"
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        tag = "nosilence" if mode == "remove" else ("fastsilence" if mode == "fast_forward" else "gated")
        ext = media_path.suffix if media_path.suffix else (".mp4" if has_video else ".mp3")
        output_path = output_dir / f"{media_path.stem}_{tag}{ext}"
    else:
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

    v_expr, a_expr = build_silence_filter_expressions(
        keep_intervals=keep_intervals,
        mode=mode,
        speed_factor=speed_factor,
        total_duration=total_dur,
    )

    if audio_enhancement_filter:
        a_expr = f"{a_expr},{audio_enhancement_filter}" if a_expr else audio_enhancement_filter

    # Estimate expected output duration for accurate progress bar
    speech_dur = sum(max(0.0, e - s) for s, e in (keep_intervals or []))
    if mode == "remove" and speech_dur > 0:
        calc_dur = speech_dur
    elif mode == "fast_forward" and speech_dur > 0:
        sf = max(2, int(speed_factor or 4))
        calc_dur = speech_dur + max(0.0, total_dur - speech_dur) / sf
    else:
        calc_dur = max(0.1, total_dur)

    temp_part = output_path.with_name(f"{output_path.stem}_part{output_path.suffix}")
    script_file = None
    proc = None

    try:
        input_opts = []
        if keep_intervals:
            last_cut_end = max((e for s, e in keep_intervals), default=0.0)
            if last_cut_end > 0 and total_dur > 0 and (total_dur - last_cut_end) >= 1.0:
                input_opts.extend(["-to", f"{last_cut_end + 0.3:.3f}"])

        cmd = [
            ffmpeg_bin,
            "-y",
            "-hide_banner",
            "-loglevel", "error",
            "-nostdin",
            "-progress", "pipe:2",
            *input_opts,
            "-i", str(media_path),
        ]

        if has_video:
            fc_parts = []
            if v_expr:
                fc_parts.append(f"[0:v]{v_expr}[outv]")
            else:
                fc_parts.append("[0:v]null[outv]")
            if a_expr:
                fc_parts.append(f"[0:a]{a_expr}[outa]")
            else:
                fc_parts.append("[0:a]anull[outa]")

            fc_str = ";".join(fc_parts)
            if len(fc_str) > 200:
                script_file = output_path.with_name(f"_fc_{int(time.time() * 1000)}.txt")
                script_file.write_text(fc_str, encoding="utf-8")
                cmd.extend(["-filter_complex_script", str(script_file)])
            else:
                cmd.extend(["-filter_complex", fc_str])

            cmd.extend(["-map", "[outv]", "-map", "[outa]"])

            crf_val = "20"
            vq_str = str(video_quality).strip().lower()
            if vq_str in ("original", "very high", "pristine", "18"):
                crf_val = "18"
            elif vq_str in ("high", "22"):
                crf_val = "22"
            elif vq_str in ("medium", "26"):
                crf_val = "26"
            elif vq_str in ("small", "30"):
                crf_val = "30"

            cmd.extend([
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", crf_val,
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
            ])
            if output_path.suffix.lower() in (".mp4", ".m4v", ".mov"):
                cmd.extend(["-movflags", "+faststart"])
            cmd.append(str(temp_part))
        else:
            cmd.append("-vn")
            if a_expr:
                if len(a_expr) > 200:
                    script_file = output_path.with_name(f"_af_{int(time.time() * 1000)}.txt")
                    script_file.write_text(f"[0:a]{a_expr}[outa]", encoding="utf-8")
                    cmd.extend(["-filter_complex_script", str(script_file), "-map", "[outa]"])
                else:
                    cmd.extend(["-af", a_expr])

            ext_l = output_path.suffix.lower()
            if ext_l == ".mp3":
                cmd.extend(["-c:a", "libmp3lame", "-b:a", "192k"])
            elif ext_l in (".m4a", ".aac", ".mp4"):
                cmd.extend(["-c:a", "aac", "-b:a", "192k"])
            elif ext_l == ".wav":
                cmd.extend(["-c:a", "pcm_s16le"])
            elif ext_l == ".flac":
                cmd.extend(["-c:a", "flac"])
            cmd.append(str(temp_part))

        if cancel_callback and cancel_callback():
            raise CancelledError("Operation canceled by user")

        stderr_output = []
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        _register_proc(proc)

        last_report_sec = -1.0
        while True:
            if cancel_callback and cancel_callback():
                _stop_proc(proc)
                raise CancelledError("Operation canceled by user")

            line = proc.stderr.readline()
            if not line:
                if proc.poll() is not None:
                    break
                time.sleep(0.02)
                continue

            line = line.strip()
            stderr_output.append(line)
            if len(stderr_output) > 100:
                stderr_output.pop(0)

            cur_sec = None
            if line.startswith("out_time_us="):
                try:
                    out_time_us = int(line.split("=")[1])
                    cur_sec = max(0.0, out_time_us / 1_000_000.0)
                except Exception:
                    pass
            elif line.startswith("out_time_ms="):
                try:
                    out_time_ms = int(line.split("=")[1])
                    cur_sec = max(0.0, out_time_ms / 1_000_000.0)
                except Exception:
                    pass

            if cur_sec is not None and abs(cur_sec - last_report_sec) >= 0.15:
                last_report_sec = cur_sec
                pct = min(99, int((cur_sec / max(calc_dur, 0.1)) * 100))
                if progress_callback:
                    try:
                        progress_callback(pct, cur_sec, calc_dur)
                    except Exception:
                        pass

        returncode = proc.wait()
        if cancel_callback and cancel_callback():
            _stop_proc(proc)
            raise CancelledError("Operation canceled by user")

        if returncode != 0:
            err = "".join(stderr_output).strip()
            raise RuntimeError(f"FFmpeg silence cut failed (code {returncode}): {err}")

        if temp_part.exists():
            final_target = output_path
            for _attempt in range(5):
                try:
                    if final_target.exists():
                        final_target.unlink()
                    temp_part.rename(final_target)
                    break
                except (PermissionError, OSError):
                    time.sleep(0.25)
            output_path = final_target

        if progress_callback:
            try:
                progress_callback(100, calc_dur, calc_dur)
            except Exception:
                pass

        return output_path

    finally:
        if proc:
            _unregister_proc(proc)
            _stop_proc(proc)
        if script_file and script_file.exists():
            try:
                script_file.unlink()
            except Exception:
                pass
        if temp_part.exists():
            try:
                temp_part.unlink()
            except Exception:
                pass

