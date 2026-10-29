# คลิปอนิเมชั่น 3D สนามบาส (5 วินาที)

มีสองเวอร์ชัน:

| เวอร์ชัน | ไฟล์ | เทคนิค |
|---|---|---|
| **สมจริง (แนะนำ)** | `output/clip_realistic.mp4` | Blender Cycles path tracing + โมเดลคนสแกนจริง + texture PBR |
| สไตล์ low-poly | `output/clip.mp4` | Three.js (WebGL) รูปทรงพื้นฐานล้วน |

## เนื้อเรื่อง
- **0.0–2.3 วิ** ช็อตใกล้: ชายเสื้อเชิ้ตน้ำเงินปล่อย "ลูกหิน" ลงพื้น → ไม่เด้ง เศษหินกระจาย กล้องสั่น (ซับ *Stone balls, don't bounce...*)
- **2.3–5.0 วิ** มุมกว้าง: ชายเสื้อยืดขาวยืนข้างที่สูบลมแล้วชี้ ชายเสื้อน้ำเงินเลี้ยงลูกบาส (ซับ *So rubber! Clever!*)

## เวอร์ชันสมจริง (`blender/`)
- `fetch_assets.py` — ดาวน์โหลด HDRI ท้องฟ้า, texture PBR (ยางมะตอย, ไม้, หิน, ผนัง, หลังคา) และโมเดลต้นไม้/พุ่มไม้/ที่สูบลม จาก [Poly Haven](https://polyhaven.com) (CC0)
- `prep_characters.py` — ดาวน์โหลดตัวละคร [Microsoft Rocketbox](https://github.com/microsoft/Microsoft-Rocketbox) (MIT) แล้วย้อมสีเสื้อผ้าให้ตรงกับคลิป
- `scene.py` — สร้างฉาก, จัดท่าตัวละครด้วย IK แบบสองท่อนที่เขียนเอง (ขาแตะพื้น, มือตามลูกบอล), ฟิสิกส์ลูกบอล/เศษหิน, กล้อง, motion blur, depth of field แล้วเรนเดอร์ด้วย Cycles
- `compose.py` — ใส่ซับไตเติลคำต่อคำแล้วรวมเป็น MP4

```bash
pip install bpy pillow numpy          # Blender แบบ Python module
python3 blender/fetch_assets.py
python3 blender/prep_characters.py
python3 blender/scene.py --samples 20  # เรนเดอร์ 150 เฟรม (CPU 4 core ≈ 40 วิ/เฟรม)
python3 blender/compose.py             # ได้ output/clip_realistic.mp4
python3 blender/scene.py --still 100 --scale 50   # เรนเดอร์เฟรมเดียวไว้ตรวจภาพ
```
ถ้ามี GPU (NVIDIA/AMD) เปิด `scene.cycles.device = "GPU"` จะเร็วขึ้นหลายสิบเท่า และเพิ่ม `--samples 128` ได้

## เวอร์ชัน low-poly (`src/`)
```bash
npm install && npm run render   # ได้ output/clip.mp4
```
