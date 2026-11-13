# Multi-voice narration (offline Piper voices via sherpa-onnx) + lip-sync envelopes.
# Usage: python3 narrate.py <tts_models_dir> <out.wav> <timings.js>
import sys, os, json, wave
import numpy as np, sherpa_onnx
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lines import LINES
mroot, out, tjs = sys.argv[1:4]
VOICES = {"narr": "fettah-medium", "ham": "fahrettin-medium", "myst": "dfki-medium"}
engines = {}
def tts(v):
    if v not in engines:
        d = f"{mroot}/vits-piper-tr_TR-{VOICES[v]}"; n = f"tr_TR-{VOICES[v]}"
        engines[v] = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
            vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=f"{d}/{n}.onnx", tokens=f"{d}/tokens.txt", data_dir=f"{d}/espeak-ng-data",
                                                       length_scale=1.05 if v != "narr" else 0.97), num_threads=4)))
    return engines[v]
SR = 22050
clips, t, timings = [], 0.0, []
for want, text, v in LINES:
    a = tts(v).generate(text, sid=0, speed=1.0)
    x = np.array(a.samples, np.float32)
    if a.sample_rate != SR: x = np.interp(np.arange(int(len(x) * SR / a.sample_rate)) * a.sample_rate / SR, np.arange(len(x)), x).astype(np.float32)
    if v == "myst":   # deeper + echo
        x = np.interp(np.arange(int(len(x) / 0.86)) * 0.86, np.arange(len(x)), x).astype(np.float32)
        y = np.zeros(len(x) + int(0.9 * SR), np.float32); y[:len(x)] += x
        for k, g in ((0.18, 0.45), (0.36, 0.25), (0.6, 0.12)): d = int(k * SR); y[d:d + len(x)] += x * g
        x = y
    if v == "ham": x = x * 0.9
    start = max(want, t + 0.3)
    clips.append((start, x, v)); t = start + len(x) / SR
    timings.append({"start": round(start, 2), "end": round(t, 2), "text": text, "voice": v})
    print(f"{want:5.1f} {start:5.2f}-{t:5.2f} [{v}] {text}")
n = int((t + 1) * SR); buf = np.zeros(n, np.float32); hbuf = np.zeros(n, np.float32)
for s, x, v in clips:
    i = int(s * SR); buf[i:i + len(x)] += x
    if v == "ham": hbuf[i:i + len(x)] += x
buf = buf / max(1e-6, np.abs(buf).max()) * 0.9
with wave.open(out, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((buf * 32767).astype(np.int16).tobytes())
def envelope(b):
    hop = SR // 30; e = [float(np.sqrt(np.mean(b[i * hop:(i + 1) * hop] ** 2))) for i in range(len(b) // hop)]
    ref = float(np.percentile([v for v in e if v > 0.01] or [1], 90)); return [round(min(1.0, v / ref), 3) for v in e]
with open(tjs, 'w') as f:
    f.write("window.SUBS = " + json.dumps(timings, ensure_ascii=False, indent=1) + ";\n")
    f.write("window.ENV = " + json.dumps(envelope(buf)) + ";\n")
    f.write("window.ENVH = " + json.dumps(envelope(hbuf)) + ";\n")
