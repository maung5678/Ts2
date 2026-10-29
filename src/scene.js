// ฉากสนามบาสเกตบอลหลังบ้าน (สไตล์ "theoddtilt") สร้างด้วย Three.js
// ฟังก์ชัน window.renderAt(t) วาดเฟรมที่เวลา t (วินาที) แบบ deterministic
// เพื่อให้สคริปต์ render.mjs จับภาพทีละเฟรมแล้วรวมเป็นวิดีโอ 5 วินาที
import * as THREE from 'three';

const W = 720, H = 1280, DURATION = 5;

// ---------- สุ่มแบบกำหนด seed (ทุกครั้งที่ render ได้ผลเหมือนเดิม) ----------
let seed = 1337;
const rand = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
const lerp = (a, b, k) => a + (b - a) * k;
const clamp01 = (x) => Math.min(1, Math.max(0, x));
const smooth = (x) => { x = clamp01(x); return x * x * (3 - 2 * x); };

// ---------- Renderer ----------
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W, H);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.getElementById('stage').prepend(renderer.domElement);

const scene = new THREE.Scene();
scene.fog = new THREE.Fog(0xb9c9dc, 25, 70);
const camera = new THREE.PerspectiveCamera(50, W / H, 0.05, 200);

// ท้องฟ้าไล่สี (น้ำเงินด้านบน → ฟ้าอ่อนที่ขอบฟ้า เหมือนในคลิป)
{
  const c = document.createElement('canvas'); c.width = 4; c.height = 256;
  const g = c.getContext('2d');
  const gr = g.createLinearGradient(0, 0, 0, 256);
  gr.addColorStop(0, '#3f6fa8'); gr.addColorStop(0.55, '#7d9fc6'); gr.addColorStop(1, '#c4d3e2');
  g.fillStyle = gr; g.fillRect(0, 0, 4, 256);
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
  scene.background = tex;
}

// ---------- แสง ----------
scene.add(new THREE.HemisphereLight(0xdfe9ff, 0x6b6560, 1.25));
const sun = new THREE.DirectionalLight(0xfff3e2, 2.4);
sun.position.set(6, 12, 8);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -9, right: 9, top: 9, bottom: -9, near: 1, far: 40 });
sun.shadow.bias = -0.0004;
sun.shadow.radius = 4;
scene.add(sun);

// ---------- Texture ที่วาดด้วย canvas ----------
function canvasTex(size, draw, repeat = 1) {
  const c = document.createElement('canvas'); c.width = c.height = size;
  draw(c.getContext('2d'), size);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(repeat, repeat);
  t.anisotropy = 8;
  return t;
}
function speckle(g, s, base, n, colors, rMax = 1.5) {
  g.fillStyle = base; g.fillRect(0, 0, s, s);
  for (let i = 0; i < n; i++) {
    g.fillStyle = colors[(rand() * colors.length) | 0];
    g.globalAlpha = 0.25 + rand() * 0.5;
    g.beginPath(); g.arc(rand() * s, rand() * s, rand() * rMax + 0.3, 0, 7); g.fill();
  }
  g.globalAlpha = 1;
}
const asphaltTex = canvasTex(512, (g, s) =>
  speckle(g, s, '#5a5856', 14000, ['#3e3c3b', '#77736f', '#4b4947', '#8a8580']), 10);
const jeansTex = canvasTex(256, (g, s) => {
  g.fillStyle = '#8197b8'; g.fillRect(0, 0, s, s);
  for (let i = 0; i < 2600; i++) {
    g.fillStyle = rand() < 0.5 ? '#a9bad3' : '#5c7092';
    g.globalAlpha = 0.35; g.fillRect(rand() * s, rand() * s, 1, 4 + rand() * 10);
  }
  g.globalAlpha = 1;
}, 2);
const woodTex = canvasTex(256, (g, s) => {
  g.fillStyle = '#e3c8ae'; g.fillRect(0, 0, s, s);
  for (let i = 0; i < 90; i++) {
    g.strokeStyle = rand() < 0.5 ? '#d2b598' : '#efd9c4';
    g.globalAlpha = 0.5; g.lineWidth = 1 + rand() * 2;
    const x = rand() * s; g.beginPath(); g.moveTo(x, 0); g.lineTo(x + rand() * 6 - 3, s); g.stroke();
  }
  g.globalAlpha = 1;
});
const stoneTex = canvasTex(256, (g, s) =>
  speckle(g, s, '#a8a6a2', 5000, ['#d8d6d2', '#7f7c78', '#bdbab5', '#6a6763'], 3));
