import json
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from io import BytesIO
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk


APP_DIR = Path(__file__).resolve().parent
os.chdir(APP_DIR)
DEFAULT_OUTPUT_DIR = Path.home() / "Music" / "Media Audio Studio"
SETTINGS_PATH = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Media Audio Studio" / "settings.json"

VLC_DIRS = [
    Path(r"C:\Program Files\VideoLAN\VLC"),
    Path(r"C:\Program Files (x86)\VideoLAN\VLC"),
]
for vlc_dir in VLC_DIRS:
    if vlc_dir.exists():
        os.environ["PATH"] = f"{vlc_dir}{os.pathsep}{os.environ.get('PATH', '')}"
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(vlc_dir))
        break

try:
    import vlc  # noqa: E402
except Exception:
    vlc = None

import convert  # noqa: E402


TRANSLATIONS = {
    "English": {
        "app_title": "Media Audio Studio",
        "subtitle": "Choose one audio/video file or a folder, pick the output format, then run conversion with cover art.",
        "language": "Language",
        "choose_file": "Choose File",
        "choose_folder": "Choose Folder",
        "output": "Output",
        "source_group": "Source",
        "conversion_group": "Conversion and video compression",
        "cover_group": "Cover search",
        "youtube_group": "YouTube download",
        "tools_group": "Player and trim",
        "media_player_group": "Media player",
        "log_group": "Log",
        "format": "Format",
        "quality": "Quality",
        "video_only_group": "Video compression only",
        "video_count": "{count} video files",
        "compress_videos": "Compress Video",
        "video_compression": "Video size",
        "video_resolution": "Resolution",
        "keep_original": "Keep original format",
        "skip_existing": "Skip if output exists",
        "preview_cover": "Preview cover",
        "open_output_done": "Open output when done",
        "enhance": "Enhance",
        "manual_search": "Manual search",
        "use_custom_cover": "Use custom cover",
        "choose_image": "Choose Image",
        "youtube_url": "YouTube URL",
        "fetch_qualities": "Get Qualities",
        "download_youtube": "Download",
        "youtube_quality": "YouTube quality",
        "youtube_size": "Size: {size}",
        "youtube_save_to": "Save to: {path}",
        "choose_download_folder": "Choose Folder",
        "paste": "Paste",
        "copy": "Copy",
        "cut": "Cut",
        "select_all": "Select All",
        "youtube_url_required": "Enter a YouTube link first.",
        "youtube_fetching": "Getting YouTube qualities...",
        "youtube_downloading": "Downloading from YouTube...",
        "youtube_ready": "Choose a quality, then download.",
        "youtube_no_formats": "No downloadable formats were found.",
        "run": "Convert Audio",
        "cancel": "Cancel",
        "canceling": "Canceling...",
        "canceled": "Canceled",
        "close_running": "An operation is running. Stop it and close?",
        "play_file": "▶ Play",
        "pause_file": "Pause",
        "stop_file": "■ Stop",
        "back_10": "-10s",
        "forward_10": "+10s",
        "speed": "Speed",
        "volume": "Volume",
        "vlc_missing": "Install VLC Media Player to play files inside the app.",
        "open_source": "Open Source",
        "open_output": "Open Output",
        "timeline": "Timeline",
        "mark_start": "Mark Start",
        "mark_end": "Mark End",
        "duration_unknown": "Duration: unknown",
        "duration_label": "Duration: {duration}",
        "trim_start": "Start",
        "trim_end": "End",
        "trim_selected": "Trim Selected",
        "choose_single_trim": "Choose one audio/video file first.",
        "trim_times_required": "Enter start and end times, for example 00:30 and 01:10.",
        "trimming": "Trimming...",
        "source_empty": "No file or folder selected",
        "output_empty": "Output folder will be created after selecting a source",
        "cover_empty": "No custom cover selected",
        "choose_start": "Choose a file or folder to start",
        "ready": "Ready",
        "running": "Running...",
        "done": "Done",
        "failed": "Failed",
        "no_media": "No supported audio or video files found in this source",
        "choose_cover_first": "Choose a cover image first.",
        "error_check_log": "Something went wrong. Check the log.",
        "files_ready": "Files are ready in the output folder.",
        "custom_cover_selected": "Custom cover selected",
        "starting": "Starting conversion as {mode}...\n",
        "starting_video_only": "Starting video compression only...\n",
        "no_videos": "No supported video files found in this source",
        "processed": "{current} / {total} files processed",
        "progress_detail": "{current} / {total} files | current {file_percent}% | done {overall_percent}% | left {remaining_percent}% | ETA {eta}",
        "estimating": "estimating...",
        "media_count": "{count} media files",
        "folder_title": "Choose folder with audio/video files",
        "file_title": "Choose one audio/video file",
        "cover_title": "Choose cover image",
        "media_files": "Media files",
        "audio_files": "Audio files",
        "video_files": "Video files",
        "image_files": "Image files",
        "all_files": "All files",
        "preview_title": "Preview Cover",
        "search": "Search",
        "use_cover": "Use Cover",
        "skip_cover": "Skip Cover",
        "preview_error": "Could not preview image: {error}",
        "mode_original": "original format",
    },
    "العربية": {
        "app_title": "استوديو الصوت والوسائط",
        "subtitle": "اختار ملف صوت/فيديو أو فولدر، حدد صيغة الخروج، وبعدها شغل التحويل مع صورة الغلاف.",
        "language": "اللغة",
        "choose_file": "اختيار ملف",
        "choose_folder": "اختيار فولدر",
        "output": "الخروج",
        "source_group": "المصدر",
        "conversion_group": "التحويل وضغط الفيديو",
        "cover_group": "بحث الغلاف",
        "tools_group": "التشغيل والقص",
        "media_player_group": "مشغل الميديا",
        "log_group": "السجل",
        "format": "الصيغة",
        "quality": "الجودة",
        "video_only_group": "ضغط الفيديوهات فقط",
        "video_count": "{count} فيديو",
        "compress_videos": "ضغط الفيديو",
        "video_compression": "حجم الفيديو",
        "video_resolution": "الأبعاد",
        "keep_original": "الحفاظ على نفس الصيغة",
        "skip_existing": "تخطي الموجود",
        "preview_cover": "معاينة الصورة",
        "open_output_done": "فتح الخرج بعد الانتهاء",
        "enhance": "تحسين الصوت",
        "manual_search": "بحث يدوي",
        "use_custom_cover": "استخدام صورة من الجهاز",
        "choose_image": "اختيار صورة",
        "run": "تحويل الصوت",
        "cancel": "إيقاف",
        "canceling": "جاري الإيقاف...",
        "canceled": "تم الإيقاف",
        "close_running": "في عملية شغالة. أوقفها وأقفل البرنامج؟",
        "play_file": "▶ تشغيل",
        "pause_file": "إيقاف مؤقت",
        "stop_file": "■ إيقاف",
        "back_10": "-10ث",
        "forward_10": "+10ث",
        "speed": "السرعة",
        "volume": "الصوت",
        "vlc_missing": "ثبت VLC Media Player لتشغيل الملفات داخل البرنامج.",
        "open_source": "فتح المصدر",
        "open_output": "فتح الخرج",
        "timeline": "الشريط الزمني",
        "mark_start": "تحديد البداية",
        "mark_end": "تحديد النهاية",
        "duration_unknown": "المدة: غير معروفة",
        "duration_label": "المدة: {duration}",
        "trim_start": "البداية",
        "trim_end": "النهاية",
        "trim_selected": "قص الملف",
        "choose_single_trim": "اختار ملف صوت/فيديو واحد أولا.",
        "trim_times_required": "اكتب وقت البداية والنهاية، مثال 00:30 و 01:10.",
        "trimming": "جاري القص...",
        "source_empty": "لم يتم اختيار ملف أو فولدر",
        "output_empty": "سيتم إنشاء فولدر الخرج بعد اختيار المصدر",
        "cover_empty": "لم يتم اختيار صورة",
        "choose_start": "اختار ملف أو فولدر للبدء",
        "ready": "جاهز",
        "running": "جاري التشغيل...",
        "done": "تم",
        "failed": "فشل",
        "no_media": "لا توجد ملفات صوت أو فيديو مدعومة في هذا المصدر",
        "choose_cover_first": "اختار صورة الغلاف أولا.",
        "error_check_log": "حدث خطأ. راجع السجل.",
        "files_ready": "الملفات جاهزة في فولدر الخرج.",
        "custom_cover_selected": "تم اختيار صورة الغلاف",
        "starting": "بدء التحويل إلى {mode}...\n",
        "starting_video_only": "بدء ضغط الفيديوهات فقط...\n",
        "no_videos": "لا توجد ملفات فيديو مدعومة في هذا المصدر",
        "processed": "تمت معالجة {current} / {total} ملفات",
        "progress_detail": "{current} / {total} ملفات | الحالي {file_percent}% | خلص {overall_percent}% | فاضل {remaining_percent}% | المتبقي {eta}",
        "estimating": "جارى الحساب...",
        "media_count": "{count} ملف",
        "folder_title": "اختيار فولدر يحتوي على ملفات صوت/فيديو",
        "file_title": "اختيار ملف صوت/فيديو",
        "cover_title": "اختيار صورة الغلاف",
        "media_files": "ملفات الصوت والفيديو",
        "audio_files": "ملفات الصوت",
        "video_files": "ملفات الفيديو",
        "image_files": "ملفات الصور",
        "all_files": "كل الملفات",
        "preview_title": "معاينة الغلاف",
        "search": "بحث",
        "use_cover": "استخدام الصورة",
        "skip_cover": "تخطي الصورة",
        "preview_error": "تعذرت معاينة الصورة: {error}",
        "mode_original": "نفس الصيغة",
    },
}

ENHANCEMENT_LABELS = {
    "English": {
        "Off": "Off",
        "Normalize volume": "Normalize volume",
        "Louder and clearer": "Louder and clearer",
        "Noise reduction": "Noise reduction",
        "Strong noise cleanup": "Strong noise cleanup",
        "Podcast voice": "Podcast voice",
        "Voice cleanup": "Voice cleanup",
        "Reduce echo": "Reduce echo",
        "Auto clean all": "Auto clean all",
    },
    "العربية": {
        "Off": "إيقاف",
        "Normalize volume": "تظبيط مستوى الصوت",
        "Louder and clearer": "أعلى وأوضح",
        "Noise reduction": "تقليل الضوضاء",
        "Strong noise cleanup": "تنضيف ضوضاء قوي",
        "Podcast voice": "صوت بودكاست",
        "Voice cleanup": "تنظيف صوت الكلام",
        "Reduce echo": "تقليل الصدى",
        "Auto clean all": "تصليح الكل مرة واحدة",
    },
}

