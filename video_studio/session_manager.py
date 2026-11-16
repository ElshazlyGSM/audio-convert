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
from typing import Any, Dict, List, Optional, Tuple, Union

AUTOSAVE_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ClipCraft Studio"
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


PROJECT_EXTENSION = ".masproj"
RECENT_PROJECTS_FILE = AUTOSAVE_DIR / "recent_projects.json"
RECENT_MEDIA_FILE = AUTOSAVE_DIR / "recent_media.json"


def save_project_file(file_path: Path, project_data: Dict[str, Any]) -> bool:
    """
    Saves a complete Media Audio Studio project file (.masproj or .json).
    Stores media path as both absolute and relative (to project directory)
    for seamless folder portability.
    """
    try:
        p_path = Path(file_path)
        p_path.parent.mkdir(parents=True, exist_ok=True)
        payload = copy.deepcopy(project_data)
        payload["format"] = "MediaAudioStudioProject"
        payload["version"] = 2
        payload["saved_at"] = time.time()
        payload["saved_at_readable"] = time.strftime("%Y-%m-%d %H:%M:%S")

        media_str = payload.get("media_path", "")
        if media_str:
            m_path = Path(media_str)
            try:
                rel = os.path.relpath(str(m_path), str(p_path.parent))
                payload["media_rel_path"] = rel
            except Exception:
                payload["media_rel_path"] = ""

        tmp_file = p_path.with_suffix(p_path.suffix + ".tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())

        if tmp_file.exists():
            tmp_file.replace(p_path)

        add_recent_project(
            p_path,
            title=payload.get("project_name", p_path.stem),
            clips_count=len(payload.get("nle_project", {}).get("clips", [])),
        )
        return True
    except Exception as e:
        logger_name = "session_manager"
        try:
            if tmp_file.exists():
                tmp_file.unlink()
        except Exception:
            pass
        return False


def load_project_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Loads and parses a .masproj or .json project file.
    Resolves relative media paths if media was moved together with the project.
    """
    try:
        p_path = Path(file_path)
        if not p_path.is_file():
            return None
        content = p_path.read_text(encoding="utf-8")
        data = json.loads(content)
        if not isinstance(data, dict):
            return None

        # Resolve media path: 1. Absolute -> 2. Relative to project file -> 3. Same folder by filename
        raw_media = data.get("media_path", "")
        rel_media = data.get("media_rel_path", "")

        resolved_media = None
        if raw_media and Path(raw_media).is_file():
            resolved_media = Path(raw_media)
        elif rel_media:
            cand = (p_path.parent / rel_media).resolve()
            if cand.is_file():
                resolved_media = cand
        if not resolved_media and raw_media:
            cand_same_dir = p_path.parent / Path(raw_media).name
            if cand_same_dir.is_file():
                resolved_media = cand_same_dir

        if resolved_media:
            data["media_path"] = str(resolved_media)

        add_recent_project(
            p_path,
            title=data.get("project_name", p_path.stem),
            clips_count=len(data.get("nle_project", {}).get("clips", [])),
        )
        return data
    except Exception:
        return None


def get_recent_projects(max_items: int = 15) -> List[Dict[str, Any]]:
    """
    Returns list of recently opened/saved projects.
    """
    try:
        if not RECENT_PROJECTS_FILE.exists():
            return []
        content = RECENT_PROJECTS_FILE.read_text(encoding="utf-8")
        data = json.loads(content)
        if isinstance(data, list):
            # Filter existing files
            valid = [item for item in data if isinstance(item, dict) and Path(item.get("path", "")).is_file()]
            return valid[:max_items]
        return []
    except Exception:
        return []


def add_recent_project(project_path: Path, title: str = "", clips_count: int = 1):
    """
    Adds a project to the recent projects list.
    """
    try:
        AUTOSAVE_DIR.mkdir(parents=True, exist_ok=True)
        items = get_recent_projects(50)
        p_str = str(Path(project_path).resolve())
        # Filter existing matching entry
        items = [it for it in items if str(Path(it.get("path", "")).resolve()) != p_str]
        new_entry = {
            "path": p_str,
            "title": title or Path(project_path).stem,
            "last_opened": time.strftime("%Y-%m-%d %H:%M"),
            "clips_count": int(clips_count),
        }
        items.insert(0, new_entry)
        RECENT_PROJECTS_FILE.write_text(json.dumps(items[:20], ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def get_recent_media(max_items: int = 15) -> List[Dict[str, Any]]:
    """
    Returns list of recently opened media video/audio files.
    """
    try:
        if not RECENT_MEDIA_FILE.exists():
            return []
        content = RECENT_MEDIA_FILE.read_text(encoding="utf-8")
        data = json.loads(content)
        if isinstance(data, list):
            valid = [item for item in data if isinstance(item, dict) and Path(item.get("path", "")).is_file()]
            return valid[:max_items]
        return []
    except Exception:
        return []


def add_recent_media(media_path: Path):
    """
    Adds a media file to the recent media list.
    """
    try:
        AUTOSAVE_DIR.mkdir(parents=True, exist_ok=True)
        items = get_recent_media(50)
        m_str = str(Path(media_path).resolve())
        items = [it for it in items if str(Path(it.get("path", "")).resolve()) != m_str]
        new_entry = {
            "path": m_str,
            "name": Path(media_path).name,
            "last_opened": time.strftime("%Y-%m-%d %H:%M"),
        }
        items.insert(0, new_entry)
        RECENT_MEDIA_FILE.write_text(json.dumps(items[:20], ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

