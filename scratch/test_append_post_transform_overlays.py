import sys
from pathlib import Path
import tempfile
from PIL import Image

sys.path.insert(0, ".")
from video_studio.filter_compositor import _append_post_transform_overlays

def test_append_overlays():
    print("=== Testing _append_post_transform_overlays with animations ===")
    tmp_dir = Path(tempfile.gettempdir()) / "test_comp_overlays"
    tmp_dir.mkdir(exist_ok=True)

    media_items = [
        {
            "enabled": True,
            "type": "icon",
            "icon_key": "youtube",
            "x": 0.5,
            "y": 0.5,
            "scale": 0.2,
            "opacity": 1.0,
            "rotation": 0.0,
            "start_sec": 1.0,
            "end_sec": 4.0,
            "full_duration": False,
            "anim_in": "bounce",
            "anim_out": "fade",
            "anim_dur": 0.5,
        }
    ]

    title_config = {
        "text_items": [
            {
                "enabled": True,
                "text": "عنوان تجريبي متحرك",
                "x_pct": 0.5,
                "y_pct": 0.8,
                "bg_color": "black",
                "text_color": "white",
                "font_size": 34,
                "start_sec": 0.5,
                "end_sec": 5.0,
                "full_duration": False,
                "anim_in": "tilt_slide_up",
                "anim_out": "slide_down",
                "anim_dur": 0.6,
            }
        ]
    }

    # Dummy logo file
    logo_file = tmp_dir / "test_logo.png"
    Image.new("RGBA", (100, 100), (255, 0, 0, 200)).save(str(logo_file))

    logo_items = [
        {
            "enabled": True,
            "path": str(logo_file),
            "x": 0.8,
            "y": 0.1,
            "scale": 0.15,
            "opacity": 0.9,
            "rotation": 0.0,
            "start_sec": 2.0,
            "end_sec": 6.0,
            "full_duration": False,
            "anim_in": "spin_in",
            "anim_out": "drop_out",
            "anim_dur": 0.5,
        }
    ]

    chains, cur_label, step_cnt, temp_files = _append_post_transform_overlays(
        cur_label="v_base",
        step=0,
        canvas_w=1080,
        canvas_h=1920,
        color_config=None,
        media_overlays=media_items,
        title_config=title_config,
        logo_config=None,
        logo_items=logo_items,
        subtitle_config=None,
        active_keep_intervals=None,
        sil_mode="cut",
        sil_speed=1,
        t_dir=tmp_dir,
        is_ar=True,
    )

    print(f"Generated {len(chains)} overlay chains:")
    for i, c in enumerate(chains):
        print(f"[{i}]: {c[:140]}...")

    assert len(chains) == 3, f"Expected 3 chains, got {len(chains)}"
    assert cur_label == f"v_cur_{step_cnt - 1}"

    # Verify each chain contains its animation
    assert "sin" in chains[0] or "bounce" in chains[0]
    assert "PI/180" in chains[1] or "tilt_slide_up" in chains[1]
    assert "2*PI" in chains[2] or "spin_in" in chains[2]

    print("ALL POST TRANSFORM OVERLAY ANIMATION TESTS PASSED 100%!")

if __name__ == "__main__":
    test_append_overlays()
