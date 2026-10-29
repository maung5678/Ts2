"""ฉากสนามบาสหลังบ้านแบบสมจริง เรนเดอร์ด้วย Blender Cycles (path tracing)

ใช้งาน (ต้อง pip install bpy และรัน fetch_assets.py + prep_characters.py ก่อน):
    python3 blender/scene.py                       # เรนเดอร์ทั้งคลิปไปที่ blender/out/frames
    python3 blender/scene.py --still 100           # เรนเดอร์เฟรมเดียว (ไว้ตรวจภาพ)
    python3 blender/scene.py --samples 64 --scale 100
"""
import argparse
import math
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
FPS, DURATION = 30, 5.0
N_FRAMES = int(FPS * DURATION)
CUT = 2.3                      # วินาทีที่ตัดจากช็อตใกล้ไปมุมกว้าง
DROP_T = 0.55                  # ปล่อยลูกหิน
G = 9.81

ap = argparse.ArgumentParser()
ap.add_argument("--still", type=int, default=None)
ap.add_argument("--samples", type=int, default=48)
ap.add_argument("--scale", type=int, default=100, help="เปอร์เซ็นต์ของ 720x1280")
ap.add_argument("--out", default=os.path.join(HERE, "out"))
ap.add_argument("--start", type=int, default=1)
ap.add_argument("--end", type=int, default=N_FRAMES)
ap.add_argument("--preset", choices=["quality", "fast", "eevee"], default="quality",
                help="fast = Cycles ลดแสงสะท้อน/ไม่มี motion blur, eevee = เอนจินเรียลไทม์")
args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])

rng = np.random.default_rng(7)
smooth = lambda x: (lambda c: c * c * (3 - 2 * c))(min(1.0, max(0.0, x)))
lerp = lambda a, b, k: a + (b - a) * k

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection


# ======================================================================
# วัสดุ
# ======================================================================
def nodes_of(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    return nt, nt.nodes, nt.links, nt.nodes["Principled BSDF"]


def img(path, color=True):
    im = bpy.data.images.load(os.path.abspath(path), check_existing=True)
    if not color:
        im.colorspace_settings.name = "Non-Color"
    return im


def pbr(name, tex, scale=1.0, tint=None, tint_mix=0.0, rough_mul=1.0, normal=1.0, random_offset=False):
    """วัสดุ PBR จาก Poly Haven ฉายภาพแบบ box จากพิกัด object (ไม่ต้องพึ่ง UV)"""
    mat = bpy.data.materials.new(name)
    nt, N, L, bsdf = nodes_of(mat)
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / scale,) * 3
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    if random_offset:  # ให้ไม้แต่ละแผ่นลายไม่ซ้ำกัน
        oi = N.new("ShaderNodeObjectInfo")
        mul = N.new("ShaderNodeVectorMath"); mul.operation = "SCALE"; mul.inputs[3].default_value = 37.0
        L.new(oi.outputs["Random"], mul.inputs[0])
        L.new(mul.outputs[0], mp.inputs["Location"])
    d = f"{ASSETS}/textures/{tex}"

    def tex_node(file, color):
        t = N.new("ShaderNodeTexImage")
        t.image = img(f"{d}/{file}", color)
        t.projection = "BOX"; t.projection_blend = 0.25
        L.new(mp.outputs[0], t.inputs[0])
        return t

    diff = tex_node("diff.jpg", True)
    base = diff.outputs[0]
    if tint is not None:
        mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY" if tint_mix == 0 else "MIX"
        mix.inputs["Factor"].default_value = 1.0 if tint_mix == 0 else tint_mix
        L.new(base, mix.inputs[6]); mix.inputs[7].default_value = (*tint, 1)
        base = mix.outputs[2]
    L.new(base, bsdf.inputs["Base Color"])
    if os.path.exists(f"{d}/rough.jpg"):
        r = tex_node("rough.jpg", False)
        m = N.new("ShaderNodeMath"); m.operation = "MULTIPLY"; m.inputs[1].default_value = rough_mul
        L.new(r.outputs[0], m.inputs[0]); L.new(m.outputs[0], bsdf.inputs["Roughness"])
    if os.path.exists(f"{d}/nor.jpg"):
        n = tex_node("nor.jpg", False)
        nm = N.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = normal
        L.new(n.outputs[0], nm.inputs["Color"]); L.new(nm.outputs[0], bsdf.inputs["Normal"])
    return mat


def plain(name, color, rough=0.5, metal=0.0, coat=0.0):
    mat = bpy.data.materials.new(name)
    _, _, _, bsdf = nodes_of(mat)
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Coat Weight"].default_value = coat
    return mat


# ======================================================================
# ตัวช่วยสร้างวัตถุ
# ======================================================================
def finish(obj, mat=None, bevel=0.0, smooth_shade=False):
    if mat:
        obj.data.materials.clear(); obj.data.materials.append(mat)
    if bevel:
        m = obj.modifiers.new("bevel", "BEVEL"); m.width = bevel; m.segments = 2
    if smooth_shade:
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj


