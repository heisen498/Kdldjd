# Paspaslı Diplomat — devir notu (yerel oturum için)

Bu depo, Instagram Reels için yapılan "Paspaslı Diplomat" animasyon serisinin tüm kaynaklarını içerir. Kullanıcı Türkçe konuşur; cevaplar sade ve adım adım olmalı (komutları tek tek ver).

## Seri
- 1. sezon (2D canvas, `kpss/`, `kova/`, `genelkurul/`, `lise/`, `yazili/`, `final/`): Hamsican'ın Uİ'den KPSS ile Dışişleri'nde kadrolu temizlik görevlisi olup "Kova İşleri Müsteşarı"na yükselmesi. Zaman çizelgesi: liseye başlama 2020, mezuniyet 2024, bugün 2026. Annesinin bayılma sayacı her bölümde şaka olarak artar.
- 2. sezon (3D):
  - `s2b1/` "Kayıp Kova" (Three.js). Başında 2D→3D bozulma geçişi var. **Bu bölüm değiştirilmeyecek.**
  - `s2b2/` "Uzay Paspası" (Three.js, Lost havasında). Sonu: kapak açılır, gizemli ses "Seni bekliyorduk, Hamsican."
  - Sıradaki: **Bölüm 3 "Kapağın Altında"** — önerilen hikâye: Hamsican kapağın altındaki sığınağa iner, sesin sahibi Makif'li astronot sıra arkadaşıdır (altın kova onda), "her 50 dakikada bir zemini sil" sayacı (Lost düğmesine gönderme), Hamsican paspasla sayacı sıfırlar. Kullanıcıya onaylat.
- `motor3d/motor.html`: en güncel Three.js karakter motoru (sonraki bölümler için).

## Blender'a geçiş (şu anki iş)
- Kullanıcının bilgisayarında **Blender 5.3 (Steam)**: `C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe`, ekran kartı **NVIDIA RTX 4050 (OptiX)**.
- `blender/hamsican_model.py`: Hamsican modeli (skin modifier ile dikişsiz gövde, şekillendirilmiş kafa, parçacık kıvırcık saç, SSS cilt, Cycles). Çalıştırma: `blender -b -P hamsican_model.py -- --out render` (`--low` = hızlı ön izleme). `hamsican_model.bat` aynı şeyi Windows'ta yapar.
- Betik Blender 4.0'da test edildi; 5.3'te uyarı (deprecation) var, hata yok. 5.3 API farklarına dikkat.
- Modelde yapılacaklar: kafa yumurta gibi (alın geniş, yüz hatları alçak), kaşlar saçın altında kalıyor, ağız sadece çizgi, kıyafette kırışık yok, eller basit. Sonra: armature (skin modifier'dan `skin_armature_create`), poz/animasyon, sahneler, kamera; bölümleri Blender'da işlemek.

## Ses
- Anlatım: offline Piper sesleri (sherpa-onnx). Anlatıcı **Fettah**, Hamsican **Fahrettin**, gizemli ses **DFKI** (pes + yankı). Modeller GitHub release'ten: `k2-fsa/sherpa-onnx` → `tts-models/vits-piper-tr_TR-<ses>-medium.tar.bz2`. Python paketi: `sherpa-onnx==1.13.8` (2.x espeak'siz).
- Müzik/efektler: her bölümdeki `audio.py` (numpy sentez). Dudak senkronu için `narrate.py` → `timings.js` içinde `window.ENV`/`window.ENVH`.

## İşleme
- Three.js bölümleri: `node render.js goruntu.mp4` (`GPU=1` ile ekran kartı), sonra `birlestir.bat`.
- Commit mesajlarının sonuna kullanıcının ortamındaki atıf satırları eklenir; dal: `claude/awesome-cannon-xcxrme`.
