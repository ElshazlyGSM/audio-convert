import sys
from pathlib import Path
import subprocess
import tempfile

sys.path.insert(0, ".")
from video_studio.transitions import build_xfade_filter_chains, TRANSITION_PRESETS

def test_clip_transitions():
    print(f"=== Testing Multi-Clip Transitions (Total presets: {len(TRANSITION_PRESETS)}) ===")
    assert len(TRANSITION_PRESETS) >= 56

    filter_chains, total_dur = build_xfade_filter_chains(
        n_segs=2,
        seg_durations=[3.0, 3.0],
        transitions_config={
            "enabled": True,
            "default_transition": "coverup",
            "default_duration": 0.5,
            "apply_to_all": True,
        },
        has_audio=True
    )
    print(f"Generated xfade chain (total duration: {total_dur}s):")
    joined = " ".join(filter_chains)
    print(joined)
    assert "transition=coverup" in joined
    assert total_dur == 5.5

    tmp_dir = Path(tempfile.gettempdir()) / "test_xfade_run"
    tmp_dir.mkdir(exist_ok=True)
    out_mp4 = tmp_dir / "xfade_result.mp4"

    cmd1 = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=red:s=720x1280:d=2:r=30",
        "-f", "lavfi", "-i", "color=c=blue:s=720x1280:d=2:r=30",
        "-filter_complex", "[0:v][1:v]xfade=transition=coverup:duration=0.5:offset=1.5[v]",
        "-map", "[v]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(out_mp4)
    ]
    res1 = subprocess.run(cmd1, capture_output=True, text=True)
    assert res1.returncode == 0
    assert out_mp4.is_file() and out_mp4.stat().st_size > 1000
    print(f"SUCCESS! Rendered xfade coverup transition video: {out_mp4} ({out_mp4.stat().st_size} bytes)")

    out_mp4_2 = tmp_dir / "xfade_revealup.mp4"
    cmd2 = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=red:s=720x1280:d=2:r=30",
        "-f", "lavfi", "-i", "color=c=blue:s=720x1280:d=2:r=30",
        "-filter_complex", "[0:v][1:v]xfade=transition=revealup:duration=0.5:offset=1.5[v]",
        "-map", "[v]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(out_mp4_2)
    ]
    res2 = subprocess.run(cmd2, capture_output=True, text=True)
    assert res2.returncode == 0
    assert out_mp4_2.is_file() and out_mp4_2.stat().st_size > 1000
    print(f"SUCCESS! Rendered xfade revealup transition video: {out_mp4_2} ({out_mp4_2.stat().st_size} bytes)")

    print("ALL CLIP TRANSITION TESTS PASSED 100%!")

if __name__ == "__main__":
    test_clip_transitions()