def box(name, size, loc, mat=None, bevel=0.004, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    return finish(o, mat, bevel)


def cylinder(name, r, depth, loc, mat=None, verts=32, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=verts)
    o = bpy.context.object; o.name = name
    return finish(o, mat, 0.0, True)


def ribbon(name, pts, width, mat, z=0.003):
    """เส้นสนาม: แถบแบนตามเส้นทาง pts (x, y)"""
    import bmesh
    bm = bmesh.new()
    left, right = [], []
    for i, p in enumerate(pts):
        a = Vector(pts[max(i - 1, 0)]); b = Vector(pts[min(i + 1, len(pts) - 1)])
        t = (b - a).normalized(); n = Vector((-t.y, t.x)) * width / 2
        left.append(bm.verts.new((p[0] + n.x, p[1] + n.y, z)))
        right.append(bm.verts.new((p[0] - n.x, p[1] - n.y, z)))
    for i in range(len(pts) - 1):
        bm.faces.new((left[i], right[i], right[i + 1], left[i + 1]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me)
    o = bpy.data.objects.new(name, me); col.objects.link(o)
    return finish(o, mat)


def import_gltf(path, loc, rot_z=0.0, scale=1.0, tint=None, tint_mix=0.6):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(path))
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(os.path.basename(path), None); col.objects.link(root)
    for o in new:
        if o.parent is None:
            o.parent = root
    root.location = loc; root.rotation_euler.z = rot_z; root.scale = (scale,) * 3
    if tint:
        for o in new:
            for m in getattr(o.data, "materials", []) or []:
                if m and m.use_nodes and not m.get("tinted"):
                    m["tinted"] = 1
                    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
                    link = bsdf and bsdf.inputs["Base Color"].links
                    if link:
                        src = link[0].from_socket
                        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
                        mix.inputs["Factor"].default_value = tint_mix
                        nt.links.new(src, mix.inputs[6]); mix.inputs[7].default_value = (*tint, 1)
                        nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    return root, new


def instance(root, loc, rot_z, scale):
    """สำเนาแบบ linked (ใช้ mesh ร่วมกัน ประหยัดหน่วยความจำ)"""
    new_root = bpy.data.objects.new(root.name + "_inst", None); col.objects.link(new_root)
    for c in root.children:
        o = c.copy(); col.objects.link(o); o.parent = new_root
    new_root.location = loc; new_root.rotation_euler.z = rot_z; new_root.scale = (scale,) * 3
    return new_root


# ======================================================================
# โลก + แสง
# ======================================================================
world = bpy.data.worlds.new("sky"); scene.world = world
world.use_nodes = True
wn, wl = world.node_tree.nodes, world.node_tree.links
env = wn.new("ShaderNodeTexEnvironment")
env.image = img(f"{ASSETS}/hdri/kloofendal_48d_partly_cloudy_puresky.hdr")
wmap = wn.new("ShaderNodeMapping"); wmap.inputs["Rotation"].default_value[2] = math.radians(200)
wl.new(wn.new("ShaderNodeTexCoord").outputs["Generated"], wmap.inputs[0])
wl.new(wmap.outputs[0], env.inputs[0])
wn["Background"].inputs["Strength"].default_value = 0.9
wl.new(env.outputs[0], wn["Background"].inputs[0])

sun_data = bpy.data.lights.new("sun", "SUN")
sun_data.energy = 3.2; sun_data.angle = math.radians(1.5); sun_data.color = (1.0, 0.96, 0.9)
sun = bpy.data.objects.new("sun", sun_data); col.objects.link(sun)
sun.rotation_euler = (math.radians(42), 0, math.radians(-145))

# ======================================================================
# ฉาก
# ======================================================================
M_ASPHALT = pbr("asphalt", "asphalt_02", scale=2.2, tint=(0.82, 0.8, 0.78), normal=0.8)
M_LINE = plain("court_line", (0.85, 0.85, 0.82), 0.6)
M_FENCE = pbr("fence", "fine_grained_wood", scale=1.4, tint=(0.88, 0.74, 0.62), tint_mix=0.8, rough_mul=1.2, random_offset=True)
M_WALL = pbr("wall", "white_plaster_rough_01", scale=2.0, tint=(0.82, 0.74, 0.64))
M_ROOF = pbr("roof", "grey_roof_tiles", scale=2.0, tint=(0.78, 0.7, 0.62), tint_mix=0.7)
M_STONE = pbr("stone", "rock_boulder_dry", scale=0.35, tint=(0.82, 0.8, 0.77), tint_mix=0.35, normal=1.5)
M_POLE = plain("pole_paint", (0.13, 0.26, 0.48), 0.32, 0.55, coat=0.3)
M_BOARD = plain("backboard", (0.92, 0.93, 0.94), 0.25, coat=0.5)
M_BOARD_LINE = plain("board_line", (0.2, 0.42, 0.75), 0.4)
M_RIM = plain("rim", (0.85, 0.22, 0.05), 0.35, 0.6)
M_NET = plain("net", (0.95, 0.95, 0.95), 0.8)

ground = box("ground", (80, 80, 0.02), (0, 0, -0.01), M_ASPHALT, bevel=0)

# เส้นสนาม (พิกัด: แป้นอยู่ทาง +y)
HOOP = Vector((-0.35, 4.2))
arc = [(HOOP.x + 5.6 * math.cos(a), HOOP.y - 0.9 - 5.0 * math.sin(a)) for a in np.linspace(0.08, math.pi - 0.08, 60)]
ribbon("three_point", arc, 0.05, M_LINE)
ribbon("baseline", [(-14, HOOP.y + 0.6), (14, HOOP.y + 0.6)], 0.05, M_LINE)
ribbon("sideline", [(-7.6, HOOP.y + 0.6), (-8.0, -9)], 0.05, M_LINE)

# แป้นบาส
cylinder("pole", 0.075, 3.35, (HOOP.x, HOOP.y + 0.95, 1.675), M_POLE)
box("arm", (0.09, 0.9, 0.09), (HOOP.x, HOOP.y + 0.48, 3.02), M_POLE, rot=(math.radians(-8), 0, 0))
box("backboard", (1.8, 0.05, 1.05), (HOOP.x, HOOP.y, 3.4), M_BOARD, bevel=0.01)
for dx, dz, w, h in [(0, 3.53, 0.59, 0.05), (0, 3.13, 0.59, 0.05), (-0.27, 3.33, 0.05, 0.45), (0.27, 3.33, 0.05, 0.45)]:
    box("board_line", (w, 0.004, h), (HOOP.x + dx, HOOP.y - 0.027, dz), M_BOARD_LINE, bevel=0)
bpy.ops.mesh.primitive_torus_add(major_radius=0.235, minor_radius=0.011, location=(HOOP.x, HOOP.y - 0.27, 3.05))
finish(bpy.context.object, M_RIM, smooth_shade=True)
bpy.ops.mesh.primitive_cone_add(vertices=14, radius1=0.235, radius2=0.15, depth=0.42, end_fill_type="NOTHING",
                                location=(HOOP.x, HOOP.y - 0.27, 2.84))
net = bpy.context.object
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.subdivide(number_cuts=3); bpy.ops.object.mode_set(mode="OBJECT")
wf = net.modifiers.new("wire", "WIREFRAME"); wf.thickness = 0.006
finish(net, M_NET)

# รั้วไม้ + ราว
plank = box("plank", (0.4, 0.035, 2.0), (0, 0, 0), M_FENCE, bevel=0.006)
x = -14.0
while x <= 14.0:
    p = plank.copy(); col.objects.link(p)
    p.location = (x, 6.2, 1.0 + rng.uniform(-0.01, 0.01)); p.rotation_euler.z = rng.uniform(-0.01, 0.01)
    x += 0.42
bpy.data.objects.remove(plank)
for z in (0.45, 1.6):
    box("rail", (28.5, 0.05, 0.1), (0, 6.25, z), M_FENCE)
box("curb", (28.5, 0.5, 0.08), (0, 5.95, 0.04), pbr("curb", "white_plaster_rough_01", 1.5, (0.55, 0.53, 0.5)))


def house(cx, cy, w, d, h, rz=0.0):
    root = bpy.data.objects.new("house", None); col.objects.link(root)
    parts = [box("wall", (w, d, h), (0, 0, h / 2), M_WALL)]
    import bmesh
    bm = bmesh.new()
    hw, hd, rh = w / 2 + 0.35, d / 2 + 0.35, h * 0.5
    v = [bm.verts.new(c) for c in [(-hw, -hd, h), (hw, -hd, h), (0, -hd, h + rh), (-hw, hd, h), (hw, hd, h), (0, hd, h + rh)]]
    for f in [(0, 1, 2), (3, 5, 4), (0, 2, 5, 3), (1, 4, 5, 2), (0, 3, 4, 1)]:
        bm.faces.new([v[i] for i in f])
    me = bpy.data.meshes.new("roof"); bm.to_mesh(me)
    roof = bpy.data.objects.new("roof", me); col.objects.link(roof); finish(roof, M_ROOF)
    sol = roof.modifiers.new("solid", "SOLIDIFY"); sol.thickness = 0.08
    parts.append(roof)
    parts.append(box("chimney", (0.5, 0.5, 1.1), (w * 0.28, 0, h + rh * 0.75), M_WALL))
    for i in range(int(w // 2.2)):  # หน้าต่าง
        parts.append(box("window", (0.9, 0.03, 1.0), (-w / 2 + 1.3 + i * 2.2, -d / 2 - 0.01, h * 0.55),
                         plain("glass", (0.25, 0.3, 0.35), 0.08)))
    for p in parts:
        p.parent = root
    root.location = (cx, cy, 0); root.rotation_euler.z = rz


house(-6.5, 14.5, 8, 6, 3.2, 0.04)
house(5.5, 15.5, 9, 6, 3.4, -0.03)
house(-16, 12.5, 7, 6, 3.0, -0.2)
house(15, 13, 7, 6, 3.0, 0.15)

tree, _ = import_gltf(f"{ASSETS}/models/tree_small_02/tree_small_02.gltf", (-3.2, 9.5, 0), 0.4, 1.6)
for loc, rz, s in [((3.4, 10.0, 0), 1.7, 1.8), ((-9.5, 8.8, 0), 2.6, 1.5), ((9.5, 9.0, 0), 4.0, 1.7), ((14.5, 9.5, 0), 0.8, 1.4)]:
    instance(tree, loc, rz, s)
shrub, _ = import_gltf(f"{ASSETS}/models/shrub_01/shrub_01.gltf", (-1.6, 7.2, 0), 0.0, 1.4)
for loc, rz, s in [((1.8, 7.3, 0), 1.0, 1.2), ((6.5, 7.0, 0), 2.0, 1.5), ((-6.0, 7.1, 0), 3.0, 1.3)]:
    instance(shrub, loc, rz, s)

# ลังไม้ + ที่สูบลม + ลูกหินข้างสนาม
M_CRATE = pbr("crate", "fine_grained_wood", scale=1.0, tint=(0.88, 0.7, 0.64), tint_mix=0.7, rough_mul=1.1, random_offset=True)


def slat_crate(cx, cy, rz, s=0.8, h=0.78):
    """ลังไม้ระแนงสีชมพูอ่อนแบบในคลิป"""
    root = bpy.data.objects.new("crate", None); col.objects.link(root)
    parts = [box("top", (s, s, 0.04), (0, 0, h - 0.02), M_CRATE, 0.006)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(box("post", (0.07, 0.07, h - 0.04), (sx * (s / 2 - 0.035), sy * (s / 2 - 0.035), (h - 0.04) / 2), M_CRATE))
    for i in range(3):
        z = 0.13 + i * 0.22
        for sy in (-1, 1):
            parts.append(box("slat", (s - 0.02, 0.025, 0.17), (0, sy * (s / 2 - 0.0125), z), M_CRATE))
        for sx in (-1, 1):
            parts.append(box("slat", (0.025, s - 0.02, 0.17), (sx * (s / 2 - 0.0125), 0, z), M_CRATE))
    for pt in parts:
        pt.parent = root
    root.location = (cx, cy, 0); root.rotation_euler.z = rz


slat_crate(-0.1, -0.3, 0.1)


def rock_sphere(name, r, loc, detail=5, amount=0.06, mat=None):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=detail, radius=r, location=loc)
    o = bpy.context.object; o.name = name
    tx = bpy.data.textures.new(name + "_n", "CLOUDS"); tx.noise_scale = 0.35; tx.noise_depth = 3
    d = o.modifiers.new("disp", "DISPLACE"); d.texture = tx; d.strength = r * amount; d.mid_level = 0.5
    d.texture_coords = "OBJECT"
    return finish(o, mat or M_STONE, smooth_shade=detail > 2)


STONE_R = 0.17
stone = rock_sphere("stone_ball", STONE_R, (0, 0, 1))
rock_sphere("stone_ball_side", STONE_R, (-1.75, -0.75, STONE_R - 0.02))

M_PEBBLE = pbr("pebble", "rock_boulder_dry", scale=0.2, tint=(0.5, 0.48, 0.45), tint_mix=0.45)
pebbles = []
for i in range(30):
    r = rng.uniform(0.008, 0.028)
    p = rock_sphere(f"pebble{i}", r, (0, 0, -1), detail=1, amount=0.9, mat=M_PEBBLE)
    p.scale = (1, rng.uniform(0.6, 1), rng.uniform(0.5, 0.9))
    a, sp = rng.uniform(0, 2 * math.pi), rng.uniform(0.3, 1.2)
    pebbles.append(dict(o=p, r=r, vx=math.cos(a) * sp, vy=math.sin(a) * sp, vz=rng.uniform(0.8, 2.2), spin=rng.uniform(5, 25)))


# ลูกบาส: วาดตะเข็บลง texture แบบ equirect บน UV sphere + bump เม็ดยาง
def basketball_tex(w=1024, h=512):
    u, v = np.meshgrid((np.arange(w) + 0.5) / w, (np.arange(h) + 0.5) / h)
    th, ph = u * 2 * math.pi, v * math.pi
    x, y, z = np.cos(th) * np.sin(ph), np.sin(th) * np.sin(ph), -np.cos(ph)
    wdt = 0.018
    seam = (np.abs(x) < wdt) | (np.abs(z) < wdt) | (np.abs(np.abs(y) - (0.62 + 0.3 * (x * x - z * z))) < wdt)
    rgb = np.where(seam[..., None], [0.02, 0.015, 0.012], [0.62, 0.17, 0.035])
    a = np.concatenate([rgb, np.ones((h, w, 1))], -1).astype(np.float32)
    im = bpy.data.images.new("basketball", w, h, float_buffer=True)
    im.pixels.foreach_set(a.ravel())
    return im


M_BALL = bpy.data.materials.new("basketball")
nt, N, L, bsdf = nodes_of(M_BALL)
t = N.new("ShaderNodeTexImage"); t.image = basketball_tex()
L.new(t.outputs[0], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.62
vor = N.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 900
bump = N.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25; bump.inputs["Distance"].default_value = 0.0006
L.new(vor.outputs["Distance"], bump.inputs["Height"]); L.new(bump.outputs[0], bsdf.inputs["Normal"])
BALL_R = 0.12
bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=BALL_R, location=(0, 0, -1))
ball = finish(bpy.context.object, M_BALL, smooth_shade=True); ball.name = "basketball"


# ======================================================================
# ตัวละคร + ระบบจัดท่า (IK แบบสองท่อน + หมุนกระดูกในพิกัดโลก)
# ======================================================================
class Person:
    def __init__(self, key, pos, yaw):
        d = f"{ASSETS}/characters/{key}"
        fbx = [f for f in os.listdir(d) if f.endswith(".fbx")][0]
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=f"{d}/{fbx}")
        new = [o for o in bpy.data.objects if o not in before]
        self.arm = next(o for o in new if o.type == "ARMATURE")
        self.meshes = [o for o in new if o.type == "MESH"]
        for o in new:
            if o.type == "EMPTY":
                o.hide_render = True
        self._materials(d, key)
        self.base = self.arm.matrix_world.copy()
        self.pos, self.yaw = Vector(pos), yaw
        self.pb = self.arm.pose.bones
        for b in self.pb:
            b.rotation_mode = "QUATERNION"
        self.place(pos, yaw)
        bpy.context.view_layer.update()
        self.rest = {b.name: (self.arm.matrix_world @ b.head) for b in self.pb}

    def _materials(self, d, key):
        for o in self.meshes:
            for i, m in enumerate(o.data.materials):
                part = "head" if "head" in m.name else "opacity" if "opacity" in m.name else "body"
                nm = bpy.data.materials.new(f"{key}_{part}")
                nt, N, L, bsdf = nodes_of(nm)
                uv = N.new("ShaderNodeUVMap")
                if part == "opacity":
                    tx = N.new("ShaderNodeTexImage"); tx.image = img(f"{d}/opacity_color.png")
                    L.new(tx.outputs["Color"], bsdf.inputs["Base Color"]); L.new(tx.outputs["Alpha"], bsdf.inputs["Alpha"])
                    bsdf.inputs["Roughness"].default_value = 0.6
                else:
                    tx = N.new("ShaderNodeTexImage"); tx.image = img(f"{d}/{part}_color.png")
                    L.new(tx.outputs[0], bsdf.inputs["Base Color"])
                    nx = N.new("ShaderNodeTexImage"); nx.image = img(f"{d}/{part}_normal.png", False)
                    nmap = N.new("ShaderNodeNormalMap"); nmap.inputs["Strength"].default_value = 0.9
                    L.new(nx.outputs[0], nmap.inputs["Color"]); L.new(nmap.outputs[0], bsdf.inputs["Normal"])
                    bsdf.inputs["Roughness"].default_value = 0.55 if part == "head" else 0.85
                    if part == "head":  # ผิวโปร่งแสง (subsurface) ให้ดูเป็นผิวคนจริง
                        bsdf.inputs["Subsurface Weight"].default_value = 0.15
                        bsdf.inputs["Subsurface Radius"].default_value = (0.012, 0.005, 0.003)
                        bsdf.inputs["Subsurface Scale"].default_value = 1.0
                o.data.materials[i] = nm
            for p in o.data.polygons:
                p.use_smooth = True

    # ---- พิกัดของตัวละคร: r = ขวา, f = หน้า, u = ขึ้น ----
    def place(self, pos, yaw):
        self.pos, self.yaw = Vector(pos), yaw
        self.arm.matrix_world = Matrix.Translation(self.pos) @ Matrix.Rotation(yaw, 4, "Z") @ self.base

    def C(self, r, f, u):
        return Matrix.Rotation(self.yaw, 3, "Z") @ Vector((-r, -f, u))

    def P(self, r, f, u):
        return self.pos + self.C(r, f, u)

    def head(self, name):
        return self.arm.matrix_world @ self.pb[name].head

    def world(self, name):
        return self.arm.matrix_world @ self.pb[name].matrix

    def set_world(self, name, M):
        self.pb[name].matrix = self.arm.matrix_world.inverted() @ M
        bpy.context.view_layer.update()

    def rotate(self, name, axis_world, angle):
        h = self.head(name)
        R = Matrix.Translation(h) @ Matrix.Rotation(angle, 4, axis_world) @ Matrix.Translation(-h)
        self.set_world(name, R @ self.world(name))

    def rot_local(self, name, axis_rfu, angle):
        self.rotate(name, self.C(*axis_rfu).normalized(), angle)

    def aim(self, name, child, direction):
        v = self.head(child) - self.head(name)
        q = v.normalized().rotation_difference(direction.normalized())
        h = self.head(name)
        R = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h)
        self.set_world(name, R @ self.world(name))

    def reset(self):
        for b in self.pb:
            b.matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()

    def ik(self, upper, lower, end, target, pole):
        a = self.head(upper)
        l1 = (self.rest[lower] - self.rest[upper]).length
        l2 = (self.rest[end] - self.rest[lower]).length
        d = target - a
        dist = min(max(d.length, 1e-3), (l1 + l2) * 0.999)
        dn = d.normalized()
        cos_a = (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist)
        sin_a = math.sqrt(max(0.0, 1 - cos_a * cos_a))
        pp = (pole - pole.project(dn)).normalized()
        knee = a + dn * (l1 * cos_a) + pp * (l1 * sin_a)
        self.aim(upper, lower, knee - a)
        self.aim(lower, end, a + dn * dist - knee)

    def pelvis_to(self, r, f, u):
        M = self.world("Bip01 Pelvis")
        M.translation = self.P(r, f, u)
        self.set_world("Bip01 Pelvis", M)

    def legs(self, stance=0.12, toe_out=0.25, knee_out=0.25, front=(0.0, 0.0)):
        for side, s in (("L", -1), ("R", 1)):
            fwd = front[0] if side == "L" else front[1]
            ankle = self.P(s * stance, fwd, 0.1)
            self.ik(f"Bip01 {side} Thigh", f"Bip01 {side} Calf", f"Bip01 {side} Foot", ankle,
                    self.C(s * knee_out, 1, 0))
            self.aim(f"Bip01 {side} Foot", f"Bip01 {side} Toe0", self.C(s * toe_out, 1, -0.55))

    def arm_to(self, side, target, pole, hand_dir=None):
        self.ik(f"Bip01 {side} UpperArm", f"Bip01 {side} Forearm", f"Bip01 {side} Hand", target, pole)
        if hand_dir is not None:
            self.aim(f"Bip01 {side} Hand", f"Bip01 {side} Finger2", hand_dir)

    def fingers(self, side, curl):
        hand = f"Bip01 {side} Hand"
        across = (self.head(f"Bip01 {side} Finger1") - self.head(f"Bip01 {side} Finger4")).normalized()
        sign = -1 if side == "L" else 1
        for f in "1234":
            for seg, k in (("", 0.8), ("1", 1.0), ("2", 0.8)):
                name = f"Bip01 {side} Finger{f}{seg}"
                if name in self.pb:
                    self.rotate(name, across, sign * curl * k)
        if f"Bip01 {side} Finger0" in self.pb:
            self.rotate(f"Bip01 {side} Finger01", across, sign * curl * 0.4)


blue = Person("blue", (0.78, -0.5, 0), -0.45)
white = Person("white", (-1.0, 0.05, 0), 0.95)
import_gltf(f"{ASSETS}/models/tire_pump/tire_pump.gltf", white.P(0.34, 0.16, 0), 0.95, 1.9)  # สูง ~1.1 ม.


def key_pose(person, frame):
    for b in person.pb:
        b.keyframe_insert("rotation_quaternion", frame=frame)
        b.keyframe_insert("location", frame=frame)


# ======================================================================
# Timeline
# ======================================================================
IMPACT_T = DROP_T + math.sqrt(2 * (1.0 - STONE_R) / G)
DRIBBLE_HZ = 2.2


def ball_height(t):
    ph = ((t - CUT) * DRIBBLE_HZ) % 1.0          # 0 = บนสุด, 0.5 = กระทบพื้น
    u = abs(ph - 0.5) * 2
    return BALL_R + (0.8 - BALL_R) * (1 - (1 - u) ** 2), ph


def pose_blue(t):
    p = blue
    p.reset()
    if t < CUT:
        k = smooth((t - DROP_T + 0.15) / 0.5)          # ปล่อยลูก
        sur = smooth((t - IMPACT_T) / 0.3)              # ตกใจหลังลูกกระแทก
        p.pelvis_to(0, -0.05 - 0.03 * k, 0.86 - 0.05 * k)
        p.legs(stance=0.17, knee_out=0.3, front=(0.03, -0.05))
        p.rot_local("Bip01 Spine1", (1, 0, 0), -(0.12 + 0.1 * k))
        p.rot_local("Bip01 Spine2", (1, 0, 0), -(0.1 + 0.08 * k))
        look = smooth((t - DROP_T) / 0.35)
        p.rot_local("Bip01 Neck", (1, 0, 0), -(0.15 + 0.25 * look))
        p.rot_local("Bip01 Head", (1, 0, 0), -(0.1 + 0.25 * look))
        for side, s in (("L", -1), ("R", 1)):
            hold = p.P(s * 0.19 - 0.05, 0.42, 0.98)
            open_ = p.P(s * (0.29 + 0.04 * sur), 0.16, 0.9 + 0.04 * sur)
            tgt = hold.lerp(open_, k)
            p.arm_to(side, tgt, p.C(s * 1, -0.6, -0.6), p.C(s * lerp(-0.6, 0.3, k), 0.6, -0.4))
            p.fingers(side, lerp(0.5, 0.15, k))
    else:
        h, ph = ball_height(t)
        bob = 0.015 * math.cos(ph * 2 * math.pi)
        p.pelvis_to(0, -0.1, 0.78 + bob)
        p.legs(stance=0.24, knee_out=0.35, toe_out=0.35, front=(0.12, -0.1))
        p.rot_local("Bip01 Spine1", (1, 0, 0), -0.3)
        p.rot_local("Bip01 Spine2", (1, 0, 0), -0.15)
        p.rot_local("Bip01 Spine1", (0, 0, 1), 0.12)
        p.rot_local("Bip01 Neck", (1, 0, 0), -0.25)
        p.rot_local("Bip01 Head", (1, 0, 0), -0.3)
        ball_pos = p.P(0.33, 0.45, h)
        hand = ball_pos + Vector((0, 0, BALL_R + 0.03))
        hand.z = max(hand.z, 0.68 + 0.05 * math.cos(ph * 2 * math.pi))
        p.arm_to("R", hand, p.C(1, -0.5, -0.4), p.C(0.05, 0.7, -0.7))
        p.fingers("R", 0.25)
        p.arm_to("L", p.P(-0.38, 0.32, 0.95), p.C(-1, -0.3, -0.5), p.C(-0.3, 1, -0.2))
        p.fingers("L", 0.35)


def pose_white(t):
    p = white
    p.reset()
    p.pelvis_to(0, 0, 0.885)
    p.legs(stance=0.13, knee_out=0.15, toe_out=0.2, front=(0.05, -0.04))
    p.rot_local("Bip01 Spine1", (0, 0, 1), 0.04 * math.sin(t * 2))
    p.rot_local("Bip01 Head", (0, 0, 1), 0.15)
    # มือขวาวางบนด้ามที่สูบลม
    p.arm_to("R", p.P(0.33, 0.16, 1.12), p.C(1, -1, -0.6), p.C(0.1, 0.4, -1))
    p.fingers("R", 0.6)
    k = smooth((t - CUT - 0.2) / 0.45) if t > CUT else 0.0
    rest = p.P(-0.24, 0.05, 0.85)
    shoulder = p.head("Bip01 L UpperArm")
    to_ball = (blue.P(0.33, 0.45, 0.6) - shoulder).normalized()
    point = shoulder + to_ball * 0.56 + Vector((0, 0, 0.06 + 0.015 * math.sin(t * 10)))
    p.arm_to("L", rest.lerp(point, k), p.C(-1, -0.5, -0.6), p.C(-0.2, 0.2, -1).lerp(to_ball, k))
    p.fingers("L", lerp(0.3, 0.1, k))
    p.rot_local("Bip01 Head", (0, 0, 1), 0.2 * k)


def animate():
    for f in range(1, N_FRAMES + 1):
        t = (f - 1) / FPS
        scene.frame_set(f)
        pose_blue(t); key_pose(blue, f)
        pose_white(t); key_pose(white, f)
        # ลูกหิน
        start = blue.P(-0.05, 0.42, 0.98)
        if t < CUT:
            if t < DROP_T:
                z = start.z
            else:
                z = max(STONE_R - 0.03, start.z - 0.5 * G * (t - DROP_T) ** 2)
            stone.location = (start.x, start.y, z)
            stone.rotation_euler = (0.3, 0.1 * t, 0)
        else:
            stone.location = (start.x - 0.05, start.y + 0.05, STONE_R - 0.03)
            stone.hide_render = True
        stone.keyframe_insert("location", frame=f); stone.keyframe_insert("rotation_euler", frame=f)
        stone.keyframe_insert("hide_render", frame=f)
        stone.hide_render = False
        # เศษหิน (บอลลิสติก + กระดอนลดทอน)
        it = t - IMPACT_T
        for pb_ in pebbles:
            o = pb_["o"]
            if it <= 0 or t >= CUT:
                o.location = (0, 0, -1)
            else:
                vz, z0, tt, z = pb_["vz"], 0.05, it, 0.0
                for _ in range(4):
                    land = (vz + math.sqrt(vz * vz + 2 * G * z0)) / G
                    if tt < land:
                        z = z0 + vz * tt - 0.5 * G * tt * tt
                        break
                    tt -= land; vz *= 0.3; z0 = 0.0
                drag = 1 - 0.5 * smooth(it / 1.2)
                o.location = (stone.location.x + pb_["vx"] * it * drag, stone.location.y + pb_["vy"] * it * drag,
                              max(pb_["r"] * 0.6, z + pb_["r"] * 0.6))
                o.rotation_euler = (it * pb_["spin"], it * pb_["spin"] * 0.6, 0)
            o.keyframe_insert("location", frame=f); o.keyframe_insert("rotation_euler", frame=f)
        # ลูกบาส
        if t < CUT:
            ball.location = (0, 0, -1)
        else:
            h, ph = ball_height(t)
            ball.location = blue.P(0.33, 0.45, h)
            sq = 1 - 0.16 * max(0.0, 1 - abs(ph - 0.5) / 0.035)
            ball.scale = (1 / math.sqrt(sq), 1 / math.sqrt(sq), sq)
            ball.rotation_euler = (-t * 14, 0.3, 0.2)
        for prop in ("location", "scale", "rotation_euler"):
            ball.keyframe_insert(prop, frame=f)
        camera_at(t); cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_euler", frame=f)
        cam_data.keyframe_insert("lens", frame=f); cam_data.dof.keyframe_insert("focus_distance", frame=f)
    # ช็อตตัด: ให้ทุก key เป็นแบบ constant ที่จุดตัด จะได้ไม่มี motion blur ข้ามช็อต
    for o in [cam, cam_data, ball, stone] + [p["o"] for p in pebbles]:
        ad = o.animation_data
        if ad and ad.action:
            for fc in getattr(ad.action, "fcurves", []):
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"


# ======================================================================
# กล้อง
# ======================================================================
cam_data = bpy.data.cameras.new("cam")
cam_data.sensor_fit = "VERTICAL"; cam_data.sensor_height = 24
cam_data.dof.use_dof = True; cam_data.dof.aperture_fstop = 4.0
cam = bpy.data.objects.new("cam", cam_data); col.objects.link(cam); scene.camera = cam


def look(pos, target, fov_v):
    cam.location = pos
    cam.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    cam_data.lens = 12 / math.tan(math.radians(fov_v) / 2)


def camera_at(t):
    if t < CUT:
        k = t / CUT
        tgt = Vector((0.68, -0.35, 0.8))
        pos = Vector((lerp(0.5, 0.54, k), lerp(-3.3, -3.0, k), lerp(1.7, 1.65, k)))
        it = t - IMPACT_T
        if 0 < it < 0.35:  # กล้องสั่นตอนลูกหินกระแทก
            a = (1 - it / 0.35) * 0.012
            pos += Vector((math.sin(it * 90) * a, 0, math.cos(it * 77) * a))
        look(pos, tgt, 50)
        cam_data.dof.focus_distance = (blue.pos - pos).length - 0.3
    else:
        k = (t - CUT) / (DURATION - CUT)
        pos = Vector((lerp(0.0, 0.05, k), lerp(-4.0, -3.8, k), lerp(1.35, 1.32, k)))
        look(pos, (-0.05, 1.0, 1.02), 62)
        cam_data.dof.focus_distance = (blue.pos - pos).length


# ======================================================================
# ตั้งค่าการเรนเดอร์
# ======================================================================
r = scene.render
r.engine = "CYCLES"
r.resolution_x, r.resolution_y, r.resolution_percentage = 720, 1280, args.scale
r.fps = FPS
r.use_motion_blur = True; r.motion_blur_shutter = 0.5
r.image_settings.file_format = "PNG"
r.film_transparent = False
cy = scene.cycles
cy.device = "CPU"
cy.samples = args.samples
cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.03
cy.use_denoising = True; cy.denoiser = "OPENIMAGEDENOISE"
cy.max_bounces = 6; cy.diffuse_bounces = 3; cy.glossy_bounces = 3; cy.transmission_bounces = 4
cy.caustics_reflective = cy.caustics_refractive = False
cy.blur_glossy = 1.0
r.use_persistent_data = True
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = 0.15
scene.frame_start, scene.frame_end = 1, N_FRAMES

t0 = time.time()
animate()
print(f"animation baked in {time.time() - t0:.1f}s", flush=True)

os.makedirs(f"{args.out}/frames", exist_ok=True)
if args.preset == "fast":
    cy.max_bounces = 3; cy.diffuse_bounces = 1; cy.glossy_bounces = 1; cy.transmission_bounces = 2
    cy.adaptive_threshold = 0.1; cy.light_sampling_threshold = 0.05
    cy.denoising_prefilter = "FAST"; cy.denoising_quality = "FAST"
    r.use_motion_blur = False; cam_data.dof.use_dof = False
    r.use_simplify = True; r.simplify_subdivision_render = 0; cy.texture_limit_render = "1024"
elif args.preset == "eevee":
    r.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = args.samples
    r.use_motion_blur = False

frames = [args.still] if args.still else range(args.start, args.end + 1)
for f in frames:
    t0 = time.time()
    scene.frame_set(f)
    r.filepath = f"{args.out}/frames/{f:04d}.png" if not args.still else f"{args.out}/still_{f:04d}.png"
    bpy.ops.render.render(write_still=True)
    print(f"frame {f} rendered in {time.time() - t0:.1f}s", flush=True)
