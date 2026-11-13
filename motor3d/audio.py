# Music bed + sound effects + voice-over mix for the 'Paspaslı Diplomat' S2B1 reels (all synthesized, no samples).
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
def bassline(t0, t1, notes, step=0.3, g=0.5):
    t = t0; i = 0
    while t < t1: add(mus, sine(NOTE(notes[i % len(notes)] - 24), step * 0.9, 6), t, g); t += step; i += 1
# title: low drone + timpani + brass hit
add(mus, pad([NOTE(m) for m in (38, 45, 50)], 4.6, 0.5), 0.0, 0.5)
for tt in (0.3, 0.9, 1.2, 1.5): timp(tt, 60, 0.7)
brass(1.6, (50, 57, 62, 65), 2.4, 0.42)
# empty vitrine: suspense
add(mus, pad([NOTE(m) for m in (38, 44, 50)], 6.6, 1.0), 4.6, 0.5)
for k in range(10): add(mus, pl(74 + (k % 2), 0.4, 0.8), 5.0 + k * 0.6, 0.2)
# investigation: heist bass + staccato
bassline(11.2, 21.2, [50, 50, 53, 50, 55, 53, 50, 48], 0.3, 0.55)
groove(12.0, 21.2, 100, [Dm, Dm, Bb, E], drums=True, vol=0.3, stacc=True)
for k in range(12): add(mus, pl(84 + (k * 5) % 12, 1.0, 0.9), 18.45 + k * 0.08, 0.25)       # sparkle on 'uzay tozu'
# CCTV: eerie drone
add(mus, pad([NOTE(m) for m in (40, 46, 52)], 7.2, 3.5), 21.4, 0.45)
# remembering: melancholic plucks
for k, m in enumerate((69, 67, 64, 62, 64, 60, 62, 57, 60, 64, 62, 57)): add(mus, pl(m, 1.4, 0.4), 28.8 + k * 0.52, 0.3)
add(mus, pad([NOTE(m) for m in (57, 60, 64)], 6.8, 0.4), 28.6, 0.3)
# station: wonder pad
add(mus, pad([NOTE(m) for m in (48, 55, 64, 71)], 8.4, 0.6), 35.4, 0.5)
for k in range(12): add(mus, pl((72, 76, 79, 83)[k % 4], 1.2, 0.5), 35.6 + k * 0.68, 0.18)
# heroic rise
bassline(43.8, 50.2, [50, 50, 53, 55, 57, 58, 60, 62], 0.4, 0.5)
for i, tt in enumerate((44.0, 45.6, 47.2, 48.8)): brass(tt, tuple(m + i * 2 for m in (50, 57, 62)), 1.4, 0.35); timp(tt, 62 + i * 4, 0.6)
# launch: epic swell
add(mus, pad([NOTE(m) for m in (38, 45, 50, 57, 62)], 9.8, 0.3), 50.2, 0.6)
for tt in (50.3, 52.3, 54.3, 56.3): timp(tt, 58, 0.8); brass(tt + 0.05, (50, 57, 62, 66), 1.8, 0.33)
for i, m in enumerate((50, 57, 62, 66, 69, 74)): add(mus, pl(m, 2.0, 0.5), 58.4 + i * 0.03, 0.4)

fx = np.zeros(N, np.float32)
for c in [4.6, 11.2, 21.4, 28.6, 35.4, 43.8, 50.2]: add(fx, lowpass(noise(0.6, 900, 4), 900) * np.linspace(0, 1, T(0.6)), c - 0.5, 0.35)   # deep whooshes
st = np.arange(T(14.4)) / SR
siren = (np.sin(2 * np.pi * np.cumsum(650 + 220 * np.sin(2 * np.pi * 0.9 * st)) / SR) * 0.4).astype(np.float32) * env(len(st), 0.3, 0.6)
add(fx, siren, 7.0, 0.14)                                                                 # alarm siren
add(fx, noise(0.4, 4000, 8), 7.0, 0.3)
for k in range(10): add(fx, sine(110, 0.12, 25, 70), 11.25 + k * 0.17, 0.4)             # running steps
add(fx, noise(0.3, 1500, 12), 13.9, 0.3)                                                  # kneel rustle
for k in range(16): add(fx, sine(2600 + (k * 311) % 1800, 0.5, 6), 18.4 + k * 0.07, 0.07)   # sparkle shimmer
hum = lowpass(rng.uniform(-1, 1, T(7.2)).astype(np.float32), 200) * 1.5 + 0.05 * np.sin(2 * np.pi * 60 * np.arange(T(7.2)) / SR).astype(np.float32)
add(fx, hum, 21.4, 0.3); add(fx, noise(7.2, 5000, 0.0) * 0.25, 21.4, 0.25)                # CCTV hum + static
add(fx, sine(300, 1.6, 1.0, 900), 24.6, 0.12)                                            # float whoosh
for k in range(3): add(fx, sine(1700, 0.08, 20), 35.5 + k * 0.25, 0.25)                  # call connect blips
vent = lowpass(rng.uniform(-1, 1, T(8.4)).astype(np.float32), 400) * 1.2
add(fx, vent * env(len(vent), 0.4, 0.4), 35.4, 0.2)                                       # station vent
add(fx, noise(0.3, 1200, 10), 45.6, 0.35); add(fx, sine(260, 0.25, 12, 180), 46.1, 0.4)   # bucket on head (thunk)
add(fx, noise(0.4, 2500, 8), 46.9, 0.3)                                                   # mop swing
rum = lowpass(rng.uniform(-1, 1, T(9.8)).astype(np.float32), 90) * 3.5
add(fx, rum * np.linspace(0.3, 1, len(rum)).astype(np.float32), 50.2, 0.45)              # rocket rumble
add(fx, lowpass(noise(9.0, 2500, 0.0), 2500) * 0.4, 50.6, 0.2)                            # steam hiss

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
