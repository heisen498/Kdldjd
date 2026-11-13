# Music bed + sound effects + voice-over mix for the 'Paspaslı Diplomat 3' reels (all synthesized, no samples).
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
for i, m in enumerate((60, 64, 67, 72)): add(mus, saw(NOTE(m), 0.4 if i < 3 else 1.2, 1.4), 0.3 + i * 0.12, 0.45)
groove(1.0, 4.4, 120, [C, F, G, C], drums=True, vol=0.45)
groove(4.4, 6.6, 110, [C, G], drums=False, vol=0.4)
groove(6.9, 11.4, 92, [Am, F, C, G], drums=False, vol=0.36, pattern=(0, 1, 2, 3, 2, 1, 0, 1))
groove(11.4, 14.6, 140, [Am, E], drums=False, vol=0.4, stacc=True)
for i, (tt, m) in enumerate([(15.1, 55), (15.6, 54), (16.1, 53), (16.6, 50)]): add(mus, saw(NOTE(m), 0.5 if i < 3 else 1.1, 1.2), tt, 0.5)  # sad trombone
add(mus, pad([NOTE(m) for m in (38, 45, 50)], 5.4, 1.5), 17.5, 0.6)
groove(23.0, 30.0, 118, [Am, Dm, G, C], drums=True, vol=0.48)
for k in range(14): add(mus, noise(0.09, 2200, 30), 26.4 + k * 60 / 118 * 1.0, 0.45)   # claps
for tt in (30.3, 31.6):
    for i, m in enumerate((60, 64, 67)): add(mus, saw(NOTE(m), 1.0, 1.0), tt + i * 0.02, 0.35)
groove(30.6, 38.4, 120, [C, G, Am, F], drums=True, vol=0.48)
add(mus, pad([NOTE(m) for m in (60, 64, 67, 72, 76)], 4.0, 4.0), 38.4, 0.5)
for k in range(12): add(mus, pl(84 + (k * 7) % 12, 0.8, 0.9), 38.5 + k * 0.32, 0.25)
groove(42.4, 48.8, 112, [Am, Dm, E, Am], drums=False, vol=0.42, stacc=True)
groove(48.8, 52.6, 120, [Dm, Bb, C, Dm], drums=False, vol=0.38)
groove(52.6, 55.6, 112, [Am, E], drums=False, vol=0.4, stacc=True)
add(mus, sum(saw(NOTE(m), 1.6, 0.8) for m in (50, 57, 62, 65)) / 4, 55.7, 0.8)
for i, (tt, m) in enumerate([(58.4, 45), (58.8, 44)]): add(mus, sum(saw(NOTE(m + d), 0.9, 1.2) for d in (0, 7, 12)) / 3, tt, 0.6)
for i, m in enumerate((50, 57, 62, 65, 69, 74)): add(mus, pl(m, 1.4, 0.5), 59.2 + i * 0.03, 0.4)

fx = np.zeros(N, np.float32)
for c in [4.4, 6.6, 11.4, 15.0, 17.4, 23, 30, 38.4, 42.4, 48.8, 52.6, 55.6]:
    add(fx, noise(0.35, 2000, 6) * np.linspace(0, 1, T(0.35)) ** 2, c - 0.3, 0.25)
jet = lowpass(rng.uniform(-1, 1, T(2.2)).astype(np.float32), 300) * 2.5
add(fx, jet * env(len(jet), 0.3, 0.4), 4.4, 0.4)
add(fx, sine(988, 0.5, 4), 6.75, 0.3); add(fx, sine(784, 0.7, 3), 6.95, 0.3)            # cabin chime
cab = lowpass(rng.uniform(-1, 1, T(4.8)).astype(np.float32), 160) * 2
add(fx, cab * env(len(cab), 0.3, 0.3), 6.6, 0.2)
add(fx, noise(0.3, 1500, 12), 9.3, 0.2)                                                 # pouring
for k in range(8): add(fx, sine(70, 0.12, 25), 11.6 + k * 0.38, 0.6); add(fx, sine(60, 0.1, 30), 11.75 + k * 0.38, 0.45)   # heartbeat
add(fx, sine(500, 0.3, 4, 150), 13.9, 0.3)                                              # trip
add(fx, noise(0.5, 1200, 7), 14.7, 0.6); add(fx, sine(300, 0.25, 10, 900), 14.7, 0.3)   # ŞLAP splash
for k in range(6): add(fx, sine(1600 - k * 120, 0.1, 25), 15.3 + k * 0.32, 0.18)        # drips
add(fx, noise(0.35, 900, 10), 20.8, 0.45); add(fx, noise(0.3, 900, 12), 21.1, 0.35)     # öhö
for k in range(6):
    ch = sine(4600, 0.18, 10) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 40 * np.arange(T(0.18)) / SR)))
    add(fx, ch.astype(np.float32), 21.6 + k * 0.26, 0.1)
for k in range(18): add(fx, sine(1800 + 300 * (k % 2), 0.08, 30), 23.4 + k * 0.36, 0.12)  # mop squeaks
add(fx, lowpass(noise(2.6, 3500, 1.0), 3500), 31.6, 0.5)                                 # ovation
for k in range(10): add(fx, noise(0.25, 2500, 12), 33.8 + k * 0.4, 0.12)                # mop swishes
add(fx, sine(523, 0.25, 8), 43.8, 0.3); add(fx, sine(392, 0.4, 6), 44.0, 0.3)            # "!" sting
add(fx, noise(1.0, 2000, 3) * np.linspace(0, 1, T(1.0)), 48.8, 0.3)                      # letter flies in
add(fx, noise(0.2, 2500, 14), 50.0, 0.4)                                                 # unfold
add(fx, sine(120, 0.3, 14, 60), 50.8, 0.8)                                               # stamp
add(fx, sine(220, 0.5, 3, 660) * np.sin(np.linspace(0, 60, T(0.5))), 51.4, 0.35)          # NE?!
for i in range(4): add(fx, sine(700, 0.22, 12, 160), 53.2 + i * 0.7, 0.45)              # BONK
add(fx, noise(1.2, 5000, 2.5), 55.65, 0.25)
add(fx, sine(1320, 0.4, 6), 58.4, 0.3)                                                   # counter flip

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
