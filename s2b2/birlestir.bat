@echo off
rem 3D goruntu + ses = tam Reels videosu
ffmpeg -y -i goruntu.mp4 -i ses.m4a -map 0:v -map 1:a -c:v copy -c:a copy -shortest -movflags +faststart paspasli-diplomat-s2b2.mp4
echo.
echo Hazir: paspasli-diplomat-s2b2.mp4
explorer .