const ballTex = canvasTex(512, (g, s) => {
  speckle(g, s, '#d9661f', 6000, ['#e87a2c', '#b8501a', '#f08a3a'], 1.2);
  g.strokeStyle = '#2a160c'; g.lineWidth = 7;
  g.beginPath(); g.moveTo(0, s / 2); g.lineTo(s, s / 2); g.stroke();
  [s * 0.25, s * 0.75].forEach((x) => { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, s); g.stroke(); });
  g.beginPath(); g.ellipse(s / 2, s / 2, s * 0.14, s * 0.5, 0, 0, 7); g.stroke();
  g.beginPath(); g.ellipse(0, s / 2, s * 0.14, s * 0.5, 0, 0, 7); g.stroke();
  g.beginPath(); g.ellipse(s, s / 2, s * 0.14, s * 0.5, 0, 0, 7); g.stroke();
});
ballTex.wrapS = ballTex.wrapT = THREE.ClampToEdgeWrapping; ballTex.repeat.set(1, 1);

const mat = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.85, ...o });
function mesh(geo, material, parent, x = 0, y = 0, z = 0) {
  const m = new THREE.Mesh(geo, material);
  m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true;
  if (parent) parent.add(m);
  return m;
}

// ---------- พื้นสนาม + เส้น ----------
const ground = mesh(new THREE.PlaneGeometry(80, 80), mat(0xffffff, { map: asphaltTex, roughness: 0.95 }), scene);
ground.rotation.x = -Math.PI / 2; ground.castShadow = false;
const lineMat = new THREE.MeshBasicMaterial({ color: 0xe9e9e6 });
function courtLine(points) {
  const curve = new THREE.CatmullRomCurve3(points.map((p) => new THREE.Vector3(p[0], 0.006, p[1])));
  const geo = new THREE.TubeGeometry(curve, 80, 0.035, 3, false);
  geo.scale(1, 0.05, 1);
  const m = new THREE.Mesh(geo, lineMat); m.receiveShadow = true; scene.add(m);
}
const HOOP_Z = -4.2;
{ // เส้นโค้งสามแต้ม + เส้นข้าง/เส้นหลัง
  const arc = []; for (let i = 0; i <= 40; i++) {
    const a = Math.PI * (i / 40);
    arc.push([Math.cos(a) * 5.6, HOOP_Z + 0.9 + Math.sin(a) * 5.0]);
  }
  courtLine(arc);
  courtLine([[-12, HOOP_Z - 0.6], [0, HOOP_Z - 0.6], [12, HOOP_Z - 0.6]]);
  courtLine([[-7.5, HOOP_Z - 0.6], [-7.8, 2], [-8.2, 9]]);
}

// ---------- แป้นบาส ----------
{
  const hoop = new THREE.Group(); hoop.position.set(-0.35, 0, HOOP_Z); scene.add(hoop);
  const poleMat = mat(0x4f78a8, { metalness: 0.5, roughness: 0.4 });
  mesh(new THREE.CylinderGeometry(0.075, 0.085, 3.4, 20), poleMat, hoop, 0, 1.7, -0.9);
  const arm = mesh(new THREE.BoxGeometry(0.1, 0.1, 0.85), poleMat, hoop, 0, 3.0, -0.45);
  arm.rotation.x = 0.12;
  mesh(new THREE.BoxGeometry(1.8, 1.08, 0.05), mat(0xf4f5f6, { roughness: 0.5 }), hoop, 0, 3.4, 0);
  const sq = new THREE.MeshBasicMaterial({ color: 0x5f8fc8 });
  [[0, 3.53, 0.6, 0.04], [0, 3.13, 0.6, 0.04], [-0.29, 3.33, 0.04, 0.44], [0.29, 3.33, 0.04, 0.44]]
    .forEach(([x, y, w, h]) => mesh(new THREE.PlaneGeometry(w, h), sq, hoop, x, y, 0.027));
  const rim = mesh(new THREE.TorusGeometry(0.23, 0.014, 8, 40), mat(0xe0521f, { metalness: 0.4, roughness: 0.4 }), hoop, 0, 3.05, 0.27);
  rim.rotation.x = Math.PI / 2;
  // ตาข่าย: เส้นแนวตั้งที่ไขว้กัน
  const pts = [];
  for (let i = 0; i < 16; i++) {
    const a0 = (i / 16) * Math.PI * 2, a1 = a0 + Math.PI / 8;
    for (const [a, b] of [[a0, a1], [a1, a0]]) {
      pts.push(new THREE.Vector3(Math.cos(a) * 0.23, 3.05, 0.27 + Math.sin(a) * 0.23));
      pts.push(new THREE.Vector3(Math.cos(b) * 0.15, 2.62, 0.27 + Math.sin(b) * 0.15));
    }
  }
  hoop.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(pts),
    new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.85 })));
}

