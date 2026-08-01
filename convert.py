import re
import shutil
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from urllib.parse import quote, urlparse

import requests
from PIL import Image
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, ID3, TIT2, TPE1
from mutagen.mp4 import MP4, MP4Cover
from mutagen.mp3 import MP3


folder = Path.cwd()
INPUT_DIR = folder / "input"
OUTPUT_DIR = folder / "output"
REFRESH_EXISTING_COVERS = True
AUDIO_EXTS = {".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus", ".wma"}
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
        return discovered

    raise FileNotFoundError("ffmpeg.exe was not found")


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


def convert_audio(
    source_path,
    output_ext,
    input_dir=INPUT_DIR,
    output_dir=OUTPUT_DIR,
    quality="192k",
    skip_if_exists=False,
):
    output_path = output_path_for(source_path, input_dir, output_dir, output_ext)

    if skip_if_exists and output_path.exists():
        print(f"Skipping existing file: {output_path.name}")
        return None

    if source_path.suffix.lower() == output_ext:
        print(f"Copying {source_path.name}")
        shutil.copy2(source_path, output_path)
        return output_path

    print(f"Converting {source_path.name} -> {output_path.name}")
    converted = subprocess.run(
        [
            str(ffmpeg_executable()),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source_path),
            *ffmpeg_args_for(output_ext, quality),
            str(output_path),
        ],
        check=False,
    )

    if converted.returncode != 0:
        print(f"Conversion failed: {source_path}")
        return None

    return output_path


def iter_input_audio(input_dir=INPUT_DIR, exclude_dir=None):
    exclude_dir = Path(exclude_dir).resolve() if exclude_dir else None
    for source_path in input_dir.rglob("*"):
        if exclude_dir and source_path.resolve().is_relative_to(exclude_dir):
            continue
        if source_path.is_file() and source_path.suffix.lower() in AUDIO_EXTS:
            yield source_path


def collect_audio_files(input_path=INPUT_DIR, exclude_dir=None):
    input_path = Path(input_path)
    if input_path.is_file():
        return [input_path] if input_path.suffix.lower() in AUDIO_EXTS else []
    if input_path.is_dir():
        return list(iter_input_audio(input_path, exclude_dir))
    return []


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
):
    output_ext = normalize_output_ext(output_ext)
    quality = normalize_quality(quality)
    input_path = Path(input_dir) if input_dir else INPUT_DIR
    input_root = input_root_for(input_path)
    output_dir = Path(output_dir) if output_dir else input_root / "output"
    if input_path.is_dir():
        input_path.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    if keep_original_format:
        print("Output format: keep original")
    else:
        print(f"Output format: {OUTPUT_FORMATS[output_ext]['label']} ({output_ext})")
        if output_ext in {".mp3", ".m4a"}:
            print(f"Quality: {quality}")
    print(f"Input: {input_path}")
    print(f"Output folder: {output_dir}")
    audio_files = collect_audio_files(input_path, output_dir)
    if not audio_files:
        print("No supported audio files found")
        return

    total = len(audio_files)
    if progress_callback:
        progress_callback(0, total, None)

    for index, source_path in enumerate(audio_files, start=1):
        current_ext = source_path.suffix.lower() if keep_original_format else output_ext
        if current_ext not in OUTPUT_FORMATS:
            print(f"Skipping unsupported output format: {source_path.name}")
            if progress_callback:
                progress_callback(index, total, source_path)
            continue

        output_path = convert_audio(
            source_path,
            current_ext,
            input_root,
            output_dir,
            quality=quality,
            skip_if_exists=skip_if_exists,
        )
        if not output_path:
            if progress_callback:
                progress_callback(index, total, source_path)
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
            progress_callback(index, total, source_path)

    print("Done")


if __name__ == "__main__":
    main()
