"""
ClipCraft Studio - Audio & Video Processing Core
Developer: ahmed elshazly
Email: Elshazly.gsm@gmail.com
"""

__author__ = "ahmed elshazly"
__email__ = "Elshazly.gsm@gmail.com"
__version__ = "1.0.0"

import re
import shutil
import subprocess
import sys
import os
import threading
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import quote, urlparse

import requests
from PIL import Image
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, ID3, TIT2, TPE1
from mutagen.mp4 import MP4, MP4Cover
from mutagen.mp3 import MP3

try:
    import yt_dlp
except Exception:
    yt_dlp = None

try:
    import av
    _orig_av_open = av.open
    def _safe_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _orig_av_open(*args, **kwargs)
    av.open = _safe_av_open
except Exception:
    av = None

try:
    import faster_whisper
except Exception:
    faster_whisper = None



folder = Path.cwd()
APP_DIR = Path(__file__).parent.resolve()
INPUT_DIR = folder / "input"
OUTPUT_DIR = folder / "output"
CACHE_DIR = APP_DIR / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
REFRESH_EXISTING_COVERS = False
AUDIO_EXTS = {".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus", ".wma"}
VIDEO_EXTS = {
    ".mp4",
    ".mkv",
    ".mov",
    ".avi",
    ".webm",
    ".flv",
    ".wmv",
    ".m4v",
    ".3gp",
}
MEDIA_EXTS = AUDIO_EXTS | VIDEO_EXTS
OUTPUT_FORMATS = {
    ".mp3": {"label": "MP3", "args": ["-codec:a", "libmp3lame", "-b:a", "{quality}"]},
    ".m4a": {"label": "M4A", "args": ["-codec:a", "aac", "-b:a", "{quality}"]},
    ".aac": {"label": "AAC", "args": ["-codec:a", "aac", "-b:a", "192k"]},
    ".wav": {"label": "WAV", "args": ["-codec:a", "pcm_s16le"]},
    ".flac": {"label": "FLAC", "args": ["-codec:a", "flac"]},
    ".ogg": {"label": "OGG", "args": ["-codec:a", "libvorbis", "-b:a", "192k"]},
    ".opus": {"label": "OPUS", "args": ["-codec:a", "libopus", "-b:a", "128k"]},
    ".wma": {"label": "WMA", "args": ["-codec:a", "wmav2", "-b:a", "192k"]},
}
VIDEO_OUTPUT_FORMATS = {
    ".mp4": {
        "label": "MP4",
        "video_codec": "libx264",
        "audio_codec": "aac",
        "container_args": ["-movflags", "+faststart"],
        "rate_control": "crf",
    },
    ".mkv": {
        "label": "MKV",
        "video_codec": "libx264",
        "audio_codec": "aac",
        "container_args": [],
        "rate_control": "crf",
    },
    ".avi": {
        "label": "AVI",
        "video_codec": "mpeg4",
        "audio_codec": "libmp3lame",
        "container_args": ["-vtag", "xvid"],
        "rate_control": "qscale",
    },
    ".mov": {
        "label": "MOV",
        "video_codec": "libx264",
        "audio_codec": "aac",
        "container_args": ["-movflags", "+faststart"],
        "rate_control": "crf",
    },
    ".webm": {
        "label": "WEBM",
        "video_codec": "libvpx-vp9",
        "audio_codec": "libopus",
        "container_args": ["-deadline", "realtime", "-cpu-used", "4", "-row-mt", "1"],
        "rate_control": "vp9",
    },
    ".wmv": {
        "label": "WMV",
        "video_codec": "wmv2",
        "audio_codec": "wmav2",
        "container_args": [],
        "rate_control": "qscale",
    },
    ".flv": {
        "label": "FLV",
        "video_codec": "libx264",
        "audio_codec": "aac",
        "container_args": [],
        "rate_control": "crf",
    },
    ".3gp": {
        "label": "3GP",
        "video_codec": "libx264",
        "audio_codec": "aac",
        "container_args": [],
        "rate_control": "crf",
    },
}
QUALITY_OPTIONS = ("128k", "192k", "256k", "320k")
YOUTUBE_AUDIO_FORMAT_ID = "__audio_mp3__"
YOUTUBE_BEST_VIDEO_FORMAT_ID = "__best_video_mp4__"
YOUTUBE_BEST_VIDEO_FORMAT = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
VIDEO_COMPRESSION_PRESETS = {
    "Original": {
        "label": "Original quality (no compression)",
        "crf": "18",
        "qscale": "2",
        "crf_vp9": "20",
        "audio_bitrate": "320k",
    },
    "Very High": {
        "label": "Very high quality",
        "crf": "20",
        "qscale": "3",
        "crf_vp9": "24",
        "audio_bitrate": "192k",
    },
    "High": {
        "label": "High quality",
        "crf": "24",
        "qscale": "4",
        "crf_vp9": "28",
        "audio_bitrate": "160k",
    },
    "Medium": {
        "label": "Medium file",
        "crf": "28",
        "qscale": "6",
        "crf_vp9": "33",
        "audio_bitrate": "128k",
    },
    "Small": {
        "label": "Small file",
        "crf": "32",
        "qscale": "8",
        "crf_vp9": "38",
        "audio_bitrate": "96k",
    },
    "Very Small": {
        "label": "Very small file",
        "crf": "36",
        "qscale": "11",
        "crf_vp9": "44",
        "audio_bitrate": "80k",
    },
}
VIDEO_RESOLUTION_PRESETS = {
    "Original": {
        "label": "Original size",
        "scale": None,
    },
    "1080p": {
        "label": "Limit to 1080p",
        "scale": "1920:1080",
    },
    "720p": {
        "label": "Limit to 720p",
        "scale": "1280:720",
    },
    "480p": {
        "label": "Limit to 480p",
        "scale": "854:480",
    },
    "360p": {
        "label": "Limit to 360p",
        "scale": "640:360",
    },
}
ENHANCEMENT_PRESETS = {
    "Off": [],
    "Normalize volume": ["loudnorm=I=-16:TP=-1.5:LRA=11"],
    "Louder and clearer": [
        "highpass=f=70",
        "lowpass=f=14000",
        "equalizer=f=3000:width_type=h:width=2500:g=3",
        "speechnorm=e=4:c=2:t=0.02",
        "loudnorm=I=-14:TP=-1.2:LRA=9",
    ],
    "Noise reduction": ["afftdn=nf=-30"],
    "Strong noise cleanup": [
        "highpass=f=90",
        "lowpass=f=11000",
        "afftdn=nf=-35",
        "anlmdn=s=0.0003:p=0.002:r=0.006:m=11",
        "speechnorm=e=3:c=2:t=0.02",
        "loudnorm=I=-16:TP=-1.5:LRA=10",
    ],
    "Podcast voice": [
        "highpass=f=80",
        "lowpass=f=12500",
        "afftdn=nf=-30",
        "anlmdn=s=0.0002:p=0.002:r=0.006:m=11",
        "equalizer=f=180:width_type=h:width=120:g=-2",
        "equalizer=f=3500:width_type=h:width=2200:g=4",
        "speechnorm=e=5:c=2:t=0.015",
        "compand=attacks=0.05:decays=0.4:points=-80/-80|-45/-35|-18/-12|-6/-5|0/-3:soft-knee=6",
        "loudnorm=I=-14:TP=-1.2:LRA=8",
    ],
    "Reduce echo": [
        "highpass=f=120",
        "lowpass=f=8500",
        "afftdn=nf=-32",
        "anlmdn=s=0.0004:p=0.002:r=0.008:m=15",
        "speechnorm=e=3:c=2:t=0.03",
    ],
    "Auto clean all": [
        "highpass=f=85",
        "lowpass=f=12000",
        "afftdn=nf=-34",
        "anlmdn=s=0.00035:p=0.002:r=0.008:m=13",
        "equalizer=f=200:width_type=h:width=160:g=-2",
        "equalizer=f=3200:width_type=h:width=2400:g=4",
        "speechnorm=e=5:c=2:t=0.015",
        "compand=attacks=0.05:decays=0.5:points=-80/-80|-45/-34|-20/-13|-6/-5|0/-3:soft-knee=6",
        "loudnorm=I=-14:TP=-1.2:LRA=8",
    ],
}


class CancelledError(RuntimeError):
    pass


WHISPER_MODELS = {
    "small": {"label": "⚡ Small (~465MB, Recommended Balanced - موصى به)", "id": "small"},
    "base": {"label": "Base (~140MB, Fast - سريع)", "id": "base"},
    "turbo": {"label": "🚀 Large-v3 Turbo (~1.5GB, Best Quality - مثل CapCut/NoteGPT)", "id": "turbo"},
    "tiny": {"label": "Tiny (~75MB, Ultra Fast - فائق السرعة)", "id": "tiny"},
    "medium": {"label": "💎 Medium (~1.5GB, Very High Quality)", "id": "medium"},
}

WHISPER_LANGUAGES = {
    "auto": "Auto Detect (تلقائي)",
    "ar": "Arabic (العربية)",
    "en": "English (الإنجليزية)",
    "fr": "French (الفرنسية)",
    "es": "Spanish (الإسبانية)",
    "de": "German (الألمانية)",
    "it": "Italian (الإيطالية)",
    "tr": "Turkish (التركية)",
    "ru": "Russian (الروسية)",
    "zh": "Chinese (الصينية)",
    "ja": "Japanese (اليابانية)",
    "ko": "Korean (الكورية)",
    "ur": "Urdu (الأوردو)",
}

SUBTITLE_TRANSLATION_LANGUAGES = {
    "none": "Original Audio Language (نفس لغة الصوت الأصلية)",
    "ar": "Arabic (العربية)",
    "en": "English (الإنجليزية)",
    "fr": "French (الفرنسية)",
    "es": "Spanish (الإسبانية)",
    "de": "German (الألمانية)",
    "it": "Italian (الإيطالية)",
    "tr": "Turkish (التركية)",
    "ru": "Russian (الروسية)",
    "zh-CN": "Chinese (الصينية)",
    "ja": "Japanese (اليابانية)",
    "ko": "Korean (الكورية)",
    "ur": "Urdu (الأوردو)",
}


def whisper_available():
    return faster_whisper is not None



def app_base_dir():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def ffmpeg_executable():
    bundled = app_base_dir() / "ffmpeg.exe"
    if bundled.exists():
        return bundled

    discovered = shutil.which("ffmpeg")
    if discovered:
        return Path(discovered)

    raise FileNotFoundError("ffmpeg.exe was not found")


def ffplay_executable():
    bundled = app_base_dir() / "ffplay.exe"
    if bundled.exists():
        return bundled

    discovered = shutil.which("ffplay")
    if discovered:
        return Path(discovered)

    raise FileNotFoundError("ffplay.exe was not found")


def ffprobe_executable():
    bundled = app_base_dir() / "ffprobe.exe"
    if bundled.exists():
        return bundled

    discovered = shutil.which("ffprobe")
    if discovered:
        return Path(discovered)

    raise FileNotFoundError("ffprobe.exe was not found")


def hidden_subprocess_kwargs():
    if sys.platform.startswith("win"):
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def require_yt_dlp():
    if yt_dlp is None:
        raise RuntimeError("yt-dlp is not installed. Run: python -m pip install -r requirements.txt")
    return yt_dlp


def youtube_ffmpeg_location():
    try:
        return str(ffmpeg_executable().parent)
    except FileNotFoundError:
        return None


def human_size(size):
    if not size:
        return "Unknown"
    size = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def format_filesize(item):
    return item.get("filesize") or item.get("filesize_approx") or 0


def fetch_youtube_formats(url):
    ydl_module = require_yt_dlp()
    options = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "skip_download": True,
        "noplaylist": True,
        "check_formats": True,
    }
    ffmpeg_location = youtube_ffmpeg_location()
    if ffmpeg_location:
        options["ffmpeg_location"] = ffmpeg_location

    with ydl_module.YoutubeDL(options) as downloader:
        info = downloader.extract_info(url, download=False)

    audio_formats = [
        item for item in info.get("formats", [])
        if item.get("acodec") not in (None, "none") and item.get("vcodec") in (None, "none")
    ]
    best_audio = max(audio_formats, key=lambda item: item.get("abr") or item.get("tbr") or 0, default={})
    best_audio_size = format_filesize(best_audio)

    rows = [
        {
            "format_id": YOUTUBE_AUDIO_FORMAT_ID,
            "label": f"Audio only MP3 - {human_size(best_audio_size)}",
            "height": 0,
            "ext": "mp3",
            "has_audio": True,
            "size": best_audio_size,
            "size_label": human_size(best_audio_size),
        }
    ]

    best_video_size = 0
    try:
        best_video = max(
            (
                item for item in info.get("formats", [])
                if item.get("vcodec") not in (None, "none") and (item.get("ext") or "").lower() == "mp4"
            ),
            key=lambda item: ((item.get("height") or 0), (item.get("tbr") or 0)),
        )
        best_video_size = format_filesize(best_video)
        if best_audio_size:
            best_video_size += best_audio_size
    except ValueError:
        pass

    rows.append(
        {
            "format_id": YOUTUBE_BEST_VIDEO_FORMAT_ID,
            "selector": YOUTUBE_BEST_VIDEO_FORMAT,
            "label": f"Best video MP4 (recommended) - {human_size(best_video_size)}",
            "height": 0,
            "ext": "mp4",
            "has_audio": True,
            "size": best_video_size,
            "size_label": human_size(best_video_size),
        }
    )

    seen = set()
    for item in info.get("formats", []):
        if item.get("vcodec") in (None, "none"):
            continue
        format_id = item.get("format_id")
        height = item.get("height")
        ext = item.get("ext") or "video"
        if not format_id or not height:
            continue
        acodec = item.get("acodec")
        has_audio = acodec not in (None, "none")
        key = (height, ext, item.get("fps"), has_audio)
        if key in seen:
            continue
        seen.add(key)
        fps = item.get("fps")
        size = format_filesize(item)
        if not has_audio and best_audio_size:
            size += best_audio_size
        selector = str(format_id) if has_audio else f"{format_id}+bestaudio[ext=m4a]/bestaudio/best"
        label = f"{height}p"
        if fps and fps >= 50:
            label += f"{int(fps)}"
        label += f" {ext.upper()}"
        if not has_audio:
            label += " + audio"
        label += f" ({format_id})"
        label += f" - {human_size(size)}"
        rows.append(
            {
                "format_id": str(format_id),
                "selector": selector,
                "label": label,
                "height": int(height),
                "ext": ext,
                "has_audio": has_audio,
                "size": size,
                "size_label": human_size(size),
            }
        )

    video_rows = sorted(rows[2:], key=lambda row: row["height"], reverse=True)
    rows = rows[:2] + video_rows
    return {
        "title": info.get("title") or "YouTube video",
        "live_status": info.get("live_status"),
        "is_live": bool(info.get("is_live")),
        "formats": rows,
    }