// ---------- รั้วไม้ ----------
{
  const plankMat = mat(0xffffff, { map: woodTex });
  const plankGeo = new THREE.BoxGeometry(0.42, 2.1, 0.05);
  for (let x = -14; x <= 14; x += 0.46) {
    const h = 2.1 + (rand() - 0.5) * 0.04;
    const p = mesh(plankGeo, plankMat, scene, x, h / 2, -6.2);
    p.rotation.y = (rand() - 0.5) * 0.02;
  }
  const rail = new THREE.BoxGeometry(28.5, 0.1, 0.06);
  mesh(rail, plankMat, scene, 0, 0.5, -6.25); mesh(rail, plankMat, scene, 0, 1.6, -6.25);
  const curb = mesh(new THREE.BoxGeometry(28.5, 0.08, 0.6), mat(0x8c8782), scene, 0, 0.04, -5.9);
  curb.castShadow = false;
}

// ---------- บ้าน + ต้นไม้ด้านหลัง ----------
function house(x, z, w, d, h, ry = 0) {
  const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry; scene.add(g);
  const wallM = mat(0xd9c7b2), roofM = mat(0xcbb8a3);
  mesh(new THREE.BoxGeometry(w, h, d), wallM, g, 0, h / 2, 0);
  const shape = new THREE.Shape([new THREE.Vector2(-w / 2 - 0.4, 0), new THREE.Vector2(w / 2 + 0.4, 0), new THREE.Vector2(0, h * 0.55)]);
  const roof = mesh(new THREE.ExtrudeGeometry(shape, { depth: d + 0.6, bevelEnabled: false }), roofM, g, 0, h, -d / 2 - 0.3);
  roof.castShadow = false;
  mesh(new THREE.BoxGeometry(0.5, 1.2, 0.5), roofM, g, w * 0.3, h + h * 0.4, 0);
}
house(-6.5, -14, 8, 6, 3.2, 0.05);
house(5.5, -15, 9, 6, 3.4, -0.03);
house(-15, -12, 7, 6, 3.0, 0.2);
{
  const brick = canvasTex(256, (g, s) => {
    g.fillStyle = '#8a3f2c'; g.fillRect(0, 0, s, s);
    g.fillStyle = '#c9b7a6';
    for (let y = 0; y < s; y += 16) { g.fillRect(0, y, s, 2); for (let x = (y / 16) % 2 ? 16 : 0; x < s; x += 32) g.fillRect(x, y, 2, 16); }
  }, 3);
  mesh(new THREE.BoxGeometry(4, 4, 4), mat(0xffffff, { map: brick }), scene, -10, 2, -8.5);
}
function tree(x, z, s) {
  const g = new THREE.Group(); g.position.set(x, 0, z); scene.add(g);
  mesh(new THREE.CylinderGeometry(0.08 * s, 0.12 * s, 2.2 * s, 8), mat(0x6b4f3a), g, 0, 1.1 * s, 0);
  const leaf = mat(0x6f8a4a);
  for (let i = 0; i < 9; i++) {
    const r = (0.5 + rand() * 0.5) * s;
    mesh(new THREE.IcosahedronGeometry(r, 3), leaf, g,
      (rand() - 0.5) * 1.6 * s, (2.2 + rand() * 1.4) * s, (rand() - 0.5) * 1.0 * s);
  }
}
[[-9, -9, 1.1], [-3.5, -10, 0.9], [2.8, -10.5, 1.2], [8.5, -9.5, 1.0], [12, -11, 1.3], [-13, -9.5, 1.0]]
  .forEach((p) => tree(...p));

// ---------- ลังไม้ ----------
{
  const crate = new THREE.Group(); crate.position.set(-0.1, 0, 0.45); crate.rotation.y = -0.12; scene.add(crate);
  const cm = mat(0xe4bfae);
  const s = 0.8, hgt = 0.75;
  mesh(new THREE.BoxGeometry(s, 0.05, s), cm, crate, 0, hgt, 0);
  for (const sx of [-1, 1]) for (const sz of [-1, 1])
    mesh(new THREE.BoxGeometry(0.08, hgt, 0.08), cm, crate, sx * (s / 2 - 0.04), hgt / 2, sz * (s / 2 - 0.04));
  for (let i = 0; i < 3; i++) {
    const y = 0.14 + i * 0.22;
    mesh(new THREE.BoxGeometry(s - 0.02, 0.17, 0.03), cm, crate, 0, y, s / 2 - 0.02);
    mesh(new THREE.BoxGeometry(s - 0.02, 0.17, 0.03), cm, crate, 0, y, -s / 2 + 0.02);
    mesh(new THREE.BoxGeometry(0.03, 0.17, s - 0.02), cm, crate, s / 2 - 0.02, y, 0);
    mesh(new THREE.BoxGeometry(0.03, 0.17, s - 0.02), cm, crate, -s / 2 + 0.02, y, 0);
  }
  mesh(new THREE.BoxGeometry(s + 0.02, 0.04, 0.05), cm, crate, 0, hgt - 0.03, s / 2);
}

