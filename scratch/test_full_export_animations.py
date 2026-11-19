import sys
from pathlib import Path
import subprocess
import tempfile
from PIL import Image, ImageDraw

sys.path.insert(0, ".")
from video_studio.branding import build_timed_rgba_overlay_filter

def test_full_export():
    print("=== Testing build_timed_rgba_overlay_filter in FFmpeg ===")
    tmp_dir = Path(tempfile.gettempdir()) / "test_full_export_anim"
    tmp_dir.mkdir(exist_ok=True)

    # 1. Create a paper banner text overlay image like the user's video
    banner_png = tmp_dir / "paper_banner.png"
    bim = Image.new("RGBA", (500, 110), (245, 240, 230, 255))
    d = ImageDraw.Draw(bim)
    d.rectangle([4, 4, 496, 106], outline=(180, 150, 100, 255), width=3)
    d.text((40, 35), "هل يجوز للحائض الطواف بالبيت؟", fill=(20, 20, 20, 255))
    bim.save(str(banner_png))

    # 2. Test filter generation with tilt_slide_up entrance and slide_down exit
    f_seg = build_timed_rgba_overlay_filter(
        image_path=banner_png,
        x_pct=0.5,
        y_pct=0.85,
        video_w=1080,
        video_h=1920,
        img_w=500,
        img_h=110,
        anchor="center",
        start_sec=1.0,
        end_sec=4.0,
        full_duration=False,
        anim_in="tilt_slide_up",
        anim_out="slide_down",
        anim_dur=0.6,
        stream_id="ov_banner",
        input_label="v_in",
        output_label="v_out",
    )
    print("Generated filter segment:")
    print(f_seg)

    out_mp4 = tmp_dir / "rendered_sample.mp4"
    full_filter = f"[0:v]null[v_in];{f_seg}"

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=darkblue:s=1080x1920:d=5:r=30",
        "-filter_complex", full_filter,
        "-map", "[v_out]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(out_mp4)
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("FFmpeg Render FAILED:")
        print(res.stderr[-500:])
        assert False, "FFmpeg render failed"

    assert out_mp4.is_file() and out_mp4.stat().st_size > 1000
    print(f"SUCCESS! Rendered video: {out_mp4} ({out_mp4.stat().st_size} bytes)")

    # 3. Extract frames at key timestamps:
    # 0.5s (before), 1.3s (during tilted entrance), 2.5s (static middle), 3.8s (during exit slide down), 4.5s (after)
    frames = [
        ("before", 0.5),
        ("in_tilted", 1.3),
        ("middle", 2.5),
        ("exit_sliding", 3.8),
        ("after", 4.5),
    ]
    for name, ts in frames:
        fp = tmp_dir / f"frame_{name}.png"
        subprocess.run(["ffmpeg", "-y", "-ss", str(ts), "-i", str(out_mp4), "-vframes", "1", str(fp)], capture_output=True)
        assert fp.is_file() and fp.stat().st_size > 500
        print(f"Extracted {name} at {ts}s: {fp.stat().st_size} bytes")

    print("ALL FULL EXPORT ANIMATION TESTS PASSED 100%!")

if __name__ == "__main__":
    test_full_export()
