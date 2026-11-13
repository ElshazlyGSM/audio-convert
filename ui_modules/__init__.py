"""
UI Modules Package for Media & Audio Studio
Modular decomposition of UI components, playback controllers, inspector panels, and export engines.
"""

from ui_modules.master_export import MasterExportMixin
from ui_modules.studio_canvas import StudioCanvasMixin
from ui_modules.studio_inspector import StudioInspectorMixin
from ui_modules.playback_sync import PlaybackSyncMixin
from ui_modules.audio_mastering import AudioMasteringMixin
from ui_modules.silence_workflow import SilenceWorkflowMixin
from ui_modules.subtitles_manager import SubtitlesMixin

__all__ = [
    "MasterExportMixin",
    "StudioCanvasMixin",
    "StudioInspectorMixin",
    "PlaybackSyncMixin",
    "AudioMasteringMixin",
    "SilenceWorkflowMixin",
    "SubtitlesMixin",
]
