@echo off
rem Hamsican Blender modeli: kurar ve portre/boy goruntulerini isler
set "BL="
for /d %%D in ("C:\Program Files\Blender Foundation\Blender*") do if exist "%%D\blender.exe" set "BL=%%D\blender.exe"
if not defined BL if exist "C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe" set "BL=C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe"
if not defined BL (
  echo Blender bulunamadi. Blender.exe yolunu bana gonderin.
  pause
  exit /b
)
echo Blender: %BL%
"%BL%" -b -P "%~dp0hamsican_model.py" -- --out "%~dp0render"
explorer "%~dp0render"
pause