// ---------- ที่สูบลม ----------
{
  const pump = new THREE.Group(); pump.position.set(-1.6, 0, 0.6); pump.rotation.y = 0.3; scene.add(pump);
  mesh(new THREE.BoxGeometry(0.5, 0.025, 0.14), mat(0x2a2a2a), pump, 0, 0.012, 0);
  mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.55, 16), mat(0xc8202a, { roughness: 0.4 }), pump, 0, 0.3, 0);
  mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.6, 8), mat(0xcccccc, { metalness: 0.8, roughness: 0.3 }), pump, 0, 0.85, 0);
  const handle = mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.42, 10), mat(0x222222), pump, 0, 1.15, 0);
  handle.rotation.z = Math.PI / 2;
  const gauge = mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.03, 20), mat(0xeeeeee, { roughness: 0.3 }), pump, 0, 0.16, 0.05);
  gauge.rotation.x = Math.PI / 2;
}

// ---------- ตัวละคร (โครงกระดูกแบบลำดับชั้น) ----------
function limb(r, len, material) {
  const geo = new THREE.CapsuleGeometry(r, len, 6, 14);
  geo.translate(0, -len / 2, 0);
  return new THREE.Mesh(geo, material);
}
function joint(parent, x, y, z) {
  const g = new THREE.Group(); g.position.set(x, y, z); parent.add(g); return g;
}
function addMesh(m, parent, y = 0) { m.position.y = y; m.castShadow = m.receiveShadow = true; parent.add(m); return m; }

