"""แผน B: อัปสเกลเฟรม 540p → 1080p ด้วย AI (FSRCNN) + ใส่ซับคำต่อคำ + สังเคราะห์เสียงประกอบ → MP4
ใช้งาน: CLIP_FPS=24 python3 blender/compose.py [output.mp4]
"""
import glob
import os
import subprocess
import sys
import wave

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = f"{HERE}/out"
FRAMES = sorted(glob.glob(f"{OUT_DIR}/frames/*.png"))
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else f"{HERE}/../output/clip_viral_15s.mp4")
FPS = int(os.environ.get("CLIP_FPS", 24))
FONT = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
SR_MODEL = f"{HERE}/../assets/sr/FSRCNN_x2.pb"
sys.path.insert(0, HERE)
import json  # noqa: E402
from timeline import CUT, DRIB_END, DRIB_START, DRIBBLE_HZ, IMPACT_T, LAND_T, PUMP_END, PUMP_HZ, PUMP_START, SHOOT_T  # noqa: E402

# ซับคำต่อคำจากเวลาเสียงพากย์ (รวมคำสั้น ๆ ให้แต่ละชิ้นค้างอย่างน้อย 0.3 วิ)
HIGHLIGHT = {"stone": (200, 200, 200), "don't": (255, 80, 60), "air.": (120, 220, 255), "boing!": (255, 214, 60),
             "clever!": (255, 214, 60), "basket,": (255, 140, 40), "basketball": (255, 140, 40), "throw": (255, 214, 60)}
CAPTIONS = []
for line in json.load(open(f"{OUT_DIR}/vo.json")):
    chunk = []
    for w in line["words"]:
        chunk.append(w)
        if chunk[-1]["e"] - chunk[0]["s"] >= 0.3 or w is line["words"][-1]:
            text = " ".join(c["w"] for c in chunk)
            color = next((HIGHLIGHT[c["w"].lower()] for c in chunk if c["w"].lower() in HIGHLIGHT), None)
            CAPTIONS.append((chunk[0]["s"], chunk[-1]["e"], text, color))
            chunk = []

