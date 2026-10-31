@echo off
cd /d "%~dp0"
if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" "e:\Songs\gui.py"
) else (
    start "" py.exe -3.12 "e:\Songs\gui.py"
)
