"""
ClipCraft Studio GUI
Developer: ahmed elshazly
Email: Elshazly.gsm@gmail.com
"""

__author__ = "ahmed elshazly"
__email__ = "Elshazly.gsm@gmail.com"
__version__ = "1.0.0"

import copy
import json
import math
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
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL import Image, ImageTk


APP_DIR = Path(__file__).resolve().parent
os.chdir(APP_DIR)
DEFAULT_OUTPUT_DIR = Path.home() / "Videos" / "ClipCraft Studio"
SETTINGS_PATH = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ClipCraft Studio" / "settings.json"

EXE_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else APP_DIR
MEI_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))

VLC_CANDIDATE_DIRS = [
    EXE_DIR / "vlc",
    EXE_DIR,
    MEI_DIR / "vlc",
    MEI_DIR,
    APP_DIR / "vlc",
    APP_DIR,
    Path(r"C:\Program Files\VideoLAN\VLC"),
    Path(r"C:\Program Files (x86)\VideoLAN\VLC"),
]

for _vdir in VLC_CANDIDATE_DIRS:
    if not _vdir.exists():
        continue
    _lib = _vdir / "libvlc.dll" if (_vdir / "libvlc.dll").exists() else None
    if _lib and _lib.is_file():
        _folder = _lib.parent
        os.environ["PATH"] = f"{_folder}{os.pathsep}{os.environ.get('PATH', '')}"
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(str(_folder))
            except Exception:
                pass
        _plugins = _folder / "plugins"
        if _plugins.is_dir():
            os.environ["PYTHON_VLC_MODULE_PATH"] = str(_plugins)
        os.environ["PYTHON_VLC_LIB_PATH"] = str(_lib)
        break

try:
    import vlc  # noqa: E402
except Exception:
    vlc = None

import convert  # noqa: E402


TRANSLATIONS = {
    "English": {
        "app_title": "ClipCraft Studio",
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
        "video_only_group": "Video conversion and compression",
        "video_count": "{count} video files",
        "video_format": "Video format",
        "compress_videos": "Convert Video",
        "video_compression": "Compression / Quality",
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
        "vlc_missing": "Direct Media Engine is required for in-app video playback.",
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
        "trim_extract_audio": "Extract audio only (MP3)",
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
        "starting_video_only": "Starting video conversion...\n",
        "no_videos": "No supported video files found in this source",
        "processed": "{current} / {total} files processed",
        "processed_single": "Processing completed successfully",
        "progress_detail": "Progress: {file_percent}% | Elapsed: {elapsed} | Remaining: {eta}",
        "progress_detail_multi": "File {current} of {total} ({file_percent}%) | Total: {overall_percent}% | Elapsed: {elapsed} | Remaining: {eta}",
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
        "about": "About",
        "developer_credit": "Developer: ahmed elshazly | Elshazly.gsm@gmail.com",
        "about_title": "About ClipCraft Studio",
        "about_desc": "All-in-one audio and video conversion studio with metadata and cover art support.",
        "about_developer_header": "Developer Information",
        "about_developer_name": "Developer: ahmed elshazly",
        "about_developer_email": "Email: Elshazly.gsm@gmail.com",
        "copy_email": "Copy Email",
        "close": "Close",
        "settings_btn": "⚙️ Settings",
        "settings_title": "ClipCraft Studio — Settings & Preferences",
        "check_updates": "Check for Updates",
        "checking_updates": "Checking for updates...",
        "caption_group": "Auto Caption & Speech-to-Text",
        "open_caption_studio": "🎙️ Auto Caption / Transcribe",
        "caption_studio_title": "Auto Caption & Speech-to-Text Studio",
        "caption_source_label": "Source file:",
        "caption_folder_label": "Folder: {count} media files",
        "caption_model_label": "AI Whisper Model",
        "caption_lang_label": "Audio Language",
        "caption_translate_label": "Translate Subtitles To",
        "caption_translate_btn": "🌐 Translate Text",
        "caption_translating": "Translating subtitles to {target}...",
        "caption_translate_done": "Subtitles translated to {target} successfully!",
        "caption_export_srt": "Subtitle (.srt)",
        "caption_export_vtt": "WebVTT (.vtt)",
        "caption_export_txt": "Plain Text (.txt)",
        "caption_burn_video": "Burn subtitles onto video (Hardcode)",
        "caption_start": "Start Transcribing",
        "caption_stop": "Cancel",
        "caption_tab_text": "Plain Text",
        "caption_tab_srt": "Subtitles (SRT)",
        "caption_tab_bubbles": "Segment Bubbles (Interactive)",
        "caption_style_btn": "🎨 Subtitle Style & Position",
        "subtitle_style_title": "Subtitle Style & Video Position",
        "sub_font_name": "Font Family:",
        "sub_font_size": "Font Size:",
        "sub_font_auto": "Auto (Based on Resolution)",
        "sub_text_color": "Text Color:",
        "sub_outline_style": "Outline & Background:",
        "sub_bold": "Bold Text",
        "sub_italic": "Italic Text",
        "sub_pos_v": "Vertical Position:",
        "sub_pos_h": "Horizontal Align:",
        "sub_pos_bottom": "Bottom of Video",
        "sub_pos_middle": "Middle of Video",
        "sub_pos_top": "Top of Video",
        "sub_align_center": "Center",
        "sub_align_left": "Left",
        "sub_align_right": "Right",
        "sub_margin_v": "Vertical Margin (Offset):",
        "sub_preview_label": "Live Font & Style Preview:",
        "sub_preview_sample": "هذه معاينة شكل الخط ومكانه على الفيديو - Sample Caption",
        "sub_save_apply": "Save & Apply Style",
        "sub_reset_defaults": "Reset to Defaults",
        "sub_search_placeholder": "Search words...",
        "sub_page_label": "Page {current} of {total}",
        "sub_total_segments": "{count} segments",
        "sub_add_segment": "Add Segment",
        "sub_del_segment": "Delete",
        "sub_play_segment": "Play",
        "sub_save_edits": "Save Changes",
        "sub_edits_saved": "Subtitle edits saved successfully!",
        "sub_no_segments": "No subtitle segments available. Transcribe or import first.",
        "sub_prompt_add_text": "Enter new segment text:",
        "sub_prompt_add_title": "Add Subtitle Segment",
        "caption_copy": "Copy Text",
        "caption_save_as": "Save As...",
        "caption_burn_now": "Burn to Video",
        "caption_open_folder": "Open Output Folder",
        "caption_ready": "Ready to transcribe. Click 'Start Transcribing'.",
        "caption_loading": "Loading AI model...",
        "caption_transcribing": "Transcribing: {percent}%",
        "caption_burning": "Burning subtitles onto video...",
        "caption_done": "Transcription completed successfully!",
        "caption_error": "Transcription failed: {error}",
        "caption_saved": "File saved successfully!",
        "caption_burned_success": "Captioned video created: {filename}",
        "tab_convert": "🔄 Convert, Compress & Cover",
        "tab_volume": "🔊 Audio Mastering & Booster",
        "tab_player": "▶️ Player & Montage Studio",
        "tab_caption": "🎙️ Auto Caption",
        "tab_silence": "✂️ Auto Silence Cut",
        "tab_cover": "🖼️ Cover Art",
        "tab_youtube": "📥 YouTube Download",
        "volume_group": "Audio Amplification & Volume Booster",
        "volume_analysis_group": "Audio Level Analysis",
        "detect_volume": "Analyze Volume",
        "detecting_volume": "Analyzing audio volume...",
        "volume_current_level": "Current Mean: {mean} dB | Peak: {max} dB",
        "volume_suggested": "Suggested Clean Boost: +{gain} dB",
        "volume_gain_label": "Volume Gain:",
        "volume_anti_clipping": "Anti-Clipping Limiter (Prevents Distortion)",
        "volume_normalize_peak": "Auto Clean Peak to 0 dB (Maximum Clarity)",
        "boost_save": "Apply Mastering & Save Audio",
        "boosting_volume": "Mastering & boosting audio...",
        "volume_boosted_success": "Saved mastered audio: {filename}",
        "volume_preset_light": "+3 dB (140%)",
        "volume_preset_double": "+6 dB (200% / Double)",
        "volume_preset_high": "+10 dB (316% / 3x)",
        "volume_preset_extreme": "+15 dB (560% / 5.5x)",
        "audio_options": "Audio Conversion Options",
        "video_options": "Video Conversion & Compression",
        "trim_group": "Audio & Video Trimming",
        "caption_settings_group": "Transcription & Subtitle Settings",
        "caption_output_group": "Transcribed Text & Subtitles",
        "caption_model_status_ready": "✅ Ready (Downloaded)",
        "caption_model_status_needs_download": "⬇️ Needs download (~{size} MB)",
        "caption_models_dir": "Models Folder:",
        "caption_open_models_dir": "📂 Open Models Folder",
        "caption_download_model_btn": "⬇️ Download Model",
        "caption_model_ready_btn": "✅ Model Ready",
        "caption_downloading_model": "Downloading AI model '{model}' ({dl_mb:.1f} / {tot_mb:.1f} MB - {pct}%) [{speed}{eta_part}]",
        "caption_download_complete": "Model '{model}' downloaded successfully!",
        "caption_saving_to": "Saving to: {path}",
        "caption_import_capcut": "🎬 Import from CapCut",
        "caption_capcut_dialog_title": "Import Auto-Captions from CapCut",
        "caption_no_capcut_drafts": "No CapCut desktop projects with captions were found on this computer.",
        "caption_capcut_select": "Select a CapCut Project to import subtitles from:",
        "caption_capcut_imported": "Imported {count} subtitle segments successfully from CapCut ({project})!",
        "caption_select_video_to_burn": "Select the video file to burn subtitles onto:",
        "branding_dialog_title": "Video Dimensions, Branding & Export Settings",
        "branding_aspect_group": "Dimensions & Aspect Ratio",
        "branding_aspect_ratio": "Aspect Ratio:",
        "branding_fit_mode": "Fit Style:",
        "branding_logo_group": "Logo / Watermark Overlay",
        "branding_logo_enable": "Add Logo / Watermark to Video",
        "branding_logo_file": "Logo Image:",
        "branding_logo_pos": "Position:",
        "branding_logo_opacity": "Opacity:",
        "branding_title_group": "Video Title Banner / Headline",
        "branding_title_enable": "Add Title Banner to Video",
        "branding_title_text": "Title Text:",
        "branding_title_bg": "Background:",
        "branding_title_color": "Text Color:",
        "branding_burn_subtitles_chk": "Burn Subtitles onto Exported Video",
        "branding_preview_title": "Interactive Visual Preview",
        "branding_btn": "⚙️ Branding & Overlays...",
        "trim_burn_subtitles": "Burn Subtitles",
        "trim_add_logo": "Add Logo",
        "trim_add_title": "Add Title",
        "trim_color_grading": "Color Correction",
        "trim_remove_silence": "✂️ Remove Silences",
        "btn_color_grading": "🎨 Color Grading...",
        "btn_silence_studio": "✂️ Silence Studio...",
        "color_grading_summary": "Color Graded",
        "trim_aspect_ratio": "Aspect Ratio:",
        "branding_add_text": "➕ Add New Text",
        "branding_delete_text": "🗑️ Delete Text",
        "branding_canvas_hint": "🖱️ Click element to select. Drag white box to move, drag corners to resize.",
        "branding_subs_sample": "SAMPLE SUBTITLE معاينة الترجمة",
        "master_export_btn": "🎬 Export Video",
        "master_export_desc": "Export video with applied edits, compression, silence cuts, framing, logo, and subtitles.",
        "master_export_summary": "Active Edits:",
        "master_export_done": "Video exported successfully!",
        "trim_style_group": "Canvas, Subtitles, Colors & Silence Cut",
        "master_export_card": "Export Video",
        "view_log_btn": "View Log",
        "video_required": "Please select a valid video file first.",
        "theme_dark": "Dark Mode",
        "theme_light": "Light Mode",
        "toggle_theme": "Theme",
        "snapshot_btn": "📸 Snapshot",
        "snapshot_saved": "Saved high-res frame snapshot: {filename}",
        "silence_settings_group": "✂️ Smart Silence Detection & Jump-Cut Settings",
        "silence_results_group": "📊 Detected Silences & Visual Timeline",
        "silence_preset_label": "Smart Preset:",
        "silence_mode_label": "Silence Action:",
        "silence_threshold_label": "Silence Threshold:",
        "silence_auto_threshold": "✨ Auto Detect dB",
        "silence_min_dur_label": "Min Silence (sec):",
        "silence_padding_label": "Speech Margin (sec):",
        "silence_quality_label": "Quality / Compression:",
        "silence_format_label": "Export Format:",
        "silence_analyze_btn": "🔍 Analyze Silences",
        "silence_export_btn": "✂️ Cut Silences & Export Now",
        "silence_sync_subs_chk": "🔄 Auto-Sync Subtitles with Cuts",
        "silence_save_synced_srt": "💾 Save Synced .SRT",
        "silence_select_all": "Select All",
        "silence_deselect_all": "Deselect All",
        "silence_analyzing": "Scanning audio for silent pauses...",
        "silence_exporting": "Cutting silences & exporting media...",
        "silence_ready_hint": "📊 Detected Silences: 0 — Click '🔍 Analyze Silences' to scan pauses",
        "silence_summary_fmt": "✅ Found {count} silences | Original: {orig} ➔ New: {new} | Saved: {saved} ({pct}%)",
        "silence_none_found": "No silent pauses detected at {db} dB. Try raising the threshold (e.g. -28 dB).",
        "silence_empty_list": "No silences analyzed yet. Click '🔍 Analyze Silences' to inspect and toggle individual pauses.",
        "silence_item_label": "#{idx}  [{start} ➔ {end}]   Pause: {dur}s",
        "silence_cut_chk": "Cut",
        "silence_preview_seg": "▶ Preview",
        "silence_done_msg": "Silence removal completed! Saved: {filename}",
        "fade_in_label": "Fade In (sec):",
        "fade_out_label": "Fade Out (sec):",
    },
    "العربية": {
        "app_title": "كليب كرافت ستوديو (ClipCraft)",
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
        "video_only_group": "تحويل وضغط الفيديو",
        "video_count": "{count} فيديو",
        "video_format": "صيغة الفيديو",
        "compress_videos": "تحويل الفيديو",
        "video_compression": "الضغط / الجودة",
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
        "vlc_missing": "محرك المعاينة المباشرة مطلوب لتشغيل الفيديو داخل البرنامج.",
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
        "trim_extract_audio": "استخراج كصوت فقط (MP3)",
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
        "starting_video_only": "بدء تحويل الفيديوهات...\n",
        "no_videos": "لا توجد ملفات فيديو مدعومة في هذا المصدر",
        "processed": "تمت معالجة {current} / {total} ملفات",
        "processed_single": "تمت المعالجة بنجاح",
        "progress_detail": "التقدم: {file_percent}% | المنقضي: {elapsed} | المتبقي: {eta}",
        "progress_detail_multi": "ملف {current} من {total} ({file_percent}%) | الإجمالي: {overall_percent}% | المنقضي: {elapsed} | المتبقي: {eta}",
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
        "about": "عن البرنامج",
        "developer_credit": "المطور: ahmed elshazly | Elshazly.gsm@gmail.com",
        "about_title": "حول ClipCraft Studio",
        "about_desc": "برنامج شامل لتحويل ومعالجة الصوتيات والفيديو وضغط الوسائط وإضافة صور الأغلفة.",
        "about_developer_header": "بيانات المطور",
        "about_developer_name": "المطور: ahmed elshazly",
        "about_developer_email": "البريد الإلكتروني: Elshazly.gsm@gmail.com",
        "copy_email": "نسخ الإيميل",
        "close": "إغلاق",
        "settings_btn": "⚙️ الإعدادات",
        "settings_title": "ClipCraft Studio — إعدادات البرنامج والتفضيلات",
        "check_updates": "التحقق من التحديثات",
        "checking_updates": "جاري التحقق من التحديثات...",
        "caption_group": "التفريغ الصوتي والترجمة التلقائية",
        "open_caption_studio": "🎙️ تفريغ الصوت والترجمة",
        "caption_studio_title": "استوديو تفريغ الصوت والترجمة التلقائية",
        "caption_source_label": "الملف المحدد:",
        "caption_folder_label": "المجلد المحدد: {count} ملف وسائط",
        "caption_model_label": "نموذج الذكاء الاصطناعي (Whisper)",
        "caption_lang_label": "لغة الصوت الأصلية",
        "caption_translate_label": "ترجمة التفريغ التلقائي إلى",
        "caption_translate_btn": "🌐 ترجمة النص الآن",
        "caption_translating": "جاري ترجمة النصوص إلى {target}...",
        "caption_translate_done": "تمت ترجمة النصوص بنجاح إلى {target}!",
        "caption_export_srt": "ملف ترجمة (.srt)",
        "caption_export_vtt": "ملف ترجمة ويب (.vtt)",
        "caption_export_txt": "نص كامل (.txt)",
        "caption_burn_video": "دمج الترجمة بالفيديو مباشرة (Hardcode)",
        "caption_start": "بدء التفريغ التلقائي",
        "caption_stop": "إلغاء",
        "caption_tab_text": "نص مقروء (كامل)",
        "caption_tab_srt": "ترجمة مع التوقيتات (SRT)",
        "caption_tab_bubbles": "بالونات المقاطع (تعديل مباشر)",
        "caption_style_btn": "🎨 تنسيق الخط ومكان الترجمة",
        "subtitle_style_title": "تنسيق مظهر ومكان الخط على الفيديو",
        "sub_font_name": "نوع الخط:",
        "sub_font_size": "حجم الخط:",
        "sub_font_auto": "تلقائي (بحسب دقة الفيديو)",
        "sub_text_color": "لون النص:",
        "sub_outline_style": "التحديد والخلفية:",
        "sub_bold": "خط عريض (Bold)",
        "sub_italic": "خط مائل (Italic)",
        "sub_pos_v": "المكان الرأسي:",
        "sub_pos_h": "المحاذاة الأفقية:",
        "sub_pos_bottom": "أسفل الفيديو",
        "sub_pos_middle": "وسط الفيديو",
        "sub_pos_top": "أعلى الفيديو",
        "sub_align_center": "في المنتصف",
        "sub_align_left": "يسار",
        "sub_align_right": "يمين",
        "sub_margin_v": "الهامش الرأسي (الارتفاع):",
        "sub_preview_label": "معاينة شكل الخط على الفيديو:",
        "sub_preview_sample": "هذه معاينة شكل الخط ومكانه على الفيديو - Sample Caption",
        "sub_save_apply": "حفظ وتطبيق التنسيق",
        "sub_reset_defaults": "استعادة الافتراضي",
        "sub_search_placeholder": "بحث في الكلمات...",
        "sub_page_label": "صفحة {current} من {total}",
        "sub_total_segments": "{count} مقطع",
        "sub_add_segment": "إضافة مقطع",
        "sub_del_segment": "حذف",
        "sub_play_segment": "تشغيل",
        "sub_save_edits": "حفظ التعديلات",
        "sub_edits_saved": "تم حفظ وتحديث تعديلات النصوص بنجاح!",
        "sub_no_segments": "لا توجد مقاطع ترجمة حالياً. قم بالتفريغ أو استيراد كاب كات أولاً.",
        "sub_prompt_add_text": "اكتب نص المقطع الجديد:",
        "sub_prompt_add_title": "إضافة مقطع ترجمة",
        "caption_copy": "نسخ النص",
        "caption_save_as": "حفظ كملف",
        "caption_burn_now": "دمج الترجمة مع الفيديو",
        "caption_open_folder": "فتح مجلد الحفظ",
        "caption_ready": "جاهز للتفريغ. اضغط على 'بدء التفريغ التلقائي'.",
        "caption_loading": "جاري تحميل نموذج الذكاء الاصطناعي...",
        "caption_transcribing": "جاري التفريغ: {percent}%",
        "caption_burning": "جاري دمج الترجمة على الفيديو...",
        "caption_done": "تم التفريغ بنجاح!",
        "caption_error": "فشل التفريغ: {error}",
        "caption_saved": "تم حفظ الملف بنجاح!",
        "caption_burned_success": "تم إنشاء الفيديو مع الترجمة: {filename}",
        "tab_convert": "🔄 التحويل والضغط والغلاف",
        "tab_volume": "🔊 هندسة وتضخيم الصوت",
        "tab_player": "▶️ المشغل والمونتاج الاحترافي",
        "tab_caption": "🎙️ التفريغ الصوتي والترجمة",
        "tab_silence": "✂️ تقطيع السكتات الذكي",
        "tab_cover": "🖼️ صور الأغلفة والبيانات",
        "tab_youtube": "📥 تحميل من يوتيوب",
        "volume_group": "تضخيم وهندسة الصوت الذكية",
        "volume_analysis_group": "فحص وتحليل مستوى الصوت الحالي",
        "detect_volume": "فحص مستوى الصوت",
        "detecting_volume": "جاري فحص مستوى صوت الملف...",
        "volume_current_level": "متوسط الصوت: {mean} dB | أعلى ذروة: {max} dB",
        "volume_suggested": "الزيادة النقية المقترحة: +{gain} dB",
        "volume_gain_label": "نسبة تضخيم الصوت:",
        "volume_anti_clipping": "حماية من الخربشة والقص (Anti-Clipping Limiter)",
        "volume_normalize_peak": "رفع تلقائي ذكي لأعلى صوت نقي (Auto Peak)",
        "boost_save": "تطبيق هندسة الصوت والحفظ الآن",
        "boosting_volume": "جاري هندسة وتضخيم الصوت وحفظه...",
        "volume_boosted_success": "تم حفظ الملف بالصوت المحسّن: {filename}",
        "volume_preset_light": "+3 dB (140% - زيادة خفيفة)",
        "volume_preset_double": "+6 dB (200% - مضاعفة الصوت)",
        "volume_preset_high": "+10 dB (316% - تضخيم قوي)",
        "volume_preset_extreme": "+15 dB (560% - تضخيم فائق)",
        "audio_options": "خيارات تحويل الصوت والغلاف",
        "video_options": "خيارات تحويل وضغط الفيديو",
        "trim_group": "قص واقتطاع المقاطع",
        "caption_settings_group": "إعدادات التفريغ والترجمة",
        "caption_output_group": "النص المستخرج والترجمة التلقائية",
        "caption_model_status_ready": "✅ جاهز (مُحَمّل على الجهاز)",
        "caption_model_status_needs_download": "⬇️ يحتاج تحميل (~{size} ميجابايت)",
        "caption_models_dir": "مجلد النماذج:",
        "caption_open_models_dir": "📂 فتح مجلد النماذج",
        "caption_download_model_btn": "⬇️ تحميل النموذج",
        "caption_model_ready_btn": "✅ النموذج جاهز",
        "caption_downloading_model": "جاري تحميل نموذج الذكاء الاصطناعي '{model}' ({dl_mb:.1f} من {tot_mb:.1f} ميجابايت - {pct}%) [{speed}{eta_part}]",
        "caption_download_complete": "تم تحميل نموذج الذكاء الاصطناعي '{model}' بنجاح وهو جاهز للاستخدام!",
        "caption_saving_to": "مكان الحفظ: {path}",
        "caption_import_capcut": "🎬 استيراد من كاب كات",
        "caption_capcut_dialog_title": "استيراد الترجمة التلقائية من كاب كات",
        "caption_no_capcut_drafts": "لم يتم العثور على مشاريع بترجمة جاهزة داخل كاب كات في هذا الجهاز.",
        "caption_capcut_select": "اختر مشروع كاب كات لاستيراد ترجمته:",
        "caption_capcut_imported": "تم استيراد {count} مقطع ترجمة بنجاح من مشروع كاب كات ({project})!",
        "caption_select_video_to_burn": "اختر ملف الفيديو الذي تريد حرق الترجمة عليه:",
        "youtube_group": "تحميل من يوتيوب",
        "youtube_url": "رابط يوتيوب",
        "fetch_qualities": "جلب الجودات",
        "download_youtube": "تحميل",
        "youtube_quality": "جودة يوتيوب",
        "youtube_size": "الحجم: {size}",
        "youtube_save_to": "مكان الحفظ: {path}",
        "choose_download_folder": "اختر فولدر",
        "paste": "لصق",
        "copy": "نسخ",
        "cut": "قص",
        "select_all": "تحديد الكل",
        "youtube_url_required": "اكتب رابط يوتيوب الأول.",
        "youtube_fetching": "جاري جلب جودات يوتيوب...",
        "youtube_downloading": "جاري التحميل من يوتيوب...",
        "youtube_ready": "اختار الجودة ثم ابدأ التحميل.",
        "youtube_no_formats": "لم يتم العثور على جودات قابلة للتحميل.",
        "branding_dialog_title": "تخصيص أبعاد وهوية الفيديو وإعدادات الإخراج",
        "branding_aspect_group": "الأبعاد ونسبة العرض إلى الارتفاع",
        "branding_aspect_ratio": "أبعاد الفيديو:",
        "branding_fit_mode": "طريقة الملء:",
        "branding_logo_group": "إضافة لوجو أو علامة مائية",
        "branding_logo_enable": "تفعيل إضافة لوجو / علامة مائية على الفيديو",
        "branding_logo_file": "صورة اللوجو:",
        "branding_logo_pos": "المكان:",
        "branding_logo_opacity": "الشفافية:",
        "branding_title_group": "عنوان / شريط نصي للفيديو",
        "branding_title_enable": "تفعيل إضافة شريط عنوان على الفيديو",
        "branding_title_text": "نص العنوان:",
        "branding_title_bg": "لون الخلفية:",
        "branding_title_color": "لون الخط:",
        "branding_burn_subtitles_chk": "دمج وحرق الترجمة على الفيديو المخرَج",
        "branding_preview_title": "معاينة مرئية تفاعلية للفيديو",
        "branding_btn": "⚙️ الهوية والنصوص...",
        "trim_burn_subtitles": "دمج الترجمة",
        "trim_add_logo": "إضافة لوجو",
        "trim_add_title": "إضافة عنوان",
        "trim_color_grading": "تصحيح الألوان",
        "trim_remove_silence": "✂️ حذف السكتات",
        "btn_color_grading": "🎨 ضبط الألوان...",
        "btn_silence_studio": "✂️ استوديو السكتات...",
        "color_grading_summary": "ألوان مصححة",
        "trim_aspect_ratio": "أبعاد الفيديو:",
        "branding_add_text": "➕ إضافة نص جديد",
        "branding_delete_text": "🗑️ حذف هذا النص",
        "branding_canvas_hint": "🖱️ اضغط على العنصر لتحديده. اسحب الإطار الأبيض للتحريك، أو المربعات البيضاء للتكبير والتصغير.",
        "branding_subs_sample": "معاينة شكل الترجمة على الفيديو",
        "master_export_btn": "🎬 تصدير الفيديو",
        "master_export_desc": "تصدير الفيديو بالتعديلات المختارة، ضغط الحجم بجودة ممتازة، قص السكتات، الأبعاد، والشعار.",
        "master_export_summary": "التعديلات النشطة:",
        "master_export_done": "تم تصدير الفيديو بنجاح!",
        "trim_style_group": "الأبعاد والترجمة والألوان وتقطيع السكتات",
        "master_export_card": "تصدير الفيديو",
        "view_log_btn": "عرض السجل",
        "video_required": "يرجى اختيار ملف فيديو أولاً.",
        "theme_dark": "الوضع الليلي",
        "theme_light": "الوضع النهاري",
        "toggle_theme": "المظهر",
        "snapshot_btn": "📸 لقطة شاشة",
        "snapshot_saved": "تم حفظ لقطة الشاشة بجودة عالية: {filename}",
        "silence_settings_group": "✂️ إعدادات الاكتشاف الذكي وتقطيع السكتات (Jump Cut)",
        "silence_results_group": "📊 الخط الزمني المرئي وقائمة السكتات المكتشفة",
        "silence_preset_label": "الوضع الجاهز:",
        "silence_mode_label": "طريقة التعامل:",
        "silence_threshold_label": "حد السكون (dB):",
        "silence_auto_threshold": "✨ تحديد ذكي للحد",
        "silence_min_dur_label": "أقل مدة للسكتة (ث):",
        "silence_padding_label": "هامش أمان الكلام (ث):",
        "silence_quality_label": "جودة الفيديو والضغط:",
        "silence_format_label": "صيغة التصدير:",
        "silence_analyze_btn": "🔍 فحص السكتات الآن",
        "silence_export_btn": "✂️ بدء تقطيع السكتات وتصدير الملف",
        "silence_sync_subs_chk": "🔄 مزامنة الترجمة تلقائياً مع القص",
        "silence_save_synced_srt": "💾 حفظ ملف ترجمة متزامن (.SRT)",
        "silence_select_all": "تحديد الكل",
        "silence_deselect_all": "إلغاء الكل",
        "silence_analyzing": "جاري فحص الصوت واكتشاف أماكن السكتات...",
        "silence_exporting": "جاري قص السكتات وتصدير الملف بدون توقف...",
        "silence_ready_hint": "📊 السكتات المكتشفة: 0 — اضغط على زر [🔍 فحص السكتات الآن] لبدء الكشف",
        "silence_summary_fmt": "✅ تم اكتشاف {count} سكتة | المدة الأصلية: {orig} ⬅ الجديدة: {new} | توفير: {saved} ({pct}%)",
        "silence_none_found": "لم يتم العثور على سكتات عند حد {db} dB. جرب رفع الحد قليلاً (مثلاً -28 dB).",
        "silence_empty_list": "لم يتم فحص السكتات بعد. اضغط على '🔍 فحص السكتات الآن' لعرض المقاطع والتحكم بها.",
        "silence_item_label": "#{idx}  [{start} ⬅ {end}]   مدة السكتة: {dur} ثانية",
        "silence_cut_chk": "قص / تفعيل",
        "silence_preview_seg": "▶ معاينة",
        "silence_done_msg": "تم تقطيع السكتات بنجاح! الملف المحفوظ: {filename}",
        "fade_in_label": "تدرج الدخول (ث):",
        "fade_out_label": "تدرج الخروج (ث):",
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

VIDEO_FORMAT_LABELS = {
    "English": {
        ".mp4": ".mp4 - MP4",
        ".mkv": ".mkv - MKV",
        ".avi": ".avi - AVI",
        ".mov": ".mov - MOV",
        ".webm": ".webm - WEBM",
        ".wmv": ".wmv - WMV",
        ".flv": ".flv - FLV",
        ".3gp": ".3gp - 3GP",
        "original": "Keep original format",
    },
    "العربية": {
        ".mp4": ".mp4 - MP4",
        ".mkv": ".mkv - MKV",
        ".avi": ".avi - AVI",
        ".mov": ".mov - MOV",
        ".webm": ".webm - WEBM",
        ".wmv": ".wmv - WMV",
        ".flv": ".flv - FLV",
        ".3gp": ".3gp - 3GP",
        "original": "الحفاظ على نفس الصيغة",
    },
}

VIDEO_COMPRESSION_LABELS = {
    "English": {
        "Original": "No compression (Original)",
        "Very High": "Very high quality",
        "High": "High quality",
        "Medium": "Medium",
        "Small": "Small",
        "Very Small": "Very small",
    },
    "العربية": {
        "Original": "بدون ضغط (نفس الجودة)",
        "Very High": "أعلى جودة",
        "High": "جودة عالية",
        "Medium": "متوسط",
        "Small": "صغير",
        "Very Small": "صغير جداً",
    },
}

VIDEO_RESOLUTION_LABELS = {
    "English": {
        "Original": "Original",
        "1080p": "1080p",
        "720p": "720p",
        "480p": "480p",
        "360p": "360p",
    },
    "العربية": {
        "Original": "الأصلية",
        "1080p": "1080p",
        "720p": "720p",
        "480p": "480p",
        "360p": "360p",
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



from ui_dialogs import (
    SubtitleStyleDialog,
    VideoBrandingDialog,
    CaptionStudioDialog,
    VideoColorDialog,
    VideoTransitionDialog,
    IconPickerDialog,
    DaVinciTimelinePanel,
)
from video_studio.transitions import (
    DEFAULT_TRANSITIONS_CONFIG,
    TRANSITION_PRESETS,
    TRANSITION_CATEGORIES,
    get_transition_info,
    list_transitions_by_category,
)
from video_studio.aspect_ratios import (
    ASPECT_RATIOS,
    FIT_MODES,
    clamp_pan_for_transform,
    render_transformed_pil_frame,
)
from video_studio.color_grading import (
    COLOR_PRESETS,
    AUTO_COLOR_MODES,
    DEFAULT_COLOR_CONFIG,
    auto_analyze_and_correct,
    is_color_neutral,
    extract_video_sample_frame,
    apply_color_to_image,
)
from video_studio.branding import (
    BANNER_BG_COLORS,
    BANNER_TEXT_COLORS,
    AVAILABLE_FONTS,
    render_text_card_pil,
)
from video_studio.icons_library import (
    ICON_PRESETS,
    apply_opacity_and_rotation,
    render_media_overlay_pil,
)
from video_studio.timeline_engine import (
    NLEProjectState,
    FastVideoPreviewProvider,
    extract_audio_waveform_peaks,
    parse_srt_segments,
)
from video_studio.arabic_support import prepare_arabic_for_rendering
from video_studio.silence_remover import (
    SILENCE_PRESETS,
    SILENCE_MODES,
    SILENCE_QUALITIES,
    SILENCE_FORMATS,
    summarize_silence_analysis,
    compute_speech_segments,
    remap_subtitles_for_cuts,
)
from video_studio.session_manager import (
    AUTOSAVE_FILE,
    save_session_state,
    load_session_state,
    has_recoverable_session,
    mark_clean_exit,
    clear_autosave,
    save_project_file,
    load_project_file,
    get_recent_projects,
    get_recent_media,
    add_recent_media,
)
from video_studio.license_manager import (
    check_license_status,
    activate_license_key,
    ActivationDialog,
    get_hardware_id,
    format_plan_name,
)
from video_studio.tooltip import add_tooltip
from ui_modules import (
    MasterExportMixin,
    StudioCanvasMixin,
    StudioInspectorMixin,
    PlaybackSyncMixin,
    AudioMasteringMixin,
    SilenceWorkflowMixin,
    SubtitlesMixin,
)


class SongCoverApp(
    MasterExportMixin,
    StudioCanvasMixin,
    StudioInspectorMixin,
    PlaybackSyncMixin,
    AudioMasteringMixin,
    SilenceWorkflowMixin,
    SubtitlesMixin,
    tk.Tk,
):
    def __init__(self):
        super().__init__()
        self.title("ClipCraft Studio")
        self.geometry("1280x820")
        self.minsize(1050, 680)

        try:
            ico_path = APP_DIR / "app_icon.ico"
            if ico_path.exists():
                self.iconbitmap(str(ico_path))
        except Exception:
            pass

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

        # Universal App-Wide Undo/Redo Engine & Step Auto-Save
        self._app_undo_stack: List[Dict[str, Any]] = []
        self._app_redo_stack: List[Dict[str, Any]] = []
        self._is_restoring_state: bool = False
        self._last_step_autosave_ts: float = 0.0
        self._col_slider_drag_undo_recorded: bool = False

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
        if speed not in {"0.50x", "0.75x", "1.00x", "1.25x", "1.50x", "1.75x", "2.00x"}:
            speed = "1.00x"
        video_format = self.settings.get("video_format")
        if video_format not in convert.VIDEO_OUTPUT_FORMATS and video_format != "original":
            video_format = ".mp4"
        video_compression = self.settings.get("video_compression")
        if video_compression not in convert.VIDEO_COMPRESSION_PRESETS:
            video_compression = "Original"
        video_resolution = self.settings.get("video_resolution")
        if video_resolution not in convert.VIDEO_RESOLUTION_PRESETS:
            video_resolution = "Original"

        theme = self.settings.get("theme")
        if theme not in ("dark", "light"):
            theme = "dark" if self._detect_windows_dark_mode() else "light"
        self.theme_var = tk.StringVar(value=theme)

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
        self.trim_extract_audio_var = tk.BooleanVar(value=False)
        self.timeline_var = tk.DoubleVar(value=0)
        self.timeline_text_var = tk.StringVar(value="00:00 / 00:00")
        self.speed_var = tk.StringVar(value=speed)
        self.volume_var = tk.IntVar(value=100)
        self.quality_var = tk.StringVar(value=quality)
        self.language_var = tk.StringVar(value=language)
        self.video_format_key = video_format
        self.video_format_var = tk.StringVar(value=video_format)
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
        self._cover_thumb_photo = None
        self.enhancement_key = "Off"
        self.enhancement_var = tk.StringVar(value="Off")
        self.format_options = [
            f"{ext} - {info['label']}" for ext, info in convert.OUTPUT_FORMATS.items()
        ]
        self.output_format_var = tk.StringVar(value=".mp3 - MP3")
        self.busy_widgets = []
        self.i18n_widgets = {}

        # Volume Booster & Audio Mastering state
        self.boost_gain_var = tk.DoubleVar(value=6.0)
        self.boost_gain_label_var = tk.StringVar(value="+6.0 dB (200% / Double)")
        self.boost_anti_clip_var = tk.BooleanVar(value=True)
        self.boost_stats_var = tk.StringVar(value="")
        self.boost_output_format_var = tk.StringVar(value="auto")
        self.boost_fade_in_var = tk.StringVar(value="0.0")
        self.boost_fade_out_var = tk.StringVar(value="0.0")

        # Auto Silence Cut / Smart Jump-Cut Studio state
        sil_cfg = self.settings.get("silence_config", {})
        self.silence_preset_key = sil_cfg.get("preset", "natural")
        if self.silence_preset_key not in SILENCE_PRESETS:
            self.silence_preset_key = "natural"
        self.silence_mode_key = sil_cfg.get("mode", "remove")
        if self.silence_mode_key not in SILENCE_MODES:
            self.silence_mode_key = "remove"
        self.silence_preset_var = tk.StringVar(value="")
        self.silence_mode_var = tk.StringVar(value="")
        self.silence_quality_key = sil_cfg.get("video_quality", "original")
        if self.silence_quality_key not in SILENCE_QUALITIES:
            self.silence_quality_key = "original"
        self.silence_format_key = sil_cfg.get("export_format", "same")
        if self.silence_format_key not in SILENCE_FORMATS:
            self.silence_format_key = "same"
        self.silence_quality_var = tk.StringVar(value="")
        self.silence_format_var = tk.StringVar(value="")
        self.silence_noise_db_var = tk.DoubleVar(value=float(sil_cfg.get("noise_db", -35.0)))
        self.silence_noise_label_var = tk.StringVar(value=f"{float(sil_cfg.get('noise_db', -35.0)):.1f} dB")
        self.silence_min_dur_var = tk.StringVar(value=str(sil_cfg.get("min_silence_sec", "0.50")))
        self.silence_padding_var = tk.StringVar(value=str(sil_cfg.get("padding_sec", "0.15")))
        self.silence_sync_subs_var = tk.BooleanVar(value=bool(sil_cfg.get("sync_subtitles", True)))
        self.silence_summary_var = tk.StringVar(value="")
        self.silence_analysis_result = None
        self.silence_row_vars = []

        # Auto Caption / Speech-to-Text state
        self.caption_model_var = tk.StringVar(value="small")
        self.caption_model_status_var = tk.StringVar(value="")
        self.caption_models_dir_var = tk.StringVar(value=str(convert.get_whisper_models_dir()))
        self.caption_lang_var = tk.StringVar(value="auto")
        self.caption_translate_var = tk.StringVar(value="")
        self.caption_export_srt_var = tk.BooleanVar(value=True)
        self.caption_export_vtt_var = tk.BooleanVar(value=True)
        self.caption_export_txt_var = tk.BooleanVar(value=True)
        self.caption_burn_var = tk.BooleanVar(value=False)
        self.caption_view_mode_var = tk.StringVar(value="bubbles")
        self.caption_status_var = tk.StringVar(value="")
        self.caption_current_result = None
        self.caption_segments_accumulated = []
        self.caption_cancel_event = threading.Event()
        self.caption_thread = None

        # Subtitle Style and Segment Bubbles state
        self.subtitle_style = self.settings.get("subtitle_style", {
            "font_name": "Segoe UI",
            "font_size": "26",
            "text_color": "yellow",
            "outline_style": "box_semi",
            "bold": True,
            "italic": False,
            "position_v": "bottom",
            "position_h": "center",
            "margin_v": 35,
        })
        self.bubble_current_page = 0
        self.bubble_page_size = 25
        self.bubble_search_var = tk.StringVar(value="")
        self.bubble_search_var.trace_add("write", lambda *_: self._on_bubble_search_changed())
        self.bubble_card_widgets = []
        self.current_project_file = None
        self.export_encoder_key = "auto"
        self.export_encoder_combo_var = tk.StringVar(value="")

        # Video Branding, Aspect Ratio & DaVinci Reels Transform state
        self.video_branding_config = self.settings.get("video_branding_config", {
            "aspect_ratio": "original",
            "fit_mode": "fit",
            "video_zoom": 1.0,
            "video_pan_x": 0.0,
            "video_pan_y": 0.0,
            "video_flip_h": False,
            "video_clamp_edges": True,
            "show_safe_grid": False,
            "logo_enabled": False,
            "logo_path": "",
            "logo_position": "top_right",
            "logo_scale": 0.15,
            "logo_opacity": 1.0,
            "title_enabled": False,
            "title_text": "",
            "title_position": "top",
            "title_bg": "black",
            "title_color": "white",
            "burn_subtitles": False,
            "remove_silence": False,
            "davinci_fill_migrated": True,
        })
        if not self.video_branding_config.get("davinci_fill_migrated"):
            if self.video_branding_config.get("fit_mode") == "pad":
                self.video_branding_config["fit_mode"] = "crop"
            self.video_branding_config["davinci_fill_migrated"] = True
        self.video_branding_config.setdefault("fit_mode", "crop")
        self.video_branding_config.setdefault("video_zoom", 1.0)
        self.video_branding_config.setdefault("video_pan_x", 0.0)
        self.video_branding_config.setdefault("video_pan_y", 0.0)
        self.video_branding_config.setdefault("video_flip_h", False)
        self.video_branding_config.setdefault("video_clamp_edges", True)

        self.trim_aspect_var = tk.StringVar(value=self.video_branding_config.get("aspect_ratio", "original"))
        self.trim_burn_subs_var = tk.BooleanVar(value=False)
        self.trim_logo_var = tk.BooleanVar(value=self.video_branding_config.get("logo_enabled", False))
        self.trim_title_var = tk.BooleanVar(value=self.video_branding_config.get("title_enabled", False))
        color_cfg = self.video_branding_config.get("color_config", {})
        self.trim_color_var = tk.BooleanVar(value=False)
        if isinstance(color_cfg, dict):
            color_cfg["enabled"] = False
        self.trim_remove_silence_var = tk.BooleanVar(value=False)
        trans_cfg = self.video_branding_config.get("transitions_config")
        if not isinstance(trans_cfg, dict):
            trans_cfg = dict(DEFAULT_TRANSITIONS_CONFIG)
            self.video_branding_config["transitions_config"] = trans_cfg
        self.trans_enable_var = tk.BooleanVar(value=bool(trans_cfg.get("enabled", False)))
        self.trim_trans_var = self.trans_enable_var
        self.trans_dur_var = tk.DoubleVar(value=float(trans_cfg.get("default_duration", 0.5)))
        self.trans_audio_var = tk.BooleanVar(value=bool(trans_cfg.get("audio_crossfade", True)))

        self.master_export_summary_var = tk.StringVar(value="")

        # DaVinci Multi-Track NLE State & Fast PyAV Preview Engine
        self.nle_project = NLEProjectState()
        self.nle_project.on_push_undo_cb = self._on_nle_undo_pushed
        self.nle_project.reset_for_media(None, 0.0)
        self.fast_preview = FastVideoPreviewProvider()
        self.nle_playhead_sec = 0.0
        self.active_playback_clip_idx = 0
        self.studio_live_preview_mode = True
        self._preview_decode_busy = False

        # Player Studio Canvas, Render Cache & Dynamic Context-Sensitive Inspector State
        self.active_inspector_context = "video"
        self.export_opt_framing_var = tk.BooleanVar(value=False)
        self.export_opt_timeline_var = tk.BooleanVar(value=False)
        self.export_opt_overlays_var = tk.BooleanVar(value=False)
        self.export_opt_audio_fx_var = tk.BooleanVar(value=False)
        self.export_opt_transcript_files_var = tk.BooleanVar(value=False)
        self.export_format_key = "same"
        self.export_size_key = "Match Source"
        self.player_canvas_element_boxes = {}
        self.player_canvas_selected = None  # e.g. ("V3", 0), ("V2", 1), ("V4", 0), or ("clip", 0)
        self.player_canvas_drag_mode = None
        self.player_canvas_drag_start = (0, 0)
        self.player_canvas_drag_orig_pos = (0.0, 0.0)
        self.player_canvas_drag_orig_scale = 1.0
        self.player_canvas_drag_orig_rot = 0.0
        self._snap_guide_x = False
        self._snap_guide_y = False
        self._cached_player_frame = None
        self._cached_player_frame_ts = -1.0
        self._cached_player_frame_path = None
        self._player_photo_image = None
        self._player_logo_photo = None
        self._overlay_photo_refs = []
        self._overlay_pil_cache = {}
        self._studio_video_img_id = None
        self._last_studio_scene_sig = None
        self._ready_composed_video = None
        self._studio_paint_pending = False
        self._in_gap_playback = False
        self._gap_last_wall_ts = 0.0
        self._player_canvas_video_box = (0, 0, 100, 100)

        self._build_ui()
        self.youtube_url_var.trace_add("write", self._youtube_url_changed)
        self._apply_language()
        self._refresh_youtube_details()
        self._update_run_state()
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self.after(100, self._drain_messages)
        self.after(350, self._check_and_prompt_crash_recovery)
        self.after(450, self._check_and_enforce_license)
        self.after(3500, self._startup_update_check)

        # Ensure window is brought to foreground upon launch without aggressive focus stealing
        try:
            self.lift()
        except Exception:
            pass

        # Pre-warm VLC instance in background thread for instantaneous hardware video/audio playback
        threading.Thread(target=self._prewarm_vlc, daemon=True).start()

    def _prewarm_vlc(self):
        try:
            if vlc is None:
                return
            if self.vlc_instance is None:
                self.vlc_instance = vlc.Instance(
                    "--no-video-title-show",
                    "--no-plugins-cache",
                    "--quiet",
                    "--no-stats",
                    "--no-mouse-events",
                    "--no-keyboard-events",
                    "--avcodec-hw=any",
                    "--avcodec-threads=0",
                    "--file-caching=1500",
                    "--network-caching=1500",
                    "--disc-caching=1500",
                    "--drop-late-frames",
                    "--skip-frames",
                )
            if self.media_player is None and self.vlc_instance:
                self.media_player = self.vlc_instance.media_player_new()
        except Exception:
            pass

    def _load_settings(self):
        try:
            if SETTINGS_PATH.exists():
                return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _save_settings(self):
        if hasattr(self, "nle_project") and hasattr(self, "video_branding_config"):
            if self.nle_project.logo_items:
                l0 = self.nle_project.logo_items[0]
                self.video_branding_config["logo_path"] = l0.get("path", "")
                self.video_branding_config["logo_x"] = l0.get("x", 0.82)
                self.video_branding_config["logo_y"] = l0.get("y", 0.04)
                self.video_branding_config["logo_scale"] = l0.get("scale", 0.16)
                self.video_branding_config["logo_opacity"] = l0.get("opacity", 1.0)
                self.video_branding_config["logo_rotation"] = l0.get("rotation", 0.0)
        self.settings["last_media_dir"] = str(self.last_media_dir)
        self.settings["last_cover_dir"] = str(self.last_cover_dir)
        self.settings["youtube_output_dir"] = str(self.youtube_output_dir_path)
        self.settings["language"] = self.language_var.get()
        self.settings["quality"] = self.quality_var.get()
        self.settings["speed"] = self.speed_var.get()
        self.settings["video_format"] = self.video_format_key
        self.settings["video_compression"] = self.video_compression_key
        self.settings["video_resolution"] = self.video_resolution_key
        self.settings["subtitle_style"] = getattr(self, "subtitle_style", {})
        self.settings["video_branding_config"] = getattr(self, "video_branding_config", {})
        self.settings["silence_config"] = {
            "preset": getattr(self, "silence_preset_key", "natural"),
            "mode": getattr(self, "silence_mode_key", "remove"),
            "video_quality": getattr(self, "silence_quality_key", "original"),
            "export_format": getattr(self, "silence_format_key", "same"),
            "noise_db": round(float(self.silence_noise_db_var.get()), 1) if hasattr(self, "silence_noise_db_var") else -35.0,
            "min_silence_sec": self.silence_min_dur_var.get() if hasattr(self, "silence_min_dur_var") else "0.50",
            "padding_sec": self.silence_padding_var.get() if hasattr(self, "silence_padding_var") else "0.15",
            "sync_subtitles": bool(self.silence_sync_subs_var.get()) if hasattr(self, "silence_sync_subs_var") else True,
        }
        self.settings["theme"] = self.theme_var.get()
        try:
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS_PATH.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    @staticmethod
    def _detect_windows_dark_mode() -> bool:
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            ) as key:
                val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return val == 0
        except Exception:
            return False

    @classmethod
    def _set_window_immersive_dark_mode(cls, window, is_dark: bool):
        try:
            import ctypes
            if not window or not window.winfo_exists():
                return
            window.update_idletasks()
            wid = window.winfo_id()
            hwnd = ctypes.windll.user32.GetAncestor(wid, 2) or ctypes.windll.user32.GetParent(wid) or wid
            if hwnd:
                val = ctypes.c_int(1 if is_dark else 0)
                # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 11 and Windows 10 build 19041+)
                res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 20, ctypes.byref(val), ctypes.sizeof(val)
                )
                if res != 0:
                    # DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19 (Windows 10 1809 - 1909)
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd, 19, ctypes.byref(val), ctypes.sizeof(val)
                    )
                # DWMWA_CAPTION_COLOR = 35 (Windows 11 build 22000+) - explicitly set titlebar color
                if is_dark:
                    cap_color = ctypes.c_uint(0x00201B18)  # #181b20 in BGR format
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd, 35, ctypes.byref(cap_color), ctypes.sizeof(cap_color)
                    )
                    txt_color = ctypes.c_uint(0x00F3EDE6)  # #e6edf3 in BGR format
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd, 36, ctypes.byref(txt_color), ctypes.sizeof(txt_color)
                    )
                else:
                    cap_color = ctypes.c_uint(0x00F0F0F0)  # #f0f0f0 in BGR format
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd, 35, ctypes.byref(cap_color), ctypes.sizeof(cap_color)
                    )
                    txt_color = ctypes.c_uint(0x001A1A1A)  # #1a1a1a in BGR format
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd, 36, ctypes.byref(txt_color), ctypes.sizeof(txt_color)
                    )

                # Force Windows DWM to redraw the non-client frame (title bar) immediately
                ctypes.windll.user32.SetWindowPos(
                    hwnd, 0, 0, 0, 0, 0,
                    0x0002 | 0x0001 | 0x0004 | 0x0020  # SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED
                )
        except Exception:
            pass

    def _reapply_dark_titlebar(self):
        is_dark = getattr(self, "theme_var", None) and self.theme_var.get() == "dark"
        self._set_window_immersive_dark_mode(self, is_dark)
        self.after(50, lambda: self._set_window_immersive_dark_mode(self, is_dark))
        self.after(200, lambda: self._set_window_immersive_dark_mode(self, is_dark))

    def _on_window_map(self, event):
        if event.widget == self:
            is_dark = getattr(self, "theme_var", None) and self.theme_var.get() == "dark"
            self._set_window_immersive_dark_mode(self, is_dark)

    def _apply_theme_to_toplevel(self, window):
        is_dark = getattr(self, "theme_var", None) and self.theme_var.get() == "dark"
        bg = "#181b20" if is_dark else "#f0f0f0"
        try:
            window.configure(bg=bg)
        except Exception:
            pass
        self._set_window_immersive_dark_mode(window, is_dark)

    def toggle_theme(self):
        new_theme = "light" if self.theme_var.get() == "dark" else "dark"
        self.theme_var.set(new_theme)
        self._apply_theme()
        self._save_settings()

    def _update_theme_button_text(self):
        if not hasattr(self, "theme_button"):
            return
        is_dark = self.theme_var.get() == "dark"
        is_ar = self.language_var.get() == "العربية"
        if is_dark:
            self.theme_button.configure(text="☀️ " + ("الوضع النهاري" if is_ar else "Light Mode"))
        else:
            self.theme_button.configure(text="🌙 " + ("الوضع الليلي" if is_ar else "Dark Mode"))

    def _apply_theme(self):
        theme = self.theme_var.get() if hasattr(self, "theme_var") else "light"
        is_dark = (theme == "dark")

        self._update_theme_button_text()

        style = ttk.Style(self)
        if is_dark:
            try:
                style.theme_use("clam")
            except Exception:
                pass

            bg = "#181b20"
            card_bg = "#1f242d"
            fg = "#e6edf3"
            muted_fg = "#8b949e"
            border_col = "#343b47"
            border_hover = "#485263"
            input_bg = "#252b36"
            btn_bg = "#2b323f"
            btn_hover = "#363e4f"
            btn_pressed = "#1c212a"
            player_btn_bg = "#232832"
            player_btn_hover = "#313745"
            accent_blue = "#1f6feb"
            accent_blue_hover = "#388bfd"
            accent_green = "#238636"
            accent_green_hover = "#2ea043"

            self.configure(bg=bg)

            # Global Style defaults
            style.configure(".", background=bg, foreground=fg, bordercolor=border_col, lightcolor=border_col, darkcolor=border_col)
            style.configure("TFrame", background=bg)
            style.configure("TLabel", background=bg, foreground=fg)
            style.configure("TLabelframe", background=bg, bordercolor=border_col, lightcolor=border_col, darkcolor=border_col)
            style.configure("TLabelframe.Label", background=bg, foreground=fg, font=("Segoe UI", 9, "bold"))

            # Buttons
            style.configure("TButton", background=btn_bg, foreground=fg, bordercolor=border_col, lightcolor=border_col, darkcolor=border_col, padding=(5, 3))
            style.map("TButton",
                background=[("pressed", btn_pressed), ("active", btn_hover), ("disabled", bg)],
                foreground=[("disabled", muted_fg), ("active", fg)],
                bordercolor=[("active", border_hover)]
            )

            style.configure("Player.TButton", background=player_btn_bg, foreground=fg, bordercolor=border_col, lightcolor=border_col, darkcolor=border_col, font=("Segoe UI", 9), padding=(4, 2))
            style.map("Player.TButton",
                background=[("pressed", btn_pressed), ("active", player_btn_hover), ("disabled", bg)],
                foreground=[("disabled", muted_fg), ("active", fg)],
                bordercolor=[("active", border_hover)]
            )

            style.configure("PrimaryPlayer.TButton", background=accent_blue, foreground="#ffffff", bordercolor=border_col, lightcolor=border_col, darkcolor=border_col, font=("Segoe UI", 10, "bold"), padding=(6, 4))
            style.map("PrimaryPlayer.TButton",
                background=[("pressed", "#1158c7"), ("active", accent_blue_hover), ("disabled", bg)],
                foreground=[("disabled", muted_fg), ("active", "#ffffff")]
            )

            style.configure("Action.TButton", background=accent_green, foreground="#ffffff", bordercolor=border_col, lightcolor=border_col, darkcolor=border_col, font=("Segoe UI", 10, "bold"), padding=(8, 4))
            style.map("Action.TButton",
                background=[("pressed", "#1a6328"), ("active", accent_green_hover), ("disabled", bg)],
                foreground=[("disabled", muted_fg), ("active", "#ffffff")]
            )

            # Notebook & Tabs
            style.configure("TNotebook", background=bg, bordercolor=border_col, tabmargins=[2, 4, 2, 0])
            style.configure("TNotebook.Tab", background="#14171c", foreground=muted_fg, padding=[12, 5], bordercolor=border_col, lightcolor=border_col)
            style.map("TNotebook.Tab",
                background=[("selected", card_bg), ("active", btn_bg)],
                foreground=[("selected", fg), ("active", fg)]
            )

            # Entry, Spinbox & Combobox
            style.configure("TEntry", fieldbackground=input_bg, foreground=fg, insertcolor=fg, bordercolor=border_col, lightcolor=border_col, darkcolor=border_col, padding=3)
            style.configure("TSpinbox", fieldbackground=input_bg, background=btn_bg, foreground=fg, arrowcolor=fg, bordercolor=border_col, lightcolor=border_col, darkcolor=border_col, insertcolor=fg, padding=3)
            style.map("TSpinbox",
                fieldbackground=[("readonly", input_bg), ("disabled", bg), ("active", input_bg)],
                foreground=[("disabled", muted_fg), ("active", fg)],
                arrowcolor=[("disabled", muted_fg), ("active", "#58a6ff")],
                bordercolor=[("focus", accent_blue), ("active", border_hover)],
            )
            style.configure("TCombobox", fieldbackground=input_bg, background=btn_bg, foreground=fg, arrowcolor=fg, bordercolor=border_col, lightcolor=border_col, darkcolor=border_col, padding=2)
            style.map("TCombobox",
                fieldbackground=[("readonly", input_bg), ("disabled", bg)],
                foreground=[("readonly", fg), ("disabled", muted_fg)],
                selectbackground=[("readonly", accent_blue)],
                selectforeground=[("readonly", "#ffffff")]
            )

            # Checkbutton & Radiobutton
            style.configure("TCheckbutton", background=bg, foreground=fg, indicatorbackground=input_bg, indicatorforeground="#388bfd", upperbordercolor=border_col, lowerbordercolor=border_col)
            style.map("TCheckbutton",
                background=[("active", bg)],
                foreground=[("active", fg), ("disabled", muted_fg)],
                indicatorbackground=[("selected", accent_blue), ("pressed", input_bg)],
                indicatorforeground=[("selected", "#ffffff")]
            )
            style.configure("TRadiobutton", background=bg, foreground=fg, indicatorbackground=input_bg, indicatorforeground="#388bfd", upperbordercolor=border_col, lowerbordercolor=border_col)
            style.map("TRadiobutton",
                background=[("active", bg)],
                foreground=[("active", fg), ("disabled", muted_fg)],
                indicatorbackground=[("selected", accent_blue), ("pressed", input_bg)],
                indicatorforeground=[("selected", "#ffffff")]
            )

            # Scale, Progressbar, Scrollbar, Separator
            style.configure("Horizontal.TScale", background=bg, troughcolor=input_bg, sliderrelief="flat", bordercolor=border_col)
            style.configure("Horizontal.TProgressbar", background=accent_green, troughcolor=input_bg, bordercolor=border_col)
            style.configure("Vertical.TScrollbar", background=btn_bg, troughcolor=bg, bordercolor=border_col, arrowcolor=fg)
            style.map("Vertical.TScrollbar", background=[("active", btn_hover)])
            style.configure("Horizontal.TScrollbar", background=btn_bg, troughcolor=bg, bordercolor=border_col, arrowcolor=fg)
            style.map("Horizontal.TScrollbar", background=[("active", btn_hover)])
            style.configure("TSeparator", background=border_col)

            # Combobox Popdown Listbox & Classic Spinbox/Entry options
            self.option_add("*TCombobox*Listbox.background", input_bg)
            self.option_add("*TCombobox*Listbox.foreground", fg)
            self.option_add("*TCombobox*Listbox.selectBackground", accent_blue)
            self.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
            self.option_add("*Spinbox.background", input_bg)
            self.option_add("*Spinbox.foreground", fg)
            self.option_add("*Spinbox.insertBackground", fg)
            self.option_add("*Spinbox.buttonBackground", btn_bg)
            self.option_add("*Spinbox.selectBackground", accent_blue)
            self.option_add("*Spinbox.selectForeground", "#ffffff")
            self.option_add("*TSpinbox*background", input_bg)
            self.option_add("*TSpinbox*foreground", fg)

            # Native Text & Canvas widgets
            if hasattr(self, "log"):
                self.log.configure(bg="#12151a", fg="#c9d1d9", insertbackground="#58a6ff", selectbackground=accent_blue, selectforeground="#ffffff")
            if hasattr(self, "caption_text_view"):
                self.caption_text_view.configure(bg="#12151a", fg="#c9d1d9", insertbackground="#58a6ff", selectbackground=accent_blue, selectforeground="#ffffff")
            if hasattr(self, "bubble_canvas"):
                self.bubble_canvas.configure(bg="#12151a", highlightbackground=border_col)
            if hasattr(self, "silence_list_canvas"):
                self.silence_list_canvas.configure(bg="#12151a", highlightbackground=border_col)

            # Colored Labels
            if hasattr(self, "i18n_widgets") and "subtitle" in self.i18n_widgets:
                self.i18n_widgets["subtitle"].configure(foreground=muted_fg)
            if hasattr(self, "output_val_label"):
                self.output_val_label.configure(foreground=muted_fg)
            if hasattr(self, "count_label"):
                self.count_label.configure(foreground="#58a6ff")
            if hasattr(self, "dev_label"):
                self.dev_label.configure(foreground=muted_fg)
            if hasattr(self, "video_estimate_label"):
                self.video_estimate_label.configure(foreground="#3fb950")
            if hasattr(self, "boost_stats_label"):
                self.boost_stats_label.configure(foreground="#58a6ff")
            if hasattr(self, "boost_gain_display"):
                self.boost_gain_display.configure(foreground="#ff7b72")
            if hasattr(self, "silence_noise_display"):
                self.silence_noise_display.configure(foreground="#ff7b72")
            if hasattr(self, "silence_summary_label"):
                self.silence_summary_label.configure(foreground="#58a6ff")
            if hasattr(self, "silence_time_badge"):
                self.silence_time_badge.configure(foreground="#3fb950")
            if hasattr(self, "silence_saved_badge"):
                self.silence_saved_badge.configure(foreground="#d29922")
            if hasattr(self, "caption_models_dir_path_label"):
                self.caption_models_dir_path_label.configure(foreground=muted_fg)
            if hasattr(self, "caption_status_label"):
                self.caption_status_label.configure(foreground="#58a6ff")
            if hasattr(self, "bubble_count_label"):
                self.bubble_count_label.configure(foreground="#58a6ff")
            if hasattr(self, "custom_cover_text_label"):
                self.custom_cover_text_label.configure(foreground=muted_fg)
            if hasattr(self, "youtube_detail_label"):
                self.youtube_detail_label.configure(foreground="#58a6ff")

        else:
            try:
                style.theme_use("vista")
            except Exception:
                try:
                    style.theme_use("clam")
                except Exception:
                    pass

            bg = "#f0f0f0"
            self.configure(bg=bg)

            # Standard style configurations for Light
            style.configure(".", background=bg, foreground="#000000")
            style.configure("TFrame", background=bg)
            style.configure("TLabel", background=bg, foreground="#000000")
            style.configure("TLabelframe", background=bg)
            style.configure("TLabelframe.Label", background=bg, foreground="#000000", font=("Segoe UI", 9, "bold"))
            style.configure("Player.TButton", font=("Segoe UI", 9), padding=(4, 2))
            style.configure("PrimaryPlayer.TButton", font=("Segoe UI", 10, "bold"), padding=(6, 4))
            style.configure("Action.TButton", font=("Segoe UI", 10, "bold"), padding=(8, 4))

            style.configure("TSpinbox", fieldbackground="#ffffff", background="#e1e1e1", foreground="#000000", arrowcolor="#000000", bordercolor="#adadad", padding=3)

            # Combobox Popdown Listbox & Spinbox options
            self.option_add("*TCombobox*Listbox.background", "#ffffff")
            self.option_add("*TCombobox*Listbox.foreground", "#000000")
            self.option_add("*TCombobox*Listbox.selectBackground", "#0078d7")
            self.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
            self.option_add("*Spinbox.background", "#ffffff")
            self.option_add("*Spinbox.foreground", "#000000")
            self.option_add("*Spinbox.insertBackground", "#000000")
            self.option_add("*Spinbox.buttonBackground", "#e1e1e1")

            # Native Text & Canvas widgets
            if hasattr(self, "log"):
                self.log.configure(bg="#ffffff", fg="#000000", insertbackground="#000000", selectbackground="#0078d7", selectforeground="#ffffff")
            if hasattr(self, "caption_text_view"):
                self.caption_text_view.configure(bg="#fafafa", fg="#000000", insertbackground="#000000", selectbackground="#0078d7", selectforeground="#ffffff")
            if hasattr(self, "bubble_canvas"):
                self.bubble_canvas.configure(bg="#f6f8fa", highlightbackground="#e1e4e8")
            if hasattr(self, "silence_list_canvas"):
                self.silence_list_canvas.configure(bg="#f6f8fa", highlightbackground="#e1e4e8")

            # Colored Labels
            if hasattr(self, "i18n_widgets") and "subtitle" in self.i18n_widgets:
                self.i18n_widgets["subtitle"].configure(foreground="#555555")
            if hasattr(self, "output_val_label"):
                self.output_val_label.configure(foreground="#555555")
            if hasattr(self, "count_label"):
                self.count_label.configure(foreground="#0066cc")
            if hasattr(self, "dev_label"):
                self.dev_label.configure(foreground="#555555")
            if hasattr(self, "video_estimate_label"):
                self.video_estimate_label.configure(foreground="#007700")
            if hasattr(self, "boost_stats_label"):
                self.boost_stats_label.configure(foreground="#0055aa")
            if hasattr(self, "boost_gain_display"):
                self.boost_gain_display.configure(foreground="#cc3300")
            if hasattr(self, "silence_noise_display"):
                self.silence_noise_display.configure(foreground="#cc3300")
            if hasattr(self, "silence_summary_label"):
                self.silence_summary_label.configure(foreground="#0066cc")
            if hasattr(self, "silence_time_badge"):
                self.silence_time_badge.configure(foreground="#2da44e")
            if hasattr(self, "silence_saved_badge"):
                self.silence_saved_badge.configure(foreground="#b08800")
            if hasattr(self, "caption_models_dir_path_label"):
                self.caption_models_dir_path_label.configure(foreground="#555555")
            if hasattr(self, "caption_status_label"):
                self.caption_status_label.configure(foreground="#0066cc")
            if hasattr(self, "bubble_count_label"):
                self.bubble_count_label.configure(foreground="#0969da")
            if hasattr(self, "custom_cover_text_label"):
                self.custom_cover_text_label.configure(foreground="#555555")
            if hasattr(self, "youtube_detail_label"):
                self.youtube_detail_label.configure(foreground="#0066cc")

        # Refresh caption bubbles if present
        if hasattr(self, "_refresh_bubbles_ui") and hasattr(self, "caption_current_result") and self.caption_current_result:
            try:
                self._refresh_bubbles_ui()
            except Exception:
                pass
        if hasattr(self, "_refresh_silence_ui"):
            try:
                self._refresh_silence_ui()
            except Exception:
                pass
        if hasattr(self, "_draw_player_visual_timeline"):
            try:
                self._draw_player_visual_timeline()
            except Exception:
                pass

        # Windows immersive dark titlebar for the root window
        self._set_window_immersive_dark_mode(self, is_dark)

        # Update any open toplevel dialog windows
        try:
            for child in self.winfo_children():
                if isinstance(child, tk.Toplevel):
                    self._apply_theme_to_toplevel(child)
        except Exception:
            pass

    def _dialog_dir(self, path):
        path = Path(path or APP_DIR)
        if path.is_file():
            path = path.parent
        return str(path if path.exists() else APP_DIR)

    def text(self, key, **kwargs):
        lang = self.language_var.get() if hasattr(self, "language_var") else "English"
        if lang not in TRANSLATIONS:
            lang = "English"
        val = TRANSLATIONS[lang].get(key, TRANSLATIONS["English"].get(key, key))
        return val.format(**kwargs) if kwargs else val

    def _build_ui(self):
        style = ttk.Style(self)
        style.configure("Player.TButton", font=("Segoe UI", 9), padding=(4, 2))
        style.configure("PrimaryPlayer.TButton", font=("Segoe UI", 10, "bold"), padding=(6, 4))
        style.configure("Action.TButton", font=("Segoe UI", 10, "bold"), padding=(8, 4))

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # ------------------ Row 0: Sleek Integrated Top Header Bar ------------------
        header = ttk.Frame(self, padding=(10, 6, 10, 6))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        hdr_left = ttk.Frame(header)
        hdr_left.pack(side="left", fill="y")

        self.i18n_widgets["title"] = ttk.Label(hdr_left, text=self.text("app_title"), font=("Segoe UI", 12, "bold"))
        self.i18n_widgets["title"].pack(side="left", padx=(0, 10))

        ttk.Separator(hdr_left, orient="vertical").pack(side="left", fill="y", padx=(0, 8))

        self.choose_file_button = ttk.Button(
            hdr_left,
            text="📁 " + self.text("choose_file"),
            command=self.choose_input_file,
            style="Action.TButton",
        )
        self.choose_file_button.pack(side="left", padx=(0, 4))
        add_tooltip(self.choose_file_button, "اختيار ملف صوتي أو فيديو للبدء في معالجته ومونتاجه", "Choose an audio or video file to start editing", app=self)

        self.choose_folder_button = ttk.Button(
            hdr_left,
            text="📁 " + self.text("choose_folder"),
            command=self.choose_input_folder,
            style="Player.TButton",
        )
        self.choose_folder_button.pack(side="left", padx=(0, 8))
        add_tooltip(self.choose_folder_button, "اختيار مجلد كامل لتحويل كافة الملفات بضغطة واحدة", "Select an entire folder for batch conversion", app=self)

        self.loaded_filename_var = tk.StringVar(value="")
        self.loaded_filename_label = ttk.Label(
            hdr_left,
            textvariable=self.loaded_filename_var,
            font=("Segoe UI", 9, "bold"),
            foreground="#2ea043",
        )
        self.loaded_filename_label.pack(side="left", padx=(0, 8))

        self.open_input_button = ttk.Button(
            hdr_left,
            text="📂 المصدر" if self.language_var.get() == "العربية" else "📂 Source",
            command=self.open_source,
            style="Player.TButton",
        )
        self.open_input_button.pack(side="left", padx=(0, 3))
        add_tooltip(self.open_input_button, "فتح المجلد الحاوي للملف الحالي في مستكشف ويندوز", "Open folder containing the input file", app=self)

        self.open_output_button = ttk.Button(
            hdr_left,
            text="📁 المخرجات" if self.language_var.get() == "العربية" else "📁 Output",
            command=lambda: self.open_folder(self.output_dir),
            style="Player.TButton",
        )
        self.open_output_button.pack(side="left", padx=(0, 3))
        add_tooltip(self.open_output_button, "فتح مجلد المخرجات حيث تُحفظ الملفات المصدرة", "Open the output export folder", app=self)

        self.restore_session_button = ttk.Button(
            hdr_left,
            text="🔄 استعادة" if self.language_var.get() == "العربية" else "🔄 Restore",
            command=self._manual_restore_session,
            style="Player.TButton",
        )
        self.restore_session_button.pack(side="left", padx=(0, 6))
        add_tooltip(self.restore_session_button, "استعادة التعديلات والملفات المفتوحة في آخر جلسة سابقة", "Restore previous session edits and timeline", app=self)

        hdr_right = ttk.Frame(header)
        hdr_right.pack(side="right", fill="y")

        self.settings_button = ttk.Button(
            hdr_right,
            command=self.show_settings_dialog,
            style="Player.TButton",
            width=11,
        )
        self.settings_button.pack(side="right", padx=(4, 0))
        self.i18n_widgets["settings_button"] = self.settings_button
        add_tooltip(self.settings_button, "فتح نافذة الإعدادات الشاملة للبرنامج والتخصيص", "Open application settings and preferences", app=self)

        self.about_button = ttk.Button(
            hdr_right,
            command=self.show_about_dialog,
            style="Player.TButton",
            width=9,
        )
        self.about_button.pack(side="right", padx=(4, 0))
        self.i18n_widgets["about_button"] = self.about_button
        add_tooltip(self.about_button, "معلومات عن البرنامج والإصدار وحقوق المطور", "About ClipCraft Studio and developer info", app=self)

        self.theme_button = ttk.Button(
            hdr_right,
            command=self.toggle_theme,
            style="Player.TButton",
            width=12,
        )
        self.theme_button.pack(side="right", padx=(4, 0))
        self.i18n_widgets["theme_button"] = self.theme_button
        add_tooltip(self.theme_button, "التبديل بين الوضع الليلي الداكن والوضع النهاري الفاتح (Ctrl+D)", "Toggle Dark / Light theme mode (Ctrl+D)", app=self)

        self.language_combo = ttk.Combobox(
            hdr_right,
            textvariable=self.language_var,
            values=list(TRANSLATIONS),
            state="readonly",
            width=9,
        )
        self.language_combo.pack(side="right", padx=(4, 0))
        self.language_combo.bind("<<ComboboxSelected>>", self._language_changed)
        add_tooltip(self.language_combo, "تغيير لغة الواجهة الفورية (العربية / English)", "Change user interface language", app=self)

        self.i18n_widgets["language_label"] = ttk.Label(hdr_right)
        self.i18n_widgets["language_label"].pack(side="right", padx=(8, 2))

        is_ar = (self.language_var.get() == "العربية")

        # Compact Shortcuts & Guide Button next to Language
        self.btn_shortcuts_guide = ttk.Button(
            hdr_right,
            text="💡 الاختصارات" if is_ar else "💡 Keys",
            command=self.open_shortcuts_guide_dialog,
            style="Player.TButton",
            width=11,
        )
        self.btn_shortcuts_guide.pack(side="right", padx=(6, 2))
        add_tooltip(self.btn_shortcuts_guide, "عرض الدليل الكامل لاختصارات لوحة المفاتيح والتحكم السريع", "Open keyboard shortcuts cheat sheet", app=self)

        ttk.Separator(hdr_right, orient="vertical").pack(side="right", fill="y", padx=(6, 6))

        # Project Management Controls (Save, Open, Recent) in Top Bar
        self.btn_recent_proj = ttk.Button(
            hdr_right,
            text="🕒 الأخيرة" if is_ar else "🕒 Recent",
            command=self.show_recent_projects_popup,
            style="Player.TButton",
        )
        self.btn_recent_proj.pack(side="right", padx=(2, 0))
        add_tooltip(self.btn_recent_proj, "قائمة المشاريع الأخيرة التي تم العمل عليها مؤخراً", "List of recent projects", app=self)

        self.btn_open_proj = ttk.Button(
            hdr_right,
            text="📂 فتح" if is_ar else "📂 Open",
            command=self.open_project,
            style="Player.TButton",
        )
        self.btn_open_proj.pack(side="right", padx=(2, 0))
        add_tooltip(self.btn_open_proj, "فتح مشروع مونتاج سابق محفوظ على جهازك (Ctrl+O)", "Open a saved project file (Ctrl+O)", app=self)

        self.btn_save_proj = ttk.Button(
            hdr_right,
            text="💾 حفظ" if is_ar else "💾 Save",
            command=self.save_project,
            style="Player.TButton",
        )
        self.btn_save_proj.pack(side="right", padx=(2, 0))
        add_tooltip(self.btn_save_proj, "حفظ المشروع والتعديلات والتايم لاين الحالي (Ctrl+S)", "Save current project and timeline (Ctrl+S)", app=self)

        # License / Trial Status Indicator Button
        self.btn_license_trial = ttk.Button(
            hdr_right,
            text="👑 الترخيص" if is_ar else "👑 License",
            command=self._show_license_dialog,
            style="Player.TButton",
        )
        self.btn_license_trial.pack(side="right", padx=(2, 6))
        add_tooltip(self.btn_license_trial, "عرض حالة التفعيل ورخصة البرنامج وفترة التجربة", "View license and activation status", app=self)

        # Hidden backward-compatibility holders for existing variable bindings
        self.i18n_widgets["subtitle"] = ttk.Label(self)
        _dummy_source_panel = ttk.LabelFrame(self)
        self.i18n_widgets["source_group"] = _dummy_source_panel
        self.i18n_widgets["output_label"] = ttk.Label(_dummy_source_panel)
        self.output_val_label = ttk.Label(_dummy_source_panel, textvariable=self.output_var)
        self.count_label = ttk.Label(_dummy_source_panel, textvariable=self.count_var)

        # ------------------ Row 1: Tabs Container (Notebook) ------------------
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=8, pady=(2, 6))

        self.tab_convert = ttk.Frame(self.notebook, padding=12)
        self.tab_volume = ttk.Frame(self.notebook, padding=12)
        self.tab_player = ttk.Frame(self.notebook, padding=10)
        self.tab_silence = ttk.Frame(self.notebook, padding=12)
        self.tab_caption = ttk.Frame(self.notebook, padding=12)
        self.tab_youtube = ttk.Frame(self.notebook, padding=12)
        self.tab_cover = self.tab_convert  # Consolidated into Convert & Cover tab

        self.notebook.add(self.tab_convert, text=self.text("tab_convert"))
        self.notebook.add(self.tab_volume, text=self.text("tab_volume"))
        self.notebook.add(self.tab_player, text=self.text("tab_player"))
        self.notebook.add(self.tab_silence, text=self.text("tab_silence"))
        self.notebook.add(self.tab_caption, text=self.text("tab_caption"))
        self.notebook.add(self.tab_youtube, text=self.text("tab_youtube"))

        self._build_tab_convert(self.tab_convert)
        self._build_tab_volume(self.tab_volume)
        self._build_tab_player(self.tab_player)
        self._build_tab_silence(self.tab_silence)
        self._build_tab_caption(self.tab_caption)
        self._build_tab_youtube(self.tab_youtube)

        # Tab Selection Monitor (Ensures canvas renders immediately when switching to Video tab)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_notebook_tab_changed, add="+")

        # Far-Right Dedicated Export Placed on Notebook Tab Bar
        self.btn_export_mode = ttk.Button(
            self.notebook,
            text="🚀 تصدير الفيديو" if is_ar else "🚀 Export Video",
            command=self._toggle_export_context,
            style="Action.TButton",
        )
        self.btn_export_mode.place(in_=self.notebook, relx=1.0, rely=0.0, x=-6, y=2, anchor="ne")
        self.btn_export_mode.lift()
        add_tooltip(self.btn_export_mode, "🚀 بدء معالجة وتصدير الفيديو النهائي بأعلى جودة", "🚀 Start final video export and processing", app=self)

        self.notebook.bind(
            "<Configure>",
            lambda _e: hasattr(self, "btn_export_mode") and self.btn_export_mode.lift(),
            add="+",
        )

        # Keyboard Shortcuts (Ctrl+S, Ctrl+Shift+S, Ctrl+O, F12, Escape, F11)
        self.bind("<Control-s>", lambda e: self._handle_save_project_event(e), add="+")
        self.bind("<Control-S>", lambda e: self._handle_save_project_event(e, save_as=True), add="+")
        self.bind("<Control-o>", lambda e: self._handle_open_project_event(e), add="+")
        self.bind("<Control-O>", lambda e: self._handle_open_project_event(e), add="+")
        self.bind("<F12>", lambda _e: self.capture_current_frame_snapshot(), add="+")
        self.bind("<Escape>", lambda _e: self._handle_app_escape(), add="+")
        self.bind("<F11>", lambda _e: self.toggle_app_fullscreen(), add="+")
        self.bind("<Map>", self._on_window_map, add="+")

        # ------------------ Row 3: Bottom Panel (Progress & Log) ------------------
        bottom_box = ttk.Frame(self, padding=(16, 0, 16, 10))
        bottom_box.grid(row=3, column=0, sticky="ew")
        bottom_box.columnconfigure(1, weight=1)

        prog_row = ttk.Frame(bottom_box)
        prog_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        prog_row.columnconfigure(1, weight=1)

        ttk.Label(prog_row, textvariable=self.progress_var, font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
        self.progress = ttk.Progressbar(prog_row, mode="indeterminate")
        self.progress.grid(row=0, column=1, padx=(12, 8), sticky="ew")

        is_ar = (self.language_var.get() == "العربية")
        self.btn_cancel_progress = ttk.Button(
            prog_row,
            text="🛑 إلغاء" if is_ar else "🛑 Cancel",
            command=self.cancel_current_operation,
            style="Player.TButton",
        )
        self.btn_cancel_progress.grid(row=0, column=2, sticky="e")
        self.btn_cancel_progress.grid_remove()

        log_frame = ttk.LabelFrame(bottom_box, padding=(8, 4, 8, 6))
        log_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 4))
        log_frame.columnconfigure(0, weight=1)
        self.i18n_widgets["log_group"] = log_frame
        self.log_frame = log_frame

        self.log = tk.Text(log_frame, wrap="word", height=3, state="disabled", font=("Consolas", 8))
        self.log.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)

        self.log_visible = False
        self.log_frame.grid_remove()

        footer = ttk.Frame(bottom_box)
        footer.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        footer.columnconfigure(0, weight=1)

        ttk.Label(footer, textvariable=self.status_var, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        self.btn_toggle_log = ttk.Button(
            footer,
            text=f"{self.text('view_log_btn')} ▼",
            style="Player.TButton",
            command=self.toggle_log_drawer,
        )
        self.btn_toggle_log.grid(row=0, column=1, padx=(8, 12), sticky="e")

        self.dev_label = ttk.Label(
            footer,
            font=("Segoe UI", 9),
            foreground="#555555",
            cursor="hand2",
        )
        self.dev_label.grid(row=0, column=2, padx=(10, 0), sticky="e")
        self.dev_label.bind("<Button-1>", lambda _e: self.show_about_dialog())
        self.i18n_widgets["dev_label"] = self.dev_label

        self.busy_widgets = [
            self.language_combo,
            self.format_combo,
            self.quality_combo,
            self.video_format_combo,
            self.video_compression_combo,
            self.video_resolution_combo,
            self.compress_video_button,
            self.keep_original_check,
            self.skip_existing_check,
            self.preview_check,
            self.open_output_check,
            self.enhancement_combo,
            self.run_button,
            self.detect_volume_button,
            self.auto_peak_button,
            self.boost_gain_scale,
            self.boost_anti_clip_check,
            self.boost_output_format_combo,
            self.boost_button,
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
            self.caption_model_combo,
            self.caption_lang_combo,
            self.caption_export_srt_check,
            self.caption_export_vtt_check,
            self.caption_export_txt_check,
            self.caption_burn_check,
            self.caption_start_button,
            self.silence_analyze_button,
            self.silence_export_button,
            self.silence_auto_db_button,
        ]
        self._sync_option_state()
        self._bind_studio_shortcuts()
        self.bind("<Control-d>", lambda _e: self.toggle_theme(), add="+")
        self.bind("<Control-D>", lambda _e: self.toggle_theme(), add="+")
        self._apply_theme()

        # Standard Maximized Window Mode (Taskbar always visible, no auto-fullscreen)
        self.after(150, self._init_app_window_mode)

    def _build_tab_convert(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)

        # Left Column: Audio Conversion + Consolidated Cover Art Studio
        audio_panel = ttk.LabelFrame(parent, padding=12)
        audio_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=2)
        audio_panel.columnconfigure(1, weight=1)
        self.i18n_widgets["conversion_group"] = audio_panel

        self.i18n_widgets["format_label"] = ttk.Label(audio_panel)
        self.i18n_widgets["format_label"].grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.format_combo = ttk.Combobox(
            audio_panel, textvariable=self.output_format_var, values=self.format_options, state="readonly", width=18
        )
        self.format_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=(0, 5))

        self.i18n_widgets["quality_label"] = ttk.Label(audio_panel)
        self.i18n_widgets["quality_label"].grid(row=1, column=0, sticky="w", pady=(0, 5))
        self.quality_combo = ttk.Combobox(
            audio_panel, textvariable=self.quality_var, values=convert.QUALITY_OPTIONS, state="readonly", width=18
        )
        self.quality_combo.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(0, 5))
        self.quality_combo.bind("<<ComboboxSelected>>", lambda _event: self._save_settings())

        self.i18n_widgets["enhance_label"] = ttk.Label(audio_panel)
        self.i18n_widgets["enhance_label"].grid(row=2, column=0, sticky="w", pady=(0, 8))
        self.enhancement_combo = ttk.Combobox(
            audio_panel,
            textvariable=self.enhancement_var,
            state="readonly",
            width=18,
        )
        self.enhancement_combo.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
        self.enhancement_combo.bind("<<ComboboxSelected>>", lambda _event: self._remember_enhancement_key())

        # Checkboxes in a compact 2x2 grid
        chk_grid = ttk.Frame(audio_panel)
        chk_grid.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        chk_grid.columnconfigure(0, weight=1)
        chk_grid.columnconfigure(1, weight=1)

        self.keep_original_check = ttk.Checkbutton(chk_grid, variable=self.keep_original_var, command=self._sync_option_state)
        self.keep_original_check.grid(row=0, column=0, sticky="w", pady=1)

        self.skip_existing_check = ttk.Checkbutton(chk_grid, variable=self.skip_existing_var)
        self.skip_existing_check.grid(row=0, column=1, sticky="w", pady=1)

        self.preview_check = ttk.Checkbutton(chk_grid, variable=self.preview_var)
        self.preview_check.grid(row=1, column=0, sticky="w", pady=1)

        self.open_output_check = ttk.Checkbutton(chk_grid, variable=self.open_output_var)
        self.open_output_check.grid(row=1, column=1, sticky="w", pady=1)

        # Consolidated Album Cover & Metadata Card
        search_panel = ttk.LabelFrame(audio_panel, padding=(10, 6, 10, 8))
        search_panel.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(4, 6))
        search_panel.columnconfigure(1, weight=1)
        self.i18n_widgets["cover_group"] = search_panel

        self.i18n_widgets["manual_search_label"] = ttk.Label(search_panel)
        self.i18n_widgets["manual_search_label"].grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.manual_search_entry = ttk.Entry(search_panel, textvariable=self.manual_search_var)
        self.manual_search_entry.grid(row=0, column=1, padx=(8, 0), sticky="ew", pady=(0, 6))
        self._attach_entry_context_menu(self.manual_search_entry)

        self.custom_cover_check = ttk.Checkbutton(
            search_panel, variable=self.custom_cover_var, command=self._sync_option_state
        )
        self.custom_cover_check.grid(row=1, column=0, columnspan=2, pady=(0, 6), sticky="w")

        custom_cover_row = ttk.Frame(search_panel)
        custom_cover_row.grid(row=2, column=0, columnspan=2, sticky="ew")
        custom_cover_row.columnconfigure(1, weight=1)

        self.choose_cover_button = ttk.Button(custom_cover_row, command=self.choose_custom_cover, style="Player.TButton")
        self.choose_cover_button.grid(row=0, column=0, sticky="w")
        add_tooltip(self.choose_cover_button, "اختيار صورة غلاف مخصصة من جهازك", "Choose a custom cover image", app=self)
        self.custom_cover_text_label = ttk.Label(custom_cover_row, textvariable=self.custom_cover_text_var, foreground="#555555")
        self.custom_cover_text_label.grid(row=0, column=1, padx=(8, 6), sticky="ew")
        self.cover_thumb_label = ttk.Label(custom_cover_row)
        self.cover_thumb_label.grid(row=0, column=2, sticky="e")

        audio_panel.rowconfigure(5, weight=1)
        self.run_button = ttk.Button(audio_panel, command=self.start_conversion, style="Action.TButton")
        self.run_button.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        add_tooltip(self.run_button, "بدء تحويل وضغط الملفات المحددة", "Start batch conversion", app=self)

        # Right Column: Video Conversion & Compression
        video_panel = ttk.LabelFrame(parent, padding=12)
        video_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=2)
        video_panel.columnconfigure(1, weight=1)
        self.i18n_widgets["video_only_group"] = video_panel

        self.i18n_widgets["video_format_label"] = ttk.Label(video_panel)
        self.i18n_widgets["video_format_label"].grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.video_format_combo = ttk.Combobox(
            video_panel,
            textvariable=self.video_format_var,
            state="readonly",
            width=18,
        )
        self.video_format_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=(0, 6))
        self.video_format_combo.bind("<<ComboboxSelected>>", self._video_format_changed)

        self.i18n_widgets["video_compression_label"] = ttk.Label(video_panel)
        self.i18n_widgets["video_compression_label"].grid(row=1, column=0, sticky="w", pady=(0, 6))
        self.video_compression_combo = ttk.Combobox(
            video_panel,
            textvariable=self.video_compression_var,
            state="readonly",
            width=18,
        )
        self.video_compression_combo.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(0, 6))
        self.video_compression_combo.bind("<<ComboboxSelected>>", self._video_compression_changed)

        self.i18n_widgets["video_resolution_label"] = ttk.Label(video_panel)
        self.i18n_widgets["video_resolution_label"].grid(row=2, column=0, sticky="w", pady=(0, 10))
        self.video_resolution_combo = ttk.Combobox(
            video_panel,
            textvariable=self.video_resolution_var,
            state="readonly",
            width=18,
        )
        self.video_resolution_combo.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(0, 10))
        self.video_resolution_combo.bind("<<ComboboxSelected>>", self._video_resolution_changed)

        ttk.Separator(video_panel, orient="horizontal").grid(row=3, column=0, columnspan=2, sticky="ew", pady=(2, 10))

        v_stats = ttk.Frame(video_panel)
        v_stats.grid(row=4, column=0, columnspan=2, sticky="ew", pady=4)
        ttk.Label(v_stats, textvariable=self.video_count_var, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.video_estimate_label = ttk.Label(v_stats, textvariable=self.video_estimate_var, foreground="#007700", font=("Segoe UI", 9))
        self.video_estimate_label.pack(
            anchor="w", pady=(4, 0)
        )

        video_panel.rowconfigure(5, weight=1)
        self.compress_video_button = ttk.Button(
            video_panel,
            command=self.start_video_conversion,
            style="Action.TButton",
        )
        self.compress_video_button.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(12, 0))


    def _build_tab_player(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        is_ar = self.language_var.get() == "العربية"

        # Vertical Resizable PanedWindow: Top (Viewer + DaVinci Inspector) | Bottom (5-Track NLE Timeline)
        self.nle_v_paned = tk.PanedWindow(
            parent,
            orient="vertical",
            sashwidth=5,
            sashrelief="flat",
            bg="#262c36",
            bd=0,
        )
        self.nle_v_paned.grid(row=0, column=0, sticky="nsew")

        top_workspace = ttk.Frame(self.nle_v_paned)
        top_workspace.columnconfigure(0, weight=8)
        top_workspace.columnconfigure(1, weight=3, minsize=350)
        top_workspace.rowconfigure(0, weight=1)

        # ---------------- Left Column: DaVinci Cinema Viewer Stage ----------------
        player_panel = ttk.LabelFrame(top_workspace, padding=(5, 4, 5, 4))
        player_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        player_panel.columnconfigure(0, weight=1)
        player_panel.rowconfigure(1, weight=1)
        self.i18n_widgets["media_player_group"] = player_panel

        # Top Viewer Quick-Ratio & Framing Bar
        viewer_topbar = ttk.Frame(player_panel)
        viewer_topbar.grid(row=0, column=0, sticky="ew", pady=(0, 3))
        viewer_topbar.columnconfigure(6, weight=1)

        self.btn_q_reels = ttk.Button(
            viewer_topbar,
            text="📱 9:16 ريلز" if is_ar else "📱 9:16 Reels",
            command=lambda: self._quick_set_aspect_ratio("9:16"),
            style="Player.TButton",
        )
        self.btn_q_reels.grid(row=0, column=0, padx=(0, 2))
        add_tooltip(self.btn_q_reels, "ضبط أبعاد الكادر لنسبة 9:16 بالطول (Reels / Shorts / TikTok)", "9:16 Vertical Aspect Ratio (Reels/TikTok)", app=self)

        self.btn_q_169 = ttk.Button(
            viewer_topbar,
            text="🖥️ 16:9",
            command=lambda: self._quick_set_aspect_ratio("16:9"),
            style="Player.TButton",
        )
        self.btn_q_169.grid(row=0, column=1, padx=2)
        add_tooltip(self.btn_q_169, "ضبط أبعاد الكادر لنسبة 16:9 بالعرض (YouTube / TV)", "16:9 Landscape Aspect Ratio (YouTube/TV)", app=self)

        self.btn_q_11 = ttk.Button(
            viewer_topbar,
            text="⬜ 1:1",
            command=lambda: self._quick_set_aspect_ratio("1:1"),
            style="Player.TButton",
        )
        self.btn_q_11.grid(row=0, column=2, padx=2)
        add_tooltip(self.btn_q_11, "ضبط أبعاد الكادر لنسبة 1:1 مربعة (Instagram Post)", "1:1 Square Aspect Ratio", app=self)

        self.btn_q_orig = ttk.Button(
            viewer_topbar,
            text="الأصلي" if is_ar else "Original",
            command=lambda: self._quick_set_aspect_ratio("original"),
            style="Player.TButton",
        )
        self.btn_q_orig.grid(row=0, column=3, padx=2)
        add_tooltip(self.btn_q_orig, "العودة للأبعاد الأصلية للفيديو بدون اقتصاص", "Reset to original video aspect ratio", app=self)

        self.btn_safe_grid = ttk.Button(
            viewer_topbar,
            text="⊞ شبكة" if is_ar else "⊞ Grid",
            command=self._toggle_safe_grid,
            style="Player.TButton",
        )
        self.btn_safe_grid.grid(row=0, column=4, padx=(6, 2))
        add_tooltip(self.btn_safe_grid, "إظهار أو إخفاء شبكة الكادر ومناطق الأمان (Safe Zones)", "Toggle Safe Framing Grid", app=self)

        self.btn_reset_cam = ttk.Button(
            viewer_topbar,
            text="↺ ضبط الكادر" if is_ar else "↺ Reset Framing",
            command=self._reset_video_transform,
            style="Player.TButton",
        )
        self.btn_reset_cam.grid(row=0, column=5, padx=2)
        add_tooltip(self.btn_reset_cam, "إعادة ضبط موضع وتكبير الكاميرا للوضع الطبيعي المركز", "Reset Camera Framing & Pan/Zoom", app=self)

        viewer_topbar.columnconfigure(6, weight=1)

        self.studio_toggle_btn = ttk.Button(
            viewer_topbar,
            text=("🎨 استوديو المونتاج" if is_ar else "🎨 Studio Preview"),
            command=self.toggle_studio_view,
            style="Player.TButton",
        )
        self.studio_toggle_btn.grid(row=0, column=8, sticky="e")
        add_tooltip(self.studio_toggle_btn, "التبديل بين استوديو المونتاج المرئي ومعاينة VLC المباشرة", "Toggle Studio Canvas Preview / VLC", app=self)

        # Video Surface (VLC) + Interactive DaVinci Studio Canvas
        self.video_surface = tk.Frame(player_panel, bg="black")
        self.video_surface.grid(row=1, column=0, sticky="nsew")
        self.video_surface.bind("<Double-Button-1>", lambda _e: None)
        self.video_surface.grid_remove()

        self.player_studio_canvas = tk.Canvas(player_panel, bg="#090c12", highlightthickness=0)
        self.player_studio_canvas.grid(row=1, column=0, sticky="nsew")
        self.player_studio_canvas.bind("<Configure>", lambda _e: self._render_player_studio_canvas())
        self.player_studio_canvas.bind("<ButtonPress-1>", self._on_player_canvas_press)
        self.player_studio_canvas.bind("<B1-Motion>", self._on_player_canvas_drag)
        self.player_studio_canvas.bind("<ButtonRelease-1>", self._on_player_canvas_release)
        self.player_studio_canvas.bind("<Motion>", self._on_player_canvas_hover)
        self.player_studio_canvas.bind("<MouseWheel>", self._on_player_canvas_mousewheel)
        self.player_studio_canvas.bind("<Double-Button-1>", self._on_player_canvas_double_click)
        self.player_studio_canvas.bind("<Button-3>", self._show_player_canvas_context_menu)

        # Compact Scrubber Row
        player_timeline_row = ttk.Frame(player_panel)
        player_timeline_row.grid(row=2, column=0, sticky="ew", pady=(4, 1))
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
        self.timeline_scale.grid(row=0, column=1, padx=(6, 0), sticky="ew")
        self.timeline_scale.bind("<ButtonPress-1>", self._timeline_press)
        self.timeline_scale.bind("<ButtonRelease-1>", self._timeline_release)
        ttk.Label(player_timeline_row, textvariable=self.timeline_text_var, font=("Consolas", 9, "bold")).grid(
            row=0, column=2, padx=(6, 0), sticky="e"
        )

        # Keep compact silence/trim mini-indicator bar for quick reference
        self.player_visual_timeline = tk.Canvas(
            player_panel, height=8, bg="#161b22", highlightthickness=0, cursor="hand2"
        )
        self.player_visual_timeline.grid(row=3, column=0, sticky="ew", pady=(0, 2))
        self.player_visual_timeline.bind("<Configure>", lambda _e: self._draw_player_visual_timeline())
        self.player_visual_timeline.bind("<Button-1>", self._on_player_visual_timeline_click)

        # Transport Controls Toolbar
        media_controls = ttk.Frame(player_panel)
        media_controls.grid(row=4, column=0, sticky="ew", pady=(1, 0))
        media_controls.columnconfigure(17, weight=1)

        self.play_button = ttk.Button(media_controls, text="▶", command=self.toggle_play_pause, style="PrimaryPlayer.TButton", width=4)
        self.play_button.grid(row=0, column=0, sticky="w")
        add_tooltip(self.play_button, "تشغيل / إيقاف المعاينة مؤقتاً (المسافة Space)", "Play / Pause (Space)", app=self)
        self.pause_button = ttk.Button(media_controls, command=self.pause_playback, style="Player.TButton", width=3)
        self.stop_button = ttk.Button(media_controls, command=self.stop_playback, style="Player.TButton", width=3)
        self.stop_button.grid(row=0, column=1, padx=(3, 0), sticky="w")
        add_tooltip(self.stop_button, "إيقاف التشغيل والعودة لنقطة البداية", "Stop Playback", app=self)
        ttk.Separator(media_controls, orient="vertical").grid(row=0, column=2, padx=5, sticky="ns")
        self.previous_button = ttk.Button(media_controls, command=self.seek_to_start, style="Player.TButton", width=3)
        self.previous_button.grid(row=0, column=3, sticky="w")
        add_tooltip(self.previous_button, "القفز إلى بداية الفيديو (Home)", "Seek to Start (Home)", app=self)
        self.back_button = ttk.Button(media_controls, command=lambda: self.seek_relative(-5), style="Player.TButton", width=4)
        self.back_button.grid(row=0, column=4, padx=(2, 0), sticky="w")
        add_tooltip(self.back_button, "تقديم 5 ثوانٍ للخلف (السهم الأيسر ←)", "Seek 5s Backward (Left Arrow)", app=self)
        self.forward_button = ttk.Button(media_controls, command=lambda: self.seek_relative(5), style="Player.TButton", width=4)
        self.forward_button.grid(row=0, column=5, padx=(2, 0), sticky="w")
        add_tooltip(self.forward_button, "تقديم 5 ثوانٍ للأمام (السهم الأيمن →)", "Seek 5s Forward (Right Arrow)", app=self)
        self.next_button = ttk.Button(media_controls, command=self.seek_to_end, style="Player.TButton", width=3)
        self.next_button.grid(row=0, column=6, padx=(2, 0), sticky="w")
        add_tooltip(self.next_button, "القفز إلى نهاية الفيديو (End)", "Seek to End (End)", app=self)
        ttk.Separator(media_controls, orient="vertical").grid(row=0, column=7, padx=5, sticky="ns")
        self.expand_video_button = ttk.Button(media_controls, text="⛶ تكبير" if is_ar else "⛶ Full", command=self.toggle_video_size, style="Player.TButton", width=7)
        self.expand_video_button.grid(row=0, column=8, sticky="w")
        add_tooltip(self.expand_video_button, "تكبير المعاينة لشاشة السينما الكاملة (F11)", "Cinema Fullscreen Preview (F11)", app=self)
        self.snapshot_button = ttk.Button(
            media_controls,
            text=self.text("snapshot_btn"),
            command=self.capture_current_frame_snapshot,
            style="Player.TButton",
        )
        self.snapshot_button.grid(row=0, column=10, padx=(3, 0), sticky="w")
        add_tooltip(self.snapshot_button, "التقاط صورة بجودة فائقة للإطار الحالي وحفظها (F12)", "Capture High-Res Frame Snapshot (F12)", app=self)
        ttk.Separator(media_controls, orient="vertical").grid(row=0, column=11, padx=5, sticky="ns")
        self.i18n_widgets["speed_label"] = ttk.Label(media_controls)
        self.i18n_widgets["speed_label"].grid(row=0, column=12, sticky="w")
        self.speed_combo = ttk.Combobox(
            media_controls,
            textvariable=self.speed_var,
            values=("0.50x", "0.75x", "1.00x", "1.25x", "1.50x", "1.75x", "2.00x"),
            state="readonly",
            width=6,
        )
        self.speed_combo.grid(row=0, column=13, padx=(3, 0), sticky="w")
        self.speed_combo.bind("<<ComboboxSelected>>", self._speed_changed)
        add_tooltip(self.speed_combo, "تغيير سرعة معاينة الفيديو", "Playback Speed", app=self)
        ttk.Separator(media_controls, orient="vertical").grid(row=0, column=14, padx=5, sticky="ns")
        self.i18n_widgets["volume_label"] = ttk.Label(media_controls)
        self.i18n_widgets["volume_label"].grid(row=0, column=15, sticky="e")
        self.volume_scale = ttk.Scale(
            media_controls,
            variable=self.volume_var,
            from_=0,
            to=100,
            orient="horizontal",
            command=self.apply_volume,
        )
        self.volume_scale.grid(row=0, column=17, padx=(4, 0), sticky="ew")
        add_tooltip(self.volume_scale, "التحكم في مستوى صوت المعاينة", "Playback Volume", app=self)

        # ---------------- Right Column: Dynamic Context-Sensitive Inspector + Modular Export ----------------
        inspector_panel = ttk.Frame(top_workspace)
        inspector_panel.grid(row=0, column=1, sticky="nsew")
        inspector_panel.columnconfigure(0, weight=1)
        inspector_panel.rowconfigure(2, weight=1)
        self.inspector_panel = inspector_panel

        # Row 0: Quick-Add Overlay Palette (adds at current playhead on V3/V2/V4)
        add_palette = ttk.Frame(inspector_panel)
        add_palette.grid(row=0, column=0, sticky="ew", pady=(0, 3))
        self.add_palette = add_palette
        for c_i in range(5):
            add_palette.columnconfigure(c_i, weight=1)

        self.btn_pal_txt = ttk.Button(
            add_palette,
            text="📝 نص" if is_ar else "📝 Text",
            command=self._open_text_settings,
            style="Player.TButton",
        )
        self.btn_pal_txt.grid(row=0, column=0, sticky="ew", padx=(0, 2))
        add_tooltip(self.btn_pal_txt, "إضافة نص متحرك أو عنوان جديد فوق الفيديو", "Add Text Overlay", app=self)

        self.btn_pal_ico = ttk.Button(
            add_palette,
            text="⭐ + أيقونة" if is_ar else "⭐ + Icon",
            command=lambda: self._nle_add_element("icon"),
            style="Player.TButton",
        )
        self.btn_pal_ico.grid(row=0, column=1, sticky="ew", padx=2)
        add_tooltip(self.btn_pal_ico, "إضافة أيقونة أو ملصق تعبيري فوق الفيديو", "Add Icon / Sticker Overlay", app=self)

        self.btn_pal_img = ttk.Button(
            add_palette,
            text="🖼️ + صورة" if is_ar else "🖼️ + Image",
            command=lambda: self._nle_add_element("image"),
            style="Player.TButton",
        )
        self.btn_pal_img.grid(row=0, column=2, sticky="ew", padx=2)
        add_tooltip(self.btn_pal_img, "إضافة صورة خارجية كطبقة فوق الفيديو", "Add Image Overlay", app=self)

        self.btn_pal_lgo = ttk.Button(
            add_palette,
            text="🛡️ + لوجو" if is_ar else "🛡️ + Logo",
            command=lambda: self._nle_add_element("logo"),
            style="Player.TButton",
        )
        self.btn_pal_lgo.grid(row=0, column=3, sticky="ew", padx=2)
        add_tooltip(self.btn_pal_lgo, "إضافة شعار (لوجو) أو علامة مائية على الفيديو", "Add Logo / Watermark", app=self)

        self.btn_pal_aud = ttk.Button(
            add_palette,
            text="🎵 + صوت" if is_ar else "🎵 + Audio",
            command=lambda: self.davinci_timeline.add_audio_file_dialog() if hasattr(self, "davinci_timeline") else None,
            style="Player.TButton",
        )
        self.btn_pal_aud.grid(row=0, column=4, sticky="ew", padx=(2, 0))
        add_tooltip(self.btn_pal_aud, "إضافة ملف صوتي أو مؤثر موسيقي جديد للتايم لاين", "Add Audio Track", app=self)

        # Row 1: Tool Context Switcher Bar (clicking any tool shows ONLY its settings in the single slot below)
        ctx_bar = ttk.Frame(inspector_panel)
        ctx_bar.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        self.ctx_bar = ctx_bar
        for c_i in range(6):
            ctx_bar.columnconfigure(c_i, weight=1)

        self.btn_ctx_video = ttk.Button(
            ctx_bar,
            text="🎬 فيديو" if is_ar else "🎬 Video",
            command=lambda: self._show_inspector_context("video"),
            style="PrimaryPlayer.TButton",
        )
        self.btn_ctx_video.grid(row=0, column=0, sticky="ew", padx=(0, 1))
        add_tooltip(self.btn_ctx_video, "إعدادات أبعاد الفيديو والكادر والتكبير", "Video Framing & Transform Settings", app=self)

        self.btn_ctx_color = ttk.Button(
            ctx_bar,
            text="🎨 ألوان" if is_ar else "🎨 Color",
            command=lambda: self._show_inspector_context("color"),
            style="Player.TButton",
        )
        self.btn_ctx_color.grid(row=0, column=1, sticky="ew", padx=1)
        add_tooltip(self.btn_ctx_color, "لوحة تصحيح الألوان وتدرج الفلاتر السينمائية", "Color Grading & Filters", app=self)

        self.btn_ctx_transition = ttk.Button(
            ctx_bar,
            text="✨ انتقال" if is_ar else "✨ Trans",
            command=lambda: self._show_inspector_context("transition"),
            style="Player.TButton",
        )
        self.btn_ctx_transition.grid(row=0, column=2, sticky="ew", padx=1)
        add_tooltip(self.btn_ctx_transition, "مؤثرات الانتقال الحركي بين اللقطات والقصات", "Transitions Effects", app=self)

        self.btn_ctx_silence = ttk.Button(
            ctx_bar,
            text="✂️ صمت" if is_ar else "✂️ Silence",
            command=lambda: self._show_inspector_context("silence"),
            style="Player.TButton",
        )
        self.btn_ctx_silence.grid(row=0, column=3, sticky="ew", padx=1)
        add_tooltip(self.btn_ctx_silence, "الكشف التلقائي عن السكتات الصامتة وحذفها بضغطة زر", "Smart Silence Detection & Removal", app=self)

        self.btn_ctx_audio = ttk.Button(
            ctx_bar,
            text="🔊 صوت" if is_ar else "🔊 Audio",
            command=lambda: self._show_inspector_context("audio"),
            style="Player.TButton",
        )
        self.btn_ctx_audio.grid(row=0, column=4, sticky="ew", padx=1)
        add_tooltip(self.btn_ctx_audio, "هندسة الصوت ومعادلة الترددات وخفض الضوضاء ومسارات الصوت", "Audio Mastering & Tracks Manager", app=self)

        self.btn_ctx_subs = ttk.Button(
            ctx_bar,
            text="🎙️ تفريغ" if is_ar else "🎙️ Subs/AI",
            command=lambda: self._show_inspector_context("subs"),
            style="Player.TButton",
        )
        self.btn_ctx_subs.grid(row=0, column=5, sticky="ew", padx=(1, 0))
        add_tooltip(self.btn_ctx_subs, "التفريغ الصوتي التلقائي بالذكاء الاصطناعي وإنشاء الترجمة والكتابة على الفيديو", "AI Transcription & Subtitles", app=self)

        # Row 2: Single Dynamic Context-Sensitive Inspector Host (Clean, static layout without scrolling)
        self.inspector_host_wrapper = ttk.Frame(inspector_panel)
        self.inspector_host_wrapper.grid(row=2, column=0, sticky="nsew", pady=(0, 2))
        self.inspector_host_wrapper.columnconfigure(0, weight=1)
        self.inspector_host_wrapper.rowconfigure(0, weight=1)

        self.inspector_canvas = tk.Canvas(self.inspector_host_wrapper, highlightthickness=0, bg="#161b22", bd=0)
        self.inspector_canvas.grid(row=0, column=0, sticky="nsew")

        # Scrollbar hidden as inspector elements fit cleanly without scrolling
        self.inspector_scroll = ttk.Scrollbar(self.inspector_host_wrapper, orient="vertical", command=self.inspector_canvas.yview)

        self.dynamic_inspector_host = ttk.Frame(self.inspector_canvas)
        self.dynamic_inspector_host_id = self.inspector_canvas.create_window((0, 0), window=self.dynamic_inspector_host, anchor="nw")
        self.dynamic_inspector_host.columnconfigure(0, weight=1)
        self.dynamic_inspector_host.rowconfigure(0, weight=1)

        def _on_insp_canvas_cfg(e):
            self.inspector_canvas.itemconfig(self.dynamic_inspector_host_id, width=e.width)

        def _on_insp_host_cfg(_e):
            self.inspector_canvas.configure(scrollregion=self.inspector_canvas.bbox("all"))
            self.inspector_canvas.yview_moveto(0.0)

        self.inspector_canvas.bind("<Configure>", _on_insp_canvas_cfg)
        self.dynamic_inspector_host.bind("<Configure>", _on_insp_host_cfg)

        # ---------------- Context 1: Video Framing, Numeric Transform & Selected Clip ----------------
        self.ctx_frame_video = ttk.Frame(self.dynamic_inspector_host)
        self.ctx_frame_video.grid(row=0, column=0, sticky="nsew")
        self.ctx_frame_video.columnconfigure(1, weight=1)

        self.i18n_widgets["trim_aspect_label"] = ttk.Label(self.ctx_frame_video, text=self.text("trim_aspect_ratio"))
        self.i18n_widgets["trim_aspect_label"].grid(row=0, column=0, sticky="w", pady=1)

        aspect_display_vals = [
            (k, info["label_ar"] if is_ar else info["label_en"])
            for k, info in ASPECT_RATIOS.items()
        ]
        self.trim_aspect_map = {disp: k for k, disp in aspect_display_vals}
        self.trim_aspect_rev = {k: disp for k, disp in aspect_display_vals}
        cur_ratio = self.video_branding_config.get("aspect_ratio", "original")
        self.trim_aspect_combo_var = tk.StringVar(value=self.trim_aspect_rev.get(cur_ratio, aspect_display_vals[0][1]))
        self.trim_aspect_combo = ttk.Combobox(
            self.ctx_frame_video,
            textvariable=self.trim_aspect_combo_var,
            values=[d[1] for d in aspect_display_vals],
            state="readonly",
        )
        self.trim_aspect_combo.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=1)
        self.trim_aspect_combo.bind("<<ComboboxSelected>>", self._on_trim_aspect_changed)

        self.lbl_fit_style = ttk.Label(self.ctx_frame_video, text="طريقة الملاءمة:" if is_ar else "Fit Mode:")
        self.lbl_fit_style.grid(row=1, column=0, sticky="w", pady=1)

        fit_vals = [(k, info["label_ar"] if is_ar else info["label_en"]) for k, info in FIT_MODES.items()]
        self.fit_mode_map = {disp: k for k, disp in fit_vals}
        self.fit_mode_rev = {k: disp for k, disp in fit_vals}
        cur_fit = self.video_branding_config.get("fit_mode", "crop")
        self.fit_mode_combo_var = tk.StringVar(value=self.fit_mode_rev.get(cur_fit, fit_vals[0][1]))
        self.fit_mode_combo = ttk.Combobox(
            self.ctx_frame_video,
            textvariable=self.fit_mode_combo_var,
            values=[d[1] for d in fit_vals],
            state="readonly",
        )
        self.fit_mode_combo.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=1)
        self.fit_mode_combo.bind("<<ComboboxSelected>>", self._on_fit_mode_combo_changed)

        # Video Transform & Properties
        self.xf_group = ttk.LabelFrame(
            self.ctx_frame_video,
            text="📐 خصائص وتحويل الفيديو" if is_ar else "📐 Video Transform",
            padding=(6, 3, 6, 4),
        )
        self.xf_group.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(3, 3))
        self.xf_group.columnconfigure(1, weight=1)

        self.clip_override_var = tk.BooleanVar(value=False)
        self.chk_clip_override = ttk.Checkbutton(
            self.xf_group,
            text="🎞️ تخصيص لهذا المقطع فقط" if is_ar else "🎞️ Apply to Selected Clip Only",
            variable=self.clip_override_var,
            command=self._on_clip_override_toggled,
        )
        self.chk_clip_override.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 2))

        # Zoom Row (Slider + Numeric % Spinbox + 1x Reset)
        self.lbl_zoom_title = ttk.Label(self.xf_group, text="التكبير (Zoom):" if is_ar else "Scale (Zoom):")
        self.lbl_zoom_title.grid(row=1, column=0, sticky="w")
        self.vid_zoom_var = tk.DoubleVar(value=float(self.video_branding_config.get("video_zoom", 1.0)))
        self.vid_zoom_scale = ttk.Scale(
            self.xf_group,
            from_=0.25,
            to=4.00,
            variable=self.vid_zoom_var,
            orient="horizontal",
            command=self._on_vid_transform_slider,
        )
        self.vid_zoom_scale.grid(row=1, column=1, sticky="ew", padx=4)
        self.vid_zoom_spin_var = tk.StringVar(value="100")
        self.vid_zoom_spin = tk.Spinbox(
            self.xf_group,
            from_=25,
            to=400,
            increment=5,
            textvariable=self.vid_zoom_spin_var,
            width=5,
            font=("Consolas", 9, "bold"),
            command=self._on_vid_transform_spin,
        )
        self.vid_zoom_spin.grid(row=1, column=2, padx=2)
        self.vid_zoom_spin.bind("<Return>", self._on_vid_transform_spin)
        self.vid_zoom_spin.bind("<FocusOut>", self._on_vid_transform_spin)
        ttk.Button(self.xf_group, text="1x", width=3, style="Player.TButton", command=lambda: self._nudge_transform(zoom=1.0)).grid(row=1, column=3)

        # Position X Row (Right / Left: Slider + Numeric % Spinbox + 0 Reset)
        self.lbl_panx_title = ttk.Label(self.xf_group, text="الموضع الأفقي (X):" if is_ar else "Position X:")
        self.lbl_panx_title.grid(row=2, column=0, sticky="w", pady=1)
        self.vid_panx_var = tk.DoubleVar(value=float(self.video_branding_config.get("video_pan_x", 0.0)))
        self.vid_panx_scale = ttk.Scale(
            self.xf_group,
            from_=-1.00,
            to=1.00,
            variable=self.vid_panx_var,
            orient="horizontal",
            command=self._on_vid_transform_slider,
        )
        self.vid_panx_scale.grid(row=2, column=1, sticky="ew", padx=4, pady=1)
        self.vid_panx_spin_var = tk.StringVar(value="0")
        self.vid_panx_spin = tk.Spinbox(
            self.xf_group,
            from_=-100,
            to=100,
            increment=1,
            textvariable=self.vid_panx_spin_var,
            width=5,
            font=("Consolas", 9, "bold"),
            command=self._on_vid_transform_spin,
        )
        self.vid_panx_spin.grid(row=2, column=2, padx=2)
        self.vid_panx_spin.bind("<Return>", self._on_vid_transform_spin)
        self.vid_panx_spin.bind("<FocusOut>", self._on_vid_transform_spin)
        ttk.Button(self.xf_group, text="0", width=3, style="Player.TButton", command=lambda: self._nudge_transform(pan_x=0.0)).grid(row=2, column=3)

        # Position Y Row (Up / Down: Slider + Numeric % Spinbox + 0 Reset)
        self.lbl_pany_title = ttk.Label(self.xf_group, text="الموضع الرأسي (Y):" if is_ar else "Position Y:")
        self.lbl_pany_title.grid(row=3, column=0, sticky="w", pady=1)
        self.vid_pany_var = tk.DoubleVar(value=float(self.video_branding_config.get("video_pan_y", 0.0)))
        self.vid_pany_scale = ttk.Scale(
            self.xf_group,
            from_=-1.00,
            to=1.00,
            variable=self.vid_pany_var,
            orient="horizontal",
            command=self._on_vid_transform_slider,
        )
        self.vid_pany_scale.grid(row=3, column=1, sticky="ew", padx=4, pady=1)
        self.vid_pany_spin_var = tk.StringVar(value="0")
        self.vid_pany_spin = tk.Spinbox(
            self.xf_group,
            from_=-100,
            to=100,
            increment=1,
            textvariable=self.vid_pany_spin_var,
            width=5,
            font=("Consolas", 9, "bold"),
            command=self._on_vid_transform_spin,
        )
        self.vid_pany_spin.grid(row=3, column=2, padx=2)
        self.vid_pany_spin.bind("<Return>", self._on_vid_transform_spin)
        self.vid_pany_spin.bind("<FocusOut>", self._on_vid_transform_spin)
        ttk.Button(self.xf_group, text="0", width=3, style="Player.TButton", command=lambda: self._nudge_transform(pan_y=0.0)).grid(row=3, column=3)

        # Flip & Clamp Row
        xf_opts = ttk.Frame(self.xf_group)
        xf_opts.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(2, 0))
        self.vid_flip_var = tk.BooleanVar(value=bool(self.video_branding_config.get("video_flip_h", False)))
        self.chk_vid_flip = ttk.Checkbutton(
            xf_opts,
            text="⇄ عكس أفقي" if is_ar else "⇄ Flip H",
            variable=self.vid_flip_var,
            command=self._on_vid_transform_toggle,
        )
        self.chk_vid_flip.pack(side="left", padx=(0, 8))

        self.vid_clamp_var = tk.BooleanVar(value=bool(self.video_branding_config.get("video_clamp_edges", True)))
        self.chk_vid_clamp = ttk.Checkbutton(
            xf_opts,
            text="🧲 منع الحواف السوداء" if is_ar else "🧲 Clamp Edges",
            variable=self.vid_clamp_var,
            command=self._on_vid_transform_toggle,
        )
        self.chk_vid_clamp.pack(side="left")

        # Selected V1 Clip Timing, Gap Position, Speed & Volume (Numeric Spinboxes!)
        self.clip_fx_group = ttk.LabelFrame(
            self.ctx_frame_video,
            text="🎞️ المقطع المحدد: المكان، القص، السرعة، والصوت" if is_ar else "🎞️ Selected Clip: Position, In/Out, Speed & Vol",
            padding=(6, 3, 6, 4),
        )
        self.clip_fx_group.grid(row=3, column=0, columnspan=2, sticky="ew")
        for ci in (1, 3, 5):
            self.clip_fx_group.columnconfigure(ci, weight=1)

        self.lbl_clip_tl_pos = ttk.Label(self.clip_fx_group, text="موقعs:" if is_ar else "Pos s:")
        self.lbl_clip_tl_pos.grid(row=0, column=0, sticky="w")
        self.clip_tl_pos_var = tk.StringVar(value="0.00")
        self.clip_tl_pos_spin = tk.Spinbox(
            self.clip_fx_group, from_=0.0, to=99999.0, increment=0.25, format="%.2f",
            textvariable=self.clip_tl_pos_var, width=6, font=("Consolas", 8),
            command=self._on_clip_numeric_changed,
        )
        self.clip_tl_pos_spin.grid(row=0, column=1, sticky="ew", padx=(2, 4))
        self.clip_tl_pos_spin.bind("<Return>", self._on_clip_numeric_changed)
        self.clip_tl_pos_spin.bind("<FocusOut>", self._on_clip_numeric_changed)

        self.lbl_clip_in = ttk.Label(self.clip_fx_group, text="منs:" if is_ar else "In s:")
        self.lbl_clip_in.grid(row=0, column=2, sticky="w")
        self.clip_in_var = tk.StringVar(value="0.00")
        self.clip_in_spin = tk.Spinbox(
            self.clip_fx_group, from_=0.0, to=99999.0, increment=0.10, format="%.2f",
            textvariable=self.clip_in_var, width=6, font=("Consolas", 8),
            command=self._on_clip_numeric_changed,
        )
        self.clip_in_spin.grid(row=0, column=3, sticky="ew", padx=(2, 4))
        self.clip_in_spin.bind("<Return>", self._on_clip_numeric_changed)
        self.clip_in_spin.bind("<FocusOut>", self._on_clip_numeric_changed)

        self.lbl_clip_out = ttk.Label(self.clip_fx_group, text="إلىs:" if is_ar else "Out s:")
        self.lbl_clip_out.grid(row=0, column=4, sticky="w")
        self.clip_out_var = tk.StringVar(value="60.00")
        self.clip_out_spin = tk.Spinbox(
            self.clip_fx_group, from_=0.1, to=99999.0, increment=0.10, format="%.2f",
            textvariable=self.clip_out_var, width=6, font=("Consolas", 8),
            command=self._on_clip_numeric_changed,
        )
        self.clip_out_spin.grid(row=0, column=5, sticky="ew", padx=(2, 0))
        self.clip_out_spin.bind("<Return>", self._on_clip_numeric_changed)
        self.clip_out_spin.bind("<FocusOut>", self._on_clip_numeric_changed)

        clip_row2 = ttk.Frame(self.clip_fx_group)
        clip_row2.grid(row=1, column=0, columnspan=6, sticky="ew", pady=(3, 0))
        clip_row2.columnconfigure(3, weight=1)

        self.lbl_clip_speed = ttk.Label(clip_row2, text="سرعةx:" if is_ar else "Spd x:")
        self.lbl_clip_speed.grid(row=0, column=0, sticky="w")
        self.clip_speed_combo_var = tk.StringVar(value="1.00")
        self.clip_speed_combo = tk.Spinbox(
            clip_row2,
            from_=0.25,
            to=4.00,
            increment=0.10,
            format="%.2f",
            textvariable=self.clip_speed_combo_var,
            width=5,
            font=("Consolas", 8, "bold"),
            command=self._on_clip_speed_changed,
        )
        self.clip_speed_combo.grid(row=0, column=1, padx=(2, 6))
        self.clip_speed_combo.bind("<Return>", self._on_clip_speed_changed)
        self.clip_speed_combo.bind("<FocusOut>", self._on_clip_speed_changed)

        self.lbl_clip_vol = ttk.Label(clip_row2, text="صوت%:" if is_ar else "Vol%:")
        self.lbl_clip_vol.grid(row=0, column=2, sticky="w")
        self.clip_vol_var = tk.DoubleVar(value=100.0)
        self.clip_vol_scale = ttk.Scale(
            clip_row2,
            from_=0.0,
            to=200.0,
            variable=self.clip_vol_var,
            orient="horizontal",
            command=self._on_clip_vol_changed,
        )
        self.clip_vol_scale.grid(row=0, column=3, sticky="ew", padx=(3, 3))
        self.clip_vol_spin_var = tk.StringVar(value="100")
        self.clip_vol_spin = tk.Spinbox(
            clip_row2,
            from_=0,
            to=200,
            increment=5,
            textvariable=self.clip_vol_spin_var,
            width=4,
            font=("Consolas", 8, "bold"),
            command=self._on_clip_vol_spin_changed,
        )
        self.clip_vol_spin.grid(row=0, column=4, padx=(0, 3))
        self.clip_vol_spin.bind("<Return>", self._on_clip_vol_spin_changed)
        self.clip_vol_spin.bind("<FocusOut>", self._on_clip_vol_spin_changed)

        self.clip_mute_var = tk.BooleanVar(value=False)
        self.chk_clip_mute = ttk.Checkbutton(
            clip_row2,
            text="🔇",
            variable=self.clip_mute_var,
            command=self._on_clip_mute_toggled,
        )
        self.chk_clip_mute.grid(row=0, column=5)

        # Selected Clip Audio Fade In, Fade Out & Noise Reduction (clip_row3)
        clip_row3 = ttk.Frame(self.clip_fx_group)
        clip_row3.grid(row=2, column=0, columnspan=6, sticky="ew", pady=(3, 0))
        clip_row3.columnconfigure(1, weight=1)
        clip_row3.columnconfigure(3, weight=1)

        self.lbl_clip_fade_in = ttk.Label(clip_row3, text="تلاشي دخولs:" if is_ar else "Fade In s:")
        self.lbl_clip_fade_in.grid(row=0, column=0, sticky="w")
        self.clip_fade_in_var = tk.StringVar(value="0.00")
        self.clip_fade_in_spin = tk.Spinbox(
            clip_row3, from_=0.0, to=15.0, increment=0.25, format="%.2f",
            textvariable=self.clip_fade_in_var, width=5, font=("Consolas", 8),
            command=self._on_clip_audio_fade_changed,
        )
        self.clip_fade_in_spin.grid(row=0, column=1, sticky="ew", padx=(2, 4))
        self.clip_fade_in_spin.bind("<Return>", self._on_clip_audio_fade_changed)
        self.clip_fade_in_spin.bind("<FocusOut>", self._on_clip_audio_fade_changed)

        self.lbl_clip_fade_out = ttk.Label(clip_row3, text="خروجs:" if is_ar else "Fade Out s:")
        self.lbl_clip_fade_out.grid(row=0, column=2, sticky="w")
        self.clip_fade_out_var = tk.StringVar(value="0.00")
        self.clip_fade_out_spin = tk.Spinbox(
            clip_row3, from_=0.0, to=15.0, increment=0.25, format="%.2f",
            textvariable=self.clip_fade_out_var, width=5, font=("Consolas", 8),
            command=self._on_clip_audio_fade_changed,
        )
        self.clip_fade_out_spin.grid(row=0, column=3, sticky="ew", padx=(2, 4))
        self.clip_fade_out_spin.bind("<Return>", self._on_clip_audio_fade_changed)
        self.clip_fade_out_spin.bind("<FocusOut>", self._on_clip_audio_fade_changed)

        self.clip_denoise_var = tk.BooleanVar(value=False)
        self.chk_clip_denoise = ttk.Checkbutton(
            clip_row3,
            text="🧹 تنقية" if is_ar else "🧹 Denoise",
            variable=self.clip_denoise_var,
            command=self._on_clip_denoise_toggled,
        )
        self.chk_clip_denoise.grid(row=0, column=4, padx=(2, 0))

        # ---------------- Context 2: Selected Overlay Properties (V4 Logo / V3 Text+ / V2 Icon & Image) ----------------
        self.item_prop_card = ttk.LabelFrame(self.dynamic_inspector_host, padding=(7, 5, 7, 5))
        self.item_prop_card.grid(row=0, column=0, sticky="nsew")
        self.item_prop_card.columnconfigure(1, weight=1)

        # ---------------- Context 3: Live Color Grading (Sliders + Numeric Spinboxes + Presets) ----------------
        self.ctx_frame_color = ttk.LabelFrame(
            self.dynamic_inspector_host,
            text="🎨 تصحيح وتدرج الألوان المباشر" if is_ar else "🎨 Live Color Grading",
            padding=(7, 4, 7, 4),
        )
        self.ctx_frame_color.grid(row=0, column=0, sticky="nsew")
        self.ctx_frame_color.columnconfigure(1, weight=1)

        # Top Action Bar: Enable Checkbox + Reset + Direct Color Studio Button (Always Visible at Top!)
        top_c_bar = ttk.Frame(self.ctx_frame_color)
        top_c_bar.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 3))
        top_c_bar.columnconfigure(0, weight=1)

        self.trim_color_check = ttk.Checkbutton(
            top_c_bar,
            text=self.text("trim_color_grading"),
            variable=self.trim_color_var,
            command=self._on_trim_branding_toggle,
        )
        self.trim_color_check.grid(row=0, column=0, sticky="w")

        self.btn_col_reset = ttk.Button(
            top_c_bar,
            text="↺ تصفير" if is_ar else "↺ Reset",
            command=self._reset_studio_color_grading,
            style="Player.TButton",
            width=7,
        )
        self.btn_col_reset.grid(row=0, column=1, padx=(2, 3), sticky="e")

        self.btn_color_grading = ttk.Button(
            top_c_bar,
            text="🎨 استديو الألوان المتقدم" if is_ar else "🎨 Color Studio",
            command=self.open_video_color_dialog,
            style="PrimaryPlayer.TButton",
        )
        self.btn_color_grading.grid(row=0, column=2, sticky="e")

        auto_frame = ttk.Frame(self.ctx_frame_color)
        auto_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 3))
        auto_frame.columnconfigure(1, weight=1)

        mode_items = [(k, info["label_ar"] if is_ar else info["label_en"]) for k, info in AUTO_COLOR_MODES.items()]
        self._studio_color_mode_map = {d: k for k, d in mode_items}
        self._studio_color_mode_rev = {k: d for k, d in mode_items}
        self._studio_color_mode_var = tk.StringVar(value=mode_items[0][1])

        self.btn_studio_auto_color = ttk.Button(
            auto_frame,
            text="🤖 تصحيح ذكي" if is_ar else "🤖 Auto Color",
            command=self._on_studio_auto_color_clicked,
            style="Action.TButton",
        )
        self.btn_studio_auto_color.grid(row=0, column=0, sticky="w", padx=(0, 4))

        self.studio_color_mode_combo = ttk.Combobox(
            auto_frame,
            textvariable=self._studio_color_mode_var,
            values=[d for _, d in mode_items],
            state="readonly",
            width=16,
        )
        self.studio_color_mode_combo.grid(row=0, column=1, sticky="ew")

        self.lbl_studio_color_diag = ttk.Label(
            self.ctx_frame_color,
            text="",
            font=("Segoe UI", 8, "italic"),
            foreground="#58a6ff",
            wraplength=340,
        )
        self.lbl_studio_color_diag.grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 2))

        c_preset_items = []
        _seen_p = set()
        for k, info in COLOR_PRESETS.items():
            _lbl = info["label_ar"] if is_ar else info["label_en"]
            if _lbl not in _seen_p:
                _seen_p.add(_lbl)
                c_preset_items.append((k, _lbl))
        self._studio_color_preset_map = {d: k for k, d in c_preset_items}
        self._studio_color_preset_var = tk.StringVar(value=c_preset_items[0][1])

        preset_frame = ttk.Frame(self.ctx_frame_color)
        preset_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 2))
        preset_frame.columnconfigure(1, weight=1)

        self.lbl_color_preset = ttk.Label(preset_frame, text="فلتر جاهز:" if is_ar else "Preset:")
        self.lbl_color_preset.grid(row=0, column=0, sticky="w")
        self.studio_color_preset_combo = ttk.Combobox(
            preset_frame,
            textvariable=self._studio_color_preset_var,
            values=[d for _, d in c_preset_items],
            state="readonly",
        )
        self.studio_color_preset_combo.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        self.studio_color_preset_combo.bind("<<ComboboxSelected>>", self._on_studio_color_preset_selected)

        raw_cc = self.video_branding_config.get("color_config", {})
        self.col_bright_var = tk.DoubleVar(value=round(float(raw_cc.get("brightness", 0.0)) * 100.0, 1))
        self.col_contrast_var = tk.DoubleVar(value=round(float(raw_cc.get("contrast", 1.0)) * 100.0, 1))
        self.col_sat_var = tk.DoubleVar(value=round(float(raw_cc.get("saturation", 1.0)) * 100.0, 1))
        self.col_temp_var = tk.DoubleVar(value=round(float(raw_cc.get("temperature", 0.0)) * 100.0, 1))
        self.col_bright_spin_var = tk.StringVar(value=f"{int(round(self.col_bright_var.get()))}")
        self.col_contrast_spin_var = tk.StringVar(value=f"{int(round(self.col_contrast_var.get()))}")
        self.col_sat_spin_var = tk.StringVar(value=f"{int(round(self.col_sat_var.get()))}")
        self.col_temp_spin_var = tk.StringVar(value=f"{int(round(self.col_temp_var.get()))}")

        for r_idx, (attr_lbl, ar_t, en_t, dvar, svar, f_min, f_max) in enumerate((
            ("lbl_col_br", "إضاءة %:", "Bright %:", self.col_bright_var, self.col_bright_spin_var, -50, 50),
            ("lbl_col_ct", "تباين %:", "Contrast %:", self.col_contrast_var, self.col_contrast_spin_var, 50, 200),
            ("lbl_col_st", "تشبع %:", "Saturate %:", self.col_sat_var, self.col_sat_spin_var, 0, 250),
            ("lbl_col_tp", "دفء/برودة:", "Warmth %:", self.col_temp_var, self.col_temp_spin_var, -50, 50),
        ), start=4):
            lbl = ttk.Label(self.ctx_frame_color, text=ar_t if is_ar else en_t)
            lbl.grid(row=r_idx, column=0, sticky="w", pady=1)
            setattr(self, attr_lbl, lbl)
            ttk.Scale(
                self.ctx_frame_color, from_=float(f_min), to=float(f_max), variable=dvar,
                orient="horizontal", command=self._on_studio_color_slider,
            ).grid(row=r_idx, column=1, sticky="ew", padx=4, pady=1)
            sp = tk.Spinbox(
                self.ctx_frame_color, from_=f_min, to=f_max, increment=2,
                textvariable=svar, width=5, font=("Consolas", 8, "bold"),
                command=self._on_studio_color_spin,
            )
            sp.grid(row=r_idx, column=2, pady=1)
            sp.bind("<Return>", self._on_studio_color_spin)
            sp.bind("<FocusOut>", self._on_studio_color_spin)

        # ---------------- Context 3.5: Live Video Transitions Studio ----------------
        self.ctx_frame_transition = ttk.LabelFrame(
            self.dynamic_inspector_host,
            text="✨ حركات وانتقالات الفيديو السينمائية" if is_ar else "✨ Video Transitions Studio",
            padding=(7, 4, 7, 4),
        )
        self.ctx_frame_transition.grid(row=0, column=0, sticky="nsew")
        self.ctx_frame_transition.columnconfigure(1, weight=1)

        # Top Action Bar: Enable Checkbox + Open Full Transitions Library Button
        top_t_bar = ttk.Frame(self.ctx_frame_transition)
        top_t_bar.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 4))
        top_t_bar.columnconfigure(0, weight=1)

        self.trim_trans_check = ttk.Checkbutton(
            top_t_bar,
            text="تفعيل الانتقالات بين المقاطع" if is_ar else "Enable Video Transitions",
            variable=self.trans_enable_var,
            command=self._on_studio_trans_toggle,
        )
        self.trim_trans_check.grid(row=0, column=0, sticky="w")

        self.btn_trans_library = ttk.Button(
            top_t_bar,
            text="✨ مكتبة الانتقالات (46+ حركة)" if is_ar else "✨ Transitions Library",
            command=self.open_video_transitions_dialog,
            style="PrimaryPlayer.TButton",
        )
        self.btn_trans_library.grid(row=0, column=1, sticky="e")

        # Timeline cuts status label
        self.lbl_trans_status = ttk.Label(
            self.ctx_frame_transition,
            text="",
            font=("Segoe UI", 8, "italic"),
            foreground="#58a6ff",
            wraplength=340,
        )
        self.lbl_trans_status.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 4))

        # Selected Transition Combobox
        t_row = ttk.Frame(self.ctx_frame_transition)
        t_row.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 4))
        t_row.columnconfigure(1, weight=1)

        ttk.Label(t_row, text="الحركة:" if is_ar else "Transition:").grid(row=0, column=0, sticky="w")
        t_items = []
        for p in list_transitions_by_category("all"):
            _name = p["label_ar"] if is_ar else p["label_en"]
            _ic = p.get("icon", "✨")
            t_items.append((p["key"], f"{_ic} {_name}"))
        self._studio_trans_map = {d: k for k, d in t_items}
        self.trans_preset_var = tk.StringVar(value=t_items[0][1] if t_items else "")
        self.studio_trans_combo = ttk.Combobox(
            t_row,
            textvariable=self.trans_preset_var,
            values=[d for _, d in t_items],
            state="readonly",
        )
        self.studio_trans_combo.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        self.studio_trans_combo.bind("<<ComboboxSelected>>", self._on_studio_trans_selected)

        # Quick Popular Preset Pills (1-click transition change)
        pills_box = ttk.Frame(self.ctx_frame_transition)
        pills_box.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        for col_p in range(3):
            pills_box.columnconfigure(col_p, weight=1)

        top_popular_pills = [
            ("fade", "💫 تلاشي متقاطع" if is_ar else "💫 Crossfade"),
            ("smoothleft", "⬅️ انزلاق لليسار" if is_ar else "⬅️ Slide Left"),
            ("zoomin", "🔍 تكبير وزوم" if is_ar else "🔍 Zoom In"),
            ("fadeblack", "🎬 تلاشي لأسود" if is_ar else "🎬 Dip to Black"),
            ("pixelize", "👾 بيكسيل غليتش" if is_ar else "👾 Pixelize"),
            ("horzopen", "↔️ ستارة أفقية" if is_ar else "↔️ Curtain Open"),
        ]
        for p_idx, (pk, plbl) in enumerate(top_popular_pills):
            r_i = p_idx // 3
            c_i = p_idx % 3
            ttk.Button(
                pills_box,
                text=plbl,
                command=lambda key=pk: self._apply_studio_quick_trans(key),
                style="Player.TButton",
            ).grid(row=r_i, column=c_i, sticky="ew", padx=1, pady=1)

        # Duration Slider & Controls
        dur_box = ttk.Frame(self.ctx_frame_transition)
        dur_box.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 2))
        dur_box.columnconfigure(1, weight=1)

        ttk.Label(dur_box, text="المدة:" if is_ar else "Duration:").grid(row=0, column=0, sticky="w")
        ttk.Scale(
            dur_box,
            from_=0.10,
            to=2.00,
            variable=self.trans_dur_var,
            orient="horizontal",
            command=self._on_studio_trans_slider,
        ).grid(row=0, column=1, sticky="ew", padx=4)

        self.lbl_trans_dur_val = ttk.Label(
            dur_box,
            text=f"{self.trans_dur_var.get():.2f} " + ("ثانية" if is_ar else "s"),
            font=("Segoe UI", 8, "bold"),
            foreground="#2ea043",
            width=8,
        )
        self.lbl_trans_dur_val.grid(row=0, column=2, sticky="e")

        # Quick duration presets & Audio crossfade checkbox
        opt_t_box = ttk.Frame(self.ctx_frame_transition)
        opt_t_box.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(2, 0))

        ttk.Button(
            opt_t_box,
            text="⚡ 0.3s",
            command=lambda: self._set_studio_trans_quick_duration(0.30),
            style="Player.TButton",
            width=5,
        ).pack(side="left", padx=(0, 2))

        ttk.Button(
            opt_t_box,
            text="🎬 0.5s",
            command=lambda: self._set_studio_trans_quick_duration(0.50),
            style="Player.TButton",
            width=5,
        ).pack(side="left", padx=2)

        ttk.Button(
            opt_t_box,
            text="🌊 1.0s",
            command=lambda: self._set_studio_trans_quick_duration(1.00),
            style="Player.TButton",
            width=5,
        ).pack(side="left", padx=2)

        ttk.Checkbutton(
            opt_t_box,
            text="🔊 تلاشي صوتي" if is_ar else "🔊 Audio Crossfade",
            variable=self.trans_audio_var,
            command=self._on_studio_trans_toggle,
        ).pack(side="right")

        # Row 6: Hand Drag-and-Drop Badge + Click-to-Place Wand Tool!
        drag_bar = ttk.Frame(self.ctx_frame_transition)
        drag_bar.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(8, 2))
        drag_bar.columnconfigure(0, weight=1)

        self.btn_drag_trans = tk.Label(
            drag_bar,
            text="🖐️ اسحب الانتقال بيدك وأفلته على أي قطع في التايم لاين" if is_ar else "🖐️ Drag transition & drop on any timeline cut",
            bg="#1c2433",
            fg="#58a6ff",
            font=("Segoe UI", 8, "bold"),
            relief="solid",
            bd=1,
            cursor="hand2",
            padx=8,
            pady=5,
        )
        self.btn_drag_trans.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.btn_drag_trans.bind("<ButtonPress-1>", self._on_start_trans_drag)

        self.btn_place_trans_wand = ttk.Button(
            drag_bar,
            text="🪄 نقرة للوضع" if is_ar else "🪄 Click Place",
            command=self._toggle_transition_placement_tool,
            style="Player.TButton",
            width=11,
        )
        self.btn_place_trans_wand.grid(row=0, column=1, sticky="e")

        # ---------------- Context 4: Live Silence Splitting & Jump-Cut Studio ----------------
        self.ctx_frame_silence = ttk.LabelFrame(
            self.dynamic_inspector_host,
            text="✂️ معالجة وحذف السكتات" if is_ar else "✂️ Silence Processing",
            padding=(7, 5, 7, 5),
        )
        self.ctx_frame_silence.grid(row=0, column=0, sticky="nsew")
        self.ctx_frame_silence.columnconfigure(1, weight=1)

        self.trim_remove_silence_check = ttk.Checkbutton(
            self.ctx_frame_silence,
            text=self.text("trim_remove_silence"),
            variable=self.trim_remove_silence_var,
            command=self._on_trim_branding_toggle,
        )
        self.trim_remove_silence_check.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))

        self.lbl_sil_db = ttk.Label(self.ctx_frame_silence, text="حد الصمت (dB):" if is_ar else "Threshold (dB):")
        self.lbl_sil_db.grid(row=1, column=0, sticky="w", pady=2)
        ttk.Scale(
            self.ctx_frame_silence, from_=-55.0, to=-18.0, variable=self.silence_noise_db_var,
            orient="horizontal", command=self._on_silence_noise_changed,
        ).grid(row=1, column=1, sticky="ew", padx=4)
        self.sil_db_spin = tk.Spinbox(
            self.ctx_frame_silence, from_=-55.0, to=-18.0, increment=1.0, format="%.1f",
            textvariable=self.silence_noise_db_var, width=6, font=("Consolas", 8, "bold"),
            command=self._on_silence_noise_changed,
        )
        self.sil_db_spin.grid(row=1, column=2, pady=2)

        sil_p_row = ttk.Frame(self.ctx_frame_silence)
        sil_p_row.grid(row=2, column=0, columnspan=3, sticky="ew", pady=3)
        sil_p_row.columnconfigure(1, weight=1)
        sil_p_row.columnconfigure(3, weight=1)

        self.lbl_sil_min = ttk.Label(sil_p_row, text="أقل سكتة(ث):" if is_ar else "Min Sil(s):")
        self.lbl_sil_min.grid(row=0, column=0, sticky="w")
        ttk.Spinbox(
            sil_p_row, from_=0.10, to=5.00, increment=0.05,
            textvariable=self.silence_min_dur_var, width=6, font=("Consolas", 9, "bold"),
            command=self._save_settings, justify="center"
        ).grid(row=0, column=1, sticky="ew", padx=(3, 8))

        self.lbl_sil_pad = ttk.Label(sil_p_row, text="هامش كلام(ث):" if is_ar else "Pad(s):")
        self.lbl_sil_pad.grid(row=0, column=2, sticky="w")
        ttk.Spinbox(
            sil_p_row, from_=0.00, to=1.00, increment=0.02,
            textvariable=self.silence_padding_var, width=6, font=("Consolas", 9, "bold"),
            command=self._on_silence_padding_changed, justify="center"
        ).grid(row=0, column=3, sticky="ew", padx=(3, 0))

        self.btn_live_cut_silences = ttk.Button(
            self.ctx_frame_silence,
            text="⚡ حذف السكتات تلقائياً من التايم لاين" if is_ar else "⚡ Auto-Cut Silences on Timeline",
            command=lambda: self._split_silences_onto_nle_timeline(True),
            style="PrimaryPlayer.TButton",
        )
        self.btn_live_cut_silences.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(4, 2))

        self.btn_live_mark_silences = ttk.Button(
            self.ctx_frame_silence,
            text="🔇 فحص وكتم السكتات للمراجعة اليدوية" if is_ar else "🔇 Mute Silences for Review",
            command=lambda: self._split_silences_onto_nle_timeline(False),
            style="Player.TButton",
        )
        self.btn_live_mark_silences.grid(row=4, column=0, columnspan=3, sticky="ew", pady=2)

        sil_bot = ttk.Frame(self.ctx_frame_silence)
        sil_bot.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        sil_bot.columnconfigure(0, weight=1)
        sil_bot.columnconfigure(1, weight=1)
        self.btn_sil_auto_db_inline = ttk.Button(
            sil_bot,
            text="🎯 معايرة الحساسية تلقائياً (Auto dB)" if is_ar else "🎯 Auto Calibrate (dB)",
            command=self.start_auto_detect_silence_db,
            style="Player.TButton",
        )
        self.btn_sil_auto_db_inline.grid(row=0, column=0, sticky="ew", padx=(0, 2))
        self.btn_silence_studio = ttk.Button(
            sil_bot,
            text="📑 قائمة السكتات المتقدمة" if is_ar else self.text("btn_silence_studio"),
            command=lambda: self.notebook.select(self.tab_silence),
            style="Player.TButton",
        )
        self.btn_silence_studio.grid(row=0, column=1, sticky="ew", padx=(2, 0))

        self.lbl_sil_auto_diag = ttk.Label(
            self.ctx_frame_silence,
            text="",
            font=("Segoe UI", 8),
            foreground="#56d364",
            wraplength=340,
        )
        self.lbl_sil_auto_diag.grid(row=6, column=0, columnspan=3, sticky="w", pady=(3, 0))

        # ---------------- Context 5: Audio Enhancement & Gain Boost ----------------
        self.ctx_frame_audio = ttk.LabelFrame(
            self.dynamic_inspector_host,
            text="🔊 إعدادات وتحسين الصوت" if is_ar else "🔊 Audio Settings & Enhancements",
            padding=(7, 5, 7, 5),
        )
        self.ctx_frame_audio.grid(row=0, column=0, sticky="nsew")
        self.ctx_frame_audio.columnconfigure(1, weight=1)

        self.chk_studio_audio_fx = ttk.Checkbutton(
            self.ctx_frame_audio,
            text="تطبيق تحسينات الصوت" if is_ar else "Apply Audio Enhancements",
            variable=self.export_opt_audio_fx_var,
            command=self._refresh_master_export_summary,
        )
        self.chk_studio_audio_fx.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))

        self.lbl_studio_enhance = ttk.Label(self.ctx_frame_audio, text=self.text("enhance"))
        self.lbl_studio_enhance.grid(row=1, column=0, sticky="w", pady=3)
        self.studio_enhance_combo = ttk.Combobox(
            self.ctx_frame_audio,
            textvariable=self.enhancement_var,
            state="readonly",
        )
        self.studio_enhance_combo.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(4, 0), pady=3)
        self.studio_enhance_combo.bind("<<ComboboxSelected>>", lambda _e: (self._remember_enhancement_key(), self._refresh_master_export_summary()))

        self.lbl_studio_gain = ttk.Label(self.ctx_frame_audio, text="تكبير الصوت dB:" if is_ar else "Gain Boost dB:")
        self.lbl_studio_gain.grid(row=2, column=0, sticky="w", pady=3)
        ttk.Scale(
            self.ctx_frame_audio, from_=0.0, to=25.0, variable=self.boost_gain_var,
            orient="horizontal", command=lambda _v: (self._boost_gain_changed(), self._refresh_master_export_summary()),
        ).grid(row=2, column=1, sticky="ew", padx=4, pady=3)
        tk.Spinbox(
            self.ctx_frame_audio, from_=0.0, to=25.0, increment=0.5, format="%.1f",
            textvariable=self.boost_gain_var, width=5, font=("Consolas", 8, "bold"),
            command=lambda: (self._boost_gain_changed(), self._refresh_master_export_summary()),
        ).grid(row=2, column=2, pady=3)

        self.chk_studio_anticlip = ttk.Checkbutton(
            self.ctx_frame_audio,
            text=self.text("volume_anti_clipping"),
            variable=self.boost_anti_clip_var,
        )
        self.chk_studio_anticlip.grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 0))

        # Audio Tracks & External Mixing Controls
        aud_tracks_card = ttk.LabelFrame(
            self.ctx_frame_audio,
            text="🎚️ مسارات وتحكم الصوت" if is_ar else "🎚️ Audio Tracks & Mixing",
            padding=(7, 5, 7, 5),
        )
        aud_tracks_card.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(8, 2))
        aud_tracks_card.columnconfigure(0, weight=1)

        self.btn_toggle_orig_audio = ttk.Button(
            aud_tracks_card,
            text="🔇 كتم صوت الفيديو الأصلي بالكامل (A1)" if is_ar else "🔇 Mute Video Audio (A1)",
            command=self._toggle_orig_video_audio,
            style="Player.TButton",
        )
        self.btn_toggle_orig_audio.grid(row=0, column=0, sticky="ew", pady=(1, 3))
        add_tooltip(self.btn_toggle_orig_audio, "كتم أو تفعيل صوت الفيديو الأصلي بالكامل (مسار A1)", "Toggle original video audio track (A1) mute", app=self)

        self.btn_add_ext_audio = ttk.Button(
            aud_tracks_card,
            text="➕ إضافة ملف صوت / موسيقى (مسار A2)" if is_ar else "➕ Add Audio / Music (A2)",
            command=lambda: self.davinci_timeline.add_audio_file_dialog() if hasattr(self, "davinci_timeline") else None,
            style="PrimaryPlayer.TButton",
        )
        self.btn_add_ext_audio.grid(row=1, column=0, sticky="ew", pady=(1, 3))
        add_tooltip(self.btn_add_ext_audio, "إضافة ملف صوت أو مؤثر موسيقي خارجي في مسار A2", "Add external audio or music file to track A2", app=self)

        self.lbl_audio_tracks_status = ttk.Label(
            aud_tracks_card,
            text="",
            font=("Segoe UI", 8),
            foreground="#58a6ff",
            wraplength=330,
        )
        self.lbl_audio_tracks_status.grid(row=2, column=0, sticky="w", pady=(2, 0))

        # ---------------- Context 6: AI Transcription, Subtitles & Quick Range Trim ----------------
        self.ctx_frame_subs = ttk.Frame(self.dynamic_inspector_host)
        self.ctx_frame_subs.grid(row=0, column=0, sticky="nsew")
        self.ctx_frame_subs.columnconfigure(0, weight=1)

        style_card = ttk.LabelFrame(self.ctx_frame_subs, padding=(7, 4, 7, 5))
        style_card.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        style_card.columnconfigure(0, weight=1)
        style_card.columnconfigure(1, weight=1)
        self.i18n_widgets["trim_style_group"] = style_card
        self.trim_style_row = style_card

        self.chk_studio_save_transcript = ttk.Checkbutton(
            style_card,
            text="🎙️ تفريغ صوتي وحفظ ملف نصي وترجمة (.txt + .srt)" if is_ar else "🎙️ AI Transcribe & Save (.txt + .srt)",
            variable=self.export_opt_transcript_files_var,
            command=self._refresh_master_export_summary,
        )
        self.chk_studio_save_transcript.grid(row=0, column=0, columnspan=2, sticky="w", pady=1)

        self.trim_burn_subs_check = ttk.Checkbutton(
            style_card,
            text=self.text("trim_burn_subtitles"),
            variable=self.trim_burn_subs_var,
            command=self._on_trim_branding_toggle,
        )
        self.trim_burn_subs_check.grid(row=1, column=0, sticky="w", pady=1)

        self.trim_logo_check = ttk.Checkbutton(
            style_card,
            text=self.text("trim_add_logo"),
            variable=self.trim_logo_var,
            command=self._on_trim_branding_toggle,
        )
        self.trim_logo_check.grid(row=1, column=1, sticky="w", pady=1)

        self.trim_title_check = ttk.Checkbutton(
            style_card,
            text=self.text("trim_add_title"),
            variable=self.trim_title_var,
            command=self._on_trim_branding_toggle,
        )
        self.trim_title_check.grid(row=2, column=0, columnspan=2, sticky="w", pady=1)

        subs_btns = ttk.Frame(style_card)
        subs_btns.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(3, 0))
        subs_btns.columnconfigure(0, weight=1)
        subs_btns.columnconfigure(1, weight=1)
        self.btn_studio_transcribe = ttk.Button(
            subs_btns,
            text="🎙️ تفريغ بالذكاء الاصطناعي الآن" if is_ar else "🎙️ Transcribe Audio Now",
            command=self._start_studio_transcription_quick,
            style="PrimaryPlayer.TButton",
        )
        self.btn_studio_transcribe.grid(row=0, column=0, sticky="ew", padx=(0, 2))
        add_tooltip(self.btn_studio_transcribe, "بدء التفريغ الصوتي الذكي وتحويل الكلام لنصوص وترجمة دقيقة", "Transcribe audio to subtitles using AI", app=self)
        self.btn_branding = ttk.Button(
            subs_btns,
            text=self.text("branding_btn"),
            command=self.open_video_branding_dialog,
            style="Player.TButton",
        )
        self.btn_branding.grid(row=0, column=1, sticky="ew", padx=(2, 0))
        add_tooltip(self.btn_branding, "فتح إعدادات العلامة المائية والشعار والنصوص المتحركة", "Open Video Branding & Watermark Dialog", app=self)

        # Quick Range Trim Card
        controls = ttk.LabelFrame(self.ctx_frame_subs, padding=(7, 4, 7, 5))
        controls.grid(row=1, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)
        self.i18n_widgets["tools_group"] = controls

        self.i18n_widgets["trim_start_label"] = ttk.Label(controls)
        self.i18n_widgets["trim_start_label"].grid(row=0, column=0, sticky="w", pady=1)
        self.trim_start_entry = ttk.Entry(controls, textvariable=self.trim_start_var, width=10)
        self.trim_start_entry.grid(row=0, column=1, padx=(6, 4), sticky="ew", pady=1)
        self.mark_start_button = ttk.Button(controls, command=self.mark_trim_start, style="Player.TButton")
        self.mark_start_button.grid(row=0, column=2, sticky="e", pady=1)
        add_tooltip(self.mark_start_button, "تحديد موضع بداية القص من موقع مؤشر التشغيل الحالي (I)", "Set Trim Start to Current Time (I)", app=self)

        self.i18n_widgets["trim_end_label"] = ttk.Label(controls)
        self.i18n_widgets["trim_end_label"].grid(row=1, column=0, sticky="w", pady=1)
        self.trim_end_entry = ttk.Entry(controls, textvariable=self.trim_end_var, width=10)
        self.trim_end_entry.grid(row=1, column=1, padx=(6, 4), sticky="ew", pady=1)
        self.mark_end_button = ttk.Button(controls, command=self.mark_trim_end, style="Player.TButton")
        self.mark_end_button.grid(row=1, column=2, sticky="e", pady=1)
        add_tooltip(self.mark_end_button, "تحديد موضع نهاية القص من موقع مؤشر التشغيل الحالي (O)", "Set Trim End to Current Time (O)", app=self)

        trim_act_row = ttk.Frame(controls)
        trim_act_row.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(3, 0))
        trim_act_row.columnconfigure(1, weight=1)

        self.trim_extract_audio_check = ttk.Checkbutton(
            trim_act_row,
            text=self.text("trim_extract_audio"),
            variable=self.trim_extract_audio_var,
        )
        self.trim_extract_audio_check.grid(row=0, column=0, sticky="w")

        self.trim_button = ttk.Button(trim_act_row, command=self.start_trim, style="Action.TButton")
        self.trim_button.grid(row=0, column=1, sticky="e")

        # ---------------- Context 7: Modular Master Video Export ----------------
        self.ctx_frame_export = ttk.LabelFrame(
            self.dynamic_inspector_host,
            text="🚀 إعدادات وتصدير الفيديو" if is_ar else "🚀 Export Video Studio",
            padding=(8, 6, 8, 6),
        )
        self.ctx_frame_export.grid(row=0, column=0, sticky="nsew")
        self.ctx_frame_export.columnconfigure(0, weight=1)
        self.master_export_frame = self.ctx_frame_export
        self.i18n_widgets["master_export_card"] = self.ctx_frame_export

        # Back Navigation Row inside export context
        exp_nav_bar = ttk.Frame(self.ctx_frame_export)
        exp_nav_bar.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        exp_nav_bar.columnconfigure(0, weight=1)
        self.lbl_exp_ctx_title = ttk.Label(
            exp_nav_bar,
            text="🎬 تجهيز وإعداد التصدير النهائي" if is_ar else "🎬 Final Export Setup",
            font=("Segoe UI", 9, "bold"),
            foreground="#2ea043",
        )
        self.lbl_exp_ctx_title.grid(row=0, column=0, sticky="w")
        self.btn_exp_back = ttk.Button(
            exp_nav_bar,
            text="⬅ عودة للإعدادات" if is_ar else "⬅ Back to Settings",
            command=self._back_from_export,
            style="Player.TButton",
        )
        self.btn_exp_back.grid(row=0, column=1, sticky="e")

        # Selective Export Checkboxes (choose 1, 2, or ALL edits!)
        exp_hdr = ttk.Frame(self.ctx_frame_export)
        exp_hdr.grid(row=1, column=0, sticky="ew", pady=(2, 2))
        exp_hdr.columnconfigure(0, weight=1)
        self.lbl_exp_pick = ttk.Label(
            exp_hdr,
            text="☑️ اختر التعديلات المطلوب تصديرها:" if is_ar else "☑️ Select Edits to Export:",
            font=("Segoe UI", 8, "bold"),
        )
        self.lbl_exp_pick.grid(row=0, column=0, sticky="w")
        self.btn_exp_all = ttk.Button(
            exp_hdr, text="الكل" if is_ar else "All", width=5, style="Player.TButton",
            command=lambda: self._set_all_export_toggles(True),
        )
        self.btn_exp_all.grid(row=0, column=1, padx=(2, 2))
        self.btn_exp_none = ttk.Button(
            exp_hdr, text="يدوي" if is_ar else "None", width=5, style="Player.TButton",
            command=lambda: self._set_all_export_toggles(False),
        )
        self.btn_exp_none.grid(row=0, column=2, padx=(0, 2))

        self._export_card_collapsed = False
        self.btn_exp_collapse = ttk.Button(
            exp_hdr,
            text="▲ إخفاء" if is_ar else "▲ Hide",
            width=6,
            style="Player.TButton",
            command=self._toggle_export_card_collapse,
        )
        self.btn_exp_collapse.grid(row=0, column=3)

        exp_scope_group = ttk.LabelFrame(
            self.ctx_frame_export,
            text="🎯 نوع ونطاق التصدير المطلـوب:" if is_ar else "🎯 Export Scope & Target:",
            padding=(8, 6, 8, 6),
        )
        exp_scope_group.grid(row=2, column=0, sticky="ew", pady=(4, 5))
        self.exp_scope_group = exp_scope_group
        self.exp_scope_row = exp_scope_group
        exp_scope_group.columnconfigure(0, weight=1)
        exp_scope_group.columnconfigure(1, weight=1)
        exp_scope_group.columnconfigure(2, weight=1)

        self.export_scope_var = tk.StringVar(value="all")
        self.rdo_scope_all = ttk.Radiobutton(
            exp_scope_group,
            text="🎬 كامل المشروع (فيديو مدمج)" if is_ar else "🎬 Full Sequence (Single Video)",
            variable=self.export_scope_var,
            value="all",
            command=self._on_export_scope_changed,
        )
        self.rdo_scope_all.grid(row=0, column=0, sticky="w", padx=(2, 4))

        self.rdo_scope_sel = ttk.Radiobutton(
            exp_scope_group,
            text="🎞️ المقطع المحدد فقط" if is_ar else "🎞️ Selected Clip Only",
            variable=self.export_scope_var,
            value="selected",
            command=self._on_export_scope_changed,
        )
        self.rdo_scope_sel.grid(row=0, column=1, sticky="w", padx=4)

        self.rdo_scope_sep = ttk.Radiobutton(
            exp_scope_group,
            text="📂 كل مقطع في ملف منفصل" if is_ar else "📂 Each Clip Separately",
            variable=self.export_scope_var,
            value="separate",
            command=self._on_export_scope_changed,
        )
        self.rdo_scope_sep.grid(row=0, column=2, sticky="w", padx=(4, 2))

        exp_checks = ttk.LabelFrame(
            self.ctx_frame_export,
            text="🎛️ التعديلات المختارة للتصدير" if is_ar else "🎛️ Selective Edits to Export",
            padding=(6, 4, 6, 4),
        )
        exp_checks.grid(row=3, column=0, sticky="ew", pady=(2, 4))
        self.exp_checks = exp_checks
        for ci in range(4):
            exp_checks.columnconfigure(ci, weight=1)

        self.chk_exp_framing = ttk.Checkbutton(
            exp_checks, text="كادر/أبعاد" if is_ar else "Framing",
            variable=self.export_opt_framing_var, command=self._refresh_master_export_summary,
        )
        self.chk_exp_framing.grid(row=0, column=0, sticky="w")

        self.chk_exp_timeline = ttk.Checkbutton(
            exp_checks, text="قص التايم لاين" if is_ar else "Timeline",
            variable=self.export_opt_timeline_var, command=self._refresh_master_export_summary,
        )
        self.chk_exp_timeline.grid(row=0, column=1, sticky="w")

        self.chk_exp_overlays = ttk.Checkbutton(
            exp_checks, text="عناصر ولوجو" if is_ar else "Overlays",
            variable=self.export_opt_overlays_var, command=self._refresh_master_export_summary,
        )
        self.chk_exp_overlays.grid(row=0, column=2, sticky="w")

        self.chk_exp_color = ttk.Checkbutton(
            exp_checks, text="ألوان" if is_ar else "Colors",
            variable=self.trim_color_var, command=self._on_trim_branding_toggle,
        )
        self.chk_exp_color.grid(row=0, column=3, sticky="w")

        self.chk_exp_silence = ttk.Checkbutton(
            exp_checks, text="قص السكتات" if is_ar else "Silence Cut",
            variable=self.trim_remove_silence_var, command=self._on_trim_branding_toggle,
        )
        self.chk_exp_silence.grid(row=1, column=0, sticky="w")

        self.chk_exp_audio = ttk.Checkbutton(
            exp_checks, text="تحسين الصوت" if is_ar else "Audio FX",
            variable=self.export_opt_audio_fx_var, command=self._refresh_master_export_summary,
        )
        self.chk_exp_audio.grid(row=1, column=1, sticky="w")

        self.chk_exp_subs = ttk.Checkbutton(
            exp_checks, text="دمج ترجمة" if is_ar else "Burn Subs",
            variable=self.trim_burn_subs_var, command=self._on_trim_branding_toggle,
        )
        self.chk_exp_subs.grid(row=1, column=2, sticky="w")

        self.chk_exp_transcript = ttk.Checkbutton(
            exp_checks, text="تفريغ نصي" if is_ar else "Transcript",
            variable=self.export_opt_transcript_files_var, command=self._refresh_master_export_summary,
        )
        self.chk_exp_transcript.grid(row=1, column=3, sticky="w")

        # Format & Size/Quality Row ("بنفس حجمه وبنفس صيغته أو بتغييرها")
        exp_fmt_row = ttk.LabelFrame(
            self.ctx_frame_export,
            text="⚙️ الصيغة وجودة الضغط" if is_ar else "⚙️ Format & Quality",
            padding=(6, 4, 6, 4),
        )
        exp_fmt_row.grid(row=4, column=0, sticky="ew", pady=(2, 4))
        self.exp_fmt_row = exp_fmt_row
        exp_fmt_row.columnconfigure(1, weight=1)
        exp_fmt_row.columnconfigure(3, weight=1)

        self.lbl_exp_fmt = ttk.Label(exp_fmt_row, text="الصيغة:" if is_ar else "Format:")
        self.lbl_exp_fmt.grid(row=0, column=0, sticky="w")
        self.export_format_combo_var = tk.StringVar()
        self.export_format_combo = ttk.Combobox(
            exp_fmt_row, textvariable=self.export_format_combo_var, state="readonly", width=13,
        )
        self.export_format_combo.grid(row=0, column=1, sticky="ew", padx=(3, 6))
        self.export_format_combo.bind("<<ComboboxSelected>>", self._on_export_format_or_size_changed)

        self.lbl_exp_size = ttk.Label(exp_fmt_row, text="الضغط/الجودة:" if is_ar else "Quality/Comp:")
        self.lbl_exp_size.grid(row=0, column=2, sticky="w")
        self.export_size_combo_var = tk.StringVar()
        self.export_size_combo = ttk.Combobox(
            exp_fmt_row, textvariable=self.export_size_combo_var, state="readonly", width=13,
        )
        self.export_size_combo.grid(row=0, column=3, sticky="ew", padx=(3, 0))
        self.export_size_combo.bind("<<ComboboxSelected>>", self._on_export_format_or_size_changed)

        self.lbl_exp_encoder = ttk.Label(exp_fmt_row, text="المسرّع (GPU):" if is_ar else "Encoder (GPU):")
        self.lbl_exp_encoder.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.export_encoder_combo = ttk.Combobox(
            exp_fmt_row, textvariable=self.export_encoder_combo_var, state="readonly", width=28,
        )
        self.export_encoder_combo.grid(row=1, column=1, columnspan=3, sticky="ew", padx=(3, 0), pady=(4, 0))
        self.export_encoder_combo.bind("<<ComboboxSelected>>", self._on_export_encoder_changed)

        self._refresh_modular_export_combos()

        self.master_export_summary_label = ttk.Label(
            self.ctx_frame_export,
            textvariable=self.master_export_summary_var,
            font=("Segoe UI", 8, "italic"),
            wraplength=340,
        )
        self.master_export_summary_label.grid(row=5, column=0, sticky="ew", pady=(2, 4))

        self.btn_master_export = ttk.Button(
            self.ctx_frame_export,
            text=self.text("master_export_btn"),
            command=self.start_master_export,
            style="Action.TButton",
        )
        self.btn_master_export.grid(row=6, column=0, sticky="ew", pady=(2, 2))

        self.nle_v_paned.add(top_workspace, minsize=295, stretch="always")

        # ---------------- Bottom Pane: DaVinci Multi-Track NLE Timeline ----------------
        self.davinci_timeline = DaVinciTimelinePanel(
            self.nle_v_paned,
            nle_state=self.nle_project,
            is_ar_fn=lambda: self.language_var.get() == "العربية",
            on_scrub=self._on_nle_timeline_scrub,
            on_select=self._on_nle_timeline_select,
            on_modified=self._on_nle_timeline_modified,
            on_add_element=self._nle_add_element,
            on_split_silences=self._split_silences_onto_nle_timeline,
            on_export_clip=self.export_selected_clip_only,
            on_export_all_clips=self.export_all_clips_separately,
        )
        self.nle_v_paned.add(self.davinci_timeline, minsize=200, stretch="never")
        self.davinci_timeline.on_undo_request = self.do_app_undo
        self.davinci_timeline.on_redo_request = self.do_app_redo
        self.davinci_timeline.can_undo_fn = lambda: bool(self._app_undo_stack)
        self.davinci_timeline.can_redo_fn = lambda: bool(self._app_redo_stack)

        self._show_inspector_context("video")
        self._sync_transform_sliders_from_state()
        self._update_inspector_properties()



    def _build_tab_youtube(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        youtube_panel = ttk.LabelFrame(parent, padding=16)
        youtube_panel.grid(row=0, column=0, sticky="nsew")
        youtube_panel.columnconfigure(1, weight=1)
        self.i18n_widgets["youtube_group"] = youtube_panel

        self.i18n_widgets["youtube_url_label"] = ttk.Label(youtube_panel)
        self.i18n_widgets["youtube_url_label"].grid(row=0, column=0, sticky="w")
        self.youtube_url_entry = ttk.Entry(youtube_panel, textvariable=self.youtube_url_var)
        self.youtube_url_entry.grid(row=0, column=1, padx=(10, 8), sticky="ew")
        self._attach_entry_context_menu(self.youtube_url_entry)

        self.fetch_youtube_button = ttk.Button(youtube_panel, command=self.start_fetch_youtube_formats, style="Action.TButton")
        self.fetch_youtube_button.grid(row=0, column=2, sticky="w")
        add_tooltip(self.fetch_youtube_button, "فحص الرابط واستخراج الجودات والصيغ المتاحة للتحميل", "Fetch available video formats & resolutions", app=self)

        self.i18n_widgets["youtube_quality_label"] = ttk.Label(youtube_panel)
        self.i18n_widgets["youtube_quality_label"].grid(row=1, column=0, sticky="w", pady=(12, 0))
        self.youtube_quality_combo = ttk.Combobox(
            youtube_panel,
            textvariable=self.youtube_quality_var,
            state="readonly",
        )
        self.youtube_quality_combo.grid(row=1, column=1, padx=(10, 8), sticky="ew", pady=(12, 0))
        self.youtube_quality_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_youtube_details())

        self.download_youtube_button = ttk.Button(
            youtube_panel,
            command=self.start_youtube_download,
            style="Action.TButton",
        )
        self.download_youtube_button.grid(row=1, column=2, sticky="w", pady=(12, 0))
        add_tooltip(self.download_youtube_button, "بدء تنزيل الفيديو بأعلى جودة وحفظه في جهازك", "Download video from YouTube", app=self)

        dest_row = ttk.Frame(youtube_panel)
        dest_row.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(16, 0))
        dest_row.columnconfigure(1, weight=1)

        self.choose_youtube_output_button = ttk.Button(dest_row, command=self.choose_youtube_output_folder, style="Player.TButton")
        self.choose_youtube_output_button.grid(row=0, column=0, sticky="w")
        add_tooltip(self.choose_youtube_output_button, "تحديد المجلد الذي سيتم حفظ الفيديو المحمل بداخله", "Choose destination folder for downloaded video", app=self)
        self.youtube_detail_label = ttk.Label(dest_row, textvariable=self.youtube_detail_var, foreground="#0066cc", font=("Segoe UI", 9))
        self.youtube_detail_label.grid(
            row=0, column=1, padx=(10, 0), sticky="w"
        )

    # ------------------ Smart Silence Cut Studio Methods ------------------

















    def _draw_player_visual_timeline(self, playhead_only: bool = False):
        if not hasattr(self, "player_visual_timeline") or not self.player_visual_timeline.winfo_exists():
            return
        c = self.player_visual_timeline
        w = max(10, c.winfo_width())
        h = max(8, c.winfo_height())
        tot = float(self.media_duration or 0.0)
        if tot <= 0 and self.silence_analysis_result:
            tot = float(self.silence_analysis_result.get("total_duration", 0.0))

        tl_s = float(self.timeline_var.get() or 0.0)
        _idx, _c, cur_s = self.nle_project.timeline_to_source(tl_s) if hasattr(self, "nle_project") else (0, None, tl_s)

        sil_list = self.silence_analysis_result.get("silences", []) if self.silence_analysis_result else []
        bg_sig = (
            w, h, round(tot, 2),
            len(sil_list),
            self.trim_start_var.get().strip(),
            self.trim_end_var.get().strip(),
        )
        if (
            playhead_only
            and tot > 0
            and getattr(self, "_pvt_bg_sig", None) == bg_sig
            and getattr(self, "_pvt_playhead_id", None) is not None
        ):
            xp = max(1, min(w - 1, int((cur_s / tot) * w)))
            try:
                c.coords(self._pvt_playhead_id, xp, 0, xp, h)
                return
            except Exception:
                pass

        c.delete("all")
        self._pvt_playhead_id = None
        self._pvt_bg_sig = bg_sig
        if tot <= 0:
            c.create_rectangle(0, 0, w, h, fill="#161b22", outline="")
            return

        has_sil = bool(sil_list)
        c.create_rectangle(0, 0, w, h, fill="#1f6f3d" if has_sil else "#21262d", outline="")

        if has_sil:
            for s_item in sil_list:
                if not s_item.get("enabled", True):
                    continue
                x1 = int((s_item["start"] / tot) * w)
                x2 = max(x1 + 2, int((s_item["end"] / tot) * w))
                c.create_rectangle(x1, 2, x2, h - 2, fill="#da3633", outline="")

        try:
            s_raw = self.trim_start_var.get().strip()
            e_raw = self.trim_end_var.get().strip()
            if s_raw:
                s_sec = convert.parse_time_seconds(s_raw)
                xs = int((s_sec / tot) * w)
                c.create_line(xs, 0, xs, h, fill="#58a6ff", width=2)
            if e_raw:
                e_sec = convert.parse_time_seconds(e_raw)
                xe = int((e_sec / tot) * w)
                c.create_line(xe, 0, xe, h, fill="#58a6ff", width=2)
        except Exception:
            pass

        xp = max(1, min(w - 1, int((cur_s / tot) * w)))
        self._pvt_playhead_id = c.create_line(xp, 0, xp, h, fill="#ffd700", width=2)

    def _on_player_visual_timeline_click(self, event):
        tot = float(self.media_duration or 0.0)
        if tot <= 0:
            return
        w = max(1, self.player_visual_timeline.winfo_width())
        src_sec = max(0.0, min(tot, (event.x / w) * tot))
        if hasattr(self, "nle_project") and self.nle_project.clips:
            c_idx, tl_sec = self.nle_project.source_to_timeline(src_sec)
            self.active_playback_clip_idx = c_idx
        else:
            tl_sec = src_sec
        self.nle_playhead_sec = tl_sec
        self.timeline_var.set(tl_sec)
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.set_playhead(tl_sec, auto_follow=True)
        self._refresh_timeline_text()
        self._draw_player_visual_timeline()
        if self._is_playing():
            self._start_media_from(src_sec, is_timeline_time=False)
        else:
            if getattr(self, "studio_live_preview_mode", False):
                self._show_studio_canvas()
                self._request_fast_preview_frame(src_sec, force=True)
            else:
                self._show_vlc_surface()
                if self.media_player and self.media_player.get_state() not in {vlc.State.Ended, vlc.State.Error, vlc.State.Stopped}:
                    self.media_player.set_time(int(src_sec * 1000))

    def capture_current_frame_snapshot(self):
        if not self.input_path or not self.input_path.is_file() or not convert.has_video_stream(self.input_path):
            messagebox.showwarning(self.text("app_title"), self.text("video_required"))
            return
        is_ar = self.language_var.get() == "العربية"
        out_dir = self.output_dir or (self.input_path.parent / "output")
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        tl_ts = self._current_timeline_seconds()

        # Generate full-res composite (overlays, animations, color grading, aspect ratio)
        img = None
        if hasattr(self, "compose_full_res_snapshot_frame"):
            try:
                img = self.compose_full_res_snapshot_frame()
            except Exception as e:
                self._append_log(f"[Snapshot Compose Info] {e}\n")

        stem = self.input_path.stem
        ts_tag = f"{int(tl_ts // 60):02d}m{int(tl_ts % 60):02d}s"
        default_name = f"{stem}_cover_{ts_tag}.jpg"
        out_file = out_dir / default_name

        try:
            if img is not None:
                img.convert("RGB").save(str(out_file), "JPEG", quality=95)
            else:
                color_cfg = self.video_branding_config.get("color_config") if (hasattr(self, "trim_color_var") and self.trim_color_var.get()) else None
                _idx, _c, ts = self.nle_project.timeline_to_source(tl_ts) if hasattr(self, "nle_project") else (0, None, tl_ts)
                out_file = convert.capture_video_snapshot(
                    video_path=self.input_path,
                    timestamp_sec=ts,
                    output_dir=out_dir,
                    color_config=color_cfg,
                )

            msg = f"📸 تم حفظ صورة الغلاف عالية الدقة:\n{out_file.name}" if is_ar else f"📸 High-Res Cover Snapshot saved:\n{out_file.name}"
            self.status_var.set(msg)
            self._append_log(f"[Cover Snapshot] {out_file}\n")
            if hasattr(self, "davinci_timeline"):
                self.davinci_timeline.show_hud_toast("📸 " + ("تم حفظ لقطة الغلاف الاحترافية!" if is_ar else "Cover Snapshot Saved!"))
            messagebox.showinfo(self.text("app_title"), f"{msg}\n\n{out_file}")
        except Exception as exc:
            messagebox.showerror(self.text("app_title"), f"Snapshot failed: {exc}")



    # ------------------ Volume Booster & Audio Mastering Methods ------------------






    # ------------------ Auto Caption Methods ------------------
































    # ------------------ Language & Localized Labels ------------------
    def _apply_language(self):
        is_ar = self.language_var.get() == "العربية"
        self.title(self.text("app_title"))
        self.i18n_widgets["title"].configure(text=self.text("app_title"))
        self.i18n_widgets["subtitle"].configure(text=self.text("subtitle"))
        self.i18n_widgets["language_label"].configure(text=self.text("language"))
        self.i18n_widgets["source_group"].configure(text=self.text("source_group"))
        self.i18n_widgets["conversion_group"].configure(text=self.text("audio_options"))
        self.i18n_widgets["video_only_group"].configure(text=self.text("video_options"))
        self.i18n_widgets["volume_analysis_group"].configure(text=self.text("volume_analysis_group"))
        self.i18n_widgets["volume_group"].configure(text=self.text("volume_group"))
        self.i18n_widgets["media_player_group"].configure(text=self.text("media_player_group"))
        self.i18n_widgets["tools_group"].configure(text=self.text("trim_group"))
        if "trim_style_group" in self.i18n_widgets:
            self.i18n_widgets["trim_style_group"].configure(text=self.text("trim_style_group"))
        if "master_export_card" in self.i18n_widgets:
            self.i18n_widgets["master_export_card"].configure(text=self.text("master_export_card"))
        self.i18n_widgets["caption_settings_group"].configure(text=self.text("caption_settings_group"))
        self.i18n_widgets["caption_output_group"].configure(text=self.text("caption_output_group"))
        if "silence_settings_group" in self.i18n_widgets:
            self.i18n_widgets["silence_settings_group"].configure(text=self.text("silence_settings_group"))
        if "silence_results_group" in self.i18n_widgets:
            self.i18n_widgets["silence_results_group"].configure(text=self.text("silence_results_group"))
        self.i18n_widgets["cover_group"].configure(text=self.text("cover_group"))
        self.i18n_widgets["youtube_group"].configure(text=self.text("youtube_group"))
        self.i18n_widgets["log_group"].configure(text=self.text("log_group"))

        # Update Notebook tab titles
        self.notebook.tab(0, text=self.text("tab_convert"))
        self.notebook.tab(1, text=self.text("tab_volume"))
        self.notebook.tab(2, text=self.text("tab_player"))
        self.notebook.tab(3, text=self.text("tab_silence"))
        self.notebook.tab(4, text=self.text("tab_caption"))
        self.notebook.tab(5, text=self.text("tab_youtube"))

        # Labels
        self.i18n_widgets["output_label"].configure(text=self.text("output"))
        self.i18n_widgets["format_label"].configure(text=self.text("format"))
        self.i18n_widgets["quality_label"].configure(text=self.text("quality"))
        self.i18n_widgets["enhance_label"].configure(text=self.text("enhance"))
        if "boost_enhance_label" in self.i18n_widgets:
            self.i18n_widgets["boost_enhance_label"].configure(text=self.text("enhance"))
        if "fade_in_label" in self.i18n_widgets:
            self.i18n_widgets["fade_in_label"].configure(text=self.text("audio_fade_in"))
        if "fade_out_label" in self.i18n_widgets:
            self.i18n_widgets["fade_out_label"].configure(text=self.text("audio_fade_out"))
        self.i18n_widgets["video_format_label"].configure(text=self.text("video_format"))
        self.i18n_widgets["video_compression_label"].configure(text=self.text("video_compression"))
        self.i18n_widgets["video_resolution_label"].configure(text=self.text("video_resolution"))
        self.i18n_widgets["volume_gain_label"].configure(text=self.text("volume_gain_label"))
        self.i18n_widgets["boost_fmt_label"].configure(text=self.text("format"))
        self.i18n_widgets["timeline_label"].configure(text=self.text("timeline"))
        self.i18n_widgets["speed_label"].configure(text=self.text("speed"))
        self.i18n_widgets["volume_label"].configure(text=self.text("volume"))
        self.i18n_widgets["trim_start_label"].configure(text=self.text("trim_start"))
        self.i18n_widgets["trim_end_label"].configure(text=self.text("trim_end"))
        if "silence_preset_label" in self.i18n_widgets:
            self.i18n_widgets["silence_preset_label"].configure(text=self.text("silence_preset_label"))
        if "silence_mode_label" in self.i18n_widgets:
            self.i18n_widgets["silence_mode_label"].configure(text=self.text("silence_mode_label"))
        if "silence_threshold_label" in self.i18n_widgets:
            self.i18n_widgets["silence_threshold_label"].configure(text=self.text("silence_threshold_label"))
        if "silence_min_dur_label" in self.i18n_widgets:
            self.i18n_widgets["silence_min_dur_label"].configure(text=self.text("silence_min_dur_label"))
        if "silence_padding_label" in self.i18n_widgets:
            self.i18n_widgets["silence_padding_label"].configure(text=self.text("silence_padding_label"))
        if "silence_quality_label" in self.i18n_widgets:
            self.i18n_widgets["silence_quality_label"].configure(text=self.text("silence_quality_label"))
        if "silence_format_label" in self.i18n_widgets:
            self.i18n_widgets["silence_format_label"].configure(text=self.text("silence_format_label"))
        self.i18n_widgets["caption_model_label"].configure(text=self.text("caption_model_label"))
        if "caption_models_dir" in self.i18n_widgets:
            self.i18n_widgets["caption_models_dir"].configure(text=self.text("caption_models_dir"))
        self.i18n_widgets["caption_lang_label"].configure(text=self.text("caption_lang_label"))
        if "caption_translate_label" in self.i18n_widgets:
            self.i18n_widgets["caption_translate_label"].configure(text=self.text("caption_translate_label"))
        if hasattr(self, "caption_translate_button"):
            self.caption_translate_button.configure(text=self.text("caption_translate_btn"))
        self.i18n_widgets["manual_search_label"].configure(text=self.text("manual_search"))
        self.i18n_widgets["youtube_url_label"].configure(text=self.text("youtube_url"))
        self.i18n_widgets["youtube_quality_label"].configure(text=self.text("youtube_quality"))

        # Buttons
        self.choose_file_button.configure(text=self.text("choose_file"))
        self.choose_folder_button.configure(text=self.text("choose_folder"))
        self.open_input_button.configure(text=self.text("open_source"))
        self.open_output_button.configure(text=self.text("open_output"))
        if hasattr(self, "restore_session_button"):
            self.restore_session_button.configure(
                text="🔄 استعادة آخر جلسة" if self.language_var.get() == "العربية" else "🔄 Restore Session"
            )
        self.run_button.configure(text=self.text("run"))
        self.compress_video_button.configure(text=self.text("compress_videos"))
        self.detect_volume_button.configure(text=self.text("detect_volume"))
        self.auto_peak_button.configure(text=self.text("volume_normalize_peak"))
        self.preset_btn_1.configure(text=self.text("volume_preset_light"))
        self.preset_btn_2.configure(text=self.text("volume_preset_double"))
        self.preset_btn_3.configure(text=self.text("volume_preset_high"))
        self.preset_btn_4.configure(text=self.text("volume_preset_extreme"))
        self.boost_button.configure(text=self.text("boost_save"))
        self.pause_button.configure(text="Pause")
        self.stop_button.configure(text="■")
        self.previous_button.configure(text="|◀")
        self.back_button.configure(text="-5s")
        self.forward_button.configure(text="+5s")
        self.next_button.configure(text="▶|")
        self.expand_video_button.configure(text="⛶" if not self.video_expanded else "▣")
        if hasattr(self, "snapshot_button"):
            self.snapshot_button.configure(text=self.text("snapshot_btn"))
        self._refresh_play_button()
        self.mark_start_button.configure(text=self.text("mark_start"))
        self.mark_end_button.configure(text=self.text("mark_end"))
        self.trim_button.configure(text=self.text("trim_selected"))
        if hasattr(self, "trim_extract_audio_check"):
            self.trim_extract_audio_check.configure(text=self.text("trim_extract_audio"))
        if "trim_aspect_label" in self.i18n_widgets:
            self.i18n_widgets["trim_aspect_label"].configure(text=self.text("trim_aspect_ratio"))
        if hasattr(self, "trim_burn_subs_check"):
            self.trim_burn_subs_check.configure(text=self.text("trim_burn_subtitles"))
        if hasattr(self, "trim_logo_check"):
            self.trim_logo_check.configure(text=self.text("trim_add_logo"))
        if hasattr(self, "trim_title_check"):
            self.trim_title_check.configure(text=self.text("trim_add_title"))
        if hasattr(self, "trim_color_check"):
            self.trim_color_check.configure(text=self.text("trim_color_grading"))
        if hasattr(self, "trim_remove_silence_check"):
            self.trim_remove_silence_check.configure(text=self.text("trim_remove_silence"))
        if hasattr(self, "btn_color_grading"):
            self.btn_color_grading.configure(text="🎨 استديو الألوان المتقدم" if is_ar else "🎨 Color Studio")
        if hasattr(self, "btn_exp_collapse"):
            collapsed = getattr(self, "_export_card_collapsed", False)
            self.btn_exp_collapse.configure(text=("▼ إظهار" if is_ar else "▼ Options") if collapsed else ("▲ إخفاء" if is_ar else "▲ Hide"))
        if hasattr(self, "btn_branding"):
            self.btn_branding.configure(text=self.text("branding_btn"))
        if hasattr(self, "btn_silence_studio"):
            self.btn_silence_studio.configure(text=self.text("tab_silence"))
        if hasattr(self, "silence_auto_db_button"):
            self.silence_auto_db_button.configure(text=self.text("silence_auto_threshold"))
        if hasattr(self, "silence_analyze_button"):
            self.silence_analyze_button.configure(text=self.text("silence_analyze_btn"))
        if hasattr(self, "silence_export_button"):
            self.silence_export_button.configure(text=self.text("silence_export_btn"))
        if hasattr(self, "silence_save_srt_button"):
            self.silence_save_srt_button.configure(text=self.text("silence_save_synced_srt"))
        if hasattr(self, "silence_sync_subs_check"):
            self.silence_sync_subs_check.configure(text=self.text("silence_sync_subs_chk"))
        if hasattr(self, "silence_sel_all_btn"):
            self.silence_sel_all_btn.configure(text=self.text("silence_select_all"))
        if hasattr(self, "silence_desel_all_btn"):
            self.silence_desel_all_btn.configure(text=self.text("silence_deselect_all"))

        is_ar = self.language_var.get() == "العربية"
        if hasattr(self, "trim_aspect_combo"):
            aspect_display_vals = [
                (k, info["label_ar"] if is_ar else info["label_en"])
                for k, info in ASPECT_RATIOS.items()
            ]
            self.trim_aspect_map = {disp: k for k, disp in aspect_display_vals}
            self.trim_aspect_rev = {k: disp for k, disp in aspect_display_vals}
            self.trim_aspect_combo.configure(values=[d[1] for d in aspect_display_vals])
            cur_r = self.video_branding_config.get("aspect_ratio", "original")
            self.trim_aspect_combo_var.set(self.trim_aspect_rev.get(cur_r, aspect_display_vals[0][1]))

        if hasattr(self, "fit_mode_combo"):
            fit_vals = [(k, info["label_ar"] if is_ar else info["label_en"]) for k, info in FIT_MODES.items()]
            self.fit_mode_map = {disp: k for k, disp in fit_vals}
            self.fit_mode_rev = {k: disp for k, disp in fit_vals}
            self.fit_mode_combo.configure(values=[d[1] for d in fit_vals])
            cur_f = self.video_branding_config.get("fit_mode", "fit")
            self.fit_mode_combo_var.set(self.fit_mode_rev.get(cur_f, fit_vals[0][1]))

        if hasattr(self, "btn_export_mode"):
            if getattr(self, "active_inspector_context", None) == "export":
                self.btn_export_mode.configure(text="⬅ عودة للإعدادات" if is_ar else "⬅ Back to Settings")
            else:
                self.btn_export_mode.configure(text="🚀 تصدير الفيديو" if is_ar else "🚀 Export Video")

        if hasattr(self, "btn_shortcuts_guide"):
            self.btn_shortcuts_guide.configure(text="💡 الاختصارات" if is_ar else "💡 Keys")
        if hasattr(self, "btn_save_proj"):
            self.btn_save_proj.configure(text="💾 حفظ" if is_ar else "💾 Save")
        if hasattr(self, "btn_open_proj"):
            self.btn_open_proj.configure(text="📂 فتح" if is_ar else "📂 Open")
        if hasattr(self, "btn_recent_proj"):
            self.btn_recent_proj.configure(text="🕒 الأخيرة" if is_ar else "🕒 Recent")
        if hasattr(self, "_check_and_enforce_license"):
            self._check_and_enforce_license()

        if hasattr(self, "exp_scope_group"):
            self.exp_scope_group.configure(text="🎯 نوع ونطاق التصدير المطلـوب:" if is_ar else "🎯 Export Scope & Target:")
        if hasattr(self, "rdo_scope_all"):
            self.rdo_scope_all.configure(text="🎬 كامل المشروع (فيديو مدمج)" if is_ar else "🎬 Full Sequence (Single Video)")
            self.rdo_scope_sel.configure(text="🎞️ المقطع المحدد فقط" if is_ar else "🎞️ Selected Clip Only")
            self.rdo_scope_sep.configure(text="📂 كل مقطع في ملف منفصل" if is_ar else "📂 Each Clip Separately")
        if hasattr(self, "btn_cancel_progress"):
            self.btn_cancel_progress.configure(text="🛑 إلغاء" if is_ar else "🛑 Cancel")

        if hasattr(self, "btn_ctx_video"):
            self.btn_ctx_video.configure(text="🎬 فيديو" if is_ar else "🎬 Video")
            self.btn_ctx_color.configure(text="🎨 ألوان" if is_ar else "🎨 Color")
            if hasattr(self, "btn_ctx_transition"):
                self.btn_ctx_transition.configure(text="✨ انتقال" if is_ar else "✨ Trans")
            self.btn_ctx_silence.configure(text="✂️ صمت" if is_ar else "✂️ Silence")
            self.btn_ctx_audio.configure(text="🔊 صوت" if is_ar else "🔊 Audio")
            self.btn_ctx_subs.configure(text="🎙️ تفريغ" if is_ar else "🎙️ Subs/AI")
        if hasattr(self, "ctx_frame_transition"):
            self.ctx_frame_transition.configure(text="✨ حركات وانتقالات الفيديو السينمائية" if is_ar else "✨ Video Transitions Studio")
            if hasattr(self, "trim_trans_check"):
                self.trim_trans_check.configure(text="تفعيل الانتقالات بين المقاطع" if is_ar else "Enable Video Transitions")
            if hasattr(self, "btn_trans_library"):
                self.btn_trans_library.configure(text="✨ مكتبة الانتقالات (46+ حركة)" if is_ar else "✨ Transitions Library")
        if hasattr(self, "lbl_fit_style"):
            self.lbl_fit_style.configure(text="طريقة الملاءمة:" if is_ar else "Fit Mode:")
        if hasattr(self, "xf_group"):
            self.xf_group.configure(text="📐 خصائص وتحويل الفيديو" if is_ar else "📐 Video Transform")
        if hasattr(self, "chk_clip_override"):
            self.chk_clip_override.configure(text="🎞️ تخصيص لهذا المقطع فقط" if is_ar else "🎞️ Apply to Selected Clip Only")
        if hasattr(self, "lbl_zoom_title"):
            self.lbl_zoom_title.configure(text="التكبير (Zoom):" if is_ar else "Scale (Zoom):")
        if hasattr(self, "lbl_panx_title"):
            self.lbl_panx_title.configure(text="الموضع الأفقي (X):" if is_ar else "Position X:")
        if hasattr(self, "lbl_pany_title"):
            self.lbl_pany_title.configure(text="الموضع الرأسي (Y):" if is_ar else "Position Y:")
        if hasattr(self, "chk_vid_flip"):
            self.chk_vid_flip.configure(text="⇄ عكس أفقي" if is_ar else "⇄ Flip H")
        if hasattr(self, "chk_vid_clamp"):
            self.chk_vid_clamp.configure(text="🧲 منع الحواف السوداء" if is_ar else "🧲 Clamp Edges")
        if hasattr(self, "clip_fx_group"):
            self.clip_fx_group.configure(text="🎞️ المقطع المحدد: المكان، القص، السرعة، والصوت" if is_ar else "🎞️ Selected Clip: Position, In/Out, Speed & Vol")
        if hasattr(self, "lbl_clip_tl_pos"):
            self.lbl_clip_tl_pos.configure(text="موقعs:" if is_ar else "Pos s:")
            self.lbl_clip_in.configure(text="منs:" if is_ar else "In s:")
            self.lbl_clip_out.configure(text="إلىs:" if is_ar else "Out s:")
        if hasattr(self, "lbl_clip_speed"):
            self.lbl_clip_speed.configure(text="سرعةx:" if is_ar else "Spd x:")
        if hasattr(self, "lbl_clip_vol"):
            self.lbl_clip_vol.configure(text="صوت%:" if is_ar else "Vol%:")
        if hasattr(self, "ctx_frame_color"):
            self.ctx_frame_color.configure(text="🎨 تصحيح وتدرج الألوان المباشر" if is_ar else "🎨 Live Color Grading")
            if hasattr(self, "btn_studio_auto_color"):
                self.btn_studio_auto_color.configure(text="🤖 تصحيح ذكي" if is_ar else "🤖 Auto Color")
            if hasattr(self, "studio_color_mode_combo"):
                m_items = [(k, info["label_ar"] if is_ar else info["label_en"]) for k, info in AUTO_COLOR_MODES.items()]
                self._studio_color_mode_map = {d: k for k, d in m_items}
                self._studio_color_mode_rev = {k: d for k, d in m_items}
                cur_m = getattr(self, "_studio_color_mode_var", tk.StringVar()).get()
                cur_m_key = self._studio_color_mode_map.get(cur_m, "balanced")
                self.studio_color_mode_combo.configure(values=[d for _, d in m_items])
                self._studio_color_mode_var.set(self._studio_color_mode_rev.get(cur_m_key, m_items[0][1]))
            self.lbl_color_preset.configure(text="فلتر جاهز:" if is_ar else "Preset:")
            c_preset_items = [(k, info["label_ar"] if is_ar else info["label_en"]) for k, info in COLOR_PRESETS.items()]
            self._studio_color_preset_map = {d: k for k, d in c_preset_items}
            self.studio_color_preset_combo.configure(values=[d for _, d in c_preset_items])
            self._studio_color_preset_var.set(c_preset_items[0][1])
            self.lbl_col_br.configure(text="إضاءة %:" if is_ar else "Bright %:")
            self.lbl_col_ct.configure(text="تباين %:" if is_ar else "Contrast %:")
            self.lbl_col_st.configure(text="تشبع %:" if is_ar else "Saturate %:")
            self.lbl_col_tp.configure(text="دفء/برودة:" if is_ar else "Warmth %:")
            self.btn_col_reset.configure(text="↺ تصفير" if is_ar else "↺ Reset")
        if hasattr(self, "ctx_frame_silence"):
            self.ctx_frame_silence.configure(text="✂️ معالجة وحذف السكتات" if is_ar else "✂️ Silence Processing")
            self.lbl_sil_db.configure(text="حد الصمت (dB):" if is_ar else "Threshold (dB):")
            self.lbl_sil_min.configure(text="أقل سكتة(ث):" if is_ar else "Min Sil(s):")
            self.lbl_sil_pad.configure(text="هامش كلام(ث):" if is_ar else "Pad(s):")
            self.btn_live_cut_silences.configure(text="⚡ حذف السكتات تلقائياً من التايم لاين" if is_ar else "⚡ Auto-Cut Silences on Timeline")
            self.btn_live_mark_silences.configure(text="🔇 كتم السكتات للمراجعة اليدوية" if is_ar else "🔇 Mute Silences for Review")
            self.btn_sil_auto_db_inline.configure(text="✨ كشف تلقائي لمستوى السكتات (Auto dB)" if is_ar else "✨ Auto Detect Threshold (dB)")
        if hasattr(self, "ctx_frame_audio"):
            self.ctx_frame_audio.configure(text="🔊 إعدادات وتحسين الصوت" if is_ar else "🔊 Audio Settings & Enhancements")
            self.chk_studio_audio_fx.configure(text="تطبيق تحسينات الصوت" if is_ar else "Apply Audio Enhancements")
            self.lbl_studio_enhance.configure(text=self.text("enhance"))
            self.lbl_studio_gain.configure(text="تكبير الصوت dB:" if is_ar else "Gain Boost dB:")
            self.chk_studio_anticlip.configure(text=self.text("volume_anti_clipping"))
        if hasattr(self, "chk_studio_save_transcript"):
            self.chk_studio_save_transcript.configure(
                text="🎙️ تفريغ صوتي وحفظ ملف نصي وترجمة (.txt + .srt)" if is_ar else "🎙️ AI Transcribe & Save (.txt + .srt)"
            )
            self.btn_studio_transcribe.configure(text="🎙️ تفريغ بالذكاء الاصطناعي الآن" if is_ar else "🎙️ Transcribe Audio Now")
        if hasattr(self, "lbl_exp_pick"):
            self.lbl_exp_pick.configure(text="☑️ اختر التعديلات المطلوب تصديرها:" if is_ar else "☑️ Select Edits to Export:")
            self.btn_exp_all.configure(text="الكل" if is_ar else "All")
            self.btn_exp_none.configure(text="يدوي" if is_ar else "None")
            self.chk_exp_framing.configure(text="كادر/أبعاد" if is_ar else "Framing")
            self.chk_exp_timeline.configure(text="قص التايم لاين" if is_ar else "Timeline")
            self.chk_exp_overlays.configure(text="عناصر ولوجو" if is_ar else "Overlays")
            self.chk_exp_color.configure(text="ألوان" if is_ar else "Colors")
            self.chk_exp_silence.configure(text="قص السكتات" if is_ar else "Silence Cut")
            self.chk_exp_audio.configure(text="تحسين الصوت" if is_ar else "Audio FX")
            self.chk_exp_subs.configure(text="دمج ترجمة" if is_ar else "Burn Subs")
            self.chk_exp_transcript.configure(text="تفريغ نصي" if is_ar else "Transcript")
            self.lbl_exp_fmt.configure(text="الصيغة:" if is_ar else "Format:")
            self.lbl_exp_size.configure(text="الحجم:" if is_ar else "Size:")
            self._refresh_modular_export_combos()
        if hasattr(self, "btn_q_reels"):
            self.btn_q_reels.configure(text="📱 9:16 ريلز" if is_ar else "📱 9:16 Reels")
        if hasattr(self, "btn_q_orig"):
            self.btn_q_orig.configure(text="الأصلي" if is_ar else "Original")
        if hasattr(self, "btn_safe_grid"):
            self.btn_safe_grid.configure(text="⊞ شبكة" if is_ar else "⊞ Grid")
        if hasattr(self, "btn_reset_cam"):
            self.btn_reset_cam.configure(text="↺ توسيط الفيديو" if is_ar else "↺ Reset Pan/Zoom")
        if hasattr(self, "btn_pal_txt"):
            self.btn_pal_txt.configure(text="📝 نص" if is_ar else "📝 Text")
        if hasattr(self, "btn_pal_ico"):
            self.btn_pal_ico.configure(text="⭐ + أيقونة" if is_ar else "⭐ + Icon")
        if hasattr(self, "btn_pal_img"):
            self.btn_pal_img.configure(text="🖼️ + صورة" if is_ar else "🖼️ + Image")
        if hasattr(self, "btn_pal_lgo"):
            self.btn_pal_lgo.configure(text="🛡️ + لوجو" if is_ar else "🛡️ + Logo")
        if hasattr(self, "btn_pal_aud"):
            self.btn_pal_aud.configure(text="🎵 + صوت" if is_ar else "🎵 + Audio")
        if hasattr(self, "btn_add_ext_audio"):
            self.btn_add_ext_audio.configure(text="➕ إضافة ملف صوت / موسيقى (مسار A2)" if is_ar else "➕ Add Audio / Music (A2)")
        if hasattr(self, "_refresh_audio_inspector_status"):
            self._refresh_audio_inspector_status()
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.apply_language()

        if hasattr(self, "btn_master_export"):
            self.btn_master_export.configure(text=self.text("master_export_btn"))
        if hasattr(self, "lbl_exp_fmt"):
            self.lbl_exp_fmt.configure(text="الصيغة:" if is_ar else "Format:")
        if hasattr(self, "lbl_exp_size"):
            self.lbl_exp_size.configure(text="الضغط/الجودة:" if is_ar else "Quality/Comp:")
        if hasattr(self, "_refresh_modular_export_combos"):
            self._refresh_modular_export_combos()
        if hasattr(self, "studio_toggle_btn"):
            if getattr(self, "studio_live_preview_mode", False):
                self.studio_toggle_btn.configure(text="📺 المعاينة المباشرة" if is_ar else "📺 Direct Preview")
            else:
                self.studio_toggle_btn.configure(text="🎨 استوديو المونتاج" if is_ar else "🎨 Studio Preview")
        if hasattr(self, "_refresh_master_export_summary"):
            self._refresh_master_export_summary()
        if hasattr(self, "btn_toggle_log"):
            arrow = "▲" if getattr(self, "log_visible", False) else "▼"
            self.btn_toggle_log.configure(text=f"{self.text('view_log_btn')} {arrow}")
        self.caption_start_button.configure(text=self.text("caption_start"))
        self.caption_stop_button.configure(text=self.text("caption_stop"))
        if hasattr(self, "caption_import_capcut_button"):
            self.caption_import_capcut_button.configure(text=self.text("caption_import_capcut"))
        if hasattr(self, "caption_open_models_button"):
            self.caption_open_models_button.configure(text=self.text("caption_open_models_dir"))
        if hasattr(self, "caption_download_model_button"):
            m_stat = convert.get_whisper_model_status(self._get_current_caption_model_id())
            btn_txt = self.text("caption_model_ready_btn") if m_stat["is_downloaded"] else self.text("caption_download_model_btn")
            self.caption_download_model_button.configure(text=btn_txt)
        self.caption_copy_button.configure(text=self.text("caption_copy"))
        self.caption_save_button.configure(text=self.text("caption_save_as"))
        self.caption_burn_button.configure(text=self.text("caption_burn_now"))
        if hasattr(self, "caption_burn_cancel_button"):
            self.caption_burn_cancel_button.configure(text=self.text("caption_stop"))
        self.caption_open_folder_button.configure(text=self.text("caption_open_folder"))
        self.caption_rb_text.configure(text=self.text("caption_tab_text"))
        self.caption_rb_srt.configure(text=self.text("caption_tab_srt"))
        self.choose_cover_button.configure(text=self.text("choose_image"))
        self.fetch_youtube_button.configure(text=self.text("fetch_qualities"))
        self.download_youtube_button.configure(text=self.text("download_youtube"))
        self.choose_youtube_output_button.configure(text=self.text("choose_download_folder"))

        # Checkbuttons
        self.keep_original_check.configure(text=self.text("keep_original"))
        self.skip_existing_check.configure(text=self.text("skip_existing"))
        self.preview_check.configure(text=self.text("preview_cover"))
        self.open_output_check.configure(text=self.text("open_output_done"))
        self.boost_anti_clip_check.configure(text=self.text("volume_anti_clipping"))
        self.caption_export_srt_check.configure(text=self.text("caption_export_srt"))
        self.caption_export_vtt_check.configure(text=self.text("caption_export_vtt"))
        self.caption_export_txt_check.configure(text=self.text("caption_export_txt"))
        self.caption_burn_check.configure(text=self.text("caption_burn_video"))
        self.custom_cover_check.configure(text=self.text("use_custom_cover"))

        if "settings_button" in self.i18n_widgets:
            self.i18n_widgets["settings_button"].configure(text=self.text("settings_btn"))
        if "about_button" in self.i18n_widgets:
            self.i18n_widgets["about_button"].configure(text=self.text("about"))
        if "theme_button" in self.i18n_widgets:
            self._update_theme_button_text()
        if "dev_label" in self.i18n_widgets:
            self.i18n_widgets["dev_label"].configure(text=self.text("developer_credit"))

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
        self._refresh_video_format_options()
        self._refresh_video_compression_options()
        self._refresh_video_resolution_options()
        self._refresh_video_estimate()
        self._refresh_youtube_details()
        if hasattr(self, "_refresh_silence_options"):
            self._refresh_silence_options()
        if hasattr(self, "_refresh_silence_ui"):
            self._refresh_silence_ui()
        if hasattr(self, "_update_inspector_properties"):
            self._update_inspector_properties()
        if hasattr(self, "_sync_live_video_overlay"):
            self._sync_live_video_overlay()
        self._refresh_boost_format_options()
        self._refresh_caption_options()
        self._boost_gain_changed()

    def show_about_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title(self.text("about_title"))
        self._apply_theme_to_toplevel(dialog)
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill="both", expand=True)

        ver_fg = "#8b949e" if (getattr(self, "theme_var", None) and self.theme_var.get() == "dark") else "#666666"
        ttk.Label(frame, text="ClipCraft Studio Pro", font=("Segoe UI", 15, "bold")).pack(pady=(0, 2))
        ttk.Label(frame, text="Version 1.0.0", font=("Segoe UI", 9), foreground=ver_fg).pack(pady=(0, 4))

        # License Badge in About Dialog
        status = check_license_status()
        state = status.get("state", "trial")
        is_ar = (getattr(self, "language_var", None) and self.language_var.get() == "العربية")
        if state == "licensed":
            p_disp = format_plan_name(status.get("plan", "PRO"), is_ar=is_ar)
            lic_badge = f"👑 مرخص ومفعل رسمياً ({p_disp})" if is_ar else f"👑 Officially Licensed ({p_disp})"
            lic_fg = "#3fb950"
        elif state == "trial":
            rem_d = status.get("remaining_days", 3)
            lic_badge = f"⏳ نسخة تجريبية ({rem_d} أيام متبقية)" if is_ar else f"⏳ Trial Edition ({rem_d} days left)"
            lic_fg = "#d29922"
        else:
            lic_badge = "🔒 الترخيص منتهي" if is_ar else "🔒 License Expired"
            lic_fg = "#f85149"
        ttk.Label(frame, text=lic_badge, font=("Segoe UI", 9, "bold"), foreground=lic_fg).pack(pady=(0, 8))

        # Check for Updates Button right inside About dialog
        btn_update = ttk.Button(
            frame,
            text="🔄 " + ("التحقق من وجود تحديثات" if is_ar else "Check for Updates"),
            command=self.check_for_updates_interactive,
            style="Player.TButton",
        )
        btn_update.pack(pady=(0, 10))

        ttk.Label(frame, text=self.text("about_desc"), font=("Segoe UI", 9), wraplength=380, justify="center").pack(pady=(0, 14))

        dev_group = ttk.LabelFrame(frame, text=self.text("about_developer_header"), padding=12)
        dev_group.pack(fill="x", pady=(0, 14))

        ttk.Label(dev_group, text=self.text("about_developer_name"), font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 4))
        ttk.Label(dev_group, text=self.text("about_developer_email"), font=("Segoe UI", 10)).pack(anchor="w")

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(6, 0))

        def copy_email():
            self.clipboard_clear()
            self.clipboard_append("Elshazly.gsm@gmail.com")
            copy_btn.configure(text=self.text("copied"))

        copy_btn = ttk.Button(btn_frame, text=self.text("copy_email"), command=copy_email)
        copy_btn.pack(side="left", padx=(0, 8))

        close_btn = ttk.Button(btn_frame, text=self.text("close"), command=dialog.destroy)
        close_btn.pack(side="right")

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")

    def show_settings_dialog(self):
        is_ar = (getattr(self, "language_var", None) and self.language_var.get() == "العربية")
        dialog = tk.Toplevel(self)
        dialog.title("ClipCraft Studio — " + ("إعدادات البرنامج والتفضيلات" if is_ar else "Settings & Preferences"))
        self._apply_theme_to_toplevel(dialog)
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("540x510")
        dialog.minsize(500, 450)
        dialog.resizable(False, False)

        dialog.update_idletasks()
        w, h = 540, 510
        x = max(10, self.winfo_x() + (self.winfo_width() - w) // 2)
        y = max(10, self.winfo_y() + (self.winfo_height() - h) // 2)
        dialog.geometry(f"{w}x{h}+{x}+{y}")

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)

        # 1. Header
        ttk.Label(frame, text="⚙️ " + ("إعدادات البرنامج والتفضيلات العامة" if is_ar else "Settings & Preferences"), font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 12))

        # 2. Updates & Maintenance Section
        upd_group = ttk.LabelFrame(frame, text="🚀 " + ("التحديثات والصيانة" if is_ar else "Updates & Maintenance"), padding=12)
        upd_group.pack(fill="x", pady=(0, 12))

        auto_upd_var = tk.BooleanVar(value=bool(self.settings.get("check_updates_on_startup", True)))
        chk_upd = ttk.Checkbutton(
            upd_group,
            text="التحقق التلقائي من وجود تحديثات عند بدء التشغيل" if is_ar else "Check for updates automatically on startup",
            variable=auto_upd_var,
        )
        chk_upd.pack(anchor="w", pady=(0, 6))

        last_check_ts = self.settings.get("last_update_check")
        if last_check_ts:
            import datetime
            dt_str = datetime.datetime.fromtimestamp(last_check_ts).strftime("%Y-%m-%d %H:%M")
            last_check_txt = f"آخر تحقق: {dt_str}" if is_ar else f"Last checked: {dt_str}"
        else:
            last_check_txt = "آخر تحقق: لم يتم بعد" if is_ar else "Last checked: Not yet"

        ttk.Label(upd_group, text=last_check_txt, font=("Segoe UI", 8), foreground="#8b949e").pack(anchor="w", pady=(0, 8))

        btn_chk_now = ttk.Button(
            upd_group,
            text="🔄 " + ("التحقق من وجود تحديثات الآن" if is_ar else "Check for Updates Now"),
            command=self.check_for_updates_interactive,
            style="Player.TButton",
        )
        btn_chk_now.pack(anchor="w")

        # 3. License & Activation Section
        lic_group = ttk.LabelFrame(frame, text="👑 " + ("الترخيص والتفعيل" if is_ar else "License & Activation"), padding=12)
        lic_group.pack(fill="x", pady=(0, 12))

        status = check_license_status()
        state = status.get("state", "trial")
        if state == "licensed":
            plan_raw = status.get("plan", "PRO")
            display_plan = format_plan_name(plan_raw, is_ar=is_ar)
            days = status.get("remaining_days", 9999)
            dur_str = "دائم مدى الحياة" if days >= 9999 else f"متبقي {days} يوم"
            lic_summary = f"✅ مفعل رسمياً: {display_plan} ({dur_str})" if is_ar else f"✅ Officially Licensed: {display_plan} ({dur_str})"
            lic_color = "#3fb950"
        elif state == "trial":
            rem_d = status.get("remaining_days", 3)
            lic_summary = f"⏳ نسخة تجريبية: متبقي {rem_d} أيام" if is_ar else f"⏳ Trial Version: {rem_d} days remaining"
            lic_color = "#d29922"
        else:
            lic_summary = "🔒 الترخيص منتهي — يلزم التفعيل" if is_ar else "🔒 License Expired — Activation Required"
            lic_color = "#f85149"

        ttk.Label(lic_group, text=lic_summary, font=("Segoe UI", 9, "bold"), foreground=lic_color).pack(anchor="w", pady=(0, 8))

        def _open_lic_and_close():
            dialog.destroy()
            self._show_license_dialog()

        btn_manage_lic = ttk.Button(
            lic_group,
            text="👑 " + ("إدارة الترخيص والمفتاح" if is_ar else "Manage License & Key"),
            command=_open_lic_and_close,
            style="Player.TButton",
        )
        btn_manage_lic.pack(anchor="w")

        # 4. Default Output Directory Section
        dir_group = ttk.LabelFrame(frame, text="📁 " + ("مجلد الإخراج الافتراضي" if is_ar else "Default Output Directory"), padding=12)
        dir_group.pack(fill="x", pady=(0, 12))

        dir_box = ttk.Frame(dir_group)
        dir_box.pack(fill="x")

        dir_entry_var = tk.StringVar(value=str(self.output_dir or DEFAULT_OUTPUT_DIR))
        ent_dir = ttk.Entry(dir_box, textvariable=dir_entry_var, state="readonly")
        ent_dir.pack(side="left", fill="x", expand=True, padx=(0, 6))

        def _browse_dir():
            chosen = filedialog.askdirectory(parent=dialog, title="Select Default Output Folder", initialdir=dir_entry_var.get())
            if chosen:
                dir_entry_var.set(chosen)

        btn_browse = ttk.Button(dir_box, text="استعراض..." if is_ar else "Browse...", command=_browse_dir)
        btn_browse.pack(side="right")

        # 5. Dialog Bottom Buttons
        btn_box = ttk.Frame(frame)
        btn_box.pack(fill="x", side="bottom", pady=(8, 0))

        def _save_and_close():
            self.settings["check_updates_on_startup"] = bool(auto_upd_var.get())
            new_out = Path(dir_entry_var.get().strip())
            if new_out.exists() and new_out.is_dir():
                self.output_dir = new_out
                self.output_var.set(str(new_out))
            self._save_settings()
            dialog.destroy()

        btn_save = ttk.Button(btn_box, text="💾 " + ("حفظ الإعدادات" if is_ar else "Save Settings"), command=_save_and_close, style="Action.TButton")
        btn_save.pack(side="left")

        btn_cancel = ttk.Button(btn_box, text="إلغاء" if is_ar else "Cancel", command=dialog.destroy, style="Player.TButton")
        btn_cancel.pack(side="right")

    # -------------------------------------------------------------------------
    # Update Checker Engine
    # -------------------------------------------------------------------------

    def _startup_update_check(self):
        try:
            if not self.settings.get("check_updates_on_startup", True):
                return
            threading.Thread(target=self._run_background_update_check, daemon=True).start()
        except Exception:
            pass

    def _run_background_update_check(self):
        try:
            from video_studio.update_manager import check_for_updates
            res = check_for_updates(timeout=4)
            self.settings["last_update_check"] = time.time()
            self._save_settings()
            if res.get("has_update"):
                lat_v = res.get("latest_version")
                last_notified = self.settings.get("last_update_version_notified", "")
                if lat_v != last_notified:
                    self.settings["last_update_version_notified"] = lat_v
                    self._save_settings()
                    is_ar = (getattr(self, "language_var", None) and self.language_var.get() == "العربية")
                    self.after(0, lambda: self._show_update_dialog_popup(res, is_manual=False, is_ar=is_ar))
        except Exception:
            pass

    def check_for_updates_interactive(self):
        is_ar = (getattr(self, "language_var", None) and self.language_var.get() == "العربية")
        self._append_log("🔄 " + ("جاري التحقق من التحديثات عبر الإنترنت...\n" if is_ar else "Checking for updates online...\n"))

        def _worker():
            try:
                from video_studio.update_manager import check_for_updates
                res = check_for_updates(timeout=6)
                self.settings["last_update_check"] = time.time()
                self._save_settings()
                self.after(0, lambda: self._show_update_dialog_popup(res, is_manual=True, is_ar=is_ar))
            except Exception as e:
                err_text = f"تعذر التحقق من التحديثات: {e}" if is_ar else f"Could not check for updates: {e}"
                self.after(0, lambda: messagebox.showwarning("ClipCraft Studio", err_text))

        threading.Thread(target=_worker, daemon=True).start()

    def _show_update_dialog_popup(self, res, is_manual=True, is_ar=True):
        try:
            from video_studio.update_manager import UpdateDialog
            UpdateDialog(self, result=res, is_manual=is_manual, is_ar=is_ar)
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Licensing & Activation Enforcement
    # -------------------------------------------------------------------------

    def _check_and_enforce_license(self):
        try:
            status = check_license_status()
            state = status.get("state", "trial")
            is_ar = (getattr(self, "language_var", None) and self.language_var.get() == "العربية")

            if state == "licensed":
                plan = status.get("plan", "PRO")
                days = status.get("remaining_days", 9999)
                if days < 9999:
                    if is_ar:
                        p_upper = str(plan).upper()
                        if "شهر" in plan or "MONTH" in p_upper:
                            short_p = "اشتراك شهر"
                        elif "6" in plan:
                            short_p = "اشتراك 6 أشهر"
                        elif "سنة" in plan or "YEAR" in p_upper:
                            short_p = "اشتراك سنوي"
                        else:
                            short_p = "مفعل"
                        txt = f"👑 {short_p} ({days} يوم)"
                    else:
                        p_clean = "1 Month" if "MONTH" in str(plan).upper() else str(plan)
                        txt = f"👑 {p_clean} ({days}d)"
                else:
                    txt = "👑 مفعل مدى الحياة" if is_ar else "👑 Lifetime Pro"
                if hasattr(self, "btn_license_trial"):
                    self.btn_license_trial.configure(text=txt)
                title_tag = " [نسخة مفعلة 👑]" if is_ar else " [Licensed 👑]"
                self.title(f"ClipCraft Studio Pro{title_tag}")
            elif state == "trial":
                days = status.get("remaining_days", 3)
                txt = f"⏳ تجريبي ({days} يوم)" if is_ar else f"⏳ Trial ({days}d)"
                if hasattr(self, "btn_license_trial"):
                    self.btn_license_trial.configure(text=txt)
                self.title("ClipCraft Studio Pro [فترة تجريبية ⏳]" if is_ar else "ClipCraft Studio Pro [Trial ⏳]")
            else:
                if hasattr(self, "btn_license_trial"):
                    self.btn_license_trial.configure(text="🔒 انتهت التجربة" if is_ar else "🔒 Expired")
                self.title("ClipCraft Studio Pro [انتهت التجربة 🔒]" if is_ar else "ClipCraft Studio Pro [Expired 🔒]")
                self._show_license_dialog(is_expired=True)
        except Exception:
            pass

    def _show_license_dialog(self, is_expired: bool = False):
        try:
            # Singleton Guard: If an activation dialog is already open, bring it to front
            dlg = getattr(self, "_license_dialog_instance", None)
            if dlg is not None:
                try:
                    if dlg.winfo_exists():
                        if dlg.wm_state() == "iconic":
                            dlg.deiconify()
                        dlg.lift()
                        dlg.focus_force()
                        return
                except Exception:
                    self._license_dialog_instance = None

            status = check_license_status()
            if not is_expired and status.get("state") in ("expired", "tampered"):
                is_expired = True
            is_ar = (getattr(self, "language_var", None) and self.language_var.get() == "العربية")
            self._license_dialog_instance = ActivationDialog(
                self, is_expired=is_expired, on_success=self._on_license_activated, is_ar=is_ar
            )
        except Exception as e:
            is_ar = (getattr(self, "language_var", None) and self.language_var.get() == "العربية")
            err_msg = f"تعذر فتح نافذة التفعيل: {e}" if is_ar else f"Failed to open activation dialog: {e}"
            messagebox.showerror("ClipCraft Studio", err_msg)

    def _on_license_activated(self):
        self._check_and_enforce_license()

    def _refresh_enhancement_options(self):
        labels = ENHANCEMENT_LABELS[self.language_var.get()]
        vals = [labels[key] for key in convert.ENHANCEMENT_PRESETS]
        self.enhancement_combo.configure(values=vals)
        if hasattr(self, "boost_enhancement_combo"):
            self.boost_enhancement_combo.configure(values=vals)
        if hasattr(self, "studio_enhance_combo"):
            self.studio_enhance_combo.configure(values=vals)
        self.enhancement_var.set(labels[self.enhancement_key])

    def _refresh_video_format_options(self):
        labels = VIDEO_FORMAT_LABELS[self.language_var.get()]
        self.video_format_combo.configure(values=[labels[key] for key in VIDEO_FORMAT_LABELS[self.language_var.get()]])
        self.video_format_var.set(labels.get(self.video_format_key, labels[".mp4"]))

    def _refresh_video_compression_options(self):
        labels = VIDEO_COMPRESSION_LABELS[self.language_var.get()]
        self.video_compression_combo.configure(values=[labels.get(key, key) for key in convert.VIDEO_COMPRESSION_PRESETS])
        self.video_compression_var.set(labels.get(self.video_compression_key, self.video_compression_key))

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

    def _attach_text_context_menu(self, widget):
        def show_menu(event):
            menu = tk.Menu(widget, tearoff=False)
            menu.add_command(label=self.text("cut"), command=lambda: widget.event_generate("<<Cut>>"))
            menu.add_command(label=self.text("copy"), command=lambda: widget.event_generate("<<Copy>>"))
            menu.add_command(label=self.text("paste"), command=lambda: widget.event_generate("<<Paste>>"))
            menu.add_separator()
            menu.add_command(label=self.text("select_all"), command=lambda: widget.tag_add("sel", "1.0", "end"))
            menu.tk_popup(event.x_root, event.y_root)

        widget.bind("<Button-3>", show_menu)
        widget.bind("<Control-a>", lambda _e: (widget.tag_add("sel", "1.0", "end"), "break")[-1])

    def _on_notebook_tab_changed(self, _event=None):
        if hasattr(self, "btn_export_mode"):
            try:
                self.btn_export_mode.lift()
            except Exception:
                pass
        if not hasattr(self, "notebook") or not hasattr(self, "tab_player"):
            return
        try:
            selected_tab = self.notebook.select()
            if selected_tab == str(self.tab_player):
                if getattr(self, "studio_live_preview_mode", True):
                    self._show_studio_canvas()
                    if getattr(self, "input_path", None) and self.input_path.is_file() and self.input_path.suffix.lower() in convert.VIDEO_EXTS:
                        tl_sec = self._current_timeline_seconds() if hasattr(self, "_current_timeline_seconds") else 0.0
                        _idx, _c, src_sec = self.nle_project.timeline_to_source(tl_sec) if hasattr(self, "nle_project") else (0, None, tl_sec)
                        self._request_fast_preview_frame(src_sec, force=(self._cached_player_frame is None))
                        self._render_player_studio_canvas()
        except Exception:
            pass

    def _language_changed(self, _event=None):
        self._apply_language()
        self._save_settings()

    def _speed_changed(self, _event=None):
        self.apply_playback_speed()
        self._save_settings()

    def _video_format_changed(self, _event=None):
        self._remember_video_format_key()
        self._save_settings()
        self._refresh_video_estimate()

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
            "Original": 10000,
            "Very High": 7500,
            "High": 4800,
            "Medium": 2800,
            "Small": 1600,
            "Very Small": 950,
        }.get(compression, 2800)
        res_factors = {
            "360p": 0.20,
            "480p": 0.35,
            "720p": 0.58,
            "1080p": 1.0,
            "Original": 1.0,
        }
        return int(base * res_factors.get(resolution, 1.0))

    def _estimate_video_output_size(self, video_files):
        if not video_files:
            return None
        compression = self.selected_video_compression()
        resolution = self.selected_video_resolution()

        total_source_size = 0
        valid_files = []
        for path in video_files:
            try:
                if path.is_file():
                    total_source_size += path.stat().st_size
                    valid_files.append(path)
            except OSError:
                continue

        if not valid_files or total_source_size <= 0:
            return None

        if compression == "Original" and resolution == "Original":
            return total_source_size

        base_ratio = {
            "Original": 1.0,
            "Very High": 0.88,
            "High": 0.68,
            "Medium": 0.48,
            "Small": 0.28,
            "Very Small": 0.16,
        }.get(compression, 0.50)

        res_ratio = {
            "Original": 1.0,
            "1080p": 1.0,
            "720p": 0.72,
            "480p": 0.50,
            "360p": 0.35,
        }.get(resolution, 1.0)

        # For batches with many files (> 3), calculate instantly without spawning 50+ blocking ffprobe processes!
        if len(valid_files) > 3:
            combined_ratio = base_ratio * res_ratio
            if compression != "Original":
                combined_ratio = min(combined_ratio, base_ratio)
            est = int(total_source_size * combined_ratio)
            return max(est, 1024)

        # For single files or very small batches (<= 3 files), use detailed model if cached or lightweight fallback
        if not hasattr(self, "_video_info_cache"):
            self._video_info_cache = {}

        total_est = 0
        for path in valid_files:
            try:
                cache_key = (str(path), path.stat().st_mtime)
            except OSError:
                continue
            info = self._video_info_cache.get(cache_key)
            if not info:
                # Use immediate fast calculation rather than blocking the UI
                sz = path.stat().st_size
                total_est += int(sz * base_ratio * res_ratio)
                continue

            dur = info.get("duration", 0)
            if dur <= 0:
                total_est += int(info.get("size", 0) * base_ratio * res_ratio)
                continue

            w = info.get("w", 1920)
            h = info.get("h", 1080)
            source_size = info.get("size", 0)

            res_limits = {
                "360p": (640, 360),
                "480p": (854, 480),
                "720p": (1280, 720),
                "1080p": (1920, 1080),
            }
            tw, th = w, h
            if resolution in res_limits:
                mw, mh = res_limits[resolution]
                if w > mw or h > mh:
                    scale = min(mw / w, mh / h)
                    tw, th = int(w * scale), int(h * scale)

            target_pixels = max(tw * th, 640 * 360)
            pixel_scale = (target_pixels / 2_073_600) ** 0.72

            crf_1080p_kbps = {
                "Original": 10000,
                "Very High": 7500,
                "High": 4800,
                "Medium": 2800,
                "Small": 1600,
                "Very Small": 950,
            }.get(compression, 2800)
            crf_model_kbps = crf_1080p_kbps * pixel_scale

            source_kbps = (source_size * 8 / 1000) / dur if dur > 0 else 0
            ratio = base_ratio
            if w > 0 and h > 0 and (tw * th < w * h):
                ratio *= ((tw * th) / (w * h)) ** 0.72

            if source_kbps > 0:
                source_based_kbps = source_kbps * ratio
                target_video_kbps = min(
                    crf_model_kbps,
                    max(source_based_kbps, min(source_kbps * 0.95, crf_model_kbps * 0.7)),
                )
            else:
                target_video_kbps = crf_model_kbps

            audio_preset = convert.VIDEO_COMPRESSION_PRESETS.get(compression, {})
            raw_audio = str(audio_preset.get("audio_bitrate", "128k")).rstrip("k")
            try:
                audio_kbps = int(raw_audio)
            except ValueError:
                audio_kbps = 128

            file_est = int(((target_video_kbps + audio_kbps) * 1000 / 8) * dur * 1.025)
            if compression != "Original" and source_size > 0 and file_est > source_size:
                file_est = int(source_size * ratio)

            total_est += file_est

        return total_est if total_est > 0 else None

    def _refresh_video_estimate(self):
        video_files = self.video_files()
        if not video_files:
            self.video_estimate_var.set("")
            return

        is_ar = (getattr(self, "language_var", None) and self.language_var.get() == "العربية")
        try:
            estimate = self._estimate_video_output_size(video_files)
            if estimate:
                prefix = "الحجم التقريبي: ~" if is_ar else "Est. ~"
                self.video_estimate_var.set(f"{prefix}{convert.human_size(estimate)}")
            else:
                self.video_estimate_var.set("الحجم التقريبي غير معروف" if is_ar else "Est. unknown")
        except Exception:
            self.video_estimate_var.set("")

    def _remember_enhancement_key(self):
        selected_label = self.enhancement_var.get()
        labels = ENHANCEMENT_LABELS[self.language_var.get()]
        for key, label in labels.items():
            if label == selected_label:
                self.enhancement_key = key
                return

    def _remember_video_format_key(self):
        selected_label = self.video_format_var.get()
        labels = VIDEO_FORMAT_LABELS[self.language_var.get()]
        for key, label in labels.items():
            if label == selected_label:
                self.video_format_key = key
                return

    def _remember_video_compression_key(self):
        selected_label = self.video_compression_var.get()
        labels = VIDEO_COMPRESSION_LABELS[self.language_var.get()]
        for key in convert.VIDEO_COMPRESSION_PRESETS:
            label = labels.get(key, key)
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

    def selected_video_format(self):
        self._remember_video_format_key()
        return self.video_format_key

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
        if hasattr(self, "cover_thumb_label"):
            try:
                img = Image.open(self.custom_cover_path)
                img.thumbnail((42, 42))
                self._cover_thumb_photo = ImageTk.PhotoImage(img)
                self.cover_thumb_label.configure(image=self._cover_thumb_photo, text="")
            except Exception:
                pass
        self._update_run_state()

    def choose_youtube_output_folder(self):
        selected = filedialog.askdirectory(title=self.text("choose_download_folder"), initialdir=self._dialog_dir(self.youtube_output_dir()))
        if selected:
            self.youtube_output_dir_path = Path(selected)
            self._save_settings()
            self._refresh_youtube_details()

    def set_source(self, source_path):
        prev_source = self.input_path
        self.stop_playback()
        self.input_path = source_path
        if source_path and source_path.is_file():
            try:
                add_recent_media(source_path)
            except Exception:
                pass
        output_base = source_path.parent if source_path.is_file() else source_path
        self.output_dir = output_base / "output"
        self.media_files = convert.collect_media_files(self.input_path, self.output_dir)

        source_changed = (prev_source != source_path)
        if source_changed:
            self.silence_analysis_result = None
            if hasattr(self, "silence_summary_var"):
                self.silence_summary_var.set(self.text("silence_ready_hint"))
            if hasattr(self, "_refresh_silence_ui"):
                self._refresh_silence_ui()
            if hasattr(self, "fast_preview"):
                self.fast_preview.close()
            self._cached_player_frame = None
            self._cached_player_frame_ts = -1.0
            self._cached_player_frame_path = None
            self.media_width = 0
            self.media_height = 0
            self.nle_playhead_sec = 0.0
            self.active_playback_clip_idx = 0
            if hasattr(self, "nle_project"):
                self.nle_project.reset_for_media(source_path if source_path.is_file() else None, 60.0)
            if hasattr(self, "davinci_timeline"):
                self.davinci_timeline.waveform_peaks = None
                self.davinci_timeline.silence_intervals = None
                self.davinci_timeline.selected_ref = ("clip", 0)
                self.davinci_timeline.zoom_fit()
                self.davinci_timeline.set_playhead(0.0)
            self.player_canvas_selected = ("clip", 0)
            if hasattr(self, "_sync_transform_sliders_from_state"):
                self._sync_transform_sliders_from_state()
            if hasattr(self, "_update_inspector_properties"):
                self._update_inspector_properties()
            # Clean import: reset color grading so new media is never distorted by old sessions
            if hasattr(self, "video_branding_config") and isinstance(self.video_branding_config, dict):
                self.video_branding_config["color_config"] = {
                    "enabled": False,
                    "brightness": 0.0,
                    "contrast": 1.0,
                    "saturation": 1.0,
                    "gamma": 1.0,
                    "temperature": 0.0,
                    "red": 0.0,
                    "green": 0.0,
                    "blue": 0.0,
                    "preset": "original",
                }
            if hasattr(self, "trim_color_var"):
                self.trim_color_var.set(False)
            if hasattr(self, "_sync_studio_color_controls"):
                self._sync_studio_color_controls()
            if hasattr(self, "lbl_studio_color_diag"):
                self.lbl_studio_color_diag.configure(text="")
            # Clean import: reset transitions configuration so new media starts clean
            if hasattr(self, "video_branding_config") and isinstance(self.video_branding_config, dict):
                self.video_branding_config["transitions_config"] = dict(DEFAULT_TRANSITIONS_CONFIG)
            if hasattr(self, "trans_enable_var"):
                self.trans_enable_var.set(False)
            if hasattr(self, "refresh_video_transitions_panel"):
                self.refresh_video_transitions_panel()
            # Default export compression & quality to Match Source upon selecting a file
            self.export_size_key = "Match Source"
            if hasattr(self, "_exp_sz_rev") and hasattr(self, "export_size_combo_var"):
                match_label = self._exp_sz_rev.get("Match Source")
                if match_label:
                    self.export_size_combo_var.set(match_label)
            # Reset aspect ratio to native original for fresh import
            if hasattr(self, "video_branding_config") and isinstance(self.video_branding_config, dict):
                self.video_branding_config["aspect_ratio"] = "original"
                self.video_branding_config["fit_mode"] = "crop"
            if hasattr(self, "trim_aspect_var"):
                self.trim_aspect_var.set("original")
            if hasattr(self, "trim_aspect_combo_var") and hasattr(self, "trim_aspect_rev"):
                disp_orig = self.trim_aspect_rev.get("original")
                if disp_orig:
                    self.trim_aspect_combo_var.set(disp_orig)
            self.apply_video_aspect_ratio()
            if hasattr(self, "_refresh_master_export_summary"):
                self._refresh_master_export_summary()

        # Set UI values immediately for instant 0ms responsiveness
        self.source_var.set(str(self.input_path))
        if hasattr(self, "loaded_filename_var"):
            fn = self.input_path.name if (self.input_path and hasattr(self.input_path, "name")) else ""
            self.loaded_filename_var.set(f"🎬 {fn}" if fn else "")
        self.output_var.set(str(self.output_dir))
        self.count_var.set(self.text("media_count", count=len(self.media_files)))
        self.video_count_var.set(self.text("video_count", count=len(self.video_files())))
        self.progress_var.set(self.text("processed", current=0, total=len(self.media_files)))
        self.status_var.set(self.text("ready") if self.media_files else self.text("no_media"))
        self._update_run_state()

        if source_changed:
            self.media_duration = 0
            self.timeline_var.set(0)
            self.timeline_scale.configure(to=100)
            self._refresh_timeline_text()
        is_ar = self.language_var.get() == "العربية"
        self.video_estimate_var.set("جاري الفحص..." if is_ar else "Probing...")

        if source_path.is_file() and source_path.suffix.lower() in convert.VIDEO_EXTS:
            if hasattr(self, "notebook") and hasattr(self, "tab_player"):
                try:
                    self.notebook.select(self.tab_player)
                except Exception:
                    pass
            self.studio_live_preview_mode = True
            self._show_studio_canvas()
            if source_changed or self._cached_player_frame is None:
                self._request_fast_preview_frame(0.0, force=True)
            else:
                self._render_player_studio_canvas()
        else:
            self._cached_player_frame = None
            if hasattr(self, "player_studio_canvas"):
                self._render_player_studio_canvas()

        # Run ffprobe / estimate / waveform extraction asynchronously so UI never freezes
        threading.Thread(
            target=self._async_load_media_info,
            args=(source_path, source_changed),
            daemon=True,
        ).start()

    def _async_load_media_info(self, source_path, extract_waveform=True):
        dur_f = 0.0
        vid_w, vid_h = 0, 0
        if source_path.is_file() and source_path == self.input_path:
            try:
                dur_f = float(convert.get_media_duration(source_path) or 0.0)
            except Exception:
                dur_f = 0.0
            if source_path.suffix.lower() in convert.VIDEO_EXTS:
                try:
                    vid_w, vid_h = convert.get_video_dimensions(source_path)
                except Exception:
                    vid_w, vid_h = 0, 0

        video_files = [p for p in self.media_files if p.suffix.lower() in convert.VIDEO_EXTS] if source_path == self.input_path else []
        estimate = None
        if video_files:
            try:
                estimate = self._estimate_video_output_size(video_files)
            except Exception:
                estimate = None

        def _apply_info():
            if self.input_path != source_path:
                return
            self.media_duration = int(round(dur_f))
            if vid_w > 0 and vid_h > 0:
                self.media_width = vid_w
                self.media_height = vid_h
            if hasattr(self, "nle_project") and dur_f > 0:
                self.nle_project.update_source_duration_if_single_untouched(dur_f, source_path)
                tot_tl = max(self.nle_project.total_duration, 0.1)
                self.timeline_scale.configure(to=tot_tl)
                if hasattr(self, "davinci_timeline"):
                    self.davinci_timeline.redraw()
            else:
                self.timeline_scale.configure(to=max(self.media_duration, 0))
            self._refresh_timeline_text()
            if hasattr(self, "_draw_player_visual_timeline"):
                self._draw_player_visual_timeline()
            if hasattr(self, "_refresh_master_export_summary"):
                self._refresh_master_export_summary()
            is_ar = self.language_var.get() == "العربية"
            if estimate:
                prefix = "الحجم التقريبي: ~" if is_ar else "Est. ~"
                self.video_estimate_var.set(f"{prefix}{convert.human_size(estimate)}")
            else:
                self.video_estimate_var.set("الحجم التقريبي غير معروف" if is_ar else "Est. unknown")

        self.run_on_main_thread(_apply_info)

        # Extract real high-density audio waveform peaks for DaVinci Track A1 in background
        if extract_waveform and source_path.is_file() and source_path == self.input_path:
            try:
                peaks = extract_audio_waveform_peaks(
                    source_path,
                    ffmpeg_exe=str(convert.ffmpeg_executable()),
                    duration=dur_f,
                )
                if peaks and self.input_path == source_path:
                    def _apply_peaks():
                        if self.input_path == source_path and hasattr(self, "davinci_timeline"):
                            self.davinci_timeline.waveform_peaks = peaks
                            self.davinci_timeline.redraw()
                    self.run_on_main_thread(_apply_peaks)
            except Exception:
                pass

    def open_source(self):
        if not self.input_path:
            return
        self.open_folder(self.input_path.parent if self.input_path.is_file() else self.input_path)

    def _load_media_duration(self):
        self.media_duration = 0
        self.timeline_var.set(0)
        if self._single_media_file_selected():
            try:
                dur_f = float(convert.get_media_duration(self.input_path) or 0.0)
                self.media_duration = int(round(dur_f))
                if hasattr(self, "nle_project") and dur_f > 0:
                    self.nle_project.update_source_duration_if_single_untouched(dur_f, self.input_path)
            except Exception:
                self.media_duration = 0
        tot = self._edited_total_duration()
        self.timeline_scale.configure(to=max(tot, 0))
        self._refresh_timeline_text()

    def _edited_total_duration(self) -> float:
        if hasattr(self, "nle_project") and self.nle_project.clips and self.media_duration > 0:
            return float(self.nle_project.total_duration)
        return float(self.media_duration or 0.0)

    def _format_time(self, seconds):
        seconds = max(0, int(seconds))
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def _refresh_timeline_text(self, playhead_only: bool = False):
        current = self._current_timeline_seconds()
        tot = self._edited_total_duration()
        if tot > 0:
            self.timeline_text_var.set(f"{self._format_time(current)} / {self._format_time(tot)}")
        else:
            self.timeline_text_var.set("00:00 / 00:00")
        if hasattr(self, "_draw_player_visual_timeline"):
            self._draw_player_visual_timeline(playhead_only=playhead_only)

    def _current_timeline_seconds(self):
        tot = self._edited_total_duration()
        return max(0.0, min(float(self.timeline_var.get() or 0.0), tot if tot > 0 else 999999.0))

    def _timeline_dragged(self, _value=None):
        tl_sec = self._current_timeline_seconds()
        self.nle_playhead_sec = tl_sec
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.set_playhead(tl_sec)
        self._refresh_timeline_text(playhead_only=True)
        if hasattr(self, "nle_project") and self.nle_project.clips:
            c_idx, cur_c, src_sec = self.nle_project.timeline_to_source(tl_sec)
            self.active_playback_clip_idx = c_idx
            if not self._is_playing():
                self._show_studio_canvas()
            if cur_c is None:
                self._render_player_studio_canvas()
            else:
                self._request_fast_preview_frame(src_sec)
        else:
            self._sync_live_video_overlay()

    def _timeline_press(self, _event=None):
        self.timeline_dragging = True
        self.was_playing_before_drag = self._is_playing()
        self._in_gap_playback = False

    def _timeline_release(self, _event=None):
        self.timeline_dragging = False
        tl_sec = self._current_timeline_seconds()
        self.nle_playhead_sec = tl_sec
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.set_playhead(tl_sec)
        c_idx, clip, src_sec = self.nle_project.timeline_to_source(tl_sec) if hasattr(self, "nle_project") else (0, None, tl_sec)
        self.active_playback_clip_idx = c_idx
        if self.media_player:
            self.media_player.set_time(int(src_sec * 1000))
            self._apply_active_clip_playback_fx(clip)
        self._refresh_timeline_text(playhead_only=True)
        if self.was_playing_before_drag and self.media_player:
            if not getattr(self, "studio_live_preview_mode", False):
                self._show_vlc_surface()
            else:
                self._show_studio_canvas()
            if clip is None:
                self._in_gap_playback = True
                self._gap_last_wall_ts = time.monotonic()
                if self.media_player.is_playing():
                    self.media_player.pause()
            else:
                self._in_gap_playback = False
                self.media_player.play()
                self._apply_active_clip_playback_fx(clip)
            self._schedule_playback_tick()
        else:
            self._show_studio_canvas()
            if clip is None:
                self._render_player_studio_canvas()
            else:
                self._request_fast_preview_frame(src_sec, force=True)
        self.was_playing_before_drag = False

    def mark_trim_start(self):
        self.push_app_undo("تحديد بداية التقطيع (In Point)", "Set In Point")
        tl_sec = self._current_timeline_seconds()
        _idx, _c, src_sec = self.nle_project.timeline_to_source(tl_sec) if hasattr(self, "nle_project") else (0, None, tl_sec)
        self.trim_start_var.set(self._format_time(src_sec))
        if hasattr(self, "_draw_player_visual_timeline"):
            self._draw_player_visual_timeline()

    def mark_trim_end(self):
        self.push_app_undo("تحديد نهاية التقطيع (Out Point)", "Set Out Point")
        tl_sec = self._current_timeline_seconds()
        _idx, _c, src_sec = self.nle_project.timeline_to_source(tl_sec) if hasattr(self, "nle_project") else (0, None, tl_sec)
        self.trim_end_var.set(self._format_time(src_sec))
        if hasattr(self, "_draw_player_visual_timeline"):
            self._draw_player_visual_timeline()














    def apply_playback_speed(self):
        self._apply_active_clip_playback_fx()

    def apply_volume(self, _value=None):
        self._apply_active_clip_playback_fx()

    def apply_video_aspect_ratio(self):
        if not self.media_player:
            return
        try:
            ratio = self.trim_aspect_var.get() if hasattr(self, "trim_aspect_var") else "original"
            fit_m = getattr(self, "video_branding_config", {}).get("fit_mode", "crop")
            if ratio and ratio != "original" and fit_m == "crop":
                self.media_player.video_set_aspect_ratio(None)
                self.media_player.video_set_crop_geometry(ratio.encode("utf-8") if isinstance(ratio, str) else ratio)
            else:
                self.media_player.video_set_crop_geometry(None)
                self.media_player.video_set_aspect_ratio(None)
        except Exception:
            pass

    def apply_video_color_adjustments(self, cfg=None):
        if not self.media_player:
            return
        if cfg is None:
            cfg = getattr(self, "video_branding_config", {}).get("color_config", {})
        try:
            from video_studio.color_grading import is_color_neutral
            if isinstance(cfg, dict) and cfg.get("enabled", True) and not is_color_neutral(cfg):
                self.media_player.video_set_adjust_int(vlc.VideoAdjustOption.Enable, 1)
                b = float(cfg.get("brightness", 0.0))
                self.media_player.video_set_adjust_float(vlc.VideoAdjustOption.Brightness, max(0.0, min(2.0, 1.0 + b)))
                c = float(cfg.get("contrast", 1.0))
                self.media_player.video_set_adjust_float(vlc.VideoAdjustOption.Contrast, max(0.0, min(2.0, c)))
                s = float(cfg.get("saturation", 1.0))
                self.media_player.video_set_adjust_float(vlc.VideoAdjustOption.Saturation, max(0.0, min(3.0, s)))
                g = float(cfg.get("gamma", 1.0))
                self.media_player.video_set_adjust_float(vlc.VideoAdjustOption.Gamma, max(0.1, min(4.0, g)))
            else:
                self.media_player.video_set_adjust_int(vlc.VideoAdjustOption.Enable, 0)
        except Exception:
            pass

    def _sync_live_video_overlay(self):
        """Refreshes the live studio canvas overlay with current branding, text, icons, and DaVinci transform."""
        if hasattr(self, "player_studio_canvas"):
            self._render_player_studio_canvas()

    # -------------------------------------------------------------------------
    # Player Studio Canvas & Interactive DaVinci Video Transform Engine
    # -------------------------------------------------------------------------






    # -------------------------------------------------------------------------
    # DaVinci Video Transform (Pan X / Pan Y / Zoom / Flip) & Clip FX Controls
    # -------------------------------------------------------------------------














    def _on_vid_transform_toggle(self):
        if getattr(self, "_updating_xf_ui", False):
            return
        self._ready_composed_video = None
        self._set_effective_video_transform(
            flip_h=bool(self.vid_flip_var.get()),
            clamp_edges=bool(self.vid_clamp_var.get()),
        )
        self._sync_transform_sliders_from_state()
        self._save_settings()
        self._refresh_master_export_summary()
        self._render_player_studio_canvas()

    def _on_clip_numeric_changed(self, _e=None):
        if getattr(self, "_updating_xf_ui", False):
            return
        c_idx = self._get_selected_or_active_clip_idx()
        if not hasattr(self, "nle_project") or not (0 <= c_idx < len(self.nle_project.clips)):
            return
        clip = self.nle_project.clips[c_idx]
        try:
            new_tl_pos = max(0.0, float(self.clip_tl_pos_var.get().strip()))
            new_in = max(0.0, float(self.clip_in_var.get().strip()))
            new_out = float(self.clip_out_var.get().strip())
        except ValueError:
            self._sync_transform_sliders_from_state()
            return

        max_src = float(self.nle_project.source_duration or 0.0)
        if max_src > 0.2:
            new_out = min(max_src, new_out)
            new_in = min(max(0.0, max_src - 0.12), new_in)
        if new_out < new_in + 0.12:
            new_out = new_in + 0.12

        in_changed = abs(new_in - float(clip.get("src_start", 0.0))) >= 0.01
        out_changed = abs(new_out - float(clip.get("src_end", 0.0))) >= 0.01
        pos_changed = abs(new_tl_pos - float(clip.get("tl_start", 0.0))) >= 0.015
        if not (in_changed or out_changed or pos_changed):
            self._sync_transform_sliders_from_state()
            return

        self.nle_project.push_undo()
        clip["src_start"] = round(new_in, 3)
        clip["src_end"] = round(new_out, 3)
        if pos_changed:
            self.nle_project.move_clip_to_time(c_idx, new_tl_pos, push_undo=False)
        else:
            self.nle_project.recompute_timeline()

        if hasattr(self, "export_opt_timeline_var"):
            self.export_opt_timeline_var.set(True)
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.redraw()
        self._on_nle_timeline_modified()

    def _on_clip_speed_changed(self, _e=None):
        if getattr(self, "_updating_xf_ui", False):
            return
        c_idx = self._get_selected_or_active_clip_idx()
        if not hasattr(self, "nle_project") or not (0 <= c_idx < len(self.nle_project.clips)):
            return
        try:
            spd = float(self.clip_speed_combo_var.get().replace("x", "").strip())
        except ValueError:
            self._sync_transform_sliders_from_state()
            return
        spd = round(max(0.25, min(4.0, spd)), 2)
        if abs(spd - float(self.nle_project.clips[c_idx].get("speed", 1.0))) < 0.005:
            return
        self.nle_project.push_undo()
        self.nle_project.clips[c_idx]["speed"] = spd
        self.nle_project.recompute_timeline()
        if hasattr(self, "export_opt_timeline_var"):
            self.export_opt_timeline_var.set(True)
        if self._is_playing():
            self._apply_active_clip_playback_fx()
        self._on_nle_timeline_modified()
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.redraw()

    def _on_clip_vol_changed(self, _val=None):
        if getattr(self, "_updating_xf_ui", False):
            return
        c_idx = self._get_selected_or_active_clip_idx()
        if not hasattr(self, "nle_project") or not (0 <= c_idx < len(self.nle_project.clips)):
            return
        vol_pct = max(0, min(200, int(round(float(self.clip_vol_var.get())))))
        clip = self.nle_project.clips[c_idx]
        clip["volume"] = round(vol_pct / 100.0, 2)
        if vol_pct > 0 and clip.get("muted"):
            clip["muted"] = False
        self._updating_xf_ui = True
        try:
            if hasattr(self, "clip_vol_spin_var"):
                self.clip_vol_spin_var.set(f"{vol_pct}")
            if hasattr(self, "clip_mute_var"):
                self.clip_mute_var.set(bool(clip.get("muted", False)))
        finally:
            self._updating_xf_ui = False
        if self._is_playing():
            self._apply_active_clip_playback_fx()
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.redraw()
        self._refresh_master_export_summary()

    def _on_clip_vol_spin_changed(self, _e=None):
        if getattr(self, "_updating_xf_ui", False):
            return
        c_idx = self._get_selected_or_active_clip_idx()
        if not hasattr(self, "nle_project") or not (0 <= c_idx < len(self.nle_project.clips)):
            return
        try:
            vol_pct = max(0, min(200, int(round(float(self.clip_vol_spin_var.get().replace("%", "").strip())))))
        except ValueError:
            self._sync_transform_sliders_from_state()
            return
        clip = self.nle_project.clips[c_idx]
        clip["volume"] = round(vol_pct / 100.0, 2)
        if vol_pct > 0 and clip.get("muted"):
            clip["muted"] = False
        self._sync_transform_sliders_from_state()
        if self._is_playing():
            self._apply_active_clip_playback_fx()
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.redraw()
        self._refresh_master_export_summary()

    def _on_clip_mute_toggled(self):
        if getattr(self, "_updating_xf_ui", False):
            return
        c_idx = self._get_selected_or_active_clip_idx()
        if not hasattr(self, "nle_project") or not (0 <= c_idx < len(self.nle_project.clips)):
            return
        self.nle_project.push_undo()
        clip = self.nle_project.clips[c_idx]
        clip["muted"] = bool(self.clip_mute_var.get())
        if hasattr(self, "export_opt_timeline_var"):
            self.export_opt_timeline_var.set(True)
        if self._is_playing():
            self._apply_active_clip_playback_fx()
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.redraw()
        self._refresh_master_export_summary()

    def _on_clip_audio_fade_changed(self, _e=None):
        if getattr(self, "_updating_xf_ui", False):
            return
        c_idx = self._get_selected_or_active_clip_idx()
        if not hasattr(self, "nle_project") or not (0 <= c_idx < len(self.nle_project.clips)):
            return
        clip = self.nle_project.clips[c_idx]
        try:
            fin = max(0.0, min(15.0, float(self.clip_fade_in_var.get().strip() or 0.0)))
        except ValueError:
            fin = 0.0
        try:
            fout = max(0.0, min(15.0, float(self.clip_fade_out_var.get().strip() or 0.0)))
        except ValueError:
            fout = 0.0

        if abs(fin - float(clip.get("audio_fade_in", 0.0) or 0.0)) < 0.01 and abs(fout - float(clip.get("audio_fade_out", 0.0) or 0.0)) < 0.01:
            return
        self.nle_project.push_undo()
        clip["audio_fade_in"] = round(fin, 2)
        clip["audio_fade_out"] = round(fout, 2)
        if hasattr(self, "export_opt_timeline_var"):
            self.export_opt_timeline_var.set(True)
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.redraw()
        self._refresh_master_export_summary()

    def _on_clip_denoise_toggled(self):
        if getattr(self, "_updating_xf_ui", False):
            return
        c_idx = self._get_selected_or_active_clip_idx()
        if not hasattr(self, "nle_project") or not (0 <= c_idx < len(self.nle_project.clips)):
            return
        self.nle_project.push_undo()
        clip = self.nle_project.clips[c_idx]
        clip["audio_denoise"] = bool(self.clip_denoise_var.get())
        if hasattr(self, "export_opt_timeline_var"):
            self.export_opt_timeline_var.set(True)
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.redraw()
        self._refresh_master_export_summary()

    # -------------------------------------------------------------------------
    # Universal App-Wide Undo/Redo Engine & Step-by-Step Auto-Save
    # -------------------------------------------------------------------------
    def _create_app_state_snapshot(self, action_ar: str = "", action_en: str = "") -> Dict[str, Any]:
        """
        Creates an immutable snapshot of the entire project state (NLE clips, overlays,
        branding, color grading, trim, playhead, selection).
        """
        nle_snap = self.nle_project.snapshot_dict() if hasattr(self, "nle_project") else {}
        branding_snap = copy.deepcopy(getattr(self, "video_branding_config", {}))
        return {
            "action_ar": action_ar or "خطوة سابقة",
            "action_en": action_en or "Previous Step",
            "timestamp": time.time(),
            "media_path": str(self.input_path) if getattr(self, "input_path", None) else "",
            "nle_project": nle_snap,
            "video_branding_config": branding_snap,
            "trim_in_sec": float(getattr(self, "trim_in_sec", 0.0) or 0.0),
            "trim_out_sec": float(getattr(self, "trim_out_sec", 0.0) or 0.0),
            "nle_playhead_sec": float(getattr(self, "nle_playhead_sec", 0.0) or 0.0),
            "selected_ref": getattr(self, "player_canvas_selected", ("clip", 0)),
        }

    def push_app_undo(self, action_ar: str, action_en: str = ""):
        """
        Pushes a new state to the application undo stack and auto-saves the step.
        Guarantees that ANY step (timeline cut, color grading, aspect ratio, trim, branding)
        can be undone seamlessly with Ctrl+Z.
        """
        if getattr(self, "_is_restoring_state", False):
            return
        snapshot = self._create_app_state_snapshot(action_ar, action_en)
        self._app_undo_stack.append(snapshot)
        if len(self._app_undo_stack) > 60:
            self._app_undo_stack.pop(0)
        self._app_redo_stack.clear()
        self.trigger_step_autosave()

    def _on_nle_undo_pushed(self):
        """
        Callback triggered whenever NLEProjectState records an internal undo step.
        Ensures the entire app-level snapshot and step auto-save stay synchronized.
        """
        if getattr(self, "_is_restoring_state", False):
            return
        now = time.time()
        if self._app_undo_stack and (now - self._app_undo_stack[-1].get("timestamp", 0.0) < 0.12):
            self.trigger_step_autosave()
            return
        self.push_app_undo("تعديل على التايم لاين", "Timeline Edit")

    def _apply_app_state_snapshot(self, snap: Dict[str, Any]):
        """
        Restores a previously captured snapshot and syncs all GUI panels.
        """
        self._is_restoring_state = True
        try:
            if hasattr(self, "nle_project") and "nle_project" in snap:
                self.nle_project.restore_snapshot(snap["nle_project"])
            if "video_branding_config" in snap:
                self.video_branding_config = copy.deepcopy(snap["video_branding_config"])
            if "trim_in_sec" in snap:
                self.trim_in_sec = snap["trim_in_sec"]
            if "trim_out_sec" in snap:
                self.trim_out_sec = snap["trim_out_sec"]
            if "nle_playhead_sec" in snap:
                self.nle_playhead_sec = snap["nle_playhead_sec"]
                self.timeline_var.set(self.nle_playhead_sec)
                if hasattr(self, "davinci_timeline"):
                    self.davinci_timeline.set_playhead(self.nle_playhead_sec)
            if "selected_ref" in snap:
                self.player_canvas_selected = snap["selected_ref"]
                if hasattr(self, "davinci_timeline"):
                    self.davinci_timeline.selected_ref = self.player_canvas_selected

            # Sync all controls and canvases
            self._sync_studio_color_controls()
            self._sync_transform_sliders_from_state()
            self._update_inspector_properties()
            self._refresh_timeline_text()
            self._refresh_master_export_summary()
            if hasattr(self, "davinci_timeline"):
                self.davinci_timeline.redraw()
            self._render_player_studio_canvas()
        finally:
            self._is_restoring_state = False

    def do_app_undo(self) -> bool:
        """
        Performs application-wide Undo (Ctrl + Z).
        Restores the previous step across timeline, color grading, branding, and trim.
        """
        is_ar = self.language_var.get() == "العربية"
        if not self._app_undo_stack:
            self._show_undo_toast("⚠️ " + ("لا توجد خطوات سابقة للتراجع عنها" if is_ar else "Nothing to undo"))
            return False

        # Current state becomes the redo target
        current_state = self._create_app_state_snapshot("الوضع الحالي", "Current State")
        self._app_redo_stack.append(current_state)

        # Pop previous step
        prev_snap = self._app_undo_stack.pop()
        self._apply_app_state_snapshot(prev_snap)

        action_desc = prev_snap.get("action_ar" if is_ar else "action_en") or ("خطوة سابقة" if is_ar else "Step")
        self._show_undo_toast(f"↩️ {action_desc}")
        self.trigger_step_autosave()
        return True

    def do_app_redo(self) -> bool:
        """
        Performs application-wide Redo (Ctrl + Y or Ctrl + Shift + Z).
        """
        is_ar = self.language_var.get() == "العربية"
        if not self._app_redo_stack:
            self._show_undo_toast("⚠️ " + ("لا توجد خطوات للإعادة" if is_ar else "Nothing to redo"))
            return False

        current_state = self._create_app_state_snapshot("الوضع الحالي", "Current State")
        self._app_undo_stack.append(current_state)

        next_snap = self._app_redo_stack.pop()
        self._apply_app_state_snapshot(next_snap)

        action_desc = next_snap.get("action_ar" if is_ar else "action_en") or ("خطوة" if is_ar else "Step")
        self._show_undo_toast(f"↪️ {action_desc}")
        self.trigger_step_autosave()
        return True

    def _show_undo_toast(self, text: str):
        """
        Displays non-intrusive feedback on the timeline bar, inspector status, and main status bar.
        """
        self.status_var.set(text)
        if hasattr(self, "davinci_timeline") and hasattr(self.davinci_timeline, "show_hud_toast"):
            self.davinci_timeline.show_hud_toast(text)
        if hasattr(self, "lbl_studio_color_diag"):
            self.lbl_studio_color_diag.configure(text=text)

    def trigger_step_autosave(self):
        """
        Auto-saves the complete project session after every single step.
        Guarantees 100% crash protection: if the app is abruptly closed or crashes,
        everything is safely persisted on disk.
        """
        if not getattr(self, "input_path", None) or not Path(self.input_path).is_file():
            return
        try:
            nle_dict = self.nle_project.snapshot_dict() if hasattr(self, "nle_project") else {}
            session_data = {
                "media_path": str(self.input_path),
                "media_duration": float(getattr(self, "media_duration", 0.0) or 0.0),
                "nle_project": nle_dict,
                "video_branding_config": copy.deepcopy(getattr(self, "video_branding_config", {})),
                "trim_in_sec": float(getattr(self, "trim_in_sec", 0.0) or 0.0),
                "trim_out_sec": float(getattr(self, "trim_out_sec", 0.0) or 0.0),
                "nle_playhead_sec": float(getattr(self, "nle_playhead_sec", 0.0) or 0.0),
                "subtitle_style": getattr(self, "subtitle_style", {}),
                "silence_config": getattr(self, "silence_config", {}),
                "video_format_key": getattr(self, "video_format_key", ".mp4"),
                "video_compression_key": getattr(self, "video_compression_key", "Original"),
                "video_resolution_key": getattr(self, "video_resolution_key", "Original"),
                "quality": self.quality_var.get() if hasattr(self, "quality_var") else "192k",
                "speed": self.speed_var.get() if hasattr(self, "speed_var") else "1.00x",
            }
            save_session_state(session_data, clean_exit=False)
            self._last_step_autosave_ts = time.time()
        except Exception:
            pass

    def _check_and_prompt_crash_recovery(self):
        """
        Checks if an unclosed or crashed previous session exists upon startup,
        and prompts the user to restore their work seamlessly.
        """
        try:
            has_rec, rec_data = has_recoverable_session()
            if not has_rec or not rec_data:
                return

            m_path_str = rec_data.get("media_path", "")
            m_path = Path(m_path_str)
            if not m_path.is_file():
                return

            nle = rec_data.get("nle_project", {})
            n_clips = len(nle.get("clips", []))
            saved_time = rec_data.get("saved_at_readable", "")
            is_ar = self.language_var.get() == "العربية"

            msg = (
                f"🚨 تم العثور على جلسة عمل سابقة غير محفوظة (تم إغلاق البرنامج بالخطأ أو فجأة)!\n\n"
                f"📁 اسم الفيديو: {m_path.name}\n"
                f"✂️ عدد المقاطع في التايم لاين: {n_clips} مقاطع\n"
                f"⏱️ تاريخ آخر حفظ: {saved_time}\n\n"
                f"هل تود استعادة جميع التعديلات ومتابعة العمل من حيث توقفت؟"
                if is_ar
                else
                f"🚨 An unsaved previous session was recovered (app closed unexpectedly)!\n\n"
                f"📁 Video: {m_path.name}\n"
                f"✂️ Timeline Clips: {n_clips} clips\n"
                f"⏱️ Last Autosave: {saved_time}\n\n"
                f"Would you like to restore all edits and resume work?"
            )

            if messagebox.askyesno(self.text("app_title"), msg):
                self.restore_saved_session(rec_data)
            else:
                clear_autosave()
        except Exception:
            pass

    def restore_saved_session(self, session_data: Dict[str, Any]):
        """
        Fully restores a session: media file, timeline clips, overlays, branding, colors, and markers.
        """
        is_ar = self.language_var.get() == "العربية"
        try:
            media_path = Path(session_data["media_path"])
            if not media_path.is_file():
                messagebox.showerror(
                    self.text("app_title"),
                    "تعذر العثور على ملف الفيديو على القرص." if is_ar else "Media file not found on disk."
                )
                return

            self._is_restoring_state = True
            try:
                self.set_source(media_path)
                if "nle_project" in session_data and hasattr(self, "nle_project"):
                    self.nle_project.restore_snapshot(session_data["nle_project"])
                if "video_branding_config" in session_data:
                    self.video_branding_config = copy.deepcopy(session_data["video_branding_config"])
                if "trim_in_sec" in session_data:
                    self.trim_in_sec = session_data["trim_in_sec"]
                if "trim_out_sec" in session_data:
                    self.trim_out_sec = session_data["trim_out_sec"]
                if "nle_playhead_sec" in session_data:
                    self.nle_playhead_sec = session_data["nle_playhead_sec"]
                    self.timeline_var.set(self.nle_playhead_sec)

                self._sync_studio_color_controls()
                self._sync_transform_sliders_from_state()
                self._update_inspector_properties()
                self._refresh_timeline_text()
                self._refresh_master_export_summary()
                if hasattr(self, "davinci_timeline"):
                    self.davinci_timeline.redraw()
                    self.davinci_timeline.set_playhead(self.nle_playhead_sec)
                self._render_player_studio_canvas()
            finally:
                self._is_restoring_state = False

            self.push_app_undo("استعادة جلسة العمل المحفوظة", "Restored Autosaved Session")
            succ_msg = "✅ تم استعادة مشروعك السابق بنجاح وكافة التعديلات محفوظة!" if is_ar else "✅ Previous session successfully restored!"
            self._show_undo_toast(succ_msg)
            self._append_log(f"\n{succ_msg}\n")
        except Exception as e:
            messagebox.showerror(self.text("app_title"), f"Error restoring session: {e}")

    def _manual_restore_session(self):
        """
        Manually trigger session restoration via the Restore Session button.
        """
        is_ar = self.language_var.get() == "العربية"
        data = load_session_state()
        if not data or not data.get("media_path") or not Path(data["media_path"]).is_file():
            messagebox.showinfo(
                self.text("app_title"),
                "لا توجد جلسة عمل محفوظة حالياً لاستعادتها." if is_ar else "No saved session found to restore."
            )
            return
        m_name = Path(data["media_path"]).name
        n_clips = len(data.get("nle_project", {}).get("clips", []))
        time_str = data.get("saved_at_readable", "")
        q = (
            f"هل تريد استعادة آخر جلسة عمل محفوظة؟\n\n"
            f"📁 الملف: {m_name}\n"
            f"✂️ المقاطع: {n_clips}\n"
            f"⏱️ الحفظ: {time_str}"
            if is_ar else
            f"Restore last saved session?\n\n"
            f"📁 Video: {m_name}\n"
            f"✂️ Clips: {n_clips}\n"
            f"⏱️ Saved: {time_str}"
        )
        if messagebox.askyesno(self.text("app_title"), q):
            self.restore_saved_session(data)

    def _handle_undo_event(self, event=None):
        if event and isinstance(event.widget, (tk.Entry, ttk.Entry, tk.Text, tk.Spinbox, ttk.Spinbox)):
            return
        self.do_app_undo()
        return "break"

    def _handle_redo_event(self, event=None):
        if event and isinstance(event.widget, (tk.Entry, ttk.Entry, tk.Text, tk.Spinbox, ttk.Spinbox)):
            return
        self.do_app_redo()
        return "break"

    # -------------------------------------------------------------------------
    # Project File Management (.masproj / .json) & Recent Projects
    # -------------------------------------------------------------------------
    def save_project(self, save_as: bool = False):
        """
        Saves the current montage project, clips, overlays, branding, and color grading
        to a portable .masproj project file.
        """
        is_ar = self.language_var.get() == "العربية"
        if not getattr(self, "input_path", None) or not self.input_path.is_file():
            messagebox.showwarning(
                self.text("app_title"),
                "يرجى فتح ملف وسائط أو فيديو أولاً لحفظ المشروع." if is_ar else "Please open a media file first to save a project."
            )
            return

        target_file = getattr(self, "current_project_file", None)
        if save_as or not target_file:
            init_name = f"{self.input_path.stem}.ccproj"
            init_dir = str(self.input_path.parent)
            chosen = filedialog.asksaveasfilename(
                title="حفظ المشروع باسم" if is_ar else "Save Project As",
                initialdir=init_dir,
                initialfile=init_name,
                defaultextension=".ccproj",
                filetypes=[
                    ("ClipCraft Studio Project (*.ccproj, *.masproj)", "*.ccproj;*.masproj"),
                    ("JSON Project File (*.json)", "*.json"),
                    ("All Files (*.*)", "*.*"),
                ],
            )
            if not chosen:
                return
            target_file = Path(chosen)

        snap = self._create_app_state_snapshot("حفظ المشروع", "Save Project")
        snap["project_name"] = target_file.stem
        success = save_project_file(target_file, snap)
        if success:
            self.current_project_file = target_file
            self.title(f"{self.text('app_title')} — [{target_file.name}]")
            succ_msg = f"💾 تم حفظ المشروع بنجاح: {target_file.name}" if is_ar else f"💾 Project saved successfully: {target_file.name}"
            self.status_var.set(succ_msg)
            self._append_log(f"\n{succ_msg}\n")
            if hasattr(self, "davinci_timeline"):
                self.davinci_timeline.show_hud_toast("💾 " + ("تم حفظ المشروع!" if is_ar else "Project Saved!"))
        else:
            messagebox.showerror(
                self.text("app_title"),
                "حدث خطأ أثناء حفظ ملف المشروع." if is_ar else "Failed to save project file."
            )

    def open_project(self, target_path: Optional[Union[str, Path]] = None):
        """
        Opens and restores an existing .ccproj, .masproj or .json project file.
        """
        is_ar = self.language_var.get() == "العربية"
        if not target_path:
            chosen = filedialog.askopenfilename(
                title="فتح مشروع مونتاج" if is_ar else "Open Project",
                filetypes=[
                    ("ClipCraft Studio Projects (*.ccproj, *.masproj, *.json)", "*.ccproj;*.masproj;*.json"),
                    ("All Files (*.*)", "*.*"),
                ],
            )
            if not chosen:
                return
            target_path = Path(chosen)
        else:
            target_path = Path(target_path)

        if not target_path.is_file():
            messagebox.showerror(
                self.text("app_title"),
                "ملف المشروع المحدد غير موجود على القرص." if is_ar else "The specified project file does not exist."
            )
            return

        data = load_project_file(target_path)
        if not data or not isinstance(data, dict):
            messagebox.showerror(
                self.text("app_title"),
                "تعذر قراءة ملف المشروع أو أن الصيغة غير مدعومة." if is_ar else "Could not load or parse project file."
            )
            return

        media_str = data.get("media_path", "")
        m_path = Path(media_str) if media_str else None
        if not m_path or not m_path.is_file():
            # Prompt user to locate missing media
            msg = (
                f"⚠️ تعذر العثور تلقائياً على ملف الوسائط المرتبط بالمشروع:\n\n{media_str or 'غير محدد'}\n\nهل تود تحديد مكانه الآن يدوياً؟"
                if is_ar else
                f"⚠️ Could not find the associated media file:\n\n{media_str or 'Not specified'}\n\nWould you like to locate it now?"
            )
            if messagebox.askyesno(self.text("app_title"), msg):
                loc = filedialog.askopenfilename(
                    title="تحديد ملف الوسائط للمشروع" if is_ar else "Locate Project Media File",
                    filetypes=[("Media Files", "*.*")],
                )
                if loc and Path(loc).is_file():
                    data["media_path"] = str(Path(loc).resolve())
                else:
                    return
            else:
                return

        self.restore_saved_session(data)
        self.current_project_file = target_path
        self.title(f"{self.text('app_title')} — [{target_path.name}]")
        open_msg = f"📂 تم فتح المشروع بنجاح: {target_path.name}" if is_ar else f"📂 Project opened successfully: {target_path.name}"
        self.status_var.set(open_msg)
        self._append_log(f"\n{open_msg}\n")
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.show_hud_toast("📂 " + ("تم فتح المشروع بنجاح!" if is_ar else "Project Loaded!"))

    def show_recent_projects_popup(self):
        """
        Displays a popup menu under the '🕒 الأخيرة' button listing recent projects and recent media.
        """
        is_ar = self.language_var.get() == "العربية"
        rec_projects = get_recent_projects()
        rec_media = get_recent_media()

        if not rec_projects and not rec_media:
            msg = "لا توجد مشاريع أو ملفات وسائط سابقة مسجلة." if is_ar else "No recent projects or media files found."
            if hasattr(self, "davinci_timeline"):
                self.davinci_timeline.show_hud_toast("🕒 " + msg)
            else:
                messagebox.showinfo(self.text("app_title"), msg)
            return

        menu = tk.Menu(self, tearoff=0, font=("Segoe UI", 9))

        if rec_projects:
            menu.add_command(
                label="📁 المشاريع السابقة (.masproj):" if is_ar else "📁 Recent Projects (.masproj):",
                state="disabled"
            )
            for item in rec_projects[:10]:
                p_path = item.get("path", "")
                p_title = item.get("title", Path(p_path).stem if p_path else "")
                n_c = item.get("clips_count", 0)
                lbl = f"  💾 {p_title} ({n_c} مقاطع)" if is_ar else f"  💾 {p_title} ({n_c} clips)"
                menu.add_command(
                    label=lbl,
                    command=lambda p=p_path: self.open_project(p)
                )

        if rec_projects and rec_media:
            menu.add_separator()

        if rec_media:
            menu.add_command(
                label="🎬 ملفات الوسائط الأخيرة:" if is_ar else "🎬 Recent Media Files:",
                state="disabled"
            )
            for m_item in rec_media[:10]:
                m_path = m_item.get("path", "")
                m_name = m_item.get("name", Path(m_path).name if m_path else "")
                lbl = f"  🎥 {m_name}"
                menu.add_command(
                    label=lbl,
                    command=lambda p=m_path: self.set_source(Path(p))
                )

        # Calculate popup placement
        btn = getattr(self, "btn_recent_proj", None)
        if btn and btn.winfo_ismapped():
            x = btn.winfo_rootx()
            y = btn.winfo_rooty() + btn.winfo_height()
        else:
            x = self.winfo_pointerx()
            y = self.winfo_pointery()

        try:
            menu.post(x, y)
        except Exception:
            pass

    def _handle_save_project_event(self, event=None, save_as: bool = False):
        if event and isinstance(event.widget, (tk.Entry, ttk.Entry, tk.Text, tk.Spinbox, ttk.Spinbox)):
            return
        self.save_project(save_as=save_as)
        return "break"

    def _handle_open_project_event(self, event=None):
        if event and isinstance(event.widget, (tk.Entry, ttk.Entry, tk.Text, tk.Spinbox, ttk.Spinbox)):
            return
        self.open_project()
        return "break"

    # -------------------------------------------------------------------------
    # Live Studio Color Grading, Live Silence Splitting & Modular Export Helpers
    # -------------------------------------------------------------------------








    def _start_studio_transcription_quick(self):
        """Starts AI audio transcription directly, switching smoothly to the Auto-Caption Studio."""
        is_ar = self.language_var.get() == "العربية"
        if not self._single_media_file_selected():
            messagebox.showwarning(self.text("app_title"), self.text("choose_single_trim"))
            return
        if hasattr(self, "export_opt_transcript_files_var"):
            self.export_opt_transcript_files_var.set(True)
        self._refresh_master_export_summary()
        if hasattr(self, "notebook") and hasattr(self, "tab_caption"):
            self.notebook.select(self.tab_caption)
        self.start_embedded_caption()

    def _toggle_export_card_collapse(self):
        is_ar = self.language_var.get() == "العربية"
        collapsed = getattr(self, "_export_card_collapsed", False)
        if collapsed:
            self._export_card_collapsed = False
            if hasattr(self, "exp_scope_row") and self.exp_scope_row:
                self.exp_scope_row.grid()
            if hasattr(self, "exp_checks") and self.exp_checks:
                self.exp_checks.grid()
            if hasattr(self, "exp_fmt_row") and self.exp_fmt_row:
                self.exp_fmt_row.grid()
            if hasattr(self, "master_export_summary_label") and self.master_export_summary_label:
                self.master_export_summary_label.grid()
            if hasattr(self, "btn_exp_collapse") and self.btn_exp_collapse:
                self.btn_exp_collapse.configure(text="▲ إخفاء" if is_ar else "▲ Hide")
        else:
            self._export_card_collapsed = True
            if hasattr(self, "exp_scope_row") and self.exp_scope_row:
                self.exp_scope_row.grid_remove()
            if hasattr(self, "exp_checks") and self.exp_checks:
                self.exp_checks.grid_remove()
            if hasattr(self, "exp_fmt_row") and self.exp_fmt_row:
                self.exp_fmt_row.grid_remove()
            if hasattr(self, "master_export_summary_label") and self.master_export_summary_label:
                self.master_export_summary_label.grid_remove()
            if hasattr(self, "btn_exp_collapse") and self.btn_exp_collapse:
                self.btn_exp_collapse.configure(text="▼ إظهار" if is_ar else "▼ Options")
        if hasattr(self, "inspector_canvas") and hasattr(self, "dynamic_inspector_host"):
            self.dynamic_inspector_host.update_idletasks()
            self.inspector_canvas.configure(scrollregion=self.inspector_canvas.bbox("all"))




    def _open_text_settings(self):
        """Opens text properties inspector without automatically creating timeline elements."""
        if hasattr(self, "nle_project") and self.nle_project.text_items:
            sel = getattr(self, "player_canvas_selected", None)
            if not (sel and sel[0] == "V3" and 0 <= sel[1] < len(self.nle_project.text_items)):
                self.player_canvas_selected = ("V3", len(self.nle_project.text_items) - 1)
        else:
            self.player_canvas_selected = ("V3", "new")
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.selected_ref = self.player_canvas_selected
            self.davinci_timeline.redraw()
        self._show_inspector_context("overlay")

    # -------------------------------------------------------------------------
    # Multi-Track NLE Timeline Callbacks & Element Creation (V2, V3, V4)
    # -------------------------------------------------------------------------
    def _nle_add_element(self, kind: str, at_sec=None, custom_text=None, font_name=None, font_size=None, text_color=None, bg_color=None):
        is_ar = self.language_var.get() == "العربية"
        tot = max(5.0, self._edited_total_duration() or 60.0)
        s_sec = round(max(0.0, min(max(0.0, tot - 0.5), float(at_sec if at_sec is not None else self.nle_playhead_sec))), 2)
        e_sec = round(min(tot, max(s_sec + 1.0, s_sec + 5.0)), 2)

        if kind == "text":
            self.nle_project.push_undo()
            idx_num = len(self.nle_project.text_items) + 1
            new_item = {
                "id": self.nle_project.next_id("v3"),
                "text": str(custom_text) if custom_text else (f"عنوان احترافي {idx_num}" if is_ar else f"Pro Title {idx_num}"),
                "x": 0.50,
                "y": min(0.86, 0.14 + ((idx_num - 1) % 4) * 0.10),
                "font_size": int(font_size) if font_size else 38,
                "font_name": str(font_name) if font_name else "Segoe UI",
                "bg_color": str(bg_color) if bg_color else "black",
                "text_color": str(text_color) if text_color else ("yellow" if idx_num % 2 == 0 else "white"),
                "opacity": 1.0,
                "rotation": 0.0,
                "full_duration": (at_sec is None and tot <= 6.0),
                "start_sec": s_sec,
                "end_sec": e_sec,
                "enabled": True,
            }
            self.nle_project.text_items.append(new_item)
            self.nle_project.track_enabled["V3"] = True
            self.trim_title_var.set(True)
            self.video_branding_config["title_enabled"] = True
            sel = ("V3", len(self.nle_project.text_items) - 1)

        elif kind == "icon":
            dlg = IconPickerDialog(self)
            self.wait_window(dlg)
            if not dlg.result:
                return
            self.nle_project.push_undo()
            ikey = dlg.result["icon_key"]
            custom_txt = dlg.result.get("text", "")
            preset = ICON_PRESETS.get(ikey, {})
            is_badge = (preset.get("kind") == "badge")
            new_item = {
                "id": self.nle_project.next_id("v2"),
                "type": "icon",
                "icon_key": ikey,
                "text": custom_txt,
                "x": 0.50,
                "y": 0.80 if is_badge else 0.25,
                "scale": 0.34 if is_badge else 0.16,
                "opacity": 1.0,
                "rotation": 0.0,
                "full_duration": False,
                "start_sec": s_sec,
                "end_sec": e_sec,
                "enabled": True,
            }
            self.nle_project.media_items.append(new_item)
            self.nle_project.track_enabled["V2"] = True
            sel = ("V2", len(self.nle_project.media_items) - 1)

        elif kind == "image":
            chosen = filedialog.askopenfilename(
                parent=self,
                title="اختر صورة لإضافتها فوق الفيديو" if is_ar else "Select Overlay Image",
                filetypes=[
                    ("Images", "*.png *.jpg *.jpeg *.webp *.bmp"),
                    ("PNG Transparent", "*.png"),
                    ("All files", "*.*"),
                ],
            )
            if not chosen:
                return
            self.nle_project.push_undo()
            new_item = {
                "id": self.nle_project.next_id("v2"),
                "type": "image",
                "path": chosen,
                "x": 0.50,
                "y": 0.50,
                "scale": 0.32,
                "opacity": 1.0,
                "rotation": 0.0,
                "full_duration": False,
                "start_sec": s_sec,
                "end_sec": e_sec,
                "enabled": True,
            }
            self.nle_project.media_items.append(new_item)
            self.nle_project.track_enabled["V2"] = True
            sel = ("V2", len(self.nle_project.media_items) - 1)

        elif kind == "logo":
            chosen = filedialog.askopenfilename(
                parent=self,
                title=self.text("branding_logo_file"),
                filetypes=[
                    ("Image files", "*.png *.jpg *.jpeg *.webp *.bmp"),
                    ("PNG Transparent", "*.png"),
                    ("All files", "*.*"),
                ],
            )
            if not chosen:
                return
            self.nle_project.push_undo()
            is_first_global = (len(self.nle_project.logo_items) == 0 and at_sec is None)
            new_logo = {
                "id": self.nle_project.next_id("v4"),
                "path": chosen,
                "x": 0.80,
                "y": 0.04,
                "scale": 0.16,
                "opacity": 1.0,
                "rotation": 0.0,
                "anchor": "nw",
                "full_duration": is_first_global,
                "start_sec": s_sec,
                "end_sec": tot if is_first_global else e_sec,
                "enabled": True,
            }
            self.nle_project.logo_items.append(new_logo)
            self.nle_project.track_enabled["V4"] = True
            self.video_branding_config["logo_path"] = chosen
            self.video_branding_config["logo_enabled"] = True
            self.trim_logo_var.set(True)
            sel = ("V4", len(self.nle_project.logo_items) - 1)
        else:
            return

        if hasattr(self, "export_opt_overlays_var"):
            self.export_opt_overlays_var.set(True)
        self._overlay_pil_cache.clear()
        self.player_canvas_selected = sel
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.selected_ref = sel
            self.davinci_timeline.redraw()
        self._save_settings()
        self._refresh_master_export_summary()
        self._show_inspector_context("overlay")
        self._show_studio_canvas()

    def _on_nle_timeline_scrub(self, tl_sec: float, is_final: bool):
        tot = max(0.1, self._edited_total_duration() or 60.0)
        tl_sec = max(0.0, min(tot, float(tl_sec)))
        self.nle_playhead_sec = tl_sec
        self.timeline_var.set(tl_sec)
        self._refresh_timeline_text(playhead_only=not is_final)

        c_idx, clip, src_sec = self.nle_project.timeline_to_source(tl_sec)
        if c_idx != self.active_playback_clip_idx:
            self.active_playback_clip_idx = c_idx
            self._sync_transform_sliders_from_state()

        if self.media_player and self.loaded_media_path == self.input_path:
            if is_final or self._is_playing():
                try:
                    if clip is None:
                        if self._is_playing():
                            self._in_gap_playback = True
                            self._gap_last_wall_ts = time.monotonic()
                            if self.media_player.is_playing():
                                self.media_player.pause()
                    else:
                        self._in_gap_playback = False
                        self.media_player.set_time(int(src_sec * 1000))
                        self._apply_active_clip_playback_fx(clip)
                except Exception:
                    pass

        if clip is None:
            self._render_player_studio_canvas()
        else:
            self._request_fast_preview_frame(src_sec, force=is_final)

    def _on_nle_timeline_select(self, sel_ref):
        self.player_canvas_selected = sel_ref
        self._sync_transform_sliders_from_state()
        if isinstance(sel_ref, tuple) and (sel_ref[0] in ("V2", "V3", "V4", "A2") or str(sel_ref[0]).startswith("AUD")):
            self._show_inspector_context("overlay")
        elif isinstance(sel_ref, tuple) and sel_ref[0] == "clip":
            c_idx = sel_ref[1]
            if hasattr(self, "nle_project") and 0 <= c_idx < len(self.nle_project.clips):
                c = self.nle_project.clips[c_idx]
                s_sec = float(c.get("src_start", 0.0))
                e_sec = float(c.get("src_end", 0.0))
                self.trim_start_var.set(self._format_time(s_sec))
                self.trim_end_var.set(self._format_time(e_sec))
            self._show_inspector_context("video")
        else:
            self._update_inspector_properties()
        if hasattr(self, "_refresh_master_export_summary"):
            self._refresh_master_export_summary()
        self._render_player_studio_canvas()

    def _toggle_orig_video_audio(self):
        if not hasattr(self, "nle_project"):
            return
        cur = self.nle_project.track_enabled.get("A1", True)
        self.nle_project.track_enabled["A1"] = not cur
        is_ar = self.language_var.get() == "العربية"
        self._refresh_audio_inspector_status()
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.redraw()
            is_on = self.nle_project.track_enabled.get("A1", True)
            self.davinci_timeline.show_hud_toast("🔊 تم تفعيل صوت الفيديو الأصلي" if is_on else "🔇 تم كتم صوت الفيديو الأصلي بالكامل" if is_ar else ("🔊 Original video audio enabled" if is_on else "🔇 Original video audio muted"))
        if hasattr(self, "media_player") and self.media_player:
            self._apply_active_clip_playback_fx()
        self._refresh_master_export_summary()

    def _refresh_audio_inspector_status(self):
        if not hasattr(self, "lbl_audio_tracks_status") or not self.lbl_audio_tracks_status.winfo_exists():
            return
        is_ar = self.language_var.get() == "العربية"
        a1_on = self.nle_project.track_enabled.get("A1", True) if hasattr(self, "nle_project") else True
        num_a2 = len(getattr(self.nle_project, "audio_items", [])) if hasattr(self, "nle_project") else 0
        a2_on = self.nle_project.track_enabled.get("A2", True) if hasattr(self, "nle_project") else True

        if hasattr(self, "btn_toggle_orig_audio"):
            if a1_on:
                self.btn_toggle_orig_audio.configure(
                    text="🔇 كتم صوت الفيديو الأصلي بالكامل (A1)" if is_ar else "🔇 Mute Video Audio (A1)",
                    style="Player.TButton",
                )
            else:
                self.btn_toggle_orig_audio.configure(
                    text="🔊 تشغيل صوت الفيديو الأصلي (A1)" if is_ar else "🔊 Unmute Video Audio (A1)",
                    style="PrimaryPlayer.TButton",
                )

        a1_str = ("🔊 مفعل" if is_ar else "🔊 On") if a1_on else ("🔇 مكتوم" if is_ar else "🔇 Muted")
        a2_str = f"🎵 {num_a2} " + (("ملفات مضافة" if num_a2 != 1 else "ملف مضاف") if is_ar else "items") if num_a2 > 0 else ("لا توجد ملفات" if is_ar else "None")
        if not a2_on and num_a2 > 0:
            a2_str += " (🔇 مكتوم)" if is_ar else " (Muted)"
        txt = f"• صوت الفيديو: {a1_str}  |  • المسار A2: {a2_str}" if is_ar else f"• Video Audio: {a1_str}  |  • Track A2: {a2_str}"
        self.lbl_audio_tracks_status.configure(text=txt)

    def _on_nle_timeline_modified(self):
        tot = max(0.1, self._edited_total_duration() or 60.0)
        self.timeline_scale.configure(to=tot)
        if self.nle_playhead_sec > tot:
            self.nle_playhead_sec = tot
            self.timeline_var.set(tot)
            if hasattr(self, "davinci_timeline"):
                self.davinci_timeline.set_playhead(tot)

        # Keep selection valid if items were deleted/undone
        sel = self.player_canvas_selected
        if isinstance(sel, tuple):
            kind, idx = sel
            if kind == "clip":
                if not (0 <= idx < len(self.nle_project.clips)):
                    self.player_canvas_selected = ("clip", max(0, len(self.nle_project.clips) - 1))
            elif kind in ("V2", "V3", "V4", "A2") or str(kind).startswith("AUD"):
                tlist = self.nle_project.get_track_list(kind)
                if not (0 <= idx < len(tlist)):
                    self.player_canvas_selected = ("clip", max(0, len(self.nle_project.clips) - 1))
                    if getattr(self, "active_inspector_context", "video") == "overlay":
                        self._show_inspector_context("video")

        self._overlay_pil_cache.clear()
        self._refresh_timeline_text()
        self._sync_transform_sliders_from_state()
        self._update_inspector_properties()
        self.refresh_video_transitions_panel()
        self._refresh_master_export_summary()
        self._save_settings()
        self.trigger_step_autosave()
        if hasattr(self, "_apply_active_clip_playback_fx"):
            self._apply_active_clip_playback_fx()

        _c_idx, cur_clip, src_sec = self.nle_project.timeline_to_source(self.nle_playhead_sec)
        if cur_clip is None:
            self._render_player_studio_canvas()
        else:
            self._request_fast_preview_frame(src_sec)

    # -------------------------------------------------------------------------
    # Context-Sensitive Overlay Inspector (V4 Logos, V3 Text+, V2 Icons/Images)
    # -------------------------------------------------------------------------

    def _build_overlay_xy_numeric_row(self, parent, row_idx: int, track_key: str, item: dict, idx: int):
        """Builds numeric X% and Y% Spinboxes so any overlay can be positioned both manually and numerically."""
        is_ar = self.language_var.get() == "العربية"
        xy_row = ttk.Frame(parent)
        xy_row.grid(row=row_idx, column=0, columnspan=2, sticky="ew", pady=1)
        xy_row.columnconfigure(1, weight=1)
        xy_row.columnconfigure(3, weight=1)

        xv = tk.StringVar(value=f"{float(item.get('x', 0.5)) * 100.0:.1f}")
        yv = tk.StringVar(value=f"{float(item.get('y', 0.5)) * 100.0:.1f}")

        def _apply_xy(*_a):
            try:
                nx = max(0.0, min(99.0, float(xv.get().replace("%", "").strip()))) / 100.0
                ny = max(0.0, min(99.0, float(yv.get().replace("%", "").strip()))) / 100.0
                item["x"] = round(nx, 4)
                item["y"] = round(ny, 4)
                if track_key == "V4" and idx == 0:
                    self.video_branding_config["logo_x"] = item["x"]
                    self.video_branding_config["logo_y"] = item["y"]
                self._save_settings()
                self._render_player_studio_canvas()
            except ValueError:
                pass

        ttk.Label(xy_row, text="أفقي X%:" if is_ar else "Pos X%:").grid(row=0, column=0, sticky="w")
        sp_x = tk.Spinbox(xy_row, from_=0.0, to=99.0, increment=1.0, format="%.1f", textvariable=xv, width=6, font=("Consolas", 8, "bold"), command=_apply_xy)
        sp_x.grid(row=0, column=1, sticky="ew", padx=(2, 6))
        sp_x.bind("<Return>", _apply_xy)
        sp_x.bind("<FocusOut>", _apply_xy)

        ttk.Label(xy_row, text="رأسي Y%:" if is_ar else "Pos Y%:").grid(row=0, column=2, sticky="w")
        sp_y = tk.Spinbox(xy_row, from_=0.0, to=99.0, increment=1.0, format="%.1f", textvariable=yv, width=6, font=("Consolas", 8, "bold"), command=_apply_xy)
        sp_y.grid(row=0, column=3, sticky="ew", padx=(2, 0))
        sp_y.bind("<Return>", _apply_xy)
        sp_y.bind("<FocusOut>", _apply_xy)

    def _build_overlay_timing_controls(self, parent, start_row: int, track_key: str, item: dict, idx: int):
        is_ar = self.language_var.get() == "العربية"
        tot = max(1.0, self._edited_total_duration() or 60.0)

        sep = ttk.Separator(parent, orient="horizontal")
        sep.grid(row=start_row, column=0, columnspan=2, sticky="ew", pady=(4, 2))

        t_frame = ttk.Frame(parent)
        t_frame.grid(row=start_row + 1, column=0, columnspan=2, sticky="ew")
        t_frame.columnconfigure(1, weight=1)
        t_frame.columnconfigure(4, weight=1)

        full_var = tk.BooleanVar(value=bool(item.get("full_duration", False)))
        s_var = tk.StringVar(value=f"{float(item.get('start_sec', 0.0)):.2f}")
        e_var = tk.StringVar(value=f"{float(item.get('end_sec', min(tot, 5.0))):.2f}")

        def _toggle_full():
            item["full_duration"] = bool(full_var.get())
            st = "disabled" if full_var.get() else "normal"
            s_ent.configure(state=st)
            e_ent.configure(state=st)
            btn_set_s.configure(state=st)
            btn_set_e.configure(state=st)
            st_anim = "disabled" if full_var.get() else "readonly"
            cmb_anim_in.configure(state=st_anim)
            cmb_anim_out.configure(state=st_anim)
            if hasattr(self, "davinci_timeline"):
                self.davinci_timeline.redraw()
            self._save_settings()
            self._render_player_studio_canvas()

        chk_full = ttk.Checkbutton(
            t_frame,
            text="⏱ عرض طوال الفيديو بالكامل" if is_ar else "⏱ Show Across Full Video",
            variable=full_var,
            command=_toggle_full,
        )
        chk_full.grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 2))

        def _apply_times(*_a):
            try:
                sv = max(0.0, float(s_var.get().strip()))
                ev = max(sv + 0.2, float(e_var.get().strip()))
                item["start_sec"] = round(sv, 2)
                item["end_sec"] = round(ev, 2)
                if hasattr(self, "davinci_timeline"):
                    self.davinci_timeline.redraw()
                self._save_settings()
                self._render_player_studio_canvas()
            except ValueError:
                pass

        ttk.Label(t_frame, text="منs:" if is_ar else "In s:").grid(row=1, column=0, sticky="w")
        s_ent = tk.Spinbox(t_frame, from_=0.0, to=99999.0, increment=0.20, format="%.2f", textvariable=s_var, width=6, font=("Consolas", 8), command=_apply_times)
        s_ent.grid(row=1, column=1, sticky="ew", padx=2)
        s_ent.bind("<Return>", _apply_times)
        s_ent.bind("<FocusOut>", _apply_times)

        def _set_in_playhead():
            s_var.set(f"{self.nle_playhead_sec:.2f}")
            if float(e_var.get() or 0) <= self.nle_playhead_sec:
                e_var.set(f"{min(tot, self.nle_playhead_sec + 4.0):.2f}")
            _apply_times()

        btn_set_s = ttk.Button(t_frame, text="📍", width=2, style="Player.TButton", command=_set_in_playhead)
        btn_set_s.grid(row=1, column=2, padx=(0, 4))

        ttk.Label(t_frame, text="إلىs:" if is_ar else "Out s:").grid(row=1, column=3, sticky="w")
        e_ent = tk.Spinbox(t_frame, from_=0.2, to=99999.0, increment=0.20, format="%.2f", textvariable=e_var, width=6, font=("Consolas", 8), command=_apply_times)
        e_ent.grid(row=1, column=4, sticky="ew", padx=2)
        e_ent.bind("<Return>", _apply_times)
        e_ent.bind("<FocusOut>", _apply_times)

        def _set_out_playhead():
            if self.nle_playhead_sec > float(s_var.get() or 0) + 0.2:
                e_var.set(f"{self.nle_playhead_sec:.2f}")
                _apply_times()

        btn_set_e = ttk.Button(t_frame, text="📍", width=2, style="Player.TButton", command=_set_out_playhead)
        btn_set_e.grid(row=1, column=5)

        # In / Out Animation Row
        anim_row = ttk.Frame(t_frame)
        anim_row.grid(row=2, column=0, columnspan=6, sticky="ew", pady=(3, 1))
        anim_row.columnconfigure(1, weight=1)
        anim_row.columnconfigure(3, weight=1)

        anim_in_opts = [
            ("none", "بدون" if is_ar else "None"),
            ("fade", "تلاشي Fade" if is_ar else "Fade"),
            ("slide_up", "انزلاق لأعلى" if is_ar else "Slide Up"),
            ("slide_down", "انزلاق لأسفل" if is_ar else "Slide Down"),
            ("slide_left", "انزلاق يسار" if is_ar else "Slide Left"),
            ("slide_right", "انزلاق يمين" if is_ar else "Slide Right"),
            ("pop", "وثب Pop" if is_ar else "Pop / Zoom"),
        ]
        anim_out_opts = [
            ("none", "بدون" if is_ar else "None"),
            ("fade", "تلاشي Fade" if is_ar else "Fade"),
            ("slide_down", "انزلاق لأسفل" if is_ar else "Slide Down"),
            ("slide_up", "انزلاق لأعلى" if is_ar else "Slide Up"),
            ("shrink", "انكماش Shrink" if is_ar else "Shrink"),
        ]
        in_map = {d: k for k, d in anim_in_opts}
        in_rev = {k: d for k, d in anim_in_opts}
        out_map = {d: k for k, d in anim_out_opts}
        out_rev = {k: d for k, d in anim_out_opts}

        cur_in = str(item.get("anim_in", "none") or "none")
        cur_out = str(item.get("anim_out", "none") or "none")

        ttk.Label(anim_row, text="دخول:" if is_ar else "In:").grid(row=0, column=0, sticky="w")
        var_anim_in = tk.StringVar(value=in_rev.get(cur_in, anim_in_opts[0][1]))
        cmb_anim_in = ttk.Combobox(anim_row, textvariable=var_anim_in, values=[d for _, d in anim_in_opts], state="readonly", width=9)
        cmb_anim_in.grid(row=0, column=1, sticky="ew", padx=(2, 4))

        ttk.Label(anim_row, text="خروج:" if is_ar else "Out:").grid(row=0, column=2, sticky="w")
        var_anim_out = tk.StringVar(value=out_rev.get(cur_out, anim_out_opts[0][1]))
        cmb_anim_out = ttk.Combobox(anim_row, textvariable=var_anim_out, values=[d for _, d in anim_out_opts], state="readonly", width=9)
        cmb_anim_out.grid(row=0, column=3, sticky="ew", padx=(2, 0))

        def _on_anim_select(_e=None):
            item["anim_in"] = in_map.get(var_anim_in.get(), "none")
            item["anim_out"] = out_map.get(var_anim_out.get(), "none")
            self._save_settings()
            self._render_player_studio_canvas()

        cmb_anim_in.bind("<<ComboboxSelected>>", _on_anim_select)
        cmb_anim_out.bind("<<ComboboxSelected>>", _on_anim_select)

        if full_var.get():
            s_ent.configure(state="disabled")
            e_ent.configure(state="disabled")
            btn_set_s.configure(state="disabled")
            btn_set_e.configure(state="disabled")
            cmb_anim_in.configure(state="disabled")
            cmb_anim_out.configure(state="disabled")

        # Split, Duplicate & Delete Row
        act_row = ttk.Frame(parent)
        act_row.grid(row=start_row + 2, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        for ci in range(3):
            act_row.columnconfigure(ci, weight=1)

        def _split_item():
            new_idx = self.nle_project.split_overlay_at(track_key, idx, self.nle_playhead_sec)
            if new_idx >= 0:
                self.player_canvas_selected = (track_key, new_idx)
                if hasattr(self, "davinci_timeline"):
                    self.davinci_timeline.selected_ref = (track_key, new_idx)
                    self.davinci_timeline.redraw()
                self._on_nle_timeline_modified()

        def _dup_item():
            if hasattr(self, "davinci_timeline"):
                self.davinci_timeline.selected_ref = (track_key, idx)
                self.davinci_timeline.duplicate_selected()

        def _del_item():
            self.nle_project.push_undo()
            tlist = self.nle_project.get_track_list(track_key)
            if 0 <= idx < len(tlist):
                tlist.pop(idx)
            self.player_canvas_selected = ("clip", self._get_selected_or_active_clip_idx())
            if hasattr(self, "davinci_timeline"):
                self.davinci_timeline.selected_ref = self.player_canvas_selected
                self.davinci_timeline.redraw()
            self._show_inspector_context("video")
            self._on_nle_timeline_modified()

        ttk.Button(
            act_row,
            text="✂️ شطر" if is_ar else "✂️ Split",
            command=_split_item,
            style="Player.TButton",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 2))
        ttk.Button(
            act_row,
            text="📋 تكرار" if is_ar else "📋 Duplicate",
            command=_dup_item,
            style="Player.TButton",
        ).grid(row=0, column=1, sticky="ew", padx=1)
        ttk.Button(
            act_row,
            text="🗑️ حذف" if is_ar else "🗑️ Delete",
            command=_del_item,
            style="Player.TButton",
        ).grid(row=0, column=2, sticky="ew", padx=(2, 0))

    def _update_inspector_properties(self):
        if not hasattr(self, "item_prop_card") or not self.item_prop_card.winfo_exists():
            return
        for child in self.item_prop_card.winfo_children():
            child.destroy()

        is_ar = self.language_var.get() == "العربية"
        sel = self._normalize_selection_ref(getattr(self, "player_canvas_selected", None))
        self.player_canvas_selected = sel

        back_btn = ttk.Button(
            self.item_prop_card,
            text="⬅ 🎬 العودة لإعدادات الفيديو والمقطع" if is_ar else "⬅ 🎬 Back to Video & Clip Settings",
            command=lambda: self._show_inspector_context("video"),
            style="Player.TButton",
        )
        back_btn.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 3))

        # ---------------- V4: Logo Properties ----------------
        if sel and sel[0] == "V4" and 0 <= sel[1] < len(self.nle_project.logo_items):
            l_idx = sel[1]
            item = self.nle_project.logo_items[l_idx]
            self.item_prop_card.configure(text=f"🛡️ خصائص اللوجو #{l_idx + 1}" if is_ar else f"🛡️ Logo #{l_idx + 1} Properties")

            self._build_overlay_xy_numeric_row(self.item_prop_card, 1, "V4", item, l_idx)

            sc_row = ttk.Frame(self.item_prop_card)
            sc_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=1)
            sc_row.columnconfigure(1, weight=1)
            l_scale = float(item.get("scale", 0.16))
            sc_spin_var = tk.StringVar(value=f"{int(round(l_scale * 100))}")
            ttk.Label(sc_row, text="الحجم%:" if is_ar else "Scale%:").grid(row=0, column=0, sticky="w", padx=(0, 4))

            def _on_l_sc(v):
                fv = round(float(v), 3)
                item["scale"] = fv
                self.video_branding_config["logo_scale"] = fv
                sc_spin_var.set(f"{int(round(fv * 100))}")
                self._overlay_pil_cache.clear()
                self._render_player_studio_canvas()

            sc_sl = ttk.Scale(sc_row, from_=0.05, to=0.65, value=l_scale, orient="horizontal", command=_on_l_sc)
            sc_sl.grid(row=0, column=1, sticky="ew")

            def _on_l_sc_spin(*_a):
                try:
                    fv = max(0.05, min(0.85, float(sc_spin_var.get().strip()) / 100.0))
                    item["scale"] = round(fv, 3)
                    self.video_branding_config["logo_scale"] = item["scale"]
                    sc_sl.set(fv)
                    self._overlay_pil_cache.clear()
                    self._render_player_studio_canvas()
                except ValueError:
                    pass

            sp_sc = tk.Spinbox(sc_row, from_=5, to=85, increment=2, textvariable=sc_spin_var, width=4, font=("Consolas", 8, "bold"), command=_on_l_sc_spin)
            sp_sc.grid(row=0, column=2, padx=(4, 0))
            sp_sc.bind("<Return>", _on_l_sc_spin)

            or_row = ttk.Frame(self.item_prop_card)
            or_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=1)
            or_row.columnconfigure(1, weight=1)
            or_row.columnconfigure(3, weight=1)
            l_op_var = tk.StringVar(value=f"{int(round(float(item.get('opacity', 1.0)) * 100))}")
            l_rot_var = tk.StringVar(value=f"{int(round(float(item.get('rotation', 0.0))))}")

            def _apply_l_or(*_a):
                try:
                    item["opacity"] = round(max(0.10, min(1.0, float(l_op_var.get().strip()) / 100.0)), 2)
                    item["rotation"] = round(max(-180.0, min(180.0, float(l_rot_var.get().strip()))), 1)
                    self._overlay_pil_cache.clear()
                    self._render_player_studio_canvas()
                except ValueError:
                    pass

            ttk.Label(or_row, text="شفافية%:" if is_ar else "Op%:").grid(row=0, column=0, sticky="w")
            sp_op = tk.Spinbox(or_row, from_=10, to=100, increment=5, textvariable=l_op_var, width=5, font=("Consolas", 8), command=_apply_l_or)
            sp_op.grid(row=0, column=1, sticky="ew", padx=(2, 6))
            sp_op.bind("<Return>", _apply_l_or)
            ttk.Label(or_row, text="دوران°:" if is_ar else "Rot°:").grid(row=0, column=2, sticky="w")
            sp_rt = tk.Spinbox(or_row, from_=-180, to=180, increment=5, textvariable=l_rot_var, width=5, font=("Consolas", 8), command=_apply_l_or)
            sp_rt.grid(row=0, column=3, sticky="ew", padx=(2, 0))
            sp_rt.bind("<Return>", _apply_l_or)

            p_row = ttk.Frame(self.item_prop_card)
            p_row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(2, 1))
            for ci in range(5):
                p_row.columnconfigure(ci, weight=1)

            def _chg_logo_img():
                ch = filedialog.askopenfilename(parent=self, title=self.text("branding_logo_file"), filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp")])
                if ch:
                    item["path"] = ch
                    self.video_branding_config["logo_path"] = ch
                    self._overlay_pil_cache.clear()
                    self._save_settings()
                    self._render_player_studio_canvas()

            def _snap_corner(nx, ny):
                item["x"] = nx
                item["y"] = ny
                item["anchor"] = "nw"
                self._save_settings()
                self._update_inspector_properties()
                self._render_player_studio_canvas()

            ttk.Button(p_row, text="📁 صورة" if is_ar else "📁 File", command=_chg_logo_img, style="Player.TButton").grid(row=0, column=0, sticky="ew", padx=1)
            ttk.Button(p_row, text="↖", width=3, command=lambda: _snap_corner(0.04, 0.04), style="Player.TButton").grid(row=0, column=1, sticky="ew", padx=1)
            ttk.Button(p_row, text="↗", width=3, command=lambda: _snap_corner(0.80, 0.04), style="Player.TButton").grid(row=0, column=2, sticky="ew", padx=1)
            ttk.Button(p_row, text="↙", width=3, command=lambda: _snap_corner(0.04, 0.84), style="Player.TButton").grid(row=0, column=3, sticky="ew", padx=1)
            ttk.Button(p_row, text="↘", width=3, command=lambda: _snap_corner(0.80, 0.84), style="Player.TButton").grid(row=0, column=4, sticky="ew", padx=1)

            self._build_overlay_timing_controls(self.item_prop_card, 5, "V4", item, l_idx)
            return

        # ---------------- V3: New Text Creator / Settings ----------------
        if sel and sel[0] == "V3" and sel[1] == "new":
            self.item_prop_card.configure(text="📝 إعدادات النص (Text+)" if is_ar else "📝 Text+ Settings")

            hint_lbl = ttk.Label(
                self.item_prop_card,
                text="اضبط خيارات النص واضغط الزر بالأسفل لإدراجه في التايم لاين عند المؤشر" if is_ar else "Configure text options and click Add below to insert onto timeline at playhead",
                font=("Segoe UI", 8),
                foreground="#8b949e",
                justify="center",
                wraplength=320,
            )
            hint_lbl.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 6))

            txt_row = ttk.Frame(self.item_prop_card)
            txt_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=2)
            txt_row.columnconfigure(1, weight=1)
            ttk.Label(txt_row, text="النص:" if is_ar else "Text:").grid(row=0, column=0, sticky="w", padx=(0, 4))
            idx_num = len(self.nle_project.text_items) + 1 if hasattr(self, "nle_project") else 1
            default_txt = f"عنوان احترافي {idx_num}" if is_ar else f"Pro Title {idx_num}"
            draft_txt_var = tk.StringVar(value=default_txt)
            ent = ttk.Entry(txt_row, textvariable=draft_txt_var)
            ent.grid(row=0, column=1, sticky="ew")
            self._attach_entry_context_menu(ent)

            fs_row = ttk.Frame(self.item_prop_card)
            fs_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=2)
            fs_row.columnconfigure(3, weight=1)
            ttk.Label(fs_row, text="الخط:" if is_ar else "Font:").grid(row=0, column=0, sticky="w")
            draft_font_var = tk.StringVar(value=AVAILABLE_FONTS[0])
            fnt_cb = ttk.Combobox(fs_row, textvariable=draft_font_var, values=AVAILABLE_FONTS, state="readonly", width=10)
            fnt_cb.grid(row=0, column=1, padx=(2, 4))

            draft_size_var = tk.StringVar(value="38")
            ttk.Label(fs_row, text="حجم:" if is_ar else "Sz:").grid(row=0, column=2, sticky="w")
            draft_size_scale = ttk.Scale(fs_row, from_=14, to=110, value=38, orient="horizontal", command=lambda v: draft_size_var.set(str(int(float(v)))))
            draft_size_scale.grid(row=0, column=3, sticky="ew", padx=2)

            def _on_draft_size_spin(*_a):
                try:
                    iv = max(14, min(120, int(float(draft_size_var.get().strip()))))
                    draft_size_scale.set(iv)
                except ValueError:
                    pass

            sp_fs = tk.Spinbox(fs_row, from_=14, to=120, increment=2, textvariable=draft_size_var, width=4, font=("Consolas", 8, "bold"), command=_on_draft_size_spin)
            sp_fs.grid(row=0, column=4)
            sp_fs.bind("<Return>", _on_draft_size_spin)

            col_row = ttk.Frame(self.item_prop_card)
            col_row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=2)
            for ci in (1, 3):
                col_row.columnconfigure(ci, weight=1)

            fg_choices = [(k, info["label_ar"] if is_ar else info["label_en"]) for k, info in BANNER_TEXT_COLORS.items()]
            fg_map = {d: k for k, d in fg_choices}
            draft_fg_var = tk.StringVar(value=fg_choices[0][1])
            ttk.Label(col_row, text="لون:" if is_ar else "FG:").grid(row=0, column=0, sticky="w")
            fg_cb = ttk.Combobox(col_row, textvariable=draft_fg_var, values=[c[1] for c in fg_choices], state="readonly", width=8)
            fg_cb.grid(row=0, column=1, sticky="ew", padx=(2, 4))

            bg_choices = [(k, info["label_ar"] if is_ar else info["label_en"]) for k, info in BANNER_BG_COLORS.items()]
            bg_map = {d: k for k, d in bg_choices}
            draft_bg_var = tk.StringVar(value=bg_choices[0][1])
            ttk.Label(col_row, text="خلفية:" if is_ar else "BG:").grid(row=0, column=2, sticky="w")
            bg_cb = ttk.Combobox(col_row, textvariable=draft_bg_var, values=[c[1] for c in bg_choices], state="readonly", width=8)
            bg_cb.grid(row=0, column=3, sticky="ew", padx=(2, 0))

            def _do_add():
                ctext = draft_txt_var.get().strip() or default_txt
                cfont = draft_font_var.get()
                try:
                    csize = int(float(draft_size_var.get().strip()))
                except Exception:
                    csize = 38
                cfg = fg_map.get(draft_fg_var.get(), "white")
                cbg = bg_map.get(draft_bg_var.get(), "black")
                self._nle_add_element("text", custom_text=ctext, font_name=cfont, font_size=csize, text_color=cfg, bg_color=cbg)

            add_action_btn = ttk.Button(
                self.item_prop_card,
                text="➕ إضافة هذا النص للتايم لاين" if is_ar else "➕ Add Text to Timeline",
                command=_do_add,
                style="PrimaryPlayer.TButton",
            )
            add_action_btn.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(8, 4))
            return

        # ---------------- V3: Text+ Card Properties ----------------
        if sel and sel[0] == "V3" and 0 <= sel[1] < len(self.nle_project.text_items):
            t_idx = sel[1]
            item = self.nle_project.text_items[t_idx]
            self.item_prop_card.configure(text=f"📝 خصائص النص #{t_idx + 1}" if is_ar else f"📝 Text+ #{t_idx + 1} Properties")

            action_bar = ttk.Frame(self.item_prop_card)
            action_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 3))
            action_bar.columnconfigure(0, weight=1)
            action_bar.columnconfigure(1, weight=1)

            def _switch_to_new_text():
                self.player_canvas_selected = ("V3", "new")
                self._update_inspector_properties()

            ttk.Button(
                action_bar,
                text="➕ إضافة نص جديد" if is_ar else "➕ Add New Text",
                command=_switch_to_new_text,
                style="PrimaryPlayer.TButton",
            ).grid(row=0, column=0, sticky="ew", padx=(0, 2))

            if len(self.nle_project.text_items) > 1:
                t_names = [f"{i + 1}: {it.get('text', '')[:14]}" for i, it in enumerate(self.nle_project.text_items)]
                t_sel_var = tk.StringVar(value=t_names[t_idx])

                def _on_pick_t(_e=None):
                    try:
                        n_idx = t_names.index(t_sel_var.get())
                        self.player_canvas_selected = ("V3", n_idx)
                        if hasattr(self, "davinci_timeline"):
                            self.davinci_timeline.selected_ref = self.player_canvas_selected
                            self.davinci_timeline.redraw()
                        self._update_inspector_properties()
                        self._render_player_studio_canvas()
                    except Exception:
                        pass

                t_pick_cb = ttk.Combobox(action_bar, textvariable=t_sel_var, values=t_names, state="readonly", width=12)
                t_pick_cb.grid(row=0, column=1, sticky="ew", padx=(2, 0))
                t_pick_cb.bind("<<ComboboxSelected>>", _on_pick_t)

            txt_row = ttk.Frame(self.item_prop_card)
            txt_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=1)
            txt_row.columnconfigure(1, weight=1)
            ttk.Label(txt_row, text="النص:" if is_ar else "Text:").grid(row=0, column=0, sticky="w", padx=(0, 4))
            txt_var = tk.StringVar(value=item.get("text", ""))

            def _on_txt(*_a):
                item["text"] = txt_var.get()
                self._overlay_pil_cache.clear()
                if hasattr(self, "davinci_timeline"):
                    self.davinci_timeline.redraw()
                self._render_player_studio_canvas()

            txt_var.trace_add("write", _on_txt)
            ent = ttk.Entry(txt_row, textvariable=txt_var)
            ent.grid(row=0, column=1, sticky="ew")
            self._attach_entry_context_menu(ent)

            self._build_overlay_xy_numeric_row(self.item_prop_card, 3, "V3", item, t_idx)

            # Font Family & Numeric Font Size Spinbox + Slider
            fs_row = ttk.Frame(self.item_prop_card)
            fs_row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=1)
            fs_row.columnconfigure(3, weight=1)
            ttk.Label(fs_row, text="الخط:" if is_ar else "Font:").grid(row=0, column=0, sticky="w")
            fnt_var = tk.StringVar(value=item.get("font_name", AVAILABLE_FONTS[0]))
            fnt_cb = ttk.Combobox(fs_row, textvariable=fnt_var, values=AVAILABLE_FONTS, state="readonly", width=10)
            fnt_cb.grid(row=0, column=1, padx=(2, 4))
            fnt_cb.bind("<<ComboboxSelected>>", lambda _e: (item.update({"font_name": fnt_var.get()}), self._overlay_pil_cache.clear(), self._save_settings(), self._render_player_studio_canvas()))

            cur_fs = int(item.get("font_size", 36))
            fs_spin_var = tk.StringVar(value=f"{cur_fs}")
            ttk.Label(fs_row, text="حجم:" if is_ar else "Sz:").grid(row=0, column=2, sticky="w")

            def _on_fs(v):
                iv = int(float(v))
                item["font_size"] = iv
                fs_spin_var.set(f"{iv}")
                self._overlay_pil_cache.clear()
                self._render_player_studio_canvas()

            fs_sl = ttk.Scale(fs_row, from_=14, to=110, value=cur_fs, orient="horizontal", command=_on_fs)
            fs_sl.grid(row=0, column=3, sticky="ew", padx=2)

            def _on_fs_spin(*_a):
                try:
                    iv = max(14, min(120, int(float(fs_spin_var.get().strip()))))
                    item["font_size"] = iv
                    fs_sl.set(iv)
                    self._overlay_pil_cache.clear()
                    self._render_player_studio_canvas()
                except ValueError:
                    pass

            sp_fs = tk.Spinbox(fs_row, from_=14, to=120, increment=2, textvariable=fs_spin_var, width=4, font=("Consolas", 8, "bold"), command=_on_fs_spin)
            sp_fs.grid(row=0, column=4)
            sp_fs.bind("<Return>", _on_fs_spin)

            # Colors Row + Opacity/Rotation Spinboxes
            col_row = ttk.Frame(self.item_prop_card)
            col_row.grid(row=5, column=0, columnspan=2, sticky="ew", pady=1)
            for ci in (1, 3, 5):
                col_row.columnconfigure(ci, weight=1)

            fg_choices = [(k, info["label_ar"] if is_ar else info["label_en"]) for k, info in BANNER_TEXT_COLORS.items()]
            fg_map = {d: k for k, d in fg_choices}
            fg_rev = {k: d for k, d in fg_choices}
            fg_var = tk.StringVar(value=fg_rev.get(item.get("text_color", "white"), fg_choices[0][1]))
            ttk.Label(col_row, text="لون:" if is_ar else "FG:").grid(row=0, column=0, sticky="w")
            fg_cb = ttk.Combobox(col_row, textvariable=fg_var, values=[c[1] for c in fg_choices], state="readonly", width=7)
            fg_cb.grid(row=0, column=1, sticky="ew", padx=(2, 4))
            fg_cb.bind("<<ComboboxSelected>>", lambda _e: (item.update({"text_color": fg_map.get(fg_var.get(), "white")}), self._overlay_pil_cache.clear(), self._save_settings(), self._render_player_studio_canvas()))

            bg_choices = [(k, info["label_ar"] if is_ar else info["label_en"]) for k, info in BANNER_BG_COLORS.items()]
            bg_map = {d: k for k, d in bg_choices}
            bg_rev = {k: d for k, d in bg_choices}
            bg_var = tk.StringVar(value=bg_rev.get(item.get("bg_color", "black"), bg_choices[0][1]))
            ttk.Label(col_row, text="خلفية:" if is_ar else "BG:").grid(row=0, column=2, sticky="w")
            bg_cb = ttk.Combobox(col_row, textvariable=bg_var, values=[c[1] for c in bg_choices], state="readonly", width=7)
            bg_cb.grid(row=0, column=3, sticky="ew", padx=(2, 4))
            bg_cb.bind("<<ComboboxSelected>>", lambda _e: (item.update({"bg_color": bg_map.get(bg_var.get(), "black")}), self._overlay_pil_cache.clear(), self._save_settings(), self._render_player_studio_canvas()))

            t_rot_var = tk.StringVar(value=f"{int(round(float(item.get('rotation', 0.0))))}")
            ttk.Label(col_row, text="°").grid(row=0, column=4, sticky="w")
            sp_tr = tk.Spinbox(
                col_row, from_=-180, to=180, increment=5, textvariable=t_rot_var, width=4, font=("Consolas", 8),
                command=lambda: (item.update({"rotation": round(max(-180.0, min(180.0, float(t_rot_var.get() or 0))), 1)}), self._overlay_pil_cache.clear(), self._render_player_studio_canvas()),
            )
            sp_tr.grid(row=0, column=5, sticky="ew")
            sp_tr.bind("<Return>", lambda _e: (item.update({"rotation": round(max(-180.0, min(180.0, float(t_rot_var.get() or 0))), 1)}), self._overlay_pil_cache.clear(), self._render_player_studio_canvas()))

            self._build_overlay_timing_controls(self.item_prop_card, 6, "V3", item, t_idx)
            return

        # ---------------- V2: Icons, Badges & Custom Images ----------------
        if sel and sel[0] == "V2" and 0 <= sel[1] < len(self.nle_project.media_items):
            m_idx = sel[1]
            item = self.nle_project.media_items[m_idx]
            is_img = (item.get("type") == "image")
            title_lbl = (f"🖼️ خصائص الصورة #{m_idx + 1}" if is_img else f"⭐ خصائص الأيقونة #{m_idx + 1}") if is_ar else (f"🖼️ Image #{m_idx + 1}" if is_img else f"⭐ Icon #{m_idx + 1}")
            self.item_prop_card.configure(text=title_lbl)

            top_r = ttk.Frame(self.item_prop_card)
            top_r.grid(row=1, column=0, columnspan=2, sticky="ew", pady=1)
            top_r.columnconfigure(1, weight=1)

            if is_img:
                p_name = Path(item.get("path", "Image")).name[:26]
                ttk.Label(top_r, text=p_name, foreground="#58a6ff").grid(row=0, column=0, sticky="w", padx=(0, 6))

                def _chg_ov_img():
                    ch = filedialog.askopenfilename(parent=self, filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp")])
                    if ch:
                        item["path"] = ch
                        self._overlay_pil_cache.clear()
                        if hasattr(self, "davinci_timeline"):
                            self.davinci_timeline.redraw()
                        self._save_settings()
                        self._render_player_studio_canvas()
                        self._update_inspector_properties()

                ttk.Button(top_r, text="📁 تغيير الصورة" if is_ar else "📁 Change Image", command=_chg_ov_img, style="Player.TButton").grid(row=0, column=1, sticky="ew")
            else:
                def _chg_icon():
                    dlg = IconPickerDialog(self, initial_key=item.get("icon_key", "subscribe_ar"), initial_text=item.get("text", ""))
                    self.wait_window(dlg)
                    if dlg.result:
                        item["icon_key"] = dlg.result["icon_key"]
                        item["text"] = dlg.result.get("text", "")
                        self._overlay_pil_cache.clear()
                        if hasattr(self, "davinci_timeline"):
                            self.davinci_timeline.redraw()
                        self._save_settings()
                        self._render_player_studio_canvas()
                        self._update_inspector_properties()

                ttk.Button(top_r, text="⭐ تغيير الأيقونة" if is_ar else "⭐ Change Icon", command=_chg_icon, style="Player.TButton").grid(row=0, column=0, padx=(0, 4))
                btxt_var = tk.StringVar(value=item.get("text", ""))

                def _on_btxt(*_a):
                    item["text"] = btxt_var.get()
                    self._overlay_pil_cache.clear()
                    self._render_player_studio_canvas()

                btxt_var.trace_add("write", _on_btxt)
                bent = ttk.Entry(top_r, textvariable=btxt_var)
                bent.grid(row=0, column=1, sticky="ew")
                self._attach_entry_context_menu(bent)

            self._build_overlay_xy_numeric_row(self.item_prop_card, 2, "V2", item, m_idx)

            sc_r = ttk.Frame(self.item_prop_card)
            sc_r.grid(row=3, column=0, columnspan=2, sticky="ew", pady=1)
            sc_r.columnconfigure(1, weight=1)
            m_sc = float(item.get("scale", 0.22))
            msc_spin_var = tk.StringVar(value=f"{int(round(m_sc * 100))}")
            ttk.Label(sc_r, text="الحجم%:" if is_ar else "Scale%:").grid(row=0, column=0, sticky="w", padx=(0, 4))

            def _on_msc(v):
                fv = round(float(v), 3)
                item["scale"] = fv
                msc_spin_var.set(f"{int(round(fv * 100))}")
                self._overlay_pil_cache.clear()
                self._render_player_studio_canvas()

            msc_sl = ttk.Scale(sc_r, from_=0.05, to=0.95, value=m_sc, orient="horizontal", command=_on_msc)
            msc_sl.grid(row=0, column=1, sticky="ew")

            def _on_msc_spin(*_a):
                try:
                    fv = max(0.05, min(0.95, float(msc_spin_var.get().strip()) / 100.0))
                    item["scale"] = round(fv, 3)
                    msc_sl.set(fv)
                    self._overlay_pil_cache.clear()
                    self._render_player_studio_canvas()
                except ValueError:
                    pass

            sp_msc = tk.Spinbox(sc_r, from_=5, to=95, increment=2, textvariable=msc_spin_var, width=4, font=("Consolas", 8, "bold"), command=_on_msc_spin)
            sp_msc.grid(row=0, column=2, padx=(4, 0))
            sp_msc.bind("<Return>", _on_msc_spin)

            or_r = ttk.Frame(self.item_prop_card)
            or_r.grid(row=4, column=0, columnspan=2, sticky="ew", pady=1)
            or_r.columnconfigure(1, weight=1)
            or_r.columnconfigure(3, weight=1)
            m_op_var = tk.StringVar(value=f"{int(round(float(item.get('opacity', 1.0)) * 100))}")
            m_rot_var = tk.StringVar(value=f"{int(round(float(item.get('rotation', 0.0))))}")

            def _apply_m_or(*_a):
                try:
                    item["opacity"] = round(max(0.10, min(1.0, float(m_op_var.get().strip()) / 100.0)), 2)
                    item["rotation"] = round(max(-180.0, min(180.0, float(m_rot_var.get().strip()))), 1)
                    self._overlay_pil_cache.clear()
                    self._render_player_studio_canvas()
                except ValueError:
                    pass

            ttk.Label(or_r, text="شفافية%:" if is_ar else "Op%:").grid(row=0, column=0, sticky="w")
            sp_mop = tk.Spinbox(or_r, from_=10, to=100, increment=5, textvariable=m_op_var, width=5, font=("Consolas", 8), command=_apply_m_or)
            sp_mop.grid(row=0, column=1, sticky="ew", padx=(2, 6))
            sp_mop.bind("<Return>", _apply_m_or)
            ttk.Label(or_r, text="دوران°:" if is_ar else "Rot°:").grid(row=0, column=2, sticky="w")
            sp_mrt = tk.Spinbox(or_r, from_=-180, to=180, increment=5, textvariable=m_rot_var, width=5, font=("Consolas", 8), command=_apply_m_or)
            sp_mrt.grid(row=0, column=3, sticky="ew", padx=(2, 0))
            sp_mrt.bind("<Return>", _apply_m_or)

            self._build_overlay_timing_controls(self.item_prop_card, 5, "V2", item, m_idx)
            return

        # ---------------- A2: Audio Item Properties ----------------
        if sel and (sel[0] == "A2" or str(sel[0]).startswith("AUD")) and 0 <= sel[1] < len(self.nle_project.audio_items):
            a_idx = sel[1]
            item = self.nle_project.audio_items[a_idx]
            self.item_prop_card.configure(text=f"🎵 خصائص ملف الصوت #{a_idx + 1}" if is_ar else f"🎵 Audio File #{a_idx + 1} Properties")

            # Row 1: File name & Change file button
            p_val = str(item.get("audio_path", "")).strip()
            p_name = Path(p_val).name if p_val else ("بدون ملف" if is_ar else "No file")
            fn_row = ttk.Frame(self.item_prop_card)
            fn_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 4))
            fn_row.columnconfigure(0, weight=1)

            lbl_fn = ttk.Label(fn_row, text=f"📁 {p_name}", font=("Segoe UI", 8, "bold"), foreground="#79c0ff", wraplength=230)
            lbl_fn.grid(row=0, column=0, sticky="w")

            def _replace_audio_file():
                chosen = filedialog.askopenfilename(
                    title="تغيير الملف الصوتي" if is_ar else "Replace Audio File",
                    filetypes=[("Audio Files", "*.mp3 *.wav *.aac *.m4a *.flac *.ogg *.wma *.opus"), ("All Files", "*.*")],
                )
                if chosen:
                    self.nle_project.push_undo()
                    item["audio_path"] = chosen
                    lbl_fn.configure(text=f"📁 {Path(chosen).name}")
                    if hasattr(self, "davinci_timeline"):
                        self.davinci_timeline.redraw()
                    self._on_nle_timeline_modified()

            ttk.Button(fn_row, text="تغيير" if is_ar else "Browse", command=_replace_audio_file, style="Player.TButton", width=7).grid(row=0, column=1, sticky="e", padx=(4, 0))

            # Row 2: Volume Slider & Spinbox
            vol_row = ttk.Frame(self.item_prop_card)
            vol_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=2)
            vol_row.columnconfigure(1, weight=1)

            cur_vol = float(item.get("volume", 1.0))
            vol_spin_var = tk.StringVar(value=f"{int(round(cur_vol * 100))}")

            ttk.Label(vol_row, text="الصوت%:" if is_ar else "Vol%:").grid(row=0, column=0, sticky="w", padx=(0, 4))

            def _on_vol_slider(v):
                fv = round(float(v), 2)
                item["volume"] = fv
                vol_spin_var.set(f"{int(round(fv * 100))}")
                if hasattr(self, "davinci_timeline"):
                    self.davinci_timeline.redraw()
                if hasattr(self, "aux_audio_player") and self.aux_audio_player:
                    base_v = float(self.volume_var.get()) if hasattr(self, "volume_var") else 100.0
                    self.aux_audio_player.audio_set_volume(max(0, min(200, int(round(base_v * fv)))))
                self._refresh_master_export_summary()

            vol_slider = ttk.Scale(vol_row, from_=0.0, to=2.0, value=cur_vol, orient="horizontal", command=_on_vol_slider)
            vol_slider.grid(row=0, column=1, sticky="ew")

            def _on_vol_spin(*_a):
                try:
                    pct = max(0, min(200, int(vol_spin_var.get().strip())))
                    fv = round(pct / 100.0, 2)
                    item["volume"] = fv
                    vol_slider.set(fv)
                    if hasattr(self, "davinci_timeline"):
                        self.davinci_timeline.redraw()
                    self._refresh_master_export_summary()
                except Exception:
                    pass

            sp = tk.Spinbox(vol_row, from_=0, to=200, increment=5, textvariable=vol_spin_var, width=5, font=("Consolas", 8, "bold"), command=_on_vol_spin)
            sp.grid(row=0, column=2, sticky="e", padx=(4, 0))
            sp.bind("<Return>", _on_vol_spin)

            # Row 3: Mute Checkbox
            mut_row = ttk.Frame(self.item_prop_card)
            mut_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=2)

            mut_var = tk.BooleanVar(value=bool(item.get("muted", False)))
            def _on_mut():
                item["muted"] = bool(mut_var.get())
                if hasattr(self, "davinci_timeline"):
                    self.davinci_timeline.redraw()
                if hasattr(self, "aux_audio_player") and self.aux_audio_player and item["muted"]:
                    self.aux_audio_player.pause()
                self._refresh_master_export_summary()

            ttk.Checkbutton(
                mut_row,
                text="🔇 كتم هذا الملف الصوتي" if is_ar else "🔇 Mute this audio item",
                variable=mut_var,
                command=_on_mut,
            ).grid(row=0, column=0, sticky="w")

            # Row 4: Timing row (Start sec & Duration sec)
            self._build_overlay_timing_controls(self.item_prop_card, 4, "A2", item, a_idx)

            # Row 5: Action buttons (Duplicate, Delete)
            act_f = ttk.Frame(self.item_prop_card)
            act_f.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(6, 2))
            act_f.columnconfigure(0, weight=1)
            act_f.columnconfigure(1, weight=1)

            def _dup_aud():
                self.nle_project.push_undo()
                new_it = copy.deepcopy(item)
                new_it["id"] = self.nle_project.next_id("a2")
                new_it["start_sec"] = float(item.get("end_sec", 0.0))
                new_it["end_sec"] = new_it["start_sec"] + float(item.get("duration", 5.0))
                self.nle_project.audio_items.append(new_it)
                self.player_canvas_selected = ("A2", len(self.nle_project.audio_items) - 1)
                self._on_nle_timeline_modified()
                self._update_inspector_properties()

            def _del_aud():
                self.nle_project.push_undo()
                if 0 <= a_idx < len(self.nle_project.audio_items):
                    self.nle_project.audio_items.pop(a_idx)
                self.player_canvas_selected = None
                self._on_nle_timeline_modified()
                self._show_inspector_context("video")

            ttk.Button(act_f, text="📋 تكرار" if is_ar else "📋 Duplicate", command=_dup_aud, style="Player.TButton").grid(row=0, column=0, sticky="ew", padx=(0, 2))
            ttk.Button(act_f, text="🗑️ حذف" if is_ar else "🗑️ Delete", command=_del_aud, style="Player.TButton").grid(row=0, column=1, sticky="ew", padx=(2, 0))
            return

        # ---------------- Default: Active Layers Summary & Quick Select ----------------
        self.item_prop_card.configure(
            text="📚 طبقات وعناصر التايم لاين الحالية" if is_ar else "📚 Active Timeline Layers"
        )
        total_ov = len(self.nle_project.logo_items) + len(self.nle_project.text_items) + len(self.nle_project.media_items) + len(self.nle_project.audio_items)
        if total_ov == 0:
            msg = (
                "💡 أضف (نص، أيقونة، صورة، أو لوجو) من الأزرار بالأعلى أو زر [+] في كل مسار،\n"
                "ثم اسحب العنصر بالماوس أو تحكم فيه بالأرقام هنا."
                if is_ar
                else "💡 Add a Text, Pro Icon, Image, or Logo above or via [+] on any track,\n"
                     "then drag on Viewer or adjust numerically here."
            )
            ttk.Label(self.item_prop_card, text=msg, font=("Segoe UI", 8), foreground="#8b949e", justify="center", wraplength=330).grid(
                row=1, column=0, columnspan=2, pady=10, sticky="ew"
            )
        else:
            list_f = ttk.Frame(self.item_prop_card)
            list_f.grid(row=1, column=0, columnspan=2, sticky="nsew")
            list_f.columnconfigure(0, weight=1)
            r_i = 0
            for t_key, badge_ico, items in (
                ("V4", "🛡️", self.nle_project.logo_items),
                ("V3", "📝", self.nle_project.text_items),
                ("V2", "⭐", self.nle_project.media_items),
                ("A2", "🎵", self.nle_project.audio_items),
            ):
                for idx, it in enumerate(items):
                    if r_i >= 8:
                        break
                    if t_key == "V3":
                        nm = it.get("text", "Text")[:24]
                    elif t_key == "V4":
                        nm = Path(it.get("path", "Logo")).name[:24]
                    elif t_key == "A2":
                        nm = Path(it.get("audio_path", "Audio")).name[:24]
                    else:
                        nm = Path(it.get("path", "Image")).name[:24] if it.get("type") == "image" else ICON_PRESETS.get(it.get("icon_key", ""), {}).get("name_ar" if is_ar else "name_en", "Icon")
                    rng = ("طوال الفيديو" if is_ar else "Full") if it.get("full_duration") else f"{float(it.get('start_sec', 0)):.1f}s–{float(it.get('end_sec', 5)):.1f}s"
                    btn = ttk.Button(
                        list_f,
                        text=f"{badge_ico} [{t_key}] {nm}  ({rng})",
                        style="Player.TButton",
                        command=lambda tk_r=(t_key, idx): self._select_overlay_from_inspector(tk_r),
                    )
                    btn.grid(row=r_i, column=0, sticky="ew", pady=1)
                    r_i += 1

    def _select_overlay_from_inspector(self, ref_tuple):
        self.player_canvas_selected = ref_tuple
        tlist = self.nle_project.get_track_list(ref_tuple[0])
        if 0 <= ref_tuple[1] < len(tlist):
            it = tlist[ref_tuple[1]]
            if not it.get("full_duration", False):
                s = float(it.get("start_sec", 0.0))
                if not (s <= self.nle_playhead_sec <= float(it.get("end_sec", s + 5.0))):
                    self._on_nle_timeline_scrub(s + 0.05, True)
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.selected_ref = ref_tuple
            self.davinci_timeline.redraw()
        self._show_inspector_context("overlay")
        self._render_player_studio_canvas()

    # -------------------------------------------------------------------------
    # WYSIWYG DaVinci Studio Viewer Canvas + Direct Pan/Zoom/Overlay Gizmos
    # -------------------------------------------------------------------------
    def _get_live_subtitle_at(self, tl_sec: float) -> str:
        """Returns active subtitle text at edited timeline second tl_sec if available."""
        segs = None
        if hasattr(self, "caption_current_result") and self.caption_current_result:
            segs = self.caption_current_result.get("segments")
        if segs:
            _c_idx, _clip, src_sec = self.nle_project.timeline_to_source(tl_sec) if hasattr(self, "nle_project") else (0, None, tl_sec)
            for s in segs:
                if float(s.get("start", 0.0)) <= src_sec <= float(s.get("end", 0.0)):
                    return str(s.get("text", "")).strip()
        return ""










    def _quick_delete_selected_text(self):
        sel_norm = self._normalize_selection_ref(self.player_canvas_selected)
        if sel_norm and sel_norm[0] in ("V2", "V3", "V4"):
            self.nle_project.push_undo()
            tlist = self.nle_project.get_track_list(sel_norm[0])
            if 0 <= sel_norm[1] < len(tlist):
                tlist.pop(sel_norm[1])
            self.player_canvas_selected = None
            if hasattr(self, "davinci_timeline"):
                self.davinci_timeline.selected_ref = None
                self.davinci_timeline.redraw()
            self._on_nle_timeline_modified()

    def _quick_choose_logo(self):
        self._nle_add_element("logo", self.nle_playhead_sec)

    def _reset_branding_positions(self):
        self.nle_project.push_undo()
        for l_it in self.nle_project.logo_items:
            l_it["x"] = 0.80
            l_it["y"] = 0.04
            l_it["scale"] = 0.16
            l_it["rotation"] = 0.0
        for i, it in enumerate(self.nle_project.text_items):
            it["x"] = 0.50
            it["y"] = min(0.85, 0.10 + i * 0.12)
            it["rotation"] = 0.0
        for i, it in enumerate(self.nle_project.media_items):
            it["x"] = 0.50
            it["y"] = min(0.85, 0.78 - i * 0.12)
            it["rotation"] = 0.0
        self._save_settings()
        self._refresh_master_export_summary()
        self._render_player_studio_canvas()
        self._update_inspector_properties()

    def _attach_vlc_subtitles_if_available(self):
        if not self.media_player or not hasattr(self, "trim_burn_subs_var") or not self.trim_burn_subs_var.get():
            return
        try:
            srt_path = None
            if hasattr(self, "caption_current_result") and self.caption_current_result and (self.caption_current_result.get("srt") or self.caption_current_result.get("segments")):
                srt_content = self.caption_current_result.get("srt") or convert.generate_srt_content(self.caption_current_result.get("segments", []))
                cache_dir = getattr(convert, "CACHE_DIR", convert.APP_DIR / ".cache")
                cache_dir.mkdir(parents=True, exist_ok=True)
                sub_tmp = cache_dir / "active_player_sub.srt"
                sub_tmp.write_text(srt_content, encoding="utf-8-sig")
                srt_path = sub_tmp
            elif self.input_path and self.input_path.with_suffix(".srt").exists():
                srt_path = self.input_path.with_suffix(".srt")

            if srt_path and srt_path.is_file():
                self.media_player.add_slave(vlc.MediaSlaveType.subtitle, srt_path.as_uri(), True)
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Transport Seek & Multi-Clip Real-Time Playback Scheduler
    # -------------------------------------------------------------------------

    def seek_relative(self, seconds):
        if not self._single_media_file_selected():
            return
        tot = max(0.1, self._edited_total_duration() or float(self.media_duration or 0.0))
        new_tl = max(0.0, min(max(0.0, tot - 0.05), self._current_timeline_seconds() + float(seconds)))
        self.nle_playhead_sec = new_tl
        self.timeline_var.set(new_tl)
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.set_playhead(new_tl, auto_follow=True)
        c_idx, clip, src_sec = self.nle_project.timeline_to_source(new_tl) if hasattr(self, "nle_project") else (0, None, new_tl)
        self.active_playback_clip_idx = c_idx
        if clip is None:
            self._in_gap_playback = True
            self._gap_last_wall_ts = time.monotonic()
            if self.media_player and self.media_player.is_playing():
                self.media_player.pause()
        else:
            self._in_gap_playback = False
            if self.media_player and self.media_player.get_state() not in {vlc.State.Ended, vlc.State.Error, vlc.State.Stopped}:
                self.media_player.set_time(int(src_sec * 1000))
                self._apply_active_clip_playback_fx(clip)
        self._refresh_timeline_text()
        if not self._is_playing():
            self._show_studio_canvas()
            if clip is None:
                self._render_player_studio_canvas()
            else:
                self._request_fast_preview_frame(src_sec, force=True)

    def seek_to_start(self):
        self._in_gap_playback = False
        self._gap_last_wall_ts = 0.0
        self.nle_playhead_sec = 0.0
        self.timeline_var.set(0.0)
        self.active_playback_clip_idx = 0
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.set_playhead(0.0, auto_follow=True)
        _idx, clip, src_sec = self.nle_project.timeline_to_source(0.0) if hasattr(self, "nle_project") else (0, None, 0.0)
        if clip is None:
            self._in_gap_playback = True
            self._gap_last_wall_ts = time.monotonic()
            if self.media_player and self.media_player.is_playing():
                self.media_player.pause()
        else:
            if self.media_player and self.media_player.get_state() not in {vlc.State.Ended, vlc.State.Error, vlc.State.Stopped}:
                self.media_player.set_time(int(src_sec * 1000))
                self._apply_active_clip_playback_fx(clip)
        self._refresh_timeline_text()
        if not self._is_playing():
            self._show_studio_canvas()
            if clip is None:
                self._render_player_studio_canvas()
            else:
                self._request_fast_preview_frame(max(0.05, src_sec), force=True)

    def seek_to_end(self):
        self._in_gap_playback = False
        self._gap_last_wall_ts = 0.0
        if not self._single_media_file_selected():
            return
        tot = max(0.1, self._edited_total_duration() or float(self.media_duration or 0.0))
        end_tl = max(0.0, tot - 0.15)
        self.nle_playhead_sec = end_tl
        self.timeline_var.set(end_tl)
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.set_playhead(end_tl, auto_follow=True)
        c_idx, clip, src_sec = self.nle_project.timeline_to_source(end_tl) if hasattr(self, "nle_project") else (0, None, end_tl)
        self.active_playback_clip_idx = c_idx
        if clip is None:
            self._in_gap_playback = True
            self._gap_last_wall_ts = time.monotonic()
            if self.media_player and self.media_player.is_playing():
                self.media_player.pause()
        else:
            if self.media_player and self.media_player.get_state() not in {vlc.State.Ended, vlc.State.Error, vlc.State.Stopped}:
                self.media_player.set_time(int(src_sec * 1000))
                self._apply_active_clip_playback_fx(clip)
        self._refresh_timeline_text()
        if not self._is_playing():
            self._show_studio_canvas()
            if clip is None:
                self._render_player_studio_canvas()
            else:
                self._request_fast_preview_frame(max(0.05, src_sec), force=True)

    def seek_timeline_to(self, target_sec):
        if not self._single_media_file_selected():
            return
        tot = max(0.1, self._edited_total_duration() or float(self.media_duration or 0.0))
        new_tl = max(0.0, min(max(0.0, tot - 0.05), float(target_sec)))
        self.nle_playhead_sec = new_tl
        self.timeline_var.set(new_tl)
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.set_playhead(new_tl, auto_follow=True)
        c_idx, clip, src_sec = self.nle_project.timeline_to_source(new_tl) if hasattr(self, "nle_project") else (0, None, new_tl)
        self.active_playback_clip_idx = c_idx
        if clip is None:
            self._in_gap_playback = True
            self._gap_last_wall_ts = time.monotonic()
            if self.media_player and self.media_player.is_playing():
                self.media_player.pause()
        else:
            self._in_gap_playback = False
            if self.media_player and self.media_player.get_state() not in {vlc.State.Ended, vlc.State.Error, vlc.State.Stopped}:
                self.media_player.set_time(int(src_sec * 1000))
                self._apply_active_clip_playback_fx(clip)
        self._refresh_timeline_text()
        if not self._is_playing():
            self._show_studio_canvas()
            if clip is None:
                self._render_player_studio_canvas()
            else:
                self._request_fast_preview_frame(src_sec, force=True)
        if getattr(self, "_theater_dialog", None) and self._theater_dialog.winfo_exists():
            self._theater_dialog.refresh_preview()

    def _sync_render_playhead_safe(self, tl_sec: float):
        """Zero-lag timeline playhead and timecode visual sync during video export."""
        try:
            sec = max(0.0, float(tl_sec or 0.0))
            if hasattr(self, "davinci_timeline") and self.davinci_timeline.winfo_exists():
                self.davinci_timeline.set_playhead(sec, auto_follow=True)
            if hasattr(self, "timeline_var"):
                self.timeline_var.set(sec)
            if hasattr(self, "_refresh_timeline_text"):
                self._refresh_timeline_text()
            if hasattr(self, "_draw_player_visual_timeline"):
                self._draw_player_visual_timeline()
        except Exception:
            pass



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
        now = time.monotonic()
        self.run_started_at = now
        self._completed_file_durations = []
        self._current_file_start_time = now
        self._last_completed_file_index = -1
        self._progress_samples = []
        self._smoothed_eta_seconds = None

    def cancel_current_operation(self):
        has_worker = bool(self.worker and self.worker.is_alive())
        has_caption = bool(hasattr(self, "caption_thread") and self.caption_thread and self.caption_thread.is_alive())
        if not has_worker and not has_caption:
            return
        if has_caption:
            self.cancel_embedded_caption()
        if has_worker:
            self.cancel_event.set()
            try:
                convert.stop_all_active_processes()
            except Exception:
                pass
            self.status_var.set(self.text("canceling"))
            self._append_log(self.text("canceling") + "\n")

    def _operation_canceled(self):
        return self.cancel_event.is_set()

    def _restore_operation_buttons(self):
        self.run_button.configure(command=self.start_conversion)
        self.compress_video_button.configure(command=self.start_video_compression)
        self.boost_button.configure(command=self.start_boost_volume)
        self.trim_button.configure(command=self.start_trim)
        self.fetch_youtube_button.configure(command=self.start_fetch_youtube_formats)
        self.download_youtube_button.configure(command=self.start_youtube_download)
        self.caption_start_button.configure(command=self.start_embedded_caption)
        self.run_button.configure(text=self.text("run"))
        self.compress_video_button.configure(text=self.text("compress_videos"))
        self.boost_button.configure(text=self.text("boost_save"))
        self.trim_button.configure(text=self.text("trim_selected"))
        self.fetch_youtube_button.configure(text=self.text("fetch_qualities"))
        self.download_youtube_button.configure(text=self.text("download_youtube"))
        self.caption_start_button.configure(text=self.text("caption_start"))
        if hasattr(self, "silence_export_button"):
            self.silence_export_button.configure(command=self.start_silence_export)
            self.silence_export_button.configure(text=self.text("silence_export_btn"))
        if hasattr(self, "silence_analyze_button"):
            self.silence_analyze_button.configure(command=self.start_analyze_silences)
            self.silence_analyze_button.configure(text=self.text("silence_analyze_btn"))
        if hasattr(self, "btn_master_export"):
            self.btn_master_export.configure(command=self.start_master_export)
            self.btn_master_export.configure(text=self.text("master_export_btn"))
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

    def start_video_conversion(self):
        if self.worker and self.worker.is_alive():
            return
        video_files = self.video_files()
        if not self.input_path or not video_files:
            messagebox.showwarning(self.text("app_title"), self.text("no_videos"))
            return

        video_format = self.selected_video_format()
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
                self.selected_output_ext(),
                self.quality_var.get(),
                self.skip_existing_var.get(),
                False,
                None,
                None,
                "Off",
                "convert_video",
                video_compression,
                video_resolution,
                True,
                video_format,
            ),
            daemon=True,
        )
        self.worker.start()

    start_video_compression = start_video_conversion

    def _on_trim_aspect_changed(self, _e=None):
        disp = self.trim_aspect_combo_var.get()
        ratio = self.trim_aspect_map.get(disp, "original")
        self.trim_aspect_var.set(ratio)
        self.video_branding_config["aspect_ratio"] = ratio
        if ratio in ("9:16", "4:5", "1:1") and self.video_branding_config.get("fit_mode") == "pad":
            self.video_branding_config["fit_mode"] = "crop"
            if hasattr(self, "fit_mode_combo_var") and hasattr(self, "fit_mode_rev"):
                f_disp = self.fit_mode_rev.get("crop")
                if f_disp:
                    self.fit_mode_combo_var.set(f_disp)
        self._set_effective_video_transform()
        self._sync_transform_sliders_from_state()
        self._save_settings()
        self._refresh_master_export_summary()
        self.apply_video_aspect_ratio()
        self._show_studio_canvas()
        self._sync_live_video_overlay()

    def _on_trim_branding_toggle(self):
        self.video_branding_config["burn_subtitles"] = bool(self.trim_burn_subs_var.get())
        self.video_branding_config["logo_enabled"] = bool(self.trim_logo_var.get())
        self.video_branding_config["title_enabled"] = bool(self.trim_title_var.get())
        if hasattr(self, "trim_remove_silence_var"):
            self.video_branding_config["remove_silence"] = bool(self.trim_remove_silence_var.get())
        if hasattr(self, "trim_color_var"):
            if not isinstance(self.video_branding_config.get("color_config"), dict):
                self.video_branding_config["color_config"] = {}
            self.video_branding_config["color_config"]["enabled"] = bool(self.trim_color_var.get())
        self._save_settings()
        self._refresh_master_export_summary()
        self.apply_video_color_adjustments()
        self._sync_live_video_overlay()
        self._update_inspector_properties()



    def open_video_branding_dialog(self):
        self._save_settings()
        dlg = VideoBrandingDialog(self)
        self._apply_theme_to_toplevel(dlg)
        dlg.wait_window()
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.redraw()
        self._sync_transform_sliders_from_state()
        self._update_inspector_properties()
        self._refresh_master_export_summary()
        self._render_player_studio_canvas()

    def open_video_color_dialog(self):
        dlg = VideoColorDialog(self)
        self._apply_theme_to_toplevel(dlg)
        dlg.wait_window()
        self._refresh_master_export_summary()
        self._render_player_studio_canvas()

    def open_shortcuts_guide_dialog(self):
        """Opens the comprehensive shortcuts & user manual guide modal dialog."""
        from ui_dialogs.shortcuts_guide_dialog import ShortcutsGuideDialog
        is_ar = (self.language_var.get() == "العربية")
        dlg = ShortcutsGuideDialog(self, is_ar=is_ar)
        self._apply_theme_to_toplevel(dlg)

    def open_video_transitions_dialog(self, target_cut_index=None):
        """Opens the 46+ transitions library modal dialog."""
        try:
            from ui_dialogs.video_transition_dialog import VideoTransitionDialog
            dlg = VideoTransitionDialog(self, target_cut_index=target_cut_index)
            self._apply_theme_to_toplevel(dlg)
        except Exception as e:
            print(f"Error opening transitions dialog: {e}")

    # -------------------------------------------------------------------------
    # Window State & Fullscreen (Clean Standard Windows Behavior)
    # -------------------------------------------------------------------------
    def _init_app_window_mode(self):
        try:
            if self.wm_state() != "iconic":
                self.state("zoomed")
                self._reapply_dark_titlebar()
        except Exception:
            pass

    def toggle_app_fullscreen(self):
        th_dlg = getattr(self, "_theater_dialog", None)
        if th_dlg is not None and th_dlg.winfo_exists():
            self.toggle_video_size()
            return
        try:
            is_fs = bool(self.attributes("-fullscreen"))
            new_fs = not is_fs
            self.attributes("-fullscreen", new_fs)
            if not new_fs:
                self.state("zoomed")
                self._reapply_dark_titlebar()
        except Exception:
            pass

    def _handle_app_escape(self):
        th_dlg = getattr(self, "_theater_dialog", None)
        if th_dlg is not None and th_dlg.winfo_exists():
            self._exit_video_fullscreen()
        elif bool(self.attributes("-fullscreen")):
            self.toggle_app_fullscreen()

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

        is_video = convert.has_video_stream(self.input_path) or (self.input_path.suffix.lower() in convert.VIDEO_EXTS)
        extract_audio = self.trim_extract_audio_var.get()

        if is_video and not extract_audio:
            keep_original_format = True
            output_ext = self.input_path.suffix.lower()
        elif is_video and extract_audio:
            keep_original_format = False
            output_ext = ".mp3"
        else:
            keep_original_format = not extract_audio
            output_ext = ".mp3" if extract_audio else self.input_path.suffix.lower()

        aspect_ratio = "original"
        fit_mode = "crop"
        video_transform = None
        color_cfg = None
        logo_cfg = None
        logo_items = None
        title_cfg = None
        media_overlays = None
        sub_cfg = None
        silence_cfg = self._build_silence_config()

        if is_video and not extract_audio:
            try:
                configs = self._build_branding_configs(remap_subs_to_nle=False)
            except Exception as exc:
                messagebox.showerror(self.text("app_title"), f"Error preparing branding: {exc}")
                return
            if configs is None:
                return
            aspect_ratio = configs["aspect_ratio"]
            fit_mode = configs["fit_mode"]
            video_transform = configs["video_transform"]
            color_cfg = configs["color_cfg"]
            logo_cfg = configs["logo_cfg"]
            logo_items = configs["logo_items"]
            title_cfg = configs["title_cfg"]
            media_overlays = configs["media_overlays"]
            sub_cfg = configs["sub_cfg"]

        quality = self.quality_var.get()
        enhancement = self.selected_enhancement()
        self._clear_log()
        self._begin_operation("trim", self.trim_button)
        self._append_log(self.text("trimming") + "\n")
        self.status_var.set(self.text("trimming"))
        self._set_busy(True)
        self.progress.configure(mode="determinate", maximum=100, value=0)
        self.progress_var.set(self.text("progress_detail", current=0, total=1, file_percent=0, overall_percent=0, remaining_percent=100, elapsed="00:00", eta=self.text("estimating")))

        self.worker = threading.Thread(
            target=self._run_trim,
            args=(
                start_time,
                end_time,
                output_ext,
                quality,
                keep_original_format,
                enhancement,
                aspect_ratio,
                fit_mode,
                color_cfg,
                logo_cfg,
                title_cfg,
                sub_cfg,
                silence_cfg,
                video_transform,
                media_overlays,
                logo_items,
            ),
            daemon=True,
        )
        self.worker.start()



    def open_caption_studio(self):
        dlg = CaptionStudioDialog(
            self,
            initial_source=self.input_path,
            initial_output_dir=self.output_dir,
            media_files=self.media_files,
        )
        self._apply_theme_to_toplevel(dlg)


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
        format_id = selected_format["format_id"] if selected_format else convert.YOUTUBE_AUDIO_FORMAT_ID
        format_has_audio = bool(selected_format and selected_format.get("has_audio"))
        self._clear_log()
        self._begin_operation("youtube_download", self.download_youtube_button)
        self._append_log(self.text("youtube_downloading") + "\n")
        self.status_var.set(self.text("youtube_downloading"))
        self._set_busy(True)
        self.progress.configure(mode="determinate", maximum=100, value=0)
        self.progress_var.set(self.text("progress_detail", current=0, total=1, file_percent=0, overall_percent=0, remaining_percent=100, elapsed="00:00", eta=self.text("estimating")))

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
            if self._operation_canceled() or "cancel" in str(exc).lower():
                self.messages.put("\n__CANCELED__")
            else:
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
        video_output_ext=".mp4",
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
                video_output_ext=video_output_ext,
                video_only=video_only,
                cancel_callback=self._operation_canceled,
            )
            self.messages.put("\n__DONE__")
        except convert.CancelledError:
            self.messages.put("\n__CANCELED__")
        except Exception as exc:
            if self._operation_canceled() or "cancel" in str(exc).lower():
                self.messages.put("\n__CANCELED__")
            else:
                self.messages.put(f"\nError: {exc}\n")
                self.messages.put("\n__FAILED__")
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def _run_trim(
        self,
        start_time,
        end_time,
        output_ext,
        quality,
        keep_original_format,
        enhancement,
        aspect_ratio="original",
        fit_mode="crop",
        color_config=None,
        logo_config=None,
        title_config=None,
        subtitle_config=None,
        silence_config=None,
        video_transform=None,
        media_overlays=None,
        logo_items=None,
    ):
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
                aspect_ratio=aspect_ratio,
                fit_mode=fit_mode,
                video_transform=video_transform,
                color_config=color_config,
                logo_config=logo_config,
                logo_items=logo_items,
                title_config=title_config,
                media_overlays=media_overlays,
                subtitle_config=subtitle_config,
                silence_config=silence_config,
            )
            if output_path:
                self.messages.put(f"Saved: {output_path}\n")
                self.messages.put("\n__DONE__")
            else:
                self.messages.put("\n__FAILED__")
        except convert.CancelledError:
            self.messages.put("\n__CANCELED__")
        except Exception as exc:
            if self._operation_canceled() or "cancel" in str(exc).lower():
                self.messages.put("\n__CANCELED__")
            else:
                self.messages.put(f"\nError: {exc}\n")
                self.messages.put("\n__FAILED__")
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def run_on_main_thread(self, fn):
        if hasattr(self, "messages"):
            self.messages.put(fn)
        else:
            try:
                self.after(0, fn)
            except Exception:
                pass

    def _drain_messages(self):
        try:
            while True:
                message = self.messages.get_nowait()
                if callable(message):
                    try:
                        message()
                    except Exception:
                        pass
                elif message == "\n__DONE__":
                    self._finish(self.text("done"))
                elif message == "\n__FETCH_DONE__":
                    self._finish_fetch_youtube_formats()
                elif message == "\n__CANCELED__":
                    self._finish(self.text("canceled"), canceled=True)
                elif message == "\n__FAILED__":
                    self._finish(self.text("failed"), failed=True)
                elif isinstance(message, tuple) and message[0] == "progress":
                    _, current, total, source_name, file_percent = message
                    now = time.monotonic()
                    if not hasattr(self, "_last_completed_file_index"):
                        self._last_completed_file_index = -1
                        self._completed_file_durations = []
                        self._current_file_start_time = now

                    if current > self._last_completed_file_index:
                        if self._last_completed_file_index >= 0:
                            f_dur = max(0.2, now - getattr(self, "_current_file_start_time", now))
                            self._completed_file_durations.append(f_dur)
                        self._current_file_start_time = now
                        self._last_completed_file_index = current

                    overall_units = min(total * 100, current * 100 + file_percent)
                    overall_percent = int((overall_units / max(total * 100, 1)) * 100)
                    remaining_percent = max(0, 100 - overall_percent)
                    eta = self._estimate_remaining_time(overall_units, total * 100, current=current, total=total, file_percent=file_percent)
                    elapsed = self._format_seconds(now - self.run_started_at) if self.run_started_at else "00:00"
                    self.progress.configure(maximum=max(total, 1) * 100, value=overall_units)
                    if source_name and current < total:
                        if total > 1:
                            self.progress_var.set(
                                self.text(
                                    "progress_detail_multi",
                                    current=current + 1,
                                    total=total,
                                    file_percent=file_percent,
                                    overall_percent=overall_percent,
                                    remaining_percent=remaining_percent,
                                    elapsed=elapsed,
                                    eta=eta,
                                )
                            )
                        else:
                            self.progress_var.set(
                                self.text(
                                    "progress_detail",
                                    file_percent=file_percent,
                                    overall_percent=overall_percent,
                                    remaining_percent=remaining_percent,
                                    elapsed=elapsed,
                                    eta=eta,
                                )
                            )
                        self.status_var.set(source_name)
                    else:
                        final_txt = self.text("processed_single") if total <= 1 else self.text("processed", current=current, total=total)
                        self.progress_var.set(final_txt)
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
        if hasattr(self, "btn_cancel_progress"):
            if busy:
                self.btn_cancel_progress.grid(row=0, column=2, padx=(8, 0), sticky="e")
            else:
                self.btn_cancel_progress.grid_remove()
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
        if hasattr(self, "btn_master_export") and (not busy or self.btn_master_export is not self.active_operation_button):
            is_vid = bool(self._single_media_file_selected() and self.input_path and (self.input_path.suffix.lower() in convert.VIDEO_EXTS or convert.has_video_stream(self.input_path)))
            self.btn_master_export.configure(state=widget_state if is_vid else "disabled")
        if hasattr(self, "silence_export_button") and (not busy or self.silence_export_button is not self.active_operation_button):
            self.silence_export_button.configure(state=widget_state if self.media_files else "disabled")
        if hasattr(self, "silence_analyze_button"):
            self.silence_analyze_button.configure(state=widget_state if self.media_files else "disabled")
        if not busy or self.compress_video_button is not self.active_operation_button:
            self.compress_video_button.configure(state=widget_state if self.video_files() else "disabled")
        if not busy or self.run_button is not self.active_operation_button:
            self.run_button.configure(state="disabled" if busy else self._run_button_state())
        if not busy or self.boost_button is not self.active_operation_button:
            self.boost_button.configure(state=widget_state if self.media_files else "disabled")
        if not busy or self.caption_start_button is not self.active_operation_button:
            self.caption_start_button.configure(state=widget_state if self.media_files else "disabled")
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
        self.video_format_combo.configure(state="readonly")
        self.video_compression_combo.configure(state="readonly")
        self.video_resolution_combo.configure(state="readonly")
        self.enhancement_combo.configure(state="readonly")
        if hasattr(self, "boost_enhancement_combo"):
            self.boost_enhancement_combo.configure(state="readonly")
        self.boost_output_format_combo.configure(state="readonly")
        self.caption_model_combo.configure(state="readonly")
        self.caption_lang_combo.configure(state="readonly")
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

    def _estimate_remaining_time(self, progress_units, total_units, current=0, total=1, file_percent=0):
        if not self.run_started_at or progress_units <= 0 or progress_units >= total_units:
            return self.text("estimating") if progress_units < total_units else "00:00"

        now = time.monotonic()
        elapsed_total = max(0.1, now - self.run_started_at)

        # Sliding window samples over the last 15 seconds
        if not hasattr(self, "_progress_samples") or self._progress_samples is None:
            self._progress_samples = []
        self._progress_samples.append((now, progress_units))
        self._progress_samples = [s for s in self._progress_samples if now - s[0] <= 15.0]

        sliding_rate = 0.0
        if len(self._progress_samples) >= 2:
            time_delta = self._progress_samples[-1][0] - self._progress_samples[0][0]
            units_delta = self._progress_samples[-1][1] - self._progress_samples[0][1]
            if time_delta > 0.8 and units_delta > 0:
                sliding_rate = units_delta / time_delta

        global_rate = progress_units / elapsed_total if elapsed_total > 0 else 0.0
        effective_rate = sliding_rate if sliding_rate > 0 else global_rate

        raw_remaining = 0.0
        if total > 1:
            completed_durs = getattr(self, "_completed_file_durations", [])
            remaining_files_after_cur = max(0, total - (current + 1))
            if completed_durs:
                avg_file_time = sum(completed_durs) / len(completed_durs)
                cur_frac_left = max(0.0, 1.0 - (file_percent / 100.0))
                cur_file_rem = cur_frac_left * avg_file_time
                if effective_rate > 0 and file_percent > 10:
                    rate_based_cur_rem = (100 - file_percent) / (effective_rate * (total_units / (total * 100)))
                    cur_file_rem = 0.6 * rate_based_cur_rem + 0.4 * cur_file_rem
                raw_remaining = cur_file_rem + (remaining_files_after_cur * avg_file_time)
            else:
                if effective_rate > 0 and overall_units >= 2:
                    raw_remaining = (total_units - progress_units) / effective_rate
                else:
                    return self.text("estimating")
        else:
            if effective_rate > 0 and overall_units >= 2:
                raw_remaining = (total_units - progress_units) / effective_rate
            else:
                return self.text("estimating")

        # Smooth changes using exponential moving average to prevent fluctuating jitter
        prev_smoothed = getattr(self, "_smoothed_eta_seconds", None)
        if prev_smoothed is not None and abs(prev_smoothed - raw_remaining) < 300:
            smoothed = 0.82 * prev_smoothed + 0.18 * raw_remaining
        else:
            smoothed = raw_remaining

        self._smoothed_eta_seconds = smoothed
        return self._format_seconds(smoothed)

    def _format_seconds(self, seconds):
        seconds = max(0, int(seconds))
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

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
        self._apply_theme_to_toplevel(dialog)
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
        if not getattr(self, "input_path", None):
            return False
        p = Path(self.input_path)
        return bool(p.is_file() and p.suffix.lower() in convert.MEDIA_EXTS)

    def video_files(self):
        return [path for path in self.media_files if path.suffix.lower() in convert.VIDEO_EXTS]

    def _update_run_state(self):
        self.run_button.configure(state=self._run_button_state())
        self.compress_video_button.configure(state="normal" if self.video_files() else "disabled")
        self.boost_button.configure(state="normal" if self.media_files else "disabled")
        self.detect_volume_button.configure(state="normal" if self.media_files else "disabled")
        self.auto_peak_button.configure(state="normal" if self.media_files else "disabled")
        self.caption_start_button.configure(state="normal" if self.media_files else "disabled")
        if hasattr(self, "silence_export_button"):
            self.silence_export_button.configure(state="normal" if self.media_files else "disabled")
        if hasattr(self, "silence_analyze_button"):
            self.silence_analyze_button.configure(state="normal" if self.media_files else "disabled")
        if hasattr(self, "silence_auto_db_button"):
            self.silence_auto_db_button.configure(state="normal" if self.media_files else "disabled")
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
        if hasattr(self, "btn_master_export"):
            is_vid = bool(self._single_media_file_selected() and self.input_path and (self.input_path.suffix.lower() in convert.VIDEO_EXTS or convert.has_video_stream(self.input_path)))
            self.btn_master_export.configure(state="normal" if is_vid else "disabled")
        if hasattr(self, "snapshot_button"):
            is_vid = bool(self._single_media_file_selected() and self.input_path and (self.input_path.suffix.lower() in convert.VIDEO_EXTS or convert.has_video_stream(self.input_path)))
            self.snapshot_button.configure(state="normal" if is_vid else "disabled")
        self._refresh_play_button()

    def close_app(self):
        if (self.worker and self.worker.is_alive()) or (self.caption_thread and self.caption_thread.is_alive()):
            if not messagebox.askyesno(self.text("app_title"), self.text("close_running")):
                return
            self.cancel_event.set()
            self.caption_cancel_event.set()
            convert.abort_whisper_download()
            self.status_var.set(self.text("canceling"))
            self.update_idletasks()
            if self.worker:
                self.worker.join(timeout=3)
            if self.caption_thread:
                self.caption_thread.join(timeout=2)
        convert.abort_whisper_download()
        self.trigger_step_autosave()
        mark_clean_exit()
        self._save_settings()
        self._exit_video_fullscreen()
        self.stop_playback()
        if hasattr(self, "fast_preview") and self.fast_preview:
            try:
                self.fast_preview.close()
            except Exception:
                pass
        if self.media_player:
            self.media_player.release()
            self.media_player = None
        if self.vlc_instance:
            self.vlc_instance.release()
            self.vlc_instance = None
        self.destroy()

    def toggle_log_drawer(self):
        if getattr(self, "log_visible", False):
            self.log_frame.grid_remove()
            self.log_visible = False
            arrow = "▼"
        else:
            self.log_frame.grid()
            self.log_visible = True
            arrow = "▲"
        if hasattr(self, "btn_toggle_log"):
            self.btn_toggle_log.configure(text=f"{self.text('view_log_btn')} {arrow}")

    def _handle_split_at_playhead_shortcut(self, event=None):
        if isinstance(getattr(event, "widget", None), (tk.Entry, ttk.Entry, tk.Text, tk.Spinbox, ttk.Spinbox, ttk.Combobox)):
            return
        if hasattr(self, "davinci_timeline"):
            self.davinci_timeline.split_at_playhead()
            return "break"

    def _bind_studio_shortcuts(self):
        def _on_key(event):
            if isinstance(event.widget, (tk.Entry, ttk.Entry, tk.Text, tk.Spinbox, ttk.Spinbox, ttk.Combobox)):
                return
            k = (event.keysym or "").lower()
            kc = getattr(event, "keycode", 0)
            ctrl_held = bool(event.state & 0x0004)
            shift_held = bool(event.state & 0x0001)
            in_player_tab = bool(hasattr(self, "davinci_timeline") and self.davinci_timeline.winfo_ismapped())

            # Universal Z, Y, B, S, A detection (handles English layout, Arabic layout, Windows virtual keycodes)
            # VK_B = 66, VK_S = 83, VK_A = 65, VK_Z = 90, VK_Y = 89, VK_SPACE = 32, VK_DELETE = 46
            is_z_key = (kc == 90) or (k in ("z", "arabic_yeh_hamzaabove", "yeh_hamzaabove", "\u0626"))
            is_y_key = (kc == 89) or (k in ("y", "arabic_ghain", "ghain", "\u063a"))
            is_b_key = (kc == 66) or (k in ("b", "arabic_laa", "arabic_lam_alef", "\u0644\u0627", "\u0644"))
            is_s_key = (kc == 83) or (k in ("s", "arabic_seen", "seen", "\u0633"))
            is_a_key = (kc == 65) or (k in ("a", "arabic_sheen", "sheen", "\u0634"))

            if ctrl_held:
                # Universal REDO: Ctrl + Shift + Z  OR  Ctrl + Y
                if (shift_held and is_z_key) or (not shift_held and is_y_key):
                    self.do_app_redo()
                    return "break"
                # Universal UNDO: Ctrl + Z
                if not shift_held and is_z_key:
                    self.do_app_undo()
                    return "break"
                # Split at playhead: Ctrl + B
                if is_b_key:
                    return self._handle_split_at_playhead_shortcut(event)
                return

            if k == "space" or kc == 32:
                if self._single_media_file_selected() or (hasattr(self, "loaded_media_path") and self.loaded_media_path):
                    self.toggle_play_pause()
                    return "break"
            elif in_player_tab and is_s_key:
                return self._handle_split_at_playhead_shortcut(event)
            elif in_player_tab and is_b_key:
                self.davinci_timeline.set_tool_mode("blade")
                return "break"
            elif in_player_tab and is_a_key:
                self.davinci_timeline.set_tool_mode("select")
                return "break"
            elif in_player_tab and (k in ("delete", "backspace") or kc in (46, 8)):
                self.davinci_timeline.delete_selected()
                return "break"
            elif in_player_tab and (k == "left" or kc == 37):
                self.seek_relative(-5.0 if shift_held else -1.0)
                return "break"
            elif in_player_tab and (k == "right" or kc == 39):
                self.seek_relative(5.0 if shift_held else 1.0)
                return "break"
            elif k == "i":
                if self._single_media_file_selected():
                    self.mark_trim_start()
                    return "break"
            elif k == "o":
                if self._single_media_file_selected():
                    self.mark_trim_end()
                    return "break"

        self.bind("<KeyPress>", _on_key)

        # Global fallbacks ensuring Ctrl+B, Ctrl+Z, and Ctrl+Y are captured anywhere
        for seq in ("<Control-b>", "<Control-B>", "<Control-Key-66>"):
            try:
                self.bind_all(seq, self._handle_split_at_playhead_shortcut)
            except Exception:
                pass
        for seq in ("<Control-z>", "<Control-Z>", "<Control-Key-90>"):
            try:
                self.bind_all(seq, self._handle_undo_event)
            except Exception:
                pass
        for seq in ("<Control-y>", "<Control-Y>", "<Control-Key-89>", "<Control-Shift-z>", "<Control-Shift-Z>"):
            try:
                self.bind_all(seq, self._handle_redo_event)
            except Exception:
                pass

    def _append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")
        lower_t = text.lower()
        if any(w in lower_t for w in ("error", "traceback", "failed", "خطأ", "فشل")) and not getattr(self, "log_visible", False):
            self.toggle_log_drawer()

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")


if __name__ == "__main__":
    try:
        app = SongCoverApp()
        app.mainloop()
    except Exception as e:
        import traceback
        crash_log = APP_DIR / "crash.log"
        try:
            with open(crash_log, "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
            messagebox.showerror("Error / خطأ", f"حدث خطأ أثناء تشغيل البرنامج:\n{e}\n\nتم حفظ التفاصيل في:\n{crash_log}")
        except Exception:
            pass
