"""
DaVinci-Style Multi-Track NLE Timeline Engine, Fast PyAV Frame Scrubbing & Audio Waveform Analyzer
Manages V1/A1 Video-Audio clips (split, trim, ripple delete, duplicate, reorder, per-clip transform/speed/volume),
V2 Images & Icons, V3 Text+ cards, V4 Logo watermarks, Undo/Redo stack, and subtitle timeline remapping.
Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

import copy
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

from .color_grading import extract_video_sample_frame

try:
    import av
except ImportError:
    av = None


class NLEProjectState:
    """
    Holds the complete multi-track NLE timeline state for the currently loaded video.
    Tracks:
      - V4: Logo / Watermark items
      - V3: Text+ Title / Caption overlay cards
      - V2: Media overlays (Pro Icons, Badges, Custom Images)
      - V1 + A1: Main Video & Audio clips (split, trim, reorder, speed, volume, per-clip pan/zoom)
    """

    MAX_UNDO = 40

    def __init__(self):
        self.source_path_str: str = ""
        self.source_duration: float = 0.0
        self.clips: List[Dict[str, Any]] = []
        self.media_items: List[Dict[str, Any]] = []   # Track V2 (icons & images)
        self.text_items: List[Dict[str, Any]] = []    # Track V3 (texts)
        self.logo_items: List[Dict[str, Any]] = []    # Track V4 (logos)
        self.track_enabled: Dict[str, bool] = {
            "V4": True,
            "V3": True,
            "V2": True,
            "V1": True,
            "A1": True,
        }
        self.ripple_mode: bool = True
        self._id_counter: int = 1
        self._undo_stack: List[Dict[str, Any]] = []
        self._redo_stack: List[Dict[str, Any]] = []

    def next_id(self, prefix: str = "item") -> str:
        val = f"{prefix}_{self._id_counter}"
        self._id_counter += 1
        return val

    def snapshot_dict(self) -> Dict[str, Any]:
        return copy.deepcopy({
            "clips": self.clips,
            "media_items": self.media_items,
            "text_items": self.text_items,
            "logo_items": self.logo_items,
            "track_enabled": self.track_enabled,
            "ripple_mode": self.ripple_mode,
            "id_counter": self._id_counter,
        })

    def restore_snapshot(self, snap: Dict[str, Any]):
        data = copy.deepcopy(snap)
        self.clips = data.get("clips", [])
        self.media_items = data.get("media_items", [])
        self.text_items = data.get("text_items", [])
        self.logo_items = data.get("logo_items", [])
        self.track_enabled = data.get("track_enabled", {"V4": True, "V3": True, "V2": True, "V1": True, "A1": True})
        self.ripple_mode = bool(data.get("ripple_mode", True))
        self._id_counter = max(self._id_counter, int(data.get("id_counter", 1)))
        self.recompute_timeline()

    def push_undo(self):
        self._undo_stack.append(self.snapshot_dict())
        if len(self._undo_stack) > self.MAX_UNDO:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        if hasattr(self, "on_push_undo_cb") and callable(self.on_push_undo_cb):
            try:
                self.on_push_undo_cb()
            except Exception:
                pass

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        self._redo_stack.append(self.snapshot_dict())
        snap = self._undo_stack.pop()
        self.restore_snapshot(snap)
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        self._undo_stack.append(self.snapshot_dict())
        snap = self._redo_stack.pop()
        self.restore_snapshot(snap)
        return True

    def reset_for_media(self, source_path: Optional[Path], duration_sec: float):
        if not source_path:
            self.source_path_str = ""
            self.source_duration = 0.0
            self.clips = []
            self.media_items = []
            self.text_items = []
            self.logo_items = []
            self._undo_stack.clear()
            self._redo_stack.clear()
            self.recompute_timeline()
            return

        dur = max(0.5, float(duration_sec or 60.0))
        self.source_path_str = str(source_path)
        self.source_duration = dur
        stem = Path(source_path).stem
        self.clips = [
            {
                "id": self.next_id("clip"),
                "name": stem[:28],
                "src_start": 0.0,
                "src_end": round(dur, 3),
                "tl_start": 0.0,
                "speed": 1.0,
                "volume": 1.0,
                "muted": False,
                "custom_transform": False,
                "zoom": 1.0,
                "pan_x": 0.0,
                "pan_y": 0.0,
                "flip_h": False,
            }
        ]
        self.media_items = []
        self.text_items = []
        self.logo_items = []
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.recompute_timeline()

    def update_source_duration_if_single_untouched(self, duration_sec: float, source_path: Optional[Path] = None):
        dur = max(0.5, float(duration_sec or 0.0))
        self.source_duration = dur
        if len(self.clips) == 1 and abs(self.clips[0].get("src_start", 0.0)) < 0.05:
            self.clips[0]["src_end"] = round(dur, 3)
            if source_path:
                self.clips[0]["name"] = source_path.stem[:28]
        self.recompute_timeline()

    def recompute_timeline(self, pack_gaps: bool = False) -> float:
        if not self.clips:
            return 0.0

        if pack_gaps:
            cur_t = 0.0
            for idx, c in enumerate(self.clips):
                s0 = max(0.0, float(c.get("src_start", 0.0)))
                s1 = max(s0 + 0.08, float(c.get("src_end", max(1.0, self.source_duration))))
                spd = max(0.25, min(4.0, float(c.get("speed", 1.0) or 1.0)))
                c["src_start"] = round(s0, 3)
                c["src_end"] = round(s1, 3)
                c["speed"] = round(spd, 2)
                tl_dur = (s1 - s0) / spd
                c["tl_start"] = round(cur_t, 3)
                c["tl_dur"] = round(tl_dur, 3)
                c["tl_end"] = round(cur_t + tl_dur, 3)
                c["index"] = idx
                cur_t += tl_dur
            return round(cur_t, 3)

        # Assign sequential fallback tl_start for any clip dict missing tl_start
        fallback_t = 0.0
        for c in self.clips:
            s0 = max(0.0, float(c.get("src_start", 0.0)))
            s1 = max(s0 + 0.08, float(c.get("src_end", max(1.0, self.source_duration))))
            spd = max(0.25, min(4.0, float(c.get("speed", 1.0) or 1.0)))
            tl_dur = (s1 - s0) / spd
            if "tl_start" not in c or c.get("tl_start") is None:
                c["tl_start"] = round(fallback_t, 3)
            fallback_t = max(fallback_t, float(c["tl_start"])) + tl_dur

        # Stable sort by tl_start and enforce non-overlapping invariant while preserving gaps
        self.clips.sort(key=lambda x: float(x.get("tl_start", 0.0)))
        prev_end = 0.0
        for idx, c in enumerate(self.clips):
            s0 = max(0.0, float(c.get("src_start", 0.0)))
            s1 = max(s0 + 0.08, float(c.get("src_end", max(1.0, self.source_duration))))
            spd = max(0.25, min(4.0, float(c.get("speed", 1.0) or 1.0)))
            c["src_start"] = round(s0, 3)
            c["src_end"] = round(s1, 3)
            c["speed"] = round(spd, 2)
            tl_dur = (s1 - s0) / spd
            tl_s = max(prev_end, max(0.0, float(c.get("tl_start", prev_end))))
            c["tl_start"] = round(tl_s, 3)
            c["tl_dur"] = round(tl_dur, 3)
            c["tl_end"] = round(tl_s + tl_dur, 3)
            c["index"] = idx
            prev_end = c["tl_end"]
        return round(prev_end, 3)

    @property
    def total_duration(self) -> float:
        max_end = float(self.clips[-1].get("tl_end", 0.0)) if self.clips else float(self.source_duration or 0.0)
        for t_list in (self.media_items, self.text_items, self.logo_items):
            for it in t_list:
                if it.get("enabled", True) and not it.get("full_duration", False):
                    max_end = max(max_end, float(it.get("end_sec", 0.0)))
        return max(0.2, round(max_end, 3))

    def get_timeline_gaps(self) -> List[Tuple[float, float]]:
        """Returns list of (gap_start, gap_end) intervals >= 0.04s on Track V1."""
        if not self.clips:
            return []
        gaps: List[Tuple[float, float]] = []
        prev_e = 0.0
        for c in self.clips:
            ts = float(c.get("tl_start", prev_e))
            if ts - prev_e >= 0.04:
                gaps.append((round(prev_e, 3), round(ts, 3)))
            prev_e = float(c.get("tl_end", ts))
        tot = self.total_duration
        if tot - prev_e >= 0.05:
            gaps.append((round(prev_e, 3), round(tot, 3)))
        return gaps

    def is_playhead_in_gap(self, tl_sec: float) -> Tuple[bool, Optional[int], float]:
        """
        Checks if tl_sec falls inside an empty gap between/before/after V1 clips.
        Returns (in_gap, next_clip_idx_or_None, next_clip_tl_start_or_total_end).
        """
        if not self.clips:
            return False, None, 0.0
        t = max(0.0, float(tl_sec))
        for idx, c in enumerate(self.clips):
            if t < c["tl_start"] - 0.02:
                return True, idx, float(c["tl_start"])
            if c["tl_start"] - 0.02 <= t <= c["tl_end"] + 0.02:
                return False, idx, float(c["tl_start"])
        if t > self.clips[-1]["tl_end"] + 0.02:
            return True, None, self.total_duration
        return False, len(self.clips) - 1, float(self.clips[-1]["tl_start"])

    def close_all_gaps(self) -> bool:
        if not self.clips or not self.get_timeline_gaps():
            return False
        self.push_undo()
        self.recompute_timeline(pack_gaps=True)
        return True

    def has_timeline_cuts_or_clip_fx(self) -> bool:
        """
        Returns True if the user split, trimmed, separated with gaps, deleted, reordered,
        or changed speed/volume/transform on V1 clips.
        """
        if len(self.clips) != 1:
            return True
        if self.get_timeline_gaps():
            return True
        c = self.clips[0]
        if c.get("tl_start", 0.0) > 0.04:
            return True
        if c.get("src_start", 0.0) > 0.08:
            return True
        if self.source_duration > 0 and c.get("src_end", self.source_duration) < self.source_duration - 0.15:
            return True
        if abs(float(c.get("speed", 1.0)) - 1.0) > 0.02:
            return True
        if abs(float(c.get("volume", 1.0)) - 1.0) > 0.02 or c.get("muted", False):
            return True
        if c.get("custom_transform", False):
            return True
        return False

    def timeline_to_source(self, tl_sec: float) -> Tuple[int, Optional[Dict[str, Any]], float]:
        """
        Maps an edited timeline timestamp tl_sec -> (clip_index, clip_dict_or_None_if_gap, source_video_sec).
        When tl_sec falls inside a timeline gap, clip_dict is None and clip_index points to the upcoming
        (or last) clip with its boundary source timestamp.
        """
        if not self.clips:
            return 0, None, max(0.0, float(tl_sec))
        t = max(0.0, float(tl_sec))
        for idx, c in enumerate(self.clips):
            if t < c["tl_start"] - 0.02:
                return idx, None, float(c["src_start"])
            if t <= c["tl_end"] + 0.02:
                local_t = max(0.0, min(c["tl_dur"], t - c["tl_start"]))
                src_t = c["src_start"] + local_t * float(c.get("speed", 1.0))
                src_t = max(c["src_start"], min(c["src_end"], src_t))
                return idx, c, src_t
        last = self.clips[-1]
        if t > last["tl_end"] + 0.02:
            return len(self.clips) - 1, None, float(last["src_end"])
        return len(self.clips) - 1, last, float(last["src_end"])

    def source_to_timeline(self, src_sec: float, preferred_clip_idx: Optional[int] = None) -> Tuple[int, float]:
        """
        Maps a source timestamp back to (clip_idx, tl_sec), preferring preferred_clip_idx if still inside it.
        """
        if not self.clips:
            return 0, max(0.0, float(src_sec))
        s = max(0.0, float(src_sec))

        if preferred_clip_idx is not None and 0 <= preferred_clip_idx < len(self.clips):
            c = self.clips[preferred_clip_idx]
            if c["src_start"] - 0.05 <= s <= c["src_end"] + 0.05:
                spd = max(0.25, float(c.get("speed", 1.0)))
                tl_t = c["tl_start"] + max(0.0, s - c["src_start"]) / spd
                return preferred_clip_idx, min(c["tl_end"], tl_t)

        for idx, c in enumerate(self.clips):
            if c["src_start"] <= s <= c["src_end"]:
                spd = max(0.25, float(c.get("speed", 1.0)))
                return idx, c["tl_start"] + (s - c["src_start"]) / spd

        return 0, float(self.clips[0].get("tl_start", 0.0))

    def move_clip_to_time(self, clip_idx: int, desired_tl_start: float, push_undo: bool = False) -> int:
        """
        Moves self.clips[clip_idx] freely along the timeline to create or adjust gaps between clips,
        or reorder across neighbors when dragged past a neighbor's midpoint.
        Returns the clip's index after recomputing timeline order.
        """
        if not self.clips or not (0 <= clip_idx < len(self.clips)):
            return max(0, clip_idx)
        if push_undo:
            self.push_undo()

        target = self.clips[clip_idx]
        cid = target["id"]
        dur = max(0.08, float(target.get("tl_dur", 1.0)))
        want_s = max(0.0, float(desired_tl_start))

        others = [c for i, c in enumerate(self.clips) if i != clip_idx]
        if not others:
            target["tl_start"] = round(want_s, 3)
            self.recompute_timeline(pack_gaps=False)
            return 0

        # Determine slot among others based on crossing neighbor midpoints
        insert_pos = 0
        for oc in others:
            oc_mid = float(oc["tl_start"]) + float(oc["tl_dur"]) * 0.5
            if want_s > oc_mid:
                insert_pos += 1
            else:
                break

        # Clamp against immediate left neighbor unless user crossed its midpoint (handled by insert_pos)
        if insert_pos > 0:
            left_end = float(others[insert_pos - 1]["tl_end"])
            if want_s < left_end:
                want_s = left_end

        target["tl_start"] = round(want_s, 3)
        new_order = others[:insert_pos] + [target] + others[insert_pos:]

        # Push subsequent clips right only if target's new end overlaps them
        running_end = round(want_s + dur, 3)
        for j in range(insert_pos + 1, len(new_order)):
            nc = new_order[j]
            ns = float(nc["tl_start"])
            nd = float(nc["tl_dur"])
            if ns < running_end:
                nc["tl_start"] = round(running_end, 3)
                running_end = round(running_end + nd, 3)
            else:
                running_end = round(ns + nd, 3)

        self.clips = new_order
        self.recompute_timeline(pack_gaps=False)
        for final_i, c in enumerate(self.clips):
            if c["id"] == cid:
                return final_i
        return min(insert_pos, len(self.clips) - 1)

    def split_clip_at(self, tl_sec: float, min_clip_dur: float = 0.12) -> Optional[int]:
        """
        Splits the V1 clip under tl_sec into two independent clips (DaVinci Razor/Blade tool).
        Supports frame-accurate splitting when zoomed in, preserving exact timeline positions and gaps.
        """
        if not self.clips:
            return None
        self.recompute_timeline()
        idx, c, src_split = self.timeline_to_source(tl_sec)
        if c is None:
            return None

        spd = max(0.25, float(c.get("speed", 1.0)))
        left_dur = (src_split - c["src_start"]) / spd
        right_dur = (c["src_end"] - src_split) / spd
        if left_dur < min_clip_dur or right_dur < min_clip_dur:
            return None

        self.push_undo()
        orig_tl_start = float(c["tl_start"])
        right_clip = copy.deepcopy(c)
        right_clip["id"] = self.next_id("clip")
        base_name = c.get("name", "Clip").split(" #")[0]
        c["src_end"] = round(src_split, 3)
        c["tl_start"] = round(orig_tl_start, 3)
        right_clip["src_start"] = round(src_split, 3)
        right_clip["tl_start"] = round(orig_tl_start + left_dur, 3)
        c["name"] = f"{base_name} #{idx + 1}"
        right_clip["name"] = f"{base_name} #{idx + 2}"
        self.clips.insert(idx + 1, right_clip)
        for i, cl in enumerate(self.clips):
            b = cl.get("name", "Clip").split(" #")[0]
            if len(self.clips) > 1 and not b.startswith("🔇"):
                cl["name"] = f"{b} #{i + 1}"
        self.recompute_timeline(pack_gaps=False)
        return idx + 1

    def delete_clip(self, clip_idx: int) -> bool:
        if not self.clips or not (0 <= clip_idx < len(self.clips)):
            return False
        if len(self.clips) == 1:
            return False
        self.push_undo()
        removed = self.clips.pop(clip_idx)
        removed_dur = float(removed.get("tl_dur", 0.0))
        removed_start = float(removed.get("tl_start", 0.0))

        if self.ripple_mode and removed_dur > 0:
            for j in range(clip_idx, len(self.clips)):
                self.clips[j]["tl_start"] = round(max(0.0, float(self.clips[j].get("tl_start", 0.0)) - removed_dur), 3)
        self.recompute_timeline(pack_gaps=False)

        if self.ripple_mode and removed_dur > 0:
            new_tot = self.total_duration
            for track_list in (self.media_items, self.text_items, self.logo_items):
                for it in track_list:
                    if it.get("full_duration", False):
                        continue
                    s = float(it.get("start_sec", 0.0))
                    e = float(it.get("end_sec", 5.0))
                    if s >= removed_start + removed_dur:
                        it["start_sec"] = round(max(0.0, s - removed_dur), 2)
                        it["end_sec"] = round(max(it["start_sec"] + 0.3, e - removed_dur), 2)
                    elif e > removed_start:
                        it["end_sec"] = round(min(new_tot, max(s + 0.3, e - min(removed_dur, e - removed_start))), 2)
        return True

    def duplicate_clip(self, clip_idx: int) -> Optional[int]:
        if not self.clips or not (0 <= clip_idx < len(self.clips)):
            return None
        self.push_undo()
        orig = self.clips[clip_idx]
        dup = copy.deepcopy(orig)
        dup["id"] = self.next_id("clip")
        b = dup.get("name", "Clip").split(" #")[0]
        dup["name"] = f"{b} (Copy)"
        dup_dur = float(orig.get("tl_dur", 1.0))
        dup["tl_start"] = round(float(orig.get("tl_end", 0.0)), 3)
        for j in range(clip_idx + 1, len(self.clips)):
            self.clips[j]["tl_start"] = round(float(self.clips[j].get("tl_start", 0.0)) + dup_dur, 3)
        self.clips.insert(clip_idx + 1, dup)
        self.recompute_timeline(pack_gaps=False)
        return clip_idx + 1

    def move_clip(self, from_idx: int, to_idx: int) -> Optional[int]:
        if not self.clips or from_idx == to_idx:
            return from_idx
        if not (0 <= from_idx < len(self.clips)) or not (0 <= to_idx < len(self.clips)):
            return None
        self.push_undo()
        c = self.clips.pop(from_idx)
        self.clips.insert(to_idx, c)
        self.recompute_timeline(pack_gaps=True)
        return to_idx

    def apply_silence_cuts_to_timeline(
        self,
        keep_intervals: List[Tuple[float, float]],
        remove_silences: bool = True,
        min_piece_sec: float = 0.10,
        is_ar: bool = True,
    ) -> int:
        """
        Applies detected speech keep_intervals directly onto the live V1/A1 clips!
        - If remove_silences=True: keeps only speech segments (packed back-to-back if self.ripple_mode
          is True, or separated by real timeline gaps if self.ripple_mode is False!).
        - If remove_silences=False: splits clips at silence boundaries and marks silent parts as muted
          clips so the user can review, drag, unmute, or delete them individually!
        Returns number of resulting clips (or 0 if no change).
        """
        if not self.clips or not keep_intervals:
            return 0

        clean_keep = sorted(
            [(max(0.0, float(s)), max(0.0, float(e))) for s, e in keep_intervals if float(e) - float(s) >= min_piece_sec],
            key=lambda x: x[0],
        )
        if not clean_keep:
            return 0

        new_clips: List[Dict[str, Any]] = []
        cur_packed_tl = 0.0
        speech_num = 1
        sil_label = "🔇 صمت" if is_ar else "🔇 Silence"

        for c in self.clips:
            cs0 = float(c["src_start"])
            cs1 = float(c["src_end"])
            spd = max(0.25, float(c.get("speed", 1.0)))
            orig_tl_s = float(c.get("tl_start", cur_packed_tl))
            base_name = c.get("name", "Clip").split(" #")[0]
            if base_name.startswith("🔇"):
                base_name = "Clip"

            if remove_silences:
                for ks, ke in clean_keep:
                    ov_s = max(cs0, ks)
                    ov_e = min(cs1, ke)
                    if (ov_e - ov_s) / spd >= min_piece_sec:
                        sub = copy.deepcopy(c)
                        sub["id"] = self.next_id("clip")
                        sub["src_start"] = round(ov_s, 3)
                        sub["src_end"] = round(ov_e, 3)
                        sub_dur = (ov_e - ov_s) / spd
                        if self.ripple_mode:
                            sub["tl_start"] = round(cur_packed_tl, 3)
                            cur_packed_tl += sub_dur
                        else:
                            sub["tl_start"] = round(orig_tl_s + (ov_s - cs0) / spd, 3)
                        sub["name"] = f"{base_name} #{speech_num}"
                        speech_num += 1
                        new_clips.append(sub)
            else:
                cursor_src = cs0
                for ks, ke in clean_keep:
                    if ke <= cs0:
                        continue
                    if ks >= cs1:
                        break
                    ov_s = max(cs0, ks)
                    ov_e = min(cs1, ke)
                    # Preceding silence piece inside this clip
                    if (ov_s - cursor_src) / spd >= min_piece_sec:
                        sil_c = copy.deepcopy(c)
                        sil_c["id"] = self.next_id("clip")
                        sil_c["src_start"] = round(cursor_src, 3)
                        sil_c["src_end"] = round(ov_s, 3)
                        sil_c["tl_start"] = round(orig_tl_s + (cursor_src - cs0) / spd, 3)
                        sil_c["muted"] = True
                        sil_c["name"] = sil_label
                        new_clips.append(sil_c)
                    # Speech piece
                    if (ov_e - ov_s) / spd >= min_piece_sec:
                        sp_c = copy.deepcopy(c)
                        sp_c["id"] = self.next_id("clip")
                        sp_c["src_start"] = round(ov_s, 3)
                        sp_c["src_end"] = round(ov_e, 3)
                        sp_c["tl_start"] = round(orig_tl_s + (ov_s - cs0) / spd, 3)
                        sp_c["name"] = f"{base_name} #{speech_num}"
                        speech_num += 1
                        new_clips.append(sp_c)
                    cursor_src = max(cursor_src, ov_e)
                # Trailing silence piece inside this clip
                if (cs1 - cursor_src) / spd >= min_piece_sec:
                    sil_c = copy.deepcopy(c)
                    sil_c["id"] = self.next_id("clip")
                    sil_c["src_start"] = round(cursor_src, 3)
                    sil_c["src_end"] = round(cs1, 3)
                    sil_c["tl_start"] = round(orig_tl_s + (cursor_src - cs0) / spd, 3)
                    sil_c["muted"] = True
                    sil_c["name"] = sil_label
                    new_clips.append(sil_c)

        if not new_clips:
            return 0

        self.push_undo()
        self.clips = new_clips
        self.recompute_timeline(pack_gaps=bool(remove_silences and self.ripple_mode))
        return len(self.clips)

    def get_track_list(self, track_key: str) -> List[Dict[str, Any]]:
        if track_key == "V2":
            return self.media_items
        if track_key == "V3":
            return self.text_items
        if track_key == "V4":
            return self.logo_items
        return []

    def split_overlay_at(self, track_key: str, item_idx: int, tl_sec: float) -> Optional[int]:
        t_list = self.get_track_list(track_key)
        if not (0 <= item_idx < len(t_list)):
            return None
        item = t_list[item_idx]
        tot = self.total_duration
        s0 = 0.0 if item.get("full_duration") else float(item.get("start_sec", 0.0))
        e0 = tot if item.get("full_duration") else float(item.get("end_sec", tot))
        if tl_sec - s0 < 0.15 or e0 - tl_sec < 0.15:
            return None

        self.push_undo()
        item["full_duration"] = False
        item["start_sec"] = round(s0, 2)
        item["end_sec"] = round(tl_sec, 2)

        right_item = copy.deepcopy(item)
        right_item["id"] = self.next_id(track_key.lower())
        right_item["start_sec"] = round(tl_sec, 2)
        right_item["end_sec"] = round(e0, 2)
        t_list.insert(item_idx + 1, right_item)
        return item_idx + 1

    def is_item_visible_at(self, track_key: str, item: Dict[str, Any], tl_sec: float) -> bool:
        if not self.track_enabled.get(track_key, True):
            return False
        if not item.get("enabled", True):
            return False
        if item.get("full_duration", False):
            return True
        s = float(item.get("start_sec", 0.0))
        e = float(item.get("end_sec", max(5.0, self.total_duration)))
        return (s - 0.04) <= tl_sec <= (e + 0.04)

    def remap_srt_segments_to_timeline(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Maps SRT/Whisper subtitle segments (in original source timestamps) onto the edited V1 timeline!
        Handles cuts, timeline gaps, deleted middle sections, reordered clips, duplicated hooks, and speed changes.
        """
        if not segments or not self.clips:
            return segments
        self.recompute_timeline()
        remapped = []
        for clip in self.clips:
            cs0 = clip["src_start"]
            cs1 = clip["src_end"]
            tl0 = clip["tl_start"]
            spd = max(0.25, float(clip.get("speed", 1.0)))
            for seg in segments:
                ss = float(seg.get("start", 0.0))
                se = float(seg.get("end", 0.0))
                ov_s = max(cs0, ss)
                ov_e = min(cs1, se)
                if ov_e - ov_s >= 0.12:
                    new_s = tl0 + (ov_s - cs0) / spd
                    new_e = tl0 + (ov_e - cs0) / spd
                    remapped.append({
                        "start": round(new_s, 3),
                        "end": round(new_e, 3),
                        "text": seg.get("text", ""),
                    })
        return remapped


