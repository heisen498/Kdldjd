# Music bed + sound effects + voice-over mix for the 'Paspaslı Diplomat 4' reels (all synthesized, no samples).
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
Cmaj7 = (60, 64, 71)
for k in range(30): add(mus, sine(2400 - k * 60, 0.06, 30), 0.1 + k * 0.08, 0.15)        # tape rewind chirps
for i, m in enumerate((60, 64, 67, 72)): add(mus, saw(NOTE(m), 0.4 if i < 3 else 1.0, 1.4), 2.6 + i * 0.12, 0.4)
groove(5.6, 16.6, 100, [C, Am, F, G], drums=True, vol=0.36)
for i, m in enumerate((60, 64, 67, 72, 76)): add(mus, saw(NOTE(m), 0.35 if i < 4 else 1.0, 1.4), 19.1 + i * 0.1, 0.4)   # ta-da
groove(20.0, 22.2, 100, [C, G], drums=False, vol=0.32)
groove(22.2, 30.8, 108, [Dm, Am, Dm, E], drums=False, vol=0.4, stacc=True)
groove(30.8, 36.6, 100, [F, C, G, Am], drums=False, vol=0.32)
groove(36.6, 41.8, 120, [C, G, Am, F], drums=True, vol=0.48)
add(mus, pad([NOTE(m) for m in (57, 60, 64)], 2.0, 3.0), 41.8, 0.4)
for i, (tt, m) in enumerate([(43.5, 45), (43.95, 44), (44.45, 43)]):
    add(mus, sum(saw(NOTE(m + d), 1.2 if i < 2 else 1.8, 1.0 if i < 2 else 0.6) for d in (0, 7, 12)) / 3, tt, 0.8)
add(mus, pad([NOTE(m) for m in (48, 55, 64, 71)], 9.6, 0.5), 46.2, 0.55)                   # space ambient
for k in range(14): add(mus, pl((72, 71, 67, 64, 67, 71, 72, 76)[k % 8], 1.2, 0.4), 46.6 + k * 0.62, 0.22)
add(mus, sum(saw(NOTE(m), 1.6, 0.8) for m in (50, 57, 62, 65)) / 4, 55.9, 0.8)
for i, m in enumerate((48, 55, 60, 64, 67, 72)): add(mus, pl(m, 2.0, 0.5), 58.8 + i * 0.03, 0.45)

fx = np.zeros(N, np.float32)
for c in [4.4, 10, 16.6, 22.2, 30.8, 36.6, 41.8, 46.2, 55.8]:
    add(fx, noise(0.35, 2000, 6) * np.linspace(0, 1, T(0.35)) ** 2, c - 0.3, 0.25)
hiss = noise(41.8, 5000, 0.0)
add(fx, hiss * 0.12, 4.4, 0.25)                                                           # tape hiss (flashback)
bt = np.arange(T(1.4)) / SR
bell = (np.sin(2 * np.pi * 1050 * bt) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 22 * bt))) * np.exp(-bt * 1.2)).astype(np.float32)
add(fx, bell, 4.5, 0.25)                                                                  # school bell
for k in range(12): add(fx, sine(2200 + 200 * (k % 3), 0.07, 30), 11.0 + k * 0.28, 0.1)  # board squeaks
for k in range(8): add(fx, sine(1760 + (k % 4) * 220, 0.5, 6), 12.2 + k * 0.4, 0.1)        # shine chimes
add(fx, sine(110, 0.15, 25, 70), 16.75, 0.7); add(fx, sine(110, 0.15, 25, 70), 17.0, 0.7)  # knock knock
for k in range(22): add(fx, sine(2400, 0.03, 120), 22.4 + k * 0.38, 0.12)                # thinking ticks
for i in range(6): add(fx, sine(500, 0.12, 20, 1100), 22.8 + i * 0.7, 0.25)              # item pops
for k in range(7): add(fx, noise(0.16, 2500, 16), 30.9 + k * 0.28, 0.3)                  # paper folding
pw = lowpass(noise(2.4, 1500, 0.3), 1500) * np.sin(np.linspace(0, np.pi, T(2.4)))
add(fx, pw, 32.8, 0.45)                                                                   # plane glides
add(fx, noise(0.5, 1200, 7), 35.2, 0.6); add(fx, sine(300, 0.25, 10, 900), 35.2, 0.3)     # ŞLAP
add(fx, lowpass(noise(1.8, 3500, 1.5), 3500), 39.2, 0.5)                                 # graduation cheer
for i in range(4): add(fx, noise(0.3, 2500, 8), 39.25 + i * 0.07, 0.2)                    # caps whoosh
for k in range(4): add(fx, noise(0.25, 700, 10), 42.0 + k * 0.4, 0.2)                     # sniffles
add(fx, sine(180, 0.4, 8, 60), 43.7, 0.6)                                                 # faint thud
add(fx, sine(1320, 0.4, 6), 44.2, 0.3)                                                    # counter ding
for k in range(10): add(fx, sine(1500 if k % 2 else 1200, 0.08, 20), 46.5 + k * 0.9, 0.12)  # station beeps
add(fx, lowpass(noise(1.2, 800, 1.6), 800) * np.linspace(1, 0.2, T(1.2)), 51.0, 0.35)     # sigh
add(fx, noise(1.2, 5000, 2.5), 55.85, 0.25)

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
