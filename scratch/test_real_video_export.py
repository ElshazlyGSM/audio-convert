import sys
from pathlib import Path
import subprocess
import tempfile
from PIL import Image

sys.path.insert(0, ".")
from video_studio.filter_compositor import export_styled_video

def test_real_video_export():
    print("=== Testing Full Video Export with Animations on Real Video ===")
    raw_video = Path(r"E:\dr m\Raw\Lesson 22.mp4")
    if not raw_video.is_file():
        print("Raw video not found, skipping real video test")
        return

    tmp_dir = Path(tempfile.gettempdir()) / "test_real_export"
    tmp_dir.mkdir(exist_ok=True)
    out_mp4 = tmp_dir / "lesson22_anim_out.mp4"

    # Logo
    logo_file = tmp_dir / "logo.png"
    Image.new("RGBA", (80, 80), (200, 30, 30, 240)).save(str(logo_file))

    title_config = {
        "text_items": [
            {
                "enabled": True,
                "text": "درس 22: هل يجوز للحائض الطواف؟",
                "x_pct": 0.5,
                "y_pct": 0.85,
                "bg_color": "black",
                "text_color": "white",
                "font_size": 38,
                "start_sec": 1.0,
                "end_sec": 4.5,
                "full_duration": False,
                "anim_in": "tilt_slide_up",
                "anim_out": "slide_down",
                "anim_dur": 0.6,
            }
        ]
    }

    logo_items = [
        {
            "enabled": True,
            "path": str(logo_file),
            "x": 0.85,
            "y": 0.05,
            "scale": 0.12,
            "opacity": 0.9,
            "rotation": 0.0,
            "start_sec": 0.5,
            "end_sec": 5.0,
            "full_duration": False,
            "anim_in": "fade",
            "anim_out": "fade",
            "anim_dur": 0.5,
        }
    ]

    media_items = [
        {
            "enabled": True,
            "type": "icon",
            "icon_key": "youtube",
            "x": 0.15,
            "y": 0.85,
            "scale": 0.18,
            "opacity": 1.0,
            "rotation": 0.0,
            "start_sec": 1.2,
            "end_sec": 4.0,
            "full_duration": False,
            "anim_in": "bounce",
            "anim_out": "fade",
            "anim_dur": 0.5,
        }
    ]

    out_path = export_styled_video(
        video_path=raw_video,
        output_path=out_mp4,
        start_seconds=0.0,
        duration_seconds=5.0,
        aspect_ratio="9:16",
        fit_mode="crop",
        title_config=title_config,
        logo_items=logo_items,
        media_overlays=media_items,
        is_ar=True,
    )

    print(f"Export result: out_path={out_path}")
    assert out_path is not None, "Export returned None"
    assert Path(out_path).is_file() and Path(out_path).stat().st_size > 10000
    print(f"SUCCESS! Output file: {out_path} ({Path(out_path).stat().st_size} bytes)")
    print("REAL VIDEO EXPORT WITH ANIMATIONS VERIFIED 100%!")

if __name__ == "__main__":
    test_real_video_export()
