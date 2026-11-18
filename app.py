import os
import re
import tempfile
import subprocess
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="ShafiqueClip Cloud", page_icon="🎬", layout="wide")

st.markdown("""
<style>
.stApp {background: #0b1020; color: #f5f7fb}
.block-container {max-width: 1180px; padding-top: 2rem}
.hero {padding: 28px; border: 1px solid #293653; border-radius: 18px;
       background: linear-gradient(120deg,#182544,#101729); margin-bottom: 18px}
.hero h1 {font-size: 2.5rem; margin: 0}
.hero p {color: #bdc9df; margin-bottom: 0}
.stButton>button {border-radius: 10px; font-weight: 700}
.small-note {color: #9eacc4; font-size: .88rem}
</style>
<div class="hero">
  <h1>🎬 ShafiqueClip</h1>
  <p>Long video se highlights banao. Captions style karo. Shorts export karo.</p>
  <div class="small-note">Cloud edition · Full-screen video · No facecam or split-screen</div>
</div>
""", unsafe_allow_html=True)

st.info("Sirf wahi videos import karein jinhe download aur edit karne ki permission aapke paas hai.")

with st.sidebar:
    st.header("⚙️ Clip settings")
    clip_len = st.slider("Har clip ki duration", 15, 180, 45, 5, format="%d sec")
    max_clips = st.slider("Kitne clips banane hain?", 1, 20, 5)
    st.divider()
    st.header("📱 Video format")
    aspect = st.selectbox("Platform / aspect ratio", [
        "YouTube Shorts / Instagram Reels (9:16)",
        "Instagram Feed (1:1)",
        "YouTube Landscape (16:9)"
    ])
    resolution = st.selectbox("Export quality", ["720p", "1080p", "4K"], index=1)
    st.divider()
    st.header("💬 Captions")
    captions_on = st.checkbox("Captions add karo", value=True)
    caption_language = st.selectbox("Caption language", [
        "Auto detect", "Hindi / Hinglish", "English"
    ])
    caption_style = st.selectbox("Caption design", [
        "Neon Pop", "Bold Creator", "Clean White", "Minimal"
    ])
    st.caption("Hindi words ko Roman script mein convert karne ki koshish hogi. Recognition quality audio par depend karti hai.")

url = st.text_input("Video URL", placeholder="YouTube ya direct video URL paste karein")
uploaded = st.file_uploader("Ya apni video upload karein", type=["mp4", "mov", "mkv", "webm"])

def run_cmd(args):
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or "Command failed")[-3000:])
    return p.stdout

def output_size():
    if aspect.startswith("YouTube Shorts"):
        dims = {"720p": (720, 1280), "1080p": (1080, 1920), "4K": (2160, 3840)}
    elif aspect.startswith("Instagram Feed"):
        dims = {"720p": (720, 720), "1080p": (1080, 1080), "4K": (2160, 2160)}
    else:
        dims = {"720p": (1280, 720), "1080p": (1920, 1080), "4K": (3840, 2160)}
    return dims[resolution]

def romanize_hindi(text):
    if not re.search(r"[ऀ-ॿ]", text):
        return text
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
        return transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    except Exception:
        return text

def stamp(sec):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def make_srt(segments, start, end, path):
    rows = []
    idx = 1
    for seg in segments:
        a, b = max(float(seg["start"]), start), min(float(seg["end"]), end)
        if b <= a:
            continue
        txt = seg.get("text", "").strip().replace("-->", "→")
        if caption_language == "Hindi / Hinglish":
            txt = romanize_hindi(txt)
        if txt:
            rows.append(f"{idx}\n{stamp(a-start)} --> {stamp(b-start)}\n{txt}\n")
            idx += 1
    Path(path).write_text("\n".join(rows), encoding="utf-8")

