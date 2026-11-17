import os
import re
import tempfile
import subprocess
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="ShafiqueClip", page_icon="🎬", layout="wide")

st.markdown("""
<style>
.main {background:#0b1020;color:#f5f7fb}
.block-container {padding-top:2rem;max-width:1100px}
.hero {padding:28px;border:1px solid #26324d;border-radius:18px;background:linear-gradient(120deg,#151f39,#101729)}
.hero h1 {font-size:2.6rem;margin:0}
.hero p {color:#b9c4d8;font-size:1.05rem}
.stButton>button {background:#6c5ce7;color:white;border:0;border-radius:10px;padding:.65rem 1.2rem}
.small {color:#9aa8bf;font-size:.9rem}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>🎬 ShafiqueClip</h1>
  <p>Turn long videos into short vertical clips.</p>
  <span class="small">Paste a video link • Detect speech • Create Shorts • Download MP4</span>
</div>
""", unsafe_allow_html=True)

st.write("")
st.info("Use only videos you own or have permission to download and edit. YouTube's terms and the creator's rights still apply.")

with st.sidebar:
    st.header("Clip settings")
    clip_len = st.slider("Target clip length (seconds)", 15, 90, 45, 5)
    max_clips = st.slider("Maximum clips", 1, 10, 5)
    make_vertical = st.checkbox("Convert to vertical 9:16", value=True)
    burn_captions = st.checkbox("Burn captions into video", value=True)
    st.caption("First-run AI transcription may take time. Free hosting has CPU, memory and storage limits.")

url = st.text_input("YouTube or direct video URL", placeholder="Paste your video link here...")
uploaded = st.file_uploader("Or upload a video file", type=["mp4", "mov", "mkv", "webm"])

def run_cmd(args):
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-2500:] or "Command failed")
    return p.stdout

def safe_name(name):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name)[:50] or "video"

def make_srt(segments, start, end, path):
    def stamp(sec):
        ms = int(round(sec * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    rows = []
    idx = 1
    for seg in segments:
        a, b = max(seg["start"], start), min(seg["end"], end)
        if b <= a:
            continue
        txt = seg["text"].strip().replace("-->", "→")
        if not txt:
            continue
        rows.append(f"{idx}\n{stamp(a-start)} --> {stamp(b-start)}\n{txt}\n")
        idx += 1
    Path(path).write_text("\n".join(rows), encoding="utf-8")

def choose_clips(segments, duration, target, limit):
    # Create candidate windows around spoken content; rank by speech density.
    windows = []
    step = max(10, target // 2)
    start = 0
    while start < duration:
        end = min(duration, start + target)
        if end - start >= 12:
            words = sum(len(s["text"].split()) for s in segments if s["start"] < end and s["end"] > start)
            covered = sum(max(0, min(s["end"], end)-max(s["start"], start)) for s in segments)
            score = words + covered * 1.5
            windows.append((score, start, end))
        start += step
    windows.sort(reverse=True)
    selected = []
    for score, a, b in windows:
        if all(b <= x or a >= y for _, x, y in selected):
            selected.append((score, a, b))
        if len(selected) >= limit:
            break
    return sorted(selected, key=lambda x: x[1])

def process_video(video_path, workdir):
    st.write("### 1. Reading video")
    probe = run_cmd(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path])
    duration = float(probe.strip())
    st.write(f"Video duration: **{int(duration//60)} min {int(duration%60)} sec**")

    st.write("### 2. Transcribing audio with Whisper")
    try:
        import whisper
    except Exception as e:
        raise RuntimeError("Whisper is not installed. Check requirements.txt and redeploy.") from e
    model = whisper.load_model("tiny")
    result = model.transcribe(video_path, fp16=False, verbose=False)
    segments = result.get("segments", [])
    if not segments:
        raise RuntimeError("No speech was detected in this video.")

    candidates = choose_clips(segments, duration, clip_len, max_clips)
    if not candidates:
        raise RuntimeError("Could not create clips from this video.")

    st.write("### 3. Creating clips")
    outputs = []
    progress = st.progress(0)
    for i, (_, start, end) in enumerate(candidates, 1):
        out = os.path.join(workdir, f"shafiqueclip_{i:02}.mp4")
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        if not make_vertical:
            vf = "scale=1280:-2"
        cmd = ["ffmpeg", "-y", "-ss", str(start), "-i", video_path, "-t", str(end-start), "-vf", vf]
        if burn_captions:
            srt = os.path.join(workdir, f"clip_{i:02}.srt")
            make_srt(segments, start, end, srt)
            escaped = srt.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
            cmd += ["-vf", vf + f",subtitles='{escaped}'"]
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out]
        run_cmd(cmd)
        outputs.append((out, start, end))
        progress.progress(i / len(candidates))
    return outputs

if st.button("✨ Generate Shorts", type="primary", use_container_width=True):
    if not url.strip() and uploaded is None:
        st.error("Please paste a video link or upload a video.")
    else:
        with tempfile.TemporaryDirectory() as workdir:
            video_path = os.path.join(workdir, "source_video.mp4")
            try:
                with st.spinner("Preparing your video..."):
                    if uploaded is not None:
                        with open(video_path, "wb") as f:
                            f.write(uploaded.getbuffer())
                    else:
                        # yt-dlp is used only for user-authorized content.
                        run_cmd(["yt-dlp", "--no-playlist", "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b", "--merge-output-format", "mp4", "-o", video_path, url.strip()])
                        if not os.path.exists(video_path):
                            # yt-dlp may append an extension depending on source/container.
                            matches = list(Path(workdir).glob("source_video*"))
                            if not matches:
                                raise RuntimeError("Could not locate downloaded video.")
                            video_path = str(matches[0])
                outputs = process_video(video_path, workdir)
                st.success(f"Created {len(outputs)} clips.")
                for i, (path, start, end) in enumerate(outputs, 1):
                    st.markdown(f"**Short {i}** · {int(start)}s – {int(end)}s")
                    st.video(path)
                    with open(path, "rb") as f:
                        st.download_button(f"Download Short {i}", f.read(), file_name=f"shafiqueclip_{i:02}.mp4", mime="video/mp4", key=f"dl{i}")
            except Exception as e:
                st.error(f"Processing failed: {e}")
                st.warning("Tip: try a shorter video or upload an MP4. Free hosting may not have enough memory/CPU for long videos.")
                st.caption("This MVP ranks windows by speech activity. It does not yet understand story context or guarantee viral moments.")
