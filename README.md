# AutoViral AI — Local Dashboard

Free local video-to-Shorts dashboard. No login, subscription or paid AI service. The frontend and processing backend run on your own computer.

## Quick start on Windows

1. Install Python 3.11 or 3.12 from https://www.python.org/downloads/windows/ (enable Add Python to PATH).
2. Install FFmpeg in PowerShell using `winget install --id Gyan.FFmpeg -e`. Close/reopen PowerShell and check `ffmpeg -version`.
3. Download ZIP of this repository via GitHub **Code > Download ZIP** and extract.
4. Double-click **setup_windows.bat** once. It creates `.venv` and installs packages; the initial setup and first Whisper download need Internet.
5. Double-click **START_WINDOWS.bat**. The dashboard opens at http://127.0.0.1:7860.
6. Paste an authorized *direct link to an MP4/MOV/WebM/MKV video file* and press Enter, or select the Upload tab and choose a local video. Set clip count and style. The backend automatically processes it and exports Shorts, downloadable in the dashboard and saved under `outputs/`.

**Important:** YouTube watch links, TikTok watch links, and general video webpage links are not currently supported. Those require an authorized import flow; the app does not download arbitrary platform videos.

## What is automatic?
- Download authorized public direct video-file URLs (up to 1GB)
- Detect candidate highlights using audio activity, plus optional local faster-whisper transcript scoring
- Create 1–5 vertical MP4 clips and accompanying title/caption ideas
- Show the first clip and offer finished-file downloads

## Limitations
This is a starter MVP: no professional scene understanding, face-aware cropping, reaction/gameplay split-screen, visible credit text, or automatic platform publishing. Prompts guide basic selection, not all edit operations. The computer must be running while processing. Large videos will be slow on CPU.

Creator credit is saved in MP4 metadata only, not rendered on-screen.

## Troubleshooting
If you previously installed this app, rerun `setup_windows.bat` to get the new dashboard dependencies. If FFmpeg cannot be found, reboot terminal/PC after installation. If transcription fails, untick the Whisper checkbox and try again.

## Files
- `dashboard.py`: local paste-first dashboard and download handler
- `app.py`: audio/transcript selection and FFmpeg rendering engine
- `setup_windows.bat`: one-time setup
- `START_WINDOWS.bat`: start dashboard

## License
MIT (see LICENSE).