function makePerson({ shirt, skin, hair, longSleeves, hairStyle }) {
  const P = {};
  const shirtM = mat(shirt, { roughness: 0.9 }), skinM = mat(skin, { roughness: 0.6 });
  const pantsM = mat(0xffffff, { map: jeansTex, roughness: 0.95 });
  const hairM = mat(hair, { roughness: 0.7 }), shoeM = mat(0x9a4a28, { roughness: 0.5 });

  P.root = new THREE.Group(); scene.add(P.root);
  P.pelvis = joint(P.root, 0, 0.98, 0);
  addMesh(new THREE.Mesh(new THREE.CapsuleGeometry(0.15, 0.12, 6, 14).rotateZ(Math.PI / 2).scale(1, 1, 0.75), pantsM), P.pelvis, -0.02);
  mesh(new THREE.BoxGeometry(0.36, 0.04, 0.24), mat(0x2b2420), P.pelvis, 0, 0.08, 0);

  P.spine = joint(P.pelvis, 0, 0.06, 0);
  const torso = addMesh(new THREE.Mesh(new THREE.CapsuleGeometry(0.17, 0.3, 8, 18), shirtM), P.spine, 0.27);
  torso.scale.set(1.08, 1, 0.68);
  if (longSleeves) { // ปกเสื้อเชิ้ต + กระดุม
    const collar = mesh(new THREE.TorusGeometry(0.075, 0.018, 6, 16, Math.PI * 1.4), shirtM, P.spine, 0, 0.56, 0.02);
    collar.rotation.set(Math.PI / 2, 0, -Math.PI * 0.2 - Math.PI / 2);
    for (let i = 0; i < 4; i++) mesh(new THREE.SphereGeometry(0.008, 6, 6), mat(0xdddddd), P.spine, 0, 0.46 - i * 0.1, 0.118);
    mesh(new THREE.ConeGeometry(0.035, 0.08, 3), skinM, P.spine, 0, 0.53, 0.09).rotation.x = Math.PI;
  }
  P.neck = joint(P.spine, 0, 0.56, 0);
  addMesh(new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.05, 0.12, 12), skinM), P.neck, 0.04);
  P.head = joint(P.neck, 0, 0.1, 0.01);
  const skull = addMesh(new THREE.Mesh(new THREE.SphereGeometry(0.105, 24, 18), skinM), P.head, 0.1);
  skull.scale.set(0.88, 1.12, 0.98);
  const jaw = mesh(new THREE.SphereGeometry(0.075, 16, 12), skinM, P.head, 0, 0.035, 0.025); jaw.scale.set(1, 0.8, 1.05);
  mesh(new THREE.ConeGeometry(0.016, 0.045, 8), skinM, P.head, 0, 0.09, 0.105).rotation.x = Math.PI / 2;
  const eyeM = new THREE.MeshStandardMaterial({ color: 0x2a1d17, roughness: 0.3 });
  for (const s of [-1, 1]) {
    mesh(new THREE.SphereGeometry(0.011, 8, 8), eyeM, P.head, s * 0.035, 0.12, 0.09);
    mesh(new THREE.BoxGeometry(0.035, 0.006, 0.01), mat(hair), P.head, s * 0.036, 0.142, 0.092);
    mesh(new THREE.SphereGeometry(0.02, 8, 8), skinM, P.head, s * 0.093, 0.1, 0);
  }
  mesh(new THREE.BoxGeometry(0.035, 0.008, 0.01), mat(0xb0574f), P.head, 0, 0.045, 0.098);
  // ผม
  const cap = mesh(new THREE.SphereGeometry(0.112, 24, 14, 0, Math.PI * 2, 0, Math.PI * 0.52), hairM, P.head, 0, 0.12, -0.008);
  cap.scale.set(0.92, hairStyle === 'spiky' ? 1.15 : 1.0, 1.02);
  cap.rotation.x = -0.25;
  if (hairStyle === 'spiky') {
    for (let i = 0; i < 9; i++) {
      const c = mesh(new THREE.ConeGeometry(0.03, 0.06, 5), hairM, P.head, (rand() - 0.5) * 0.12, 0.21, -0.03 + (rand() - 0.5) * 0.08);
      c.rotation.set(0.3 + rand() * 0.3, 0, (rand() - 0.5) * 0.8);
    }
  } else {
    const side = mesh(new THREE.SphereGeometry(0.1, 16, 10), hairM, P.head, 0, 0.12, -0.03);
    side.scale.set(0.95, 0.85, 0.9);
  }

  // แขน
  for (const s of [-1, 1]) { // s=-1 คือด้านขวาของตัวละคร (หันหน้าไป +z)
    const key = s < 0 ? 'R' : 'L';
    const sh = joint(P.spine, s * 0.2, 0.47, 0);
    addMesh(new THREE.Mesh(new THREE.SphereGeometry(0.07, 14, 10), shirtM), sh);
    addMesh(limb(0.052, 0.22, longSleeves ? shirtM : skinM), sh, -0.02);
    if (!longSleeves) { const sleeve = addMesh(limb(0.064, 0.08, shirtM), sh, 0); sleeve.scale.set(1, 1, 1); }
    const el = joint(sh, 0, -0.28, 0);
    addMesh(limb(0.042, 0.2, longSleeves ? shirtM : skinM), el);
    const wr = joint(el, 0, -0.25, 0);
    const hand = addMesh(new THREE.Mesh(new THREE.BoxGeometry(0.075, 0.14, 0.03), skinM), wr, -0.07);
    hand.geometry.translate(0, 0, 0); hand.scale.set(1, 1, 1);
    const thumb = mesh(new THREE.CapsuleGeometry(0.012, 0.04, 4, 6), skinM, wr, -s * -0.04, -0.04, 0.02);
    thumb.rotation.z = s * 0.6;
    P['shoulder' + key] = sh; P['elbow' + key] = el; P['wrist' + key] = wr;
  }
  // ขา
  for (const s of [-1, 1]) {
    const key = s < 0 ? 'R' : 'L';
    const hip = joint(P.pelvis, s * 0.1, -0.04, 0);
    addMesh(limb(0.078, 0.36, pantsM), hip);
    const knee = joint(hip, 0, -0.44, 0);
    addMesh(limb(0.064, 0.36, pantsM), knee);
    const ankle = joint(knee, 0, -0.45, 0);
    const shoe = mesh(new THREE.BoxGeometry(0.11, 0.08, 0.27), shoeM, ankle, 0, -0.035, 0.05);
    shoe.geometry.translate(0, 0, 0);
    mesh(new THREE.BoxGeometry(0.115, 0.02, 0.28), mat(0x3a2418), ankle, 0, -0.075, 0.05);
    P['hip' + key] = hip; P['knee' + key] = knee; P['ankle' + key] = ankle;
  }
  return P;
}

const blue = makePerson({ shirt: 0x4a6a96, skin: 0xe8c3a6, hair: 0x15130f, longSleeves: true, hairStyle: 'spiky' });
blue.root.position.set(0.95, 0, 0.55);
const white = makePerson({ shirt: 0xe9ebed, skin: 0xedc8b0, hair: 0x5a3d2c, longSleeves: false, hairStyle: 'slick' });
white.root.position.set(-1.1, 0, -0.05);

