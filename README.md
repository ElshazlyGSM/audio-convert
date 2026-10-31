# Media Audio Studio

A Windows desktop tool for converting audio/video files, extracting audio from videos, enhancing audio, and embedding cover art.

## Features

- Choose one audio/video file or a whole folder.
- Switch the app language between English and Arabic.
- Play and stop the selected audio/video file from inside the app, with a seekable timeline while playback is running.
- Trim a selected audio/video file by using the timeline and Mark Start/Mark End buttons, or by typing start/end time.
- Trim can keep the original media format, or export the selected part to the chosen audio format such as MP3.
- Convert between video formats: MP4, MKV, AVI, MOV, WEBM, WMV, FLV, 3GP, or keep original format (defaults to original quality without compression).
- Video compression & quality presets: Original (No compression), Very High, High, Medium, Small, Very Small.
- Video resolution control: Original size, 1080p, 720p, 480p, 360p.
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
- Reorganized Modern Tabbed UI (6 dedicated sections):
  - 🔄 **Convert & Compress**: Audio conversion & format options alongside video conversion & compression presets.
  - 🔊 **Volume Booster**: Audio volume amplification for quiet files with level detection and anti-clipping limiter.
  - ▶️ **Player & Trim**: Embedded video & audio playback with interactive seekbar and precision clip trimming.
  - 🎙️ **Auto Caption**: Offline AI speech-to-text transcription and subtitle generator with video hardcoding.
  - 🖼️ **Cover Art**: Album art search, custom cover embedding, and preview thumbnail.
  - 📥 **YouTube Download**: Built-in video and audio downloader with quality selection.
- Audio Volume Booster & Level Analysis:
  - Analyze quiet audio/video files to detect peak (max) and mean (RMS) volume levels in dB.
  - Suggested clean boost calculated automatically based on available headroom.
  - Auto Peak Boost button: amplifies directly to optimal volume (0 dB) with single click.
  - Adjustable gain slider from -12 dB to +30 dB with real-time dB and percentage display (e.g. +6 dB = 200%).
  - Quick gain presets: +3 dB (140%), +6 dB (200%), +10 dB (316%), +15 dB (560%).
  - Built-in Anti-Clipping Limiter (`alimiter`) to protect sound from cracking or distortion at high volume.
  - Supports exporting boosted audio to same format, MP3, M4A, WAV, or FLAC (lossless).
- Auto Caption & Speech-to-Text Studio (Local offline AI transcription with Whisper):
  - Transcribe any audio or video file (or batch transcribe whole folders).
  - High accuracy multilingual support (Arabic, English, French, Spanish, German, etc., or Auto Detect).
  - Choice of AI model size: Tiny (Fastest), Base (Balanced & Recommended), Small (High accuracy), Medium (Best accuracy).
  - Export subtitles as `.srt` (SubRip) or `.vtt` (WebVTT), or export plain full text as `.txt`.
  - Live interactive transcription window: view text in real-time as speech is recognized, switch between full text and timestamped subtitles, edit and copy text to clipboard.
  - Hardcode / Burn subtitles directly onto video files with custom styling and Arabic text shaping support.
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

## Developer

- **Developer:** ahmed elshazly
- **Email:** Elshazly.gsm@gmail.com

## Git Notes

Generated files are ignored by `.gitignore`, including `build/`, `dist/`, `installer/`, `tools/`, `input/`, `output/`, local audio/video files, and Python cache files.
