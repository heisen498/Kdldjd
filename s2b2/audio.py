# Music bed + sound effects + voice-over mix for the 'Paspaslı Diplomat' S2B2 'Uzay Paspası' reels (all synthesized, no samples).
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
def timp(tt, f=60, g=0.8): add(mus, sine(f, 1.2, 3, f * 0.75), tt, g)
def swish(tt, g=0.5, rev=True):   # flashback "whoosh": rising filtered noise ending in a hit
    n = T(0.9); x = noise(0.9, 3000, 0.0) * (np.linspace(0, 1, n) ** 3 if rev else np.linspace(1, 0, n) ** 2)
    add(fx, x.astype(np.float32), tt - (0.9 if rev else 0), g)
    add(fx, sine(80, 0.5, 6, 40), tt, g * 1.2)
fx = np.zeros(N, np.float32)
# cold open: tinnitus + heartbeat + muffled drone
add(fx, (sine(3200, 4.6, 0.6) * 0.5).astype(np.float32), 0.0, 0.08)
for k in range(5): add(fx, sine(55, 0.15, 20), 0.6 + k * 0.85, 0.7); add(fx, sine(48, 0.12, 25), 0.78 + k * 0.85, 0.5)
add(mus, pad([NOTE(m) for m in (33, 40, 45)], 4.6, 0.3), 0.0, 0.45)
# title card: ominous swell -> hard cut
sw = pad([NOTE(m) for m in (31, 38, 43, 50)], 3.2, 0.4) * np.linspace(0, 1.6, T(3.2)) ** 2
add(mus, sw.astype(np.float32), 4.7, 0.55)
add(fx, (noise(3.2, 400, 0.0) * np.linspace(0, 1, T(3.2)) ** 3).astype(np.float32), 4.7, 0.35)
timp(7.95, 45, 1.0)
# planet ambience: insects, distant calls, fire crackle (8 -> 52)
amb_len = 44.0
ins = noise(amb_len, 4500, 0.0) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 26 * np.arange(T(amb_len)) / SR)))
ins *= (0.6 + 0.4 * np.sin(2 * np.pi * 0.13 * np.arange(T(amb_len)) / SR))
add(fx, ins.astype(np.float32) * 0.08, 8.0, 1.0)
for tt in (10.5, 15.2, 27.5, 31.8, 36.4):     # distant alien calls
    ct = np.arange(T(1.2)) / SR; call = np.sin(2 * np.pi * (500 + 300 * np.sin(2 * np.pi * 3 * ct)) * ct) * np.exp(-ct * 2.5)
    add(fx, lowpass(call.astype(np.float32), 1500), tt, 0.12)
crk = np.zeros(T(10.3), np.float32)
for i in range(160): j = rng.integers(0, len(crk) - 400); crk[j:j + 300] += rng.uniform(-1, 1, 300).astype(np.float32) * np.exp(-np.arange(300) / 60)
add(fx, lowpass(crk, 3000), 8.0, 0.25)
add(mus, pad([NOTE(m) for m in (38, 45, 52, 57)], 10.3, 0.25), 8.0, 0.4)
for k in range(10): add(mus, pl((69, 72, 76, 71)[k % 4], 1.6, 0.35), 8.6 + k * 0.95, 0.14)
# flashback (18.3 -> 25.6)
swish(18.3, 0.6)
for k, tt in enumerate((20.6, 21.5, 22.4)): add(fx, sine(880, 0.25, 8), tt, 0.35)
rum = lowpass(rng.uniform(-1, 1, T(4.4)).astype(np.float32), 100) * 3.5
add(fx, rum * np.linspace(0.2, 1, len(rum)).astype(np.float32), 20.9, 0.55)
add(fx, (noise(2.2, 5000, 0.0) * 0.6).astype(np.float32), 23.4, 0.4)    # signal lost static
add(fx, sine(1000, 0.6, 0.5), 23.4, 0.12)                                # flatline beep
swish(25.6, 0.6)
# tracks: tense pulse
for k in range(16): add(mus, sine(NOTE(38), 0.25, 8), 25.8 + k * 0.48, 0.45)
add(mus, pad([NOTE(m) for m in (38, 44, 50)], 7.6, 1.5), 25.8, 0.35)
# cleaning the hatch
for k in range(12): add(fx, noise(0.25, 2200, 10), 34.2 + k * 0.42, 0.22)            # mop sweeps
add(mus, pad([NOTE(m) for m in (40, 47, 52, 55)], 10.6, 0.3), 33.6, 0.35)
for k, m in enumerate((64, 62, 60, 57, 60, 62)): add(mus, pl(m, 1.8, 0.3), 37.0 + k * 0.9, 0.18)
# hatch opens
for k in range(4): add(fx, sine(1500, 0.08, 15), 43.6 + k * 0.18, 0.3)
add(fx, (noise(1.6, 3000, 1.5)).astype(np.float32), 44.4, 0.45)        # hydraulic hiss
add(fx, sine(120, 1.4, 1.2, 60), 44.5, 0.6)                                # heavy lid
hum = (np.sin(2 * np.pi * 55 * np.arange(T(7.6)) / SR) + 0.5 * np.sin(2 * np.pi * 110 * np.arange(T(7.6)) / SR)) * np.linspace(0, 1, T(7.6))
add(fx, hum.astype(np.float32) * 0.2, 44.6, 1.0)
add(mus, pad([NOTE(m) for m in (36, 43, 48, 55, 60)], 7.8, 0.2) * np.linspace(0.3, 1.4, T(7.8)).astype(np.float32), 44.4, 0.5)
# white-out & end card swell
timp(52.2, 42, 1.1)
end = pad([NOTE(m) for m in (31, 38, 43, 50)], 7.0, 0.3) * np.linspace(1, 0, T(7.0))
add(mus, end.astype(np.float32), 52.3, 0.45)

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