def download_youtube(
    url,
    output_dir=OUTPUT_DIR,
    format_id=YOUTUBE_AUDIO_FORMAT_ID,
    format_has_audio=False,
    audio_quality="192k",
    progress_callback=None,
    cancel_callback=None,
):
    if cancellation_requested(cancel_callback):
        raise CancelledError("Operation canceled")
    ydl_module = require_yt_dlp()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if format_id == YOUTUBE_AUDIO_FORMAT_ID:
        preferred_quality = normalize_quality(audio_quality).removesuffix("k")
        ydl_format = "bestaudio/best"
        postprocessors = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": preferred_quality,
            }
        ]
    elif format_id == YOUTUBE_BEST_VIDEO_FORMAT_ID:
        ydl_format = YOUTUBE_BEST_VIDEO_FORMAT
        postprocessors = []
    else:
        format_text = str(format_id)
        if format_has_audio or "+" in format_text or "/" in format_text:
            ydl_format = format_text
        else:
            ydl_format = f"{format_text}+bestaudio[ext=m4a]/bestaudio/best"
        postprocessors = []

    def hook(data):
        if cancellation_requested(cancel_callback):
            raise CancelledError("Operation canceled")
        if not progress_callback:
            return
        status = data.get("status")
        filename = data.get("filename") or url
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            downloaded = data.get("downloaded_bytes") or 0
            percent = int((downloaded / total) * 100) if total else 0
            progress_callback(0, 1, Path(filename), max(0, min(99, percent)))
        elif status == "finished":
            progress_callback(1, 1, Path(filename), 0)

    options = {
        "format": ydl_format,
        "outtmpl": str(output_dir / "%(title).200B [%(id)s].%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "progress_hooks": [hook],
        "postprocessors": postprocessors,
        "merge_output_format": "mp4",
        "check_formats": True,
        "continuedl": True,
        "concurrent_fragment_downloads": 16,
        "fragment_retries": 10,
        "retries": 10,
        "socket_timeout": 30,
        "http_chunk_size": 25 * 1024 * 1024,
        "windowsfilenames": True,
        "noplaylist": True,
    }
    ffmpeg_location = youtube_ffmpeg_location()
    if ffmpeg_location:
        options["ffmpeg_location"] = ffmpeg_location

    print(f"YouTube URL: {url}")
    print(f"Output folder: {output_dir}")
    print("Downloading audio as MP3" if format_id == YOUTUBE_AUDIO_FORMAT_ID else f"Downloading format: {format_id}")
    try:
        with ydl_module.YoutubeDL(options) as downloader:
            result = downloader.extract_info(url, download=True)
    except Exception as exc:
        can_retry_video = format_id not in (YOUTUBE_AUDIO_FORMAT_ID, YOUTUBE_BEST_VIDEO_FORMAT_ID)
        if not can_retry_video or cancellation_requested(cancel_callback):
            raise
        print(f"Selected format failed: {exc}")
        print("Retrying with best compatible MP4 format...")
        retry_options = dict(options)
        retry_options["format"] = YOUTUBE_BEST_VIDEO_FORMAT
        retry_options["postprocessors"] = []
        with ydl_module.YoutubeDL(retry_options) as downloader:
            result = downloader.extract_info(url, download=True)

    if progress_callback:
        progress_callback(1, 1, Path(result.get("title") or "YouTube"), 0)
    print("YouTube download done")
    return result


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".gif": "image/gif",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def safe_get(url, params=None):
    response = requests.get(url, params=params, headers=HEADERS, timeout=20)
    response.raise_for_status()
    return response


def get_image_ext(url):
    suffix = Path(urlparse(url).path.lower()).suffix
    return suffix if suffix in IMAGE_EXTS else ".jpg"


def detect_image_ext(image_data):
    if image_data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if image_data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if image_data.startswith(b"RIFF") and image_data[8:12] == b"WEBP":
        return ".webp"
    if image_data.startswith(b"BM"):
        return ".bmp"
    if image_data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    return None


def load_cover_file(cover_path):
    cover_path = Path(cover_path)
    image_data = cover_path.read_bytes()
    cover_ext = detect_image_ext(image_data) or cover_path.suffix.lower()

    if cover_ext not in {".jpg", ".jpeg", ".png"}:
        image = Image.open(BytesIO(image_data)).convert("RGB")
        output = BytesIO()
        image.save(output, format="JPEG", quality=92)
        return output.getvalue(), ".jpg"

    return image_data, cover_ext


def download_image(url):
    response = safe_get(url)
    content_type = response.headers.get("Content-Type", "").lower()

    if response.content and ("image/" in content_type or url.lower().endswith(tuple(IMAGE_EXTS))):
        return response.content, detect_image_ext(response.content) or get_image_ext(url)

    return None


def extract_image_urls(html_text):
    image_urls = []
    patterns = [
        r'imgurl":"([^"]+)',
        r'murl":"([^"]+)',
        r'"thumbnailUrl":"([^"]+)',
        r'https?://[^\s"\']+\.(?:jpe?g|png|webp|bmp|gif)(?:\?[^\s"\']*)?',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, html_text, flags=re.IGNORECASE):
            value = match.group(1) if match.groups() else match.group(0)
            if value.startswith("http"):
                image_urls.append(value.replace("\\u0026", "&").replace("\\/", "/"))

    seen = set()
    cleaned = []
    for image_url in image_urls:
        if image_url not in seen:
            seen.add(image_url)
            cleaned.append(image_url)

    return cleaned


def find_cover_from_itunes(song_name):
    result = safe_get(
        "https://itunes.apple.com/search",
        params={"term": song_name, "media": "music", "entity": "song", "limit": 1},
    ).json()

    if not result.get("resultCount"):
        return None

    item = result["results"][0]
    artwork = item["artworkUrl100"].replace("100x100", "1000x1000")
    image = download_image(artwork)
    if not image:
        return None

    return image[0], image[1], item.get("trackName"), item.get("artistName")


def find_cover_from_youtube(song_name):
    search_terms = [
        f"{song_name} official music video",
        f"{song_name} official song",
        song_name,
    ]

    video_ids = []
    seen = set()
    for search_term in search_terms:
        query = quote(search_term)
        page = safe_get(f"https://www.youtube.com/results?search_query={query}")

        for video_id in re.findall(r'"videoId":"([^"]+)"', page.text):
            if video_id in seen:
                continue
            seen.add(video_id)
            video_ids.append(video_id)

        if video_ids:
            break

    if not video_ids:
        return None

    for video_id in video_ids[:5]:
        for quality in ("maxresdefault", "sddefault", "hqdefault", "mqdefault"):
            image_url = f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
            try:
                image = download_image(image_url)
            except requests.RequestException:
                continue
            if image:
                return image[0], image[1], None, None

    return None


def find_cover_from_bing(song_name):
    query = quote(f"{song_name} album cover")
    page = safe_get(f"https://www.bing.com/images/search?q={query}")

    for image_url in extract_image_urls(page.text):
        image = download_image(image_url)
        if image:
            return image[0], image[1], None, None

    return None


def find_web_cover(song_name):
    sources = [
        ("YouTube", lambda: find_cover_from_youtube(song_name)),
        ("iTunes", lambda: find_cover_from_itunes(song_name)),
        ("Bing", lambda: find_cover_from_bing(song_name)),
    ]

    for source_name, source_func in sources:
        try:
            result = source_func()
            if result:
                print(f"Found cover from {source_name}")
                return result
        except Exception as exc:
            print(f"{source_name} search failed: {exc}")

    return None


def normalize_output_ext(output_ext):
    output_ext = (output_ext or ".mp3").strip().lower()
    if not output_ext.startswith("."):
        output_ext = f".{output_ext}"
    if output_ext not in OUTPUT_FORMATS:
        supported = ", ".join(sorted(OUTPUT_FORMATS))
        raise ValueError(f"Unsupported output extension: {output_ext}. Supported: {supported}")
    return output_ext


def normalize_quality(quality):
    quality = (quality or "192k").strip().lower()
    if quality not in QUALITY_OPTIONS:
        supported = ", ".join(QUALITY_OPTIONS)
        raise ValueError(f"Unsupported quality: {quality}. Supported: {supported}")
    return quality


def normalize_enhancement(enhancement):
    enhancement = (enhancement or "Off").strip()
    if enhancement not in ENHANCEMENT_PRESETS:
        supported = ", ".join(ENHANCEMENT_PRESETS)
        raise ValueError(f"Unsupported enhancement: {enhancement}. Supported: {supported}")
    return enhancement


def normalize_video_compression(compression):
    compression = (compression or "Original").strip()
    if compression not in VIDEO_COMPRESSION_PRESETS:
        supported = ", ".join(VIDEO_COMPRESSION_PRESETS)
        raise ValueError(f"Unsupported video compression: {compression}. Supported: {supported}")
    return compression


def normalize_video_resolution(resolution):
    resolution = (resolution or "Original").strip()
    if resolution not in VIDEO_RESOLUTION_PRESETS:
        supported = ", ".join(VIDEO_RESOLUTION_PRESETS)
        raise ValueError(f"Unsupported video resolution: {resolution}. Supported: {supported}")
    return resolution


def normalize_video_output_ext(video_output_ext):
    if not video_output_ext:
        return ".mp4"
    video_output_ext = str(video_output_ext).strip().lower()
    if video_output_ext in {"original", "keep", "keep_original"}:
        return "original"
    if not video_output_ext.startswith("."):
        video_output_ext = f".{video_output_ext}"
    if video_output_ext not in VIDEO_OUTPUT_FORMATS:
        supported = ", ".join(sorted(VIDEO_OUTPUT_FORMATS))
        raise ValueError(f"Unsupported video output extension: {video_output_ext}. Supported: {supported}")
    return video_output_ext


def ffmpeg_video_args_for(target_ext, compression_preset):
    info = VIDEO_OUTPUT_FORMATS.get(target_ext) or VIDEO_OUTPUT_FORMATS[".mp4"]
    rate_control = info.get("rate_control", "crf")
    video_args = ["-c:v", info["video_codec"]]
    if rate_control == "crf":
        video_args.extend(["-preset", "medium", "-crf", str(compression_preset["crf"]), "-pix_fmt", "yuv420p"])
    elif rate_control == "vp9":
        video_args.extend(["-b:v", "0", "-crf", str(compression_preset.get("crf_vp9", 33)), "-pix_fmt", "yuv420p"])
    elif rate_control == "qscale":
        video_args.extend(["-qscale:v", str(compression_preset.get("qscale", 6))])
        if info["video_codec"] == "mpeg4":
            video_args.extend(["-pix_fmt", "yuv420p"])

    audio_bitrate = str(compression_preset["audio_bitrate"])
    if info["audio_codec"] == "libopus":
        try:
            if int(audio_bitrate.rstrip("k")) > 192:
                audio_bitrate = "192k"
        except ValueError:
            audio_bitrate = "192k"
    elif info["audio_codec"] == "wmav2":
        try:
            if int(audio_bitrate.rstrip("k")) > 192:
                audio_bitrate = "192k"
        except ValueError:
            audio_bitrate = "192k"

    audio_args = ["-c:a", info["audio_codec"], "-b:a", audio_bitrate]
    extra = list(info.get("container_args", []))
    return [*video_args, *audio_args, *extra]


def ffmpeg_filter_args(enhancement):
    filters = ENHANCEMENT_PRESETS[normalize_enhancement(enhancement)]
    if not filters:
        return []
    return ["-af", ",".join(filters)]


def ffmpeg_audio_filter_str(enhancement):
    filters = ENHANCEMENT_PRESETS[normalize_enhancement(enhancement)]
    return ",".join(filters) if filters else None


def cancellation_requested(cancel_callback):
    return bool(cancel_callback and cancel_callback())


_ACTIVE_SUBPROCESSES = set()
_ACTIVE_SUBPROCESSES_LOCK = threading.Lock()


def register_active_process(proc):
    if proc:
        with _ACTIVE_SUBPROCESSES_LOCK:
            _ACTIVE_SUBPROCESSES.add(proc)


def unregister_active_process(proc):
    if proc:
        with _ACTIVE_SUBPROCESSES_LOCK:
            _ACTIVE_SUBPROCESSES.discard(proc)


def stop_all_active_processes():
    with _ACTIVE_SUBPROCESSES_LOCK:
        procs = list(_ACTIVE_SUBPROCESSES)
        _ACTIVE_SUBPROCESSES.clear()
    for proc in procs:
        try:
            stop_process(proc)
        except Exception:
            pass


register_process = register_active_process
unregister_process = unregister_active_process
stop_all_processes = stop_all_active_processes


def stop_process(process):
    if not process or process.poll() is not None:
        return
    try:
        process.terminate()
    except Exception:
        pass
    try:
        process.wait(timeout=1.0)
    except (subprocess.TimeoutExpired, Exception):
        try:
            process.kill()
            process.wait(timeout=1.0)
        except Exception:
            pass


def remove_partial_output(output_path):
    try:
        Path(output_path).unlink(missing_ok=True)
    except OSError:
        pass


def parse_duration_seconds(text):
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def parse_time_seconds(value):
    value = str(value or "").strip()
    if not value:
        raise ValueError("Time value is required")
    if re.fullmatch(r"\d+(?:\.\d+)?", value):
        return float(value)

    parts = value.split(":")
    if not 2 <= len(parts) <= 3:
        raise ValueError("Use seconds, MM:SS, or HH:MM:SS")
    try:
        numbers = [float(part) for part in parts]
    except ValueError as exc:
        raise ValueError("Invalid time value") from exc

    if len(numbers) == 2:
        minutes, seconds = numbers
        return minutes * 60 + seconds

    hours, minutes, seconds = numbers
    return hours * 3600 + minutes * 60 + seconds


def format_time_label(seconds):
    seconds = max(0, int(seconds))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}-{minutes:02d}-{seconds:02d}"


