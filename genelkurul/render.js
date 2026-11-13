// Usage: node render.js out.mp4 [audio.wav]   |   node render.js --stills dir t1,t2,...
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs'), path = require('path');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on('pageerror', e => console.error('PAGEERR', e.message));
  await p.goto('file://' + path.resolve(__dirname, 'genelkurul.html') + '#render');
  await p.evaluate(() => document.fonts.ready);
  const { FPS, NF } = await p.evaluate(() => window.VIDEO);
  if (process.argv[2] === '--stills') {
    const dir = process.argv[3]; fs.mkdirSync(dir, { recursive: true });
    const times = process.argv[4].split(',').map(Number);
    let f = 0;
    for (const t of times) {
      const target = Math.round(t * FPS);
      const data = await p.evaluate(i => { window.renderFrame(i); return document.getElementById('c').toDataURL('image/jpeg', 0.85); }, target);
      fs.writeFileSync(`${dir}/t${String(t).padStart(5, '0')}.jpg`, Buffer.from(data.split(',')[1], 'base64'));
    }
  } else {
    const out = process.argv[2], audio = process.argv[3];
    const args = ['-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-'];
    if (audio) args.push('-i', audio);
    args.push('-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', String(FPS));
    if (audio) args.push('-c:a', 'aac', '-b:a', '160k', '-shortest');
    args.push('-movflags', '+faststart', out);
    const ff = spawn('ffmpeg', args, { stdio: ['pipe', 'ignore', 'inherit'] });
    for (let i = 0; i < NF; i++) {
      const data = await p.evaluate(i => { window.renderFrame(i); return document.getElementById('c').toDataURL('image/jpeg', 0.93); }, i);
      if (!ff.stdin.write(Buffer.from(data.split(',')[1], 'base64'))) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 150 === 0) console.error('frame', i, '/', NF);
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
  }
  await b.close();
})();
