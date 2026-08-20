import re
import shutil
import subprocess
import sys
import os
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


folder = Path.cwd()
INPUT_DIR = folder / "input"
OUTPUT_DIR = folder / "output"
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
QUALITY_OPTIONS = ("128k", "192k", "256k", "320k")
YOUTUBE_AUDIO_FORMAT_ID = "__audio_mp3__"
VIDEO_COMPRESSION_PRESETS = {
    "Small": {
        "label": "Small file",
        "crf": "29",
        "audio_bitrate": "112k",
    },
    "Medium": {
        "label": "Medium file",
        "crf": "26",
        "audio_bitrate": "128k",
    },
    "High": {
        "label": "High quality",
        "crf": "24",
        "audio_bitrate": "160k",
    },
}
VIDEO_RESOLUTION_PRESETS = {
    "Original": {
        "label": "Original size",
        "scale": None,
    },
    "720p": {
        "label": "Limit to 720p",
        "scale": "1280:720",
    },
    "480p": {
        "label": "Limit to 480p",
        "scale": "854:480",
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

    rows[1:] = sorted(rows[1:], key=lambda row: row["height"], reverse=True)
    return {
        "title": info.get("title") or "YouTube video",
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
    else:
        ydl_format = str(format_id) if format_has_audio else f"{format_id}+bestaudio[ext=m4a]/bestaudio/best"
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
    with ydl_module.YoutubeDL(options) as downloader:
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
    compression = (compression or "Medium").strip()
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


def ffmpeg_filter_args(enhancement):
    filters = ENHANCEMENT_PRESETS[normalize_enhancement(enhancement)]
    if not filters:
        return []
    return ["-af", ",".join(filters)]


def cancellation_requested(cancel_callback):
    return bool(cancel_callback and cancel_callback())


def stop_process(process):
    if not process or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


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
    temp_path.replace(final_path)
    return final_path


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
    relative_path = source_path.relative_to(input_dir)
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
            "0",
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
        return finalize_output(temp_path, output_path)
    except RuntimeError as exc:
        print(exc)
        return None


def compress_video(
    source_path,
    input_dir=INPUT_DIR,
    output_dir=OUTPUT_DIR,
    compression="Medium",
    resolution="Original",
    skip_if_exists=False,
    progress_callback=None,
    progress_index=0,
    total_files=1,
    cancel_callback=None,
):
    if cancellation_requested(cancel_callback):
        raise CancelledError("Operation canceled")
    compression = normalize_video_compression(compression)
    resolution = normalize_video_resolution(resolution)
    preset = VIDEO_COMPRESSION_PRESETS[compression]
    resolution_preset = VIDEO_RESOLUTION_PRESETS[resolution]
    output_path = output_path_for(source_path, input_dir, output_dir, ".mp4")
    if same_file_path(source_path, output_path):
        output_path = unique_output_path(output_path.with_name(f"{output_path.stem}_compressed{output_path.suffix}"))

    if skip_if_exists and output_path.exists():
        print(f"Skipping existing file: {output_path.name}")
        if progress_callback:
            progress_callback(progress_index + 1, total_files, source_path, 0)
        return None

    print(f"Compressing video ({preset['label']}, {resolution_preset['label']}): {source_path.name} -> {output_path.name}")

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
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        preset["crf"],
        "-c:a",
        "aac",
        "-b:a",
        preset["audio_bitrate"],
        "-movflags",
        "+faststart",
    ]
    if resolution_preset["scale"]:
        command.extend(["-vf", f"scale={resolution_preset['scale']}:force_original_aspect_ratio=decrease:force_divisible_by=2"])
    command.append(str(temp_path))

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
        print(f"Video compression failed: {source_path}")
        remove_partial_output(temp_path)
        return None

    try:
        return finalize_output(temp_path, output_path)
    except RuntimeError as exc:
        print(exc)
        return None


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
    video_compression="Medium",
    video_resolution="Original",
    video_only=False,
    cancel_callback=None,
):
    output_ext = normalize_output_ext(output_ext)
    quality = normalize_quality(quality)
    enhancement = normalize_enhancement(enhancement)
    video_compression = normalize_video_compression(video_compression)
    video_resolution = normalize_video_resolution(video_resolution)
    input_path = Path(input_dir) if input_dir else INPUT_DIR
    input_root = input_root_for(input_path)
    output_dir = Path(output_dir) if output_dir else input_root / "output"
    if input_path.is_dir():
        input_path.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    if keep_original_format:
        print("Output format: keep original")
        if video_action == "compress_video":
            print(f"Video compression: {VIDEO_COMPRESSION_PRESETS[video_compression]['label']}")
            print(f"Video resolution: {VIDEO_RESOLUTION_PRESETS[video_resolution]['label']}")
        else:
            print("Video inputs will still be extracted to the selected audio format")
    else:
        print(f"Output format: {OUTPUT_FORMATS[output_ext]['label']} ({output_ext})")
        if output_ext in {".mp3", ".m4a"}:
            print(f"Quality: {quality}")
        if video_action == "compress_video":
            print(f"Video compression: {VIDEO_COMPRESSION_PRESETS[video_compression]['label']}")
            print(f"Video resolution: {VIDEO_RESOLUTION_PRESETS[video_resolution]['label']}")
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
        if is_video and video_action == "compress_video":
            output_path = compress_video(
                source_path,
                input_root,
                output_dir,
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


if __name__ == "__main__":
    main()
