// Dumps frames of the season-1 finale (2D) to use as the "old style" side of the glitch transition.
// Usage: node dump_old.js <outDir> <startSec> <count>
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
(async () => {
  const [dir, start, count] = [process.argv[2], Number(process.argv[3]), Number(process.argv[4])];
  fs.mkdirSync(dir, { recursive: true });
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto('file://' + path.resolve(__dirname, '../../final/final.html') + '#render');
  await p.evaluate(() => document.fonts.ready);
  const fps = 30, s0 = Math.round(start * fps);
  for (let i = 0; i < count; i++) {
    const d = await p.evaluate(i => { window.renderFrame(i); return document.getElementById('c').toDataURL('image/png'); }, s0 + i);
    fs.writeFileSync(`${dir}/old_${String(i).padStart(3, '0')}.png`, Buffer.from(d.split(',')[1], 'base64'));
  }
  await b.close();
})();
