"""
Session Persistence & Auto-Save Recovery Engine
Handles automatic atomic project autosaving after every step, crash recovery,
session snapshot serialization, and instant project restoration.
Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

import copy
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

AUTOSAVE_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Media Audio Studio"
AUTOSAVE_FILE = AUTOSAVE_DIR / "autosave_session.json"
AUTOSAVE_TMP = AUTOSAVE_DIR / "autosave_session.json.tmp"


def get_autosave_path() -> Path:
    return AUTOSAVE_FILE


def save_session_state(session_dict: Dict[str, Any], clean_exit: bool = False) -> bool:
    """
    Atomically writes the current full session state to disk.
    Guaranteed atomic write via temporary file replacement so a crash during write
    can never corrupt the autosave file.
    """
    try:
        AUTOSAVE_DIR.mkdir(parents=True, exist_ok=True)
        payload = copy.deepcopy(session_dict)
        payload["version"] = 1
        payload["timestamp"] = time.time()
        payload["clean_exit"] = bool(clean_exit)
        payload["saved_at_readable"] = time.strftime("%Y-%m-%d %H:%M:%S")

        # Atomic write
        with open(AUTOSAVE_TMP, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())

        if AUTOSAVE_TMP.exists():
            AUTOSAVE_TMP.replace(AUTOSAVE_FILE)
        return True
    except Exception as e:
        # Fallback silent protect
        try:
            if AUTOSAVE_TMP.exists():
                AUTOSAVE_TMP.unlink()
        except Exception:
            pass
        return False


def load_session_state() -> Optional[Dict[str, Any]]:
    """
    Safely reads and parses the autosave session from disk.
    Returns None if file is missing or invalid.
    """
    try:
        if not AUTOSAVE_FILE.exists():
            return None
        content = AUTOSAVE_FILE.read_text(encoding="utf-8")
        data = json.loads(content)
        if not isinstance(data, dict):
            return None
        return data
    except Exception:
        return None


def has_recoverable_session() -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Checks if a recoverable previous session exists.
    Validates that:
    1. The autosave file exists and can be parsed.
    2. The source media file path still exists on the user's filesystem.
    3. The session was either abnormally closed (clean_exit == False) or contains timeline clips/edits.
    """
    data = load_session_state()
    if not data:
        return False, None

    media_path_str = str(data.get("media_path") or "").strip()
    if not media_path_str:
        return False, None

    media_path = Path(media_path_str)
    if not media_path.exists():
        return False, None

    nle = data.get("nle_project", {})
    clips = nle.get("clips", [])
    has_meaningful_work = len(clips) > 1 or bool(nle.get("text_items")) or bool(nle.get("media_items"))
    was_crash = not bool(data.get("clean_exit", True))

    if was_crash or has_meaningful_work:
        return True, data

    return False, None


def mark_clean_exit() -> bool:
    """
    Updates the autosave file to mark clean_exit=True when user normally closes the app.
    """
    data = load_session_state()
    if data:
        return save_session_state(data, clean_exit=True)
    return False


def clear_autosave() -> bool:
    """
    Deletes the autosave file (e.g. when user explicitly starts a new blank project).
    """
    try:
        if AUTOSAVE_FILE.exists():
            AUTOSAVE_FILE.unlink()
        if AUTOSAVE_TMP.exists():
            AUTOSAVE_TMP.unlink()
        return True
    except Exception:
        return False
