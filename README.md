# ShafiqueClip

A starter MVP for a personal AI Shorts generator built with Streamlit, FFmpeg, yt-dlp and Whisper.

## Important
- Process only videos you own or are authorised to download and edit.
- Respect YouTube's Terms of Service, copyright and creator permissions.
- This first version finds speech-heavy time windows. It is not equivalent to OpusClip's semantic/viral-moment AI.
- Streamlit Community Cloud is not suitable for long/heavy video processing; free CPU, memory, execution-time and storage limits apply.

## Run locally (Windows)
1. Install Python 3.10 or 3.11.
2. Install FFmpeg and ensure `ffmpeg` and `ffprobe` are available in PATH.
3. Extract this folder.
4. Open Command Prompt in this folder and run:

   ```bat
   py -m venv .venv
   .venv\\Scripts\\activate
   pip install -r requirements.txt
   streamlit run app.py
   ```

5. Open the local address shown in the terminal.

## Deploy free
1. Create a GitHub account and a new public repository named `shafiqueclip`.
2. Upload `app.py`, `requirements.txt`, `packages.txt`, and `README.md`.
3. Open Streamlit Community Cloud and connect GitHub.
4. Select repository `shafiqueclip`, branch `main`, and main file `app.py`.
5. Deploy. If the free host runs out of resources, use local processing.

The free subdomain is assigned by Streamlit and may not exactly match `shafiqueclip.streamlit.app` until the app is deployed and the name is available.
