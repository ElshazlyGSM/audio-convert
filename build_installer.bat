@echo off
cd /d "%~dp0"

if not exist "tools\ffmpeg-essentials" (
    echo Downloading FFmpeg essentials...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "New-Item -ItemType Directory -Force -Path 'tools' | Out-Null; Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile 'tools\ffmpeg-release-essentials.zip'; Expand-Archive -LiteralPath 'tools\ffmpeg-release-essentials.zip' -DestinationPath 'tools\ffmpeg-essentials' -Force"
)

for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "Get-ChildItem 'tools\ffmpeg-essentials' -Recurse -Filter ffmpeg.exe | Select-Object -First 1 -ExpandProperty FullName"`) do set "FFMPEG_EXE=%%F"
if "%FFMPEG_EXE%"=="" for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "(Get-Item (Get-Command ffmpeg).Source).Target"`) do set "FFMPEG_EXE=%%F"
if "%FFMPEG_EXE%"=="" for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "(Get-Command ffmpeg).Source"`) do set "FFMPEG_EXE=%%F"

if "%FFMPEG_EXE%"=="" (
    echo FFmpeg was not found.
    pause
    exit /b 1
)

python -m PyInstaller --noconfirm --onedir --windowed --name SongCoverTool --add-binary "%FFMPEG_EXE%;." gui.py
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer.iss
pause
