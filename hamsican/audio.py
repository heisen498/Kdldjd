# Music bed + sound effects + voice-over mix for the Hamsican reels (all synthesized, no samples).
# Usage: python3 audio.py <voice.wav> <out.wav>
import sys, wave
import numpy as np

SR, DUR = 44100, 60.0
N = int(SR * DUR)
rng = np.random.default_rng(7)
T = lambda s: int(s * SR)

def read_wav(p):
    with wave.open(p) as w:
        sr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        x = np.frombuffer(w.readframes(n), np.int16).astype(np.float32) / 32768
    if ch > 1: x = x.reshape(-1, ch).mean(1)
    if sr != SR: x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x)
    return x

def add(buf, x, t, g=1.0):
    i = T(t); j = min(len(buf), i + len(x))
    if i < len(buf): buf[i:j] += x[: j - i] * g

def lowpass(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); s = 0.0
    for i in range(len(x)): s = (1 - a) * x[i] + a * s; y[i] = s
    return y

def pluck(f, dur=1.2, bright=0.5):
    n = int(dur * SR); p = max(2, int(SR / f))
    buf = rng.uniform(-1, 1, p).astype(np.float32)
    buf = lowpass(buf, 2000 + 6000 * bright)
    out = np.empty(n, np.float32)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = 0.996 * 0.5 * (buf[i % p] + buf[(i + 1) % p])
    return out * np.exp(-np.arange(n) / SR * 2.2)

def sine(f, dur, decay=4.0, f2=None):
    t = np.arange(int(dur * SR)) / SR
    fr = f if f2 is None else f + (f2 - f) * t / dur
    ph = 2 * np.pi * np.cumsum(np.full_like(t, 1.0) * fr) / SR
    return (np.sin(ph) * np.exp(-t * decay)).astype(np.float32)

def noise(dur, fc=3000, decay=20.0):
    x = rng.uniform(-1, 1, int(dur * SR)).astype(np.float32)
    x = x - lowpass(x, fc) if fc > 2500 else lowpass(x, fc)
    return x * np.exp(-np.arange(len(x)) / SR * decay)

def env(n, a=0.01, r=0.05):
    e = np.ones(n, np.float32); na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na); e[-nr:] = np.linspace(1, 0, nr); return e

def horn(f1, f2, dur, g=0.25):
    t = np.arange(int(dur * SR)) / SR
    x = np.sign(np.sin(2 * np.pi * f1 * t)) + np.sign(np.sin(2 * np.pi * f2 * t))
    return lowpass(x.astype(np.float32) * 0.5, 1800) * env(len(t), 0.02, 0.08) * g

# ---------------- music ----------------
mus = np.zeros(N, np.float32)
NOTE = lambda m: 440 * 2 ** ((m - 69) / 12)
chords = [(60, 64, 67), (55, 59, 62), (57, 60, 64), (53, 57, 60)]  # C G Am F
BEAT = 0.6; BAR = BEAT * 4
cache = {}
def pl(m, dur=1.1, b=0.5):
    k = (m, dur, b)
    if k not in cache: cache[k] = pluck(NOTE(m), dur, b)
    return cache[k]
pattern = [0, 2, 1, 2, 0, 2, 1, 2]
bar = 0; t = 0.15
while t < 59.0:
    r, th, fi = chords[bar % 4]
    tones = [r, th, fi, r + 12]
    night = 34.0 <= t < 40.2
    intro = t < 4.0
    vol = 0.35 if night else 0.55
    for e8 in range(8):
        tt = t + e8 * BEAT / 2
        if tt > 58.6: break
        m = tones[[0, 2, 3, 1, 2, 3, 1, 2][e8]] + (0 if not night else -12 + 12)
        add(mus, pl(m, 0.9, 0.35 if night else 0.55), tt, vol * (0.9 if e8 % 2 else 1.0))
    # bass
    for b4 in (0, 2):
        tb = t + b4 * BEAT
        add(mus, sine(NOTE(r - 24), 0.55, 5.0), tb, 0.45 if not night else 0.3)
    # drums (not at night / intro)
    if not night and not intro:
        for b4 in range(4):
            tb = t + b4 * BEAT
            if b4 in (0, 2): add(mus, sine(110, 0.18, 18, 45), tb, 0.55)
            else: add(mus, noise(0.12, 1200, 30) * 0.5, tb, 0.25)  # soft snare-ish
            add(mus, noise(0.04, 7000, 80), tb + BEAT / 2, 0.12)   # hat
    bar += 1; t += BAR
