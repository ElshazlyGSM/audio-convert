@echo off
cd /d "%~dp0"

if not exist "tools\ffmpeg-essentials" (
    echo Downloading FFmpeg essentials...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "New-Item -ItemType Directory -Force -Path 'tools' | Out-Null; Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile 'tools\ffmpeg-release-essentials.zip'; Expand-Archive -LiteralPath 'tools\ffmpeg-release-essentials.zip' -DestinationPath 'tools\ffmpeg-essentials' -Force"
)

for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "Get-ChildItem 'tools\ffmpeg-essentials' -Recurse -Filter ffmpeg.exe | Select-Object -First 1 -ExpandProperty FullName"`) do set "FFMPEG_EXE=%%F"
for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "Get-ChildItem 'tools\ffmpeg-essentials' -Recurse -Filter ffplay.exe | Select-Object -First 1 -ExpandProperty FullName"`) do set "FFPLAY_EXE=%%F"
for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "Get-ChildItem 'tools\ffmpeg-essentials' -Recurse -Filter ffprobe.exe | Select-Object -First 1 -ExpandProperty FullName"`) do set "FFPROBE_EXE=%%F"
if "%FFMPEG_EXE%"=="" for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "(Get-Item (Get-Command ffmpeg).Source).Target"`) do set "FFMPEG_EXE=%%F"
if "%FFMPEG_EXE%"=="" for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "(Get-Command ffmpeg).Source"`) do set "FFMPEG_EXE=%%F"
if "%FFPLAY_EXE%"=="" for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "(Get-Command ffplay).Source"`) do set "FFPLAY_EXE=%%F"
if "%FFPROBE_EXE%"=="" for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "(Get-Command ffprobe).Source"`) do set "FFPROBE_EXE=%%F"

if "%FFMPEG_EXE%"=="" (
    echo FFmpeg was not found.
    pause
    exit /b 1
)

if "%FFPLAY_EXE%"=="" (
    echo FFplay was not found.
    pause
    exit /b 1
)

if "%FFPROBE_EXE%"=="" (
    echo FFprobe was not found.
    pause
    exit /b 1
)

py -3.12 -m PyInstaller --noconfirm --onedir --windowed --name MediaAudioStudio --version-file file_version_info.txt --add-binary "%FFMPEG_EXE%;." --add-binary "%FFPLAY_EXE%;." --add-binary "%FFPROBE_EXE%;." --collect-all yt_dlp --collect-all faster_whisper --collect-all ctranslate2 --collect-all tokenizers --collect-all huggingface_hub gui.py
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer.iss
if "%1" neq "--no-pause" pause
