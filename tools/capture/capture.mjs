// 視点リストを順に撮影してPNG保存する(独自実装)。ヘッドレスChromeでtools/viewerを開く。
// 使い方: node capture.mjs --spz /gen/_exp/d1/500k.spz --poses poses.json --out DIR [--scale 1 --offset 0 --w 1280 --h 960]
// poses.json: [{ "name": "front", "pos": [x,y,z], "target": [x,y,z], "fov": 60 }, ...]
import { chromium } from "playwright-core";
import { readFileSync, mkdirSync } from "node:fs";
import path from "node:path";

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, v, i, a) => (v.startsWith("--") ? [...acc, [v.slice(2), a[i + 1]]] : acc), [])
);
const W = +(args.w || 1280), H = +(args.h || 960);
let ground = +(args.ground ?? -1.5); // 地面のY(ビューア座標)。viewpoints.json の高さは地面基準
let poses = JSON.parse(readFileSync(args.poses, "utf-8"));
// T3形式(camera_paths.json): Blender世界座標(X右・Y前方・Z上、m)→ ビューア座標(X右・Y上・Z後方)。
// --char-y: キャラ位置(Blender原点)を元カメラの何m前方に置くか。--char-x も同様。
if (!Array.isArray(poses) && poses.cameras) {
  const cx = +(args["char-x"] ?? 0), cy = +(args["char-y"] ?? 3.0);
  const toV = ([x, y, z]) => [x + cx, z, -(y + cy)];
  const sensorH = (poses.render?.sensor_width_mm ?? 36) * (poses.render?.height ?? 1080) / (poses.render?.width ?? 1440);
  poses = poses.cameras.map((c, i) => ({
    name: `${i + 1}_${c.name}`, pos: toV(c.position), target: toV(c.target),
    fov: (2 * Math.atan(sensorH / 2 / c.focal_length_mm) * 180) / Math.PI,
  }));
  args.ground = 0; // 既に地面基準(z=0)
} else {
if (!Array.isArray(poses)) poses = poses.viewpoints;
poses = poses.map((p) => ({ ...p, pos: [p.pos[0], p.pos[1] + ground, p.pos[2]], target: [p.target[0], p.target[1] + ground, p.target[2]] }));
}
const out = args.out;
mkdirSync(out, { recursive: true });

const browser = await chromium.launch({
  executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  headless: true,
  args: ["--use-angle=d3d11", "--enable-webgl", "--ignore-gpu-blocklist"],
});
const page = await browser.newPage({ viewport: { width: W, height: H } });
page.on("console", (m) => { if (m.type() === "error") console.error("[page]", m.text()); });
const url = `http://127.0.0.1:${args.port || 8765}/?spz=${encodeURIComponent(args.spz)}&scale=${args.scale || 1}&offset=${args.offset || 0}&w=${W}&h=${H}&flip=${args.flip ?? 1}&hud=0`;
await page.goto(url);
const n = await page.evaluate(() => window.viewer.ready);
console.log("splats:", n);
for (const p of poses) {
  await page.evaluate((p) => window.viewer.setPose(p), p);
  await page.evaluate(() => new Promise((r) => { let k = 0; const f = () => (++k > 20 ? r() : requestAnimationFrame(f)); f(); }));
  await page.waitForTimeout(800);
  await page.locator("canvas").screenshot({ path: path.join(out, `${p.name}.png`) });
  console.log("saved", p.name);
}
await browser.close();