# ---------- 1) อัปสเกล + ซับ ----------
sr = cv2.dnn_superres.DnnSuperResImpl_create()
sr.readModel(SR_MODEL); sr.setModel("fsrcnn", 2)
os.makedirs(f"{OUT_DIR}/composed", exist_ok=True)
for i, path in enumerate(FRAMES):
    t = i / FPS
    up = sr.upsample(cv2.imread(path))
    if up.shape[1] != 1080:
        up = cv2.resize(up, (1080, 1920), interpolation=cv2.INTER_LANCZOS4)
    im = Image.fromarray(cv2.cvtColor(up, cv2.COLOR_BGR2RGB))
    cap = next((c for c in reversed(CAPTIONS) if c[0] <= t < c[1] + 0.2), None)
    if cap:
        pop = min(1.0, (t - cap[0]) / 0.1)
        scale = 0.7 + 0.3 * pop + (0.1 if 0.4 < pop < 1 else 0)
        size = int(im.width * 0.1 * scale)
        font = ImageFont.truetype(FONT, size)
        d = ImageDraw.Draw(im)
        cx, cy = im.width / 2, im.height * 0.56
        sw = max(3, size // 7)
        d.text((cx + 3, cy + 7), cap[2], font=font, anchor="mm", fill=(0, 0, 0), stroke_width=sw, stroke_fill=(0, 0, 0))
        d.text((cx, cy), cap[2], font=font, anchor="mm", fill=cap[3] or (255, 255, 255),
               stroke_width=sw, stroke_fill=(15, 15, 15))
    im.save(f"{OUT_DIR}/composed/{i:04d}.png")
    if i % 24 == 0:
        print(f"composed {i}/{len(FRAMES)}", flush=True)

# ---------- 2) เสียงประกอบ (สังเคราะห์ ไม่ติดลิขสิทธิ์) ----------
SR_A = 44100
dur = len(FRAMES) / FPS
audio = np.zeros(int(SR_A * dur) + SR_A)
rng = np.random.default_rng(1)


def add(t, sig, gain=1.0):
    i = int(t * SR_A)
    n = min(len(sig), len(audio) - i)
    if n > 0:
        audio[i:i + n] += sig[:n] * gain


def env(n, a=0.002, d=0.15):
    t = np.arange(n) / SR_A
    return np.minimum(1, t / a) * np.exp(-t / d)


def thud(freq=70, d=0.35, noise=0.6):
    n = int(SR_A * d * 3); t = np.arange(n) / SR_A
    f = freq * (1 + 1.5 * np.exp(-t * 30))
    return (np.sin(2 * np.pi * np.cumsum(f) / SR_A) + noise * rng.normal(0, 1, n) * np.exp(-t * 40)) * env(n, d=d)


def bounce():
    n = int(SR_A * 0.25); t = np.arange(n) / SR_A
    return (np.sin(2 * np.pi * 140 * t) * 0.8 + rng.normal(0, 0.4, n) * np.exp(-t * 80)) * env(n, d=0.06)


def whoosh(d=0.5, up=True):
    n = int(SR_A * d); x = rng.normal(0, 1, n)
    k = np.linspace(0.02, 0.4, n) if up else np.linspace(0.4, 0.02, n)
    y = np.zeros(n); acc = 0.0
    for i in range(n):  # low-pass แบบไล่ความถี่
        acc += k[i] * (x[i] - acc); y[i] = acc
    return y * np.sin(np.linspace(0, np.pi, n)) * 2.0


def pop():
    n = int(SR_A * 0.12); t = np.arange(n) / SR_A
    return np.sin(2 * np.pi * (900 - 4000 * t) * t) * env(n, d=0.03)


# ดนตรีพื้นหลัง: บีทเบา ๆ 100 BPM + เบสไลน์ (ดังต่อเนื่อง ไม่มีช่วงเงียบ)
beat = 60 / 100
for k in range(int(dur / beat) + 1):
    add(k * beat, thud(55, 0.18, 0.1), 0.3)
    add(k * beat + beat / 2, rng.normal(0, 1, int(SR_A * 0.05)) * env(int(SR_A * 0.05), d=0.01), 0.07)
    note = [55, 55, 65.4, 49][k % 4]
    n = int(SR_A * beat); tt = np.arange(n) / SR_A
    add(k * beat, np.sin(2 * np.pi * note * tt) * env(n, 0.01, 0.4), 0.16)

add(IMPACT_T, thud(45, 0.5, 1.0), 1.4)                      # ลูกหินกระแทก
add(CUT, whoosh(0.35, True), 0.5)                            # ตัดช็อต
t = PUMP_START
while t < PUMP_END:                                          # เสียงสูบลม "ฟู่"
    add(t + 0.5 / PUMP_HZ - 0.15, whoosh(0.25, False), 0.35)
    t += 1 / PUMP_HZ
for n in range(int((DRIB_END - DRIB_START) * DRIBBLE_HZ)):
    add(DRIB_START + (n + 0.5) / DRIBBLE_HZ, bounce(), 1.1)  # ลูกบาสกระทบพื้น
add(SHOOT_T, whoosh(0.7, False), 0.45)                       # ชู้ต
add(LAND_T, thud(110, 0.25, 0.5), 1.0)                       # ลงลัง
music = audio.copy()

# เสียงพากย์ (resample 22.05k → 44.1k) และลดเสียงดนตรีลงตอนมีคนพูด
with wave.open(f"{OUT_DIR}/vo.wav") as w:
    vo = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    vo = np.interp(np.arange(int(len(vo) * SR_A / w.getframerate())) * w.getframerate() / SR_A, np.arange(len(vo)), vo)
voice = np.zeros_like(audio); voice[: len(vo)] = vo[: len(audio)]
music /= max(1e-6, np.abs(music).max())
audio = voice * 1.0 + music * 0.28
audio /= max(1e-6, np.abs(audio).max()) / 0.9
with wave.open(f"{OUT_DIR}/audio.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR_A)
    w.writeframes((audio[: int(SR_A * dur)] * 32767).astype(np.int16).tobytes())

# ---------- 3) รวมไฟล์ ----------
os.makedirs(os.path.dirname(OUT), exist_ok=True)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{OUT_DIR}/composed/%04d.png",
                "-i", f"{OUT_DIR}/audio.wav", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT], check=True)
print("บันทึกแล้ว:", OUT, len(FRAMES), "เฟรม")
