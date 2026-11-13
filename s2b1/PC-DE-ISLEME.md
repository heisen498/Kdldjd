# Bölümü kendi bilgisayarında işleme (Windows)

Ekran kartı kullanıldığı için bulut ortamından çok daha hızlıdır (genelde birkaç dakika).

## 1. Bir kerelik kurulum
Komut İstemi'ni (cmd) aç ve şunları çalıştır:

    winget install OpenJS.NodeJS.LTS
    winget install Git.Git
    winget install Gyan.FFmpeg

Kurulumdan sonra Komut İstemi'ni kapatıp yeniden aç.

## 2. Projeyi indir
    git clone -b claude/awesome-cannon-xcxrme https://github.com/heisen498/Kdldjd.git
    cd Kdldjd\s2b1
    npm install
    npm install playwright
    npx playwright install chromium

## 3. Videoyu işle (ekran kartıyla)
    set GPU=1
    node render.js goruntu.mp4

Bir Chromium penceresi açılır; işlem bitene kadar kapatma. İlerleme her 150 karede bir yazılır (toplam 1800 kare).

## 4. Sesi ekle
    ffmpeg -i goruntu.mp4 -i ses.m4a -map 0:v -map 1:a -c copy -shortest -movflags +faststart paspasli-diplomat-s2b1.mp4

`paspasli-diplomat-s2b1.mp4` hazır Reels videosudur (1080×1920, 60 sn).

## Sadece izlemek istersen
    npx http-server -p 8080
Tarayıcıda http://localhost:8080/s2b1.html adresini aç; animasyon gerçek zamanlı oynar (altyazılı, sessiz).

## Bozulma geçişli tam sürüm
`goruntu.mp4` hazır olduktan sonra (önce `git pull` ile `gecis.mp4` ve `tam_ses.m4a` dosyalarını al):

    ffmpeg -i gecis.mp4 -i goruntu.mp4 -i tam_ses.m4a -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[v]" -map "[v]" -map 2:a -c:v libx264 -crf 19 -preset fast -pix_fmt yuv420p -c:a copy -shortest -movflags +faststart paspasli-diplomat-s2b1.mp4