def parse_srt_segments(srt_text: str) -> List[Dict[str, Any]]:
    """
    Parses standard SRT text into [{'start': float, 'end': float, 'text': str}, ...]
    so external .srt subtitle files can be remapped onto edited NLE clips.
    """
    import re
    segments: List[Dict[str, Any]] = []
    if not srt_text:
        return segments
    re_tc = re.compile(
        r"(\d{1,2}):(\d{2}):(\d{2})[,\.](\d{1,3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,\.](\d{1,3})"
    )
    blocks = re.split(r"\r?\n\s*\r?\n", srt_text.lstrip("\ufeff").strip())
    for blk in blocks:
        lines = [ln.strip() for ln in blk.splitlines() if ln.strip()]
        if not lines:
            continue
        tc_idx = -1
        m = None
        for i, ln in enumerate(lines[:3]):
            m = re_tc.search(ln)
            if m:
                tc_idx = i
                break
        if m is None or tc_idx < 0:
            continue
        s_sec = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int(m.group(4).ljust(3, "0")[:3]) / 1000.0
        e_sec = int(m.group(5)) * 3600 + int(m.group(6)) * 60 + int(m.group(7)) + int(m.group(8).ljust(3, "0")[:3]) / 1000.0
        txt = "\n".join(lines[tc_idx + 1:]).strip()
        if txt and e_sec > s_sec:
            segments.append({"start": round(s_sec, 3), "end": round(e_sec, 3), "text": txt})
    return segments


