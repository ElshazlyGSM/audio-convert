"""
Media Audio Studio GUI
Developer: ahmed elshazly
Email: Elshazly.gsm@gmail.com
"""

__author__ = "ahmed elshazly"
__email__ = "Elshazly.gsm@gmail.com"
__version__ = "1.0.0"

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
        "progress_detail": "{current} / {total} files | file: {file_percent}% | done: {overall_percent}% | elapsed: {elapsed} | remaining: ~{eta}",
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
        "about_title": "About Media Audio Studio",
        "about_desc": "All-in-one audio and video conversion studio with metadata and cover art support.",
        "about_developer_header": "Developer Information",
        "about_developer_name": "Developer: ahmed elshazly",
        "about_developer_email": "Email: Elshazly.gsm@gmail.com",
        "copy_email": "Copy Email",
        "close": "Close",
        "caption_group": "Auto Caption & Speech-to-Text",
        "open_caption_studio": "🎙️ Auto Caption / Transcribe",
        "caption_studio_title": "Auto Caption & Speech-to-Text Studio",
        "caption_source_label": "Source file:",
        "caption_folder_label": "Folder: {count} media files",
        "caption_model_label": "AI Model:",
        "caption_lang_label": "Audio Language:",
        "caption_translate_label": "Translate to:",
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
        "tab_convert": "🔄 Convert & Compress",
        "tab_volume": "🔊 Volume Booster",
        "tab_player": "▶️ Player & Trim",
        "tab_caption": "🎙️ Auto Caption",
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
        "boost_save": "Boost & Save Audio",
        "boosting_volume": "Boosting audio volume...",
        "volume_boosted_success": "Saved boosted audio: {filename}",
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
        "progress_detail": "{current} / {total} ملفات | الحالي: {file_percent}% | المكتمل: {overall_percent}% | المنقضي: {elapsed} | المتبقي: ~{eta}",
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
        "about_title": "حول Media Audio Studio",
        "about_desc": "برنامج شامل لتحويل ومعالجة الصوتيات والفيديو وضغط الوسائط وإضافة صور الأغلفة.",
        "about_developer_header": "بيانات المطور",
        "about_developer_name": "المطور: ahmed elshazly",
        "about_developer_email": "البريد الإلكتروني: Elshazly.gsm@gmail.com",
        "copy_email": "نسخ الإيميل",
        "close": "إغلاق",
        "caption_group": "التفريغ الصوتي والترجمة التلقائية",
        "open_caption_studio": "🎙️ تفريغ الصوت والترجمة",
        "caption_studio_title": "استوديو تفريغ الصوت والترجمة التلقائية",
        "caption_source_label": "الملف المحدد:",
        "caption_folder_label": "المجلد المحدد: {count} ملف وسائط",
        "caption_model_label": "نموذج الذكاء الاصطناعي:",
        "caption_lang_label": "لغة الصوت الأصلية:",
        "caption_translate_label": "ترجمة التسميات إلى:",
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
        "caption_save_as": "حفظ كملف...",
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
        "tab_convert": "🔄 تحويل وضغط الوسائط",
        "tab_volume": "🔊 تضخيم ورفع الصوت",
        "tab_player": "▶️ المشغل وقص المقاطع",
        "tab_caption": "🎙️ التفريغ الصوتي والترجمة",
        "tab_cover": "🖼️ صور الأغلفة والبيانات",
        "tab_youtube": "📥 تحميل من يوتيوب",
        "volume_group": "تضخيم ورفع مستوى الصوت",
        "volume_analysis_group": "فحص وتحليل مستوى الصوت الحالي",
        "detect_volume": "فحص مستوى الصوت",
        "detecting_volume": "جاري فحص مستوى صوت الملف...",
        "volume_current_level": "متوسط الصوت: {mean} dB | أعلى ذروة: {max} dB",
        "volume_suggested": "الزيادة النقية المقترحة: +{gain} dB",
        "volume_gain_label": "نسبة تضخيم الصوت:",
        "volume_anti_clipping": "حماية من الخربشة والقص (Anti-Clipping Limiter)",
        "volume_normalize_peak": "رفع تلقائي ذكي لأعلى صوت نقي (Auto Peak)",
        "boost_save": "تضخيم وحفظ الصوت الجديد",
        "boosting_volume": "جاري تضخيم الصوت وحفظه...",
        "volume_boosted_success": "تم حفظ الملف بالصوت العالي: {filename}",
        "volume_preset_light": "+3 dB (140% - زيادة خفيفة)",
        "volume_preset_double": "+6 dB (200% - مضاعفة الصوت)",
        "volume_preset_high": "+10 dB (316% - تضخيم قوي)",
        "volume_preset_extreme": "+15 dB (560% - تضخيم فائق)",
        "audio_options": "خيارات تحويل الصوت",
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



class SubtitleStyleDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.app = getattr(parent, "parent", parent)
        is_ar = self.app.language_var.get() == "العربية"
        self.is_ar = is_ar
        self.title(self.app.text("subtitle_style_title"))
        self.geometry("680x640")
        self.minsize(620, 580)
        self.transient(parent)
        self.resizable(True, True)

        cur_style = dict(getattr(self.app, "subtitle_style", {}))

        from tkinter import font as tkfont
        self.tkfont = tkfont
        system_fonts = []
        try:
            system_fonts = [f for f in tkfont.families() if not f.startswith("@") and not f.startswith("System")]
        except Exception:
            pass
        curated_fonts = [
            "Segoe UI", "Arial", "Cairo", "Tahoma", "Calibri", "Impact",
            "Times New Roman", "Comic Sans MS", "Verdana", "Trebuchet MS",
            "Dubai", "Traditional Arabic"
        ]
        self.font_families = []
        for f in curated_fonts:
            if f not in self.font_families:
                self.font_families.append(f)
        for f in sorted(system_fonts):
            if f not in self.font_families and len(self.font_families) < 40:
                self.font_families.append(f)

        self.font_sizes = [
            ("auto", self.app.text("sub_font_auto")),
            ("18", "18 px (صغير / Small)"),
            ("20", "20 px"),
            ("22", "22 px"),
            ("24", "24 px (افتراضي / Default)"),
            ("26", "26 px (واضح / Clear)"),
            ("28", "28 px (كبير / Large)"),
            ("32", "32 px (بارز / Prominent)"),
            ("36", "36 px"),
            ("40", "40 px"),
            ("48", "48 px (فائق الضخامة / Extra Large)"),
            ("56", "56 px"),
        ]

        self.color_options = [
            ("yellow", "أصفر (Yellow)" if is_ar else "Yellow (أصفر)"),
            ("white", "أبيض (White)" if is_ar else "White (أبيض)"),
            ("lime", "أخضر ليموني (Lime)" if is_ar else "Lime Green (أخضر ليموني)"),
            ("cyan", "سماوي (Cyan)" if is_ar else "Cyan (سماوي)"),
            ("orange", "برتقالي (Orange)" if is_ar else "Orange (برتقالي)"),
            ("pink", "وردي (Pink)" if is_ar else "Pink (وردي)"),
            ("red", "أحمر (Red)" if is_ar else "Red (أحمر)"),
            ("black", "أسود (Black)" if is_ar else "Black (أسود)"),
        ]

        self.outline_options = [
            ("box_semi", "بالونة كبسولة خلفية نصف شفافة (شبه CapCut)" if is_ar else "Semi-transparent Bubble/Box (CapCut Style)"),
            ("thick_black", "إطار أسود عريض وبارز" if is_ar else "Thick Black Outline"),
            ("medium_black", "إطار أسود متوسط" if is_ar else "Medium Black Outline"),
            ("thin_black", "إطار أسود خفيف" if is_ar else "Thin Black Outline"),
            ("box_black", "صندوق خلفية أسود داكن" if is_ar else "Solid Black Box"),
            ("box_navy", "صندوق خلفية كحلي داكن" if is_ar else "Solid Navy Blue Box"),
            ("none", "نص عادي بدون إطار أو خلفية" if is_ar else "Plain Text (No Outline/Box)"),
        ]

        self.pos_v_options = [
            ("bottom", self.app.text("sub_pos_bottom")),
            ("middle", self.app.text("sub_pos_middle")),
            ("top", self.app.text("sub_pos_top")),
        ]

        self.pos_h_options = [
            ("center", self.app.text("sub_align_center")),
            ("left", self.app.text("sub_align_left")),
            ("right", self.app.text("sub_align_right")),
        ]

        saved_font = cur_style.get("font_name", "Segoe UI")
        if saved_font not in self.font_families:
            self.font_families.insert(0, saved_font)
        self.font_name_var = tk.StringVar(value=saved_font)

        saved_size = str(cur_style.get("font_size", "26"))
        self.font_size_var = tk.StringVar()
        for s_code, s_lbl in self.font_sizes:
            if s_code == saved_size:
                self.font_size_var.set(s_lbl)
                break
        if not self.font_size_var.get():
            self.font_size_var.set(self.font_sizes[5][1])

        saved_color = cur_style.get("text_color", cur_style.get("color", "yellow"))
        self.color_var = tk.StringVar()
        for c_code, c_lbl in self.color_options:
            if c_code == saved_color:
                self.color_var.set(c_lbl)
                break
        if not self.color_var.get():
            self.color_var.set(self.color_options[0][1])

        saved_outline = cur_style.get("outline_style", cur_style.get("outline", "box_semi"))
        self.outline_var = tk.StringVar()
        for o_code, o_lbl in self.outline_options:
            if o_code == saved_outline:
                self.outline_var.set(o_lbl)
                break
        if not self.outline_var.get():
            self.outline_var.set(self.outline_options[0][1])

        self.bold_var = tk.BooleanVar(value=cur_style.get("bold", True))
        self.italic_var = tk.BooleanVar(value=cur_style.get("italic", False))

        saved_pv = cur_style.get("position_v", "bottom")
        self.pos_v_var = tk.StringVar()
        for v_code, v_lbl in self.pos_v_options:
            if v_code == saved_pv:
                self.pos_v_var.set(v_lbl)
                break
        if not self.pos_v_var.get():
            self.pos_v_var.set(self.pos_v_options[0][1])

        saved_ph = cur_style.get("position_h", "center")
        self.pos_h_var = tk.StringVar()
        for h_code, h_lbl in self.pos_h_options:
            if h_code == saved_ph:
                self.pos_h_var.set(h_lbl)
                break
        if not self.pos_h_var.get():
            self.pos_h_var.set(self.pos_h_options[0][1])

        try:
            saved_mv = int(cur_style.get("margin_v", 35))
        except Exception:
            saved_mv = 35
        self.margin_v_var = tk.IntVar(value=saved_mv)

        self._build_ui()
        self.after(50, self._update_preview)

        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        dw = self.winfo_width()
        dh = self.winfo_height()
        x = max(20, px + (pw - dw) // 2)
        y = max(20, py + (ph - dh) // 2)
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        f_card = ttk.LabelFrame(container, text="🖋️ " + ("الخط والمظهر واللون" if self.is_ar else "Font & Color Appearance"), padding=(12, 10))
        f_card.pack(fill="x", pady=(0, 10))
        f_card.columnconfigure(1, weight=1)
        f_card.columnconfigure(3, weight=1)

        ttk.Label(f_card, text=self.app.text("sub_font_name")).grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
        self.combo_font = ttk.Combobox(f_card, textvariable=self.font_name_var, values=self.font_families, state="readonly", width=18)
        self.combo_font.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=4)
        self.combo_font.bind("<<ComboboxSelected>>", lambda _e: self._update_preview())

        ttk.Label(f_card, text=self.app.text("sub_font_size")).grid(row=0, column=2, sticky="w", padx=(0, 6), pady=4)
        self.combo_size = ttk.Combobox(f_card, textvariable=self.font_size_var, values=[s[1] for s in self.font_sizes], state="readonly", width=18)
        self.combo_size.grid(row=0, column=3, sticky="ew", pady=4)
        self.combo_size.bind("<<ComboboxSelected>>", lambda _e: self._update_preview())

        ttk.Label(f_card, text=self.app.text("sub_text_color")).grid(row=1, column=0, sticky="w", padx=(0, 6), pady=4)
        self.combo_color = ttk.Combobox(f_card, textvariable=self.color_var, values=[c[1] for c in self.color_options], state="readonly", width=18)
        self.combo_color.grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=4)
        self.combo_color.bind("<<ComboboxSelected>>", lambda _e: self._update_preview())

        ttk.Label(f_card, text=self.app.text("sub_outline_style")).grid(row=1, column=2, sticky="w", padx=(0, 6), pady=4)
        self.combo_outline = ttk.Combobox(f_card, textvariable=self.outline_var, values=[o[1] for o in self.outline_options], state="readonly", width=24)
        self.combo_outline.grid(row=1, column=3, sticky="ew", pady=4)
        self.combo_outline.bind("<<ComboboxSelected>>", lambda _e: self._update_preview())

        style_row = ttk.Frame(f_card)
        style_row.grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))
        self.chk_bold = ttk.Checkbutton(style_row, text=self.app.text("sub_bold"), variable=self.bold_var, command=self._update_preview)
        self.chk_bold.pack(side="left", padx=(0, 16))
        self.chk_italic = ttk.Checkbutton(style_row, text=self.app.text("sub_italic"), variable=self.italic_var, command=self._update_preview)
        self.chk_italic.pack(side="left")

        pos_card = ttk.LabelFrame(container, text="📍 " + ("مكان الترجمة على شاشة الفيديو" if self.is_ar else "Subtitle Position on Video"), padding=(12, 10))
        pos_card.pack(fill="x", pady=(0, 10))
        pos_card.columnconfigure(1, weight=1)
        pos_card.columnconfigure(3, weight=1)

        ttk.Label(pos_card, text=self.app.text("sub_pos_v")).grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
        self.combo_pv = ttk.Combobox(pos_card, textvariable=self.pos_v_var, values=[v[1] for v in self.pos_v_options], state="readonly", width=18)
        self.combo_pv.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=4)
        self.combo_pv.bind("<<ComboboxSelected>>", lambda _e: self._update_preview())

        ttk.Label(pos_card, text=self.app.text("sub_pos_h")).grid(row=0, column=2, sticky="w", padx=(0, 6), pady=4)
        self.combo_ph = ttk.Combobox(pos_card, textvariable=self.pos_h_var, values=[h[1] for h in self.pos_h_options], state="readonly", width=18)
        self.combo_ph.grid(row=0, column=3, sticky="ew", pady=4)
        self.combo_ph.bind("<<ComboboxSelected>>", lambda _e: self._update_preview())

        ttk.Label(pos_card, text=self.app.text("sub_margin_v")).grid(row=1, column=0, sticky="w", padx=(0, 6), pady=4)
        slider_frame = ttk.Frame(pos_card)
        slider_frame.grid(row=1, column=1, columnspan=3, sticky="ew", pady=4)
        slider_frame.columnconfigure(0, weight=1)

        self.scale_margin = ttk.Scale(slider_frame, from_=10, to=120, variable=self.margin_v_var, orient="horizontal", command=lambda _v: self._on_margin_slider())
        self.scale_margin.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.lbl_margin_val = ttk.Label(slider_frame, text=f"{self.margin_v_var.get()} px", width=8)
        self.lbl_margin_val.grid(row=0, column=1, sticky="w")

        prev_card = ttk.LabelFrame(container, text="🎬 " + self.app.text("sub_preview_label"), padding=(8, 8))
        prev_card.pack(fill="both", expand=True, pady=(0, 12))

        self.preview_canvas = tk.Canvas(prev_card, bg="#14181f", height=140, highlightthickness=1, highlightbackground="#2d333b")
        self.preview_canvas.pack(fill="both", expand=True)
        self.preview_canvas.bind("<Configure>", lambda _e: self._update_preview())

        btn_box = ttk.Frame(container)
        btn_box.pack(fill="x")

        self.btn_save = ttk.Button(btn_box, text="💾 " + self.app.text("sub_save_apply"), command=self._save_and_apply, style="Action.TButton")
        self.btn_save.pack(side="left" if not self.is_ar else "right", padx=(0, 8))

        self.btn_reset = ttk.Button(btn_box, text="🔄 " + self.app.text("sub_reset_defaults"), command=self._reset_defaults, style="Player.TButton")
        self.btn_reset.pack(side="left" if not self.is_ar else "right", padx=(0, 8))

        self.btn_close = ttk.Button(btn_box, text=self.app.text("close"), command=self.destroy, style="Player.TButton")
        self.btn_close.pack(side="right" if not self.is_ar else "left")

    def _on_margin_slider(self):
        val = int(self.margin_v_var.get())
        self.lbl_margin_val.configure(text=f"{val} px")
        self._update_preview()

    def _get_selected_size_code(self):
        txt = self.font_size_var.get()
        for s_code, s_lbl in self.font_sizes:
            if s_lbl == txt:
                return s_code
        return "26"

    def _get_selected_color_code(self):
        txt = self.color_var.get()
        for c_code, c_lbl in self.color_options:
            if c_lbl == txt:
                return c_code
        return "yellow"

    def _get_selected_outline_code(self):
        txt = self.outline_var.get()
        for o_code, o_lbl in self.outline_options:
            if o_lbl == txt:
                return o_code
        return "box_semi"

    def _get_selected_pos_v_code(self):
        txt = self.pos_v_var.get()
        for v_code, v_lbl in self.pos_v_options:
            if v_lbl == txt:
                return v_code
        return "bottom"

    def _get_selected_pos_h_code(self):
        txt = self.pos_h_var.get()
        for h_code, h_lbl in self.pos_h_options:
            if h_lbl == txt:
                return h_code
        return "center"

    def _update_preview(self):
        if not hasattr(self, "preview_canvas") or not self.preview_canvas.winfo_exists():
            return

        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()
        if cw < 60:
            cw = 620
        if ch < 40:
            ch = 140

        self.preview_canvas.delete("all")

        self.preview_canvas.create_rectangle(0, 0, cw, ch, fill="#12161c", outline="#262c36", width=1)
        self.preview_canvas.create_text(
            cw - 12 if not self.is_ar else 12,
            12,
            text="1080p FULL HD • 16:9",
            anchor="ne" if not self.is_ar else "nw",
            font=("Segoe UI", 7, "bold"),
            fill="#485261",
        )

        font_name = self.font_name_var.get().strip() or "Segoe UI"
        size_code = self._get_selected_size_code()
        color_code = self._get_selected_color_code()
        outline_code = self._get_selected_outline_code()
        pv = self._get_selected_pos_v_code()
        ph = self._get_selected_pos_h_code()
        mv = int(self.margin_v_var.get())
        bold = self.bold_var.get()
        italic = self.italic_var.get()

        if size_code == "auto":
            sim_size = 14
        else:
            try:
                sim_size = max(11, min(22, int(int(size_code) * 0.58)))
            except Exception:
                sim_size = 14

        weight_str = "bold" if bold else "normal"
        slant_str = "italic" if italic else "roman"
        try:
            prev_font = self.tkfont.Font(family=font_name, size=sim_size, weight=weight_str, slant=slant_str)
        except Exception:
            prev_font = self.tkfont.Font(family="Segoe UI", size=sim_size, weight=weight_str, slant=slant_str)

        HEX_COLORS = {
            "yellow": "#FFE600",
            "white": "#FFFFFF",
            "lime": "#39FF14",
            "cyan": "#00F0FF",
            "orange": "#FF8C00",
            "pink": "#FF69B4",
            "red": "#FF3B30",
            "black": "#000000",
        }
        text_color_hex = HEX_COLORS.get(color_code, "#FFE600")

        scaled_mv = max(10, min(50, int(mv * 0.35)))
        if pv == "top":
            y = scaled_mv + 12
        elif pv == "middle":
            y = ch // 2
        else:
            y = ch - scaled_mv - 12

        if ph == "left":
            x = 24
            anchor = "w"
        elif ph == "right":
            x = cw - 24
            anchor = "e"
        else:
            x = cw // 2
            anchor = "center"

        sample_txt = self.app.text("sub_preview_sample")
        t_width = prev_font.measure(sample_txt)
        t_height = prev_font.metrics("linespace")

        if outline_code == "box_semi":
            bg_fill = "#1d232c"
            bg_border = "#3a4454"
        elif outline_code == "box_black":
            bg_fill = "#000000"
            bg_border = "#1a1a1a"
        elif outline_code == "box_navy":
            bg_fill = "#0b192e"
            bg_border = "#1b3a6b"
        else:
            bg_fill = None

        if bg_fill:
            pad_x = 10
            pad_y = 4
            if anchor == "center":
                bx0 = x - t_width // 2 - pad_x
                bx1 = x + t_width // 2 + pad_x
            elif anchor == "w":
                bx0 = x - pad_x
                bx1 = x + t_width + pad_x
            else:
                bx0 = x - t_width - pad_x
                bx1 = x + pad_x
            by0 = y - t_height // 2 - pad_y
            by1 = y + t_height // 2 + pad_y
            self.preview_canvas.create_rectangle(bx0, by0, bx1, by1, fill=bg_fill, outline=bg_border, width=1)

        if outline_code in ("thick_black", "medium_black", "thin_black"):
            off = 2 if outline_code == "thick_black" else 1
            for dx, dy in [(-off, 0), (off, 0), (0, -off), (0, off), (-off, -off), (off, -off), (-off, off), (off, off)]:
                self.preview_canvas.create_text(
                    x + dx, y + dy, text=sample_txt, font=prev_font, fill="#000000", anchor=anchor
                )

        self.preview_canvas.create_text(
            x, y, text=sample_txt, font=prev_font, fill=text_color_hex, anchor=anchor
        )

    def _save_and_apply(self):
        cfg = {
            "font_name": self.font_name_var.get().strip() or "Segoe UI",
            "font_size": self._get_selected_size_code(),
            "text_color": self._get_selected_color_code(),
            "outline_style": self._get_selected_outline_code(),
            "bold": bool(self.bold_var.get()),
            "italic": bool(self.italic_var.get()),
            "position_v": self._get_selected_pos_v_code(),
            "position_h": self._get_selected_pos_h_code(),
            "margin_v": int(self.margin_v_var.get()),
        }
        self.app.subtitle_style = cfg
        self.app.settings["subtitle_style"] = cfg
        self.app._save_settings()
        messagebox.showinfo(
            self.app.text("app_title"),
            self.app.text("sub_edits_saved"),
            parent=self,
        )
        self.destroy()

    def _reset_defaults(self):
        self.font_name_var.set("Segoe UI")
        self.font_size_var.set(self.font_sizes[5][1])
        self.color_var.set(self.color_options[0][1])
        self.outline_var.set(self.outline_options[0][1])
        self.bold_var.set(True)
        self.italic_var.set(False)
        self.pos_v_var.set(self.pos_v_options[0][1])
        self.pos_h_var.set(self.pos_h_options[0][1])
        self.margin_v_var.set(35)
        self.lbl_margin_val.configure(text="35 px")
        self._update_preview()


