# Music bed + sound effects + voice-over mix for the 'Paspaslı Diplomat' season 1 finale reels (all synthesized, no samples).
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


def saw(f, dur, decay=1.5):
    t = np.arange(int(dur * SR)) / SR
    x = (2 * ((t * f) % 1) - 1) + 0.6 * (2 * ((t * f * 1.005) % 1) - 1)
    return lowpass(x.astype(np.float32), 900) * np.exp(-t * decay) * env(len(t), 0.02, 0.2)

def pad(freqs, dur, vib=5.0):
    t = np.arange(int(dur * SR)) / SR
    x = sum(np.sin(2 * np.pi * f * t + 0.004 * f * np.sin(2 * np.pi * vib * t)) for f in freqs)
    return (x / len(freqs)).astype(np.float32) * env(len(t), 0.6, 0.8)

NOTE = lambda m: 440 * 2 ** ((m - 69) / 12)
cache = {}
def pl(m, dur=0.6, b=0.5):
    k = (m, dur, b)
    if k not in cache: cache[k] = pluck(NOTE(m), dur, b)
    return cache[k]

mus = np.zeros(N, np.float32)
def groove(t0, t1, bpm, chords, drums=True, vol=0.5, pattern=(0, 2, 1, 2, 3, 2, 1, 2), stacc=False):
    beat = 60 / bpm; t = t0; bar = 0
    while t < t1 - 0.05:
        ch = chords[bar % len(chords)]
        tones = [ch[0], ch[1], ch[2], ch[0] + 12]
        for e in range(8):
            tt = t + e * beat / 2
            if tt >= t1: break
            add(mus, pl(tones[pattern[e]], 0.35 if stacc else 0.8, 0.6), tt, vol)
        for b4 in range(4):
            tb = t + b4 * beat
            if tb >= t1: break
            add(mus, sine(NOTE(ch[0] - 24), 0.35 if stacc else 0.5, 7), tb, 0.45)
            if drums:
                if b4 in (0, 2): add(mus, sine(110, 0.18, 18, 45), tb, 0.55)
                else: add(mus, noise(0.12, 1200, 30) * 0.5, tb, 0.25)
                add(mus, noise(0.04, 7000, 80), tb + beat / 2, 0.12)
        t += beat * 4; bar += 1

Am, Dm, E, C, G, F, Bb = (57, 60, 64), (62, 65, 69), (64, 68, 71), (60, 64, 67), (55, 59, 62), (53, 57, 60), (58, 62, 65)
def timp(tt, f=65, g=0.8): add(mus, sine(f, 0.9, 4, f * 0.8), tt, g)
def brass(tt, notes, dur=1.0, g=0.4):
    for i, m in enumerate(notes): add(mus, saw(NOTE(m), dur, 1.0), tt + i * 0.015, g)
for tt in (0.2, 0.7, 1.2): timp(tt)
brass(0.4, (48, 55, 60, 64), 1.2); brass(1.6, (50, 57, 62, 65), 1.0); brass(2.6, (55, 59, 62, 67), 1.6, 0.45)
groove(4.4, 11.0, 96, [Am, F, C, G], drums=False, vol=0.34, pattern=(0, 1, 2, 3, 2, 1, 0, 1))
groove(11.0, 17.2, 112, [C, F, G, C], drums=True, vol=0.36)
for k in range(10): add(mus, pl(84 + (k * 5) % 12, 0.8, 0.9), 11.3 + k * 0.5, 0.2)
add(mus, pad([NOTE(m) for m in (38, 45, 50)], 6.0, 2.0), 17.3, 0.55)
groove(23.4, 30.8, 132, [Dm, Bb, C, Dm], drums=True, vol=0.36, stacc=True)
groove(31.2, 37.2, 100, [Am, Dm, E, Am], drums=False, vol=0.36, stacc=True)
groove(37.2, 44.2, 124, [C, G, Am, F], drums=True, vol=0.46)
add(mus, pad([NOTE(m) for m in (38, 45, 50, 53)], 6.4, 6.0), 44.4, 0.45)
groove(50.8, 55.0, 150, [Dm, Dm, Bb, C], drums=True, vol=0.5)
for tt in (55.0, 55.5): timp(tt, 60, 0.9)
brass(55.1, (48, 55, 60, 64, 67), 2.4, 0.38); brass(57.4, (53, 60, 65, 69), 2.4, 0.34)
for i, m in enumerate((48, 55, 60, 64, 67, 72)): add(mus, pl(m, 2.0, 0.5), 59.0 + i * 0.03, 0.4)