# final strum
for i, m in enumerate((48, 55, 60, 64, 67, 72)): add(mus, pl(m, 2.2, 0.5), 58.7 + i * 0.03, 0.4)

# ---------------- sfx ----------------
fx = np.zeros(N, np.float32)
cuts = [4, 14, 18.4, 23.4, 28.8, 34, 37.2, 40.2, 44.8, 50.6, 53.2]
for c in cuts:
    w = noise(0.35, 2000, 6) * np.linspace(0, 1, T(0.35)) ** 2
    add(fx, w, c - 0.3, 0.25)
for i in range(6): add(fx, noise(0.25, 1500, 10), 5.0 + i * 0.85, 0.25)            # packages flying
add(fx, sine(300, 0.2, 10, 900), 12.45, 0.4)                                        # pop!
add(fx, horn(220, 277, 0.9), 14.25)                                                 # bus horn
eng = lowpass(rng.uniform(-1, 1, T(4.0)).astype(np.float32), 120) * 3
add(fx, eng * np.linspace(0.2, 1, len(eng)), 15.2, 0.5)                             # bus pulls away
for k in range(14): add(fx, sine(90, 0.08, 40), 14.4 + k * 0.17, 0.35)              # running steps
traffic = lowpass(rng.uniform(-1, 1, T(5.0)).astype(np.float32), 200) * 2
add(fx, traffic * env(len(traffic), 0.4, 0.4), 18.4, 0.35)
for tt in (19.4, 20.5, 20.75): add(fx, horn(349, 440, 0.3, 0.2), tt)
for k in range(18): add(fx, sine(2400, 0.03, 120), 19.0 + k * 0.15, 0.25)           # clock ticks
add(fx, sine(523, 0.15, 12), 20.8, 0.3); add(fx, sine(784, 0.25, 8), 20.95, 0.3)     # "+1 saat" sting
add(fx, eng * np.linspace(0.3, 1, len(eng)), 30.6, 0.45)                             # bus leaving rest stop
add(fx, sine(880, 0.3, 6, 1320), 30.7, 0.25)                                         # "!" sting
for k in range(13): add(fx, sine(90, 0.08, 40), 31.4 + k * 0.17, 0.35)
night = lowpass(rng.uniform(-1, 1, T(3.2)).astype(np.float32), 90) * 3
add(fx, night * env(len(night), 0.3, 0.3), 34.0, 0.35)
sn = lowpass(rng.uniform(-1, 1, T(3.0)).astype(np.float32), 400)
sn *= (0.5 + 0.5 * np.sin(2 * np.pi * 0.6 * np.arange(len(sn)) / SR)) ** 3
add(fx, sn * env(len(sn), 0.2, 0.3), 37.2, 0.5)                                      # snore
cheer = lowpass(noise(1.0, 3500, 2.5), 3500)
add(fx, cheer, 48.3, 0.5)                                                            # friends cheer
for f in (1320, 2640): add(fx, sine(f, 1.2, 3), 50.85, 0.18)                         # ding
add(fx, sine(392, 0.3, 6, 196), 49.0, 0.25)                                          # sad trombone-ish

# ---------------- voice + ducking ----------------
v = read_wav(sys.argv[1]); voice = np.zeros(N, np.float32); voice[: min(N, len(v))] = v[:N]
e = np.abs(voice); k = int(0.12 * SR)
e = np.convolve(e, np.ones(k) / k, mode="same")
duck = 1 - 0.6 * np.clip(e / 0.05, 0, 1)
duck = np.convolve(duck, np.ones(k) / k, mode="same")
mix = mus * 0.36 * duck + fx * 0.8 + voice * 1.0
fade = np.ones(N, np.float32); fade[-T(0.8):] = np.linspace(1, 0, T(0.8))
mix *= fade
mix /= max(1e-6, np.abs(mix).max()) / 0.95
st = np.stack([mix, mix], 1)
with wave.open(sys.argv[2], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
print("ok")
