"""
UI Dialogs & Studio Widgets Package
Contains dialogs for subtitle styling, video branding & aspect ratio, caption studio,
color grading, pro icon picker, and the DaVinci-style multi-track NLE timeline panel.
Developer: ahmed elshazly | Elshazly.gsm@gmail.com
"""

from .subtitle_style_dialog import SubtitleStyleDialog
from .video_branding_dialog import VideoBrandingDialog
from .caption_studio_dialog import CaptionStudioDialog
from .video_color_dialog import VideoColorDialog
from .video_transition_dialog import VideoTransitionDialog
from .icon_picker_dialog import IconPickerDialog
from .nle_timeline_widget import DaVinciTimelinePanel
from .video_theater_dialog import VideoTheaterDialog
from .color_theater_dialog import ColorTheaterDialog
from .shortcuts_guide_dialog import ShortcutsGuideDialog

__all__ = [
    "SubtitleStyleDialog",
    "VideoBrandingDialog",
    "CaptionStudioDialog",
    "VideoColorDialog",
    "VideoTransitionDialog",
    "IconPickerDialog",
    "DaVinciTimelinePanel",
    "VideoTheaterDialog",
    "ColorTheaterDialog",
    "ShortcutsGuideDialog",
]