// ---------- ลูกบอล ----------
const BALL_R = 0.12;
const orangeBall = mesh(new THREE.SphereGeometry(BALL_R, 32, 24), mat(0xffffff, { map: ballTex, roughness: 0.75 }), scene);
const ghosts = [0.55, 0.35, 0.2].map((o) => {
  const g = new THREE.Mesh(orangeBall.geometry, new THREE.MeshStandardMaterial({ map: ballTex, transparent: true, opacity: o, depthWrite: false }));
  scene.add(g); return g;
});
const STONE_R = 0.17;
const stoneGeo = new THREE.IcosahedronGeometry(STONE_R, 4);
{ // ทำผิวหินให้ขรุขระ
  const p = stoneGeo.attributes.position, v = new THREE.Vector3();
  for (let i = 0; i < p.count; i++) {
    v.fromBufferAttribute(p, i);
    const n = 1 + Math.sin(v.x * 61) * Math.cos(v.y * 47) * Math.sin(v.z * 53) * 0.05;
    v.multiplyScalar(n); p.setXYZ(i, v.x, v.y, v.z);
  }
  stoneGeo.computeVertexNormals();
}
const stoneMat = mat(0xffffff, { map: stoneTex, roughness: 1 });
const stoneBall = mesh(stoneGeo, stoneMat, scene);
const stoneBall2 = mesh(stoneGeo, stoneMat, scene, -2.15, STONE_R, 0.45); // ลูกหินที่วางอยู่ข้างสนาม

// เศษหินกระเด็นตอนลูกหินตกกระแทกพื้น
const pebbles = [];
for (let i = 0; i < 26; i++) {
  const r = 0.012 + rand() * 0.022;
  const m = mesh(new THREE.DodecahedronGeometry(r, 0), mat(0xc9c6c1), scene);
  const a = rand() * Math.PI * 2, sp = 0.6 + rand() * 1.6;
  pebbles.push({ m, r, vx: Math.cos(a) * sp, vz: Math.sin(a) * sp, vy: 0.8 + rand() * 1.8, spin: rand() * 20 });
}
// รอยแตก/ฝุ่นบนพื้น
const crack = new THREE.Mesh(new THREE.CircleGeometry(0.28, 24),
  new THREE.MeshBasicMaterial({ color: 0x2a2724, transparent: true, opacity: 0, depthWrite: false }));
crack.rotation.x = -Math.PI / 2; scene.add(crack);

// ---------- Timeline ----------
// ช็อต 1 (0.0–2.3s): ใกล้ ๆ ชายเสื้อน้ำเงินปล่อย "ลูกหิน" ลงพื้น → ไม่เด้ง เศษหินกระจาย
// ช็อต 2 (2.3–5.0s): มุมกว้างแบบภาพแรก ชายเสื้อขาวชี้ ชายเสื้อน้ำเงินเลี้ยงลูกบาสยางสีส้ม → "Clever!"
const CUT = 2.3;
const DROP_T = 0.55, IMPACT_T = 0.55 + Math.sqrt((2 * (1.0 - STONE_R)) / 9.81);
const captions = [
  [0.05, 0.6, 'Stone'], [0.6, 1.25, 'balls,'], [1.25, 1.75, "don't"], [1.75, 2.3, 'bounce...'],
  [2.45, 3.3, 'So'], [3.3, 3.95, 'rubber!'], [3.95, 5.0, 'Clever!'],
];
const capEl = document.querySelector('#caption span');

function local(P, x, y, z) { return new THREE.Vector3(x, y, z).applyMatrix4(P.root.matrixWorld); }

function poseIdle(P, t, breathe = 1) {
  const b = Math.sin(t * 2.2) * 0.02 * breathe;
  P.spine.rotation.set(b, 0, 0); P.neck.rotation.set(0, 0, 0); P.head.rotation.set(0, 0, 0);
  for (const k of ['R', 'L']) {
    P['shoulder' + k].rotation.set(0, 0, (k === 'R' ? -1 : 1) * 0.12);
    P['elbow' + k].rotation.set(-0.15, 0, 0); P['wrist' + k].rotation.set(0, 0, 0);
    P['hip' + k].rotation.set(0, 0, 0); P['knee' + k].rotation.set(0, 0, 0); P['ankle' + k].rotation.set(0, 0, 0);
  }
  P.pelvis.position.y = 0.98;
}
// ย่อเข่า: ปรับสะโพก/เข่า/ข้อเท้าให้เท้าแตะพื้นเสมอ
function crouch(P, amt, stance = 0.25) {
  const thigh = 0.44, shin = 0.45;
  for (const k of ['R', 'L']) {
    const side = k === 'R' ? -1 : 1;
    P['hip' + k].rotation.x = -amt; P['knee' + k].rotation.x = amt * 2; P['ankle' + k].rotation.x = -amt;
    P['hip' + k].rotation.z = side * stance * 0.4; P['ankle' + k].rotation.z = -side * stance * 0.4;
  }
  P.pelvis.position.y = 0.98 - (thigh + shin) * (1 - Math.cos(amt)) - 0.03 * stance;
}

