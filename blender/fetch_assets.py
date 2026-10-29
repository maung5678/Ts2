"""ดาวน์โหลด asset CC0 จาก Poly Haven (texture, HDRI, โมเดล) และโมเดลคนจากตัวอย่างของ three.js
ใช้งาน: python3 blender/fetch_assets.py
"""
import json
import os
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
API = "https://api.polyhaven.com/files/"
UA = {"User-Agent": "oddtilt-clip-fetcher/1.0"}

TEXTURES = {  # ชื่อ Poly Haven -> ความละเอียด
    "asphalt_02": "2k", "weathered_planks": "1k", "denim_fabric": "1k", "cotton_jersey": "1k",
    "rock_boulder_dry": "1k", "white_plaster_rough_01": "1k", "grey_roof_tiles": "1k",
    "fine_grained_wood": "1k", "brown_leather": "1k",
}
MODELS = ["tire_pump", "wooden_crate_01", "shrub_01", "shrub_02", "tree_small_02", "jacaranda_tree"]
HDRI = ("kloofendal_48d_partly_cloudy_puresky", "2k")
HUMAN = "https://cdn.jsdelivr.net/gh/mrdoob/three.js@r170/examples/models/gltf/readyplayer.me.glb"


def get(url, dest):
    if os.path.exists(dest):
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print("↓", os.path.relpath(dest, ROOT))
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA)) as r, open(dest, "wb") as f:
        f.write(r.read())


def files(asset):
    with urllib.request.urlopen(urllib.request.Request(API + asset, headers=UA)) as r:
        return json.load(r)


for name, res in TEXTURES.items():
    f = files(name)
    for key, short in (("Diffuse", "diff"), ("nor_gl", "nor"), ("Rough", "rough")):
        if key in f:
            get(f[key][res]["jpg"]["url"], f"{ROOT}/textures/{name}/{short}.jpg")

for name in MODELS:
    g = files(name)["gltf"]["1k"]["gltf"]
    get(g["url"], f"{ROOT}/models/{name}/{name}.gltf")
    for rel, inc in g["include"].items():
        get(inc["url"], f"{ROOT}/models/{name}/{rel}")

h = files(HDRI[0])["hdri"][HDRI[1]]["hdr"]["url"]
get(h, f"{ROOT}/hdri/{HDRI[0]}.hdr")
get(HUMAN, f"{ROOT}/models/human/readyplayer.me.glb")
print("เสร็จ")
