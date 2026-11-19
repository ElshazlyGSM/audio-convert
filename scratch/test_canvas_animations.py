import math
from ui_modules.studio_canvas import evaluate_item_animation
from video_studio.icons_library import apply_opacity_and_rotation
from PIL import Image

def test_animations():
    print("=== Testing evaluate_item_animation ===")
    item = {
        "start_sec": 2.0,
        "end_sec": 7.0,
        "full_duration": False,
        "anim_in": "tilt_slide_up",
        "anim_out": "slide_down",
        "anim_dur": 0.6,
    }

    # 1. Test before start_sec
    res_before = evaluate_item_animation(item, 1.5, 1080, 1920)
    print(f"At t=1.5 (before): {res_before}")
    assert len(res_before) == 5

    # 2. Test during entrance (t = 2.0, 2.3, 2.6)
    res_in_start = evaluate_item_animation(item, 2.0, 1080, 1920)
    print(f"At t=2.0 (entrance start): {res_in_start}")
    assert res_in_start[0] == 0.0 # opacity should be 0
    assert res_in_start[4] == -12.0 # rot should be -12 deg

    res_in_mid = evaluate_item_animation(item, 2.3, 1080, 1920)
    print(f"At t=2.3 (entrance mid): {res_in_mid}")
    assert 0.0 < res_in_mid[0] < 1.0
    assert -12.0 < res_in_mid[4] < 0.0

    res_in_end = evaluate_item_animation(item, 2.6, 1080, 1920)
    print(f"At t=2.6 (entrance done): {res_in_end}")
    assert res_in_end[0] == 1.0
    assert res_in_end[4] == 0.0

    # 3. Test during middle (t = 4.0)
    res_mid = evaluate_item_animation(item, 4.0, 1080, 1920)
    print(f"At t=4.0 (static middle): {res_mid}")
    assert res_mid == (1.0, 0, 0, 1.0, 0.0)

    # 4. Test during exit (t = 6.4, 6.7, 7.0)
    res_out_start = evaluate_item_animation(item, 6.41, 1080, 1920)
    print(f"At t=6.41 (exit start): {res_out_start}")
    assert res_out_start[0] > 0.8
    assert res_out_start[2] >= 0

    res_out_mid = evaluate_item_animation(item, 6.7, 1080, 1920)
    print(f"At t=6.7 (exit mid): {res_out_mid}")
    assert 0.0 < res_out_mid[0] < 1.0
    assert res_out_mid[2] > 0 # sliding down

    res_out_end = evaluate_item_animation(item, 7.0, 1080, 1920)
    print(f"At t=7.0 (exit end): {res_out_end}")
    assert res_out_end[0] == 0.0 # fully vanished
    assert res_out_end[2] > 0

    # 5. Test all entrance presets
    all_in = [
        "fade", "tilt_slide_up", "tilt_slide_down", "slide_up", "slide_down",
        "slide_left", "slide_right", "float_in", "bounce", "pop",
        "zoom_in", "zoom_out", "dramatic_zoom", "spin_in", "drop_in", "flash", "glitch"
    ]
    for p_in in all_in:
        t_item = {"start_sec": 1.0, "end_sec": 5.0, "anim_in": p_in, "anim_out": "none", "anim_dur": 0.5}
        val = evaluate_item_animation(t_item, 1.25, 1080, 1920)
        assert len(val) == 5, f"Failed for {p_in}"
        assert 0.0 <= val[0] <= 1.0, f"Opacity out of bounds for {p_in}: {val[0]}"
    print(f"Successfully evaluated all {len(all_in)} Entrance presets!")

    # 6. Test all exit presets
    all_out = [
        "fade", "slide_down", "slide_up", "slide_left", "slide_right",
        "tilt_slide_down", "shrink", "zoom_out", "spin_out", "drop_out", "flash"
    ]
    for p_out in all_out:
        t_item = {"start_sec": 1.0, "end_sec": 5.0, "anim_in": "none", "anim_out": p_out, "anim_dur": 0.5}
        val = evaluate_item_animation(t_item, 4.75, 1080, 1920)
        assert len(val) == 5, f"Failed for {p_out}"
        assert 0.0 <= val[0] <= 1.0, f"Opacity out of bounds for {p_out}: {val[0]}"
    print(f"Successfully evaluated all {len(all_out)} Exit presets!")

    # 7. Test PIL image transformation with rotation and opacity
    test_img = Image.new("RGBA", (200, 60), (255, 100, 50, 255))
    transformed = apply_opacity_and_rotation(test_img, opacity=0.75, rotation_deg=-12.0)
    assert transformed.mode == "RGBA"
    assert transformed.width >= test_img.width
    assert transformed.height >= test_img.height
    print("PIL transformation with opacity & rotation OK!")

    print("ALL CANVAS ANIMATION TESTS PASSED 100%!")

if __name__ == "__main__":
    test_animations()