class FastVideoPreviewProvider:
    """
    Ultra-low-latency video frame decoder powered by PyAV + C libswscale (with FFmpeg CLI fallback).
    Maintains a persistent packet/frame iterator for sequential 30 FPS playback (~1.5-4ms per frame)
    and seeks keyframes only on backward scrubs or large forward jumps!
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._container = None
        self._stream = None
        self._stream_rotation: int = 0
        self._frame_iter = None
        self._open_path: Optional[str] = None
        self._last_decoded_sec: float = -999.0
        self._last_max_dim: int = 0
        self._last_pil: Optional[Image.Image] = None

    def close(self):
        with self._lock:
            self._frame_iter = None
            if self._container is not None:
                try:
                    self._container.close()
                except Exception:
                    pass
                self._container = None
                self._stream = None
                self._stream_rotation = 0
                self._open_path = None
                self._last_decoded_sec = -999.0
                self._last_pil = None

    def get_frame(self, video_path: Path, timestamp_sec: float, max_dim: int = 640) -> Optional[Image.Image]:
        p_str = str(Path(video_path).resolve())
        ts = max(0.0, float(timestamp_sec or 0.0))
        max_dim = max(160, int(max_dim or 640))

        if av is not None:
            with self._lock:
                try:
                    if self._open_path != p_str or self._container is None:
                        self._frame_iter = None
                        if self._container is not None:
                            try:
                                self._container.close()
                            except Exception:
                                pass
                        self._container = av.open(p_str)
                        v_streams = [s for s in self._container.streams.video]
                        if not v_streams:
                            self._container.close()
                            self._container = None
                            return None
                        self._stream = v_streams[0]
                        self._stream.thread_type = "AUTO"
                        self._stream_rotation = 0
                        if hasattr(self._stream, "metadata") and self._stream.metadata:
                            try:
                                self._stream_rotation = int(round(float(self._stream.metadata.get("rotate", 0) or 0)))
                            except (ValueError, TypeError):
                                self._stream_rotation = 0
                        self._frame_iter = self._container.decode(self._stream)
                        self._open_path = p_str
                        self._last_decoded_sec = -999.0
                        self._last_pil = None

                    delta = ts - self._last_decoded_sec

                    # 1. Quick reuse if within playback jitter window (-0.12s to +0.024s)
                    if -0.12 <= delta <= 0.024 and self._last_pil is not None and abs(self._last_max_dim - max_dim) <= 96:
                        return self._last_pil

                    # 2. Seek only when scrubbing backward (< -0.40s) or jumping forward (> 1.25s) or on reset
                    need_seek = (delta < -0.40) or (delta > 1.25) or (self._last_decoded_sec < 0) or (self._frame_iter is None)
                    if need_seek:
                        tb = float(self._stream.time_base) if self._stream.time_base else (1.0 / 30.0)
                        seek_sec = max(0.0, ts - 0.08)
                        seek_pts = int(seek_sec / tb)
                        try:
                            self._container.seek(seek_pts, stream=self._stream, any_frame=False, backward=True)
                        except Exception:
                            self._container.seek(int(seek_sec * av.time_base), any_frame=False, backward=True)
                        self._frame_iter = self._container.decode(self._stream)

                    best_frame = None
                    tb = float(self._stream.time_base) if self._stream.time_base else (1.0 / 30.0)
                    frames_checked = 0
                    max_scan = 45 if need_seek else 3

                    for frame in self._frame_iter:
                        frames_checked += 1
                        f_sec = float(frame.pts * tb) if frame.pts is not None else ts
                        best_frame = frame
                        self._last_decoded_sec = f_sec
                        if f_sec >= ts - 0.018 or frames_checked >= max_scan:
                            break

                    if best_frame is not None:
                        w, h = best_frame.width, best_frame.height
                        if max(w, h) > max_dim:
                            scale = max_dim / float(max(w, h))
                            nw = max(2, int(w * scale) & ~1)
                            nh = max(2, int(h * scale) & ~1)
                            rgb_frame = best_frame.reformat(width=nw, height=nh, format="rgb24")
                        else:
                            rgb_frame = best_frame.reformat(format="rgb24")
                        pil_im = rgb_frame.to_image()

                        f_rot = 0
                        try:
                            f_rot = int(round(float(getattr(best_frame, "rotation", 0) or getattr(self, "_stream_rotation", 0) or 0)))
                        except (ValueError, TypeError):
                            f_rot = 0

                        if f_rot:
                            rot_cw = (-f_rot) % 360
                            if rot_cw == 90:
                                pil_im = pil_im.transpose(Image.Transpose.ROTATE_270)
                            elif rot_cw == 180:
                                pil_im = pil_im.transpose(Image.Transpose.ROTATE_180)
                            elif rot_cw == 270:
                                pil_im = pil_im.transpose(Image.Transpose.ROTATE_90)

                        self._last_pil = pil_im
                        self._last_max_dim = max_dim
                        return pil_im
                    elif self._last_pil is not None:
                        return self._last_pil
                except Exception:
                    self._frame_iter = None
                    try:
                        if self._container is not None:
                            self._container.close()
                    except Exception:
                        pass
                    self._container = None
                    self._open_path = None

        # Fallback to FFmpeg frame extractor
        try:
            return extract_video_sample_frame(video_path, timestamp=max(0.05, ts), max_dim=max_dim)
        except Exception:
            return None


def extract_audio_waveform_peaks(
    media_path: Path,
    num_buckets: int = 6000,
    ffmpeg_exe: Optional[str] = None,
) -> Optional[List[float]]:
    """
    Extracts real normalized [0.03 .. 1.0] high-density audio waveform peak bars across the full media file
    for rendering DaVinci Resolve's green A1 audio waveform track even at deep syllable zoom!
    """
    media_path = Path(media_path).resolve()
    if not media_path.is_file():
        return None

    # Fast in-process PyAV decode (resampled to 800 Hz mono int16 for crisp syllable zoom)
    if av is not None:
        try:
            chunks = []
            with av.open(str(media_path)) as container:
                if not container.streams.audio:
                    return None
                a_stream = container.streams.audio[0]
                resampler = av.AudioResampler(format="s16", layout="mono", rate=800)
                for frame in container.decode(a_stream):
                    for rf in resampler.resample(frame):
                        arr = rf.to_ndarray()
                        chunks.append(arr.reshape(-1))
            if chunks:
                samples = np.abs(np.concatenate(chunks).astype(np.float32))
                if samples.size > 0:
                    b = min(num_buckets, max(32, samples.size))
                    pad_len = (b - (samples.size % b)) % b
                    if pad_len:
                        samples = np.pad(samples, (0, pad_len), mode="edge")
                    peaks = samples.reshape(b, -1).max(axis=1)
                    p99 = float(np.percentile(peaks, 99)) if peaks.size else 1.0
                    denom = max(120.0, p99)
                    norm = np.clip(peaks / denom, 0.03, 1.0)
                    return [round(float(x), 3) for x in norm]
        except Exception:
            pass

    # Fallback: FFmpeg raw s16le pipe at 800 Hz
    try:
        ff = ffmpeg_exe or "ffmpeg"
        cmd = [
            str(ff),
            "-hide_banner",
            "-loglevel", "error",
            "-i", str(media_path),
            "-vn",
            "-ac", "1",
            "-ar", "800",
            "-f", "s16le",
            "-",
        ]
        res = subprocess.run(
            cmd,
            capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            timeout=30,
        )
        if res.returncode == 0 and res.stdout:
            samples = np.abs(np.frombuffer(res.stdout, dtype=np.int16).astype(np.float32))
            if samples.size > 0:
                b = min(num_buckets, max(32, samples.size))
                pad_len = (b - (samples.size % b)) % b
                if pad_len:
                    samples = np.pad(samples, (0, pad_len), mode="edge")
                peaks = samples.reshape(b, -1).max(axis=1)
                p99 = float(np.percentile(peaks, 99)) if peaks.size else 1.0
                denom = max(120.0, p99)
                norm = np.clip(peaks / denom, 0.03, 1.0)
                return [round(float(x), 3) for x in norm]
    except Exception:
        pass

    return None
