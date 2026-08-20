# Media Audio Studio

A Windows desktop tool for converting audio/video files, extracting audio from videos, enhancing audio, and embedding cover art.

## Features

- Choose one audio/video file or a whole folder.
- Switch the app language between English and Arabic.
- Play and stop the selected audio/video file from inside the app, with a seekable timeline while playback is running.
- Trim a selected audio/video file by using the timeline and Mark Start/Mark End buttons, or by typing start/end time.
- Trim can keep the original media format, or export the selected part to the chosen audio format such as MP3.
- Convert to MP3, M4A, AAC, WAV, FLAC, OGG, OPUS, or WMA.
- Extract normal audio files from videos such as MP4, MKV, MOV, AVI, WEBM, and WMV.
- Keep original format if you only want to add cover art.
- Add covers from YouTube/iTunes/Bing automatically.
- Use a custom cover image from your computer.
- Preview found covers before embedding.
- Skip files when output already exists.
- Choose MP3/M4A quality: 128k, 192k, 256k, or 320k.
- Show file-by-file progress, current file percentage, and overall percentage while converting.
- Optional local FFmpeg audio enhancement presets:
  - Normalize volume
  - Louder and clearer
  - Noise reduction
  - Strong noise cleanup
  - Podcast voice
  - Reduce echo
  - Auto clean all
- Build a Windows installer that includes FFmpeg and FFplay.
- Download from YouTube, choose one of the available video qualities, or save audio only as MP3.

## Audio Enhancement Notes

The enhancement presets run locally with FFmpeg, so users do not need Adobe Podcast or any cloud service. `Podcast voice`, `Strong noise cleanup`, and `Auto clean all` are the strongest presets. They can improve volume balance, voice clarity, and steady background noise, but they are not the same as Adobe's AI voice enhancement.

## Run From Source

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the app:

```powershell
python gui.py
```

You can also double-click `convert.bat`.

## Build Installer

Install Inno Setup first if you do not already have it:

```powershell
winget install --id JRSoftware.InnoSetup --silent --accept-package-agreements --accept-source-agreements
```

Then run:

```powershell
.\build_installer.bat
```

The script downloads FFmpeg essentials automatically into `tools/`, builds the app, then creates:

```text
installer/MediaAudioStudioSetup.exe
```

## Build Portable EXE

```powershell
.\build_exe.bat
```

The output will be in:

```text
dist/MediaAudioStudio.exe
```

## Git Notes

Generated files are ignored by `.gitignore`, including `build/`, `dist/`, `installer/`, `tools/`, `input/`, `output/`, local audio/video files, and Python cache files.