fx = np.zeros(N, np.float32)
for c in [4.4, 11, 17.2, 23.4, 30.8, 37.2, 44.2, 50.8, 55]:
    add(fx, noise(0.35, 2000, 6) * np.linspace(0, 1, T(0.35)) ** 2, c - 0.3, 0.25)
add(fx, noise(32.8, 5000, 0.0) * 0.12, 4.4, 0.25)                                         # tape hiss
wind = lowpass(rng.uniform(-1, 1, T(6.4)).astype(np.float32), 400) * (0.6 + 0.4 * np.sin(np.linspace(0, 9, T(6.4)))).astype(np.float32)
add(fx, wind * env(len(wind), 0.5, 0.5), 4.5, 0.3)
add(fx, saw(140, 0.5, 4), 6.0, 0.15)                                                      # sign creak
add(fx, sine(500, 0.12, 20, 1100), 7.2, 0.3)                                              # ? pop
for k in range(30): add(fx, noise(0.03, 4000, 90), 11.2 + k * 0.19 + (k % 3) * 0.02, 0.25)  # typing
for k in range(18): add(fx, sine(2400, 0.03, 120), 17.4 + k * 0.33, 0.14)                # clock ticks
for k in range(8): add(fx, sine(70, 0.12, 25), 17.5 + k * 0.5, 0.55); add(fx, sine(60, 0.1, 30), 17.65 + k * 0.5, 0.4)
add(fx, lowpass(noise(1.4, 600, 0.8), 600), 20.8, 0.4)                                   # slow-mo whoosh
add(fx, noise(0.5, 1200, 7), 21.8, 0.7); add(fx, sine(300, 0.25, 10, 900), 21.8, 0.35)    # ŞLAP
zt = np.arange(T(3.4)) / SR
zap = (np.sign(np.sin(2 * np.pi * 120 * zt)) * (rng.uniform(0, 1, len(zt)) > 0.55)).astype(np.float32) * np.exp(-zt * 0.6)
add(fx, lowpass(zap, 3000), 23.6, 0.35)                                                   # short circuit crackle
for k in range(10): add(fx, sine(1800 + (k * 377) % 1500, 0.05, 40), 24.2 + k * 0.33, 0.15)   # glitch blips
add(fx, sine(1320, 0.5, 5), 28.0, 0.35); add(fx, sine(1760, 0.6, 4), 28.15, 0.3)           # saved ding
for k in range(4): add(fx, sine(2000, 0.12, 10), 28.4 + k * 0.3, 0.2)                     # 00:00 beeps
add(fx, noise(0.5, 5000, 8), 32.4, 0.45); add(fx, sine(2600, 0.3, 14), 32.4, 0.2)          # tea glass
for k in range(3): add(fx, sine(220, 0.4, 3, 660) * np.sin(np.linspace(0, 50, T(0.4))), 33.6 + k * 0.25, 0.2)
for i in range(6): add(fx, noise(0.3, 2500, 8) * np.linspace(0, 1, T(0.3)), 37.4 + i * 0.45, 0.2)   # tile whooshes
rt = np.arange(T(0.8)) / SR
ring = ((np.sin(2 * np.pi * 1400 * rt) + np.sin(2 * np.pi * 1750 * rt)) * (np.sin(2 * np.pi * 20 * rt) > 0)).astype(np.float32) * 0.5
for tt in (45.0, 46.1): add(fx, ring, tt, 0.25)                                            # phone ringing
for k in range(6): add(fx, sine(880, 0.25, 2, 660), 45.4 + k * 0.5, 0.15)                 # alarm
for k in range(18): add(fx, sine(90, 0.08, 40), 50.9 + k * 0.22, 0.35)                    # running steps
add(fx, lowpass(noise(2.0, 500, 0.8), 500), 55.2, 0.5)                                    # bucket-signal whoom
add(fx, noise(1.6, 5000, 2.0), 55.0, 0.25)

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
