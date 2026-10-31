@echo off
title Media Audio Studio Mobile - Build APK
cd /d "%~dp0"
echo ===================================================
echo Building Media Audio Studio Mobile APK (Android)...
echo ===================================================
call flutter build apk --split-per-abi
echo.
echo Build finished! Your APK files are in:
echo build\app\outputs\flutter-apk\
echo - For most modern phones (64-bit): app-arm64-v8a-release.apk
echo - For older 32-bit phones:         app-armeabi-v7a-release.apk
pause
