# Glitch transition: season-1 2D frames break apart into the new 3D season.
# Usage: python3 glitch.py <old_dir> <new_dir> <out_dir> <old_audio.wav> <out_audio.wav>
import sys, os, glob, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

old_dir, new_dir, out_dir, old_wav, out_wav = sys.argv[1:6]
os.makedirs(out_dir, exist_ok=True)
rng = np.random.default_rng(42)
olds = sorted(glob.glob(f"{old_dir}/old_*.png"))
news = [np.asarray(Image.open(f).convert("RGB")) for f in sorted(glob.glob(f"{new_dir}/*.jpg"))]
N = len(olds)
FONT = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf"
f_big, f_mid = ImageFont.truetype(FONT, 58), ImageFont.truetype(FONT, 44)
H, W = 1920, 1080

for k, path in enumerate(olds):
    p = k / (N - 1)
    g = min(1.0, max(0.0, (p - 0.12) / 0.68)) ** 1.25
    img = np.asarray(Image.open(path).convert("RGB")).astype(np.int16)
    # flashes of the new 3D world leaking through
    if news and 0.35 < p < 0.85 and rng.random() < 0.25 + g * 0.35:
        img = news[rng.integers(len(news))].astype(np.int16)
    # horizontal slice displacement
    for _ in range(int(g * 22)):
        y0 = rng.integers(0, H - 10); h = rng.integers(6, 90); dx = int(rng.normal(0, 1) * 170 * g)
        img[y0:y0 + h] = np.roll(img[y0:y0 + h], dx, axis=1)
    # block corruption
    pal = np.array([[255, 0, 160], [0, 255, 220], [60, 255, 60], [255, 230, 0]], np.int16)
    for _ in range(int(g * 16)):
        bw, bh = rng.integers(40, 320), rng.integers(20, 160)
        sx, sy, dx, dy = rng.integers(0, W - bw), rng.integers(0, H - bh), rng.integers(0, W - bw), rng.integers(0, H - bh)
        blk = img[sy:sy + bh, sx:sx + bw].copy()
        if rng.random() < 0.35: blk = (blk // 2 + pal[rng.integers(4)] // 2)
        img[dy:dy + bh, dx:dx + bw] = blk
    # RGB split
    sh = int(3 + g * 42 * (0.6 + 0.4 * rng.random()))
    r = np.roll(img[:, :, 0], sh, axis=1); b = np.roll(img[:, :, 2], -sh, axis=1)
    img = np.stack([r, img[:, :, 1], b], axis=2)
    # posterize + noise + scanlines
    if g > 0.45: img = (img // 40) * 40 + 10
    img = img + rng.normal(0, 6 + g * 38, img.shape).astype(np.int16)
    img[::3] = (img[::3] * (1 - 0.3 * g)).astype(np.int16)
    # final static then black
    if p > 0.82:
        q = (p - 0.82) / 0.18
        static = rng.integers(0, 255, (H // 4, W // 4), dtype=np.int16).repeat(4, 0).repeat(4, 1)[..., None].repeat(3, 2)
        img = (img * (1 - min(1, q * 1.6)) + static * min(1, q * 1.6)).astype(np.int16)
        img = (img * (1 - max(0, (q - 0.55) / 0.45))).astype(np.int16)
    img = np.clip(img, 0, 255).astype(np.uint8)
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    # system text
    if 0.25 < p < 0.9 and (k // 3) % 3 != 0:
        jitter = int(rng.normal(0, 6 * g))
        d.rectangle([60, 250 + jitter, 1020, 430 + jitter], fill=(0, 0, 0))
        d.text((90, 270 + jitter), "GRAFİK MOTORU: 2D → 3D", font=f_mid, fill=(0, 255, 200))
        bars = int(min(1, (p - 0.25) / 0.6) * 10)
        d.text((90, 340 + jitter), "YENİ SEZON YÜKLENİYOR " + "█" * bars + "░" * (10 - bars), font=f_mid, fill=(255, 230, 0))
    if 0.55 < p < 0.82 and rng.random() < 0.5:
        d.text((W // 2 - 260, H // 2 - 40), "SİNYAL HATASI", font=f_big, fill=(255, 40, 80))
    im.save(f"{out_dir}/g_{k:03d}.jpg", quality=93)

# ---- audio: stutter + bitcrush + tape stop over the old finale audio ----
with wave.open(old_wav) as w:
    sr, ch = w.getframerate(), w.getnchannels()
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
a = a.reshape(-1, ch).mean(1)
dur = N / 30.0
seg = a[int(56.4 * sr): int((56.4 + dur) * sr)]
out = seg.copy(); n = len(out)
# stutters
for s in (0.55, 0.8, 1.0, 1.15):
    i = int(s * sr); L = int(0.07 * sr)
    for rep in range(3): out[i + rep * L: i + (rep + 1) * L] = seg[i: i + L]
# bitcrush ramp
t = np.arange(n) / sr
crush = np.clip((t - 0.3) / 1.4, 0, 1)
q = np.round(out * (2 ** (12 - 9 * crush))) / (2 ** (12 - 9 * crush))
hold = np.maximum(1, (1 + crush * 14).astype(int))
idx = (np.arange(n) // hold) * hold
out = q[np.minimum(idx, n - 1)]
# digital noise bursts and blips
for s in rng.uniform(0.4, 2.0, 14):
    i = int(s * sr); L = int(rng.uniform(0.02, 0.08) * sr)
    out[i:i + L] += rng.uniform(-0.5, 0.5, min(L, n - i)).astype(np.float32)
for s in rng.uniform(0.5, 2.0, 8):
    i = int(s * sr); L = int(0.05 * sr); f = rng.uniform(800, 3000)
    out[i:i + L] += (0.3 * np.sign(np.sin(2 * np.pi * f * np.arange(min(L, n - i)) / sr))).astype(np.float32)
# tape stop: resample with slowing rate over last 0.8s
ts = int((dur - 0.9) * sr)
tail = out[ts:].copy(); m = len(tail)
rate = np.linspace(1.0, 0.05, m); pos = np.cumsum(rate); pos = np.clip(pos, 0, m - 1)
out[ts:] = np.interp(pos, np.arange(m), tail) * np.linspace(1, 0, m)
# static hiss at the end
st0 = int((dur - 0.5) * sr); out[st0:] += rng.uniform(-0.15, 0.15, n - st0).astype(np.float32) * np.linspace(1, 0, n - st0)
out = np.clip(out, -1, 1)
with wave.open(out_wav, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((out * 32767).astype(np.int16).tobytes())
print("frames", N, "audio", round(n / sr, 2))
