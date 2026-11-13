@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" "%~dp0gui.py"
) else (
    start "" py.exe -3.12 "%~dp0gui.py"
)
