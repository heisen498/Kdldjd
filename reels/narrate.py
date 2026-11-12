# Turkish voice-over for the reels video (offline, sherpa-onnx + Piper tr_TR voice).
# Usage: python3 narrate.py <model_dir> <out.wav>
import sys, json, wave
import numpy as np, sherpa_onnx

LINES = [  # (desired start s, text)
    (0.7,  "Karadeniz'in gümüş yolculuğu: hamsi göçü."),
    (5.2,  "Rota, Tonya açıklarından Samsun Tekkeköy'e uzanıyor. Kıyı boyunca yaklaşık iki yüz altmış kilometre."),
    (11.6, "Birinci gün. Sürü, Tonya açıklarında toplanıyor."),
    (15.0, "Ve yolculuk başlıyor. Sürü kıyıyı izleyerek batıya yüzüyor, martılar da peşinde."),
    (19.8, "Karadeniz hamsisinin sırtı mavi yeşil, karnı gümüş rengidir."),
    (24.4, "Ordu açıklarında yunuslar saldırıyor! Sürü sıkışıyor, dağılıyor, sonra yeniden toplanıyor."),
    (30.4, "Yason Burnu'nu dönen sürü, Ünye'ye yaklaşıyor."),
    (33.6, "Sonbaharda sular soğuyunca hamsiler, kışı geçirmek için daha ılık güneydoğu Karadeniz kıyılarına iner."),
    (39.6, "Yeşilırmak deltası geçildi. Dokuz santimden küçük hamsinin avlanması yasaktır."),
    (44.4, "On birinci gün. Sürü Tekkeköy açıklarında; gırgır teknesi ağını çeviriyor."),
    (49.4, "Gırgır av sezonu bir Eylül'de açılır, on beş Nisan'da kapanır."),
]

mdir, out = sys.argv[1], sys.argv[2]
name = mdir.rstrip('/').split('/')[-1].replace('vits-piper-', '')
cfg = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
    vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=f"{mdir}/{name}.onnx", tokens=f"{mdir}/tokens.txt",
                                               data_dir=f"{mdir}/espeak-ng-data", length_scale=0.93),
    num_threads=4))
tts = sherpa_onnx.OfflineTts(cfg)
clips, t, sr = [], 0.0, None
for want, text in LINES:
    a = tts.generate(text, sid=0, speed=1.0)
    sr = a.sample_rate
    x = np.array(a.samples, dtype=np.float32)
    start = max(want, t + 0.3)
    clips.append((start, x)); t = start + len(x) / sr
    print(json.dumps({"want": want, "start": round(start, 2), "end": round(t, 2), "text": text}, ensure_ascii=False))
total = int((t + 1) * sr)
buf = np.zeros(total, np.float32)
for s, x in clips:
    i = int(s * sr); buf[i:i + len(x)] += x
buf = buf / max(1e-6, np.abs(buf).max()) * 0.9
with wave.open(out, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((buf * 32767).astype(np.int16).tobytes())