VIDEO_COMPRESSION_LABELS = {
    "English": {
        "Small": "Small",
        "Medium": "Medium",
        "High": "High quality",
    },
    "العربية": {
        "Small": "صغير",
        "Medium": "متوسط",
        "High": "جودة أعلى",
    },
}

VIDEO_RESOLUTION_LABELS = {
    "English": {
        "Original": "Original",
        "720p": "720p",
        "480p": "480p",
    },
    "Ø§Ù„Ø¹Ø±Ø¨ÙŠØ©": {
        "Original": "الأصلية",
        "720p": "720p",
        "480p": "480p",
    },
}


class QueueWriter:
    def __init__(self, messages):
        self.messages = messages

    def write(self, text):
        if text:
            self.messages.put(text)

    def flush(self):
        pass


class SongCoverApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Media Audio Studio")
        self.geometry("1120x720")
        self.minsize(980, 640)

        self.messages = queue.Queue()
        self.worker = None
        self.cancel_event = threading.Event()
        self.active_operation = None
        self.active_operation_button = None
        self.input_path = None
        self.output_dir = None
        self.media_files = []
        self.media_duration = 0
        self.player_process = None
        self.vlc_instance = None
        self.media_player = None
        self.loaded_media_path = None
        self.play_started_at = None
        self.play_base_seconds = 0
        self.playback_tick = None
        self.timeline_dragging = False
        self.was_playing_before_drag = False
        self.video_expanded = False
        self.fullscreen_window = None
        self.fullscreen_surface = None
        self.fullscreen_grid = None
        self.fullscreen_controls_hidden = False
        self.run_started_at = None
        self.settings = self._load_settings()
        self.last_media_dir = Path(self.settings.get("last_media_dir") or APP_DIR)
        self.last_cover_dir = Path(self.settings.get("last_cover_dir") or self.last_media_dir)
        language = self.settings.get("language")
        if language not in TRANSLATIONS:
            language = "English"
        quality = self.settings.get("quality")
        if quality not in convert.QUALITY_OPTIONS:
            quality = "192k"
        speed = self.settings.get("speed")
        if speed not in {"0.50x", "0.75x", "1.00x", "1.25x", "1.50x", "2.00x"}:
            speed = "1.00x"
        video_compression = self.settings.get("video_compression")
        if video_compression not in convert.VIDEO_COMPRESSION_PRESETS:
            video_compression = "Medium"
        video_resolution = self.settings.get("video_resolution")
        if video_resolution not in convert.VIDEO_RESOLUTION_PRESETS:
            video_resolution = "Original"

        self.status_var = tk.StringVar()
        self.source_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.count_var = tk.StringVar()
        self.video_count_var = tk.StringVar()
        self.video_estimate_var = tk.StringVar(value="")
        self.progress_var = tk.StringVar()
        self.manual_search_var = tk.StringVar(value="")
        self.youtube_url_var = tk.StringVar(value="")
        self.youtube_quality_var = tk.StringVar(value="")
        self.youtube_detail_var = tk.StringVar()
        self.youtube_output_dir_path = Path(self.settings.get("youtube_output_dir") or DEFAULT_OUTPUT_DIR)
        self.youtube_formats = []
        self.trim_start_var = tk.StringVar(value="")
        self.trim_end_var = tk.StringVar(value="")
        self.timeline_var = tk.DoubleVar(value=0)
        self.timeline_text_var = tk.StringVar(value="00:00 / 00:00")
        self.speed_var = tk.StringVar(value=speed)
        self.volume_var = tk.IntVar(value=100)
        self.quality_var = tk.StringVar(value=quality)
        self.language_var = tk.StringVar(value=language)
        self.video_compression_key = video_compression
        self.video_compression_var = tk.StringVar(value=video_compression)
        self.video_resolution_key = video_resolution
        self.video_resolution_var = tk.StringVar(value=video_resolution)
        self.preview_var = tk.BooleanVar(value=True)
        self.skip_existing_var = tk.BooleanVar(value=True)
        self.keep_original_var = tk.BooleanVar(value=False)
        self.open_output_var = tk.BooleanVar(value=True)
        self.custom_cover_var = tk.BooleanVar(value=False)
        self.custom_cover_path = None
        self.custom_cover_text_var = tk.StringVar()
        self.enhancement_key = "Off"
        self.enhancement_var = tk.StringVar(value="Off")
        self.format_options = [
            f"{ext} - {info['label']}" for ext, info in convert.OUTPUT_FORMATS.items()
        ]
        self.output_format_var = tk.StringVar(value=".mp3 - MP3")
        self.busy_widgets = []
        self.i18n_widgets = {}

        self._build_ui()
        self.youtube_url_var.trace_add("write", self._youtube_url_changed)
        self._apply_language()
        self._refresh_youtube_details()
        self._update_run_state()
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self.after(100, self._drain_messages)

    def _load_settings(self):
        try:
            if SETTINGS_PATH.exists():
                return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _save_settings(self):
        self.settings["last_media_dir"] = str(self.last_media_dir)
        self.settings["last_cover_dir"] = str(self.last_cover_dir)
        self.settings["youtube_output_dir"] = str(self.youtube_output_dir_path)
        self.settings["language"] = self.language_var.get()
        self.settings["quality"] = self.quality_var.get()
        self.settings["speed"] = self.speed_var.get()
        self.settings["video_compression"] = self.video_compression_key
        self.settings["video_resolution"] = self.video_resolution_key
        try:
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS_PATH.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _dialog_dir(self, path):
        path = Path(path or APP_DIR)
        if path.is_file():
            path = path.parent
        return str(path if path.exists() else APP_DIR)

    def text(self, key, **kwargs):
        arabic_youtube_text = {
            "youtube_group": "\u062a\u062d\u0645\u064a\u0644 \u0645\u0646 \u064a\u0648\u062a\u064a\u0648\u0628",
            "youtube_url": "\u0631\u0627\u0628\u0637 \u064a\u0648\u062a\u064a\u0648\u0628",
            "fetch_qualities": "\u062c\u0644\u0628 \u0627\u0644\u062c\u0648\u062f\u0627\u062a",
            "download_youtube": "\u062a\u062d\u0645\u064a\u0644",
            "youtube_quality": "\u062c\u0648\u062f\u0629 \u064a\u0648\u062a\u064a\u0648\u0628",
            "youtube_size": "\u0627\u0644\u062d\u062c\u0645: {size}",
            "youtube_save_to": "\u0645\u0643\u0627\u0646 \u0627\u0644\u062d\u0641\u0638: {path}",
            "choose_download_folder": "\u0627\u062e\u062a\u0631 \u0641\u0648\u0644\u062f\u0631",
            "paste": "\u0644\u0635\u0642",
            "copy": "\u0646\u0633\u062e",
            "cut": "\u0642\u0635",
            "select_all": "\u062a\u062d\u062f\u064a\u062f \u0627\u0644\u0643\u0644",
            "youtube_url_required": "\u0627\u0643\u062a\u0628 \u0631\u0627\u0628\u0637 \u064a\u0648\u062a\u064a\u0648\u0628 \u0627\u0644\u0623\u0648\u0644.",
            "youtube_fetching": "\u062c\u0627\u0631\u064a \u062c\u0644\u0628 \u062c\u0648\u062f\u0627\u062a \u064a\u0648\u062a\u064a\u0648\u0628...",
            "youtube_downloading": "\u062c\u0627\u0631\u064a \u0627\u0644\u062a\u062d\u0645\u064a\u0644 \u0645\u0646 \u064a\u0648\u062a\u064a\u0648\u0628...",
            "youtube_ready": "\u0627\u062e\u062a\u0627\u0631 \u0627\u0644\u062c\u0648\u062f\u0629 \u062b\u0645 \u0627\u0628\u062f\u0623 \u0627\u0644\u062a\u062d\u0645\u064a\u0644.",
            "youtube_no_formats": "\u0644\u0645 \u064a\u062a\u0645 \u0627\u0644\u0639\u062b\u0648\u0631 \u0639\u0644\u0649 \u062c\u0648\u062f\u0627\u062a \u0642\u0627\u0628\u0644\u0629 \u0644\u0644\u062a\u062d\u0645\u064a\u0644.",
        }
        if self.language_var.get() != "English" and key in arabic_youtube_text:
            value = arabic_youtube_text[key]
        else:
            value = TRANSLATIONS[self.language_var.get()].get(key, TRANSLATIONS["English"][key])
        return value.format(**kwargs) if kwargs else value

    def _build_ui(self):
        style = ttk.Style(self)
        style.configure("Player.TButton", font=("Segoe UI Symbol", 9), padding=(3, 1))
        style.configure("PrimaryPlayer.TButton", font=("Segoe UI Symbol", 10, "bold"), padding=(4, 1))

        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(6, weight=1)

        header = ttk.Frame(self, padding=(16, 14, 16, 8))
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.columnconfigure(0, weight=1)

        self.i18n_widgets["title"] = ttk.Label(header, font=("Segoe UI", 16, "bold"))
        self.i18n_widgets["title"].grid(row=0, column=0, sticky="w")

        language_box = ttk.Frame(header)
        language_box.grid(row=0, column=1, sticky="e")
        self.i18n_widgets["language_label"] = ttk.Label(language_box)
        self.i18n_widgets["language_label"].grid(row=0, column=0, padx=(0, 8), sticky="e")
        self.language_combo = ttk.Combobox(
            language_box,
            textvariable=self.language_var,
            values=list(TRANSLATIONS),
            state="readonly",
            width=10,
        )
        self.language_combo.grid(row=0, column=1, sticky="e")
        self.language_combo.bind("<<ComboboxSelected>>", self._language_changed)

        self.i18n_widgets["subtitle"] = ttk.Label(header)
        self.i18n_widgets["subtitle"].grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        source_panel = ttk.LabelFrame(self, padding=(12, 8, 12, 10))
        source_panel.grid(row=1, column=0, sticky="ew")
        source_panel.columnconfigure(2, weight=1)
        self.i18n_widgets["source_group"] = source_panel

        self.choose_file_button = ttk.Button(source_panel, command=self.choose_input_file)
        self.choose_file_button.grid(row=0, column=0, sticky="w")
        self.choose_folder_button = ttk.Button(source_panel, command=self.choose_input_folder)
        self.choose_folder_button.grid(row=0, column=1, padx=(8, 0), sticky="w")
        ttk.Label(source_panel, textvariable=self.source_var).grid(row=0, column=2, padx=(10, 0), sticky="ew")

        self.i18n_widgets["output_label"] = ttk.Label(source_panel)
        self.i18n_widgets["output_label"].grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Label(source_panel, textvariable=self.output_var).grid(row=1, column=2, padx=(10, 0), pady=(8, 0), sticky="ew")

        options = ttk.LabelFrame(self, padding=(12, 8, 12, 10))
        options.grid(row=2, column=0, sticky="ew")
        options.columnconfigure(6, weight=1)
        self.i18n_widgets["conversion_group"] = options

        self.i18n_widgets["format_label"] = ttk.Label(options)
        self.i18n_widgets["format_label"].grid(row=0, column=0, sticky="w")
        self.format_combo = ttk.Combobox(options, textvariable=self.output_format_var, values=self.format_options, state="readonly", width=14)
        self.format_combo.grid(row=0, column=1, padx=(8, 12), sticky="w")

        self.i18n_widgets["quality_label"] = ttk.Label(options)
        self.i18n_widgets["quality_label"].grid(row=0, column=2, sticky="w")
        self.quality_combo = ttk.Combobox(options, textvariable=self.quality_var, values=convert.QUALITY_OPTIONS, state="readonly", width=8)
        self.quality_combo.grid(row=0, column=3, padx=(8, 12), sticky="w")
        self.quality_combo.bind("<<ComboboxSelected>>", lambda _event: self._save_settings())

        self.run_button = ttk.Button(options, command=self.start_conversion, width=13)
        self.run_button.grid(row=0, column=4, padx=(4, 0), sticky="w")

        self.keep_original_check = ttk.Checkbutton(options, variable=self.keep_original_var, command=self._sync_option_state)
        self.keep_original_check.grid(row=1, column=0, pady=(8, 0), sticky="w")
        self.skip_existing_check = ttk.Checkbutton(options, variable=self.skip_existing_var)
        self.skip_existing_check.grid(row=1, column=1, columnspan=2, padx=(8, 12), pady=(8, 0), sticky="w")
        self.preview_check = ttk.Checkbutton(options, variable=self.preview_var)
        self.preview_check.grid(row=1, column=3, padx=(0, 12), pady=(8, 0), sticky="w")
        self.open_output_check = ttk.Checkbutton(options, variable=self.open_output_var)
        self.open_output_check.grid(row=2, column=3, columnspan=3, pady=(8, 0), sticky="w")

        self.i18n_widgets["enhance_label"] = ttk.Label(options)
        self.i18n_widgets["enhance_label"].grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.enhancement_combo = ttk.Combobox(
            options,
            textvariable=self.enhancement_var,
            state="readonly",
            width=18,
        )
        self.enhancement_combo.grid(row=2, column=1, columnspan=2, padx=(8, 12), pady=(8, 0), sticky="w")
        self.enhancement_combo.bind("<<ComboboxSelected>>", lambda _event: self._remember_enhancement_key())

        video_panel = ttk.LabelFrame(options, padding=(10, 8, 10, 10))
        video_panel.grid(row=3, column=0, columnspan=7, sticky="ew", pady=(12, 0))
        video_panel.columnconfigure(5, weight=1)
        self.i18n_widgets["video_only_group"] = video_panel

        ttk.Label(video_panel, textvariable=self.video_count_var).grid(row=0, column=0, sticky="w")
        self.i18n_widgets["video_compression_label"] = ttk.Label(video_panel)
        self.i18n_widgets["video_compression_label"].grid(row=0, column=1, padx=(16, 0), sticky="w")
        self.video_compression_combo = ttk.Combobox(
            video_panel,
            textvariable=self.video_compression_var,
            state="readonly",
            width=14,
        )
        self.video_compression_combo.grid(row=0, column=2, padx=(8, 12), sticky="w")
        self.video_compression_combo.bind("<<ComboboxSelected>>", self._video_compression_changed)

        self.i18n_widgets["video_resolution_label"] = ttk.Label(video_panel)
        self.i18n_widgets["video_resolution_label"].grid(row=0, column=3, padx=(4, 0), sticky="w")
        self.video_resolution_combo = ttk.Combobox(
            video_panel,
            textvariable=self.video_resolution_var,
            state="readonly",
            width=10,
        )
        self.video_resolution_combo.grid(row=0, column=4, padx=(8, 12), sticky="w")
        self.video_resolution_combo.bind("<<ComboboxSelected>>", self._video_resolution_changed)

        self.compress_video_button = ttk.Button(
            video_panel,
            command=self.start_video_compression,
            style="Player.TButton",
            width=18,
        )
        self.compress_video_button.grid(row=1, column=1, columnspan=2, padx=(16, 8), pady=(8, 0), sticky="ew")
        ttk.Label(video_panel, textvariable=self.video_estimate_var).grid(row=1, column=3, columnspan=3, padx=(4, 0), pady=(8, 0), sticky="w")

        player_panel = ttk.LabelFrame(self, padding=(6, 6, 6, 8))
        player_panel.grid(row=1, column=1, rowspan=3, padx=(8, 16), pady=(0, 0), sticky="nsew")
        player_panel.columnconfigure(0, weight=1)
        player_panel.rowconfigure(0, weight=1)
        self.i18n_widgets["media_player_group"] = player_panel

        self.video_surface = tk.Frame(player_panel, bg="black", height=220)
        self.video_surface.grid(row=0, column=0, sticky="nsew")
        self.video_surface.grid_propagate(False)

        player_timeline_row = ttk.Frame(player_panel)
        player_timeline_row.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        player_timeline_row.columnconfigure(1, weight=1)
        self.i18n_widgets["timeline_label"] = ttk.Label(player_timeline_row)
        self.i18n_widgets["timeline_label"].grid(row=0, column=0, sticky="w")
        self.timeline_scale = ttk.Scale(
            player_timeline_row,
            variable=self.timeline_var,
            from_=0,
            to=0,
            orient="horizontal",
            command=self._timeline_dragged,
        )
        self.timeline_scale.grid(row=0, column=1, padx=(8, 0), sticky="ew")
        self.timeline_scale.bind("<ButtonPress-1>", self._timeline_press)
        self.timeline_scale.bind("<ButtonRelease-1>", self._timeline_release)
        ttk.Label(player_timeline_row, textvariable=self.timeline_text_var).grid(row=0, column=2, padx=(8, 0), sticky="e")

        media_controls = ttk.Frame(player_panel)
        media_controls.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        media_controls.columnconfigure(15, weight=1)

        self.play_button = ttk.Button(media_controls, command=self.toggle_play_pause, style="PrimaryPlayer.TButton", width=3)
        self.play_button.grid(row=0, column=0, sticky="w")
        self.pause_button = ttk.Button(media_controls, command=self.pause_playback, style="Player.TButton", width=3)
        self.stop_button = ttk.Button(media_controls, command=self.stop_playback, style="Player.TButton", width=3)
        self.stop_button.grid(row=0, column=1, padx=(4, 0), sticky="w")
        ttk.Separator(media_controls, orient="vertical").grid(row=0, column=2, padx=8, sticky="ns")
        self.previous_button = ttk.Button(media_controls, command=self.seek_to_start, style="Player.TButton", width=3)
        self.previous_button.grid(row=0, column=3, sticky="w")
        self.back_button = ttk.Button(media_controls, command=lambda: self.seek_relative(-10), style="Player.TButton", width=5)
        self.back_button.grid(row=0, column=4, padx=(2, 0), sticky="w")
        self.forward_button = ttk.Button(media_controls, command=lambda: self.seek_relative(10), style="Player.TButton", width=5)
        self.forward_button.grid(row=0, column=5, padx=(2, 0), sticky="w")
        self.next_button = ttk.Button(media_controls, command=self.seek_to_end, style="Player.TButton", width=3)
        self.next_button.grid(row=0, column=6, padx=(2, 0), sticky="w")
        ttk.Separator(media_controls, orient="vertical").grid(row=0, column=7, padx=8, sticky="ns")
        self.expand_video_button = ttk.Button(media_controls, command=self.toggle_video_size, style="Player.TButton", width=3)
        self.expand_video_button.grid(row=0, column=8, sticky="w")
        ttk.Separator(media_controls, orient="vertical").grid(row=0, column=9, padx=8, sticky="ns")
        self.i18n_widgets["speed_label"] = ttk.Label(media_controls)
        self.i18n_widgets["speed_label"].grid(row=0, column=10, sticky="w")
        self.speed_combo = ttk.Combobox(
            media_controls,
            textvariable=self.speed_var,
            values=("0.50x", "0.75x", "1.00x", "1.25x", "1.50x", "2.00x"),
            state="readonly",
            width=8,
        )
        self.speed_combo.grid(row=0, column=11, padx=(6, 0), sticky="w")
        self.speed_combo.bind("<<ComboboxSelected>>", self._speed_changed)
        ttk.Separator(media_controls, orient="vertical").grid(row=0, column=12, padx=8, sticky="ns")
        self.i18n_widgets["volume_label"] = ttk.Label(media_controls)
        self.i18n_widgets["volume_label"].grid(row=0, column=13, sticky="e")
        self.volume_scale = ttk.Scale(
            media_controls,
            variable=self.volume_var,
            from_=0,
            to=100,
            orient="horizontal",
            command=self.apply_volume,
        )
        self.volume_scale.grid(row=0, column=15, padx=(6, 0), sticky="ew")

        search_panel = ttk.LabelFrame(self, padding=(12, 8, 12, 10))
        search_panel.grid(row=3, column=0, sticky="ew")
        search_panel.columnconfigure(1, weight=1)
        self.i18n_widgets["cover_group"] = search_panel

        self.i18n_widgets["manual_search_label"] = ttk.Label(search_panel)
        self.i18n_widgets["manual_search_label"].grid(row=0, column=0, sticky="w")
        self.manual_search_entry = ttk.Entry(search_panel, textvariable=self.manual_search_var)
        self.manual_search_entry.grid(row=0, column=1, padx=(8, 0), sticky="ew")
        self._attach_entry_context_menu(self.manual_search_entry)

        self.custom_cover_check = ttk.Checkbutton(search_panel, variable=self.custom_cover_var, command=self._sync_option_state)
        self.custom_cover_check.grid(row=1, column=0, pady=(8, 0), sticky="w")

        custom_cover_row = ttk.Frame(search_panel)
        custom_cover_row.grid(row=1, column=1, padx=(8, 0), pady=(8, 0), sticky="ew")
        custom_cover_row.columnconfigure(1, weight=1)

        self.choose_cover_button = ttk.Button(custom_cover_row, command=self.choose_custom_cover)
        self.choose_cover_button.grid(row=0, column=0, sticky="w")
        ttk.Label(custom_cover_row, textvariable=self.custom_cover_text_var).grid(row=0, column=1, padx=(8, 0), sticky="ew")

        youtube_panel = ttk.LabelFrame(self, padding=(12, 8, 12, 10))
        youtube_panel.grid(row=5, column=0, columnspan=2, sticky="ew")
        youtube_panel.columnconfigure(1, weight=1)
        self.i18n_widgets["youtube_group"] = youtube_panel

        self.i18n_widgets["youtube_url_label"] = ttk.Label(youtube_panel)
        self.i18n_widgets["youtube_url_label"].grid(row=0, column=0, sticky="w")
        self.youtube_url_entry = ttk.Entry(youtube_panel, textvariable=self.youtube_url_var)
        self.youtube_url_entry.grid(row=0, column=1, padx=(8, 8), sticky="ew")
        self.fetch_youtube_button = ttk.Button(youtube_panel, command=self.start_fetch_youtube_formats)
        self.fetch_youtube_button.grid(row=0, column=2, sticky="w")
        self._attach_entry_context_menu(self.youtube_url_entry)

        self.i18n_widgets["youtube_quality_label"] = ttk.Label(youtube_panel)
        self.i18n_widgets["youtube_quality_label"].grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.youtube_quality_combo = ttk.Combobox(
            youtube_panel,
            textvariable=self.youtube_quality_var,
            state="readonly",
            width=42,
        )
        self.youtube_quality_combo.grid(row=1, column=1, padx=(8, 8), sticky="w", pady=(8, 0))
        self.youtube_quality_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_youtube_details())
        self.download_youtube_button = ttk.Button(
            youtube_panel,
            command=self.start_youtube_download,
            style="Player.TButton",
            width=12,
        )
        self.download_youtube_button.grid(row=1, column=2, sticky="w", pady=(8, 0))
        self.choose_youtube_output_button = ttk.Button(youtube_panel, command=self.choose_youtube_output_folder)
        self.choose_youtube_output_button.grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Label(youtube_panel, textvariable=self.youtube_detail_var).grid(row=2, column=1, columnspan=2, padx=(8, 0), pady=(8, 0), sticky="w")

        controls = ttk.LabelFrame(self, padding=(12, 8, 12, 10))
        controls.grid(row=4, column=0, columnspan=2, sticky="ew")
        controls.columnconfigure(8, weight=1)
        self.i18n_widgets["tools_group"] = controls

        ttk.Label(controls, textvariable=self.count_var).grid(row=0, column=0, sticky="w")
        ttk.Label(controls, textvariable=self.progress_var).grid(row=0, column=1, padx=(12, 0), sticky="w")

        self.open_input_button = ttk.Button(controls, command=self.open_source)
        self.open_input_button.grid(row=0, column=2, padx=(12, 0), sticky="w")
        self.open_output_button = ttk.Button(controls, command=lambda: self.open_folder(self.output_dir))
        self.open_output_button.grid(row=0, column=3, padx=(8, 0), sticky="w")

        self.progress = ttk.Progressbar(controls, mode="indeterminate")
        self.progress.grid(row=0, column=8, padx=(14, 0), sticky="ew")

        self.i18n_widgets["trim_start_label"] = ttk.Label(controls)
        self.i18n_widgets["trim_start_label"].grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.trim_start_entry = ttk.Entry(controls, textvariable=self.trim_start_var, width=10)
        self.trim_start_entry.grid(row=1, column=1, padx=(8, 0), sticky="w", pady=(8, 0))
        self.mark_start_button = ttk.Button(controls, command=self.mark_trim_start)
        self.mark_start_button.grid(row=1, column=2, padx=(8, 0), sticky="w", pady=(8, 0))
        self.i18n_widgets["trim_end_label"] = ttk.Label(controls)
        self.i18n_widgets["trim_end_label"].grid(row=1, column=3, padx=(12, 0), sticky="w", pady=(8, 0))
        self.trim_end_entry = ttk.Entry(controls, textvariable=self.trim_end_var, width=10)
        self.trim_end_entry.grid(row=1, column=4, padx=(8, 0), sticky="w", pady=(8, 0))
        self.mark_end_button = ttk.Button(controls, command=self.mark_trim_end)
        self.mark_end_button.grid(row=1, column=5, padx=(8, 0), sticky="w", pady=(8, 0))
        self.trim_button = ttk.Button(controls, command=self.start_trim)
        self.trim_button.grid(row=1, column=6, padx=(8, 0), sticky="w", pady=(8, 0))

        log_frame = ttk.LabelFrame(self, padding=(12, 8, 12, 10))
        log_frame.grid(row=6, column=0, columnspan=2, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.i18n_widgets["log_group"] = log_frame

        self.log = tk.Text(log_frame, wrap="word", height=5, state="disabled")
        self.log.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)

        footer = ttk.Frame(self, padding=(16, 0, 16, 14))
        footer.grid(row=7, column=0, columnspan=2, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var).grid(row=0, column=0, sticky="w")

        self.busy_widgets = [
            self.language_combo,
            self.format_combo,
            self.quality_combo,
            self.video_compression_combo,
            self.video_resolution_combo,
            self.compress_video_button,
            self.keep_original_check,
            self.skip_existing_check,
            self.preview_check,
            self.open_output_check,
            self.enhancement_combo,
            self.manual_search_entry,
            self.custom_cover_check,
            self.choose_cover_button,
            self.youtube_url_entry,
            self.youtube_quality_combo,
            self.fetch_youtube_button,
            self.download_youtube_button,
            self.choose_youtube_output_button,
            self.choose_file_button,
            self.choose_folder_button,
            self.previous_button,
            self.back_button,
            self.play_button,
            self.pause_button,
            self.stop_button,
            self.forward_button,
            self.next_button,
            self.expand_video_button,
            self.speed_combo,
            self.volume_scale,
            self.timeline_scale,
            self.trim_start_entry,
            self.trim_end_entry,
            self.mark_start_button,
            self.mark_end_button,
            self.trim_button,
        ]
        self._sync_option_state()

    def _apply_language(self):
        self.title(self.text("app_title"))
        self.i18n_widgets["title"].configure(text=self.text("app_title"))
        self.i18n_widgets["subtitle"].configure(text=self.text("subtitle"))
        self.i18n_widgets["language_label"].configure(text=self.text("language"))
        self.i18n_widgets["source_group"].configure(text=self.text("source_group"))
        self.i18n_widgets["conversion_group"].configure(text=self.text("conversion_group"))
        self.i18n_widgets["video_only_group"].configure(text=self.text("video_only_group"))
        self.i18n_widgets["cover_group"].configure(text=self.text("cover_group"))
        self.i18n_widgets["youtube_group"].configure(text=self.text("youtube_group"))
        self.i18n_widgets["tools_group"].configure(text=self.text("tools_group"))
        self.i18n_widgets["media_player_group"].configure(text=self.text("media_player_group"))
        self.i18n_widgets["log_group"].configure(text=self.text("log_group"))
        self.i18n_widgets["output_label"].configure(text=self.text("output"))
        self.i18n_widgets["format_label"].configure(text=self.text("format"))
        self.i18n_widgets["quality_label"].configure(text=self.text("quality"))
        self.i18n_widgets["video_compression_label"].configure(text=self.text("video_compression"))
        self.i18n_widgets["video_resolution_label"].configure(text=self.text("video_resolution"))
        self.i18n_widgets["enhance_label"].configure(text=self.text("enhance"))
        self.i18n_widgets["manual_search_label"].configure(text=self.text("manual_search"))
        self.i18n_widgets["youtube_url_label"].configure(text=self.text("youtube_url"))
        self.i18n_widgets["youtube_quality_label"].configure(text=self.text("youtube_quality"))
        self.choose_file_button.configure(text=self.text("choose_file"))
        self.choose_folder_button.configure(text=self.text("choose_folder"))
        self.compress_video_button.configure(text=self.text("compress_videos"))
        self.keep_original_check.configure(text=self.text("keep_original"))
        self.skip_existing_check.configure(text=self.text("skip_existing"))
        self.preview_check.configure(text=self.text("preview_cover"))
        self.open_output_check.configure(text=self.text("open_output_done"))
        self.custom_cover_check.configure(text=self.text("use_custom_cover"))
        self.choose_cover_button.configure(text=self.text("choose_image"))
        self.fetch_youtube_button.configure(text=self.text("fetch_qualities"))
        self.download_youtube_button.configure(text=self.text("download_youtube"))
        self.choose_youtube_output_button.configure(text=self.text("choose_download_folder"))
        self.run_button.configure(text=self.text("run"))
        self.pause_button.configure(text="Pause")
        self.stop_button.configure(text="■")
        self.previous_button.configure(text="|◀")
        self.back_button.configure(text="-10s")
        self.forward_button.configure(text="+10s")
        self.next_button.configure(text="▶|")
        self.expand_video_button.configure(text="⛶" if not self.video_expanded else "▣")
        self._refresh_play_button()
        self.i18n_widgets["speed_label"].configure(text=self.text("speed"))
        self.i18n_widgets["volume_label"].configure(text=self.text("volume"))
        self.open_input_button.configure(text=self.text("open_source"))
        self.open_output_button.configure(text=self.text("open_output"))
        self.i18n_widgets["timeline_label"].configure(text=self.text("timeline"))
        self.i18n_widgets["trim_start_label"].configure(text=self.text("trim_start"))
        self.i18n_widgets["trim_end_label"].configure(text=self.text("trim_end"))
        self.mark_start_button.configure(text=self.text("mark_start"))
        self.mark_end_button.configure(text=self.text("mark_end"))
        self.trim_button.configure(text=self.text("trim_selected"))

        if not self.input_path:
            self.source_var.set(self.text("source_empty"))
            self.output_var.set(self.text("output_empty"))
            self.status_var.set(self.text("choose_start"))
        else:
            self.set_source(self.input_path)

        if not self.custom_cover_path:
            self.custom_cover_text_var.set(self.text("cover_empty"))
        self.count_var.set(self.text("media_count", count=len(self.media_files)))
        self.video_count_var.set(self.text("video_count", count=len(self.video_files())))
        self.progress_var.set(self.text("processed", current=0, total=len(self.media_files)))
        self._refresh_enhancement_options()
        self._refresh_video_compression_options()
        self._refresh_video_resolution_options()
        self._refresh_video_estimate()
        self._refresh_youtube_details()

    def _refresh_enhancement_options(self):
        labels = ENHANCEMENT_LABELS[self.language_var.get()]
        self.enhancement_combo.configure(values=[labels[key] for key in convert.ENHANCEMENT_PRESETS])
        self.enhancement_var.set(labels[self.enhancement_key])

    def _refresh_video_compression_options(self):
        labels = VIDEO_COMPRESSION_LABELS[self.language_var.get()]
        self.video_compression_combo.configure(values=[labels[key] for key in convert.VIDEO_COMPRESSION_PRESETS])
        self.video_compression_var.set(labels[self.video_compression_key])

    def _refresh_video_resolution_options(self):
        labels = VIDEO_RESOLUTION_LABELS[self.language_var.get()]
        self.video_resolution_combo.configure(values=[labels[key] for key in convert.VIDEO_RESOLUTION_PRESETS])
        self.video_resolution_var.set(labels[self.video_resolution_key])

    def _attach_entry_context_menu(self, entry):
        def show_menu(event):
            menu = tk.Menu(entry, tearoff=False)
            menu.add_command(label=self.text("cut"), command=lambda: entry.event_generate("<<Cut>>"))
            menu.add_command(label=self.text("copy"), command=lambda: entry.event_generate("<<Copy>>"))
            menu.add_command(label=self.text("paste"), command=lambda: entry.event_generate("<<Paste>>"))
            menu.add_separator()
            menu.add_command(label=self.text("select_all"), command=lambda: entry.select_range(0, "end"))
            menu.tk_popup(event.x_root, event.y_root)

        entry.bind("<Button-3>", show_menu)
        entry.bind("<Control-a>", lambda _event: (entry.select_range(0, "end"), "break")[-1])

    def _language_changed(self, _event=None):
        self._apply_language()
        self._save_settings()

    def _speed_changed(self, _event=None):
        self.apply_playback_speed()
        self._save_settings()

    def _video_compression_changed(self, _event=None):
        self._remember_video_compression_key()
        self._save_settings()
        self._refresh_video_estimate()

    def _video_resolution_changed(self, _event=None):
        self._remember_video_resolution_key()
        self._save_settings()
        self._refresh_video_estimate()

    def _video_estimate_bitrate_kbps(self, compression, resolution):
        base = {
            "Small": 700,
            "Medium": 1200,
            "High": 2200,
        }.get(compression, 1200)
        if resolution == "480p":
            base *= 0.65
        elif resolution == "720p":
            base *= 0.9
        return int(base)

    def _estimate_video_output_size(self, video_files):
        if not video_files:
            return None
        compression = self.selected_video_compression()
        resolution = self.selected_video_resolution()
        video_kbps = self._video_estimate_bitrate_kbps(compression, resolution)
        audio_kbps = int(convert.VIDEO_COMPRESSION_PRESETS[compression]["audio_bitrate"].rstrip("k"))
        total_seconds = 0
        for path in video_files:
            try:
                total_seconds += convert.get_media_duration(path) or 0
            except Exception:
                return None
        if total_seconds <= 0:
            return None
        return int(((video_kbps + audio_kbps) * 1000 / 8) * total_seconds)

    def _refresh_video_estimate(self):
        video_files = self.video_files()
        if not video_files:
            self.video_estimate_var.set("")
            return
        estimate = self._estimate_video_output_size(video_files)
        if estimate:
            self.video_estimate_var.set(f"Est. {convert.human_size(estimate)}")
        else:
            self.video_estimate_var.set("Est. unknown")

    def _remember_enhancement_key(self):
        selected_label = self.enhancement_var.get()
        labels = ENHANCEMENT_LABELS[self.language_var.get()]
        for key, label in labels.items():
            if label == selected_label:
                self.enhancement_key = key
                return

    def _remember_video_compression_key(self):
        selected_label = self.video_compression_var.get()
        labels = VIDEO_COMPRESSION_LABELS[self.language_var.get()]
        for key, label in labels.items():
            if label == selected_label:
                self.video_compression_key = key
                return

    def _remember_video_resolution_key(self):
        selected_label = self.video_resolution_var.get()
        labels = VIDEO_RESOLUTION_LABELS[self.language_var.get()]
        for key, label in labels.items():
            if label == selected_label:
                self.video_resolution_key = key
                return

    def selected_enhancement(self):
        self._remember_enhancement_key()
        return self.enhancement_key

    def selected_video_compression(self):
        self._remember_video_compression_key()
        return self.video_compression_key

    def selected_video_resolution(self):
        self._remember_video_resolution_key()
        return self.video_resolution_key

    def choose_input_folder(self):
        selected = filedialog.askdirectory(title=self.text("folder_title"), initialdir=self._dialog_dir(self.last_media_dir))
        if selected:
            selected_path = Path(selected)
            self.last_media_dir = selected_path
            self._save_settings()
            self.set_source(selected_path)

    def choose_input_file(self):
        filetypes = [
            (self.text("media_files"), " ".join(f"*{ext}" for ext in sorted(convert.MEDIA_EXTS))),
            (self.text("audio_files"), " ".join(f"*{ext}" for ext in sorted(convert.AUDIO_EXTS))),
            (self.text("video_files"), " ".join(f"*{ext}" for ext in sorted(convert.VIDEO_EXTS))),
            (self.text("all_files"), "*.*"),
        ]
        selected = filedialog.askopenfilename(title=self.text("file_title"), initialdir=self._dialog_dir(self.last_media_dir), filetypes=filetypes)
        if selected:
            selected_path = Path(selected)
            self.last_media_dir = selected_path.parent
            self._save_settings()
            self.set_source(selected_path)

    def choose_custom_cover(self):
        filetypes = [
            (self.text("image_files"), "*.jpg *.jpeg *.png *.webp *.bmp *.gif"),
            (self.text("all_files"), "*.*"),
        ]
        selected = filedialog.askopenfilename(title=self.text("cover_title"), initialdir=self._dialog_dir(self.last_cover_dir), filetypes=filetypes)
        if not selected:
            return

        self.custom_cover_path = Path(selected)
        self.last_cover_dir = self.custom_cover_path.parent
        self._save_settings()
        self.custom_cover_text_var.set(str(self.custom_cover_path))
        self.status_var.set(self.text("custom_cover_selected"))
        self._update_run_state()

    def choose_youtube_output_folder(self):
        selected = filedialog.askdirectory(title=self.text("choose_download_folder"), initialdir=self._dialog_dir(self.youtube_output_dir()))
        if selected:
            self.youtube_output_dir_path = Path(selected)
            self._save_settings()
            self._refresh_youtube_details()

    def set_source(self, source_path):
        self.stop_playback()
        self.input_path = source_path
        output_base = source_path.parent if source_path.is_file() else source_path
        self.output_dir = output_base / "output"
        self.media_files = convert.collect_media_files(self.input_path, self.output_dir)
        self._load_media_duration()

        self.source_var.set(str(self.input_path))
        self.output_var.set(str(self.output_dir))
        self.count_var.set(self.text("media_count", count=len(self.media_files)))
        self.video_count_var.set(self.text("video_count", count=len(self.video_files())))
        self._refresh_video_estimate()
        self.progress_var.set(self.text("processed", current=0, total=len(self.media_files)))
        self.status_var.set(self.text("ready") if self.media_files else self.text("no_media"))
        self._update_run_state()

    def open_source(self):
        if not self.input_path:
            return
        self.open_folder(self.input_path.parent if self.input_path.is_file() else self.input_path)

    def _load_media_duration(self):
        self.media_duration = 0
        self.timeline_var.set(0)
        if self._single_media_file_selected():
            try:
                self.media_duration = int(convert.get_media_duration(self.input_path) or 0)
            except Exception:
                self.media_duration = 0
        self.timeline_scale.configure(to=max(self.media_duration, 0))
        self._refresh_timeline_text()

    def _format_time(self, seconds):
        seconds = max(0, int(seconds))
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def _refresh_timeline_text(self):
        current = self._current_timeline_seconds()
        if self.media_duration:
            self.timeline_text_var.set(f"{self._format_time(current)} / {self._format_time(self.media_duration)}")
        else:
            self.timeline_text_var.set("00:00 / 00:00")

    def _current_timeline_seconds(self):
        return max(0, min(float(self.timeline_var.get() or 0), float(self.media_duration or 0)))

    def _timeline_dragged(self, _value=None):
        self._refresh_timeline_text()

    def _timeline_press(self, _event=None):
        self.timeline_dragging = True
        self.was_playing_before_drag = self._is_playing()

    def _timeline_release(self, _event=None):
        self.timeline_dragging = False
        if self.media_player:
            self.media_player.set_time(int(self._current_timeline_seconds() * 1000))
        self._refresh_timeline_text()
        if self.was_playing_before_drag and self.media_player:
            self.media_player.play()
            self.apply_playback_speed()
            self._schedule_playback_tick()
        self.was_playing_before_drag = False

    def mark_trim_start(self):
        self.trim_start_var.set(self._format_time(self._current_timeline_seconds()))

    def mark_trim_end(self):
        self.trim_end_var.set(self._format_time(self._current_timeline_seconds()))

    def toggle_play_pause(self):
        if self.media_player and self.loaded_media_path == self.input_path and self.media_player.is_playing():
            self.pause_playback()
            return
        self.play_source_file()

    def play_source_file(self):
        if not self.input_path or not self.input_path.is_file():
            messagebox.showwarning(self.text("app_title"), self.text("choose_single_trim"))
            return
        if vlc is None:
            messagebox.showwarning(self.text("app_title"), self.text("vlc_missing"))
            return

        if self.media_player and self.loaded_media_path == self.input_path:
            state = self.media_player.get_state()
            if self.media_player.is_playing():
                self._refresh_play_button()
                return
            if state not in {vlc.State.Ended, vlc.State.Error, vlc.State.Stopped}:
                self.media_player.play()
                self.apply_playback_speed()
                self.apply_volume()
                self._schedule_playback_tick()
                self._update_run_state()
                self._refresh_play_button()
                return

        start_seconds = self._current_timeline_seconds()
        if self.media_duration and start_seconds >= self.media_duration - 0.5:
            start_seconds = 0
            self.timeline_var.set(0)
        self._start_media_from(start_seconds)

    def _start_media_from(self, start_seconds=0):
        self.stop_playback(reset_position=False)
        self._ensure_vlc_player()
        self._attach_video_surface()
        media = self.vlc_instance.media_new(str(self.input_path))
        self.media_player.set_media(media)
        self.loaded_media_path = self.input_path
        start_ms = int(max(0, start_seconds) * 1000)
        self.media_player.play()
        self.play_started_at = time.monotonic()
        self.apply_playback_speed()
        self.apply_volume()
        self.after(250, lambda: self._seek_loaded_player(start_ms))
        self.after(900, lambda: self._seek_loaded_player(start_ms))
        self.after(1200, self._attach_video_surface)
        self._update_run_state()
        self._schedule_playback_tick()

    def _seek_loaded_player(self, target_ms):
        if self.media_player and self.loaded_media_path == self.input_path and target_ms > 0:
            self.media_player.set_time(target_ms)

    def _is_playing(self):
        return bool(self.media_player and self.media_player.is_playing())

    def _refresh_play_button(self):
        if not hasattr(self, "play_button"):
            return
        self.play_button.configure(text="❚❚" if self._is_playing() else "▶")

    def _ensure_vlc_player(self):
        if self.vlc_instance is None:
            self.vlc_instance = vlc.Instance("--no-video-title-show")
        if self.media_player is None:
            self.media_player = self.vlc_instance.media_player_new()
        self._attach_video_surface()

    def _attach_video_surface(self):
        if not self.media_player:
            return
        self.update_idletasks()
        surface = self.video_surface
        if sys.platform.startswith("win"):
            self.media_player.set_hwnd(surface.winfo_id())
        elif sys.platform == "darwin":
            self.media_player.set_nsobject(surface.winfo_id())
        else:
            self.media_player.set_xwindow(surface.winfo_id())

    def toggle_video_size(self):
        if self.video_expanded:
            self._exit_video_fullscreen()
            return

        self.video_expanded = True
        self.fullscreen_grid = self.i18n_widgets["media_player_group"].grid_info()
        for child in self.winfo_children():
            if child is not self.i18n_widgets["media_player_group"]:
                child.grid_remove()
        self.i18n_widgets["media_player_group"].grid(row=0, column=0, columnspan=2, rowspan=8, padx=0, pady=0, sticky="nsew")
        self.i18n_widgets["media_player_group"].configure(padding=0)
        self.attributes("-fullscreen", True)
        self.bind("<Escape>", lambda _event: self._exit_video_fullscreen())
        self.bind("<F11>", lambda _event: self._exit_video_fullscreen())
        self.video_surface.bind("<Double-Button-1>", lambda _event: self._exit_video_fullscreen())
        self.expand_video_button.configure(text="▣")
        self.update_idletasks()
        self._attach_video_surface()

    def _exit_video_fullscreen(self):
        if not self.video_expanded:
            return
        self.video_expanded = False
        self.attributes("-fullscreen", False)
        self.unbind("<Escape>")
        self.unbind("<F11>")
        self.video_surface.unbind("<Double-Button-1>")
        self.i18n_widgets["media_player_group"].grid_forget()
        if self.fullscreen_grid:
            self.i18n_widgets["media_player_group"].grid(**self.fullscreen_grid)
        for child in self.winfo_children():
            if child is not self.i18n_widgets["media_player_group"]:
                child.grid()
        self.i18n_widgets["media_player_group"].configure(padding=(6, 6, 6, 8))
        self.fullscreen_grid = None
        self.expand_video_button.configure(text="⛶")
        self.update_idletasks()
        self._attach_video_surface()

    def selected_playback_speed(self):
        try:
            return float(self.speed_var.get().replace("x", ""))
        except ValueError:
            return 1.0

    def apply_playback_speed(self):
        if self.media_player:
            self.media_player.set_rate(self.selected_playback_speed())

    def apply_volume(self, _value=None):
        if self.media_player:
            self.media_player.audio_set_volume(int(float(self.volume_var.get())))

    def pause_playback(self):
        if self.media_player and self.loaded_media_path:
            self.media_player.pause()
            self._update_run_state()
            self._refresh_play_button()

    def seek_relative(self, seconds):
        if not self._single_media_file_selected():
            return
        if self.media_player and self.media_player.get_state() not in {vlc.State.Ended, vlc.State.Error, vlc.State.Stopped}:
            current_ms = max(0, self.media_player.get_time())
            duration_ms = max(0, self.media_player.get_length())
        else:
            current_ms = int(self._current_timeline_seconds() * 1000)
            duration_ms = int(max(0, self.media_duration) * 1000)
        target_ms = max(0, current_ms + int(seconds * 1000))
        if duration_ms:
            target_ms = min(max(0, duration_ms - 500), target_ms)
        if self.media_player and self.media_player.get_state() not in {vlc.State.Ended, vlc.State.Error, vlc.State.Stopped}:
            self.media_player.set_time(target_ms)
        self.timeline_var.set(target_ms / 1000)
        self._refresh_timeline_text()

    def seek_to_start(self):
        if self.media_player and self.media_player.get_state() not in {vlc.State.Ended, vlc.State.Error, vlc.State.Stopped}:
            self.media_player.set_time(0)
        self.timeline_var.set(0)
        self._refresh_timeline_text()

    def seek_to_end(self):
        if not self._single_media_file_selected():
            return
        duration_ms = max(0, self.media_player.get_length()) if self.media_player else int(max(0, self.media_duration) * 1000)
        if duration_ms:
            if self.media_player and self.media_player.get_state() not in {vlc.State.Ended, vlc.State.Error, vlc.State.Stopped}:
                self.media_player.set_time(duration_ms)
            self.timeline_var.set(duration_ms / 1000)
            self._refresh_timeline_text()

    def stop_playback(self, reset_position=True):
        if self.playback_tick:
            self.after_cancel(self.playback_tick)
            self.playback_tick = None
        if self.media_player:
            self.media_player.stop()
        if reset_position:
            self.timeline_var.set(0)
            self.loaded_media_path = None
        self.player_process = None
        self.play_started_at = None
        self.was_playing_before_drag = False
        self._refresh_timeline_text()
        self._update_run_state()
        self._refresh_play_button()

    def _schedule_playback_tick(self):
        if not self.media_player:
            return
        state = self.media_player.get_state()
        if state in {vlc.State.Ended, vlc.State.Error, vlc.State.Stopped}:
            if state == vlc.State.Stopped and self.play_started_at and time.monotonic() - self.play_started_at < 5:
                self.playback_tick = self.after(250, self._schedule_playback_tick)
                return
            if state == vlc.State.Ended and self.media_duration:
                self.timeline_var.set(self.media_duration)
                self._refresh_timeline_text()
            self._update_run_state()
            self._refresh_play_button()
            return
        duration_ms = self.media_player.get_length()
        if duration_ms and duration_ms > 0:
            self.media_duration = max(self.media_duration, int(duration_ms / 1000))
            self.timeline_scale.configure(to=max(self.media_duration, 0))
        current_ms = self.media_player.get_time()
        if current_ms >= 0 and not self.timeline_dragging:
            self.timeline_var.set(current_ms / 1000)
        self._refresh_timeline_text()
        self._refresh_play_button()
        self.playback_tick = self.after(250, self._schedule_playback_tick)

    def open_folder(self, path):
        if not path:
            return
        path.mkdir(exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def _begin_operation(self, operation, button):
        self.cancel_event.clear()
        self.active_operation = operation
        self.active_operation_button = button
        self.run_started_at = time.monotonic()

    def cancel_current_operation(self):
        if not self.worker or not self.worker.is_alive():
            return
        if self.cancel_event.is_set():
            return
        self.cancel_event.set()
        self.status_var.set(self.text("canceling"))
        self._append_log(self.text("canceling") + "\n")

    def _operation_canceled(self):
        return self.cancel_event.is_set()

    def _restore_operation_buttons(self):
        self.run_button.configure(command=self.start_conversion)
        self.compress_video_button.configure(command=self.start_video_compression)
        self.trim_button.configure(command=self.start_trim)
        self.fetch_youtube_button.configure(command=self.start_fetch_youtube_formats)
        self.download_youtube_button.configure(command=self.start_youtube_download)
        self.run_button.configure(text=self.text("run"))
        self.compress_video_button.configure(text=self.text("compress_videos"))
        self.trim_button.configure(text=self.text("trim_selected"))
        self.fetch_youtube_button.configure(text=self.text("fetch_qualities"))
        self.download_youtube_button.configure(text=self.text("download_youtube"))
        self.active_operation = None
        self.active_operation_button = None

    def start_conversion(self):
        if self.worker and self.worker.is_alive():
            return
        if not self.input_path or not self.media_files:
            return
        if self.custom_cover_var.get() and not self.custom_cover_path:
            messagebox.showwarning(self.text("app_title"), self.text("choose_cover_first"))
            return

        output_ext = self.selected_output_ext()
        quality = self.quality_var.get()
        skip_if_exists = self.skip_existing_var.get()
        keep_original_format = self.keep_original_var.get()
        search_text = self.manual_search_var.get().strip() or None
        custom_cover_path = self.custom_cover_path if self.custom_cover_var.get() else None
        enhancement = self.selected_enhancement()
        video_action = "extract_audio"
        video_compression = self.selected_video_compression()
        video_resolution = self.selected_video_resolution()
        self._clear_log()
        self._begin_operation("convert", self.run_button)
        mode = self.text("mode_original") if keep_original_format else output_ext
        self._append_log(self.text("starting", mode=mode))
        self.status_var.set(self.text("running"))
        self._set_busy(True)
        self.progress.configure(mode="determinate", maximum=max(len(self.media_files), 1) * 100, value=0)
        self.progress_var.set(self.text("processed", current=0, total=len(self.media_files)))

        self.worker = threading.Thread(
            target=self._run_conversion,
            args=(
                output_ext,
                quality,
                skip_if_exists,
                keep_original_format,
                search_text,
                custom_cover_path,
                enhancement,
                video_action,
                video_compression,
                video_resolution,
                False,
            ),
            daemon=True,
        )
        self.worker.start()

    def start_video_compression(self):
        if self.worker and self.worker.is_alive():
            return
        video_files = self.video_files()
        if not self.input_path or not video_files:
            messagebox.showwarning(self.text("app_title"), self.text("no_videos"))
            return

        output_ext = self.selected_output_ext()
        video_compression = self.selected_video_compression()
        video_resolution = self.selected_video_resolution()
        self._clear_log()
        self._begin_operation("video", self.compress_video_button)
        self._append_log(self.text("starting_video_only"))
        self.status_var.set(self.text("running"))
        self._set_busy(True)
        self.progress.configure(mode="determinate", maximum=max(len(video_files), 1) * 100, value=0)
        self.progress_var.set(self.text("processed", current=0, total=len(video_files)))

        self.worker = threading.Thread(
            target=self._run_conversion,
            args=(
                output_ext,
                self.quality_var.get(),
                self.skip_existing_var.get(),
                False,
                None,
                None,
                "Off",
                "compress_video",
                video_compression,
                video_resolution,
                True,
            ),
            daemon=True,
        )
        self.worker.start()

    def start_trim(self):
        if self.worker and self.worker.is_alive():
            return
        if not self.input_path or not self.input_path.is_file():
            messagebox.showwarning(self.text("app_title"), self.text("choose_single_trim"))
            return

        start_time = self.trim_start_var.get().strip()
        end_time = self.trim_end_var.get().strip()
        if not start_time or not end_time:
            messagebox.showwarning(self.text("app_title"), self.text("trim_times_required"))
            return

        output_ext = self.selected_output_ext()
        quality = self.quality_var.get()
        keep_original_format = self.keep_original_var.get()
        enhancement = self.selected_enhancement()
        self._clear_log()
        self._begin_operation("trim", self.trim_button)
        self._append_log(self.text("trimming") + "\n")
        self.status_var.set(self.text("trimming"))
        self._set_busy(True)
        self.progress.configure(mode="determinate", maximum=100, value=0)
        self.progress_var.set(self.text("progress_detail", current=0, total=1, file_percent=0, overall_percent=0, remaining_percent=100, eta=self.text("estimating")))

        self.worker = threading.Thread(
            target=self._run_trim,
            args=(start_time, end_time, output_ext, quality, keep_original_format, enhancement),
            daemon=True,
        )
        self.worker.start()

    def start_fetch_youtube_formats(self):
        if self.worker and self.worker.is_alive():
            return
        url = self.youtube_url_var.get().strip()
        if not url:
            messagebox.showwarning(self.text("app_title"), self.text("youtube_url_required"))
            return

        self._clear_log()
        self.youtube_formats = []
        self.youtube_quality_combo.configure(values=[])
        self.youtube_quality_var.set("")
        self._begin_operation("youtube_fetch", self.fetch_youtube_button)
        self._append_log(self.text("youtube_fetching") + "\n")
        self.status_var.set(self.text("youtube_fetching"))
        self._set_busy(True)
        self.progress.configure(mode="indeterminate")
        self.progress.start(10)

        self.worker = threading.Thread(target=self._run_fetch_youtube_formats, args=(url,), daemon=True)
        self.worker.start()

    def _run_fetch_youtube_formats(self, url):
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        writer = QueueWriter(self.messages)
        sys.stdout = writer
        sys.stderr = writer

        try:
            info = convert.fetch_youtube_formats(url)
            self.messages.put(("youtube_formats", info))
            self.messages.put("\n__FETCH_DONE__")
        except Exception as exc:
            self.messages.put(f"\nError: {exc}\n")
            self.messages.put("\n__FAILED__")
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def start_youtube_download(self):
        if self.worker and self.worker.is_alive():
            return
        url = self.youtube_url_var.get().strip()
        if not url:
            messagebox.showwarning(self.text("app_title"), self.text("youtube_url_required"))
            return
        if not self.youtube_formats:
            self.start_fetch_youtube_formats()
            return

        self.output_dir = self.youtube_output_dir()
        self.output_var.set(str(self.output_dir))
        selected_format = self._selected_youtube_format()
        format_id = selected_format.get("selector") or selected_format["format_id"] if selected_format else convert.YOUTUBE_AUDIO_FORMAT_ID
        format_has_audio = bool(selected_format and selected_format.get("has_audio"))
        self._clear_log()
        self._begin_operation("youtube_download", self.download_youtube_button)
        self._append_log(self.text("youtube_downloading") + "\n")
        self.status_var.set(self.text("youtube_downloading"))
        self._set_busy(True)
        self.progress.configure(mode="determinate", maximum=100, value=0)
        self.progress_var.set(self.text("progress_detail", current=0, total=1, file_percent=0, overall_percent=0, remaining_percent=100, eta=self.text("estimating")))

        self.worker = threading.Thread(
            target=self._run_youtube_download,
            args=(url, format_id, format_has_audio, self.quality_var.get()),
            daemon=True,
        )
        self.worker.start()

    def _selected_youtube_format_id(self):
        selected = self.youtube_quality_var.get()
        for item in self.youtube_formats:
            if item["label"] == selected:
                return item["format_id"]
        return self.youtube_formats[0]["format_id"] if self.youtube_formats else convert.YOUTUBE_AUDIO_FORMAT_ID

    def youtube_output_dir(self):
        return Path(self.youtube_output_dir_path)

    def _selected_youtube_format(self):
        selected = self.youtube_quality_var.get()
        for item in self.youtube_formats:
            if item["label"] == selected:
                return item
        return self.youtube_formats[0] if self.youtube_formats else None

    def _refresh_youtube_details(self):
        selected = self._selected_youtube_format()
        parts = [self.text("youtube_save_to", path=self.youtube_output_dir())]
        if selected:
            parts.insert(0, self.text("youtube_size", size=selected.get("size_label", "Unknown")))
        self.youtube_detail_var.set(" | ".join(parts))

    def _run_youtube_download(self, url, format_id, format_has_audio, quality):
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        writer = QueueWriter(self.messages)
        sys.stdout = writer
        sys.stderr = writer

        try:
            convert.download_youtube(
                url,
                output_dir=self.output_dir,
                format_id=format_id,
                format_has_audio=format_has_audio,
                audio_quality=quality,
                progress_callback=self._progress_request,
                cancel_callback=self._operation_canceled,
            )
            self.messages.put("\n__DONE__")
        except convert.CancelledError:
            self.messages.put("\n__CANCELED__")
        except Exception as exc:
            self.messages.put(f"\nError: {exc}\n")
            self.messages.put("\n__FAILED__")
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def selected_output_ext(self):
        return self.output_format_var.get().split(" ", 1)[0]

    def _run_conversion(
        self,
        output_ext,
        quality,
        skip_if_exists,
        keep_original_format,
        search_text,
        custom_cover_path,
        enhancement,
        video_action,
        video_compression,
        video_resolution,
        video_only,
    ):
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        writer = QueueWriter(self.messages)
        sys.stdout = writer
        sys.stderr = writer

        try:
            convert.main(
                output_ext=output_ext,
                input_dir=self.input_path,
                output_dir=self.output_dir,
                skip_if_exists=skip_if_exists,
                keep_original_format=keep_original_format,
                quality=quality,
                search_text=search_text,
                preview_callback=self._preview_cover_request if self.preview_var.get() else None,
                progress_callback=self._progress_request,
                custom_cover_path=custom_cover_path,
                enhancement=enhancement,
                video_action=video_action,
                video_compression=video_compression,
                video_resolution=video_resolution,
                video_only=video_only,
                cancel_callback=self._operation_canceled,
            )
            self.messages.put("\n__DONE__")
        except convert.CancelledError:
            self.messages.put("\n__CANCELED__")
        except Exception as exc:
            self.messages.put(f"\nError: {exc}\n")
            self.messages.put("\n__FAILED__")
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def _run_trim(self, start_time, end_time, output_ext, quality, keep_original_format, enhancement):
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        writer = QueueWriter(self.messages)
        sys.stdout = writer
        sys.stderr = writer

        try:
            output_path = convert.trim_media(
                self.input_path,
                start_time,
                end_time,
                input_dir=self.input_path.parent,
                output_dir=self.output_dir,
                output_ext=output_ext,
                quality=quality,
                keep_original_format=keep_original_format,
                enhancement=enhancement,
                progress_callback=self._progress_request,
                cancel_callback=self._operation_canceled,
            )
            if output_path:
                self.messages.put(f"Saved: {output_path}\n")
                self.messages.put("\n__DONE__")
            else:
                self.messages.put("\n__FAILED__")
        except convert.CancelledError:
            self.messages.put("\n__CANCELED__")
        except Exception as exc:
            self.messages.put(f"\nError: {exc}\n")
            self.messages.put("\n__FAILED__")
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def _drain_messages(self):
        try:
            while True:
                message = self.messages.get_nowait()
                if message == "\n__DONE__":
                    self._finish(self.text("done"))
                elif message == "\n__FETCH_DONE__":
                    self._finish_fetch_youtube_formats()
                elif message == "\n__CANCELED__":
                    self._finish(self.text("canceled"), canceled=True)
                elif message == "\n__FAILED__":
                    self._finish(self.text("failed"), failed=True)
                elif isinstance(message, tuple) and message[0] == "progress":
                    _, current, total, source_name, file_percent = message
                    overall_units = min(total * 100, current * 100 + file_percent)
                    overall_percent = int((overall_units / max(total * 100, 1)) * 100)
                    remaining_percent = max(0, 100 - overall_percent)
                    eta = self._estimate_remaining_time(overall_units, total * 100)
                    self.progress.configure(maximum=max(total, 1) * 100, value=overall_units)
                    if source_name and current < total:
                        self.progress_var.set(
                            self.text(
                                "progress_detail",
                                current=current,
                                total=total,
                                file_percent=file_percent,
                                overall_percent=overall_percent,
                                remaining_percent=remaining_percent,
                                eta=eta,
                            )
                        )
                        self.status_var.set(source_name)
                    else:
                        self.progress_var.set(self.text("processed", current=current, total=total))
                elif isinstance(message, tuple) and message[0] == "preview":
                    _, payload = message
                    self._show_preview_dialog(payload)
                elif isinstance(message, tuple) and message[0] == "youtube_formats":
                    _, info = message
                    self.youtube_formats = info.get("formats", [])
                    labels = [item["label"] for item in self.youtube_formats]
                    self.youtube_quality_combo.configure(values=labels)
                    if labels:
                        self.youtube_quality_var.set(labels[0])
                        self._refresh_youtube_details()
                        self._append_log(f"{info.get('title', 'YouTube')}\n")
                        self._append_log(f"{len(labels)} formats found\n")
                    else:
                        self.youtube_quality_var.set("")
                        self._refresh_youtube_details()
                        self._append_log(self.text("youtube_no_formats") + "\n")
                else:
                    self._append_log(message)
        except queue.Empty:
            pass
        self.after(100, self._drain_messages)

    def _finish(self, status, failed=False, canceled=False):
        self._restore_operation_buttons()
        self.progress.stop()
        self._set_busy(False)
        self.status_var.set(status)
        if self.open_output_var.get() and not failed and not canceled:
            self.open_folder(self.output_dir)
        if failed:
            messagebox.showerror(self.text("app_title"), self.text("error_check_log"))
        elif not canceled:
            messagebox.showinfo(self.text("app_title"), self.text("files_ready"))

    def _finish_fetch_youtube_formats(self):
        self._restore_operation_buttons()
        self.progress.stop()
        self._set_busy(False)
        self.status_var.set(self.text("youtube_ready") if self.youtube_formats else self.text("youtube_no_formats"))

    def _set_busy(self, busy):
        widget_state = "disabled" if busy else "normal"
        combo_state = "disabled" if busy else "readonly"
        for widget in self.busy_widgets:
            widget.configure(state=combo_state if isinstance(widget, ttk.Combobox) else widget_state)
        if busy and self.active_operation_button:
            self.active_operation_button.configure(
                state="normal",
                text=self.text("cancel"),
                command=self.cancel_current_operation,
            )
        if not busy:
            self._sync_option_state()
        self.open_input_button.configure(state=widget_state if self.input_path else "disabled")
        self.open_output_button.configure(state=widget_state if self.output_dir else "disabled")
        self.play_button.configure(state=widget_state if self._single_media_file_selected() else "disabled")
        self.pause_button.configure(state=widget_state if self.loaded_media_path else "disabled")
        self.stop_button.configure(state=widget_state if self.loaded_media_path else "disabled")
        self.previous_button.configure(state=widget_state if self._single_media_file_selected() else "disabled")
        self.back_button.configure(state=widget_state if self._single_media_file_selected() else "disabled")
        self.forward_button.configure(state=widget_state if self._single_media_file_selected() else "disabled")
        self.next_button.configure(state=widget_state if self.loaded_media_path else "disabled")
        if not busy or self.trim_button is not self.active_operation_button:
            self.trim_button.configure(state=widget_state if self._single_media_file_selected() else "disabled")
        if not busy or self.compress_video_button is not self.active_operation_button:
            self.compress_video_button.configure(state=widget_state if self.video_files() else "disabled")
        if not busy or self.run_button is not self.active_operation_button:
            self.run_button.configure(state="disabled" if busy else self._run_button_state())
        if not busy or self.download_youtube_button is not self.active_operation_button:
            self.download_youtube_button.configure(state=widget_state if self._youtube_download_state() == "normal" else "disabled")
        if not busy or self.fetch_youtube_button is not self.active_operation_button:
            self.fetch_youtube_button.configure(state=widget_state if self.youtube_url_var.get().strip() else "disabled")
        self._refresh_play_button()

    def _sync_option_state(self):
        if self.worker and self.worker.is_alive():
            return
        self.format_combo.configure(state="disabled" if self.keep_original_var.get() else "readonly")
        self.quality_combo.configure(state="readonly")
        self.video_compression_combo.configure(state="readonly")
        self.video_resolution_combo.configure(state="readonly")
        self.enhancement_combo.configure(state="readonly")
        self.manual_search_entry.configure(state="disabled" if self.custom_cover_var.get() else "normal")
        self.choose_cover_button.configure(state="normal" if self.custom_cover_var.get() else "disabled")
        self.fetch_youtube_button.configure(state="normal" if self.youtube_url_var.get().strip() else "disabled")
        self.download_youtube_button.configure(state=self._youtube_download_state())
        self._update_run_state()

    def _youtube_download_state(self):
        return "normal" if self.youtube_url_var.get().strip() and self.youtube_formats else "disabled"

    def _youtube_url_changed(self, *_args):
        if self.worker and self.worker.is_alive():
            return
        self.youtube_formats = []
        self.youtube_quality_combo.configure(values=[])
        self.youtube_quality_var.set("")
        self._refresh_youtube_details()
        self._sync_option_state()

    def _progress_request(self, current, total, source_path, file_percent=0):
        source_name = source_path.name if source_path else None
        self.messages.put(("progress", current, total, source_name, int(file_percent or 0)))

    def _estimate_remaining_time(self, progress_units, total_units):
        if not self.run_started_at or progress_units <= 0 or progress_units >= total_units:
            return self.text("estimating") if progress_units < total_units else "0s"
        elapsed = time.monotonic() - self.run_started_at
        remaining = (elapsed / progress_units) * (total_units - progress_units)
        return self._format_seconds(remaining)

    def _format_seconds(self, seconds):
        seconds = max(0, int(seconds))
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h {minutes}m"
        if minutes:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    def _preview_cover_request(self, audio_path, cover_data, cover_ext, search_name):
        done = threading.Event()
        payload = {
            "audio_path": audio_path,
            "cover_data": cover_data,
            "cover_ext": cover_ext,
            "search_name": search_name,
            "accepted": False,
            "done": done,
        }
        self.messages.put(("preview", payload))
        done.wait()
        return payload["accepted"]

    def _show_preview_dialog(self, payload):
        dialog = tk.Toplevel(self)
        dialog.title(self.text("preview_title"))
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding=14)
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text=payload["audio_path"].name, font=("Segoe UI", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(frame, text=f"{self.text('search')}: {payload['search_name']}").grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 10))

        try:
            image = Image.open(BytesIO(payload["cover_data"]))
            image.thumbnail((420, 420))
            photo = ImageTk.PhotoImage(image)
            image_label = ttk.Label(frame, image=photo)
            image_label.image = photo
            image_label.grid(row=2, column=0, columnspan=2, pady=(0, 12))
        except Exception as exc:
            ttk.Label(frame, text=self.text("preview_error", error=exc)).grid(row=2, column=0, columnspan=2, pady=(0, 12))

        def choose(accepted):
            payload["accepted"] = accepted
            payload["done"].set()
            dialog.destroy()

        ttk.Button(frame, text=self.text("use_cover"), command=lambda: choose(True)).grid(row=3, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(frame, text=self.text("skip_cover"), command=lambda: choose(False)).grid(row=3, column=1, sticky="ew", padx=(6, 0))

        dialog.protocol("WM_DELETE_WINDOW", lambda: choose(False))
        dialog.wait_window()

    def _run_button_state(self):
        if not self.input_path or not self.media_files:
            return "disabled"
        if self.custom_cover_var.get() and not self.custom_cover_path:
            return "disabled"
        return "normal"

    def _single_media_file_selected(self):
        return bool(
            self.input_path
            and self.input_path.is_file()
            and self.input_path.suffix.lower() in convert.MEDIA_EXTS
        )

    def video_files(self):
        return [path for path in self.media_files if path.suffix.lower() in convert.VIDEO_EXTS]

    def _update_run_state(self):
        self.run_button.configure(state=self._run_button_state())
        self.compress_video_button.configure(state="normal" if self.video_files() else "disabled")
        self.open_input_button.configure(state="normal" if self.input_path else "disabled")
        self.open_output_button.configure(state="normal" if self.output_dir else "disabled")
        self.play_button.configure(state="normal" if self._single_media_file_selected() else "disabled")
        self.pause_button.configure(state="normal" if self.loaded_media_path else "disabled")
        self.stop_button.configure(state="normal" if self.loaded_media_path else "disabled")
        self.previous_button.configure(state="normal" if self._single_media_file_selected() else "disabled")
        self.back_button.configure(state="normal" if self._single_media_file_selected() else "disabled")
        self.forward_button.configure(state="normal" if self._single_media_file_selected() else "disabled")
        self.next_button.configure(state="normal" if self.loaded_media_path else "disabled")
        self.mark_start_button.configure(state="normal" if self._single_media_file_selected() else "disabled")
        self.mark_end_button.configure(state="normal" if self._single_media_file_selected() else "disabled")
        self.trim_button.configure(state="normal" if self._single_media_file_selected() else "disabled")
        self._refresh_play_button()

    def close_app(self):
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno(self.text("app_title"), self.text("close_running")):
                return
            self.cancel_event.set()
            self.status_var.set(self.text("canceling"))
            self.update_idletasks()
            self.worker.join(timeout=5)
        self._save_settings()
        self._exit_video_fullscreen()
        self.stop_playback()
        if self.media_player:
            self.media_player.release()
            self.media_player = None
        if self.vlc_instance:
            self.vlc_instance.release()
            self.vlc_instance = None
        self.destroy()

    def _append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")


if __name__ == "__main__":
    SongCoverApp().mainloop()
