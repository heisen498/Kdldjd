// 3D reels renderer: serves this folder over HTTP (ES modules need it) and captures frames with headless Chromium.
// Usage: node render.js --stills <dir> t1,t2,...   |   node render.js <out.mp4> [startFrame endFrame port]
// On your own PC: set GPU=1 to use the graphics card, e.g.  set GPU=1 && node render.js video.mp4  (Windows cmd)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const http = require('http'), fs = require('fs'), path = require('path');
const root = __dirname;
const types = { '.js': 'text/javascript', '.html': 'text/html', '.json': 'application/json' };
function serve(port) {
  return http.createServer((q, s) => {
    const f = path.join(root, decodeURIComponent(q.url.split('?')[0].split('#')[0]));
    fs.readFile(f, (e, d) => { if (e) { s.writeHead(404); s.end(); return; } s.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' }); s.end(d); });
  }).listen(port);
}
(async () => {
  const stills = process.argv[2] === '--stills';
  const port = stills ? 8766 : Number(process.argv[5] || 8767);
  const srv = serve(port);
  // GPU=1 opens a visible Chromium window so your graphics card does the 3D work (much faster than software rendering).
  const gpu = (process.env.GPU || '').trim() === '1';
  const b = await chromium.launch(gpu ? { headless: false, args: ['--ignore-gpu-blocklist', '--enable-gpu-rasterization'] } : {});
  const p = await b.newPage({ viewport: { width: 540, height: 960 } });
  p.on('pageerror', e => console.error('PAGEERR', e.message));
  await p.goto(`http://localhost:${port}/s2b2.html#render`);
  await p.waitForFunction(() => window.ready, null, { timeout: 120000 });
  // motion blur (2 sub-frames) only on the fast GPU path; MB=0 turns it off
  if (gpu && (process.env.MB || '').trim() !== '0') await p.evaluate(() => { window.MB = true; });
  const { FPS, NF } = await p.evaluate(() => window.VIDEO);
  const grab = i => p.evaluate(i => { window.renderFrame(i); return document.getElementById('out').toDataURL('image/jpeg', 0.92); }, i);
  if (stills) {
    const dir = process.argv[3]; fs.mkdirSync(dir, { recursive: true });
    for (const t of process.argv[4].split(',').map(Number)) { const d = await grab(Math.round(t * FPS)); fs.writeFileSync(`${dir}/f${String(Math.round(t * FPS)).padStart(5, "0")}.jpg`, Buffer.from(d.split(',')[1], 'base64')); }
  } else {
    const outf = process.argv[3 - 1 + 1 - 1] ? process.argv[2] : null;
    const s0 = Number(process.argv[3] || 0), s1 = Number(process.argv[4] || NF);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p', '-r', String(FPS), process.argv[2]], { stdio: ['pipe', 'ignore', 'inherit'] });
    const t0 = Date.now();
    for (let i = s0; i < s1; i++) {
      const d = await grab(i);
      if (!ff.stdin.write(Buffer.from(d.split(',')[1], 'base64'))) await new Promise(r => ff.stdin.once('drain', r));
      if ((i - s0) % 150 === 0) console.error(`frame ${i}/${s1}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
  }
  await b.close(); srv.close();
})();
