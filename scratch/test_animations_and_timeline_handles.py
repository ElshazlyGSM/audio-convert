import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
import tkinter as tk
from unittest.mock import MagicMock

# 1. Test icons library scale limit
from video_studio.icons_library import render_media_overlay_pil, ICON_PRESETS
from video_studio.branding import build_timed_rgba_overlay_filter
from ui_modules.studio_canvas import evaluate_item_animation

print("Testing scale limits...")
item_sc = {"type": "icon", "icon_key": "subscribe_ar", "scale": 2.8}
im = render_media_overlay_pil(item_sc, 1000, 1000, is_ar=True)
assert im is not None
assert im.width == int(round(1000 * 2.8)), f"Expected width {int(round(1000 * 2.8))}, got {im.width}"
print("Scale 2.8 rendered successfully with width:", im.width)

# 2. Test animation evaluation (In & Out independent durations)
print("Testing animation evaluation...")
item = {
    "start_sec": 2.0,
    "end_sec": 8.0,
    "anim_in": "tilt_slide_up",
    "anim_out": "slide_down",
    "anim_dur_in": 1.2,
    "anim_dur_out": 0.8,
}
# Before start
op, dx, dy, sc, rot = evaluate_item_animation(item, 1.5, 1080, 1920)
assert op == 0.0, f"Expected opacity 0.0 before start, got {op}"

# During entrance (at 2.6s, midway through 1.2s entrance)
op, dx, dy, sc, rot = evaluate_item_animation(item, 2.6, 1080, 1920)
assert 0.0 < op < 1.0, f"Expected partial opacity during in, got {op}"
assert dy != 0.0 or rot != 0.0, "Expected movement/rotation during tilt_slide_up"

# Fully entered (at 5.0s)
op, dx, dy, sc, rot = evaluate_item_animation(item, 5.0, 1080, 1920)
assert op == 1.0, f"Expected full opacity during hold, got {op}"
assert dy == 0.0 and rot == 0.0, "Expected no offset during hold"

# During exit (at 7.6s, midway through 0.8s exit, exit starts at 7.2s)
op, dx, dy, sc, rot = evaluate_item_animation(item, 7.6, 1080, 1920)
assert 0.0 < op < 1.0, f"Expected partial opacity during out, got {op}"
assert dy > 0, "Expected downward slide on exit"

# After end
op, dx, dy, sc, rot = evaluate_item_animation(item, 8.5, 1080, 1920)
assert op == 0.0, f"Expected opacity 0.0 after end, got {op}"
print("Animation evaluation verified!")

# 3. Test FFmpeg filter builder with anim_dur_in and anim_dur_out
print("Testing FFmpeg filter string generation...")
test_img_path = Path("scratch/test_tmp.png")
im.save(test_img_path)
flt = build_timed_rgba_overlay_filter(
    test_img_path,
    x_pct=0.5,
    y_pct=0.5,
    video_w=1080,
    video_h=1920,
    start_sec=1.0,
    end_sec=5.0,
    full_duration=False,
    anim_in="tilt_slide_up",
    anim_out="slide_down",
    anim_dur_in=1.0,
    anim_dur_out=0.7,
    input_label="v_main",
    output_label="v_out",
)
print("FLT output:\n", flt)
assert "1.000" in flt or "1.0" in flt, "Expected dur_in 1.0 in filter"
assert "0.700" in flt or "0.7" in flt, "Expected dur_out 0.7 in filter"
print("FFmpeg filter generation verified!")
assert "0.700" in flt, "Expected dur_out 0.700 in filter"
print("FFmpeg filter generation verified!")

# 4. Test Timeline widget animation handles and dragging
print("Testing timeline animation hit testing and dragging...")
root = tk.Tk()
root.withdraw()

from ui_dialogs.nle_timeline_widget import DaVinciTimelinePanel
from video_studio.timeline_engine import NLEProjectState

project = NLEProjectState()
project.reset_for_media("sample.mp4", 20.0)
project.get_track_list("V2").append({
    "type": "image",
    "path": "banner.png",
    "start_sec": 2.0,
    "end_sec": 10.0,
    "anim_in": "tilt_slide_up",
    "anim_out": "slide_down",
    "anim_dur_in": 0.8,
    "anim_dur_out": 0.6,
})

timeline = DaVinciTimelinePanel(
    root,
    nle_state=project,
    is_ar_fn=lambda: True,
    on_scrub=lambda s, f: None,
    on_select=lambda r: None,
    on_modified=lambda: None,
    on_add_element=lambda e, s: None,
)
timeline.pack()
timeline.update_idletasks()
timeline.redraw()

# Check that anim hit boxes were created
assert len(timeline._anim_hit_boxes) >= 2, f"Expected at least 2 anim hit boxes, found {len(timeline._anim_hit_boxes)}"
box_in = next(b for b in timeline._anim_hit_boxes if b[0] == "anim_in")
box_out = next(b for b in timeline._anim_hit_boxes if b[0] == "anim_out")
print("Found anim boxes:", box_in[0], "and", box_out[0])

# Test hover over handle ax1
class MockEvent:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.x_root = x + 100
        self.y_root = y + 100
        self.state = 0

# Mock event at ax1 (entrance handle)
handle_x = box_in[4] # ax1
handle_y = (box_in[5] + box_in[6]) // 2
timeline._on_hover(MockEvent(handle_x, handle_y))
assert timeline.canvas.cget("cursor") == "sb_h_double_arrow", f"Expected sb_h_double_arrow cursor, got {timeline.canvas.cget('cursor')}"
print("Hover on entrance handle correctly set cursor to sb_h_double_arrow!")

# Test press on handle
timeline._on_press(MockEvent(handle_x, handle_y))
assert timeline._drag_action == "resize_anim_in", f"Expected drag_action 'resize_anim_in', got {timeline._drag_action}"
print("Press on entrance handle initiated drag action:", timeline._drag_action)

# Test drag (increase duration by dragging right)
orig_dur = timeline._drag_anim_orig_dur
px_per_sec = max(1.0, timeline._drag_ref_tot_px / max(0.1, timeline._drag_ref_tot_dur))
dx = int(0.5 * px_per_sec) # drag by ~0.5s right
timeline._on_drag(MockEvent(handle_x + dx, handle_y))
item = project.get_track_list("V2")[0]
new_dur = item["anim_dur_in"]
assert new_dur > orig_dur, f"Expected duration to increase from {orig_dur}, got {new_dur}"
print(f"Dragged duration changed from {orig_dur}s to {new_dur}s successfully!")

# Test release
timeline._on_release(MockEvent(handle_x + dx, handle_y))
assert timeline._drag_action is None, "Drag action should be cleared on release"
print("Release handled cleanly!")

# Test right-click context menu on overlay
print("Testing right-click on overlay in timeline...")
ev_rc = MockEvent(box_in[3] + 10, handle_y)
# Monkey-patch tk_popup so it doesn't block
orig_popup = tk.Menu.tk_popup
popup_called = []
def mock_popup(menu_self, x, y, entry=""):
    popup_called.append(menu_self)
tk.Menu.tk_popup = mock_popup
try:
    timeline._on_right_click(ev_rc)
    assert len(popup_called) == 1, "Expected right-click menu to be popped up"
    print("Right-click context menu verified successfully!")
finally:
    tk.Menu.tk_popup = orig_popup

root.destroy()
print("ALL TESTS PASSED SUCCESSFULLY!")
