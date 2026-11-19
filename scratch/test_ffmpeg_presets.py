import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw

def test_preset_ffmpeg(anim_in, anim_out):
    tmp_dir = Path(tempfile.gettempdir()) / 'ffmpeg_test_presets'
    tmp_dir.mkdir(exist_ok=True)
    card = tmp_dir / f'card_{anim_in}_{anim_out}.png'
    im = Image.new('RGBA', (300, 80), (220, 50, 50, 240))
    d = ImageDraw.Draw(im)
    d.text((20, 25), f'{anim_in} -> {anim_out}', fill=(255, 255, 255, 255))
    im.save(str(card))

    out_mp4 = tmp_dir / f'out_{anim_in}_{anim_out}.mp4'
    card_esc = str(card).replace("\\", "/").replace(":", r"\:")

    s = 0.5
    d_in = 0.5
    e = 2.5
    d_out = 0.5
    s_out = e - d_out

    filters_movie = ["format=rgba"]
    fade_in_str = f"fade=t=in:st={s:.3f}:d={d_in:.3f}:alpha=1"
    fade_out_str = f"fade=t=out:st={s_out:.3f}:d={d_out:.3f}:alpha=1"

    rot_exprs = []
    if anim_in == "tilt_slide_up":
        rot_exprs.append(f"if(between(t,{s:.3f},{s+d_in:.3f}),(-12*PI/180)*(1-(t-{s:.3f})/{d_in:.3f}),0)")
        filters_movie.append(fade_in_str)
    elif anim_in == "spin_in":
        rot_exprs.append(f"if(between(t,{s:.3f},{s+d_in:.3f}),(-2*PI)*(1-(t-{s:.3f})/{d_in:.3f}),0)")
        filters_movie.append(fade_in_str)
    elif anim_in in ("fade", "slide_up", "slide_down", "slide_left", "slide_right", "bounce", "pop", "drop_in"):
        filters_movie.append(fade_in_str)

    if anim_out == "tilt_slide_down":
        rot_exprs.append(f"if(between(t,{s_out:.3f},{e:.3f}),(12*PI/180)*((t-{s_out:.3f})/{d_out:.3f}),0)")
        filters_movie.append(fade_out_str)
    elif anim_out == "spin_out":
        rot_exprs.append(f"if(between(t,{s_out:.3f},{e:.3f}),(2*PI)*((t-{s_out:.3f})/{d_out:.3f}),0)")
        filters_movie.append(fade_out_str)
    elif anim_out in ("fade", "slide_down", "slide_up", "slide_left", "slide_right", "drop_out"):
        filters_movie.append(fade_out_str)

    if rot_exprs:
        rot_sum = "+".join(rot_exprs)
        filters_movie.append(f"rotate='{rot_sum}':c=none")

    movie_chain = ",".join(filters_movie)

    # Offset calculations
    dx_parts = []
    dy_parts = []

    p_in = f"((t-{s:.3f})/{d_in:.3f})"
    ease_in = f"(1-(1-{p_in})*(1-{p_in})*(1-{p_in}))"

    q_out = f"((t-{s_out:.3f})/{d_out:.3f})"

    if anim_in == "tilt_slide_up":
        dy_parts.append(f"if(between(t,{s:.3f},{s+d_in:.3f}),(1-{ease_in})*(0.22*H),0)")
        dx_parts.append(f"if(between(t,{s:.3f},{s+d_in:.3f}),-(1-{ease_in})*(0.04*W),0)")
    elif anim_in == "slide_up":
        dy_parts.append(f"if(between(t,{s:.3f},{s+d_in:.3f}),(1-{ease_in})*(0.22*H),0)")
    elif anim_in == "slide_left":
        dx_parts.append(f"if(between(t,{s:.3f},{s+d_in:.3f}),(1-{ease_in})*(0.30*W),0)")
    elif anim_in == "bounce":
        dy_parts.append(f"if(between(t,{s:.3f},{s+d_in:.3f}),(1-{p_in})*sin({p_in}*7.85)*(-0.15*H)+(1-{p_in})*(1-{p_in})*(0.20*H),0)")

    if anim_out == "slide_down":
        dy_parts.append(f"if(between(t,{s_out:.3f},{e:.3f}),({q_out}*{q_out})*(0.35*H),0)")
    elif anim_out == "tilt_slide_down":
        dy_parts.append(f"if(between(t,{s_out:.3f},{e:.3f}),({q_out}*{q_out})*(0.35*H),0)")
        dx_parts.append(f"if(between(t,{s_out:.3f},{e:.3f}),({q_out}*{q_out})*(0.04*W),0)")
    elif anim_out == "slide_left":
        dx_parts.append(f"if(between(t,{s_out:.3f},{e:.3f}),-({q_out}*{q_out})*(0.40*W),0)")

    x_expr = "W*0.5-w/2"
    if dx_parts:
        x_expr += "+" + "+".join(dx_parts)

    y_expr = "H*0.8-h/2"
    if dy_parts:
        y_expr += "+" + "+".join(dy_parts)

    filter_complex = (
        f"movie='{card_esc}',{movie_chain}[ov];"
        f"[0:v][ov]overlay=x='{x_expr}':y='{y_expr}':eval=frame:enable='between(t,{s:.3f},{e:.3f})'[vout]"
    )

    cmd = [
        'ffmpeg', '-y',
        '-f', 'lavfi', '-i', 'color=c=black:s=720x1280:d=3:r=30',
        '-filter_complex', filter_complex,
        '-map', '[vout]',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        str(out_mp4)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"FAILED {anim_in}->{anim_out}: {res.stderr[-300:]}")
        return False
    else:
        print(f"SUCCESS {anim_in}->{anim_out}: file size {out_mp4.stat().st_size} bytes")
        return True

test_pairs = [
    ("tilt_slide_up", "slide_down"),
    ("bounce", "tilt_slide_down"),
    ("slide_left", "slide_left"),
    ("spin_in", "slide_down"),
]

all_ok = True
for a_in, a_out in test_pairs:
    if not test_preset_ffmpeg(a_in, a_out):
        all_ok = False
print("ALL TESTS PASSED:", all_ok)
