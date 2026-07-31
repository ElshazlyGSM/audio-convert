import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path
from urllib.parse import quote, urlparse

import requests
from mutagen.id3 import APIC, ID3, TIT2, TPE1
from mutagen.mp3 import MP3


folder = Path.cwd()
INPUT_DIR = folder / "input"
OUTPUT_DIR = folder / "output"
REFRESH_EXISTING_COVERS = True

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
ARABIC_TO_ENGLISH = str.maketrans(
    {
        "ا": "a",
        "أ": "a",
        "إ": "e",
        "آ": "a",
        "ب": "b",
        "ت": "t",
        "ث": "th",
        "ج": "g",
        "ح": "h",
        "خ": "kh",
        "د": "d",
        "ذ": "z",
        "ر": "r",
        "ز": "z",
        "س": "s",
        "ش": "sh",
        "ص": "s",
        "ض": "d",
        "ط": "t",
        "ظ": "z",
        "ع": "a",
        "غ": "gh",
        "ف": "f",
        "ق": "q",
        "ك": "k",
        "ل": "l",
        "م": "m",
        "ن": "n",
        "ه": "h",
        "ة": "a",
        "و": "w",
        "ؤ": "w",
        "ي": "y",
        "ى": "a",
        "ئ": "y",
        "ء": "",
        "ﻻ": "la",
    }
)
NOISE_PHRASES = [
    "official music video",
    "official video",
    "lyrics video",
    "lyric video",
    "video clip",
    "videoclip",
    "music video",
    "official audio",
    "audio",
    "lyrics",
    "master",
    "version",
    "from",
]
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


def is_ascii_text(value):
    return bool(value) and value == value.encode("ascii", errors="ignore").decode("ascii")


def transliterate_to_ascii(value):
    value = value.translate(ARABIC_TO_ENGLISH)
    value = unicodedata.normalize("NFKD", value)
    return value.encode("ascii", errors="ignore").decode("ascii")


def clean_name_part(value):
    value = transliterate_to_ascii(value)
    value = re.sub(r"[<>:\"/\\|?*]", " ", value)
    value = re.sub(r"[\[\](){}]", " ", value)
    value = re.sub(r"\b(?:19|20)\d{2}\b", " ", value)

    for phrase in NOISE_PHRASES:
        value = re.sub(re.escape(phrase), " ", value, flags=re.IGNORECASE)

    value = re.sub(r"\s+", " ", value).strip(" .-_")
    return value


def title_case_name(value):
    keep_lower = {"and", "the", "of", "el", "al", "w"}
    words = []
    for word in value.split():
        if word.lower() in keep_lower:
            words.append(word.lower())
        elif word.isupper() and len(word) <= 3:
            words.append(word)
        else:
            words.append(word[:1].upper() + word[1:])
    return " ".join(words)


def clean_song_info(file_stem, track_name=None, artist_name=None):
    artist = clean_name_part(artist_name or "")
    title = clean_name_part(track_name or "")

    if artist and title and is_ascii_text(artist) and is_ascii_text(title):
        return title_case_name(artist), title_case_name(title)

    stem = clean_name_part(file_stem.replace("_", " - "))
    parts = [
        part.strip()
        for part in re.split(r"\s+-\s+|\s+-|-\s+|--+", stem)
        if clean_name_part(part)
    ]
    parts = [clean_name_part(part) for part in parts]
    parts = [
        part
        for part in parts
        if part and not part.isdigit() and len(part) > 1
    ]

    if len(parts) >= 2:
        return title_case_name(parts[0]), title_case_name(parts[1])

    fallback = title_case_name(stem or "Unknown Song")
    return "Unknown Artist", fallback


def safe_filename(value):
    value = clean_name_part(value)
    value = re.sub(r"\s+", " ", value).strip(" .-_")
    return value[:160] or "Unknown Artist - Unknown Song"


