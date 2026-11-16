"""
Video Studio Package
Video transformations, DaVinci-style aspect ratios & pan/zoom, multi-track NLE timeline engine,
pro icon library, branding overlays, and subtitle compositing.
Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

from .aspect_ratios import (
    ASPECT_RATIOS,
    FIT_MODES,
    build_aspect_ratio_filter,
    get_aspect_ratio_dimensions,
    compute_video_transform_geometry,
    clamp_pan_for_transform,
    render_transformed_pil_frame,
)
from .subtitle_style import (
    SUBTITLE_COLORS,
    SUBTITLE_OUTLINES,
    SUBTITLE_ALIGNMENTS,
    build_subtitle_style_string,
)
from .branding import (
    LOGO_POSITIONS,
    BANNER_POSITIONS,
    BANNER_BG_COLORS,
    BANNER_TEXT_COLORS,
    AVAILABLE_FONTS,
    generate_title_banner_image,
    render_text_card_pil,
    generate_text_overlay_image,
    build_logo_overlay_filter,
    build_title_banner_filter,
    build_timed_rgba_overlay_filter,
)
from .icons_library import (
    ICON_PRESETS,
    render_icon_pil,
    apply_opacity_and_rotation,
    render_media_overlay_pil,
)
from .timeline_engine import (
    NLEProjectState,
    FastVideoPreviewProvider,
    extract_audio_waveform_peaks,
    parse_srt_segments,
)
from .filter_compositor import (
    build_composite_video_filter,
    export_styled_video,
)
from .color_grading import (
    DEFAULT_COLOR_CONFIG,
    COLOR_PRESETS,
    AUTO_COLOR_MODES,
    auto_analyze_and_correct,
    apply_color_to_image,
    generate_cube_lut,
    build_ffmpeg_color_filter,
    extract_video_sample_frame,
    is_color_neutral,
)
from .arabic_support import (
    has_arabic,
    reshape_arabic,
    bidi_reorder,
    prepare_arabic_for_rendering,
)
from .silence_remover import (
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
from .transitions import (
    DEFAULT_TRANSITIONS_CONFIG,
    TRANSITION_PRESETS,
    TRANSITION_CATEGORIES,
    get_transition_info,
    list_transitions_by_category,
    render_simulated_transition_frame,
    build_xfade_filter_chains,
)
from .session_manager import (
    AUTOSAVE_FILE,
    save_session_state,
    load_session_state,
    has_recoverable_session,
    mark_clean_exit,
    clear_autosave,
)

__all__ = [
    "ASPECT_RATIOS",
    "FIT_MODES",
    "build_aspect_ratio_filter",
    "get_aspect_ratio_dimensions",
    "compute_video_transform_geometry",
    "clamp_pan_for_transform",
    "render_transformed_pil_frame",
    "SUBTITLE_COLORS",
    "SUBTITLE_OUTLINES",
    "SUBTITLE_ALIGNMENTS",
    "build_subtitle_style_string",
    "LOGO_POSITIONS",
    "BANNER_POSITIONS",
    "BANNER_BG_COLORS",
    "BANNER_TEXT_COLORS",
    "AVAILABLE_FONTS",
    "generate_title_banner_image",
    "render_text_card_pil",
    "generate_text_overlay_image",
    "build_logo_overlay_filter",
    "build_title_banner_filter",
    "build_timed_rgba_overlay_filter",
    "ICON_PRESETS",
    "render_icon_pil",
    "apply_opacity_and_rotation",
    "render_media_overlay_pil",
    "NLEProjectState",
    "FastVideoPreviewProvider",
    "extract_audio_waveform_peaks",
    "build_composite_video_filter",
    "export_styled_video",
    "DEFAULT_COLOR_CONFIG",
    "COLOR_PRESETS",
    "auto_analyze_and_correct",
    "apply_color_to_image",
    "generate_cube_lut",
    "build_ffmpeg_color_filter",
    "extract_video_sample_frame",
    "is_color_neutral",
    "has_arabic",
    "reshape_arabic",
    "bidi_reorder",
    "prepare_arabic_for_rendering",
    "SILENCE_PRESETS",
    "SILENCE_MODES",
    "detect_silences",
    "compute_speech_segments",
    "summarize_silence_analysis",
    "remap_subtitles_for_cuts",
    "parse_and_remap_srt_file",
    "build_silence_filter_expressions",
    "export_silence_cut_media",
    "DEFAULT_TRANSITIONS_CONFIG",
    "TRANSITION_PRESETS",
    "TRANSITION_CATEGORIES",
    "get_transition_info",
    "list_transitions_by_category",
    "render_simulated_transition_frame",
    "build_xfade_filter_chains",
    "AUTOSAVE_FILE",
    "save_session_state",
    "load_session_state",
    "has_recoverable_session",
    "mark_clean_exit",
    "clear_autosave",
    "check_for_updates",
    "UpdateDialog",
]

from .update_manager import check_for_updates, UpdateDialog
