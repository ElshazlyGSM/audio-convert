@echo off
cd /d "%~dp0"
py -3.12 gui.py
if %errorlevel% equ 0 exit /b
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" gui.py
    if %errorlevel% equ 0 exit /b
)
python gui.py
if %errorlevel% neq 0 (
    echo.
    echo Failed to run Media Audio Studio.
    pause
)