def unique_output_path(path):
    path = Path(path)
    if not path.exists():
        return path
    for index in range(1, 1000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"Could not create a unique output name for {path}")


def same_file_path(first, second):
    try:
        return Path(first).resolve() == Path(second).resolve()
    except OSError:
        return False


def temp_output_path(final_path):
    final_path = Path(final_path)
    return unique_output_path(final_path.with_name(f".{final_path.stem}.{os.getpid()}.part{final_path.suffix}"))


def validated_media_output(output_path):
    output_path = Path(output_path)
    if not output_path.exists() or output_path.stat().st_size <= 0:
        return False
    try:
        result = subprocess.run(
            [
                str(ffprobe_executable()),
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nokey=1:noprint_wrappers=1",
                str(output_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            **hidden_subprocess_kwargs(),
        )
        return result.returncode == 0
    except FileNotFoundError:
        return True


def finalize_output(temp_path, final_path):
    temp_path = Path(temp_path)
    final_path = Path(final_path)
    if not validated_media_output(temp_path):
        remove_partial_output(temp_path)
        raise RuntimeError(f"Output file is not a valid media file: {final_path.name}")
    final_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        temp_path.replace(final_path)
        return final_path
    except (PermissionError, OSError):
        # Target file might be locked by another process (e.g. VLC player, Windows Explorer preview)
        # Wait briefly and retry, otherwise write to a new unique filename
        time.sleep(0.3)
        try:
            temp_path.replace(final_path)
            return final_path
        except (PermissionError, OSError):
            alt_path = unique_output_path(final_path)
            try:
                temp_path.replace(alt_path)
                return alt_path
            except Exception:
                shutil.copy2(temp_path, alt_path)
                remove_partial_output(temp_path)
                return alt_path


def attach_midpoint_poster(video_path, source_path=None, timestamp=None):
    video_path = Path(video_path)
    if video_path.suffix.lower() != ".mp4" or not video_path.exists():
        return video_path

    poster_source = Path(source_path) if source_path else video_path
    if timestamp is None:
        duration = get_media_duration(poster_source) or get_media_duration(video_path) or 0
        timestamp = duration / 2 if duration else 0
    timestamp = max(0, float(timestamp or 0))

    poster_path = temp_output_path(video_path.with_suffix(".jpg"))
    remux_path = temp_output_path(video_path)
    try:
        extract = subprocess.run(
            [
                str(ffmpeg_executable()),
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                str(timestamp),
                "-i",
                str(poster_source),
                "-frames:v",
                "1",
                "-q:v",
                "2",
                str(poster_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            **hidden_subprocess_kwargs(),
        )
        if extract.returncode != 0 or not poster_path.exists():
            return video_path

        remux = subprocess.run(
            [
                str(ffmpeg_executable()),
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(video_path),
                "-i",
                str(poster_path),
                "-map",
                "0",
                "-map",
                "1",
                "-c",
                "copy",
                "-disposition:v:1",
                "attached_pic",
                str(remux_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            **hidden_subprocess_kwargs(),
        )
        if remux.returncode == 0 and validated_media_output(remux_path):
            remux_path.replace(video_path)
    finally:
        remove_partial_output(poster_path)
        remove_partial_output(remux_path)

    return video_path


def get_media_duration(source_path):
    result = subprocess.run(
        [
            str(ffmpeg_executable()),
            "-hide_banner",
            "-i",
            str(source_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        **hidden_subprocess_kwargs(),
    )
    return parse_duration_seconds(result.stderr or result.stdout or "")


def ffmpeg_args_for(output_ext, quality):
    quality = normalize_quality(quality)
    return [
        quality if arg == "{quality}" else arg
        for arg in OUTPUT_FORMATS[output_ext]["args"]
    ]


def add_cover_to_mp3(audio_path, cover_data, cover_ext, track_name=None, artist_name=None):
    detected_ext = detect_image_ext(cover_data)
    if detected_ext:
        cover_ext = detected_ext

    audio = MP3(audio_path, ID3=ID3)
    if audio.tags is None:
        audio.add_tags()

    for key in list(audio.tags.keys()):
        if key.startswith("APIC"):
            del audio.tags[key]

    audio.tags.add(
        APIC(
            encoding=3,
            mime=MIME_TYPES.get(cover_ext, "image/jpeg"),
            type=3,
            desc="Cover",
            data=cover_data,
        )
    )

    if track_name:
        audio.tags.setall("TIT2", [TIT2(encoding=3, text=track_name)])

    if artist_name:
        audio.tags.setall("TPE1", [TPE1(encoding=3, text=artist_name)])

    audio.save(v2_version=3)

    verify = MP3(audio_path, ID3=ID3)
    return bool(verify.tags and any(key.startswith("APIC") for key in verify.tags.keys()))


def add_cover_to_mp4(audio_path, cover_data, cover_ext, track_name=None, artist_name=None):
    detected_ext = detect_image_ext(cover_data) or cover_ext
    if detected_ext == ".png":
        image_format = MP4Cover.FORMAT_PNG
    else:
        image_format = MP4Cover.FORMAT_JPEG

    audio = MP4(audio_path)
    audio["covr"] = [MP4Cover(cover_data, imageformat=image_format)]

    if track_name:
        audio["\xa9nam"] = [track_name]
    if artist_name:
        audio["\xa9ART"] = [artist_name]

    audio.save()

    verify = MP4(audio_path)
    return bool(verify.tags and verify.tags.get("covr"))


def add_cover_to_flac(audio_path, cover_data, cover_ext, track_name=None, artist_name=None):
    detected_ext = detect_image_ext(cover_data) or cover_ext
    picture = Picture()
    picture.type = 3
    picture.mime = MIME_TYPES.get(detected_ext, "image/jpeg")
    picture.desc = "Cover"
    picture.data = cover_data

    audio = FLAC(audio_path)
    audio.clear_pictures()
    audio.add_picture(picture)

    if track_name:
        audio["title"] = track_name
    if artist_name:
        audio["artist"] = artist_name

    audio.save()

    verify = FLAC(audio_path)
    return bool(verify.pictures)


def add_cover_to_audio(audio_path, cover_data, cover_ext, track_name=None, artist_name=None):
    suffix = audio_path.suffix.lower()
    if suffix == ".mp3":
        return add_cover_to_mp3(audio_path, cover_data, cover_ext, track_name, artist_name)
    if suffix == ".m4a":
        return add_cover_to_mp4(audio_path, cover_data, cover_ext, track_name, artist_name)
    if suffix == ".flac":
        return add_cover_to_flac(audio_path, cover_data, cover_ext, track_name, artist_name)

    print(f"Cover embedding is not supported for {suffix} output")
    return False


def embed_cover_into_file(audio_path, image_path, track_name=None, artist_name=None):
    """Embeds cover art from image_path into audio_path (mp3, m4a, flac)."""
    cover_data, cover_ext = load_cover_file(image_path)
    return add_cover_to_audio(Path(audio_path), cover_data, cover_ext, track_name=track_name, artist_name=artist_name)


def audio_has_cover(audio_path):
    try:
        suffix = audio_path.suffix.lower()
        if suffix == ".m4a":
            audio = MP4(audio_path)
            return bool(audio.tags and audio.tags.get("covr"))
        if suffix == ".flac":
            audio = FLAC(audio_path)
            return bool(audio.pictures)
        if suffix != ".mp3":
            return False

        audio = MP3(audio_path, ID3=ID3)
        if not audio.tags:
            return False

        fixed_cover = False
        for key in list(audio.tags.keys()):
            if not key.startswith("APIC"):
                continue

            frame = audio.tags[key]
            detected_ext = detect_image_ext(frame.data)
            expected_mime = MIME_TYPES.get(detected_ext)
            if not expected_mime:
                continue

            if frame.mime != expected_mime:
                print(f"Fixing cover type: {audio_path.name}")
                frame.mime = expected_mime
                fixed_cover = True

        if fixed_cover:
            audio.save(v2_version=3)

        return any(key.startswith("APIC") for key in audio.tags.keys())
    except Exception as exc:
        print(f"Could not read audio tags: {audio_path} ({exc})")
        return False


def add_missing_cover(
    audio_path,
    force_refresh=False,
    search_text=None,
    preview_callback=None,
    custom_cover_path=None,
):
    if not force_refresh and audio_has_cover(audio_path):
        print(f"Cover already exists: {audio_path.name}")
        return None, None

    if custom_cover_path:
        print(f"Using custom cover: {custom_cover_path}")
        cover_data, cover_ext = load_cover_file(custom_cover_path)
        if preview_callback and not preview_callback(audio_path, cover_data, cover_ext, "Custom cover"):
            print("Cover skipped by user")
            return None, None

        if add_cover_to_audio(audio_path, cover_data, cover_ext):
            print("Cover Added")
            return None, None

        print("Cover write failed")
        return None, None

    search_name = (search_text or "").strip() or audio_path.stem
    print(f"Searching cover for {search_name}")
    cover = find_web_cover(search_name)

    if not cover:
        print("No Cover Found")
        return None, None

    cover_data, cover_ext, track_name, artist_name = cover
    if preview_callback and not preview_callback(audio_path, cover_data, cover_ext, search_name):
        print("Cover skipped by user")
        return None, None

    if add_cover_to_audio(audio_path, cover_data, cover_ext, track_name, artist_name):
        print("Cover Added")
        return track_name, artist_name

    print("Cover write failed")
    return None, None


def output_path_for(source_path, input_dir=INPUT_DIR, output_dir=OUTPUT_DIR, suffix=None):
    source_path = Path(source_path)
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    try:
        relative_path = source_path.resolve().relative_to(input_dir.resolve())
    except ValueError:
        relative_path = Path(source_path.name)

    if suffix:
        relative_path = relative_path.with_suffix(suffix)

    output_path = output_dir / relative_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def trim_media(
    source_path,
    start_time,
    end_time,
    input_dir=None,
    output_dir=None,
    output_ext=None,
    quality="192k",
    keep_original_format=True,
    enhancement="Off",
    aspect_ratio="original",
    fit_mode="crop",
    video_transform=None,
    media_overlays=None,
    logo_items=None,
    color_config=None,
    transitions_config=None,
    logo_config=None,
    title_config=None,
    subtitle_config=None,
    silence_config=None,
    video_quality="High",
    progress_callback=None,
    cancel_callback=None,
):
    source_path = Path(source_path)
    if cancellation_requested(cancel_callback):
        raise CancelledError("Operation canceled")
    if source_path.suffix.lower() not in MEDIA_EXTS:
        raise ValueError(f"Unsupported media file: {source_path}")

    start_seconds = parse_time_seconds(start_time)
    end_seconds = parse_time_seconds(end_time)
    if end_seconds <= start_seconds:
        raise ValueError("End time must be after start time")

    input_root = Path(input_dir) if input_dir else source_path.parent
    output_dir = Path(output_dir) if output_dir else input_root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    source_ext = source_path.suffix.lower()
    if keep_original_format:
        target_ext = source_ext
    else:
        target_ext = normalize_output_ext(output_ext)

    base_output = output_path_for(source_path, input_root, output_dir, target_ext)
    trim_name = (
        f"{base_output.stem}_trim_"
        f"{format_time_label(start_seconds)}_to_{format_time_label(end_seconds)}"
        f"{base_output.suffix}"
    )
    output_path = unique_output_path(base_output.with_name(trim_name))
    trim_duration = end_seconds - start_seconds

    vt = video_transform or {}
    has_vt = (
        abs(float(vt.get("zoom", 1.0) or 1.0) - 1.0) > 0.005
        or abs(float(vt.get("pan_x", 0.0) or 0.0)) > 0.002
        or abs(float(vt.get("pan_y", 0.0) or 0.0)) > 0.002
        or bool(vt.get("flip_h", False))
    )

    # If user requested aspect ratio changes (e.g. 9:16 Reels), pan/zoom, color grading, icons/images, logo, title, subtitles, or silence removal:
    if keep_original_format and has_video_stream(source_path):
        is_styled = bool(
            (aspect_ratio and aspect_ratio != "original")
            or has_vt
            or bool(media_overlays)
            or bool(logo_items)
            or (color_config and color_config.get("enabled"))
            or (transitions_config and transitions_config.get("enabled"))
            or (logo_config and logo_config.get("enabled"))
            or (title_config and (title_config.get("enabled") or bool(title_config.get("text_items"))))
            or (subtitle_config and subtitle_config.get("enabled"))
            or (silence_config and silence_config.get("enabled"))
        )
        if is_styled:
            def _styled_prog(pct, cur, tot):
                if progress_callback:
                    progress_callback(0, 1, source_path, pct)

            return export_styled_video(
                video_path=source_path,
                output_path=output_path,
                start_seconds=start_seconds,
                duration_seconds=trim_duration,
                aspect_ratio=aspect_ratio,
                fit_mode=fit_mode,
                video_transform=video_transform,
                media_overlays=media_overlays,
                logo_items=logo_items,
                color_config=color_config,
                transitions_config=transitions_config,
                logo_config=logo_config,
                title_config=title_config,
                subtitle_config=subtitle_config,
                silence_config=silence_config,
                audio_enhancement_filter=ffmpeg_audio_filter_str(enhancement),
                video_quality=video_quality,
                ffmpeg_exe=str(ffmpeg_executable()),
                cancel_callback=cancel_callback,
                progress_callback=_styled_prog,
            )

    action = "Trimming" if keep_original_format else "Trimming and extracting audio"
    print(f"{action} {source_path.name} -> {output_path.name}")
    command = [
        str(ffmpeg_executable()),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-progress",
        "pipe:1",
        "-nostats",
        "-ss",
        str(start_seconds),
        "-to",
        str(end_seconds),
        "-i",
        str(source_path),
    ]
    if keep_original_format:
        command.extend([
            "-map",
            "0:v?",
            "-map",
            "0:a?",
            "-map",
            "0:s?",
            "-dn",
            "-c",
            "copy",
            "-avoid_negative_ts",
            "make_zero",
        ])
    else:
        command.extend([
            "-vn",
            *ffmpeg_filter_args(enhancement),
            *ffmpeg_args_for(target_ext, quality),
        ])
    command.append(str(output_path))
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        **hidden_subprocess_kwargs(),
    )

    last_percent = -1
    for line in process.stdout:
        if cancellation_requested(cancel_callback):
            stop_process(process)
            remove_partial_output(output_path)
            raise CancelledError("Operation canceled")
        key, separator, value = line.strip().partition("=")
        if separator != "=" or key != "out_time_ms":
            continue
        try:
            elapsed = int(value) / 1_000_000
        except ValueError:
            continue
        percent = max(0, min(99, int((elapsed / trim_duration) * 100)))
        if progress_callback and percent != last_percent:
            last_percent = percent
            progress_callback(0, 1, source_path, percent)

    if cancellation_requested(cancel_callback):
        stop_process(process)
        remove_partial_output(output_path)
        raise CancelledError("Operation canceled")

    stderr = process.stderr.read() if process.stderr else ""
    return_code = process.wait()

    if progress_callback:
        progress_callback(1, 1, source_path, 0)

    if return_code != 0:
        if stderr:
            print(stderr.strip())
        print(f"Trim failed: {source_path}")
        return None

    if output_path.suffix.lower() == ".mp4":
        attach_midpoint_poster(output_path, source_path, start_seconds + (trim_duration / 2))

    return output_path


def convert_audio(
    source_path,
    output_ext,
    input_dir=INPUT_DIR,
    output_dir=OUTPUT_DIR,
    quality="192k",
    skip_if_exists=False,
    enhancement="Off",
    progress_callback=None,
    progress_index=0,
    total_files=1,
    cancel_callback=None,
):
    if cancellation_requested(cancel_callback):
        raise CancelledError("Operation canceled")
    output_path = output_path_for(source_path, input_dir, output_dir, output_ext)
    if same_file_path(source_path, output_path):
        output_path = unique_output_path(output_path.with_name(f"{output_path.stem}_converted{output_path.suffix}"))

    if skip_if_exists and output_path.exists():
        print(f"Skipping existing file: {output_path.name}")
        if progress_callback:
            progress_callback(progress_index + 1, total_files, source_path, 0)
        return None

    if source_path.suffix.lower() == output_ext and enhancement == "Off":
        print(f"Copying {source_path.name}")
        shutil.copy2(source_path, output_path)
        if progress_callback:
            progress_callback(progress_index + 1, total_files, source_path, 0)
        return output_path

    source_kind = "video" if source_path.suffix.lower() in VIDEO_EXTS else "audio"
    print(f"Converting {source_kind}: {source_path.name} -> {output_path.name}")

    duration = get_media_duration(source_path)
    temp_path = temp_output_path(output_path)
    command = [
        str(ffmpeg_executable()),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-progress",
        "pipe:1",
        "-nostats",
        "-i",
        str(source_path),
        "-vn",
        *ffmpeg_filter_args(enhancement),
        *ffmpeg_args_for(output_ext, quality),
        str(temp_path),
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        **hidden_subprocess_kwargs(),
    )

    last_percent = -1
    for line in process.stdout:
        if cancellation_requested(cancel_callback):
            stop_process(process)
            remove_partial_output(temp_path)
            raise CancelledError("Operation canceled")
        key, separator, value = line.strip().partition("=")
        if separator != "=" or key != "out_time_ms" or not duration:
            continue
        try:
            elapsed = int(value) / 1_000_000
        except ValueError:
            continue
        percent = max(0, min(99, int((elapsed / duration) * 100)))
        if progress_callback and percent != last_percent:
            last_percent = percent
            progress_callback(progress_index, total_files, source_path, percent)

    if cancellation_requested(cancel_callback):
        stop_process(process)
        remove_partial_output(temp_path)
        raise CancelledError("Operation canceled")

    stderr = process.stderr.read() if process.stderr else ""
    return_code = process.wait()

    if progress_callback:
        progress_callback(progress_index + 1, total_files, source_path, 0)

    if return_code != 0:
        if stderr:
            print(stderr.strip())
        print(f"Conversion failed: {source_path}")
        remove_partial_output(temp_path)
        return None

    try:
        final_path = finalize_output(temp_path, output_path)
        return attach_midpoint_poster(final_path, source_path)
    except RuntimeError as exc:
        print(exc)
        return None


def convert_video(
    source_path,
    target_ext=".mp4",
    input_dir=INPUT_DIR,
    output_dir=OUTPUT_DIR,
    compression="Original",
    resolution="Original",
    skip_if_exists=False,
    progress_callback=None,
    progress_index=0,
    total_files=1,
    cancel_callback=None,
):
    if cancellation_requested(cancel_callback):
        raise CancelledError("Operation canceled")
    source_path = Path(source_path)
    compression = normalize_video_compression(compression)
    resolution = normalize_video_resolution(resolution)
    preset = VIDEO_COMPRESSION_PRESETS[compression]
    resolution_preset = VIDEO_RESOLUTION_PRESETS[resolution]

    normalized_target_ext = normalize_video_output_ext(target_ext)
    actual_ext = source_path.suffix.lower() if normalized_target_ext == "original" else normalized_target_ext
    if actual_ext not in VIDEO_OUTPUT_FORMATS:
        actual_ext = ".mp4"

    output_path = output_path_for(source_path, input_dir, output_dir, actual_ext)
    if same_file_path(source_path, output_path):
        output_path = unique_output_path(output_path.with_name(f"{output_path.stem}_converted{output_path.suffix}"))

    if skip_if_exists and output_path.exists():
        print(f"Skipping existing file: {output_path.name}")
        if progress_callback:
            progress_callback(progress_index + 1, total_files, source_path, 0)
        return None

    format_label = VIDEO_OUTPUT_FORMATS.get(actual_ext, {}).get("label", actual_ext.upper().lstrip("."))
    print(f"Converting video to {format_label} ({preset['label']}, {resolution_preset['label']}): {source_path.name} -> {output_path.name}")

    duration = get_media_duration(source_path)
    temp_path = temp_output_path(output_path)

    def _execute_ffmpeg(cmd):
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            **hidden_subprocess_kwargs(),
        )
        last_percent = -1
        for line in process.stdout:
            if cancellation_requested(cancel_callback):
                stop_process(process)
                remove_partial_output(temp_path)
                raise CancelledError("Operation canceled")
            key, separator, value = line.strip().partition("=")
            if separator != "=" or key != "out_time_ms" or not duration:
                continue
            try:
                elapsed = int(value) / 1_000_000
            except ValueError:
                continue
            percent = max(0, min(99, int((elapsed / duration) * 100)))
            if progress_callback and percent != last_percent:
                last_percent = percent
                progress_callback(progress_index, total_files, source_path, percent)

        if cancellation_requested(cancel_callback):
            stop_process(process)
            remove_partial_output(temp_path)
            raise CancelledError("Operation canceled")

        stderr = process.stderr.read() if process.stderr else ""
        return_code = process.wait()
        return return_code, stderr

    used_stream_copy = False
    return_code = 0
    stderr = ""

    if compression == "Original" and not resolution_preset["scale"]:
        info = VIDEO_OUTPUT_FORMATS.get(actual_ext) or VIDEO_OUTPUT_FORMATS[".mp4"]
        extra = list(info.get("container_args", []))
        copy_command = [
            str(ffmpeg_executable()),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            "-nostats",
            "-i",
            str(source_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c",
            "copy",
            *extra,
            str(temp_path),
        ]
        return_code, stderr = _execute_ffmpeg(copy_command)
        if return_code == 0 and validated_media_output(temp_path):
            used_stream_copy = True
        else:
            remove_partial_output(temp_path)

    if not used_stream_copy:
        command = [
            str(ffmpeg_executable()),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            "-nostats",
            "-i",
            str(source_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
        ]
        if resolution_preset["scale"]:
            command.extend(["-vf", f"scale={resolution_preset['scale']}:force_original_aspect_ratio=decrease:force_divisible_by=2"])

        command.extend(ffmpeg_video_args_for(actual_ext, preset))
        command.append(str(temp_path))
        return_code, stderr = _execute_ffmpeg(command)

    if progress_callback:
        progress_callback(progress_index + 1, total_files, source_path, 0)

    if return_code != 0:
        if stderr:
            print(stderr.strip())
        print(f"Video conversion failed: {source_path}")
        remove_partial_output(temp_path)
        return None

    try:
        final_path = finalize_output(temp_path, output_path)
        if final_path.suffix.lower() == ".mp4":
            return attach_midpoint_poster(final_path, source_path)
        return final_path
    except RuntimeError as exc:
        print(exc)
        return None


def compress_video(
    source_path,
    input_dir=INPUT_DIR,
    output_dir=OUTPUT_DIR,
    compression="Original",
    resolution="Original",
    skip_if_exists=False,
    progress_callback=None,
    progress_index=0,
    total_files=1,
    cancel_callback=None,
    target_ext=".mp4",
    **kwargs,
):
    if "output_ext" in kwargs:
        target_ext = kwargs.pop("output_ext")
    if "preset" in kwargs:
        compression = kwargs.pop("preset")
    if "cancel_check" in kwargs and cancel_callback is None:
        cancel_callback = kwargs.pop("cancel_check")

    return convert_video(
        source_path=source_path,
        target_ext=target_ext,
        input_dir=input_dir,
        output_dir=output_dir,
        compression=compression,
        resolution=resolution,
        skip_if_exists=skip_if_exists,
        progress_callback=progress_callback,
        progress_index=progress_index,
        total_files=total_files,
        cancel_callback=cancel_callback,
    )


def iter_input_media(input_dir=INPUT_DIR, exclude_dir=None):
    exclude_dir = Path(exclude_dir).resolve() if exclude_dir else None
    for source_path in input_dir.rglob("*"):
        if exclude_dir and source_path.resolve().is_relative_to(exclude_dir):
            continue
        if source_path.is_file() and source_path.suffix.lower() in MEDIA_EXTS:
            yield source_path


def collect_media_files(input_path=INPUT_DIR, exclude_dir=None):
    input_path = Path(input_path)
    if input_path.is_file():
        return [input_path] if input_path.suffix.lower() in MEDIA_EXTS else []
    if input_path.is_dir():
        return list(iter_input_media(input_path, exclude_dir))
    return []


def collect_audio_files(input_path=INPUT_DIR, exclude_dir=None):
    return collect_media_files(input_path, exclude_dir)


def input_root_for(input_path):
    input_path = Path(input_path)
    return input_path.parent if input_path.is_file() else input_path


def main(
    output_ext=".mp3",
    input_dir=None,
    output_dir=None,
    skip_if_exists=False,
    keep_original_format=False,
    quality="192k",
    search_text=None,
    preview_callback=None,
    progress_callback=None,
    custom_cover_path=None,
    enhancement="Off",
    video_action="extract_audio",
    video_compression="Original",
    video_resolution="Original",
    video_output_ext=".mp4",
    video_only=False,
    cancel_callback=None,
):
    output_ext = normalize_output_ext(output_ext)
    quality = normalize_quality(quality)
    enhancement = normalize_enhancement(enhancement)
    video_compression = normalize_video_compression(video_compression)
    video_resolution = normalize_video_resolution(video_resolution)
    video_output_ext = normalize_video_output_ext(video_output_ext)
    input_path = Path(input_dir) if input_dir else INPUT_DIR
    input_root = input_root_for(input_path)
    output_dir = Path(output_dir) if output_dir else input_root / "output"
    if input_path.is_dir():
        input_path.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    if video_action in ("convert_video", "compress_video"):
        v_ext_label = "Keep original" if video_output_ext == "original" else VIDEO_OUTPUT_FORMATS.get(video_output_ext, {}).get("label", video_output_ext)
        print(f"Video target format: {v_ext_label}")
        print(f"Video quality: {VIDEO_COMPRESSION_PRESETS[video_compression]['label']}")
        print(f"Video resolution: {VIDEO_RESOLUTION_PRESETS[video_resolution]['label']}")
    elif keep_original_format:
        print("Output format: keep original")
        print("Video inputs will still be extracted to the selected audio format")
    else:
        print(f"Output format: {OUTPUT_FORMATS[output_ext]['label']} ({output_ext})")
        if output_ext in {".mp3", ".m4a"}:
            print(f"Quality: {quality}")
    print(f"Input: {input_path}")
    print(f"Output folder: {output_dir}")
    if enhancement != "Off":
        print(f"Audio enhancement: {enhancement}")
    media_files = collect_media_files(input_path, output_dir)
    if video_only:
        media_files = [path for path in media_files if path.suffix.lower() in VIDEO_EXTS]
    if not media_files:
        print("No supported audio or video files found")
        return

    total = len(media_files)
    if progress_callback:
        progress_callback(0, total, None, 0)

    for index, source_path in enumerate(media_files, start=1):
        if cancellation_requested(cancel_callback):
            raise CancelledError("Operation canceled")
        completed_before_file = index - 1
        if progress_callback:
            progress_callback(completed_before_file, total, source_path, 0)

        is_video = source_path.suffix.lower() in VIDEO_EXTS
        if is_video and video_action in ("convert_video", "compress_video"):
            output_path = convert_video(
                source_path,
                target_ext=video_output_ext,
                input_dir=input_root,
                output_dir=output_dir,
                compression=video_compression,
                resolution=video_resolution,
                skip_if_exists=skip_if_exists,
                progress_callback=progress_callback,
                progress_index=completed_before_file,
                total_files=total,
                cancel_callback=cancel_callback,
            )
            if not output_path and progress_callback:
                progress_callback(index, total, source_path, 0)
            continue

        if video_only:
            if progress_callback:
                progress_callback(index, total, source_path, 0)
            continue

        current_ext = source_path.suffix.lower() if keep_original_format and not is_video else output_ext
        if current_ext not in OUTPUT_FORMATS:
            print(f"Skipping unsupported output format: {source_path.name}")
            if progress_callback:
                progress_callback(index, total, source_path, 0)
            continue

        output_path = convert_audio(
            source_path,
            current_ext,
            input_root,
            output_dir,
            quality=quality,
            skip_if_exists=skip_if_exists,
            enhancement=enhancement,
            progress_callback=progress_callback,
            progress_index=completed_before_file,
            total_files=total,
            cancel_callback=cancel_callback,
        )
        if not output_path:
            if progress_callback:
                progress_callback(index, total, source_path, 0)
            continue
        try:
            add_missing_cover(
                output_path,
                force_refresh=REFRESH_EXISTING_COVERS,
                search_text=search_text,
                preview_callback=preview_callback,
                custom_cover_path=custom_cover_path,
            )
        except Exception as exc:
            print(f"Cover error: {output_path} ({exc})")

        if progress_callback:
            progress_callback(index, total, source_path, 0)

    print("Done")


def format_timestamp_srt(seconds: float) -> str:
    total_ms = int(round(max(0.0, float(seconds)) * 1000))
    hours, remainder = divmod(total_ms, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    secs, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def format_timestamp_vtt(seconds: float) -> str:
    total_ms = int(round(max(0.0, float(seconds)) * 1000))
    hours, remainder = divmod(total_ms, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    secs, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def generate_srt_content(segments) -> str:
    lines = []
    for idx, seg in enumerate(segments, start=1):
        start_ts = format_timestamp_srt(seg["start"])
        end_ts = format_timestamp_srt(seg["end"])
        text = seg["text"].strip()
        lines.append(f"{idx}\n{start_ts} --> {end_ts}\n{text}\n")
    return "\n".join(lines)


def generate_vtt_content(segments) -> str:
    lines = ["WEBVTT\n\n"]
    for idx, seg in enumerate(segments, start=1):
        start_ts = format_timestamp_vtt(seg["start"])
        end_ts = format_timestamp_vtt(seg["end"])
        text = seg["text"].strip()
        lines.append(f"{idx}\n{start_ts} --> {end_ts}\n{text}\n")
    return "\n".join(lines)


def generate_txt_content(segments, include_timestamps=False) -> str:
    if include_timestamps:
        lines = []
        for seg in segments:
            start_ts = format_timestamp_srt(seg["start"])
            lines.append(f"[{start_ts}] {seg['text'].strip()}")
        return "\n".join(lines)
    return "\n".join(seg["text"].strip() for seg in segments if seg["text"].strip())


def get_video_dimensions(video_path):
    """
    Returns (width, height) of the video file using ffprobe, accounting for display rotation metadata.
    """
    try:
        import json

        cmd = [
            str(ffprobe_executable()),
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height:stream_side_data=rotation:stream_tags=rotate",
            "-of", "json",
            str(video_path),
        ]
        out = subprocess.check_output(cmd, **hidden_subprocess_kwargs()).decode("utf-8").strip()
        if out:
            data = json.loads(out)
            streams = data.get("streams", [])
            if streams:
                s = streams[0]
                w = int(s.get("width", 1920))
                h = int(s.get("height", 1080))
                rot = 0
                for sd in s.get("side_data_list", []):
                    if "rotation" in sd:
                        try:
                            rot = int(round(float(sd["rotation"])))
                            break
                        except (ValueError, TypeError):
                            pass
                if rot == 0 and "tags" in s:
                    tag_rot = s["tags"].get("rotate")
                    if tag_rot is not None:
                        try:
                            rot = int(round(float(tag_rot)))
                        except (ValueError, TypeError):
                            pass
                if abs(rot) in (90, 270):
                    w, h = h, w
                return w, h
    except Exception:
        pass
    return 1920, 1080


def split_words_into_subtitles(words, max_words=6, max_duration=2.8, max_pause=0.45):
    """
    Groups word-level timestamps into natural, readable subtitle phrases
    with exact sync (like CapCut auto-captions).
    """
    if not words:
        return []
    chunks = []
    cur_words = []
    cur_start = None

    for w in words:
        w_text = w.word.strip()
        if not w_text:
            continue
        if cur_start is None:
            cur_start = w.start
            cur_words.append(w)
            continue

        pause = w.start - cur_words[-1].end
        dur = w.end - cur_start
        count = len(cur_words)

        should_split = False
        if count >= max_words or dur >= max_duration:
            should_split = True
        elif pause >= max_pause and count >= 2:
            should_split = True
        elif cur_words[-1].word.rstrip()[-1:] in (".", "!", "?", "،", "؛") and count >= 3:
            should_split = True

        if should_split:
            chunks.append({
                "start": round(cur_start, 3),
                "end": round(cur_words[-1].end, 3),
                "text": " ".join(item.word.strip() for item in cur_words),
            })
            cur_words = [w]
            cur_start = w.start
        else:
            cur_words.append(w)

    if cur_words:
        chunks.append({
            "start": round(cur_start, 3),
            "end": round(cur_words[-1].end, 3),
            "text": " ".join(item.word.strip() for item in cur_words),
        })
    return chunks


def has_video_stream(media_path):
    """
    Checks whether the file has at least one video stream using ffprobe.
    """
    if not media_path:
        return False
    try:
        p = Path(media_path).resolve()
        if not p.is_file():
            return False
        cmd = [
            str(ffprobe_executable()),
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            str(p),
        ]
        out = subprocess.check_output(cmd, **hidden_subprocess_kwargs()).decode("utf-8").strip()
        return "video" in out.lower()
    except Exception:
        return False


def find_matching_video(media_path, hint_path=None):
    """
    Finds a video file associated with the given media path (or hint).
    If media_path is already a video with a video stream, returns it.
    If media_path is an audio file, searches adjacent and parent folders
    for a video file with the matching stem (or base stem before _trim_).
    """
    if not media_path:
        return None
    try:
        p = Path(media_path).resolve()
    except Exception:
        return None

    if p.is_file() and has_video_stream(p):
        return p

    if hint_path:
        try:
            hp = Path(hint_path).resolve()
            if hp.is_file() and has_video_stream(hp):
                return hp
        except Exception:
            pass

    stem = p.stem
    base_stem = stem.split("_trim_")[0]
    search_dirs = [p.parent]
    if p.parent.parent not in search_dirs:
        search_dirs.append(p.parent.parent)
    if p.parent.name.lower() == "output" and p.parent.parent.parent not in search_dirs:
        search_dirs.append(p.parent.parent.parent)

    # 1. Exact stem video match
    for d in search_dirs:
        if not d.is_dir():
            continue
        for ext in VIDEO_EXTS:
            cand = d / f"{stem}{ext}"
            if cand.is_file() and has_video_stream(cand):
                return cand

    # 2. Base stem video match (e.g. before _trim_)
    if base_stem != stem:
        for d in search_dirs:
            if not d.is_dir():
                continue
            for ext in VIDEO_EXTS:
                cand = d / f"{base_stem}{ext}"
                if cand.is_file() and has_video_stream(cand):
                    return cand

    return None


from video_studio import (
    ASPECT_RATIOS,
    FIT_MODES,
    build_aspect_ratio_filter,
    get_aspect_ratio_dimensions,
    SUBTITLE_COLORS,
    SUBTITLE_OUTLINES,
    SUBTITLE_ALIGNMENTS,
    build_subtitle_style_string,
    LOGO_POSITIONS,
    BANNER_POSITIONS,
    BANNER_BG_COLORS,
    BANNER_TEXT_COLORS,
    generate_title_banner_image,
    build_logo_overlay_filter,
    build_title_banner_filter,
    build_composite_video_filter,
    export_styled_video,
    SILENCE_PRESETS,
    SILENCE_MODES,
    detect_silences,
    compute_speech_segments,
    summarize_silence_analysis,
    remap_subtitles_for_cuts,
    parse_and_remap_srt_file,
    build_silence_filter_expressions,
    export_silence_cut_media,
)


def burn_subtitles_to_video(
    video_path,
    srt_path,
    output_path=None,
    output_dir=None,
    font_size=None,
    font_name="Segoe UI",
    margin_v=None,
    style_config=None,
    cancel_callback=None,
    progress_callback=None,
):
    video_path = Path(video_path).resolve()
    srt_path = Path(srt_path).resolve()

    if not srt_path.exists():
        raise FileNotFoundError(f"Subtitle file not found: {srt_path}")

    is_video = has_video_stream(video_path)
    target_ext = video_path.suffix if (is_video and video_path.suffix.lower() in VIDEO_EXTS) else ".mp4"

    if output_path is None:
        if output_dir is None:
            output_dir = video_path.parent / "output"
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = unique_output_path(output_dir / f"{video_path.stem}_captioned{target_ext}")

    srt_text = srt_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not srt_text:
        if is_video:
            shutil.copy2(video_path, output_path)
        if progress_callback:
            try:
                progress_callback(100, "Subtitle file empty", 0, 0, 0)
            except Exception:
                pass
        return output_path

    # Auto-scale font size and margin according to video resolution
    if is_video:
        w, h = get_video_dimensions(video_path)
    else:
        w, h = 1920, 1080

    cfg = dict(style_config) if style_config else {}
    s_font_name = cfg.get("font_name", font_name)
    s_font_size = cfg.get("font_size", font_size)
    s_text_color = cfg.get("text_color", "white")
    s_outline_style = cfg.get("outline_style", "thick_black")
    s_bold = cfg.get("bold", True)
    s_italic = cfg.get("italic", False)
    s_pos_v = cfg.get("position_v", "bottom")
    s_pos_h = cfg.get("position_h", "center")
    s_margin_v = cfg.get("margin_v", margin_v)

    style = build_subtitle_style_string(
        font_name=s_font_name,
        font_size=s_font_size,
        text_color=s_text_color,
        outline_style=s_outline_style,
        bold=s_bold,
        italic=s_italic,
        position_v=s_pos_v,
        position_h=s_pos_h,
        margin_v=s_margin_v,
        video_h=h,
    )

    temp_path = temp_output_path(output_path)
    escaped_srt = str(srt_path).replace("\\", "/").replace(":", r"\:")
    filter_arg = f"subtitles=filename='{escaped_srt}':force_style='{style}'"

    duration = get_media_duration(video_path) or 0
    if is_video:
        cmd = [
            str(ffmpeg_executable()),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            "-nostats",
            "-i",
            str(video_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-vf",
            filter_arg,
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "22",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(temp_path),
        ]
    else:
        cmd = [
            str(ffmpeg_executable()),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            "-nostats",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s={w}x{h}:r=30",
            "-i",
            str(video_path),
            "-vf",
            filter_arg,
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "22",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(temp_path),
        ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        **hidden_subprocess_kwargs(),
    )

    for line in process.stdout:
        if cancellation_requested(cancel_callback):
            stop_process(process)
            remove_partial_output(temp_path)
            raise CancelledError("Operation canceled")
        key, separator, value = line.strip().partition("=")
        if separator != "=" or key != "out_time_ms" or not duration:
            continue
        try:
            elapsed = int(value) / 1_000_000
        except ValueError:
            continue
        percent = max(0, min(99, int((elapsed / duration) * 100)))
        if progress_callback:
            progress_callback(percent, f"Burning subtitles: {percent}%", elapsed, elapsed, duration)

    if cancellation_requested(cancel_callback):
        stop_process(process)
        remove_partial_output(temp_path)
        raise CancelledError("Operation canceled")

    stderr = process.stderr.read() if process.stderr else ""
    return_code = process.wait()

    if return_code != 0:
        remove_partial_output(temp_path)
        raise RuntimeError(f"FFmpeg subtitle burning failed: {stderr}")

    return finalize_output(temp_path, output_path)


def get_whisper_models_dir():
    local_dir = APP_DIR / "models" / "whisper"
    if local_dir.is_dir():
        return local_dir
    appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    old_d = Path(appdata) / "Media Audio Studio" / "models" / "whisper"
    new_d = Path(appdata) / "ClipCraft Studio" / "models" / "whisper"
    if old_d.is_dir() and any(old_d.iterdir()):
        return old_d
    new_d.mkdir(parents=True, exist_ok=True)
    return new_d


def get_whisper_model_status(model_size="base", models_dir=None):
    """
    Returns information about the Whisper model:
    {
        "model_size": model_size,
        "is_downloaded": bool,
        "path": Path or None,
        "folder": Path,
        "estimated_mb": float,
    }
    """
    if models_dir is None:
        models_dir = get_whisper_models_dir()
    models_dir = Path(models_dir)
    target_dir = models_dir / model_size

    est_sizes = {
        "tiny": 75.0,
        "base": 141.0,
        "small": 470.0,
        "medium": 1500.0,
        "turbo": 1540.0,
        "large-v3-turbo": 1540.0,
        "large-v3": 3100.0,
    }
    est_mb = est_sizes.get(model_size.lower(), 470.0)

    # 1. Check dedicated models directory
    if target_dir.is_dir():
        has_bin = (target_dir / "model.bin").is_file() or (target_dir / "model.safetensors").is_file()
        has_cfg = (target_dir / "config.json").is_file()
        if has_bin and has_cfg:
            return {
                "model_size": model_size,
                "is_downloaded": True,
                "path": target_dir,
                "folder": models_dir,
                "estimated_mb": est_mb,
            }

    # 2. Check standard HuggingFace Hub cache
    if faster_whisper is not None:
        try:
            import faster_whisper.utils as u
            p = u.download_model(model_size, local_files_only=True)
            return {
                "model_size": model_size,
                "is_downloaded": True,
                "path": Path(p),
                "folder": Path(p).parent.parent,
                "estimated_mb": est_mb,
            }
        except Exception:
            pass

    return {
        "model_size": model_size,
        "is_downloaded": False,
        "path": None,
        "folder": models_dir,
        "estimated_mb": est_mb,
    }


_ACTIVE_DOWNLOAD_CONTEXT = {
    "session": None,
    "response": None,
    "aborted": False,
    "active_sockets": set(),
}

try:
    import urllib3.util.connection as _uc
    _orig_create_conn = _uc.create_connection

    def _tracked_create_conn(*args, **kwargs):
        sock = _orig_create_conn(*args, **kwargs)
        _ACTIVE_DOWNLOAD_CONTEXT["active_sockets"].add(sock)
        return sock

    _uc.create_connection = _tracked_create_conn
except Exception:
    pass


def abort_whisper_download():
    """Immediately aborts any active Whisper model download in milliseconds."""
    _ACTIVE_DOWNLOAD_CONTEXT["aborted"] = True
    resp = _ACTIVE_DOWNLOAD_CONTEXT.get("response")
    sess = _ACTIVE_DOWNLOAD_CONTEXT.get("session")
    if resp is not None:
        try:
            resp.close()
        except Exception:
            pass
    if sess is not None:
        try:
            sess.close()
        except Exception:
            pass
    for s in list(_ACTIVE_DOWNLOAD_CONTEXT.get("active_sockets", [])):
        try:
            import socket
            s.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            s.close()
        except Exception:
            pass
    _ACTIVE_DOWNLOAD_CONTEXT["active_sockets"].clear()


def format_download_speed(bytes_per_sec):
    if bytes_per_sec >= 1024 * 1024:
        return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
    elif bytes_per_sec >= 1024:
        return f"{bytes_per_sec / 1024:.0f} KB/s"
    return f"{bytes_per_sec:.0f} B/s"


def format_eta_str(bytes_remaining, bytes_per_sec):
    if bytes_per_sec <= 0 or bytes_remaining <= 0:
        return ""
    secs = int(bytes_remaining / bytes_per_sec)
    mins, s = divmod(secs, 60)
    hrs, m = divmod(mins, 60)
    if hrs > 0:
        return f"{hrs:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def download_whisper_model(
    model_size="small",
    models_dir=None,
    progress_callback=None,
    cancel_callback=None,
    **kwargs,
):
    """
    Downloads a faster-whisper model with:
    - Multi-CDN / mirror fallback (hf-mirror.com and huggingface.co)
    - Resumable partial downloads (.part files)
    - Sub-second instant cancellation (< 0.1s response)
    - Real-time progress with Speed (KB/s or MB/s) and ETA (minutes:seconds)
    """
    import time
    import requests

    if "cancel_check" in kwargs and cancel_callback is None:
        cancel_callback = kwargs.pop("cancel_check")

    if models_dir is None:
        models_dir = get_whisper_models_dir()
    models_dir = Path(models_dir)
    target_dir = models_dir / model_size
    target_dir.mkdir(parents=True, exist_ok=True)

    status = get_whisper_model_status(model_size, models_dir)
    if status["is_downloaded"] and status["path"]:
        if progress_callback:
            try:
                progress_callback(100, 0, 0, "Ready", "0 KB/s", "", status["path"])
            except Exception:
                pass
        return status["path"]

    _ACTIVE_DOWNLOAD_CONTEXT["aborted"] = False

    import faster_whisper.utils as u
    repo_id = u._MODELS.get(model_size)
    if not repo_id:
        if model_size in ("turbo", "large-v3-turbo"):
            repo_id = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"
        else:
            repo_id = f"Systran/faster-whisper-{model_size}"

    FALLBACK_MODEL_FILES = {
        "tiny": [
            ("config.json", 2249),
            ("vocabulary.txt", 459861),
            ("tokenizer.json", 2203239),
            ("model.bin", 75538270),
        ],
        "base": [
            ("config.json", 2261),
            ("vocabulary.txt", 459861),
            ("tokenizer.json", 2203239),
            ("model.bin", 145214124),
        ],
        "small": [
            ("config.json", 2261),
            ("vocabulary.txt", 459861),
            ("tokenizer.json", 2203239),
            ("model.bin", 483546902),
        ],
        "turbo": [
            ("config.json", 2263),
            ("preprocessor_config.json", 340),
            ("vocabulary.json", 1068114),
            ("tokenizer.json", 2710337),
            ("model.bin", 1617884929),
        ],
        "large-v3-turbo": [
            ("config.json", 2263),
            ("preprocessor_config.json", 340),
            ("vocabulary.json", 1068114),
            ("tokenizer.json", 2710337),
            ("model.bin", 1617884929),
        ],
        "medium": [
            ("config.json", 2261),
            ("vocabulary.txt", 459861),
            ("tokenizer.json", 2203239),
            ("model.bin", 1528448882),
        ],
    }

    files_to_download = FALLBACK_MODEL_FILES.get(model_size.lower())
    if not files_to_download:
        try:
            import huggingface_hub
            api = huggingface_hub.HfApi()
            inf = api.model_info(repo_id, files_metadata=True, timeout=4)
            needed_names = {
                "config.json", "preprocessor_config.json", "model.bin",
                "model.safetensors", "tokenizer.json", "vocabulary.txt", "vocabulary.json"
            }
            files_to_download = [(s.rfilename, s.size or 0) for s in inf.siblings if s.rfilename in needed_names]
        except Exception:
            files_to_download = [
                ("config.json", 2300),
                ("tokenizer.json", 2200000),
                ("vocabulary.txt", 460000),
                ("model.bin", int(status["estimated_mb"] * 1024 * 1024)),
            ]

    total_expected_bytes = sum(size for _, size in files_to_download if size)

    downloaded_overall = 0
    pending_files = []
    for filename, expected_size in files_to_download:
        dest_file = target_dir / filename
        if dest_file.exists() and expected_size > 0 and dest_file.stat().st_size == expected_size:
            downloaded_overall += expected_size
        else:
            pending_files.append((filename, expected_size))

    if not pending_files:
        if progress_callback:
            try:
                progress_callback(100, total_expected_bytes, total_expected_bytes, "Complete", "0 KB/s", "", target_dir)
            except Exception:
                pass
        return target_dir

    start_time = time.time()
    last_report_time = start_time
    speed_calc_window = []

    session = requests.Session()
    _ACTIVE_DOWNLOAD_CONTEXT["session"] = session

    base_mirrors = [
        f"https://hf-mirror.com/{repo_id}/resolve/main/",
        f"https://huggingface.co/{repo_id}/resolve/main/",
    ]

    try:
        for filename, expected_size in pending_files:
            if _ACTIVE_DOWNLOAD_CONTEXT["aborted"] or cancellation_requested(cancel_callback):
                raise CancelledError("Model download canceled")

            dest_file = target_dir / filename
            part_file = target_dir / f"{filename}.part"

            existing_bytes = part_file.stat().st_size if part_file.exists() else 0
            if expected_size and existing_bytes > expected_size:
                existing_bytes = 0

            response = None
            for base_url in base_mirrors:
                if _ACTIVE_DOWNLOAD_CONTEXT["aborted"] or cancellation_requested(cancel_callback):
                    raise CancelledError("Model download canceled")

                file_url = base_url + filename
                headers = {"User-Agent": "Mozilla/5.0"}
                if existing_bytes > 0:
                    headers["Range"] = f"bytes={existing_bytes}-"

                try:
                    resp = session.get(file_url, stream=True, headers=headers, timeout=(4.0, 15.0))
                    if resp.status_code == 416:
                        if expected_size and existing_bytes >= expected_size:
                            response = resp
                            break
                    if resp.status_code in (200, 206):
                        response = resp
                        _ACTIVE_DOWNLOAD_CONTEXT["response"] = resp
                        break
                    else:
                        resp.close()
                except Exception:
                    continue

            if response is None:
                raise RuntimeError(f"Failed to connect to download mirror for {filename}")

            if response.status_code == 200:
                existing_bytes = 0
                write_mode = "wb"
            elif response.status_code == 206:
                write_mode = "ab"
            else:
                write_mode = "ab"

            cur_file_dl = existing_bytes
            with open(part_file, write_mode) as out_f:
                for chunk in response.iter_content(chunk_size=65536):
                    if _ACTIVE_DOWNLOAD_CONTEXT["aborted"] or cancellation_requested(cancel_callback):
                        response.close()
                        raise CancelledError("Model download canceled")

                    if chunk:
                        out_f.write(chunk)
                        chunk_len = len(chunk)
                        cur_file_dl += chunk_len

                        now = time.time()
                        speed_calc_window.append((now, chunk_len))
                        while speed_calc_window and now - speed_calc_window[0][0] > 3.0:
                            speed_calc_window.pop(0)

                        if now - last_report_time >= 0.25:
                            total_now = downloaded_overall + cur_file_dl
                            pct = min(99, int((total_now / max(total_expected_bytes, 1)) * 100))

                            win_time = max(now - speed_calc_window[0][0], 0.1) if speed_calc_window else 1.0
                            win_bytes = sum(b for _, b in speed_calc_window)
                            speed_bps = win_bytes / win_time
                            speed_str = format_download_speed(speed_bps)

                            rem_bytes = max(total_expected_bytes - total_now, 0)
                            eta_str = format_eta_str(rem_bytes, speed_bps)

                            last_report_time = now
                            if progress_callback:
                                try:
                                    progress_callback(
                                        pct,
                                        total_now,
                                        total_expected_bytes,
                                        filename,
                                        speed_str,
                                        eta_str,
                                        target_dir,
                                    )
                                except Exception:
                                    pass

            response.close()

            if _ACTIVE_DOWNLOAD_CONTEXT["aborted"] or cancellation_requested(cancel_callback):
                raise CancelledError("Model download canceled")

            if part_file.exists():
                if dest_file.exists():
                    try:
                        dest_file.unlink()
                    except Exception:
                        pass
                part_file.rename(dest_file)
                downloaded_overall += dest_file.stat().st_size

        if progress_callback:
            try:
                progress_callback(100, total_expected_bytes, total_expected_bytes, "Complete", "0 KB/s", "", target_dir)
            except Exception:
                pass

        return target_dir

    finally:
        session.close()
        _ACTIVE_DOWNLOAD_CONTEXT["response"] = None
        _ACTIVE_DOWNLOAD_CONTEXT["session"] = None
        _ACTIVE_DOWNLOAD_CONTEXT["active_sockets"].clear()


def translate_segments(segments, target_lang="ar", batch_size=20, cancel_callback=None):
    """
    Translates transcript segments into target_lang using online neural translation.
    Keeps segment timestamps intact. Returns translated copy of segments.
    """
    if not segments or not target_lang or target_lang in ("none", "same", "auto"):
        return segments

    import urllib.request
    import urllib.parse
    import json

    translated_segments = []
    total = len(segments)

    for i in range(0, total, batch_size):
        if cancellation_requested(cancel_callback):
            raise CancelledError("Translation canceled")

        chunk = segments[i : i + batch_size]
        text_lines = [s.get("text", "") for s in chunk]
        joined = " \n \n ".join(text_lines)
        url = (
            f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={urllib.parse.quote(target_lang)}&dt=t&q="
            + urllib.parse.quote(joined)
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            full_trans = "".join(c[0] for c in data[0] if c and c[0])
            trans_lines = [l.strip() for l in full_trans.split("\n") if l.strip()]
            for idx, orig_seg in enumerate(chunk):
                t_text = trans_lines[idx] if idx < len(trans_lines) else orig_seg.get("text", "")
                translated_segments.append({
                    "start": orig_seg["start"],
                    "end": orig_seg["end"],
                    "text": t_text,
                })
        except Exception as exc:
            print(f"Translation batch failed ({exc}), preserving original text")
            translated_segments.extend(chunk)

    return translated_segments


def transcribe_media(
    source_path,
    output_dir=None,
    model_size="small",
    language=None,
    task="transcribe",
    translate_to=None,
    export_srt=True,
    export_vtt=True,
    export_txt=True,
    burn_to_video=False,
    style_config=None,
    models_dir=None,
    vad_filter=True,
    condition_on_previous_text=False,
    repetition_penalty=1.15,
    no_repeat_ngram_size=3,
    initial_prompt=None,
    progress_callback=None,
    cancel_callback=None,
    **kwargs,
):
    """
    Transcribes an audio or video file to text using faster-whisper.
    Applies Silero VAD filtering, anti-hallucination safeguards, and optional subtitle translation (like CapCut/NoteGPT).
    Generates .srt, .vtt, and .txt files.
    Optionally burns subtitles into video.
    """
    if "cancel_check" in kwargs and cancel_callback is None:
        cancel_callback = kwargs.pop("cancel_check")

    if not whisper_available():
        raise RuntimeError(
            "faster-whisper is not installed. Please run: py -3.12 -m pip install faster-whisper"
        )

    source_path = Path(source_path).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"File not found: {source_path}")

    if output_dir is None:
        output_dir = source_path.parent / "output"
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if cancellation_requested(cancel_callback):
        raise CancelledError("Operation canceled")

    media_duration = get_media_duration(source_path) or 0

    device = "cpu"
    compute_type = "int8"
    try:
        import ctranslate2
        import ctypes
        if ctranslate2.get_cuda_device_count() > 0:
            can_cuda = False
            for dll in ["cublas64_12.dll", "cublas64_11.dll"]:
                try:
                    ctypes.CDLL(dll)
                    can_cuda = True
                    break
                except Exception:
                    pass
            if can_cuda:
                supported = ctranslate2.get_supported_compute_types("cuda")
                if "float16" in supported:
                    device = "cuda"
                    compute_type = "float16"
                elif "int8_float16" in supported:
                    device = "cuda"
                    compute_type = "int8_float16"
                elif "int8" in supported:
                    device = "cuda"
                    compute_type = "int8"
    except Exception:
        pass

    # Ensure model is downloaded with real-time download progress
    status = get_whisper_model_status(model_size, models_dir)
    if not status["is_downloaded"]:
        def _model_dl_cb(pct, dl_bytes, tot_bytes, cur_file, speed, *extra):
            dl_mb = dl_bytes / (1024 * 1024)
            tot_mb = tot_bytes / (1024 * 1024)
            eta = extra[0] if extra else ""
            eta_part = f" - ETA: {eta}" if eta else ""
            msg = f"Downloading AI model '{model_size}' ({dl_mb:.1f} / {tot_mb:.1f} MB - {pct}%) [{speed}{eta_part}]"
            if progress_callback:
                try:
                    progress_callback(pct, msg, 0, 0, media_duration)
                except Exception:
                    pass

        model_path = download_whisper_model(
            model_size=model_size,
            models_dir=models_dir,
            progress_callback=_model_dl_cb,
            cancel_callback=cancel_callback,
        )
    else:
        model_path = status["path"]

    if cancellation_requested(cancel_callback):
        raise CancelledError("Operation canceled")

    if progress_callback:
        progress_callback(
            0,
            f"Loading Whisper model '{model_size}'...",
            0,
            0,
            media_duration,
        )

    target_lang = None if (not language or language == "auto") else language

    if initial_prompt is None:
        if target_lang == "ar":
            initial_prompt = (
                "بسم الله الرحمن الرحيم، الحمد لله رب العالمين، وصلى الله وسلم على سيدنا محمد وعلى آله وصحبه أجمعين. "
                "تفريغ صوتي دقيق باللغة العربية الفصحى والعامية مع علامات الترقيم المناسبة."
            )
        elif target_lang == "en":
            initial_prompt = "Hello and welcome. This is a clear English transcription with proper punctuation and natural sentences."
        else:
            initial_prompt = "Accurate speech transcription with proper punctuation and natural formatting."

    vad_params = dict(
        min_silence_duration_ms=500,
        threshold=0.40,
        min_speech_duration_ms=250,
        speech_pad_ms=400,
    )

    if progress_callback:
        progress_callback(
            2,
            "Transcribing audio...",
            0,
            0,
            media_duration,
        )

    transcribe_source = str(source_path)
    temp_wav = None
    try:
        if cancellation_requested(cancel_callback):
            raise CancelledError("Operation canceled")

        import tempfile
        temp_wav_fd, temp_wav_path_str = tempfile.mkstemp(suffix=".wav", prefix="clipcraft_audio_")
        os.close(temp_wav_fd)
        temp_wav = Path(temp_wav_path_str)

        if progress_callback:
            progress_callback(
                1,
                "جاري تحضير واستخراج الصوت..." if target_lang == "ar" else "Preparing audio track...",
                0,
                0,
                media_duration,
            )

        extract_cmd = [
            str(ffmpeg_executable()),
            "-y",
            "-nostdin",
            "-threads", "0",
            "-i", str(source_path),
            "-vn", "-sn", "-dn",
            "-f", "wav",
            "-ac", "1",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            str(temp_wav),
        ]
        proc = subprocess.Popen(extract_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **hidden_subprocess_kwargs())
        register_active_process(proc)
        try:
            while proc.poll() is None:
                if cancellation_requested(cancel_callback):
                    stop_process(proc)
                    raise CancelledError("Operation canceled")
                time.sleep(0.08)
        finally:
            unregister_active_process(proc)

        if proc.returncode == 0 and temp_wav.exists() and temp_wav.stat().st_size > 1000:
            transcribe_source = str(temp_wav)
        else:
            if temp_wav and temp_wav.exists():
                temp_wav.unlink(missing_ok=True)
                temp_wav = None
            transcribe_source = str(source_path)
    except CancelledError:
        if temp_wav and temp_wav.exists():
            temp_wav.unlink(missing_ok=True)
        raise
    except Exception as exc:
        print(f"Audio extraction fallback to source path ({exc})")
        transcribe_source = str(source_path)

    try:
        cpu_cores = max(1, min(8, os.cpu_count() or 4))
        beam_sz = 1 if device == "cpu" else 2
        best_of_val = 1 if device == "cpu" else 2

        try:
            whisper_model = faster_whisper.WhisperModel(
                str(model_path),
                device=device,
                compute_type=compute_type,
                cpu_threads=cpu_cores,
                num_workers=1,
            )
            segments_gen, info = whisper_model.transcribe(
                transcribe_source,
                language=target_lang,
                task=task,
                beam_size=beam_sz,
                best_of=best_of_val,
                temperature=0.0,
                word_timestamps=True,
                vad_filter=vad_filter,
                vad_parameters=vad_params,
                condition_on_previous_text=condition_on_previous_text,
                repetition_penalty=repetition_penalty,
                no_repeat_ngram_size=no_repeat_ngram_size,
                compression_ratio_threshold=2.4,
                hallucination_silence_threshold=2.0,
                initial_prompt=initial_prompt,
            )
            detected_lang = info.language
            segments = []
            for seg in segments_gen:
                if cancellation_requested(cancel_callback):
                    raise CancelledError("Operation canceled")
                if hasattr(seg, "words") and seg.words:
                    sub_chunks = split_words_into_subtitles(seg.words)
                else:
                    sub_chunks = [{
                        "start": round(seg.start, 3),
                        "end": round(seg.end, 3),
                        "text": seg.text.strip(),
                    }]
                for ch in sub_chunks:
                    if not ch["text"]:
                        continue
                    segments.append(ch)
                    if media_duration > 0:
                        pct = min(90, max(2, int((ch["end"] / media_duration) * 100)))
                    else:
                        pct = min(90, len(segments) * 3)
                    if progress_callback:
                        progress_callback(pct, ch["text"], ch["start"], ch["end"], media_duration)
        except Exception as exc:
            if isinstance(exc, CancelledError) or cancellation_requested(cancel_callback):
                raise CancelledError("Operation canceled")
            if device != "cpu":
                print(f"CUDA transcription failed ({exc}), falling back to CPU int8...")
                whisper_model = faster_whisper.WhisperModel(
                    str(model_path),
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=cpu_cores,
                    num_workers=1,
                )
                segments_gen, info = whisper_model.transcribe(
                    transcribe_source,
                    language=target_lang,
                    task=task,
                    beam_size=1,
                    best_of=1,
                    temperature=0.0,
                    word_timestamps=True,
                    vad_filter=vad_filter,
                    vad_parameters=vad_params,
                    condition_on_previous_text=condition_on_previous_text,
                    repetition_penalty=repetition_penalty,
                    no_repeat_ngram_size=no_repeat_ngram_size,
                    compression_ratio_threshold=2.4,
                    hallucination_silence_threshold=2.0,
                    initial_prompt=initial_prompt,
                )
                detected_lang = info.language
                segments = []
                for seg in segments_gen:
                    if cancellation_requested(cancel_callback):
                        raise CancelledError("Operation canceled")
                    if hasattr(seg, "words") and seg.words:
                        sub_chunks = split_words_into_subtitles(seg.words)
                    else:
                        sub_chunks = [{
                            "start": round(seg.start, 3),
                            "end": round(seg.end, 3),
                            "text": seg.text.strip(),
                        }]
                    for ch in sub_chunks:
                        if not ch["text"]:
                            continue
                        segments.append(ch)
                        if media_duration > 0:
                            pct = min(90, max(2, int((ch["end"] / media_duration) * 100)))
                        else:
                            pct = min(90, len(segments) * 3)
                        if progress_callback:
                            progress_callback(pct, ch["text"], ch["start"], ch["end"], media_duration)
            else:
                raise

        # Subtitle translation if requested (like CapCut/NoteGPT)
        if translate_to and translate_to not in ("none", "same", "auto", detected_lang, target_lang):
            if progress_callback:
                progress_callback(
                    92,
                    f"Translating subtitles to {translate_to}...",
                    media_duration,
                    media_duration,
                    media_duration,
                )
            segments = translate_segments(segments, target_lang=translate_to, cancel_callback=cancel_callback)

        srt_path = output_dir / f"{source_path.stem}.srt"
        vtt_path = output_dir / f"{source_path.stem}.vtt"
        txt_path = output_dir / f"{source_path.stem}.txt"

        srt_content = generate_srt_content(segments)
        vtt_content = generate_vtt_content(segments)
        txt_content = generate_txt_content(segments)

        if export_srt:
            srt_path.write_text(srt_content, encoding="utf-8")
        if export_vtt:
            vtt_path.write_text(vtt_content, encoding="utf-8")
        if export_txt:
            txt_path.write_text(txt_content, encoding="utf-8")

        captioned_video_path = None
        if burn_to_video and source_path.suffix.lower() in VIDEO_EXTS:
            if progress_callback:
                progress_callback(
                    95,
                    "Burning subtitles into video...",
                    0,
                    media_duration,
                    media_duration,
                )
            captioned_video_path = burn_subtitles_to_video(
                video_path=source_path,
                srt_path=srt_path,
                output_dir=output_dir,
                style_config=style_config,
                cancel_callback=cancel_callback,
            )

        if progress_callback:
            progress_callback(
                100,
                "Transcription completed!",
                media_duration,
                media_duration,
                media_duration,
            )

        return {
            "text": txt_content,
            "segments": segments,
            "language": detected_lang,
            "translated_to": translate_to,
            "srt_path": srt_path if export_srt else None,
            "vtt_path": vtt_path if export_vtt else None,
            "txt_path": txt_path if export_txt else None,
            "video_path": captioned_video_path,
        }
    finally:
        if temp_wav and Path(temp_wav).exists():
            try:
                Path(temp_wav).unlink(missing_ok=True)
            except Exception:
                pass


def get_capcut_drafts():
    """
    Returns detected CapCut desktop drafts on the user's PC.
    Each item: {'id', 'name', 'date', 'path', 'subtitle_count'}
    """
    import os, json, datetime
    base = os.path.expandvars(r'%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft')
    drafts = []
    if not os.path.exists(base):
        return drafts
    try:
        for name in os.listdir(base):
            p = os.path.join(base, name, "draft_content.json")
            if os.path.exists(p):
                try:
                    mtime = os.path.getmtime(p)
                    dt = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                    with open(p, "r", encoding="utf-8") as f:
                        d = json.load(f)
                    proj_name = d.get("name") or name
                    texts = {t["id"] for t in d.get("materials", {}).get("texts", []) if "id" in t}
                    count = sum(
                        1
                        for track in d.get("tracks", [])
                        for seg in track.get("segments", [])
                        if seg.get("material_id") in texts
                    )
                    drafts.append({
                        "id": name,
                        "name": proj_name,
                        "date": dt,
                        "mtime": mtime,
                        "path": p,
                        "subtitle_count": count,
                    })
                except Exception:
                    pass
        drafts.sort(key=lambda x: x.get("mtime", 0), reverse=True)
    except Exception:
        pass
    return drafts


def extract_subtitles_from_capcut(draft_path, output_dir=None, export_srt=True, export_vtt=True, export_txt=True):
    """
    Extracts high-precision captions from a CapCut draft.
    Returns dict compatible with transcribe_media:
    {'segments', 'text', 'srt_path', 'vtt_path', 'txt_path', 'language'}
    """
    import json
    draft_path = Path(draft_path)
    if not draft_path.exists():
        raise FileNotFoundError(f"CapCut draft not found: {draft_path}")

    with open(draft_path, "r", encoding="utf-8") as f:
        d = json.load(f)

    materials = d.get("materials", {})
    texts = {}
    for t in materials.get("texts", []):
        if "id" in t:
            try:
                content = json.loads(t.get("content", "{}"))
                texts[t["id"]] = content.get("text", "")
            except Exception:
                pass

    segments = []
    for track in d.get("tracks", []):
        for seg in track.get("segments", []):
            mid = seg.get("material_id")
            if mid in texts and texts[mid].strip():
                tr = seg.get("target_timerange", {})
                st = tr.get("start", 0) / 1000000.0
                du = tr.get("duration", 0) / 1000000.0
                segments.append({
                    "start": round(st, 3),
                    "end": round(st + du, 3),
                    "text": texts[mid].strip(),
                })
    segments.sort(key=lambda x: x["start"])

    txt_content = " ".join(s["text"] for s in segments)

    if output_dir is None:
        output_dir = draft_path.parent
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = d.get("name") or draft_path.parent.name
    srt_path = output_dir / f"{base_name}.srt"
    vtt_path = output_dir / f"{base_name}.vtt"
    txt_path = output_dir / f"{base_name}.txt"

    if export_srt:
        srt_content = generate_srt_content(segments)
        srt_path.write_text(srt_content, encoding="utf-8-sig")
    if export_vtt:
        vtt_content = generate_vtt_content(segments)
        vtt_path.write_text(vtt_content, encoding="utf-8-sig")
    if export_txt:
        txt_path.write_text(txt_content, encoding="utf-8-sig")

    # Detect associated media file (video or audio)
    media_path = None
    for v in materials.get("videos", []):
        vp = v.get("path")
        if vp:
            v_cand = Path(vp)
            if v_cand.exists() and v_cand.suffix.lower() in VIDEO_EXTS:
                media_path = v_cand
                break
    if not media_path:
        for a in materials.get("audios", []):
            ap = a.get("path")
            if ap:
                a_cand = Path(ap)
                if a_cand.exists():
                    stem = a_cand.stem.split("_trim_")[0]
                    for p in [a_cand.parent, a_cand.parent.parent, a_cand.parent.parent.parent]:
                        try:
                            found = list(p.glob(f"{stem}*.mp4"))
                            if found:
                                media_path = found[0]
                                break
                        except Exception:
                            pass
                    if not media_path:
                        media_path = a_cand
                    break

    return {
        "text": txt_content,
        "segments": segments,
        "language": "ar",
        "srt_path": srt_path if export_srt else None,
        "vtt_path": vtt_path if export_vtt else None,
        "txt_path": txt_path if export_txt else None,
        "video_path": media_path,
    }


def batch_transcribe_media(
    media_files,
    output_dir,
    model_size="small",
    language=None,
    translate_to=None,
    export_srt=True,
    export_vtt=True,
    export_txt=True,
    burn_to_video=False,
    skip_if_exists=True,
    progress_callback=None,
    cancel_callback=None,
    **kwargs,
):
    if "cancel_check" in kwargs and cancel_callback is None:
        cancel_callback = kwargs.pop("cancel_check")
    total = len(media_files)
    results = []

    for index, media_path in enumerate(media_files):
        if cancellation_requested(cancel_callback):
            raise CancelledError("Operation canceled")

        srt_expected = output_dir / f"{media_path.stem}.srt"
        if skip_if_exists and srt_expected.exists():
            print(f"Skipping existing transcription: {srt_expected.name}")
            if progress_callback:
                try:
                    progress_callback(index + 1, total, media_path, 100, f"Skipped: {media_path.name}")
                except Exception:
                    pass
            continue

        print(f"Transcribing [{index + 1}/{total}]: {media_path.name}")

        def file_progress(pct, text, start, end, dur):
            if progress_callback:
                try:
                    progress_callback(index, total, media_path, pct, text)
                except Exception:
                    pass

        res = transcribe_media(
            source_path=media_path,
            output_dir=output_dir,
            model_size=model_size,
            language=language,
            translate_to=translate_to,
            export_srt=export_srt,
            export_vtt=export_vtt,
            export_txt=export_txt,
            burn_to_video=burn_to_video,
            progress_callback=file_progress,
            cancel_callback=cancel_callback,
            **kwargs,
        )
        results.append(res)
        if progress_callback:
            try:
                progress_callback(index + 1, total, media_path, 100, f"Finished: {media_path.name}")
            except Exception:
                pass

    return results


def detect_audio_volume(source_path, sample_seconds=180):
    """
    Detects the audio volume levels (max volume in dB and mean volume in dB)
    using FFmpeg's volumedetect filter.
    Returns dict: {'max_volume': float, 'mean_volume': float, 'suggested_gain': float}
    """
    source_path = Path(source_path).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"File not found: {source_path}")

    cmd = [
        str(ffmpeg_executable()),
        "-hide_banner",
        "-vn",
        "-sn",
        "-dn",
    ]
    if sample_seconds and float(sample_seconds) > 0:
        cmd.extend(["-t", str(float(sample_seconds))])
    cmd.extend([
        "-i",
        str(source_path),
        "-af",
        "volumedetect",
        "-f",
        "null",
        "-",
    ])
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        **hidden_subprocess_kwargs(),
    )
    _, stderr = process.communicate()

    max_match = re.search(r"max_volume:\s*([-\d\.]+)\s*dB", stderr)
    mean_match = re.search(r"mean_volume:\s*([-\d\.]+)\s*dB", stderr)

    max_vol = float(max_match.group(1)) if max_match else 0.0
    mean_vol = float(mean_match.group(1)) if mean_match else 0.0
    suggested_gain = max(0.0, -max_vol)

    return {
        "max_volume": max_vol,
        "mean_volume": mean_vol,
        "suggested_gain": round(suggested_gain, 1),
    }


def auto_suggest_silence_threshold(source_path):
    """
    Analyzes audio levels of `source_path` and suggests an optimal silence threshold in dB.
    """
    vol = detect_audio_volume(source_path)
    mean_db = vol.get("mean_volume", -20.0)
    max_db = vol.get("max_volume", 0.0)
    # Typical speech mean is ~10-14 dB above background silence floor
    suggested = round(max(-50.0, min(-22.0, mean_db - 10.0)), 1)
    return {
        "suggested_noise_db": suggested,
        "mean_volume": mean_db,
        "max_volume": max_db,
    }


def boost_audio_volume(
    source_path,
    gain_db=6.0,
    output_dir=None,
    output_ext=None,
    anti_clipping=True,
    normalize_peak=False,
    quality="192k",
    enhancement="Off",
    fade_in_sec=0.0,
    fade_out_sec=0.0,
    progress_callback=None,
    cancel_callback=None,
    **kwargs,
):
    """
    Boosts the volume of an audio or video file, optionally applying audio enhancement
    and fade-in/fade-out, and saves it with the new higher volume.
    If source is video, video track is copied without re-encoding (-c:v copy).
    """
    if "anti_clip" in kwargs:
        anti_clipping = kwargs.pop("anti_clip")
    if "output_format" in kwargs:
        output_ext = kwargs.pop("output_format")
    if "cancel_check" in kwargs and cancel_callback is None:
        cancel_callback = kwargs.pop("cancel_check")

    source_path = Path(source_path).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"File not found: {source_path}")

    if output_dir is None:
        output_dir = source_path.parent / "output"
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if cancellation_requested(cancel_callback):
        raise CancelledError("Operation canceled")

    actual_gain = float(gain_db)
    if normalize_peak:
        try:
            stats = detect_audio_volume(source_path)
            actual_gain = stats["suggested_gain"]
        except Exception:
            pass

    is_video = source_path.suffix.lower() in VIDEO_EXTS
    duration = get_media_duration(source_path) or 0

    filter_parts = []
    enh_str = ffmpeg_audio_filter_str(enhancement)
    if enh_str:
        filter_parts.append(enh_str)
    if abs(actual_gain) >= 0.05 or not filter_parts:
        filter_parts.append(f"volume={actual_gain:.1f}dB")
    if anti_clipping:
        filter_parts.append("alimiter=limit=0.98")
    if fade_in_sec and float(fade_in_sec) > 0:
        filter_parts.append(f"afade=t=in:st=0:d={float(fade_in_sec):.2f}")
    if fade_out_sec and float(fade_out_sec) > 0 and duration > float(fade_out_sec):
        st_out = max(0.0, duration - float(fade_out_sec))
        filter_parts.append(f"afade=t=out:st={st_out:.2f}:d={float(fade_out_sec):.2f}")
    af_string = ",".join(filter_parts)

    if output_ext is None or output_ext.lower() in ("original", "auto"):
        target_ext = source_path.suffix.lower()
    else:
        target_ext = output_ext.lower() if output_ext.startswith(".") else f".{output_ext.lower()}"

    output_path = output_dir / f"{source_path.stem}_boosted{target_ext}"
    if same_file_path(source_path, output_path):
        output_path = unique_output_path(output_dir / f"{source_path.stem}_louder{target_ext}")

    temp_path = temp_output_path(output_path)

    cmd = [
        str(ffmpeg_executable()),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-progress",
        "pipe:1",
        "-nostats",
        "-i",
        str(source_path),
    ]

    if is_video and target_ext in VIDEO_EXTS:
        cmd.extend([
            "-c:v", "copy",
            "-af", af_string,
            "-c:a", "aac",
            "-b:a", quality if quality in QUALITY_OPTIONS else "192k",
        ])
    else:
        cmd.extend(["-vn", "-af", af_string])
        if target_ext in OUTPUT_FORMATS:
            cmd.extend(ffmpeg_args_for(target_ext, quality))
        else:
            cmd.extend(["-codec:a", "libmp3lame", "-b:a", quality if quality in QUALITY_OPTIONS else "192k"])

    cmd.append(str(temp_path))

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        **hidden_subprocess_kwargs(),
    )

    for line in process.stdout:
        if cancellation_requested(cancel_callback):
            stop_process(process)
            remove_partial_output(temp_path)
            raise CancelledError("Operation canceled")
        key, separator, value = line.strip().partition("=")
        if separator != "=" or key != "out_time_ms" or not duration:
            continue
        try:
            elapsed = int(value) / 1_000_000
        except ValueError:
            continue
        percent = max(0, min(99, int((elapsed / duration) * 100)))
        if progress_callback:
            try:
                progress_callback(percent, f"Boosting volume: {percent}%", elapsed, duration)
            except Exception:
                pass

    if cancellation_requested(cancel_callback):
        stop_process(process)
        remove_partial_output(temp_path)
        raise CancelledError("Operation canceled")

    stderr = process.stderr.read() if process.stderr else ""
    return_code = process.wait()

    if return_code != 0:
        remove_partial_output(temp_path)
        raise RuntimeError(f"FFmpeg volume boost failed: {stderr}")

    final_path = finalize_output(temp_path, output_path)
    if progress_callback:
        try:
            progress_callback(100, "Volume boost completed!", duration, duration)
        except Exception:
            pass
    return final_path


def batch_boost_volume(
    media_files,
    output_dir,
    gain_db=6.0,
    output_ext=None,
    anti_clipping=True,
    normalize_peak=False,
    quality="192k",
    enhancement="Off",
    fade_in_sec=0.0,
    fade_out_sec=0.0,
    progress_callback=None,
    cancel_callback=None,
    **kwargs,
):
    if "anti_clip" in kwargs:
        anti_clipping = kwargs.pop("anti_clip")
    if "output_format" in kwargs:
        output_ext = kwargs.pop("output_format")
    if "cancel_check" in kwargs and cancel_callback is None:
        cancel_callback = kwargs.pop("cancel_check")

    total = len(media_files)
    results = []

    for index, media_path in enumerate(media_files):
        if cancellation_requested(cancel_callback):
            raise CancelledError("Operation canceled")

        def _file_prog(pct, msg, cur, dur):
            if progress_callback:
                try:
                    progress_callback(index, total, media_path, pct, msg)
                except TypeError:
                    try:
                        progress_callback(index, total, media_path)
                    except TypeError:
                        progress_callback(pct, msg)

        res = boost_audio_volume(
            source_path=media_path,
            gain_db=gain_db,
            output_dir=output_dir,
            output_ext=output_ext,
            anti_clipping=anti_clipping,
            normalize_peak=normalize_peak,
            quality=quality,
            enhancement=enhancement,
            fade_in_sec=fade_in_sec,
            fade_out_sec=fade_out_sec,
            progress_callback=_file_prog,
            cancel_callback=cancel_callback,
        )
        results.append(res)
        if progress_callback:
            try:
                progress_callback(index + 1, total, media_path, 100, f"Finished: {media_path.name}")
            except TypeError:
                try:
                    progress_callback(index + 1, total, media_path)
                except TypeError:
                    pass

    return results


def batch_export_silence_cut(
    media_files,
    output_dir,
    noise_db=-35.0,
    min_silence_sec=0.5,
    padding_sec=0.15,
    mode="remove",
    speed_factor=4,
    enhancement="Off",
    video_quality="High",
    chosen_ext=None,
    is_audio_only=False,
    progress_callback=None,
    cancel_callback=None,
):
    total = len(media_files)
    results = []
    enh_filter = ffmpeg_audio_filter_str(enhancement)
    ffmpeg_bin = str(ffmpeg_executable())

    for index, media_path in enumerate(media_files):
        if cancellation_requested(cancel_callback):
            raise CancelledError("Operation canceled")

        media_path = Path(media_path)
        is_vid = False if is_audio_only else (has_video_stream(media_path) or (media_path.suffix.lower() in VIDEO_EXTS))

        def _file_prog(pct, cur_s, tot_s):
            if progress_callback:
                try:
                    progress_callback(index, total, media_path, pct)
                except Exception:
                    pass

        tag = "nosilence" if mode == "remove" else ("fastsilence" if mode == "fast_forward" else "gated")
        out_ext = chosen_ext if chosen_ext else media_path.suffix
        out_p = unique_output_path(Path(output_dir) / f"{media_path.stem}_{tag}{out_ext}")

        res = export_silence_cut_media(
            media_path=media_path,
            output_path=out_p,
            output_dir=output_dir,
            keep_intervals=None,
            noise_db=noise_db,
            min_silence_sec=min_silence_sec,
            padding_sec=padding_sec,
            mode=mode,
            speed_factor=speed_factor,
            audio_enhancement_filter=enh_filter,
            video_quality=video_quality,
            has_video=is_vid,
            ffmpeg_exe=ffmpeg_bin,
            cancel_callback=cancel_callback,
            progress_callback=_file_prog,
        )
        results.append(res)
        if progress_callback:
            try:
                progress_callback(index + 1, total, media_path, 100)
            except Exception:
                pass

    return results


def capture_video_snapshot(video_path, timestamp_sec=0.0, output_dir=None, color_config=None):
    """
    Extracts a high-resolution PNG snapshot from `video_path` at `timestamp_sec`,
    optionally applying color grading adjustments.
    """
    from video_studio.color_grading import extract_video_sample_frame, apply_color_to_image, is_color_neutral

    video_path = Path(video_path).resolve()
    if output_dir is None:
        output_dir = video_path.parent / "output"
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = max(0.0, float(timestamp_sec or 0.0))
    ts_label = format_time_label(ts)
    out_png = unique_output_path(output_dir / f"{video_path.stem}_snapshot_{ts_label}.png")

    img = extract_video_sample_frame(
        video_path=video_path,
        timestamp=ts,
        max_size=(3840, 2160),
        ffmpeg_exe=str(ffmpeg_executable()),
    )
    if img is None:
        raise RuntimeError("Could not extract video frame at the selected timestamp.")

    if color_config and isinstance(color_config, dict) and color_config.get("enabled") and not is_color_neutral(color_config):
        img = apply_color_to_image(img, color_config)

    img.save(str(out_png), "PNG")
    return out_png


if __name__ == "__main__":
    main()


