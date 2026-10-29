// เรนเดอร์ฉาก src/index.html ทีละเฟรมด้วย Chromium (Playwright) แล้วรวมเป็น MP4 ด้วย ffmpeg
// ใช้งาน: node render.mjs [output.mp4] [fps]
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
let playwright;
try { playwright = require('playwright'); } catch { playwright = require('/opt/node22/lib/node_modules/playwright'); }

const root = path.dirname(fileURLToPath(import.meta.url));
const out = path.resolve(process.argv[2] || 'output/clip.mp4');
const fps = Number(process.argv[3] || 30);
const framesDir = path.join(root, 'frames');

const types = { '.html': 'text/html', '.js': 'text/javascript' };
const server = http.createServer((req, res) => {
  const file = path.join(root, decodeURIComponent(req.url.split('?')[0]));
  if (!file.startsWith(root) || !fs.existsSync(file)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
}).listen(0);
const port = server.address().port;

fs.rmSync(framesDir, { recursive: true, force: true });
fs.mkdirSync(framesDir, { recursive: true });
fs.mkdirSync(path.dirname(out), { recursive: true });

const browser = await playwright.chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 720, height: 1280 } });
page.on('pageerror', (e) => console.error('page error:', e.message));
await page.goto(`http://localhost:${port}/src/index.html?capture`);
await page.waitForFunction(() => window.sceneReady === true);
await page.evaluate(() => document.fonts.ready);

const duration = await page.evaluate(() => window.DURATION);
const total = Math.round(duration * fps);
const stage = page.locator('#stage');
for (let i = 0; i < total; i++) {
  await page.evaluate((t) => window.renderAt(t), i / fps);
  await stage.screenshot({ path: path.join(framesDir, `${String(i).padStart(4, '0')}.png`) });
  if (i % 15 === 0) process.stdout.write(`frame ${i}/${total}\r`);
}
await browser.close();
server.close();

execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(fps), '-i', path.join(framesDir, '%04d.png'),
  '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out]);
console.log(`\nบันทึกวิดีโอแล้ว: ${out} (${total} เฟรม, ${fps} fps)`);
