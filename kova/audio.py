# Music bed + sound effects + voice-over mix for the 'Paspaslı Diplomat 2' reels (all synthesized, no samples).
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
for i, m in enumerate((60, 64, 67, 72)): add(mus, saw(NOTE(m), 0.4 if i < 3 else 1.2, 1.4), 0.3 + i * 0.12, 0.45)   # intro fanfare
groove(1.0, 4.4, 120, [C, F, G, C], drums=True, vol=0.45)
groove(4.4, 10.6, 96, [C, Am, F, G], drums=False, vol=0.38, pattern=(0, 1, 2, 3, 2, 1, 0, 1))                 # classy
groove(10.6, 13.5, 120, [Am, E], drums=False, vol=0.42, stacc=True)                                         # sneaky
groove(15.0, 16.2, 120, [Am], drums=False, vol=0.35, stacc=True)
groove(16.2, 22.3, 88, [Dm, Dm, Bb, E], drums=False, vol=0.38, stacc=True)                                   # suspense
add(mus, pad([NOTE(m) for m in (38, 45, 50)], 3.2, 2.0), 22.4, 0.7)                                         # slow-mo drone
groove(28.6, 36.3, 100, [Dm, F, C, Am], drums=True, vol=0.42)                                                # doctrine march
for tt in (36.6, 38.8):
    for i, m in enumerate((60, 64, 67)): add(mus, saw(NOTE(m), 1.0, 1.0), tt + i * 0.02, 0.35)
groove(37.0, 42.2, 120, [C, G, Am, F], drums=True, vol=0.48)                                                 # anthem
for i, f in enumerate((880, 660, 990)): add(mus, sine(f, 0.25, 6), 42.25 + i * 0.22, 0.4)                    # news jingle
groove(42.9, 48.2, 132, [Am, F, C, G], drums=True, vol=0.42)
groove(48.2, 52.6, 120, [C, F, G, C], drums=True, vol=0.42)
for i, (tt, m) in enumerate([(52.65, 45), (53.1, 44), (53.6, 43)]):                                        # dun dun dunnn
    add(mus, sum(saw(NOTE(m + d), 1.3 if i < 2 else 2.0, 1.0 if i < 2 else 0.6) for d in (0, 7, 12)) / 3, tt, 0.85)
add(mus, sum(saw(NOTE(m), 1.6, 0.8) for m in (50, 57, 62, 65)) / 4, 55.5, 0.8)                              # "devam edecek" sting
groove(56.4, 58.8, 120, [Dm, C], drums=False, vol=0.35)
for i, m in enumerate((50, 57, 62, 65, 69, 74)): add(mus, pl(m, 2.2, 0.5), 58.8 + i * 0.03, 0.45)

fx = np.zeros(N, np.float32)
for c in [4.4, 10.6, 16.2, 19.4, 22.4, 28.6, 36.4, 42.2, 48.2, 51.8, 55.4]:
    add(fx, noise(0.35, 2000, 6) * np.linspace(0, 1, T(0.35)) ** 2, c - 0.3, 0.25)
crowd = lowpass(rng.uniform(-1, 1, T(6.2)).astype(np.float32), 700) * 2.2
crowd *= (0.7 + 0.3 * np.sin(2 * np.pi * 1.3 * np.arange(len(crowd)) / SR))
add(fx, crowd * env(len(crowd), 0.4, 0.4), 4.4, 0.25)                                                       # reception murmur
for tt in (5.3, 6.9, 8.4): add(fx, sine(3200, 0.6, 7), tt, 0.15); add(fx, sine(4100, 0.5, 8), tt + 0.02, 0.1)  # clinks
for k in range(16): add(fx, sine(1800 + 300 * (k % 2), 0.08, 30), 4.8 + k * 0.33, 0.1)                       # mop squeaks
for k in range(9): add(fx, sine(1800 + 300 * (k % 2), 0.08, 30), 10.8 + k * 0.32, 0.1)
add(fx, sine(400, 0.5, 0.5, 1700), 13.6, 0.35); add(fx, sine(1700, 0.6, 0.5, 300), 14.1, 0.35)             # slide whistle
add(fx, noise(0.6, 3000, 6), 14.8, 0.45); add(fx, sine(160, 0.4, 8, 60), 14.8, 0.6)                          # crash
add(fx, noise(1.4, 1500, 1.5) * np.linspace(0.2, 1, T(1.4)), 16.2, 0.35)                                   # slide in
t0 = 17.5
for k in range(6): add(fx, saw(180 + 40 * np.sin(k), 0.25, 6), t0 + k * 0.42 * (1 + k * 0.1), 0.25 * (1 - k / 7))   # door swings
sn = lowpass(rng.uniform(-1, 1, T(3.0)).astype(np.float32), 400); sn *= (0.5 + 0.5 * np.sin(2 * np.pi * 0.7 * np.arange(len(sn)) / SR)) ** 3
add(fx, sn, 16.3, 0.35)                                                                                    # guard snore
add(fx, sine(900, 0.35, 4, 200) * (rng.uniform(0.5, 1, T(0.35))).astype(np.float32), 20.3, 0.4)            # record scratch
add(fx, lowpass(noise(2.6, 600, 0.6), 600), 22.6, 0.35)                                                     # slow-mo whoosh
add(fx, sine(140, 0.3, 14, 70), 25.4, 0.9); add(fx, noise(0.12, 3000, 30), 25.4, 0.5)                      # TAK!
for k in range(10):                                                                                         # crickets
    ch = sine(4600, 0.18, 10) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 40 * np.arange(T(0.18)) / SR)))
    add(fx, ch.astype(np.float32), 26.0 + k * 0.28, 0.12)
add(fx, sine(1320, 0.4, 6), 31.5, 0.2)                                                                      # magnifier ding
add(fx, lowpass(noise(1.8, 3500, 1.4), 3500), 36.9, 0.45)                                                   # applause/cheer
add(fx, noise(0.1, 4000, 30), 38.8, 0.4)                                                                    # confetti pop
for k in range(12): add(fx, noise(0.05, 6000, 60), 42.6 + k * 0.45 + (k % 3) * 0.07, 0.35)                 # camera clicks
add(fx, sine(200, 4.0, 0.0, 900) * 0.6, 42.7, 0.18)                                                         # rising index
add(fx, lowpass(noise(1.2, 1500, 1.0), 1500), 46.0, 0.4)                                                    # rocket
add(fx, sine(1320, 0.5, 6), 48.4, 0.3); add(fx, sine(1760, 0.6, 5), 48.55, 0.3)                              # ding
for k, f in enumerate((697, 770, 852, 941)): add(fx, sine(f, 0.12, 6) + sine(1209, 0.12, 6), 49.4 + k * 0.18, 0.2)   # phone dial
add(fx, sine(180, 0.4, 8, 60), 52.8, 0.6)                                                                   # faint thud
add(fx, noise(1.2, 5000, 2.5), 55.45, 0.25)                                                                 # cymbal-ish

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
