# Voice-over with the offline Piper "Fettah" Turkish voice (sherpa-onnx).
# Usage: python3 narrate.py <model_dir> <out.wav> <timings.js>
import sys, os, json, wave
import numpy as np, sherpa_onnx
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lines import LINES

mdir, out, tjs = sys.argv[1:4]
name = mdir.rstrip('/').split('/')[-1].replace('vits-piper-', '')
tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
    vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=f"{mdir}/{name}.onnx", tokens=f"{mdir}/tokens.txt",
                                               data_dir=f"{mdir}/espeak-ng-data", length_scale=0.95),
    num_threads=4)))
clips, t, sr, timings = [], 0.0, None, []
for want, text in LINES:
    a = tts.generate(text, sid=0, speed=1.0)
    sr = a.sample_rate
    x = np.array(a.samples, dtype=np.float32)
    start = max(want, t + 0.3)
    clips.append((start, x)); t = start + len(x) / sr
    timings.append({"start": round(start, 2), "end": round(t, 2), "text": text})
    print(f"{want:5.1f} {start:5.2f}-{t:5.2f}  {text}")
buf = np.zeros(int((t + 1) * sr), np.float32)
for s, x in clips:
    i = int(s * sr); buf[i:i + len(x)] += x
buf = buf / max(1e-6, np.abs(buf).max()) * 0.9
with wave.open(out, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((buf * 32767).astype(np.int16).tobytes())
# per-frame loudness envelope (30 fps) for lip sync
hop = sr // 30
env = [float(np.sqrt(np.mean(buf[i * hop:(i + 1) * hop] ** 2))) for i in range(len(buf) // hop)]
ref = float(np.percentile([e for e in env if e > 0.01] or [1], 90))
env = [round(min(1.0, e / ref), 3) for e in env]
with open(tjs, 'w') as f:
    f.write("window.SUBS = " + json.dumps(timings, ensure_ascii=False, indent=1) + ";\n")
    f.write("window.ENV = " + json.dumps(env) + ";\n")
