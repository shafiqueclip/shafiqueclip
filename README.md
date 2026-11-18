# ShafiqueClip Cloud

A browser-based video clipping starter built with Streamlit, FFmpeg, yt-dlp and Whisper.

## Current features
- Import an uploaded video or a URL (only content you are authorised to download/edit).
- Choose clip duration from 15 to 180 seconds and request 1–20 clips.
- Export vertical 9:16, square 1:1, or landscape 16:9.
- Select 720p, 1080p, or 4K output dimensions.
- Optional subtitles with four visual styles.
- Hindi transcription mode attempts Devanagari-to-Roman transliteration for Roman Hinglish captions.
- Full-frame video only. No facecam detection, facecam tracking, or split-screen.

## Important limitations
- Highlight ranking is a lightweight transcript speech-density and keyword heuristic. It is **not** semantic viral-moment understanding and cannot guarantee viral clips.
- Whisper Tiny is used to keep resource use lower; recognition accuracy depends on audio quality and language.
- The 4K option sets 4K output dimensions; it does not create missing source detail. Rendering 4K is resource-intensive.
- Free cloud hosting has CPU, memory, storage, upload-size, and execution-time limits. Long 3–4 hour videos and 4K exports may time out or run out of resources. Free hosting is not unlimited or guaranteed fast.
- This app does not provide Hindi dubbing or voice replacement.
- Use only videos you own or have permission to download and edit. Follow the source platform's terms and copyright rules.

## Run locally on Windows
1. Install Python 3.10 or 3.11.
2. Install FFmpeg and ensure `ffmpeg` and `ffprobe` work in Command Prompt.
3. In this folder, run:
   ```bat
   py -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   streamlit run app.py
   ```
4. Open the local URL shown in the terminal.

## Deploy
This repository can be connected to Streamlit Community Cloud using `app.py` as the main file. Cloud deployment is a separate step and is not completed merely by pushing code to GitHub. Free hosting may not have enough resources for long-form video processing.
