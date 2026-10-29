"""ใส่ซับไตเติลแบบคำต่อคำ (ตัวหนา ขอบดำ เด้งตอนขึ้น) ลงบนเฟรมที่เรนเดอร์ แล้วรวมเป็น MP4
ใช้งาน: python3 blender/compose.py [output.mp4]
"""
import glob
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = sorted(glob.glob(f"{HERE}/out/frames/*.png"))
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else f"{HERE}/../output/clip_realistic.mp4")
FPS = 30
FONT = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
CAPTIONS = [
    (0.05, 0.6, "Stone"), (0.6, 1.25, "balls,"), (1.25, 1.75, "don't"), (1.75, 2.3, "bounce..."),
    (2.45, 3.3, "So"), (3.3, 3.95, "rubber!"), (3.95, 5.0, "Clever!"),
]
os.makedirs(f"{HERE}/out/composed", exist_ok=True)
for i, path in enumerate(FRAMES):
    t = i / FPS
    im = Image.open(path).convert("RGB")
    cap = next((c for c in CAPTIONS if c[0] <= t < c[1]), None)
    if cap:
        pop = min(1.0, (t - cap[0]) / 0.12)
        scale = 0.75 + 0.25 * pop + 0.08 * (1 - abs(2 * pop - 1)) * (pop < 1)
        size = int(im.width * 0.09 * scale)
        font = ImageFont.truetype(FONT, size)
        d = ImageDraw.Draw(im)
        cx, cy = im.width / 2, im.height * 0.555
        sw = max(2, size // 8)
        d.text((cx + 2, cy + 5), cap[2], font=font, anchor="mm", fill=(0, 0, 0), stroke_width=sw, stroke_fill=(0, 0, 0))
        d.text((cx, cy), cap[2], font=font, anchor="mm", fill=(255, 255, 255), stroke_width=sw, stroke_fill=(17, 17, 17))
    im.save(f"{HERE}/out/composed/{i:04d}.png")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{HERE}/out/composed/%04d.png",
                "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
               check=True)
print("บันทึกแล้ว:", OUT, len(FRAMES), "เฟรม")
