# AutoViral Local

Free, open-source, local Windows video-to-shorts app. No subscription, cloud hosting, account or API key needed.

## Windows setup

1. Install Python 3.11 or 3.12 from https://www.python.org/downloads/windows/ and check **Add Python to PATH**.
2. Open PowerShell and run `winget install --id Gyan.FFmpeg -e`. Close and reopen PowerShell. Test with `ffmpeg -version`.
3. On this repository, click **Code > Download ZIP**, then extract it to a normal folder (for example, Desktop).
4. Double-click `setup_windows.bat` once. This creates a virtual environment and installs dependencies; it requires internet initially.
5. Double-click `START_WINDOWS.bat`; the browser should open at http://127.0.0.1:7860.
6. Upload an MP4/MOV file that you own or have permission to edit. Enter a short prompt, select clip count and duration, then click **Make my Shorts**.
7. Preview and download the clips. Outputs are also saved in the `outputs/` folder.

First test: use a 1–5-minute video; set 1 clip, 30 seconds, and Whisper model `tiny`. If transcription is slow or unavailable, untick **Use AI speech transcription**.

## Features
- Local video upload, no arbitrary YouTube video downloads
- FFmpeg real 9:16 video export with audio, centered crop or fit
- Audio-energy highlight selection
- Optional local faster-whisper transcription and prompt-keyword scoring
- 1–5 clips per video, rough titles, social captions and hashtags
- Timestamp/transcript JSON output

## Limitations
This is a basic MVP, not a human-level automatic editor. It does not yet track faces, create reaction/gameplay split screens, visually overlay credits/subtitles, add effects, or publish to social media. Scores do not predict virality. Creator credit is stored in metadata only.

Long recordings can take considerable CPU time. The Whisper model downloads on first use, but later runs can work offline. Videos and processed files stay on your machine, under `outputs/`.

## Troubleshooting
- Python launcher missing: reinstall Python with PATH enabled.
- FFmpeg missing: run the winget command, then restart the terminal.
- Whisper installation problem: try `.venv\Scripts\python.exe -m pip install faster-whisper` or disable speech transcription.
- Export fails: check disk space and `ffmpeg -encoders` for `libx264`.
- Videos without audio are not well supported by the audio-ranking engine.

## License
MIT — see LICENSE.
