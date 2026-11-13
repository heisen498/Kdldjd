@echo off
rem Bozulma gecisi + 3D goruntu + ses = tam Reels videosu
ffmpeg -y -i gecis.mp4 -i goruntu.mp4 -i tam_ses.m4a -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[v]" -map "[v]" -map 2:a -c:v libx264 -crf 19 -preset fast -pix_fmt yuv420p -c:a copy -shortest -movflags +faststart paspasli-diplomat-s2b1.mp4
echo.
echo Hazir: paspasli-diplomat-s2b1.mp4
explorer .