function animateBlue(t) {
  const P = blue;
  poseIdle(P, t);
  if (t < CUT) {
    // ถือลูกหินไว้ระดับเอว แล้วปล่อย → มองลงตามลูก มือกางค้าง (เหมือนภาพที่ 3)
    P.root.rotation.y = -0.35;
    const k = smooth((t - DROP_T + 0.25) / 0.6);
    crouch(P, 0.25 + 0.12 * k, 0.6);
    P.spine.rotation.x = 0.28 + 0.12 * k;
    P.neck.rotation.x = 0.25 + 0.2 * smooth((t - DROP_T) / 0.4);
    P.head.rotation.x = 0.15 + 0.2 * smooth((t - DROP_T) / 0.4);
    const surprise = smooth((t - IMPACT_T) / 0.3);
    for (const k2 of ['R', 'L']) {
      const s = k2 === 'R' ? -1 : 1;
      P['shoulder' + k2].rotation.set(lerp(-0.75, -0.25, k) - 0.15 * surprise, 0, s * lerp(0.25, 0.45, k) + s * 0.1 * surprise);
      P['elbow' + k2].rotation.set(lerp(-0.9, -0.35, k), 0, 0);
      P['wrist' + k2].rotation.set(lerp(0, 0.4, k), 0, s * 0.2);
    }
  } else {
    // เลี้ยงลูกด้วยมือขวา ตัวย่อต่ำ
    P.root.rotation.y = -0.5;
    const ph = (t - CUT) * 2.6 * Math.PI * 2;
    crouch(P, 0.42 + Math.sin(ph) * 0.03, 0.9);
    P.spine.rotation.x = 0.42; P.spine.rotation.y = 0.15;
    P.neck.rotation.x = 0.25; P.head.rotation.x = 0.25; P.head.rotation.y = -0.1;
    const hand = 0.5 + 0.5 * Math.cos(ph); // 1 = มือบนสุด
    P.shoulderR.rotation.set(-0.55 - 0.25 * hand, 0, -0.32);
    P.elbowR.rotation.set(-0.25 - 0.55 * hand, 0, 0);
    P.wristR.rotation.set(0.7 * (1 - hand), 0, 0);
    P.shoulderL.rotation.set(0.15, 0, 0.45); P.elbowL.rotation.set(-0.6, 0, 0);
  }
}

function animateWhite(t) {
  const P = white;
  poseIdle(P, t);
  P.root.rotation.y = 0.75;
  crouch(P, 0.08, 0.2);
  P.spine.rotation.z = -0.05;
  P.head.rotation.y = 0.15;
  P.shoulderR.rotation.set(0.05, 0, -0.18); P.elbowR.rotation.set(-0.2, 0, 0);
  if (t > CUT) {
    // ยกแขนซ้ายชี้ไปทางลูกบอล
    const k = smooth((t - CUT - 0.15) / 0.45);
    P.shoulderL.rotation.set(lerp(0, -1.15, k), lerp(0, -0.35, k), lerp(0.12, 0.25, k));
    P.elbowL.rotation.set(lerp(-0.15, -0.35, k) + Math.sin(t * 9) * 0.04 * k, 0, 0);
    P.wristL.rotation.set(lerp(0, 0.35, k), 0, 0);
    P.head.rotation.x = 0.12 * k; P.head.rotation.y = lerp(0.15, 0.35, k);
  }
}