def choose_clips(segments, duration, target, limit):
    # Fast transcript-based ranking: speech density plus energetic keywords.
    keywords = ("wow", "amazing", "crazy", "unbelievable", " जीत", "जीत", "भाई", "देखो",
                "secret", "finally", "wait", "अरे", "क्या", "सबसे", "best", "challenge")
    windows = []
    step = max(8, target // 3)
    start = 0.0
    while start < duration:
        end = min(duration, start + target)
        if end - start >= min(12, target):
            relevant = [s for s in segments if float(s["start"]) < end and float(s["end"]) > start]
            words = sum(len(s.get("text", "").split()) for s in relevant)
            covered = sum(max(0, min(float(s["end"]), end) - max(float(s["start"]), start)) for s in relevant)
            text = " ".join(s.get("text", "").lower() for s in relevant)
            energy = sum(text.count(k) for k in keywords)
            score = words + covered * 1.5 + energy * 8
            windows.append((score, start, end))
        start += step
    windows.sort(reverse=True)
    selected = []
    for score, a, b in windows:
        if all(b <= x or a >= y for _, x, y in selected):
            selected.append((score, a, b))
        if len(selected) >= limit:
            break
    return sorted(selected, key=lambda item: item[1])

def subtitle_filter(srt_path):
    escaped = srt_path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    styles = {
        "Neon Pop": "FontName=Arial,FontSize=34,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00FF35D5,BorderStyle=1,Outline=4,Shadow=1,Alignment=2,MarginV=110",
        "Bold Creator": "FontName=Arial,FontSize=38,Bold=1,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=4,Shadow=2,Alignment=2,MarginV=110",
        "Clean White": "FontName=Arial,FontSize=34,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=100",
        "Minimal": "FontName=Arial,FontSize=29,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Alignment=2,MarginV=80"
    }
    return f"subtitles='{escaped}':force_style='{styles[caption_style]}'"

def process_video(video_path, workdir):
    st.write("### 1. Video check")
    probe = run_cmd(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", video_path])
    duration = float(probe.strip())
    st.write(f"Video duration: **{int(duration // 60)} min {int(duration % 60)} sec**")

    st.write("### 2. Audio transcription")
    import whisper
    model = whisper.load_model("tiny")
    options = {"fp16": False, "verbose": False}
    if caption_language == "Hindi / Hinglish":
        options["language"] = "hi"
    elif caption_language == "English":
        options["language"] = "en"
    result = model.transcribe(video_path, **options)
    segments = result.get("segments", [])
    if not segments:
        raise RuntimeError("Speech detect nahi hui. Video mein clear voice check karein.")

    candidates = choose_clips(segments, duration, clip_len, max_clips)
    if not candidates:
        raise RuntimeError("Is video se clips nahi ban paaye.")

    st.write("### 3. Clips render ho rahe hain")
    width, height = output_size()
    vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
    outputs = []
    progress = st.progress(0)
    for i, (_, start, end) in enumerate(candidates, 1):
        out = os.path.join(workdir, f"shafiqueclip_{i:02}.mp4")
        filters = vf
        if captions_on:
            srt = os.path.join(workdir, f"clip_{i:02}.srt")
            make_srt(segments, start, end, srt)
            filters += "," + subtitle_filter(srt)
        cmd = ["ffmpeg", "-y", "-ss", str(start), "-i", video_path,
               "-t", str(end-start), "-vf", filters,
               "-c:v", "libx264", "-preset", "veryfast",
               "-crf", "20" if resolution == "4K" else "23",
               "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out]
        run_cmd(cmd)
        outputs.append((out, start, end))
        progress.progress(i / len(candidates))
    return outputs

if st.button("✨ Generate Clips", type="primary", use_container_width=True):
    if not url.strip() and uploaded is None:
        st.error("Pehle video URL paste karein ya video upload karein.")
    else:
        with tempfile.TemporaryDirectory() as workdir:
            video_path = os.path.join(workdir, "source_video.mp4")
            try:
                with st.spinner("Video prepare ho rahi hai..."):
                    if uploaded is not None:
                        with open(video_path, "wb") as f:
                            f.write(uploaded.getbuffer())
                    else:
                        run_cmd(["yt-dlp", "--no-warnings", "--no-playlist",
                                 "--js-runtimes", "deno",
                                 "--remote-components", "ejs:github",
                                 "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
                                 "--merge-output-format", "mp4",
                                 "-o", os.path.join(workdir, "source_video.%(ext)s"),
                                 url.strip()])
                        matches = list(Path(workdir).glob("source_video.*"))
                        matches = [p for p in matches if p.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov")]
                        if not matches:
                            raise RuntimeError("Download command complete hua, lekin video file nahi mili.")
                        video_path = str(matches[0])
                outputs = process_video(video_path, workdir)
                st.success(f"{len(outputs)} clips ready!")
                st.caption(f"Format: {aspect} · Export: {resolution} · Captions: {'On' if captions_on else 'Off'}")
                for i, (path, start, end) in enumerate(outputs, 1):
                    st.markdown(f"**Clip {i}** · {int(start)}s se {int(end)}s")
                    st.video(path)
                    with open(path, "rb") as f:
                        st.download_button(f"⬇️ Download Clip {i}", f.read(),
                                           file_name=f"shafiqueclip_{i:02}.mp4",
                                           mime="video/mp4", key=f"download_{i}")
            except Exception as e:
                st.error(f"Processing error: {e}")
                st.warning("Free cloud hosting par long videos aur 4K rendering resource limit ki wajah se fail ya slow ho sakti hai.")
                st.caption("Highlight selection abhi transcript speech/keyword scoring hai; full story-understanding viral AI abhi included nahi hai.")
