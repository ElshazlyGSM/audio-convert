@echo off
cd /d "%~dp0"
if exist "%~dp0dist\MediaAudioStudio\MediaAudioStudio.exe" (
    start "" "%~dp0dist\MediaAudioStudio\MediaAudioStudio.exe"
) else if exist "%~dp0dist\MediaAudioStudio.exe" (
    start "" "%~dp0dist\MediaAudioStudio.exe"
) else if exist "%~dp0dist\SongCoverTool.exe" (
    start "" "%~dp0dist\SongCoverTool.exe"
) else (
    python gui.py
)
