# Music bed + sound effects + voice-over mix for the 'Paspaslı Diplomat' reels (all synthesized, no samples).
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

Am, Dm, E, C, G, F = (57, 60, 64), (62, 65, 69), (64, 68, 71), (60, 64, 67), (55, 59, 62), (53, 57, 60)
groove(0.2, 11.3, 112, [Am, Dm, E, Am], drums=False, vol=0.5, stacc=True)            # sneaky pizzicato
for i, (a, b) in enumerate([(11.3, 14.8), (14.6, 18.3)]):                            # heavenly choir
    add(mus, pad([NOTE(m) for m in ((60, 64, 67, 72) if i == 0 else (65, 69, 72, 77))], b - a), a, 0.5)
for k in range(16): add(mus, pl(84 + (k * 5) % 12, 0.8, 0.9), 11.5 + k * 0.42, 0.25)  # sparkles
groove(18.2, 19.6, 112, [C, G], drums=False, vol=0.45, stacc=True)
for i, (tt, m) in enumerate([(19.65, 45), (20.15, 44), (20.7, 43)]):                # dun dun dunnn
    add(mus, sum(saw(NOTE(m + d), 1.4 if i < 2 else 2.2, 1.0 if i < 2 else 0.6) for d in (0, 7, 12)) / 3, tt, 0.9)
groove(22.6, 25.2, 112, [Am, E], drums=False, vol=0.4, stacc=True)
groove(25.2, 38.4, 126, [C, G, Am, F], drums=True, vol=0.5)                          # montage
for k in range(24): add(mus, noise(0.06, 900, 40), 38.4 + 1.9 * (1 - (1 - k / 24) ** 1.6), 0.5)   # drumroll
for i, m in enumerate((60, 64, 67, 72)): add(mus, saw(NOTE(m), 0.5 if i < 3 else 1.6, 1.2), 40.3 + i * 0.14, 0.5)  # fanfare
groove(40.9, 45.2, 126, [C, F, G, C], drums=True, vol=0.5)
groove(45.2, 49.6, 96, [Dm, Dm, Am, E], drums=False, vol=0.45, stacc=True)            # tense summit
add(mus, pad([NOTE(m) for m in (60, 64, 67, 72)], 2.2), 49.6, 0.45)
groove(50.4, 58.8, 120, [F, G, C, Am], drums=True, vol=0.5)
for i, m in enumerate((48, 55, 60, 64, 67, 72)): add(mus, pl(m, 2.2, 0.5), 58.8 + i * 0.03, 0.45)

# ---------------- sfx ----------------
fx = np.zeros(N, np.float32)
for c in [4.1, 11.3, 18.2, 25.2, 32.4, 38.4, 45.2, 53.6]:
    add(fx, noise(0.35, 2000, 6) * np.linspace(0, 1, T(0.35)) ** 2, c - 0.3, 0.25)
for i in range(7): add(fx, sine(700, 0.22, 12, 160), 5.1 + i * 0.85, 0.45)             # BONK
add(fx, sine(300, 1.6, 1.2, 1400), 9.4, 0.3)                                          # soul leaves
add(fx, sine(180, 0.4, 8, 60), 20.6, 0.6)                                             # faint thud
add(fx, noise(0.5, 5000, 8), 21.5, 0.5); add(fx, sine(2600, 0.3, 14), 21.5, 0.2)      # glass breaks
add(fx, noise(0.25, 3000, 10), 22.4, 0.3)                                             # marker tally
for k in range(40): add(fx, sine(2400, 0.03, 120), 25.3 + k * 0.17, 0.2)             # ticking
for k in range(8): add(fx, noise(0.18, 2500, 14), 26 + k * 0.8, 0.25)                 # page flips
for k in range(48): add(fx, noise(0.07, 3500, 40), 32.5 + k * 0.11, 0.18)            # frantic scribbling
add(fx, lowpass(noise(1.2, 900, 1.5), 900), 33.0, 0.5)                                # fire whoosh
add(fx, noise(1.8, 4000, 1.0), 36.7, 0.35)                                            # extinguisher
add(fx, sine(1320, 0.5, 6), 39.6, 0.3); add(fx, sine(1760, 0.6, 5), 39.75, 0.3)        # phone ding
add(fx, lowpass(noise(1.5, 3500, 1.8), 3500), 40.3, 0.45)                             # cheer
add(fx, sine(220, 0.5, 3, 660) * np.sin(np.linspace(0, 60, T(0.5))), 42.0, 0.35)       # boing NE?!
k = 0
while True:
    tb = (np.pi / 2 + 2 * np.pi * k) / 9; k += 1
    if tb < 45.25: continue
    if tb > 47.6: break
    add(fx, sine(90, 0.25, 14, 50), tb, 0.7)                                          # table bangs
for k in range(10): add(fx, sine(1800 + 300 * (k % 2), 0.08, 30), 45.4 + k * 0.2, 0.12)  # mop squeaks
for k in range(14): add(fx, noise(0.06, 1500, 30), 50.8 + k * 0.12 + (k % 3) * 0.03, 0.3)  # applause/wings
add(fx, noise(0.9, 2000, 3) * np.linspace(0, 1, T(0.9)), 53.6, 0.3)                    # newspaper spin
add(fx, noise(0.15, 1500, 25), 54.7, 0.6)                                             # paper slap

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
