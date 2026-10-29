"""ดาวน์โหลดตัวละคร Microsoft Rocketbox (MIT) แล้วย้อมสีเสื้อผ้าให้ตรงกับคลิปต้นฉบับ
- blue  = Male_Adult_08 : เชิ้ตฟ้า → เชิ้ตน้ำเงินเข้ม, ยีนส์เข้ม → ยีนส์ฟอกสีกลาง, รองเท้าดำ → น้ำตาลส้ม
- white = Male_Adult_16 : เสื้อยืดน้ำเงินลายพิมพ์ → เสื้อยืดขาว (ยีนส์ฟอก + ผ้าใบขาวคงไว้)
ใช้งาน: python3 blender/prep_characters.py
"""
import os
import urllib.request

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "characters")
RAW = "https://raw.githubusercontent.com/microsoft/Microsoft-Rocketbox/master/Assets/Avatars/Adults"
CHARS = {
    "blue": ("Male_Adult_08", "m014", True),
    "white": ("Male_Adult_16", "m019", False),
}


def get(url, dest):
    if not os.path.exists(dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        print("↓", os.path.relpath(dest, ROOT))
        urllib.request.urlretrieve(url.replace(" ", "%20"), dest)


def hsv(a):
    mx, mn = a.max(-1), a.min(-1)
    return mx, np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)


def shade(a, mask, color, lo=0.55, hi=1.25, blur=0):
    """แทนสีบริเวณ mask ด้วย color แต่คงรอยยับ/เงาจากค่าความสว่างเดิม"""
    lum = a @ np.array([0.299, 0.587, 0.114])
    if blur:
        lum = np.asarray(Image.fromarray((lum * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur))) / 255.0
    m = lum[mask].mean()
    k = np.clip(lum / m, lo, hi)[..., None]
    out = a.copy()
    out[mask] = (np.array(color) * k)[mask]
    return out


def recolor_blue(a):
    h, w, _ = a.shape
    yy, xx = np.mgrid[0:h, 0:w] / h
    v, s = hsv(a)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    jeans_box = (yy < 0.43) & ((xx < 0.31) | (xx > 0.69))
    shirt = (b > r + 0.05) & (v > 0.45) & ~jeans_box
    jeans = jeans_box & (v < 0.45)
    shoes = (yy > 0.68) & (v < 0.3) & (v > 0.04) & (s < 0.45) & ~shirt
    a = shade(a, shirt, (0.23, 0.33, 0.5), 0.5, 1.3)
    a = shade(a, jeans, (0.3, 0.38, 0.5), 0.6, 1.45)
    a = shade(a, shoes, (0.36, 0.17, 0.08), 0.5, 1.6)
    return a


def recolor_white(a):
    h, w, _ = a.shape
    yy, xx = np.mgrid[0:h, 0:w] / h
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    jeans_box = (yy < 0.43) & ((xx < 0.31) | (xx > 0.69))
    tee = (b > r + 0.08) & ~jeans_box & ((yy < 0.62) | ((xx > 0.3) & (xx < 0.7)))
    tee = np.asarray(Image.fromarray((tee * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))) > 0
    tee &= (b > r - 0.02)
    return shade(a, tee, (0.9, 0.9, 0.88), 0.72, 1.08, blur=5)


for key, (name, code, opacity) in CHARS.items():
    d = f"{ROOT}/{key}"
    get(f"{RAW}/{name}/Export/{name}.fbx", f"{d}/{name}.fbx")
    maps = ["body_color", "body_normal", "head_color", "head_normal"] + (["opacity_color"] if opacity else [])
    for m in maps:
        get(f"{RAW}/{name}/Textures/{code}_{m}.tga", f"{d}/src_{m}.tga")
        if not os.path.exists(f"{d}/{m}.png") or m == "body_color":
            img = Image.open(f"{d}/src_{m}.tga")
            if m == "body_color":
                a = np.asarray(img.convert("RGB")) / 255.0
                a = recolor_blue(a) if key == "blue" else recolor_white(a)
                img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
            img.save(f"{d}/{m}.png")
print("เสร็จ")
