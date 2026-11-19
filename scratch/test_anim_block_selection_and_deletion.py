import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import tkinter as tk
from tkinter import ttk
from unittest.mock import MagicMock
from video_studio.timeline_engine import NLEProjectState
from ui_dialogs.nle_timeline_widget import DaVinciTimelinePanel

print("--- Testing Animation Block Individual Selection & Deletion ---")

root = tk.Tk()
root.withdraw()

project = NLEProjectState()
project.reset_for_media("sample.mp4", 20.0)
project.get_track_list("V2").append({
    "type": "image",
    "path": "test_banner.png",
    "start_sec": 2.0,
    "end_sec": 10.0,
    "anim_in": "tilt_slide_up",
    "anim_out": "slide_down",
    "anim_dur_in": 0.8,
    "anim_dur_out": 0.6,
})

selected_calls = []
def mock_select(ref):
    selected_calls.append(ref)

timeline = DaVinciTimelinePanel(
    root,
    nle_state=project,
    is_ar_fn=lambda: True,
    on_scrub=lambda s, f: None,
    on_select=mock_select,
    on_modified=lambda: None,
    on_add_element=lambda e, s: None,
)
timeline.pack()
timeline.update_idletasks()
timeline.redraw()

# 1. Verify hit boxes exist
assert len(timeline._anim_hit_boxes) == 2, f"Expected 2 anim boxes, found {len(timeline._anim_hit_boxes)}"
in_box = next(b for b in timeline._anim_hit_boxes if b[0] == "anim_in")
out_box = next(b for b in timeline._anim_hit_boxes if b[0] == "anim_out")

class MockEvent:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.x_root = x + 100
        self.y_root = y + 100
        self.state = 0

# 2. Click directly on Entrance Animation Block
mid_in_x = (in_box[3] + in_box[4]) // 2
mid_in_y = (in_box[5] + in_box[6]) // 2
timeline._on_press(MockEvent(mid_in_x, mid_in_y))

assert timeline.selected_ref == ("anim_in", "V2", 0), f"Expected ('anim_in', 'V2', 0), got {timeline.selected_ref}"
print("✓ Click on entrance animation block correctly selected ('anim_in', 'V2', 0) individually!")

# Release without drag
timeline._on_release(MockEvent(mid_in_x, mid_in_y))
assert timeline.selected_ref == ("anim_in", "V2", 0), "Selection should remain on release"

# 3. Test deleting the selected entrance animation via delete_selected()
item = project.get_track_list("V2")[0]
assert item["anim_in"] == "tilt_slide_up"
assert len(project.get_track_list("V2")) == 1

timeline.delete_selected()

assert item["anim_in"] == "none", f"Expected anim_in 'none', got {item['anim_in']}"
assert len(project.get_track_list("V2")) == 1, "Parent item must NOT be deleted when deleting animation block!"
assert timeline.selected_ref == ("V2", 0), f"Expected selection to fall back to ('V2', 0), got {timeline.selected_ref}"
print("✓ delete_selected() deleted ONLY anim_in, leaving parent item intact!")

# 4. Now test selecting Exit Animation Block
timeline.redraw()
assert len(timeline._anim_hit_boxes) == 1, "Only anim_out should remain"
out_box2 = timeline._anim_hit_boxes[0]
assert out_box2[0] == "anim_out"

mid_out_x = (out_box2[3] + out_box2[4]) // 2
mid_out_y = (out_box2[5] + out_box2[6]) // 2
timeline._on_press(MockEvent(mid_out_x, mid_out_y))

assert timeline.selected_ref == ("anim_out", "V2", 0), f"Expected ('anim_out', 'V2', 0), got {timeline.selected_ref}"
print("✓ Click on exit animation block correctly selected ('anim_out', 'V2', 0) individually!")

# 5. Test deleting the selected exit animation via delete_selected()
assert item["anim_out"] == "slide_down"
timeline.delete_selected()

assert item["anim_out"] == "none", f"Expected anim_out 'none', got {item['anim_out']}"
assert len(project.get_track_list("V2")) == 1, "Parent item must NOT be deleted when deleting exit animation!"
print("✓ delete_selected() deleted ONLY anim_out, leaving parent item intact!")

# 6. Test right-click on animation block
item["anim_in"] = "tilt_slide_up"
item["anim_out"] = "slide_down"
timeline.redraw()
in_box3 = next(b for b in timeline._anim_hit_boxes if b[0] == "anim_in")
mid_in_x3 = (in_box3[3] + in_box3[4]) // 2

orig_popup = tk.Menu.tk_popup
popup_menus = []
def mock_popup(menu_self, x, y, entry=""):
    popup_menus.append(menu_self)
tk.Menu.tk_popup = mock_popup
try:
    timeline._on_right_click(MockEvent(mid_in_x3, mid_in_y))
    assert len(popup_menus) == 1, "Right click menu should open"
    assert timeline.selected_ref == ("anim_in", "V2", 0), f"Right click should select anim_in, got {timeline.selected_ref}"
    print("✓ Right-click directly on anim block selected it and opened dedicated animation menu!")
finally:
    tk.Menu.tk_popup = orig_popup

# 7. Test Inspector UI generation
print("Testing Inspector UI generation for animation block...")
class MockApp:
    def __init__(self, proj):
        self.language_var = tk.StringVar(value="العربية")
        self.nle_project = proj
        self.item_prop_card = ttk.LabelFrame(root, text="Properties")
        self.player_canvas_selected = ("anim_in", "V2", 0)
        self.video_branding_config = {}
        self.nle_playhead_sec = 0.0

    def _normalize_selection_ref(self, sel):
        from ui_modules.studio_canvas import StudioCanvasMixin
        return StudioCanvasMixin._normalize_selection_ref(self, sel)

    def _show_inspector_context(self, ctx):
        pass

    def _on_nle_timeline_select(self, ref):
        pass

    def _save_settings(self):
        pass

    def _render_player_studio_canvas(self):
        pass

from gui import SongCoverApp
mock_app = MockApp(project)
SongCoverApp._update_inspector_properties(mock_app)

card_title = mock_app.item_prop_card.cget("text")
assert "حركة الدخول" in card_title, f"Expected 'حركة الدخول' in title, got {card_title}"
assert len(mock_app.item_prop_card.winfo_children()) >= 4, "Expected widgets inside item_prop_card"
print(f"✓ Inspector Card rendered with title: '{card_title}' and {len(mock_app.item_prop_card.winfo_children())} control rows!")

root.destroy()
print("\n>>> ALL TESTS PASSED SUCCESSFULLY! <<<")