function animateBalls(t) {
  blue.root.updateMatrixWorld(true);
  if (t < CUT) {
    orangeBall.visible = false; ghosts.forEach((g) => (g.visible = false));
    stoneBall.visible = true;
    const start = local(blue, 0.0, 0.0, 0.42); // หน้าท้อง
    start.y = 1.0;
    if (t < DROP_T) {
      stoneBall.position.copy(start);
    } else {
      const dt = t - DROP_T;
      stoneBall.position.set(start.x, Math.max(STONE_R - 0.03, start.y - 0.5 * 9.81 * dt * dt), start.z);
      if (t > IMPACT_T) stoneBall.position.y = STONE_R - 0.03 - 0.01 * smooth((t - IMPACT_T) / 0.1);
    }
    stoneBall.rotation.set(0.3, t * 0.2, 0);
    const it = t - IMPACT_T;
    crack.position.set(stoneBall.position.x, 0.004, stoneBall.position.z);
    crack.material.opacity = it > 0 ? 0.35 * smooth(it / 0.15) : 0;
    for (const p of pebbles) {
      p.m.visible = it > 0;
      if (it <= 0) continue;
      // บอลลิสติกพร้อมกระดอนพื้นแบบลดทอน
      let x = p.vx * it, z = p.vz * it, vy = p.vy, y0 = 0.04, tt = it, y = 0;
      for (let b = 0; b < 4; b++) {
        const land = (vy + Math.sqrt(vy * vy + 2 * 9.81 * y0)) / 9.81;
        if (tt < land) { y = y0 + vy * tt - 0.5 * 9.81 * tt * tt; break; }
        tt -= land; vy *= 0.35; y0 = 0; y = 0;
      }
      const drag = 1 - smooth(it / 1.2) * 0.5;
      p.m.position.set(stoneBall.position.x + x * drag, Math.max(p.r, y + p.r), stoneBall.position.z + z * drag);
      p.m.rotation.set(it * p.spin, it * p.spin * 0.7, 0);
    }
  } else {
    // ลูกหินที่แตกนอนนิ่ง, ลูกส้มเลี้ยงขึ้นลง
    stoneBall.position.copy(local(blue, -0.05, 0, 0.4)); stoneBall.position.y = STONE_R - 0.04;
    pebbles.forEach((p) => (p.m.visible = false)); crack.material.opacity = 0;
    stoneBall.visible = false;
    orangeBall.visible = true;
    const ballAt = (tt) => {
      const ph = ((tt - CUT) * 2.6) % 1; // 0 = บนสุด, 0.5 = กระทบพื้น
      const yTop = 0.78, yBot = BALL_R * 0.92;
      const u = Math.abs(ph - 0.5) * 2; // 1 ที่บนสุด, 0 ที่พื้น
      const y = yBot + (yTop - yBot) * (1 - (1 - u) * (1 - u));
      const p = local(blue, -0.27, 0, 0.42); p.y = y; return p;
    };
    orangeBall.position.copy(ballAt(t));
    const ph = ((t - CUT) * 2.6) % 1;
    const squash = 1 - 0.18 * Math.max(0, 1 - Math.abs(ph - 0.5) / 0.04);
    orangeBall.scale.set(1 / Math.sqrt(squash), squash, 1 / Math.sqrt(squash));
    orangeBall.rotation.set(t * 9, 0.4, 0);
    ghosts.forEach((g, i) => { g.visible = true; g.position.copy(ballAt(t - (i + 1) * 0.012)); g.rotation.copy(orangeBall.rotation); });
  }
}

function animateCamera(t) {
  if (t < CUT) {
    // ช็อตใกล้ จากหน้าตรง ชายเสื้อน้ำเงินกลางเฟรม, กล้องดันเข้าเล็กน้อย
    const k = t / CUT;
    camera.fov = 52;
    camera.position.set(lerp(0.6, 0.65, k), lerp(1.75, 1.7, k), lerp(3.4, 3.1, k));
    camera.lookAt(0.75, 0.82, 0.3);
    // กล้องสั่นตอนลูกหินกระแทก
    const it = t - IMPACT_T;
    if (it > 0 && it < 0.35) {
      const a = (1 - it / 0.35) * 0.012;
      camera.position.x += Math.sin(it * 90) * a; camera.position.y += Math.cos(it * 77) * a;
    }
  } else {
    const k = (t - CUT) / (DURATION - CUT);
    camera.fov = 62;
    camera.position.set(lerp(0.0, 0.06, k), lerp(1.45, 1.42, k), lerp(3.9, 3.7, k));
    camera.lookAt(-0.05, 1.22, -1.0);
  }
  camera.updateProjectionMatrix();
}

function updateCaption(t) {
  const c = captions.find(([a, b]) => t >= a && t < b);
  if (!c) { capEl.textContent = ''; return; }
  capEl.textContent = c[2];
  const pop = clamp01((t - c[0]) / 0.12);
  capEl.style.transform = `scale(${lerp(0.75, 1, pop) + Math.sin(pop * Math.PI) * 0.08})`;
}

window.renderAt = (t) => {
  animateBlue(t); animateWhite(t); animateBalls(t); animateCamera(t); updateCaption(t);
  renderer.render(scene, camera);
};
window.DURATION = DURATION;
window.sceneReady = true;

// โหมดพรีวิว: เปิดไฟล์ในเบราว์เซอร์แล้วเล่นวนแบบ real-time
if (!new URLSearchParams(location.search).has('capture')) {
  const t0 = performance.now();
  const loop = () => { window.renderAt(((performance.now() - t0) / 1000) % DURATION); requestAnimationFrame(loop); };
  loop();
}
