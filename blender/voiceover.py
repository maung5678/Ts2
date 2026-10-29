"""สร้างเสียงพากย์ฟรีแบบออฟไลน์ด้วย Piper TTS แล้ววางให้พอดีกับช่วงเวลาของแต่ละฉาก
- ยืด/หดแต่ละประโยคด้วย atempo ให้เต็มช่อง เว้นช่องว่างระหว่างประโยคไม่เกิน GAP วินาที
- ตรวจด้วย silencedetect ว่าไม่มีช่วงเงียบเกิน 0.32 วิ
ผลลัพธ์: blender/out/vo.wav + blender/out/vo.json (เวลาของแต่ละคำ ใช้ทำซับ)
ใช้งาน: python3 blender/voiceover.py
"""
import json
import os
import re
import subprocess
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = f"{HERE}/out"
VOICE = f"{HERE}/../assets/tts/en_US-ryan-high.onnx"
DURATION = 15.0
GAP = 0.12            # ช่องว่างระหว่างประโยค (ต้อง < 0.32)
MAX_SILENCE = 0.32
SR = 22050

# (เริ่ม, จบ, ประโยค) — ช่วงเวลาตรงกับ timeline ใน scene.py
LINES = [
    (0.05, 2.0, "Long ago, balls were made of stone."),
    (2.0, 4.0, "Problem is... stone balls don't bounce."),
    (4.0, 6.05, "So his buddy grabbed a pump, and filled one with air."),
    (6.05, 8.3, "Boing! Now it actually bounces. Clever!"),
    (8.3, 10.7, "But wait... where exactly are you supposed to throw this thing?"),
    (10.7, 12.4, "Into a basket, obviously!"),
    (12.4, 14.95, "And that's how basketball was invented. Follow for more!"),
]


def tts(text, path):
    subprocess.run(["python3", "-m", "piper", "-m", VOICE, "-f", path, "--sentence-silence", "0.08"],
                   input=text.encode(), check=True, capture_output=True)


def read(path):
    with wave.open(path) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768, w.getframerate()


def trim(a, thr=0.01):
    idx = np.where(np.abs(a) > thr)[0]
    return a[max(0, idx[0] - 200): idx[-1] + 400] if len(idx) else a


def squeeze_pauses(a, sr, max_pause=0.22):
    """บีบช่วงหยุดภายในประโยค (เช่นหลัง ... หรือ ,) ไม่ให้เกิน max_pause"""
    win = int(sr * 0.01)
    loud = np.array([np.abs(a[i:i + win]).max() > 0.01 for i in range(0, len(a), win)])
    keep, run = [], 0
    for i, l in enumerate(loud):
        run = 0 if l else run + 1
        if run * 0.01 <= max_pause:
            keep.append(a[i * win:(i + 1) * win])
    return np.concatenate(keep)


def atempo(a, sr, factor, tmp):
    src, dst = f"{tmp}_in.wav", f"{tmp}_out.wav"
    write(src, a, sr)
    chain = []
    f = factor
    while f > 2.0:
        chain.append("atempo=2.0"); f /= 2
    while f < 0.5:
        chain.append("atempo=0.5"); f /= 0.5
    chain.append(f"atempo={f:.4f}")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-af", ",".join(chain), dst], check=True)
    return read(dst)[0]


def write(path, a, sr):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())


os.makedirs(f"{OUT}/vo_parts", exist_ok=True)
track = np.zeros(int(SR * DURATION))
timing = []
cursor = LINES[0][0]
for i, (start, end, text) in enumerate(LINES):
    start = cursor  # วางต่อจากประโยคก่อนหน้าทันที จะได้ไม่มีช่วงเงียบสะสม
    raw = f"{OUT}/vo_parts/{i}.wav"
    tts(text, raw)
    a, sr = read(raw)
    assert sr == SR, sr
    a = squeeze_pauses(trim(a), sr)
    slot = end - start - GAP
    factor = (len(a) / sr) / slot          # >1 = เร่ง, <1 = ช้าลง
    factor = min(1.35, max(0.85, factor))  # คงความเป็นธรรมชาติของเสียง
    a = atempo(a, sr, factor, f"{OUT}/vo_parts/t{i}")
    a = squeeze_pauses(trim(a), sr)
    n = min(len(a), len(track) - int(start * SR))
    track[int(start * SR): int(start * SR) + n] += a[:n]
    dur = n / SR
    cursor = start + dur + GAP
    # เวลาของแต่ละคำ: กระจายตามจำนวนตัวอักษร (พอสำหรับซับคำต่อคำ)
    words = re.findall(r"\S+", text)
    weights = np.array([len(w.strip(".,!?")) + 2 for w in words], float)
    edges = start + np.concatenate([[0], np.cumsum(weights)]) / weights.sum() * dur
    timing.append({"start": start, "end": start + dur, "text": text,
                   "words": [{"w": w, "s": float(edges[j]), "e": float(edges[j + 1])} for j, w in enumerate(words)]})
    print(f"{start:5.2f}-{start + dur:5.2f}s  x{factor:.2f}  {text}")

track /= max(1e-6, np.abs(track).max()) / 0.95
write(f"{OUT}/vo.wav", track, SR)
json.dump(timing, open(f"{OUT}/vo.json", "w"), indent=1)

# ตรวจช่วงเงียบของเสียงพากย์
res = subprocess.run(["ffmpeg", "-i", f"{OUT}/vo.wav", "-af", f"silencedetect=noise=-38dB:d={MAX_SILENCE}",
                      "-f", "null", "-"], capture_output=True, text=True).stderr
gaps = re.findall(r"silence_duration: ([\d.]+)", res)
print("ช่วงเงียบเกิน", MAX_SILENCE, "วิ:", gaps or "ไม่มี ✓")
