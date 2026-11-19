import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw

tmp_dir = Path(tempfile.gettempdir()) / 'ffmpeg_anim_test'
tmp_dir.mkdir(exist_ok=True)
card = tmp_dir / 'card.png'
im = Image.new('RGBA', (400, 100), (40, 120, 220, 240))
d = ImageDraw.Draw(im)
d.text((20, 30), 'Test Banner Animation', fill=(255, 255, 255, 255))
im.save(str(card))

out_mp4 = tmp_dir / 'test_anim.mp4'

s = 0.5
d_in = 0.5
e = 2.5
d_out = 0.5
rot_expr = f"if(between(t,{s},{s+d_in}),(-12*PI/180)*(1-(t-{s})/{d_in}),0)"
p_in = f"((t-{s})/{d_in})"
ease_in = f"(1-(1-{p_in})*(1-{p_in})*(1-{p_in}))"
dy_in = f"if(between(t,{s},{s+d_in}),(1-{ease_in})*300,0)"

p_out = f"((t-({e}-{d_out}))/{d_out})"
dy_out = f"if(between(t,{e-d_out},{e}),({p_out}*{p_out})*400,0)"

y_expr = f"800+{dy_in}+{dy_out}-h/2"
x_expr = f"540-w/2"

card_path_esc = str(card).replace("\\", "/").replace(":", r"\:")

filter_complex = (
    f"movie='{card_path_esc}',format=rgba,"
    f"fade=t=in:st={s}:d={d_in}:alpha=1,fade=t=out:st={e-d_out}:d={d_out}:alpha=1,"
    f"rotate='{rot_expr}':c=none[ov];"
    f"[0:v][ov]overlay=x='{x_expr}':y='{y_expr}':eval=frame:enable='between(t,{s},{e})'[vout]"
)

cmd = [
    'ffmpeg', '-y',
    '-f', 'lavfi', '-i', 'color=c=black:s=1080x1920:d=3:r=30',
    '-filter_complex', filter_complex,
    '-map', '[vout]',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
    str(out_mp4)
]
res = subprocess.run(cmd, capture_output=True, text=True)
print('Returncode:', res.returncode)
if res.returncode != 0:
    print('STDERR:', res.stderr[-500:])
else:
    print('SUCCESS! File generated at:', out_mp4, 'Size:', out_mp4.stat().st_size)
