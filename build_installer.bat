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

echo Building ClipCraft Studio with PyInstaller...
py -3.12 -m PyInstaller --noconfirm ClipCraftStudio.spec
if errorlevel 1 (
    echo PyInstaller build failed!
    pause
    exit /b 1
)

echo Building Inno Setup Installer...
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer_setup.iss
if errorlevel 1 (
    echo Inno Setup compilation failed!
    pause
    exit /b 1
)

echo.
echo ========================================================
echo BUILD SUCCESSFUL! Installer created in setup_output\
echo ========================================================
if "%1" neq "--no-pause" pause
