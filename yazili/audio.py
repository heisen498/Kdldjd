# Music bed + sound effects + voice-over mix for the 'Paspaslı Diplomat 5' reels (all synthesized, no samples).
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
for i, m in enumerate((60, 64, 67, 72)): add(mus, saw(NOTE(m), 0.4 if i < 3 else 1.0, 1.4), 0.3 + i * 0.12, 0.4)
groove(1.0, 4.2, 120, [C, G, C, G], drums=True, vol=0.4, stacc=True)
groove(5.6, 9.2, 112, [Am, E], drums=False, vol=0.38, stacc=True)
groove(9.2, 15.2, 104, [C, F, G, C], drums=True, vol=0.36)
def daysting(tt):
    for i, m in enumerate((72, 76, 79, 84)): add(mus, pl(m, 0.5, 0.8), tt + i * 0.07, 0.35)
for tt in (15.2, 18.6, 22.0, 29.4): daysting(tt)
groove(15.6, 18.6, 116, [C, G], drums=True, vol=0.34)
groove(18.9, 22.0, 116, [F, C], drums=True, vol=0.34)
groove(22.3, 29.4, 100, [Dm, Am], drums=False, vol=0.32, stacc=True)
groove(29.7, 32.8, 116, [Am, E], drums=False, vol=0.34, stacc=True)
groove(32.8, 41.2, 96, [Dm, Dm, Bb, E], drums=False, vol=0.38, stacc=True)
for i, m in enumerate((60, 64, 67, 72, 76)): add(mus, saw(NOTE(m), 0.35 if i < 4 else 1.0, 1.4), 39.2 + i * 0.1, 0.4)   # ta-da
for k in range(16): add(mus, noise(0.06, 900, 40), 41.25 + 0.55 * (1 - (1 - k / 16) ** 1.6), 0.45)                   # drumroll
groove(42.0, 50.6, 128, [C, G, Am, F], drums=True, vol=0.5)
add(mus, pad([NOTE(m) for m in (57, 60, 64)], 3.0, 3.0), 50.6, 0.3)
groove(54.0, 55.8, 120, [C, G], drums=True, vol=0.4)
add(mus, sum(saw(NOTE(m), 1.6, 0.8) for m in (50, 57, 62, 65)) / 4, 55.9, 0.8)
for i, m in enumerate((48, 55, 60, 64, 67, 72)): add(mus, pl(m, 2.0, 0.5), 58.8 + i * 0.03, 0.45)

fx = np.zeros(N, np.float32)
for c in [4.2, 9.2, 15.2, 18.6, 22.0, 29.4, 32.8, 41.2, 47.4, 50.6, 55.8]:
    add(fx, noise(0.35, 2000, 6) * np.linspace(0, 1, T(0.35)) ** 2, c - 0.3, 0.25)
add(fx, noise(51.6, 5000, 0.0) * 0.12, 4.2, 0.25)                                         # tape hiss
for k in range(14): add(fx, sine(2200, 0.06, 30), 4.25 + k * 0.1, 0.2)                    # alarm clock
eng = lowpass(rng.uniform(-1, 1, T(1.8)).astype(np.float32), 140) * 3
add(fx, eng * np.linspace(1, 0.3, len(eng)), 9.2, 0.45)
add(fx, noise(0.6, 4500, 4), 10.8, 0.3); add(fx, noise(0.4, 3500, 6), 11.0, 0.3)           # brakes + door hiss
for i, m in enumerate((84, 88, 91, 96)): add(fx, sine(NOTE(m), 0.6, 4), 11.2 + i * 0.08, 0.12)  # wish chime
rumble = lowpass(rng.uniform(-1, 1, T(17.6)).astype(np.float32), 110) * 2.5
add(fx, rumble * env(len(rumble), 0.5, 0.5), 15.2, 0.3)                                   # bus interior
add(fx, sine(1320, 0.6, 4), 16.5, 0.25); add(fx, sine(600, 0.4, 3, 1200), 16.7, 0.2)      # sun ding + whistle
add(fx, sine(220, 0.5, 3, 660) * np.sin(np.linspace(0, 60, T(0.5))), 20.0, 0.3)          # boing
add(fx, sine(2500, 0.04, 80), 24.2, 0.3); add(fx, sine(2500, 0.04, 80), 24.36, 0.3)        # tsk tsk
th = np.arange(T(2.0)) / SR
add(fx, (np.sin(2 * np.pi * (700 + 120 * np.sin(2 * np.pi * 6 * th)) * th) * 0.5).astype(np.float32) * env(len(th), 0.2, 0.3), 30.4, 0.25)   # UFO theremin
add(fx, sine(300, 0.7, 2, 1800), 31.8, 0.3)                                               # UFO zooms away
for k in range(24): add(fx, sine(2400, 0.03, 120), 33.0 + k * 0.32, 0.12)                # exam clock
add(fx, sine(1568, 0.6, 4), 35.2, 0.35); add(fx, sine(2093, 0.6, 4), 35.3, 0.3)            # lightbulb
for k in range(8): add(fx, sine(NOTE(72 + k * 2), 0.3, 8), 35.8 + k * 0.05, 0.12)          # harp gliss
for k in range(9): add(fx, noise(0.07, 3500, 40), 38.2 + k * 0.11, 0.25)                   # scribble
add(fx, sine(120, 0.3, 14, 60), 41.8, 0.8)                                                 # stamp 50
add(fx, lowpass(noise(2.5, 3500, 1.2), 3500), 43.6, 0.5)                                   # crowd cheer
for tt in (47.5, 47.8): add(fx, horn(330, 415, 0.22, 0.25), tt)                           # DIT DIT
add(fx, sine(900, 0.6, 1, 300), 51.4, 0.3); add(fx, sine(300, 0.6, 1, 900), 52.0, 0.3); add(fx, sine(900, 0.6, 1, 400), 52.6, 0.3)   # wobble whistles
add(fx, sine(1320, 0.5, 5), 53.8, 0.35); add(fx, sine(1760, 0.6, 4), 53.95, 0.3)          # relief ding
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