class CaptionStudioDialog(tk.Toplevel):
    def __init__(self, parent, initial_source=None, initial_output_dir=None, media_files=None):
        super().__init__(parent)
        self.parent = parent
        self.title(parent.text("caption_studio_title"))
        self.geometry("900x680")
        self.minsize(800, 580)
        self.transient(parent)

        self.source_path = Path(initial_source).resolve() if initial_source else None
        self.media_files = list(media_files) if media_files else ([self.source_path] if self.source_path else [])
        if self.source_path:
            base_dir = self.source_path.parent if self.source_path.is_file() else self.source_path
            self.output_dir = Path(initial_output_dir).resolve() if initial_output_dir else (base_dir / "output")
        else:
            self.output_dir = Path(initial_output_dir).resolve() if initial_output_dir else convert.OUTPUT_DIR

        self.transcribe_thread = None
        self.cancel_event = threading.Event()
        self.current_result = None
        self.segments_accumulated = []

        is_ar = parent.language_var.get() == "العربية"
        self.is_ar = is_ar

        self.model_options = [
            ("small", "Small (⚡ حوالي 465MB - موصى به: توازن ممتاز ودقة عالية)" if is_ar else "Small (⚡ ~465MB - Recommended: High Accuracy & Balanced)"),
            ("base", "Base (🚀 حوالي 140MB - خفيف وسريع)" if is_ar else "Base (🚀 ~140MB - Fast & Lightweight)"),
            ("turbo", "Turbo (💎 حوالي 1.5GB - أعلى دقة مثل CapCut و NoteGPT)" if is_ar else "Turbo (💎 ~1.5GB - Max Accuracy / CapCut & NoteGPT)"),
            ("tiny", "Tiny (⚠️ حوالي 75MB - فائق السرعة / دقة منخفضة)" if is_ar else "Tiny (⚠️ ~75MB - Ultra Fast, Low Accuracy)"),
            ("medium", "Medium (💎 حوالي 1.5GB - دقة عالية جداً)" if is_ar else "Medium (~1.5GB - Very High Accuracy)"),
        ]

        self.lang_options = [
            ("auto", "كشف تلقائي للغة" if is_ar else "Auto Detect"),
            ("ar", "العربية (Arabic)"),
            ("en", "الإنجليزية (English)"),
            ("fr", "الفرنسية (French)"),
            ("es", "الإسبانية (Spanish)"),
            ("de", "الألمانية (German)"),
            ("it", "الإيطالية (Italian)"),
            ("tr", "التركية (Turkish)"),
            ("ru", "الروسية (Russian)"),
            ("zh", "الصينية (Chinese)"),
            ("ja", "اليابانية (Japanese)"),
            ("ko", "الكورية (Korean)"),
            ("ur", "الأوردو (Urdu)"),
        ]

        self.translate_options = [
            ("none", "نفس لغة الصوت الأصلية (بدون ترجمة)" if is_ar else "Original Audio Language (No Translation)"),
            ("ar", "العربية (Arabic)"),
            ("en", "الإنجليزية (English)"),
            ("fr", "الفرنسية (French)"),
            ("es", "الإسبانية (Spanish)"),
            ("de", "الألمانية (German)"),
            ("it", "الإيطالية (Italian)"),
            ("tr", "التركية (Turkish)"),
            ("ru", "الروسية (Russian)"),
            ("zh-CN", "الصينية (Chinese)"),
            ("ja", "اليابانية (Japanese)"),
            ("ko", "الكورية (Korean)"),
        ]

        saved_model = parent.settings.get("caption_model", "small")
        default_model_str = self.model_options[0][1]
        for mid, mlabel in self.model_options:
            if mid == saved_model:
                default_model_str = mlabel
                break

        saved_lang = parent.settings.get("caption_lang", "auto")
        default_lang_str = self.lang_options[0][1]
        for lid, llabel in self.lang_options:
            if lid == saved_lang:
                default_lang_str = llabel
                break

        self.source_info_var = tk.StringVar()
        self.model_var = tk.StringVar(value=default_model_str)
        self.lang_var = tk.StringVar(value=default_lang_str)
        self.translate_var = tk.StringVar(value=self.translate_options[0][1])
        self.export_srt_var = tk.BooleanVar(value=True)
        self.export_vtt_var = tk.BooleanVar(value=True)
        self.export_txt_var = tk.BooleanVar(value=True)
        self.burn_video_var = tk.BooleanVar(value=False)
        self.view_mode_var = tk.StringVar(value="text")
        self.status_var = tk.StringVar(value=parent.text("caption_ready"))
        self.progress_val_var = tk.DoubleVar(value=0)

        self._build_ui()
        self._refresh_source_info()
        self.protocol("WM_DELETE_WINDOW", self.close_dialog)

        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        dw = self.winfo_width()
        dh = self.winfo_height()
        x = max(20, px + (pw - dw) // 2)
        y = max(20, py + (ph - dh) // 2)
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        header = ttk.Frame(container)
        header.pack(fill="x", pady=(0, 10))

        title_lbl = ttk.Label(
            header,
            text=self.parent.text("caption_studio_title"),
            font=("Segoe UI", 13, "bold"),
        )
        title_lbl.pack(side="left" if not self.is_ar else "right", pady=(0, 4))

        src_frame = ttk.LabelFrame(container, text=self.parent.text("caption_group"), padding=(10, 8))
        src_frame.pack(fill="x", pady=(0, 10))
        src_frame.columnconfigure(1, weight=1)

        ttk.Label(src_frame, text=self.parent.text("caption_source_label"), font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w" if not self.is_ar else "e", padx=(0, 8)
        )
        self.source_entry = ttk.Entry(src_frame, textvariable=self.source_info_var, state="readonly")
        self.source_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        browse_btn = ttk.Button(src_frame, text=self.parent.text("choose_file"), command=self._choose_file)
        browse_btn.grid(row=0, column=2, sticky="e" if not self.is_ar else "w")

        settings_frame = ttk.Frame(container)
        settings_frame.pack(fill="x", pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1)
        settings_frame.columnconfigure(3, weight=1)

        ttk.Label(settings_frame, text=self.parent.text("caption_model_label")).grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.model_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.model_var,
            values=[opt[1] for opt in self.model_options],
            state="readonly",
            width=28,
        )
        self.model_combo.grid(row=0, column=1, sticky="w", padx=(0, 16))
        self.model_combo.bind("<<ComboboxSelected>>", self._update_model_status)

        self.model_status_var = tk.StringVar(value="")
        model_status_box = ttk.Frame(settings_frame)
        model_status_box.grid(row=1, column=1, sticky="ew", pady=(2, 0))
        self.model_status_label = ttk.Label(model_status_box, textvariable=self.model_status_var, font=("Segoe UI", 8, "bold"))
        self.model_status_label.pack(side="left", padx=(0, 6))
        self.download_model_btn = ttk.Button(
            model_status_box,
            text=self.parent.text("caption_download_model_btn"),
            command=self.download_current_model,
            style="Player.TButton",
        )
        self.download_model_btn.pack(side="left")

        ttk.Label(settings_frame, text=self.parent.text("caption_lang_label")).grid(row=0, column=2, sticky="w", padx=(0, 6))
        self.lang_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.lang_var,
            values=[opt[1] for opt in self.lang_options],
            state="readonly",
            width=20,
        )
        self.lang_combo.grid(row=0, column=3, sticky="w")

        ttk.Label(settings_frame, text=self.parent.text("caption_translate_label")).grid(row=2, column=0, sticky="w", padx=(0, 6), pady=(6, 0))
        self.translate_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.translate_var,
            values=[opt[1] for opt in self.translate_options],
            state="readonly",
            width=28,
        )
        self.translate_combo.grid(row=2, column=1, sticky="w", padx=(0, 16), pady=(6, 0))

        dir_frame = ttk.Frame(container)
        dir_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(dir_frame, text=self.parent.text("caption_models_dir"), font=("Segoe UI", 8)).pack(side="left", padx=(0, 4))
        models_dir = convert.get_whisper_models_dir()
        ttk.Label(dir_frame, text=str(models_dir), foreground="#555555", font=("Segoe UI", 8)).pack(side="left", padx=(0, 8))
        ttk.Button(
            dir_frame,
            text=self.parent.text("caption_open_models_dir"),
            command=lambda: self.parent.open_folder(models_dir),
            style="Player.TButton",
        ).pack(side="left")

        self._update_model_status()

        chk_frame = ttk.Frame(container)
        chk_frame.pack(fill="x", pady=(0, 10))

        self.srt_check = ttk.Checkbutton(chk_frame, text=self.parent.text("caption_export_srt"), variable=self.export_srt_var)
        self.srt_check.pack(side="left", padx=(0, 14))

        self.vtt_check = ttk.Checkbutton(chk_frame, text=self.parent.text("caption_export_vtt"), variable=self.export_vtt_var)
        self.vtt_check.pack(side="left", padx=(0, 14))

        self.txt_check = ttk.Checkbutton(chk_frame, text=self.parent.text("caption_export_txt"), variable=self.export_txt_var)
        self.txt_check.pack(side="left", padx=(0, 14))

        self.burn_check = ttk.Checkbutton(
            chk_frame,
            text=self.parent.text("caption_burn_video"),
            variable=self.burn_video_var,
        )
        self.burn_check.pack(side="left", padx=(0, 14))

        ctrl_frame = ttk.Frame(container)
        ctrl_frame.pack(fill="x", pady=(0, 10))
        ctrl_frame.columnconfigure(3, weight=1)

        self.start_btn = ttk.Button(
            ctrl_frame,
            text=self.parent.text("caption_start"),
            command=self.start_transcription,
            style="PrimaryPlayer.TButton",
            width=18,
        )
        self.start_btn.grid(row=0, column=0, sticky="w", padx=(0, 6))

        self.stop_btn = ttk.Button(
            ctrl_frame,
            text=self.parent.text("caption_stop"),
            command=self.cancel_transcription,
            state="disabled",
            width=8,
        )
        self.stop_btn.grid(row=0, column=1, sticky="w", padx=(0, 6))

        self.import_capcut_btn = ttk.Button(
            ctrl_frame,
            text=self.parent.text("caption_import_capcut"),
            command=self.import_from_capcut,
        )
        self.import_capcut_btn.grid(row=0, column=2, sticky="w", padx=(0, 10))

        self.prog_bar = ttk.Progressbar(ctrl_frame, variable=self.progress_val_var, maximum=100)
        self.prog_bar.grid(row=0, column=3, sticky="ew")

        status_lbl = ttk.Label(container, textvariable=self.status_var, font=("Segoe UI", 9), foreground="#333333")
        status_lbl.pack(fill="x", pady=(0, 6))

        res_header = ttk.Frame(container)
        res_header.pack(fill="x", pady=(2, 4))

        title_res = "📝 " + ("Extracted Transcript" if not self.is_ar else "النص المستخرج")
        ttk.Label(res_header, text=title_res, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 14))

        self.radio_txt = ttk.Radiobutton(
            res_header,
            text=self.parent.text("caption_tab_text"),
            variable=self.view_mode_var,
            value="text",
            command=self._view_mode_changed,
        )
        self.radio_txt.pack(side="left", padx=(0, 10))

        self.radio_srt = ttk.Radiobutton(
            res_header,
            text=self.parent.text("caption_tab_srt"),
            variable=self.view_mode_var,
            value="srt",
            command=self._view_mode_changed,
        )
        self.radio_srt.pack(side="left")

        text_frame = ttk.Frame(container)
        text_frame.pack(fill="both", expand=True, pady=(0, 10))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self.text_widget = tk.Text(
            text_frame,
            wrap="word",
            font=("Segoe UI", 10),
            padx=8,
            pady=8,
        )
        self.text_widget.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.text_widget.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.text_widget.configure(yscrollcommand=scrollbar.set)
        self._attach_text_context_menu(self.text_widget)

        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill="x")

        self.copy_btn = ttk.Button(btn_bar, text="📋 " + self.parent.text("caption_copy"), command=self.copy_text)
        self.copy_btn.pack(side="left", padx=(0, 8))

        self.save_btn = ttk.Button(btn_bar, text="💾 " + self.parent.text("caption_save_as"), command=self.save_as)
        self.save_btn.pack(side="left", padx=(0, 8))

        self.burn_btn = ttk.Button(btn_bar, text="🎬 " + self.parent.text("caption_burn_now"), command=self.burn_subtitles_now)
        self.burn_btn.pack(side="left", padx=(0, 8))

        self.style_btn = ttk.Button(btn_bar, text=self.parent.text("caption_style_btn"), command=self.open_subtitle_style_dialog, style="Player.TButton")
        self.style_btn.pack(side="left", padx=(0, 8))

        self.trans_btn = ttk.Button(btn_bar, text=self.parent.text("caption_translate_btn"), command=self.translate_current_text)
        self.trans_btn.pack(side="left", padx=(0, 8))

        self.folder_btn = ttk.Button(btn_bar, text="📂 " + self.parent.text("caption_open_folder"), command=self.open_output_folder)
        self.folder_btn.pack(side="left", padx=(0, 8))

        self.close_btn = ttk.Button(btn_bar, text=self.parent.text("close"), command=self.close_dialog)
        self.close_btn.pack(side="right")

    def open_subtitle_style_dialog(self):
        dlg = SubtitleStyleDialog(self)
        dlg.grab_set()

    def _refresh_source_info(self):
        if self.source_path and self.source_path.is_file():
            dur_str = ""
            try:
                sec = convert.get_media_duration(self.source_path)
                if sec:
                    dur_str = f" ({self.parent._format_time(sec)})"
            except Exception:
                pass
            self.source_info_var.set(f"{self.source_path.name}{dur_str}")
        elif self.media_files and len(self.media_files) > 1:
            self.source_info_var.set(self.parent.text("caption_folder_label", count=len(self.media_files)))
        else:
            self.source_info_var.set(self.parent.text("source_empty"))

        has_media = bool(self.source_path and self.source_path.is_file())
        has_subs = bool(self.current_result and (self.current_result.get("srt_path") or self.current_result.get("segments")))
        if has_media:
            self.burn_check.configure(state="normal")
        else:
            self.burn_video_var.set(False)
            self.burn_check.configure(state="disabled")
        self.burn_btn.configure(state="normal" if has_subs else "disabled")

    def _is_current_video(self):
        if not self.source_path or not self.source_path.is_file():
            return False
        return self.source_path.suffix.lower() in convert.VIDEO_EXTS

    def _choose_file(self):
        filetypes = [
            (self.parent.text("media_files"), " ".join(f"*{ext}" for ext in sorted(convert.MEDIA_EXTS))),
            (self.parent.text("audio_files"), " ".join(f"*{ext}" for ext in sorted(convert.AUDIO_EXTS))),
            (self.parent.text("video_files"), " ".join(f"*{ext}" for ext in sorted(convert.VIDEO_EXTS))),
            (self.parent.text("all_files"), "*.*"),
        ]
        init_dir = (
            (self.source_path.parent if self.source_path and self.source_path.is_file() else None)
            or self.parent.last_media_dir
            or (self.parent.input_path.parent if self.parent.input_path else None)
            or self.output_dir
        )
        selected = filedialog.askopenfilename(
            title=self.parent.text("file_title"),
            initialdir=self.parent._dialog_dir(init_dir),
            filetypes=filetypes,
        )
        if selected:
            self.source_path = Path(selected).resolve()
            self.media_files = [self.source_path]
            self.output_dir = self.source_path.parent / "output"
            self.current_result = None
            self.segments_accumulated = []
            self.text_widget.delete("1.0", "end")
            self._refresh_source_info()
            self.status_var.set(self.parent.text("caption_ready"))
            self.progress_val_var.set(0)

    def _get_model_id(self):
        val = self.model_var.get()
        for mid, label in self.model_options:
            if label == val:
                return mid
        return "turbo"

    def _get_selected_model_id(self):
        return self._get_model_id()

    def _get_lang_code(self):
        val = self.lang_var.get()
        for lid, label in self.lang_options:
            if label == val:
                return None if lid == "auto" else lid
        return None

    def _get_translate_code(self):
        val = self.translate_var.get()
        for tid, label in self.translate_options:
            if label == val:
                return None if tid == "none" else tid
        return None

    def translate_current_text(self):
        target_lang = self._get_translate_code()
        if not target_lang:
            messagebox.showinfo(self.parent.text("app_title"), self.parent.text("caption_translate_label"))
            return
        if not self.current_result and not self.segments_accumulated:
            return

        def worker():
            try:
                self.after(0, lambda: self.status_var.set(self.parent.text("caption_translating", target=target_lang)))
                orig_segments = self.current_result["segments"] if self.current_result else self.segments_accumulated
                translated = convert.translate_segments(orig_segments, target_lang=target_lang)
                if self.current_result:
                    self.current_result["segments"] = translated
                    self.current_result["text"] = "\n".join(s["text"] for s in translated)
                self.segments_accumulated = translated
                self.after(0, self._refresh_text_display)
                self.after(0, lambda: self.status_var.set(self.parent.text("caption_translate_done", target=target_lang)))
            except Exception as exc:
                self.after(0, lambda: self.status_var.set(f"Translation error: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def _view_mode_changed(self):
        self._refresh_text_display()

    def _refresh_text_display(self):
        mode = self.view_mode_var.get()
        self.text_widget.delete("1.0", "end")
        if self.current_result:
            if mode == "text":
                self.text_widget.insert("1.0", self.current_result["text"])
            else:
                self.text_widget.insert("1.0", convert.generate_srt_content(self.current_result["segments"]))
        elif self.segments_accumulated:
            if mode == "text":
                txt = " ".join(s["text"] for s in self.segments_accumulated)
                self.text_widget.insert("1.0", txt)
            else:
                self.text_widget.insert("1.0", convert.generate_srt_content(self.segments_accumulated))

    def _attach_text_context_menu(self, widget):
        def show_menu(event):
            menu = tk.Menu(widget, tearoff=False)
            menu.add_command(label=self.parent.text("copy"), command=self.copy_text)
            menu.add_command(label=self.parent.text("select_all"), command=lambda: widget.tag_add("sel", "1.0", "end"))
            menu.tk_popup(event.x_root, event.y_root)

        widget.bind("<Button-3>", show_menu)

    def start_transcription(self):
        if self.transcribe_thread and self.transcribe_thread.is_alive():
            return

        if not convert.whisper_available():
            messagebox.showerror(
                self.parent.text("app_title"),
                "faster-whisper is not installed.\nPlease run: py -3.12 -m pip install faster-whisper",
            )
            return

        if not self.source_path and not self.media_files:
            messagebox.showwarning(self.parent.text("app_title"), self.parent.text("caption_no_source"))
            return

        # Save chosen settings
        model_id = self._get_model_id()
        lang_code = self._get_lang_code()
        translate_code = self._get_translate_code()
        self.parent.settings["caption_model"] = model_id
        self.parent.settings["caption_lang"] = lang_code or "auto"
        self.parent._save_settings()

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.burn_btn.configure(state="disabled")
        self.progress_val_var.set(0)
        self.status_var.set(self.parent.text("caption_loading"))
        self.cancel_event.clear()
        self.segments_accumulated = []
        self.current_result = None
        self.text_widget.delete("1.0", "end")

        is_folder = (self.source_path and self.source_path.is_dir()) or len(self.media_files) > 1

        self.transcribe_thread = threading.Thread(
            target=self._run_transcription,
            args=(
                self.source_path,
                is_folder,
                self.media_files,
                model_id,
                lang_code,
                translate_code,
                self.export_srt_var.get(),
                self.export_vtt_var.get(),
                self.export_txt_var.get(),
                self.burn_video_var.get(),
            ),
            daemon=True,
        )
        self.transcribe_thread.start()

    def _run_transcription(
        self,
        source_path,
        is_folder,
        media_files,
        model_id,
        lang_code,
        translate_code,
        export_srt,
        export_vtt,
        export_txt,
        burn_video,
    ):
        try:
            self.start_time = time.monotonic()
            if is_folder and len(media_files) > 1:
                total_files = len(media_files)
                for idx, fpath in enumerate(media_files):
                    if self.cancel_event.is_set():
                        raise convert.CancelledError("Operation canceled")

                    def _seg_cb(pct, seg_text, start, end, dur):
                        self.after(0, lambda p=pct, t=seg_text, s=start, e=end: self._on_segment(p, t, s, e, dur))

                    convert.transcribe_media(
                        source_path=fpath,
                        output_dir=self.output_dir,
                        model_size=model_id,
                        language=lang_code,
                        translate_to=translate_code,
                        export_srt=export_srt,
                        export_vtt=export_vtt,
                        export_txt=export_txt,
                        burn_to_video=burn_video,
                        progress_callback=_seg_cb,
                        cancel_callback=lambda: self.cancel_event.is_set(),
                    )
                self.after(0, lambda: self._on_finished(None, is_batch=True))
            else:
                target_file = source_path or (media_files[0] if media_files else None)
                if not target_file:
                    raise FileNotFoundError("No source file selected")

                def _seg_cb(pct, seg_text, start, end, dur):
                    self.after(0, lambda p=pct, t=seg_text, s=start, e=end: self._on_segment(p, t, s, e, dur))

                res = convert.transcribe_media(
                    source_path=target_file,
                    output_dir=self.output_dir,
                    model_size=model_id,
                    language=lang_code,
                    translate_to=translate_code,
                    export_srt=export_srt,
                    export_vtt=export_vtt,
                    export_txt=export_txt,
                    burn_to_video=burn_video,
                    progress_callback=_seg_cb,
                    cancel_callback=lambda: self.cancel_event.is_set(),
                )
                self.after(0, lambda: self._on_finished(res, is_batch=False))
        except convert.CancelledError:
            self.after(0, self._on_cancelled)
        except Exception as exc:
            self.after(0, lambda: self._on_error(str(exc)))

    def _update_model_status(self, _e=None):
        mid = self._get_selected_model_id()
        status = convert.get_whisper_model_status(mid)
        if status["is_downloaded"]:
            self.model_status_var.set(self.parent.text("caption_model_status_ready"))
            if hasattr(self, "model_status_label"):
                self.model_status_label.configure(foreground="#008800")
            if hasattr(self, "download_model_btn"):
                self.download_model_btn.configure(state="disabled", text=self.parent.text("caption_model_ready_btn"))
        else:
            self.model_status_var.set(
                self.parent.text("caption_model_status_needs_download", size=int(status["estimated_mb"]))
            )
            if hasattr(self, "model_status_label"):
                self.model_status_label.configure(foreground="#cc6600")
            if hasattr(self, "download_model_btn"):
                self.download_model_btn.configure(state="normal", text=self.parent.text("caption_download_model_btn"))

    def download_current_model(self):
        mid = self._get_selected_model_id()
        status = convert.get_whisper_model_status(mid)
        if status["is_downloaded"]:
            messagebox.showinfo(self.parent.text("app_title"), self.parent.text("caption_model_status_ready"))
            return

        self.cancel_event.clear()
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        if hasattr(self, "download_model_btn"):
            self.download_model_btn.configure(state="disabled")
        self.model_combo.configure(state="disabled")
        self.progress_bar.configure(mode="determinate", value=0)

        def prog_cb(pct, dl_bytes, tot_bytes, fname, speed, eta, tdir):
            dl_mb = dl_bytes / (1024 * 1024)
            tot_mb = tot_bytes / (1024 * 1024)
            eta_part = f" - {eta}" if eta else ""
            msg = self.parent.text(
                "caption_downloading_model",
                model=mid,
                dl_mb=dl_mb,
                tot_mb=tot_mb,
                pct=pct,
                speed=speed,
                eta_part=eta_part,
            )
            self.after(0, lambda: self.status_var.set(msg))
            self.after(0, lambda: self.progress_val_var.set(pct))

        def worker():
            try:
                convert.download_whisper_model(
                    model_size=mid,
                    progress_callback=prog_cb,
                    cancel_callback=self.cancel_event.is_set,
                )
                if self.cancel_event.is_set():
                    self.after(0, self._on_cancelled)
                    return
                self.after(0, lambda: self._on_model_download_done(mid))
            except convert.CancelledError:
                self.after(0, self._on_cancelled)
            except Exception as exc:
                if self.cancel_event.is_set() or "cancel" in str(exc).lower():
                    self.after(0, self._on_cancelled)
                    return
                self.after(0, lambda: self._on_error(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_model_download_done(self, model_id):
        self.progress_val_var.set(100)
        self.status_var.set(self.parent.text("caption_download_complete", model=model_id))
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.model_combo.configure(state="readonly")
        self._update_model_status()
        messagebox.showinfo(
            self.parent.text("app_title"),
            self.parent.text("caption_download_complete", model=model_id),
        )

    def _on_segment(self, percent, seg_text, start, end, duration):
        if not seg_text:
            return
        self.progress_val_var.set(percent)
        if seg_text.startswith("Downloading AI model") or seg_text.startswith("جاري تحميل") or "Loading Whisper" in seg_text:
            self.status_var.set(seg_text)
            return

        self.segments_accumulated.append({"start": start, "end": end, "text": seg_text})
        preview_text = seg_text if len(seg_text) < 35 else seg_text[:32] + "..."

        is_ar = self.parent.language_var.get() == "العربية"
        elapsed_str = ""
        eta_str = ""
        if hasattr(self, "start_time") and self.start_time:
            wall_elapsed = time.monotonic() - self.start_time
            elapsed_str = self.parent._format_seconds(wall_elapsed)
            if percent > 0:
                eta_sec = (wall_elapsed / percent) * (100 - percent)
                eta_str = self.parent._format_seconds(eta_sec)
            else:
                eta_str = self.parent.text("estimating")

        pos_str = ""
        if duration and duration > 0:
            pos_str = f" ({self.parent._format_seconds(end)} / {self.parent._format_seconds(duration)})"

        if is_ar:
            status = f"جاري التفريغ: {percent}%{pos_str}"
            if elapsed_str:
                status += f" | المنقضي: {elapsed_str} | المتبقي: ~{eta_str}"
        else:
            status = f"Transcribing: {percent}%{pos_str}"
            if elapsed_str:
                status += f" | Elapsed: {elapsed_str} | Remaining: ~{eta_str}"

        self.status_var.set(f"{status}: {preview_text}")

        mode = self.view_mode_var.get()
        if mode == "text":
            self.text_widget.insert("end", f"{seg_text} ")
        else:
            ts = convert.format_timestamp_srt(start)
            self.text_widget.insert("end", f"[{ts}] {seg_text}\n")
        self.text_widget.see("end")

    def _on_finished(self, result, is_batch=False):
        self.current_result = result
        self.progress_val_var.set(100)
        self.status_var.set(self.parent.text("caption_done"))
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.burn_btn.configure(state="normal")
        self._update_model_status()

        if result:
            self._refresh_text_display()
            self._refresh_source_info()
            fname = self.source_path.name if self.source_path else "file"
            self.parent._append_log(f"\n[Auto Caption] Done transcribing {fname}\n")
            if result.get("srt_path"):
                self.parent._append_log(f"[Auto Caption] Saved SRT: {result['srt_path']}\n")
            if result.get("burned_video"):
                self.parent._append_log(f"[Auto Caption] Captioned video: {result['burned_video']}\n")
                messagebox.showinfo(
                    self.parent.text("app_title"),
                    self.parent.text("caption_burned_success", filename=Path(result["burned_video"]).name),
                )
            self.text_widget.see("1.0")
        elif is_batch:
            self.text_widget.delete("1.0", "end")
            msg = f"Batch transcription completed for {len(self.media_files)} files.\nSaved to: {self.output_dir}"
            self.text_widget.insert("1.0", msg)
            self.parent._append_log(f"\n[Auto Caption] Batch completed for {len(self.media_files)} files.\n")

    def _on_cancelled(self):
        self.status_var.set(self.parent.text("canceled"))
        self.progress_val_var.set(0)
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.burn_btn.configure(state="normal")
        self.model_combo.configure(state="readonly")
        self._update_model_status()
        self._refresh_source_info()
        self.parent._append_log("\n[Auto Caption] Operation canceled.\n")

    def _on_error(self, err_msg):
        self.status_var.set(self.parent.text("caption_error", error=err_msg))
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.model_combo.configure(state="readonly")
        self._update_model_status()
        self._refresh_source_info()
        messagebox.showerror(self.parent.text("app_title"), self.parent.text("caption_error", error=err_msg))

    def cancel_transcription(self):
        self.cancel_event.set()
        convert.abort_whisper_download()
        self.status_var.set(self.parent.text("canceling"))
        self.stop_btn.configure(state="disabled")

    def copy_text(self):
        content = self.text_widget.get("1.0", "end-1c").strip()
        if not content:
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        orig = self.copy_btn.cget("text")
        self.copy_btn.configure(text=f"✓ {self.parent.text('copied')}")
        self.after(1400, lambda: self.copy_btn.configure(text=orig))

    def save_as(self):
        content = self.text_widget.get("1.0", "end-1c").strip()
        if not content:
            return
        mode = self.view_mode_var.get()
        ext = ".srt" if mode == "srt" else ".txt"
        base_name = f"{self.source_path.stem if self.source_path else 'transcript'}{ext}"
        init_dir = str(self.output_dir if self.output_dir.exists() else convert.APP_DIR)
        selected = filedialog.asksaveasfilename(
            title=self.parent.text("caption_save_as"),
            initialdir=init_dir,
            initialfile=base_name,
            filetypes=[("Text file", "*.txt"), ("SRT Subtitle", "*.srt"), ("All files", "*.*")],
            defaultextension=ext,
        )
        if selected:
            Path(selected).write_text(content, encoding="utf-8")
            messagebox.showinfo(self.parent.text("app_title"), self.parent.text("caption_saved"))

    def burn_subtitles_now(self):
        target_media = None
        capcut_hint = self.current_result.get("video_path") if self.current_result else None
        if self.source_path and self.source_path.is_file():
            if convert.has_video_stream(self.source_path):
                target_media = self.source_path
            else:
                matching = convert.find_matching_video(self.source_path, hint_path=capcut_hint)
                if matching:
                    if "_trim_" in self.source_path.stem:
                        a_dur = convert.get_media_duration(self.source_path) or 0
                        v_dur = convert.get_media_duration(matching) or 0
                        if abs(a_dur - v_dur) > 10:
                            target_media = self.source_path
                        else:
                            target_media = matching
                    else:
                        target_media = matching
                else:
                    target_media = self.source_path
        elif capcut_hint and Path(capcut_hint).is_file():
            target_media = Path(capcut_hint).resolve()

        if not target_media:
            init_dir = (
                (self.source_path.parent if self.source_path and self.source_path.is_file() else None)
                or self.output_dir
                or self.parent.last_media_dir
            )
            filetypes = [
                (self.parent.text("media_files"), " ".join(f"*{ext}" for ext in sorted(convert.MEDIA_EXTS))),
                (self.parent.text("video_files"), " ".join(f"*{ext}" for ext in sorted(convert.VIDEO_EXTS))),
                (self.parent.text("audio_files"), " ".join(f"*{ext}" for ext in sorted(convert.AUDIO_EXTS))),
                (self.parent.text("all_files"), "*.*"),
            ]
            chosen = filedialog.askopenfilename(
                title=self.parent.text("caption_select_video_to_burn"),
                initialdir=self.parent._dialog_dir(init_dir),
                filetypes=filetypes,
            )
            if not chosen:
                return
            target_media = Path(chosen).resolve()

        self.source_path = target_media
        self._refresh_source_info()

        if self.current_result and self.current_result.get("srt_path") and Path(self.current_result["srt_path"]).exists():
            srt_path = Path(self.current_result["srt_path"])
        else:
            srt_path = self.output_dir / f"{self.source_path.stem}.srt"
            if not srt_path.exists():
                if self.current_result and self.current_result.get("segments"):
                    srt_path.write_text(convert.generate_srt_content(self.current_result["segments"]), encoding="utf-8-sig")
                else:
                    messagebox.showwarning(self.parent.text("app_title"), "Please transcribe or import subtitles first.")
                    return

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.burn_btn.configure(state="disabled")
        self.status_var.set(f"{self.parent.text('caption_burning')} (0%)")
        self.progress_val_var.set(0)
        self.cancel_event.clear()
        burn_start_time = time.monotonic()

        def _worker():
            try:
                def _prog(pct, msg, cur, dur, tot):
                    self.after(0, lambda: self._on_burn_progress(pct, msg, cur, tot, burn_start_time))

                out_vid = convert.burn_subtitles_to_video(
                    video_path=self.source_path,
                    srt_path=srt_path,
                    output_dir=self.output_dir,
                    style_config=getattr(self.parent, "subtitle_style", None),
                    cancel_callback=lambda: self.cancel_event.is_set(),
                    progress_callback=_prog,
                )
                if self.cancel_event.is_set():
                    self.after(0, self._on_cancelled)
                    return
                self.after(0, lambda: self._on_burn_done(out_vid))
            except convert.CancelledError:
                self.after(0, self._on_cancelled)
            except Exception as exc:
                if self.cancel_event.is_set() or "cancel" in str(exc).lower():
                    self.after(0, self._on_cancelled)
                    return
                self.after(0, lambda: self._on_error(str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_burn_progress(self, percent, msg, cur=0, tot=0, start_time=None):
        self.progress_val_var.set(percent)
        is_ar = self.parent.language_var.get() == "العربية"
        elapsed_str = ""
        eta_str = ""
        if start_time:
            wall_elapsed = time.monotonic() - start_time
            elapsed_str = self.parent._format_seconds(wall_elapsed)
            if percent > 0:
                eta_sec = (wall_elapsed / percent) * (100 - percent)
                eta_str = self.parent._format_seconds(eta_sec)
            else:
                eta_str = self.parent.text("estimating")

        pos_str = ""
        if tot and tot > 0:
            pos_str = f" ({self.parent._format_seconds(cur)} / {self.parent._format_seconds(tot)})"

        if is_ar:
            status = f"جاري دمج الترجمة: {percent}%{pos_str}"
            if elapsed_str:
                status += f" | المنقضي: {elapsed_str} | المتبقي: ~{eta_str}"
        else:
            status = f"Burning subtitles: {percent}%{pos_str}"
            if elapsed_str:
                status += f" | Elapsed: {elapsed_str} | Remaining: ~{eta_str}"

        self.status_var.set(status)

    def _on_burn_done(self, out_vid):
        self.progress_val_var.set(100)
        self.status_var.set(self.parent.text("caption_done"))
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.burn_btn.configure(state="normal")
        self.parent._append_log(f"\n[Auto Caption] Burned subtitles video: {out_vid.name}\n")
        messagebox.showinfo(
            self.parent.text("app_title"),
            self.parent.text("caption_burned_success", filename=out_vid.name),
        )

    def open_output_folder(self):
        folder = self.output_dir
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)
        self.parent.open_folder(folder)

    def import_from_capcut(self):
        drafts = convert.get_capcut_drafts()
        if not drafts:
            messagebox.showinfo(
                self.parent.text("app_title"),
                self.parent.text("caption_no_capcut_drafts"),
            )
            return

        chosen_draft = drafts[0]
        if len(drafts) > 1:
            dlg = tk.Toplevel(self)
            dlg.title(self.parent.text("caption_capcut_dialog_title"))
            dlg.geometry("520x340")
            dlg.transient(self)
            dlg.grab_set()
            dlg.resizable(False, False)

            lbl = ttk.Label(
                dlg,
                text=self.parent.text("caption_capcut_select"),
                font=("Segoe UI", 10, "bold"),
            )
            lbl.pack(anchor="e" if self.is_ar else "w", padx=16, pady=(16, 8))

            listbox_frame = ttk.Frame(dlg)
            listbox_frame.pack(fill="both", expand=True, padx=16, pady=4)
            scrollbar = ttk.Scrollbar(listbox_frame)
            scrollbar.pack(side="right" if not self.is_ar else "left", fill="y")
            lb = tk.Listbox(
                listbox_frame,
                yscrollcommand=scrollbar.set,
                font=("Segoe UI", 10),
                selectmode="browse",
                exportselection=False,
                justify="right" if self.is_ar else "left",
            )
            lb.pack(side="left" if not self.is_ar else "right", fill="both", expand=True)
            scrollbar.config(command=lb.yview)

            for d in drafts:
                sub_txt = f"{d['subtitle_count']} مقطع" if self.is_ar else f"{d['subtitle_count']} segments"
                lb.insert("end", f"📅 {d['date']} | 📝 {sub_txt} | {d['name']}")
            lb.selection_set(0)

            selected_idx = [0]
            cancelled = [False]

            def on_ok():
                sel = lb.curselection()
                if sel:
                    selected_idx[0] = sel[0]
                dlg.destroy()

            def on_cancel():
                cancelled[0] = True
                dlg.destroy()

            lb.bind("<Double-Button-1>", lambda _e: on_ok())
            dlg.bind("<Return>", lambda _e: on_ok())
            dlg.bind("<Escape>", lambda _e: on_cancel())
            dlg.protocol("WM_DELETE_WINDOW", on_cancel)

            btn_box = ttk.Frame(dlg)
            btn_box.pack(fill="x", padx=16, pady=12)
            import_txt = "استيراد الترجمة" if self.is_ar else "Import Subtitles"
            ttk.Button(btn_box, text=import_txt, command=on_ok, style="Action.TButton").pack(side="left" if not self.is_ar else "right", padx=4)
            ttk.Button(btn_box, text=self.parent.text("close"), command=on_cancel).pack(side="right" if not self.is_ar else "left", padx=4)
            dlg.wait_window()

            if cancelled[0]:
                return
            chosen_draft = drafts[selected_idx[0]]

        out_dir = self.output_dir or Path.home()
        res = convert.extract_subtitles_from_capcut(chosen_draft["path"], output_dir=out_dir)
        if not res["segments"]:
            messagebox.showwarning(self.parent.text("app_title"), self.parent.text("caption_no_capcut_drafts"))
            return

        if res.get("video_path") and Path(res["video_path"]).exists():
            if not self.source_path or not self.source_path.is_file():
                self.source_path = Path(res["video_path"])
                self._refresh_source_info()

        self._on_finished(res, is_batch=False)
        self.text_widget.see("1.0")
        messagebox.showinfo(
            self.parent.text("app_title"),
            self.parent.text("caption_capcut_imported", count=len(res["segments"]), project=chosen_draft["name"]),
        )

    def close_dialog(self):
        if self.transcribe_thread and self.transcribe_thread.is_alive():
            if not messagebox.askyesno(self.parent.text("app_title"), self.parent.text("close_running")):
                return
            self.cancel_event.set()
            convert.abort_whisper_download()
        convert.abort_whisper_download()
        self.destroy()


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
        video_format = self.settings.get("video_format")
        if video_format not in convert.VIDEO_OUTPUT_FORMATS and video_format != "original":
            video_format = ".mp4"
        video_compression = self.settings.get("video_compression")
        if video_compression not in convert.VIDEO_COMPRESSION_PRESETS:
            video_compression = "Original"
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
        self.enhancement_key = "Off"
        self.enhancement_var = tk.StringVar(value="Off")
        self.format_options = [
            f"{ext} - {info['label']}" for ext, info in convert.OUTPUT_FORMATS.items()
        ]
        self.output_format_var = tk.StringVar(value=".mp3 - MP3")
        self.busy_widgets = []
        self.i18n_widgets = {}

        # Volume Booster state
        self.boost_gain_var = tk.DoubleVar(value=6.0)
        self.boost_gain_label_var = tk.StringVar(value="+6.0 dB (200% / Double)")
        self.boost_anti_clip_var = tk.BooleanVar(value=True)
        self.boost_stats_var = tk.StringVar(value="")
        self.boost_output_format_var = tk.StringVar(value="auto")

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
        self.settings["video_format"] = self.video_format_key
        self.settings["video_compression"] = self.video_compression_key
        self.settings["video_resolution"] = self.video_resolution_key
        self.settings["subtitle_style"] = getattr(self, "subtitle_style", {})
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
        lang = self.language_var.get() if hasattr(self, "language_var") else "English"
        if lang not in TRANSLATIONS:
            lang = "English"
        val = TRANSLATIONS[lang].get(key, TRANSLATIONS["English"].get(key, key))
        return val.format(**kwargs) if kwargs else val

    def _build_ui(self):
        style = ttk.Style(self)
        style.configure("Player.TButton", font=("Segoe UI Symbol", 9), padding=(4, 2))
        style.configure("PrimaryPlayer.TButton", font=("Segoe UI Symbol", 10, "bold"), padding=(6, 4))
        style.configure("Action.TButton", font=("Segoe UI", 10, "bold"), padding=(8, 4))

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # ------------------ Row 0: Header ------------------
        header = ttk.Frame(self, padding=(16, 12, 16, 6))
        header.grid(row=0, column=0, sticky="ew")
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

        self.about_button = ttk.Button(
            language_box,
            command=self.show_about_dialog,
            style="Player.TButton",
            width=11,
        )
        self.about_button.grid(row=0, column=2, padx=(8, 0), sticky="e")
        self.i18n_widgets["about_button"] = self.about_button

        self.i18n_widgets["subtitle"] = ttk.Label(header, foreground="#555555")
        self.i18n_widgets["subtitle"].grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))

        # ------------------ Row 1: Source Selection Card ------------------
        source_panel = ttk.LabelFrame(self, padding=(12, 8, 12, 8))
        source_panel.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 6))
        source_panel.columnconfigure(2, weight=1)
        self.i18n_widgets["source_group"] = source_panel

        self.choose_file_button = ttk.Button(source_panel, command=self.choose_input_file)
        self.choose_file_button.grid(row=0, column=0, sticky="w")
        self.choose_folder_button = ttk.Button(source_panel, command=self.choose_input_folder)
        self.choose_folder_button.grid(row=0, column=1, padx=(6, 0), sticky="w")
        ttk.Label(source_panel, textvariable=self.source_var, font=("Segoe UI", 9, "bold")).grid(
            row=0, column=2, padx=(10, 8), sticky="ew"
        )

        self.open_input_button = ttk.Button(source_panel, command=self.open_source, style="Player.TButton")
        self.open_input_button.grid(row=0, column=3, padx=(4, 0), sticky="e")
        self.open_output_button = ttk.Button(
            source_panel, command=lambda: self.open_folder(self.output_dir), style="Player.TButton"
        )
        self.open_output_button.grid(row=0, column=4, padx=(4, 0), sticky="e")

        self.i18n_widgets["output_label"] = ttk.Label(source_panel)
        self.i18n_widgets["output_label"].grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(source_panel, textvariable=self.output_var, foreground="#555555").grid(
            row=1, column=2, padx=(10, 8), pady=(6, 0), sticky="ew"
        )
        ttk.Label(source_panel, textvariable=self.count_var, foreground="#0066cc", font=("Segoe UI", 9, "bold")).grid(
            row=1, column=3, columnspan=2, padx=(4, 0), pady=(6, 0), sticky="e"
        )

        # ------------------ Row 2: Tabs Container (Notebook) ------------------
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 6))

        self.tab_convert = ttk.Frame(self.notebook, padding=12)
        self.tab_volume = ttk.Frame(self.notebook, padding=12)
        self.tab_player = ttk.Frame(self.notebook, padding=10)
        self.tab_caption = ttk.Frame(self.notebook, padding=12)
        self.tab_cover = ttk.Frame(self.notebook, padding=12)
        self.tab_youtube = ttk.Frame(self.notebook, padding=12)

        self.notebook.add(self.tab_convert, text=self.text("tab_convert"))
        self.notebook.add(self.tab_volume, text=self.text("tab_volume"))
        self.notebook.add(self.tab_player, text=self.text("tab_player"))
        self.notebook.add(self.tab_caption, text=self.text("tab_caption"))
        self.notebook.add(self.tab_cover, text=self.text("tab_cover"))
        self.notebook.add(self.tab_youtube, text=self.text("tab_youtube"))

        self._build_tab_convert(self.tab_convert)
        self._build_tab_volume(self.tab_volume)
        self._build_tab_player(self.tab_player)
        self._build_tab_caption(self.tab_caption)
        self._build_tab_cover(self.tab_cover)
        self._build_tab_youtube(self.tab_youtube)

        # ------------------ Row 3: Bottom Panel (Progress & Log) ------------------
        bottom_box = ttk.Frame(self, padding=(16, 0, 16, 10))
        bottom_box.grid(row=3, column=0, sticky="ew")
        bottom_box.columnconfigure(1, weight=1)

        prog_row = ttk.Frame(bottom_box)
        prog_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        prog_row.columnconfigure(1, weight=1)

        ttk.Label(prog_row, textvariable=self.progress_var, font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
        self.progress = ttk.Progressbar(prog_row, mode="indeterminate")
        self.progress.grid(row=0, column=1, padx=(12, 0), sticky="ew")

        log_frame = ttk.LabelFrame(bottom_box, padding=(8, 4, 8, 6))
        log_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        log_frame.columnconfigure(0, weight=1)
        self.i18n_widgets["log_group"] = log_frame

        self.log = tk.Text(log_frame, wrap="word", height=3, state="disabled", font=("Consolas", 8))
        self.log.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)

        footer = ttk.Frame(bottom_box)
        footer.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        footer.columnconfigure(0, weight=1)

        ttk.Label(footer, textvariable=self.status_var, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        self.dev_label = ttk.Label(
            footer,
            font=("Segoe UI", 9),
            foreground="#555555",
            cursor="hand2",
        )
        self.dev_label.grid(row=0, column=1, padx=(10, 0), sticky="e")
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
        ]
        self._sync_option_state()

    def _build_tab_convert(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)

        # Left Column: Audio Conversion
        audio_panel = ttk.LabelFrame(parent, padding=14)
        audio_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=2)
        audio_panel.columnconfigure(1, weight=1)
        self.i18n_widgets["conversion_group"] = audio_panel

        self.i18n_widgets["format_label"] = ttk.Label(audio_panel)
        self.i18n_widgets["format_label"].grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.format_combo = ttk.Combobox(
            audio_panel, textvariable=self.output_format_var, values=self.format_options, state="readonly", width=18
        )
        self.format_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=(0, 6))

        self.i18n_widgets["quality_label"] = ttk.Label(audio_panel)
        self.i18n_widgets["quality_label"].grid(row=1, column=0, sticky="w", pady=(0, 6))
        self.quality_combo = ttk.Combobox(
            audio_panel, textvariable=self.quality_var, values=convert.QUALITY_OPTIONS, state="readonly", width=18
        )
        self.quality_combo.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(0, 6))
        self.quality_combo.bind("<<ComboboxSelected>>", lambda _event: self._save_settings())

        self.i18n_widgets["enhance_label"] = ttk.Label(audio_panel)
        self.i18n_widgets["enhance_label"].grid(row=2, column=0, sticky="w", pady=(0, 10))
        self.enhancement_combo = ttk.Combobox(
            audio_panel,
            textvariable=self.enhancement_var,
            state="readonly",
            width=18,
        )
        self.enhancement_combo.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(0, 10))
        self.enhancement_combo.bind("<<ComboboxSelected>>", lambda _event: self._remember_enhancement_key())

        ttk.Separator(audio_panel, orient="horizontal").grid(row=3, column=0, columnspan=2, sticky="ew", pady=(2, 10))

        self.keep_original_check = ttk.Checkbutton(audio_panel, variable=self.keep_original_var, command=self._sync_option_state)
        self.keep_original_check.grid(row=4, column=0, columnspan=2, sticky="w", pady=2)

        self.skip_existing_check = ttk.Checkbutton(audio_panel, variable=self.skip_existing_var)
        self.skip_existing_check.grid(row=5, column=0, columnspan=2, sticky="w", pady=2)

        self.preview_check = ttk.Checkbutton(audio_panel, variable=self.preview_var)
        self.preview_check.grid(row=6, column=0, columnspan=2, sticky="w", pady=2)

        self.open_output_check = ttk.Checkbutton(audio_panel, variable=self.open_output_var)
        self.open_output_check.grid(row=7, column=0, columnspan=2, sticky="w", pady=2)

        audio_panel.rowconfigure(8, weight=1)
        self.run_button = ttk.Button(audio_panel, command=self.start_conversion, style="Action.TButton")
        self.run_button.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(12, 0))

        # Right Column: Video Conversion & Compression
        video_panel = ttk.LabelFrame(parent, padding=14)
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
        ttk.Label(v_stats, textvariable=self.video_estimate_var, foreground="#007700", font=("Segoe UI", 9)).pack(
            anchor="w", pady=(4, 0)
        )

        video_panel.rowconfigure(5, weight=1)
        self.compress_video_button = ttk.Button(
            video_panel,
            command=self.start_video_conversion,
            style="Action.TButton",
        )
        self.compress_video_button.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(12, 0))

    def _build_tab_volume(self, parent):
        parent.columnconfigure(0, weight=1)

        # Top Card: Audio Analysis
        analysis_box = ttk.LabelFrame(parent, padding=14)
        analysis_box.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        analysis_box.columnconfigure(0, weight=1)
        self.i18n_widgets["volume_analysis_group"] = analysis_box

        self.boost_stats_label = ttk.Label(
            analysis_box, textvariable=self.boost_stats_var, font=("Segoe UI", 10, "bold"), foreground="#0055aa"
        )
        self.boost_stats_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        btn_row = ttk.Frame(analysis_box)
        btn_row.grid(row=1, column=0, columnspan=2, sticky="w")

        self.detect_volume_button = ttk.Button(
            btn_row, text=self.text("detect_volume"), command=self.start_detect_volume, style="Player.TButton"
        )
        self.detect_volume_button.pack(side="left", padx=(0, 10))

        self.auto_peak_button = ttk.Button(
            btn_row, text=self.text("volume_normalize_peak"), command=self.start_auto_peak_boost, style="Player.TButton"
        )
        self.auto_peak_button.pack(side="left")

        # Bottom Card: Amplification Controls
        boost_box = ttk.LabelFrame(parent, padding=14)
        boost_box.grid(row=1, column=0, sticky="nsew")
        boost_box.columnconfigure(1, weight=1)
        self.i18n_widgets["volume_group"] = boost_box

        # Gain Slider Row
        self.i18n_widgets["volume_gain_label"] = ttk.Label(boost_box, font=("Segoe UI", 10, "bold"))
        self.i18n_widgets["volume_gain_label"].grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.boost_gain_scale = ttk.Scale(
            boost_box,
            from_=-12.0,
            to=30.0,
            variable=self.boost_gain_var,
            orient="horizontal",
            command=self._boost_gain_changed,
        )
        self.boost_gain_scale.grid(row=0, column=1, sticky="ew", padx=(10, 14), pady=(0, 10))

        self.boost_gain_display = ttk.Label(
            boost_box, textvariable=self.boost_gain_label_var, font=("Segoe UI", 11, "bold"), foreground="#cc3300", width=18
        )
        self.boost_gain_display.grid(row=0, column=2, sticky="w", pady=(0, 10))

        # Quick Presets Row
        preset_box = ttk.Frame(boost_box)
        preset_box.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 12))

        ttk.Label(preset_box, text="⚡ Presets:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 10))
        self.preset_btn_1 = ttk.Button(
            preset_box, text=self.text("volume_preset_light"), command=lambda: self.set_boost_preset(3.0), style="Player.TButton"
        )
        self.preset_btn_1.pack(side="left", padx=(0, 6))

        self.preset_btn_2 = ttk.Button(
            preset_box, text=self.text("volume_preset_double"), command=lambda: self.set_boost_preset(6.0), style="Player.TButton"
        )
        self.preset_btn_2.pack(side="left", padx=(0, 6))

        self.preset_btn_3 = ttk.Button(
            preset_box, text=self.text("volume_preset_high"), command=lambda: self.set_boost_preset(10.0), style="Player.TButton"
        )
        self.preset_btn_3.pack(side="left", padx=(0, 6))

        self.preset_btn_4 = ttk.Button(
            preset_box, text=self.text("volume_preset_extreme"), command=lambda: self.set_boost_preset(15.0), style="Player.TButton"
        )
        self.preset_btn_4.pack(side="left")

        # Anti-Clipping Limiter Checkbox
        self.boost_anti_clip_check = ttk.Checkbutton(
            boost_box, text=self.text("volume_anti_clipping"), variable=self.boost_anti_clip_var
        )
        self.boost_anti_clip_check.grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 10))

        # Output format dropdown
        fmt_row = ttk.Frame(boost_box)
        fmt_row.grid(row=3, column=0, columnspan=3, sticky="w", pady=(0, 16))
        self.i18n_widgets["boost_fmt_label"] = ttk.Label(fmt_row)
        self.i18n_widgets["boost_fmt_label"].pack(side="left", padx=(0, 8))
        self.boost_output_format_combo = ttk.Combobox(
            fmt_row,
            textvariable=self.boost_output_format_var,
            state="readonly",
            width=26,
            values=["auto", ".mp3", ".m4a", ".wav", ".flac"],
        )
        self.boost_output_format_combo.pack(side="left")
        self._refresh_boost_format_options()

        # Action Button
        self.boost_button = ttk.Button(
            boost_box,
            command=self.start_boost_volume,
            style="Action.TButton",
        )
        self.boost_button.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(8, 0))

    def _build_tab_player(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        player_panel = ttk.LabelFrame(parent, padding=8)
        player_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        player_panel.columnconfigure(0, weight=1)
        player_panel.rowconfigure(0, weight=1)
        self.i18n_widgets["media_player_group"] = player_panel

        self.video_surface = tk.Frame(player_panel, bg="black", height=240)
        self.video_surface.grid(row=0, column=0, sticky="nsew")
        self.video_surface.grid_propagate(False)
        self.video_surface.bind("<Double-Button-1>", lambda _e: self.toggle_video_size())

        player_timeline_row = ttk.Frame(player_panel)
        player_timeline_row.grid(row=1, column=0, sticky="ew", pady=(6, 0))
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
        ttk.Label(player_timeline_row, textvariable=self.timeline_text_var, font=("Consolas", 9)).grid(
            row=0, column=2, padx=(8, 0), sticky="e"
        )

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

        # Trimming Section
        controls = ttk.LabelFrame(parent, padding=(12, 8, 12, 10))
        controls.grid(row=1, column=0, sticky="ew")
        controls.columnconfigure(7, weight=1)
        self.i18n_widgets["tools_group"] = controls

        self.i18n_widgets["trim_start_label"] = ttk.Label(controls)
        self.i18n_widgets["trim_start_label"].grid(row=0, column=0, sticky="w")
        self.trim_start_entry = ttk.Entry(controls, textvariable=self.trim_start_var, width=10)
        self.trim_start_entry.grid(row=0, column=1, padx=(6, 0), sticky="w")
        self.mark_start_button = ttk.Button(controls, command=self.mark_trim_start, style="Player.TButton")
        self.mark_start_button.grid(row=0, column=2, padx=(6, 12), sticky="w")

        self.i18n_widgets["trim_end_label"] = ttk.Label(controls)
        self.i18n_widgets["trim_end_label"].grid(row=0, column=3, sticky="w")
        self.trim_end_entry = ttk.Entry(controls, textvariable=self.trim_end_var, width=10)
        self.trim_end_entry.grid(row=0, column=4, padx=(6, 0), sticky="w")
        self.mark_end_button = ttk.Button(controls, command=self.mark_trim_end, style="Player.TButton")
        self.mark_end_button.grid(row=0, column=5, padx=(6, 12), sticky="w")

        self.trim_extract_audio_check = ttk.Checkbutton(
            controls,
            text=self.text("trim_extract_audio"),
            variable=self.trim_extract_audio_var,
        )
        self.trim_extract_audio_check.grid(row=0, column=6, padx=(0, 12), sticky="w")

        self.trim_button = ttk.Button(controls, command=self.start_trim, style="Action.TButton")
        self.trim_button.grid(row=0, column=7, sticky="e")

    def _build_tab_caption(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        # Settings Card
        settings_box = ttk.LabelFrame(parent, padding=12)
        settings_box.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        settings_box.columnconfigure(5, weight=1)
        self.i18n_widgets["caption_settings_group"] = settings_box

        # Row 0: Model, Download Button & Language
        self.i18n_widgets["caption_model_label"] = ttk.Label(settings_box)
        self.i18n_widgets["caption_model_label"].grid(row=0, column=0, sticky="w")
        self.caption_model_combo = ttk.Combobox(
            settings_box, textvariable=self.caption_model_var, state="readonly", width=26
        )
        self.caption_model_combo.grid(row=0, column=1, padx=(6, 8), sticky="w")
        self.caption_model_combo.bind("<<ComboboxSelected>>", lambda _e: self._update_caption_model_status())

        self.caption_model_status_label = ttk.Label(
            settings_box, textvariable=self.caption_model_status_var, font=("Segoe UI", 9, "bold")
        )
        self.caption_model_status_label.grid(row=0, column=2, padx=(0, 8), sticky="w")

        self.caption_download_model_button = ttk.Button(
            settings_box,
            text=self.text("caption_download_model_btn"),
            command=self.download_selected_caption_model,
            style="Player.TButton",
        )
        self.caption_download_model_button.grid(row=0, column=3, padx=(0, 14), sticky="w")

        self.i18n_widgets["caption_lang_label"] = ttk.Label(settings_box)
        self.i18n_widgets["caption_lang_label"].grid(row=0, column=4, sticky="w")
        self.caption_lang_combo = ttk.Combobox(
            settings_box, textvariable=self.caption_lang_var, state="readonly", width=20
        )
        self.caption_lang_combo.grid(row=0, column=5, padx=(6, 0), sticky="w")

        # Row 1: Subtitle Translation & Models Directory
        models_dir_row = ttk.Frame(settings_box)
        models_dir_row.grid(row=1, column=0, columnspan=5, sticky="ew", pady=(4, 6))

        self.i18n_widgets["caption_translate_label"] = ttk.Label(
            models_dir_row, text=self.text("caption_translate_label"), font=("Segoe UI", 9)
        )
        self.i18n_widgets["caption_translate_label"].pack(side="left", padx=(0, 6))
        self.caption_translate_combo = ttk.Combobox(
            models_dir_row, textvariable=self.caption_translate_var, state="readonly", width=22
        )
        self.caption_translate_combo.pack(side="left", padx=(0, 16))

        self.i18n_widgets["caption_models_dir"] = ttk.Label(
            models_dir_row, text=self.text("caption_models_dir"), font=("Segoe UI", 9)
        )
        self.i18n_widgets["caption_models_dir"].pack(side="left", padx=(0, 6))
        self.caption_models_dir_path_label = ttk.Label(
            models_dir_row, textvariable=self.caption_models_dir_var, foreground="#555555", font=("Segoe UI", 8)
        )
        self.caption_models_dir_path_label.pack(side="left", padx=(0, 10))
        self.caption_open_models_button = ttk.Button(
            models_dir_row,
            text=self.text("caption_open_models_dir"),
            command=self.open_models_folder,
            style="Player.TButton",
        )
        self.caption_open_models_button.pack(side="left")

        # Row 2: Checkboxes
        check_row = ttk.Frame(settings_box)
        check_row.grid(row=2, column=0, columnspan=5, sticky="w", pady=(4, 8))
        self.caption_export_srt_check = ttk.Checkbutton(
            check_row, text=self.text("caption_export_srt"), variable=self.caption_export_srt_var
        )
        self.caption_export_srt_check.pack(side="left", padx=(0, 12))
        self.caption_export_vtt_check = ttk.Checkbutton(
            check_row, text=self.text("caption_export_vtt"), variable=self.caption_export_vtt_var
        )
        self.caption_export_vtt_check.pack(side="left", padx=(0, 12))
        self.caption_export_txt_check = ttk.Checkbutton(
            check_row, text=self.text("caption_export_txt"), variable=self.caption_export_txt_var
        )
        self.caption_export_txt_check.pack(side="left", padx=(0, 12))
        self.caption_burn_check = ttk.Checkbutton(
            check_row, text=self.text("caption_burn_video"), variable=self.caption_burn_var
        )
        self.caption_burn_check.pack(side="left")

        # Row 3: Actions Bar
        act_row = ttk.Frame(settings_box)
        act_row.grid(row=3, column=0, columnspan=5, sticky="ew")
        act_row.columnconfigure(4, weight=1)

        self.caption_start_button = ttk.Button(
            act_row, text=self.text("caption_start"), command=self.start_embedded_caption, style="Action.TButton"
        )
        self.caption_start_button.grid(row=0, column=0, padx=(0, 8), sticky="w")

        self.caption_stop_button = ttk.Button(
            act_row, text=self.text("caption_stop"), command=self.cancel_embedded_caption, state="disabled"
        )
        self.caption_stop_button.grid(row=0, column=1, padx=(0, 8), sticky="w")

        self.caption_import_capcut_button = ttk.Button(
            act_row, text=self.text("caption_import_capcut"), command=self.import_from_capcut
        )
        self.caption_import_capcut_button.grid(row=0, column=2, padx=(0, 12), sticky="w")

        self.caption_progress_bar = ttk.Progressbar(act_row, mode="determinate", length=140)
        self.caption_progress_bar.grid(row=0, column=3, padx=(0, 12), sticky="w")

        ttk.Label(act_row, textvariable=self.caption_status_var, font=("Segoe UI", 9, "bold"), foreground="#0066cc").grid(
            row=0, column=4, sticky="w"
        )

        # Output Card
        output_box = ttk.LabelFrame(parent, padding=12)
        output_box.grid(row=1, column=0, sticky="nsew")
        output_box.columnconfigure(0, weight=1)
        output_box.rowconfigure(1, weight=1)
        self.i18n_widgets["caption_output_group"] = output_box

        # View Mode switcher
        view_switch = ttk.Frame(output_box)
        view_switch.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self.caption_rb_bubbles = ttk.Radiobutton(
            view_switch,
            text=self.text("caption_tab_bubbles"),
            variable=self.caption_view_mode_var,
            value="bubbles",
            command=self._caption_view_mode_changed,
        )
        self.caption_rb_bubbles.pack(side="left", padx=(0, 14))

        self.caption_rb_text = ttk.Radiobutton(
            view_switch,
            text=self.text("caption_tab_text"),
            variable=self.caption_view_mode_var,
            value="text",
            command=self._caption_view_mode_changed,
        )
        self.caption_rb_text.pack(side="left", padx=(0, 14))

        self.caption_rb_srt = ttk.Radiobutton(
            view_switch,
            text=self.text("caption_tab_srt"),
            variable=self.caption_view_mode_var,
            value="srt",
            command=self._caption_view_mode_changed,
        )
        self.caption_rb_srt.pack(side="left")

        self.caption_style_btn = ttk.Button(
            view_switch,
            text=self.text("caption_style_btn"),
            command=self.open_subtitle_style_dialog,
            style="Player.TButton",
        )
        self.caption_style_btn.pack(side="right")

        # 1. Text View Container (For Plain Text & SRT)
        self.caption_text_container = ttk.Frame(output_box)
        self.caption_text_container.columnconfigure(0, weight=1)
        self.caption_text_container.rowconfigure(0, weight=1)

        self.caption_text_view = tk.Text(
            self.caption_text_container, wrap="word", height=6, font=("Segoe UI", 10), state="disabled", bg="#fafafa"
        )
        self.caption_text_view.grid(row=0, column=0, sticky="nsew")
        txt_scroll = ttk.Scrollbar(self.caption_text_container, orient="vertical", command=self.caption_text_view.yview)
        txt_scroll.grid(row=0, column=1, sticky="ns")
        self.caption_text_view.configure(yscrollcommand=txt_scroll.set)

        # 2. Interactive Segment Bubbles Container (Default)
        self.caption_bubbles_container = ttk.Frame(output_box)
        self.caption_bubbles_container.columnconfigure(0, weight=1)
        self.caption_bubbles_container.rowconfigure(1, weight=1)

        # Toolbar for Bubbles
        bubble_bar = ttk.Frame(self.caption_bubbles_container)
        bubble_bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        is_ar = self.language_var.get() == "العربية"
        ttk.Label(bubble_bar, text="🔍").pack(side="left" if not is_ar else "right", padx=(0, 4))
        self.bubble_search_entry = ttk.Entry(bubble_bar, textvariable=self.bubble_search_var, width=22)
        self.bubble_search_entry.pack(side="left" if not is_ar else "right", padx=(0, 6))
        self._attach_entry_context_menu(self.bubble_search_entry)

        self.bubble_clear_btn = ttk.Button(
            bubble_bar, text="✖", width=3, command=lambda: self.bubble_search_var.set(""), style="Player.TButton"
        )
        self.bubble_clear_btn.pack(side="left" if not is_ar else "right", padx=(0, 10))

        self.bubble_add_btn = ttk.Button(
            bubble_bar,
            text="➕ " + self.text("sub_add_segment"),
            command=self._add_new_bubble_segment,
            style="Player.TButton",
        )
        self.bubble_add_btn.pack(side="left" if not is_ar else "right", padx=(0, 12))

        self.bubble_count_label = ttk.Label(bubble_bar, text="", font=("Segoe UI", 9, "bold"), foreground="#0969da")
        self.bubble_count_label.pack(side="left" if not is_ar else "right", padx=(0, 12))

        # Pagination Controls
        pag_side = "right" if not is_ar else "left"
        self.bubble_btn_last = ttk.Button(bubble_bar, text="⏭", width=3, command=self._bubble_page_last, style="Player.TButton")
        self.bubble_btn_last.pack(side=pag_side, padx=1)

        self.bubble_btn_next = ttk.Button(bubble_bar, text="▶" if not is_ar else "◀", width=3, command=self._bubble_page_next, style="Player.TButton")
        self.bubble_btn_next.pack(side=pag_side, padx=1)

        self.bubble_page_label = ttk.Label(bubble_bar, text="1 / 1", font=("Segoe UI", 9, "bold"))
        self.bubble_page_label.pack(side=pag_side, padx=6)

        self.bubble_btn_prev = ttk.Button(bubble_bar, text="◀" if not is_ar else "▶", width=3, command=self._bubble_page_prev, style="Player.TButton")
        self.bubble_btn_prev.pack(side=pag_side, padx=1)

        self.bubble_btn_first = ttk.Button(bubble_bar, text="⏮", width=3, command=self._bubble_page_first, style="Player.TButton")
        self.bubble_btn_first.pack(side=pag_side, padx=1)

        # Scrollable Canvas for Cards
        canvas_box = ttk.Frame(self.caption_bubbles_container)
        canvas_box.grid(row=1, column=0, sticky="nsew")
        canvas_box.columnconfigure(0, weight=1)
        canvas_box.rowconfigure(0, weight=1)

        self.bubble_canvas = tk.Canvas(canvas_box, bg="#f6f8fa", highlightthickness=1, highlightbackground="#e1e4e8")
        self.bubble_canvas.grid(row=0, column=0, sticky="nsew")

        self.bubble_scrollbar = ttk.Scrollbar(canvas_box, orient="vertical", command=self.bubble_canvas.yview)
        self.bubble_scrollbar.grid(row=0, column=1, sticky="ns")
        self.bubble_canvas.configure(yscrollcommand=self.bubble_scrollbar.set)

        self.bubble_inner = ttk.Frame(self.bubble_canvas)
        self.bubble_inner_id = self.bubble_canvas.create_window((0, 0), window=self.bubble_inner, anchor="nw")

        def _on_canvas_configure(event):
            self.bubble_canvas.itemconfig(self.bubble_inner_id, width=event.width)

        self.bubble_canvas.bind("<Configure>", _on_canvas_configure)
        self.bubble_inner.bind("<Configure>", lambda _e: self.bubble_canvas.configure(scrollregion=self.bubble_canvas.bbox("all")))

        def _on_bubble_mousewheel(event):
            if hasattr(event, "delta") and event.delta:
                self.bubble_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.bubble_canvas.bind_all("<MouseWheel>", _on_bubble_mousewheel)

        # Empty state message
        self.bubble_empty_label = ttk.Label(
            self.bubble_inner,
            text=self.text("sub_no_segments"),
            foreground="#666666",
            font=("Segoe UI", 10),
            padding=(20, 30),
        )
        self.bubble_empty_label.pack(fill="x", pady=20)

        # Grid default view (bubbles)
        self.caption_bubbles_container.grid(row=1, column=0, sticky="nsew")

        # Action Buttons
        tools_row = ttk.Frame(output_box)
        tools_row.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        self.caption_copy_button = ttk.Button(
            tools_row, text=self.text("caption_copy"), command=self.copy_embedded_caption, style="Player.TButton"
        )
        self.caption_copy_button.pack(side="left", padx=(0, 8))

        self.caption_save_button = ttk.Button(
            tools_row, text=self.text("caption_save_as"), command=self.save_embedded_caption_as, style="Player.TButton"
        )
        self.caption_save_button.pack(side="left", padx=(0, 8))

        self.caption_burn_button = ttk.Button(
            tools_row, text=self.text("caption_burn_now"), command=self.burn_embedded_caption, style="Player.TButton"
        )
        self.caption_burn_button.pack(side="left", padx=(0, 8))

        self.caption_burn_cancel_button = ttk.Button(
            tools_row,
            text=self.text("caption_stop"),
            command=self.cancel_embedded_caption,
            state="disabled",
            style="Player.TButton",
        )
        self.caption_burn_cancel_button.pack(side="left", padx=(0, 8))

        self.caption_translate_button = ttk.Button(
            tools_row,
            text=self.text("caption_translate_btn"),
            command=self.translate_embedded_caption_text,
            style="Player.TButton",
        )
        self.caption_translate_button.pack(side="left", padx=(0, 8))

        self.caption_burn_status_label = ttk.Label(
            tools_row,
            textvariable=self.caption_status_var,
            font=("Segoe UI", 9, "bold"),
            foreground="#0066cc",
        )
        self.caption_burn_status_label.pack(side="left", padx=(8, 8))

        self.caption_open_folder_button = ttk.Button(
            tools_row,
            text=self.text("caption_open_folder"),
            command=lambda: self.open_folder(self.output_dir),
            style="Player.TButton",
        )
        self.caption_open_folder_button.pack(side="right")

    def _build_tab_cover(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        search_panel = ttk.LabelFrame(parent, padding=16)
        search_panel.grid(row=0, column=0, sticky="nsew")
        search_panel.columnconfigure(1, weight=1)
        self.i18n_widgets["cover_group"] = search_panel

        self.i18n_widgets["manual_search_label"] = ttk.Label(search_panel)
        self.i18n_widgets["manual_search_label"].grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.manual_search_entry = ttk.Entry(search_panel, textvariable=self.manual_search_var)
        self.manual_search_entry.grid(row=0, column=1, padx=(10, 0), sticky="ew", pady=(0, 10))
        self._attach_entry_context_menu(self.manual_search_entry)

        self.custom_cover_check = ttk.Checkbutton(
            search_panel, variable=self.custom_cover_var, command=self._sync_option_state
        )
        self.custom_cover_check.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="w")

        custom_cover_row = ttk.Frame(search_panel)
        custom_cover_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        custom_cover_row.columnconfigure(1, weight=1)

        self.choose_cover_button = ttk.Button(custom_cover_row, command=self.choose_custom_cover, style="Player.TButton")
        self.choose_cover_button.grid(row=0, column=0, sticky="w")
        ttk.Label(custom_cover_row, textvariable=self.custom_cover_text_var, foreground="#555555").grid(
            row=0, column=1, padx=(10, 0), sticky="ew"
        )

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

        dest_row = ttk.Frame(youtube_panel)
        dest_row.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(16, 0))
        dest_row.columnconfigure(1, weight=1)

        self.choose_youtube_output_button = ttk.Button(dest_row, command=self.choose_youtube_output_folder, style="Player.TButton")
        self.choose_youtube_output_button.grid(row=0, column=0, sticky="w")
        ttk.Label(dest_row, textvariable=self.youtube_detail_var, foreground="#0066cc", font=("Segoe UI", 9)).grid(
            row=0, column=1, padx=(10, 0), sticky="w"
        )

    # ------------------ Volume Booster Methods ------------------
    def _boost_gain_changed(self, _val=None):
        db = round(self.boost_gain_var.get(), 1)
        ratio = 10.0 ** (db / 20.0)
        pct = int(ratio * 100)
        sign = "+" if db > 0 else ""
        self.boost_gain_label_var.set(f"{sign}{db:.1f} dB ({pct}%)")

    def set_boost_preset(self, db_val):
        self.boost_gain_var.set(db_val)
        self._boost_gain_changed()

    def start_detect_volume(self):
        if not self.media_files:
            messagebox.showwarning(self.text("app_title"), self.text("choose_single_trim"))
            return
        target_file = self.media_files[0]
        self.boost_stats_var.set(self.text("detecting_volume"))

        def worker():
            res = convert.detect_audio_volume(target_file)
            if res:
                mean_db = res.get("mean_volume", -99.0)
                max_db = res.get("max_volume", 0.0)
                suggested = round(max(0.0, -max_db - 0.5), 1)
                msg = (
                    self.text("volume_current_level", mean=mean_db, max=max_db)
                    + " | "
                    + self.text("volume_suggested", gain=suggested)
                )
                self.after(0, lambda: self.boost_stats_var.set(msg))
                self.after(0, lambda: self.set_boost_preset(suggested))
            else:
                self.after(0, lambda: self.boost_stats_var.set(self.text("error_check_log")))

        threading.Thread(target=worker, daemon=True).start()

    def start_auto_peak_boost(self):
        if not self.media_files:
            messagebox.showwarning(self.text("app_title"), self.text("choose_single_trim"))
            return
        target_file = self.media_files[0]
        self.boost_stats_var.set(self.text("detecting_volume"))

        def worker():
            res = convert.detect_audio_volume(target_file)
            if res:
                max_db = res.get("max_volume", 0.0)
                headroom = round(max(0.0, -max_db - 0.5), 1)
                self.after(0, lambda: self.set_boost_preset(headroom))
                self.after(100, self.start_boost_volume)
            else:
                self.after(0, lambda: self.boost_stats_var.set(self.text("error_check_log")))

        threading.Thread(target=worker, daemon=True).start()

    def start_boost_volume(self):
        if self.worker and self.worker.is_alive():
            return
        if not self.input_path or not self.media_files:
            messagebox.showwarning(self.text("app_title"), self.text("no_media"))
            return

        gain_db = round(self.boost_gain_var.get(), 1)
        anti_clip = self.boost_anti_clip_var.get()
        out_fmt = self.boost_output_format_var.get()
        if out_fmt.startswith("auto") or out_fmt.startswith("Same") or out_fmt.startswith("نفس"):
            out_fmt = None
        else:
            out_fmt = out_fmt.split(" ", 1)[0]

        self._clear_log()
        self._begin_operation("boost", self.boost_button)
        self._append_log(self.text("boosting_volume") + f" (Gain: {gain_db} dB)\n")
        self.status_var.set(self.text("boosting_volume"))
        self._set_busy(True)
        self.progress.configure(mode="determinate", maximum=max(len(self.media_files), 1) * 100, value=0)

        def worker():
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            writer = QueueWriter(self.messages)
            sys.stdout = writer
            sys.stderr = writer
            try:
                def prog_cb(curr, tot, path, pct=100, msg=""):
                    fname = path.name if hasattr(path, "name") else str(path)
                    self.messages.put(("progress", curr, tot, fname, pct))

                results = convert.batch_boost_volume(
                    self.media_files,
                    output_dir=self.output_dir,
                    gain_db=gain_db,
                    anti_clipping=anti_clip,
                    output_ext=out_fmt,
                    progress_callback=prog_cb,
                    cancel_callback=self._operation_canceled,
                )
                self.messages.put(f"\nBoost completed! Saved {len(results)} files in {self.output_dir}\n")
                self.messages.put("\n__DONE__")
            except Exception as exc:
                self.messages.put(f"\nError boosting volume: {exc}\n")
                self.messages.put("\n__FAILED__")
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

        self.worker = threading.Thread(target=worker, daemon=True)
        self.worker.start()

    def _refresh_boost_format_options(self):
        is_ar = self.language_var.get() == "العربية"
        auto_label = "نفس الصيغة الأصلية" if is_ar else "Same as input (Auto)"
        self.boost_output_format_combo.configure(
            values=[auto_label, ".mp3 - MP3", ".m4a - AAC / M4A", ".wav - WAV", ".flac - FLAC"]
        )
        cur = self.boost_output_format_var.get()
        if not cur or cur.startswith("auto") or cur.startswith("Same") or cur.startswith("نفس"):
            self.boost_output_format_var.set(auto_label)

    # ------------------ Auto Caption Methods ------------------
    def _refresh_caption_options(self):
        is_ar = self.language_var.get() == "العربية"
        models = [
            "Small (⚡ حوالي 465MB - موصى به: توازن ممتاز ودقة عالية)" if is_ar else "Small (⚡ ~465MB - Recommended: High Accuracy & Balanced)",
            "Base (🚀 حوالي 140MB - خفيف وسريع)" if is_ar else "Base (🚀 ~140MB - Fast & Lightweight)",
            "Turbo (💎 حوالي 1.5GB - أعلى دقة مثل CapCut و NoteGPT)" if is_ar else "Turbo (💎 ~1.5GB - Max Accuracy / CapCut & NoteGPT)",
            "Tiny (⚠️ حوالي 75MB - فائق السرعة / دقة منخفضة)" if is_ar else "Tiny (⚠️ ~75MB - Ultra Fast, Low Accuracy)",
            "Medium (💎 حوالي 1.5GB - دقة عالية جداً)" if is_ar else "Medium (~1.5GB - Very High Accuracy)",
        ]
        self.caption_model_combo.configure(values=models)
        cur_m = self.caption_model_var.get().lower()
        if "tiny" in cur_m:
            self.caption_model_var.set(models[3])
        elif "base" in cur_m:
            self.caption_model_var.set(models[1])
        elif "turbo" in cur_m:
            self.caption_model_var.set(models[2])
        elif "medium" in cur_m:
            self.caption_model_var.set(models[4])
        else:
            self.caption_model_var.set(models[0])

        langs = [
            "كشف تلقائي للغة" if is_ar else "Auto Detect",
            "العربية (Arabic)",
            "الإنجليزية (English)",
            "الفرنسية (French)",
            "الإسبانية (Spanish)",
            "الألمانية (German)",
            "الإيطالية (Italian)",
            "التركية (Turkish)",
            "الروسية (Russian)",
            "الصينية (Chinese)",
            "اليابانية (Japanese)",
            "الكورية (Korean)",
            "الأوردو (Urdu)",
        ]
        self.caption_lang_combo.configure(values=langs)
        if not self.caption_lang_var.get() or self.caption_lang_var.get() in {"auto", "Auto Detect", "كشف تلقائي للغة"}:
            self.caption_lang_var.set(langs[0])

        trans_langs = [
            "نفس لغة الصوت الأصلية (بدون ترجمة)" if is_ar else "Original Audio Language (No Translation)",
            "العربية (Arabic)",
            "الإنجليزية (English)",
            "الفرنسية (French)",
            "الإسبانية (Spanish)",
            "الألمانية (German)",
            "الإيطالية (Italian)",
            "التركية (Turkish)",
            "الروسية (Russian)",
            "الصينية (Chinese)",
            "اليابانية (Japanese)",
            "الكورية (Korean)",
        ]
        if hasattr(self, "caption_translate_combo"):
            self.caption_translate_combo.configure(values=trans_langs)
            if not self.caption_translate_var.get():
                self.caption_translate_var.set(trans_langs[0])

        self._update_caption_model_status()

    def open_models_folder(self):
        models_dir = convert.get_whisper_models_dir()
        self.open_folder(models_dir)

    def _get_current_caption_model_id(self):
        chosen_m = self.caption_model_var.get().lower()
        if "tiny" in chosen_m:
            return "tiny"
        elif "base" in chosen_m:
            return "base"
        elif "small" in chosen_m:
            return "small"
        elif "medium" in chosen_m:
            return "medium"
        return "turbo"

    def _update_caption_model_status(self):
        model_name = self._get_current_caption_model_id()
        status = convert.get_whisper_model_status(model_name)
        if status["is_downloaded"]:
            self.caption_model_status_var.set(self.text("caption_model_status_ready"))
            if hasattr(self, "caption_model_status_label"):
                self.caption_model_status_label.configure(foreground="#008800")
            if hasattr(self, "caption_download_model_button"):
                self.caption_download_model_button.configure(state="disabled", text=self.text("caption_model_ready_btn"))
        else:
            self.caption_model_status_var.set(
                self.text("caption_model_status_needs_download", size=int(status["estimated_mb"]))
            )
            if hasattr(self, "caption_model_status_label"):
                self.caption_model_status_label.configure(foreground="#cc6600")
            if hasattr(self, "caption_download_model_button"):
                self.caption_download_model_button.configure(state="normal", text=self.text("caption_download_model_btn"))

    def download_selected_caption_model(self):
        chosen_m = self.caption_model_var.get().lower()
        if "tiny" in chosen_m:
            model_name = "tiny"
        elif "base" in chosen_m:
            model_name = "base"
        elif "small" in chosen_m:
            model_name = "small"
        elif "medium" in chosen_m:
            model_name = "medium"
        else:
            model_name = "turbo"

        status = convert.get_whisper_model_status(model_name)
        if status["is_downloaded"]:
            messagebox.showinfo(self.text("app_title"), self.text("caption_model_status_ready"))
            return

        self.caption_cancel_event.clear()
        self.caption_start_button.configure(state="disabled")
        self.caption_stop_button.configure(state="normal")
        if hasattr(self, "caption_download_model_button"):
            self.caption_download_model_button.configure(state="disabled")
        self.caption_model_combo.configure(state="disabled")
        self.caption_progress_bar.configure(mode="determinate", value=0)

        def prog_cb(pct, dl_bytes, tot_bytes, fname, speed, eta, tdir):
            dl_mb = dl_bytes / (1024 * 1024)
            tot_mb = tot_bytes / (1024 * 1024)
            eta_part = f" - {eta}" if eta else ""
            msg = self.text(
                "caption_downloading_model",
                model=model_name,
                dl_mb=dl_mb,
                tot_mb=tot_mb,
                pct=pct,
                speed=speed,
                eta_part=eta_part,
            )
            self.after(0, lambda: self.caption_status_var.set(msg))
            self.after(0, lambda: self.caption_progress_bar.configure(value=pct))

        def worker():
            try:
                convert.download_whisper_model(
                    model_size=model_name,
                    progress_callback=prog_cb,
                    cancel_callback=self.caption_cancel_event.is_set,
                )
                if self.caption_cancel_event.is_set():
                    self.after(0, self._on_embedded_caption_cancel)
                    return
                self.after(0, lambda: self._on_caption_model_download_done(model_name))
            except convert.CancelledError:
                self.after(0, self._on_embedded_caption_cancel)
            except Exception as exc:
                if self.caption_cancel_event.is_set() or "cancel" in str(exc).lower():
                    self.after(0, self._on_embedded_caption_cancel)
                    return
                self.after(0, lambda: self._on_embedded_caption_error(exc))

        self.caption_download_thread = threading.Thread(target=worker, daemon=True)
        self.caption_download_thread.start()

    def _on_caption_model_download_done(self, model_name):
        self.caption_progress_bar.configure(value=100)
        self.caption_status_var.set(self.text("caption_download_complete", model=model_name))
        self.caption_start_button.configure(state="normal")
        self.caption_stop_button.configure(state="disabled")
        self.caption_model_combo.configure(state="readonly")
        self._update_caption_model_status()
        messagebox.showinfo(
            self.text("app_title"),
            self.text("caption_download_complete", model=model_name),
        )

    def open_subtitle_style_dialog(self):
        dlg = SubtitleStyleDialog(self)
        dlg.grab_set()

    def _caption_view_mode_changed(self):
        mode = self.caption_view_mode_var.get()
        if mode == "bubbles":
            if hasattr(self, "caption_text_container"):
                self.caption_text_container.grid_remove()
            if hasattr(self, "caption_bubbles_container"):
                self.caption_bubbles_container.grid(row=1, column=0, sticky="nsew")
            self._refresh_bubbles_ui()
        else:
            if hasattr(self, "caption_bubbles_container"):
                self.caption_bubbles_container.grid_remove()
            if hasattr(self, "caption_text_container"):
                self.caption_text_container.grid(row=1, column=0, sticky="nsew")
            self.caption_text_view.configure(state="normal")
            self.caption_text_view.delete("1.0", "end")
            if self.caption_current_result:
                if mode == "text":
                    self.caption_text_view.insert("end", self.caption_current_result.get("text", ""))
                else:
                    self.caption_text_view.insert("end", self.caption_current_result.get("srt", ""))
            self.caption_text_view.configure(state="disabled")

    def _on_bubble_search_changed(self):
        self.bubble_current_page = 0
        self._refresh_bubbles_ui()

    def _bubble_page_first(self):
        self.bubble_current_page = 0
        self._refresh_bubbles_ui()

    def _bubble_page_prev(self):
        if self.bubble_current_page > 0:
            self.bubble_current_page -= 1
            self._refresh_bubbles_ui()

    def _bubble_page_next(self):
        segments = self.caption_current_result.get("segments", []) if self.caption_current_result else []
        q = self.bubble_search_var.get().strip().lower()
        if q:
            filtered_count = sum(1 for s in segments if q in s.get("text", "").lower())
        else:
            filtered_count = len(segments)
        import math
        total_pages = max(1, math.ceil(filtered_count / self.bubble_page_size))
        if self.bubble_current_page < total_pages - 1:
            self.bubble_current_page += 1
            self._refresh_bubbles_ui()

    def _bubble_page_last(self):
        segments = self.caption_current_result.get("segments", []) if self.caption_current_result else []
        q = self.bubble_search_var.get().strip().lower()
        if q:
            filtered_count = sum(1 for s in segments if q in s.get("text", "").lower())
        else:
            filtered_count = len(segments)
        import math
        total_pages = max(1, math.ceil(filtered_count / self.bubble_page_size))
        self.bubble_current_page = max(0, total_pages - 1)
        self._refresh_bubbles_ui()

    def _refresh_bubbles_ui(self):
        if not hasattr(self, "bubble_inner"):
            return

        for child in self.bubble_inner.winfo_children():
            child.destroy()

        segments = self.caption_current_result.get("segments", []) if self.caption_current_result else []
        if not segments:
            empty_lbl = ttk.Label(
                self.bubble_inner,
                text=self.text("sub_no_segments"),
                foreground="#666666",
                font=("Segoe UI", 10),
                padding=(20, 24),
            )
            empty_lbl.pack(fill="x", pady=20)
            self.bubble_page_label.configure(text="1 / 1")
            self.bubble_count_label.configure(text="")
            self.bubble_btn_prev.configure(state="disabled")
            self.bubble_btn_next.configure(state="disabled")
            self.bubble_btn_first.configure(state="disabled")
            self.bubble_btn_last.configure(state="disabled")
            return

        q = self.bubble_search_var.get().strip().lower()
        if q:
            filtered = [(idx, seg) for idx, seg in enumerate(segments) if q in seg.get("text", "").lower()]
        else:
            filtered = [(idx, seg) for idx, seg in enumerate(segments)]

        import math
        total_items = len(filtered)
        total_pages = max(1, math.ceil(total_items / self.bubble_page_size))
        self.bubble_current_page = max(0, min(self.bubble_current_page, total_pages - 1))

        start_idx = self.bubble_current_page * self.bubble_page_size
        end_idx = min(start_idx + self.bubble_page_size, total_items)
        page_items = filtered[start_idx:end_idx]

        self.bubble_page_label.configure(text=f"{self.bubble_current_page + 1} / {total_pages}")
        self.bubble_btn_first.configure(state="normal" if self.bubble_current_page > 0 else "disabled")
        self.bubble_btn_prev.configure(state="normal" if self.bubble_current_page > 0 else "disabled")
        self.bubble_btn_next.configure(state="normal" if self.bubble_current_page < total_pages - 1 else "disabled")
        self.bubble_btn_last.configure(state="normal" if self.bubble_current_page < total_pages - 1 else "disabled")

        is_ar = self.language_var.get() == "العربية"
        if q:
            cnt_txt = f"{self.text('sub_total_segments', count=total_items)} (فلترة من {len(segments)})" if is_ar else f"{total_items} segments (filtered from {len(segments)})"
        else:
            cnt_txt = self.text("sub_total_segments", count=len(segments))
        range_str = f"[{start_idx + 1}-{end_idx}]" if total_items > 0 else "[0-0]"
        self.bubble_count_label.configure(text=f"📊 {cnt_txt} {range_str}")

        for orig_idx, seg in page_items:
            card = tk.Frame(self.bubble_inner, bg="#ffffff", bd=1, relief="solid", padx=8, pady=6)
            card.pack(fill="x", padx=8, pady=4)

            # Header row
            hdr = tk.Frame(card, bg="#ffffff")
            hdr.pack(fill="x", pady=(0, 4))

            idx_lbl = tk.Label(hdr, text=f"#{orig_idx + 1}", font=("Segoe UI", 9, "bold"), fg="#0969da", bg="#ffffff")
            idx_lbl.pack(side="left" if not is_ar else "right", padx=(0, 8))

            s_sec = seg.get("start", 0)
            e_sec = seg.get("end", 0)
            s_ts = convert.format_timestamp_srt(s_sec)[:8] + "." + str(int((s_sec % 1) * 100)).zfill(2)
            e_ts = convert.format_timestamp_srt(e_sec)[:8] + "." + str(int((e_sec % 1) * 100)).zfill(2)
            ts_lbl = tk.Label(hdr, text=f"⏱ {s_ts} ➔ {e_ts}", font=("Segoe UI", 8), fg="#57606a", bg="#ffffff")
            ts_lbl.pack(side="left" if not is_ar else "right", padx=(0, 8))

            btn_side = "right" if not is_ar else "left"

            del_btn = ttk.Button(hdr, text="🗑 " + self.text("sub_del_segment"), width=8, style="Player.TButton", command=lambda i=orig_idx: self._delete_bubble_segment(i))
            del_btn.pack(side=btn_side, padx=2)

            ins_btn = ttk.Button(hdr, text="➕", width=3, style="Player.TButton", command=lambda i=orig_idx: self._insert_bubble_segment_after(i))
            ins_btn.pack(side=btn_side, padx=2)

            if self.input_path and self.input_path.is_file():
                play_btn = ttk.Button(hdr, text="▶", width=3, style="Player.TButton", command=lambda s=s_sec, e=e_sec: self._play_bubble_segment(s, e))
                play_btn.pack(side=btn_side, padx=2)

            # Text Box
            txt_box = tk.Text(card, wrap="word", height=2, font=("Segoe UI", 10), bg="#fafbfc", bd=1, relief="solid", fg="#1f2328")
            txt_box.pack(fill="x")
            txt_box.insert("1.0", seg.get("text", ""))
            self._attach_text_context_menu(txt_box)

            def _on_key(event, idx=orig_idx, widget=txt_box):
                self._on_bubble_text_edited(idx, widget)

            txt_box.bind("<KeyRelease>", _on_key)
            txt_box.bind("<FocusOut>", _on_key)

        self.bubble_canvas.yview_moveto(0.0)
        self.bubble_canvas.update_idletasks()
        self.bubble_canvas.configure(scrollregion=self.bubble_canvas.bbox("all"))

    def _on_bubble_text_edited(self, orig_idx, widget):
        if not self.caption_current_result or "segments" not in self.caption_current_result:
            return
        segments = self.caption_current_result["segments"]
        if 0 <= orig_idx < len(segments):
            new_text = widget.get("1.0", "end-1c").strip()
            segments[orig_idx]["text"] = new_text
            self.caption_current_result["text"] = "\n".join(s.get("text", "") for s in segments)
            self.caption_current_result["srt"] = convert.generate_srt_content(segments)
            if "vtt" in self.caption_current_result:
                self.caption_current_result["vtt"] = convert.generate_vtt_content(segments)

    def _delete_bubble_segment(self, orig_idx):
        if not self.caption_current_result or "segments" not in self.caption_current_result:
            return
        segments = self.caption_current_result["segments"]
        if 0 <= orig_idx < len(segments):
            is_ar = self.language_var.get() == "العربية"
            msg = f"هل أنت متأكد من حذف المقطع #{orig_idx + 1}؟" if is_ar else f"Delete segment #{orig_idx + 1}?"
            if messagebox.askyesno(self.text("app_title"), msg, parent=self):
                segments.pop(orig_idx)
                self.caption_current_result["text"] = "\n".join(s.get("text", "") for s in segments)
                self.caption_current_result["srt"] = convert.generate_srt_content(segments)
                self._refresh_bubbles_ui()

    def _insert_bubble_segment_after(self, orig_idx):
        if not self.caption_current_result or "segments" not in self.caption_current_result:
            return
        segments = self.caption_current_result["segments"]
        if 0 <= orig_idx < len(segments):
            prev_seg = segments[orig_idx]
            new_start = prev_seg.get("end", 0) + 0.1
            new_end = new_start + 2.5
            new_seg = {"start": round(new_start, 3), "end": round(new_end, 3), "text": "نص جديد..." if self.language_var.get() == "العربية" else "New text..."}
            segments.insert(orig_idx + 1, new_seg)
            self.caption_current_result["text"] = "\n".join(s.get("text", "") for s in segments)
            self.caption_current_result["srt"] = convert.generate_srt_content(segments)
            self._refresh_bubbles_ui()

    def _add_new_bubble_segment(self):
        if not self.caption_current_result:
            self.caption_current_result = {"segments": [], "text": "", "srt": ""}
        if "segments" not in self.caption_current_result:
            self.caption_current_result["segments"] = []

        segments = self.caption_current_result["segments"]
        last_end = segments[-1].get("end", 0) if segments else 0.0
        new_start = last_end + 0.2
        new_end = new_start + 3.0
        is_ar = self.language_var.get() == "العربية"
        new_seg = {"start": round(new_start, 3), "end": round(new_end, 3), "text": "نص مقطع إضافي" if is_ar else "Additional subtitle segment"}
        segments.append(new_seg)
        self.caption_current_result["text"] = "\n".join(s.get("text", "") for s in segments)
        self.caption_current_result["srt"] = convert.generate_srt_content(segments)
        self._bubble_page_last()

    def _play_bubble_segment(self, start_sec, end_sec):
        if self.input_path and self.input_path.is_file():
            self._start_media_from(max(0, start_sec - 0.2))
            dur_ms = max(500, int((end_sec - start_sec + 0.5) * 1000))
            self.after(dur_ms, lambda: self.stop_playback(reset_position=False) if self._is_playing() else None)

    def translate_embedded_caption_text(self):
        trans_val = self.caption_translate_var.get()
        trans_code = None
        if "عرب" in trans_val or "arabic" in trans_val.lower():
            trans_code = "ar"
        elif "إنجل" in trans_val or "english" in trans_val.lower():
            trans_code = "en"
        elif "فرنس" in trans_val or "french" in trans_val.lower():
            trans_code = "fr"
        elif "إسبان" in trans_val or "spanish" in trans_val.lower():
            trans_code = "es"
        elif "ألمان" in trans_val or "german" in trans_val.lower():
            trans_code = "de"
        elif "ترك" in trans_val or "turkish" in trans_val.lower():
            trans_code = "tr"
        elif "روس" in trans_val or "russian" in trans_val.lower():
            trans_code = "ru"
        elif "صين" in trans_val or "chinese" in trans_val.lower():
            trans_code = "zh-CN"
        elif "يابان" in trans_val or "japanese" in trans_val.lower():
            trans_code = "ja"
        elif "كور" in trans_val or "korean" in trans_val.lower():
            trans_code = "ko"

        if not trans_code:
            messagebox.showinfo(self.text("app_title"), self.text("caption_translate_label"))
            return
        if not self.caption_current_result and not self.caption_segments_accumulated:
            return

        def worker():
            try:
                self.after(0, lambda: self.caption_status_var.set(self.text("caption_translating", target=trans_code)))
                orig_segments = self.caption_current_result["segments"] if self.caption_current_result else self.caption_segments_accumulated
                translated = convert.translate_segments(orig_segments, target_lang=trans_code)
                if self.caption_current_result:
                    self.caption_current_result["segments"] = translated
                    self.caption_current_result["text"] = "\n".join(s["text"] for s in translated)
                    self.caption_current_result["srt"] = convert.generate_srt_content(translated)
                self.caption_segments_accumulated = translated
                self.after(0, self._caption_view_mode_changed)
                self.after(0, lambda: self.caption_status_var.set(self.text("caption_translate_done", target=trans_code)))
            except Exception as exc:
                self.after(0, lambda: self.caption_status_var.set(f"Translation error: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def start_embedded_caption(self):
        if not convert.whisper_available():
            messagebox.showerror(
                self.text("app_title"),
                "faster-whisper is not installed.\nPlease run: pip install faster-whisper",
            )
            return
        if not self.media_files:
            messagebox.showwarning(self.text("app_title"), self.text("choose_single_trim"))
            return

        target_file = self.media_files[0]
        chosen_m = self.caption_model_var.get().lower()
        if "tiny" in chosen_m:
            model_name = "tiny"
        elif "small" in chosen_m:
            model_name = "small"
        elif "medium" in chosen_m:
            model_name = "medium"
        elif "base" in chosen_m:
            model_name = "base"
        else:
            model_name = "turbo"

        lang_val = self.caption_lang_var.get()
        lang_code = None
        for code, name in convert.WHISPER_LANGUAGES.items():
            if name.lower() in lang_val.lower():
                lang_code = code
                break
        if "عرب" in lang_val or "arabic" in lang_val.lower():
            lang_code = "ar"
        elif "إنجل" in lang_val or "english" in lang_val.lower():
            lang_code = "en"

        trans_val = self.caption_translate_var.get()
        trans_code = None
        if "عرب" in trans_val or "arabic" in trans_val.lower():
            trans_code = "ar"
        elif "إنجل" in trans_val or "english" in trans_val.lower():
            trans_code = "en"
        elif "فرنس" in trans_val or "french" in trans_val.lower():
            trans_code = "fr"
        elif "إسبان" in trans_val or "spanish" in trans_val.lower():
            trans_code = "es"
        elif "ألمان" in trans_val or "german" in trans_val.lower():
            trans_code = "de"
        elif "ترك" in trans_val or "turkish" in trans_val.lower():
            trans_code = "tr"
        elif "روس" in trans_val or "russian" in trans_val.lower():
            trans_code = "ru"
        elif "صين" in trans_val or "chinese" in trans_val.lower():
            trans_code = "zh-CN"
        elif "يابان" in trans_val or "japanese" in trans_val.lower():
            trans_code = "ja"
        elif "كور" in trans_val or "korean" in trans_val.lower():
            trans_code = "ko"

        self.caption_cancel_event.clear()
        self.caption_current_result = None
        self.caption_segments_accumulated = []

        self.caption_start_button.configure(state="disabled")
        self.caption_stop_button.configure(state="normal")
        self.caption_text_view.configure(state="normal")
        self.caption_text_view.delete("1.0", "end")
        self.caption_text_view.configure(state="disabled")
        self.caption_status_var.set(self.text("caption_loading"))
        self.caption_progress_bar.configure(mode="indeterminate")
        self.caption_progress_bar.start(10)

        def worker():
            try:
                def prog_cb(pct, text, s, e, dur):
                    self.after(0, lambda: self._on_embedded_caption_segment(pct, text, s, e, dur))

                res = convert.transcribe_media(
                    target_file,
                    model_size=model_name,
                    language=lang_code,
                    translate_to=trans_code,
                    progress_callback=prog_cb,
                    cancel_callback=self.caption_cancel_event.is_set,
                )
                if self.caption_cancel_event.is_set():
                    self.after(0, self._on_embedded_caption_cancel)
                    return

                self.after(0, lambda: self._on_embedded_caption_done(res))
            except convert.CancelledError:
                self.after(0, self._on_embedded_caption_cancel)
            except Exception as exc:
                if self.caption_cancel_event.is_set() or "cancel" in str(exc).lower():
                    self.after(0, self._on_embedded_caption_cancel)
                    return
                self.after(0, lambda: self._on_embedded_caption_error(exc))

        self.caption_transcribe_start_time = time.monotonic()
        self.caption_thread = threading.Thread(target=worker, daemon=True)
        self.caption_thread.start()

    def _on_embedded_caption_segment(self, pct, text, start, end, dur):
        if self.caption_progress_bar["mode"] == "indeterminate":
            self.caption_progress_bar.stop()
            self.caption_progress_bar.configure(mode="determinate", maximum=100)
        self.caption_progress_bar.configure(value=pct)

        if text.startswith("Downloading AI model") or text.startswith("جاري تحميل") or "Loading Whisper" in text:
            self.caption_status_var.set(text)
            return

        is_ar = self.language_var.get() == "العربية"
        elapsed_str = ""
        eta_str = ""
        if hasattr(self, "caption_transcribe_start_time") and self.caption_transcribe_start_time:
            wall_elapsed = time.monotonic() - self.caption_transcribe_start_time
            elapsed_str = self._format_seconds(wall_elapsed)
            if pct > 0:
                eta_sec = (wall_elapsed / pct) * (100 - pct)
                eta_str = self._format_seconds(eta_sec)
            else:
                eta_str = self.text("estimating")

        pos_str = ""
        if dur and dur > 0:
            pos_str = f" ({self._format_seconds(end)} / {self._format_seconds(dur)})"

        if is_ar:
            status = f"جاري التفريغ: {pct}%{pos_str}"
            if elapsed_str:
                status += f" | المنقضي: {elapsed_str} | المتبقي: ~{eta_str}"
        else:
            status = f"Transcribing: {pct}%{pos_str}"
            if elapsed_str:
                status += f" | Elapsed: {elapsed_str} | Remaining: ~{eta_str}"

        self.caption_status_var.set(status)

        self.caption_segments_accumulated.append({"start": start, "end": end, "text": text})
        self.caption_text_view.configure(state="normal")
        if self.caption_view_mode_var.get() == "text":
            self.caption_text_view.insert("end", text + " ")
        else:
            idx = len(self.caption_segments_accumulated)
            s_str = convert.format_timestamp_srt(start)
            e_str = convert.format_timestamp_srt(end)
            self.caption_text_view.insert("end", f"{idx}\n{s_str} --> {e_str}\n{text}\n\n")
        self.caption_text_view.see("end")
        self.caption_text_view.configure(state="disabled")

    def _on_embedded_caption_done(self, res):
        self.caption_progress_bar.stop()
        self.caption_progress_bar.configure(mode="determinate", value=100)
        self.caption_status_var.set(self.text("caption_done"))
        self.caption_start_button.configure(state="normal")
        self.caption_stop_button.configure(state="disabled")
        self.caption_model_combo.configure(state="readonly")
        self.caption_current_result = res
        if "srt" not in res and "segments" in res:
            res["srt"] = convert.generate_srt_content(res["segments"])
        if "vtt" not in res and "segments" in res:
            res["vtt"] = convert.generate_vtt_content(res["segments"])
        self._caption_view_mode_changed()
        self._update_caption_model_status()

        target_file = self.media_files[0] if self.media_files else (Path(self.input_path) if self.input_path else None)
        base_name = target_file.stem if target_file else "captions"
        out_dir = self.output_dir or convert.OUTPUT_DIR
        out_dir.mkdir(parents=True, exist_ok=True)

    def import_from_capcut(self):
        drafts = convert.get_capcut_drafts()
        if not drafts:
            messagebox.showinfo(
                self.text("app_title"),
                self.text("caption_no_capcut_drafts"),
            )
            return

        chosen_draft = drafts[0]
        if len(drafts) > 1:
            dlg = tk.Toplevel(self)
            dlg.title(self.text("caption_capcut_dialog_title"))
            dlg.geometry("520x340")
            dlg.transient(self)
            dlg.grab_set()
            dlg.resizable(False, False)

            is_ar = self.language_var.get() == "العربية"
            lbl = ttk.Label(
                dlg,
                text=self.text("caption_capcut_select"),
                font=("Segoe UI", 10, "bold"),
            )
            lbl.pack(anchor="e" if is_ar else "w", padx=16, pady=(16, 8))

            listbox_frame = ttk.Frame(dlg)
            listbox_frame.pack(fill="both", expand=True, padx=16, pady=4)
            scrollbar = ttk.Scrollbar(listbox_frame)
            scrollbar.pack(side="right" if not is_ar else "left", fill="y")
            lb = tk.Listbox(
                listbox_frame,
                yscrollcommand=scrollbar.set,
                font=("Segoe UI", 10),
                selectmode="browse",
                exportselection=False,
                justify="right" if is_ar else "left",
            )
            lb.pack(side="left" if not is_ar else "right", fill="both", expand=True)
            scrollbar.config(command=lb.yview)

            for d in drafts:
                sub_txt = f"{d['subtitle_count']} مقطع" if is_ar else f"{d['subtitle_count']} segments"
                lb.insert("end", f"📅 {d['date']} | 📝 {sub_txt} | {d['name']}")
            lb.selection_set(0)

            selected_idx = [0]
            cancelled = [False]

            def on_ok():
                sel = lb.curselection()
                if sel:
                    selected_idx[0] = sel[0]
                dlg.destroy()

            def on_cancel():
                cancelled[0] = True
                dlg.destroy()

            lb.bind("<Double-Button-1>", lambda _e: on_ok())
            dlg.bind("<Return>", lambda _e: on_ok())
            dlg.bind("<Escape>", lambda _e: on_cancel())
            dlg.protocol("WM_DELETE_WINDOW", on_cancel)

            btn_box = ttk.Frame(dlg)
            btn_box.pack(fill="x", padx=16, pady=12)
            import_txt = "استيراد الترجمة" if is_ar else "Import Subtitles"
            ttk.Button(btn_box, text=import_txt, command=on_ok, style="Action.TButton").pack(side="left" if not is_ar else "right", padx=4)
            ttk.Button(btn_box, text=self.text("close"), command=on_cancel).pack(side="right" if not is_ar else "left", padx=4)
            dlg.wait_window()

            if cancelled[0]:
                return
            chosen_draft = drafts[selected_idx[0]]

        out_dir = self.output_dir or (Path(self.media_files[0]).parent if self.media_files else Path.home())
        res = convert.extract_subtitles_from_capcut(chosen_draft["path"], output_dir=out_dir)
        if not res["segments"]:
            messagebox.showwarning(self.text("app_title"), self.text("caption_no_capcut_drafts"))
            return

        if res.get("video_path") and Path(res["video_path"]).exists():
            if not self.input_path or not self.input_path.is_file():
                self.set_source(Path(res["video_path"]))

        self._on_embedded_caption_done(res)
        self.caption_text_view.see("1.0")
        messagebox.showinfo(
            self.text("app_title"),
            self.text("caption_capcut_imported", count=len(res["segments"]), project=chosen_draft["name"]),
        )

    def _on_embedded_caption_cancel(self):
        self.caption_progress_bar.stop()
        self.caption_progress_bar.configure(mode="determinate", value=0)
        self.caption_status_var.set(self.text("canceled"))
        self.caption_start_button.configure(state="normal")
        self.caption_stop_button.configure(state="disabled")
        self.caption_burn_button.configure(state="normal")
        if hasattr(self, "caption_burn_cancel_button"):
            self.caption_burn_cancel_button.configure(state="disabled")
        self.caption_import_capcut_button.configure(state="normal")
        self.caption_model_combo.configure(state="readonly")
        self._update_caption_model_status()
        self._append_log(f"\n[Auto Caption] {self.text('canceled')}\n")

    def _on_embedded_caption_error(self, exc):
        self.caption_progress_bar.stop()
        self.caption_progress_bar.configure(mode="determinate", value=0)
        self.caption_status_var.set(self.text("caption_error", error=str(exc)))
        self.caption_start_button.configure(state="normal")
        self.caption_stop_button.configure(state="disabled")
        self.caption_burn_button.configure(state="normal")
        if hasattr(self, "caption_burn_cancel_button"):
            self.caption_burn_cancel_button.configure(state="disabled")
        self.caption_import_capcut_button.configure(state="normal")
        self.caption_model_combo.configure(state="readonly")
        self._update_caption_model_status()
        self._append_log(f"\n[Auto Caption] Error: {exc}\n")
        messagebox.showerror(self.text("app_title"), self.text("caption_error", error=str(exc)))

    def cancel_embedded_caption(self):
        self.caption_cancel_event.set()
        convert.abort_whisper_download()
        self.caption_status_var.set(self.text("canceling"))
        self.caption_stop_button.configure(state="disabled")
        if hasattr(self, "caption_burn_cancel_button"):
            self.caption_burn_cancel_button.configure(state="disabled")

    def copy_embedded_caption(self):
        txt = self.caption_text_view.get("1.0", "end-1c")
        if txt.strip():
            self.clipboard_clear()
            self.clipboard_append(txt)
            messagebox.showinfo(self.text("app_title"), self.text("caption_saved"))

    def save_embedded_caption_as(self):
        txt = self.caption_text_view.get("1.0", "end-1c")
        if not txt.strip():
            return
        is_srt = self.caption_view_mode_var.get() == "srt"
        def_ext = ".srt" if is_srt else ".txt"
        types = (
            [("Subtitles (.srt)", "*.srt"), ("All files", "*.*")]
            if is_srt
            else [("Text file (.txt)", "*.txt"), ("All files", "*.*")]
        )
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=def_ext,
            filetypes=types,
            initialdir=self._dialog_dir(self.output_dir),
        )
        if path:
            Path(path).write_text(txt, encoding="utf-8")
            messagebox.showinfo(self.text("app_title"), self.text("caption_saved"))

    def burn_embedded_caption(self):
        if not self.caption_current_result or not (self.caption_current_result.get("srt") or self.caption_current_result.get("segments")):
            messagebox.showwarning(self.text("app_title"), "No subtitles available to burn.")
            return

        active_candidate = self.input_path or (self.media_files[0] if self.media_files else None)
        capcut_hint = self.caption_current_result.get("video_path")

        target_video = None
        if active_candidate and Path(active_candidate).is_file():
            active_p = Path(active_candidate).resolve()
            if convert.has_video_stream(active_p):
                target_video = active_p
            else:
                matching = convert.find_matching_video(active_p, hint_path=capcut_hint)
                if matching:
                    if "_trim_" in active_p.stem:
                        a_dur = convert.get_media_duration(active_p) or 0
                        v_dur = convert.get_media_duration(matching) or 0
                        if abs(a_dur - v_dur) > 10:
                            target_video = active_p
                            self._append_log(f"\n[Auto Caption] Using trimmed audio clip: {active_p.name}\n")
                        else:
                            target_video = matching
                            self._append_log(f"\n[Auto Caption] Matched source video: {matching.name}\n")
                    else:
                        target_video = matching
                        self._append_log(f"\n[Auto Caption] Matched source video: {matching.name}\n")
                else:
                    target_video = active_p
                    self._append_log(f"\n[Auto Caption] Creating video from audio: {active_p.name}\n")
        elif capcut_hint and Path(capcut_hint).is_file():
            target_video = Path(capcut_hint).resolve()

        if not target_video:
            init_dir = (
                (self.input_path.parent if self.input_path and self.input_path.is_file() else None)
                or self.last_media_dir
                or self.output_dir
            )
            filetypes = [
                (self.text("media_files"), " ".join(f"*{ext}" for ext in sorted(convert.MEDIA_EXTS))),
                (self.text("video_files"), " ".join(f"*{ext}" for ext in sorted(convert.VIDEO_EXTS))),
                (self.text("audio_files"), " ".join(f"*{ext}" for ext in sorted(convert.AUDIO_EXTS))),
                (self.text("all_files"), "*.*"),
            ]
            chosen = filedialog.askopenfilename(
                title=self.text("caption_select_video_to_burn"),
                initialdir=self._dialog_dir(init_dir),
                filetypes=filetypes,
            )
            if not chosen:
                return
            target_video = Path(chosen).resolve()
            self.set_source(target_video)
            self.media_files = [target_video]

        out_dir = self.output_dir or convert.OUTPUT_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        srt_file = out_dir / f"{target_video.stem}_subtitles.srt"
        srt_content = self.caption_current_result.get("srt") or convert.generate_srt_content(self.caption_current_result["segments"])
        srt_file.write_text(srt_content, encoding="utf-8-sig")

        self.caption_cancel_event.clear()
        self.caption_start_button.configure(state="disabled")
        self.caption_stop_button.configure(state="normal")
        self.caption_burn_button.configure(state="disabled")
        if hasattr(self, "caption_burn_cancel_button"):
            self.caption_burn_cancel_button.configure(state="normal")
        self.caption_import_capcut_button.configure(state="disabled")
        self.caption_progress_bar.stop()
        self.caption_progress_bar.configure(mode="determinate", maximum=100, value=0)
        burn_start_time = time.monotonic()
        self.caption_status_var.set(f"{self.text('caption_burning')} (0%)")
        self._append_log(f"\n[Auto Caption] Burning subtitles to video: {target_video.name}\n")

        def worker():
            try:
                def prog_cb(pct, msg, cur, dur, tot):
                    self.after(0, lambda: self._on_embedded_burn_progress(pct, cur, tot, burn_start_time))

                out_vid = convert.burn_subtitles_to_video(
                    target_video,
                    srt_file,
                    output_dir=out_dir,
                    style_config=self.subtitle_style,
                    cancel_callback=self.caption_cancel_event.is_set,
                    progress_callback=prog_cb,
                )
                if self.caption_cancel_event.is_set():
                    self.after(0, self._on_embedded_caption_cancel)
                    return
                self.after(0, lambda: self._on_embedded_burn_done(out_vid))
            except convert.CancelledError:
                self.after(0, self._on_embedded_caption_cancel)
            except Exception as exc:
                if self.caption_cancel_event.is_set() or "cancel" in str(exc).lower():
                    self.after(0, self._on_embedded_caption_cancel)
                    return
                self.after(0, lambda: self._on_embedded_caption_error(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_embedded_burn_progress(self, percent, cur=0, tot=0, start_time=None):
        self.caption_progress_bar.configure(value=percent)
        is_ar = self.language_var.get() == "العربية"
        elapsed_str = ""
        eta_str = ""
        if start_time:
            wall_elapsed = time.monotonic() - start_time
            elapsed_str = self._format_seconds(wall_elapsed)
            if percent > 0:
                eta_sec = (wall_elapsed / percent) * (100 - percent)
                eta_str = self._format_seconds(eta_sec)
            else:
                eta_str = self.text("estimating")

        pos_str = ""
        if tot and tot > 0:
            pos_str = f" ({self._format_seconds(cur)} / {self._format_seconds(tot)})"

        if is_ar:
            status = f"جاري دمج الترجمة: {percent}%{pos_str}"
            if elapsed_str:
                status += f" | المنقضي: {elapsed_str} | المتبقي: ~{eta_str}"
        else:
            status = f"Burning subtitles: {percent}%{pos_str}"
            if elapsed_str:
                status += f" | Elapsed: {elapsed_str} | Remaining: ~{eta_str}"

        self.caption_status_var.set(status)

    def _on_embedded_burn_done(self, out_vid):
        self.caption_progress_bar.configure(value=100)
        self.caption_start_button.configure(state="normal")
        self.caption_stop_button.configure(state="disabled")
        self.caption_burn_button.configure(state="normal")
        if hasattr(self, "caption_burn_cancel_button"):
            self.caption_burn_cancel_button.configure(state="disabled")
        self.caption_import_capcut_button.configure(state="normal")
        self.caption_model_combo.configure(state="readonly")
        self._update_caption_model_status()
        msg = self.text("caption_burned_success", filename=out_vid.name)
        self.caption_status_var.set(msg)
        self._append_log(f"\n[Auto Caption] Captioned video created: {out_vid.name}\n")
        messagebox.showinfo(self.text("app_title"), msg)

    # ------------------ Language & Localized Labels ------------------
    def _apply_language(self):
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
        self.i18n_widgets["caption_settings_group"].configure(text=self.text("caption_settings_group"))
        self.i18n_widgets["caption_output_group"].configure(text=self.text("caption_output_group"))
        self.i18n_widgets["cover_group"].configure(text=self.text("cover_group"))
        self.i18n_widgets["youtube_group"].configure(text=self.text("youtube_group"))
        self.i18n_widgets["log_group"].configure(text=self.text("log_group"))

        # Update Notebook tab titles
        self.notebook.tab(0, text=self.text("tab_convert"))
        self.notebook.tab(1, text=self.text("tab_volume"))
        self.notebook.tab(2, text=self.text("tab_player"))
        self.notebook.tab(3, text=self.text("tab_caption"))
        self.notebook.tab(4, text=self.text("tab_cover"))
        self.notebook.tab(5, text=self.text("tab_youtube"))

        # Labels
        self.i18n_widgets["output_label"].configure(text=self.text("output"))
        self.i18n_widgets["format_label"].configure(text=self.text("format"))
        self.i18n_widgets["quality_label"].configure(text=self.text("quality"))
        self.i18n_widgets["enhance_label"].configure(text=self.text("enhance"))
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
        self.back_button.configure(text="-10s")
        self.forward_button.configure(text="+10s")
        self.next_button.configure(text="▶|")
        self.expand_video_button.configure(text="⛶" if not self.video_expanded else "▣")
        self._refresh_play_button()
        self.mark_start_button.configure(text=self.text("mark_start"))
        self.mark_end_button.configure(text=self.text("mark_end"))
        self.trim_button.configure(text=self.text("trim_selected"))
        if hasattr(self, "trim_extract_audio_check"):
            self.trim_extract_audio_check.configure(text=self.text("trim_extract_audio"))
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

        if "about_button" in self.i18n_widgets:
            self.i18n_widgets["about_button"].configure(text=self.text("about"))
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
        self._refresh_boost_format_options()
        self._refresh_caption_options()
        self._boost_gain_changed()

    def show_about_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title(self.text("about_title"))
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Media Audio Studio", font=("Segoe UI", 15, "bold")).pack(pady=(0, 2))
        ttk.Label(frame, text="Version 1.0.0", font=("Segoe UI", 9), foreground="#666666").pack(pady=(0, 8))
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

    def _refresh_enhancement_options(self):
        labels = ENHANCEMENT_LABELS[self.language_var.get()]
        self.enhancement_combo.configure(values=[labels[key] for key in convert.ENHANCEMENT_PRESETS])
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
        if compression == "Original" and resolution == "Original":
            total_size = sum(path.stat().st_size for path in video_files if path.is_file())
            return total_size if total_size > 0 else None

        if not hasattr(self, "_video_info_cache"):
            self._video_info_cache = {}

        total_est = 0
        for path in video_files:
            if not path.is_file():
                continue
            try:
                cache_key = (str(path), path.stat().st_mtime)
            except OSError:
                continue
            info = self._video_info_cache.get(cache_key)
            if not info:
                try:
                    dur = convert.get_media_duration(path) or 0
                    w, h = convert.get_video_dimensions(path)
                    sz = path.stat().st_size
                    info = {"duration": dur, "w": w, "h": h, "size": sz}
                    self._video_info_cache[cache_key] = info
                except Exception:
                    continue

            dur = info["duration"]
            if dur <= 0:
                continue
            w = info["w"]
            h = info["h"]
            source_size = info["size"]

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
            ratio = {
                "Original": 1.0,
                "Very High": 0.88,
                "High": 0.68,
                "Medium": 0.48,
                "Small": 0.28,
                "Very Small": 0.16,
            }.get(compression, 0.5)

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
        estimate = self._estimate_video_output_size(video_files)
        is_ar = self.language_var.get() == "العربية"
        if estimate:
            prefix = "الحجم التقريبي: ~" if is_ar else "Est. ~"
            self.video_estimate_var.set(f"{prefix}{convert.human_size(estimate)}")
        else:
            self.video_estimate_var.set("الحجم التقريبي غير معروف" if is_ar else "Est. unknown")

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
        self.fullscreen_window = tk.Toplevel(self)
        self.fullscreen_window.attributes("-fullscreen", True)
        self.fullscreen_window.configure(bg="black")
        self.fullscreen_surface = tk.Frame(self.fullscreen_window, bg="black")
        self.fullscreen_surface.pack(fill="both", expand=True)
        self.fullscreen_window.bind("<Escape>", lambda _e: self._exit_video_fullscreen())
        self.fullscreen_window.bind("<F11>", lambda _e: self._exit_video_fullscreen())
        self.fullscreen_surface.bind("<Double-Button-1>", lambda _e: self._exit_video_fullscreen())
        self.expand_video_button.configure(text="▣")
        self.fullscreen_window.update_idletasks()
        if self.media_player:
            if sys.platform.startswith("win"):
                self.media_player.set_hwnd(self.fullscreen_surface.winfo_id())
            elif sys.platform == "darwin":
                self.media_player.set_nsobject(self.fullscreen_surface.winfo_id())
            else:
                self.media_player.set_xwindow(self.fullscreen_surface.winfo_id())

    def _exit_video_fullscreen(self):
        if not self.video_expanded:
            return
        self.video_expanded = False
        if self.fullscreen_window:
            try:
                self.fullscreen_window.destroy()
            except Exception:
                pass
            self.fullscreen_window = None
            self.fullscreen_surface = None
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

        quality = self.quality_var.get()
        enhancement = self.selected_enhancement()
        self._clear_log()
        self._begin_operation("trim", self.trim_button)
        self._append_log(self.text("trimming") + "\n")
        self.status_var.set(self.text("trimming"))
        self._set_busy(True)
        self.progress.configure(mode="determinate", maximum=100, value=0)
        self.progress_var.set(self.text("progress_detail", current=0, total=1, file_percent=0, overall_percent=0, remaining_percent=100, elapsed="0s", eta=self.text("estimating")))

        self.worker = threading.Thread(
            target=self._run_trim,
            args=(start_time, end_time, output_ext, quality, keep_original_format, enhancement),
            daemon=True,
        )
        self.worker.start()

    def open_caption_studio(self):
        CaptionStudioDialog(
            self,
            initial_source=self.input_path,
            initial_output_dir=self.output_dir,
            media_files=self.media_files,
        )


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
        self.progress_var.set(self.text("progress_detail", current=0, total=1, file_percent=0, overall_percent=0, remaining_percent=100, elapsed="0s", eta=self.text("estimating")))

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
                    elapsed = self._format_seconds(time.monotonic() - self.run_started_at) if self.run_started_at else "0s"
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
                                elapsed=elapsed,
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
        self.boost_button.configure(state="normal" if self.media_files else "disabled")
        self.detect_volume_button.configure(state="normal" if self.media_files else "disabled")
        self.auto_peak_button.configure(state="normal" if self.media_files else "disabled")
        self.caption_start_button.configure(state="normal" if self.media_files else "disabled")
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
