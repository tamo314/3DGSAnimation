// 元のカメラ位置(0,視点高,0)・前方-Z・fov60・4:3 から、画面上の点までの距離を推定する(独自実装)。
// 使い方: node rayprobe.mjs --spz gen/.../full_res.spz --scale S --offset O --eye E --pts "name:u,v;name:u,v"
import { chromium } from "playwright-core";
const a = Object.fromEntries(process.argv.slice(2).reduce((acc, v, i, arr) => (v.startsWith("--") ? [...acc, [v.slice(2), arr[i + 1]]] : acc), []));
const b = await chromium.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true, args: ["--use-angle=d3d11", "--ignore-gpu-blocklist"] });
const p = await b.newPage({ viewport: { width: 1280, height: 960 } });
await p.goto(`http://127.0.0.1:8765/?spz=${a.spz}&scale=${a.scale}&offset=${a.offset}&hud=0&w=1280&h=960`);
await p.evaluate(() => window.viewer.ready);
for (const item of a.pts.split(";")) {
  const [name, uv] = item.split(":");
  const [u, v] = uv.split(",").map(Number);
  const r = await p.evaluate(([u, v, e]) => window.viewer.rayProbe([0, e, 0], u, v, 60, 4 / 3), [u, v, +a.eye]);
  console.log(name, JSON.stringify(r));
}
await b.close();
