# Turkish voice-over with Microsoft Edge neural voices (edge-tts).
# Usage: python3 narrate_edge.py <out.wav> [voice] [rate]
# Needs network access to speech.platform.bing.com; uses HTTPS_PROXY if set.
import asyncio, json, os, subprocess, sys, tempfile, wave
import numpy as np, edge_tts
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lines import LINES

out = sys.argv[1]
voice = sys.argv[2] if len(sys.argv) > 2 else "tr-TR-AhmetNeural"
rate = sys.argv[3] if len(sys.argv) > 3 else "+0%"
SR = 24000
proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

async def synth(text, path):
    await edge_tts.Communicate(text, voice, rate=rate, proxy=proxy).save(path)

def decode(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    nz = np.where(np.abs(x) > 0.01)[0]          # trim leading/trailing silence
    return x[max(0, nz[0] - 600): nz[-1] + 2400] if len(nz) else x

clips, t = [], 0.0
with tempfile.TemporaryDirectory() as d:
    for i, (want, text) in enumerate(LINES):
        p = f"{d}/{i}.mp3"
        asyncio.run(synth(text, p))
        x = decode(p)
        start = max(want, t + 0.3)
        clips.append((start, x)); t = start + len(x) / SR
        print(json.dumps({"want": want, "start": round(start, 2), "end": round(t, 2), "text": text}, ensure_ascii=False))
buf = np.zeros(int((t + 1) * SR), np.float32)
for s, x in clips:
    i = int(s * SR); buf[i:i + len(x)] += x
buf = buf / max(1e-6, np.abs(buf).max()) * 0.9
with wave.open(out, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((buf * 32767).astype(np.int16).tobytes())
