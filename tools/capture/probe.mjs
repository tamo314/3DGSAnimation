import { chromium } from "playwright-core";
const b = await chromium.launch({executablePath:"C:/Program Files/Google/Chrome/Application/chrome.exe",headless:true,args:["--use-angle=d3d11","--ignore-gpu-blocklist"]});
const p = await b.newPage();
await p.goto("http://127.0.0.1:8765/?spz="+process.argv[2]+"&hud=0");
await p.evaluate(()=>window.viewer.ready);
console.log(JSON.stringify(await p.evaluate(()=>window.viewer.groundProbe())));
await b.close();