def rename_output_mp3(mp3_path, track_name=None, artist_name=None):
    artist, title = clean_song_info(mp3_path.stem, track_name, artist_name)
    new_name = safe_filename(f"{artist} - {title}") + ".mp3"
    new_path = mp3_path.with_name(new_name)

    if new_path.name == mp3_path.name:
        return mp3_path

    if new_path.exists():
        new_path.unlink()

    mp3_path.rename(new_path)
    print(f"Renamed to: {new_path.name}")
    return new_path


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
    query = quote(f"{song_name} official song")
    page = safe_get(f"https://www.youtube.com/results?search_query={query}")
    video_match = re.search(r'"videoId":"([^"]+)"', page.text)
    if not video_match:
        return None

    video_id = video_match.group(1)
    for image_url in [
        f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
    ]:
        image = download_image(image_url)
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
        ("iTunes", lambda: find_cover_from_itunes(song_name)),
        ("Bing", lambda: find_cover_from_bing(song_name)),
        ("YouTube", lambda: find_cover_from_youtube(song_name)),
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


def add_cover_to_mp3(mp3_path, cover_data, cover_ext, track_name=None, artist_name=None):
    detected_ext = detect_image_ext(cover_data)
    if detected_ext:
        cover_ext = detected_ext

    audio = MP3(mp3_path, ID3=ID3)

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

    # ID3v2.3 is more compatible with Windows Explorer and many older players.
    audio.save(v2_version=3)

    verify = MP3(mp3_path, ID3=ID3)
    return bool(verify.tags and any(key.startswith("APIC") for key in verify.tags.keys()))


def mp3_has_cover(mp3_path):
    try:
        audio = MP3(mp3_path, ID3=ID3)
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
                print(f"Fixing cover type: {mp3_path.name}")
                frame.mime = expected_mime
                fixed_cover = True

        if fixed_cover:
            audio.save(v2_version=3)

        return any(key.startswith("APIC") for key in audio.tags.keys())
    except Exception as exc:
        print(f"Could not read MP3 tags: {mp3_path} ({exc})")
        return False


def add_missing_cover(mp3_path, force_refresh=False):
    if not force_refresh and mp3_has_cover(mp3_path):
        print(f"Cover already exists: {mp3_path.name}")
        return None, None

    print(f"Searching cover for {mp3_path.stem}")
    cover = find_web_cover(mp3_path.stem)

    if not cover:
        print("No Cover Found")
        return None, None

    cover_data, cover_ext, track_name, artist_name = cover
    if add_cover_to_mp3(mp3_path, cover_data, cover_ext, track_name, artist_name):
        print("Cover Added")
        return track_name, artist_name
    else:
        print("Cover write failed")
        return None, None


def output_path_for(source_path, suffix=None):
    relative_path = source_path.relative_to(INPUT_DIR)
    if suffix:
        relative_path = relative_path.with_suffix(suffix)

    output_path = OUTPUT_DIR / relative_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


for m4a in INPUT_DIR.rglob("*.m4a"):
    name = m4a.stem
    mp3 = output_path_for(m4a, ".mp3")

    print(f"Converting {name}")

    converted = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(m4a),
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "160k",
            str(mp3),
        ],
        check=False,
    )

    if converted.returncode != 0:
        print(f"Conversion failed: {m4a}")
        continue

    try:
        track_name, artist_name = add_missing_cover(mp3, force_refresh=True)
        rename_output_mp3(mp3, track_name, artist_name)
    except Exception as exc:
        print(f"Cover error: {exc}")


for source_mp3 in INPUT_DIR.rglob("*.mp3"):
    mp3 = output_path_for(source_mp3)
    shutil.copy2(source_mp3, mp3)

    try:
        track_name, artist_name = add_missing_cover(mp3, force_refresh=REFRESH_EXISTING_COVERS)
        rename_output_mp3(mp3, track_name, artist_name)
    except Exception as exc:
        print(f"Cover error: {mp3} ({exc})")

print("Done")
