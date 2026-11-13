#!/bin/bash
# Joins the glitch intro + both 3D render halves and muxes the full soundtrack.
# Usage: bash assemble.sh <work_dir>   (expects s21_a.mp4, s21_b.mp4, gl_out/, gl_audio.wav, s21_audio.wav there)
set -e
D="$1"; cd "$(dirname "$0")"
ffmpeg -loglevel error -y -framerate 30 -i "$D/gl_out/g_%03d.jpg" -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p "$D/intro.mp4"
printf "file '%s'\nfile '%s'\nfile '%s'\n" "$D/intro.mp4" "$D/s21_a.mp4" "$D/s21_b.mp4" > "$D/parts.txt"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$D/parts.txt" -c copy "$D/s21_full_video.mp4"
ffmpeg -loglevel error -y -i "$D/gl_audio.wav" -i "$D/s21_audio.wav" -filter_complex \
  "[0]aresample=44100,aformat=channel_layouts=stereo[a0];[1]aresample=44100,aformat=channel_layouts=stereo[a1];[a0][a1]concat=n=2:v=0:a=1,loudnorm=I=-15:TP=-1.5:LRA=11[out]" \
  -map "[out]" -ar 44100 "$D/s21_full_audio.wav"
ffmpeg -loglevel error -y -i "$D/s21_full_video.mp4" -i "$D/s21_full_audio.wav" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 160k -shortest -movflags +faststart paspasli-diplomat-s2b1.mp4
ffprobe -v error -show_entries stream=codec_name,width,height,duration -of compact paspasli-diplomat-s2b1.mp4
