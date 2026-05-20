import streamlit as st
import yt_dlp
import tempfile
import os
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

KOREAN_HOOK_CAPTIONS = [
    "이 장면 하나로 분위기 터짐ㅋㅋ",
    "이거 보고 소름 돋았잖아",
    "이 순간이 핵심임",
]
BOTTOM_CAPTION = "끝까지 보면 이해됨"
def download_youtube(url, output_path):
    ydl_opts = {
        "format": "mp4",
        "outtmpl": output_path,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
TARGET_W, TARGET_H = 720, 1280
CLIP_DURATION = 15


def find_korean_font():
    try:
        result = subprocess.run(
            ["fc-list", ":lang=ko"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split("\n"):
            if line:
                path = line.split(":")[0].strip()
                if os.path.exists(path):
                    return path
    except Exception:
        pass
    candidates = [
        "/run/current-system/sw/share/fonts/noto-cjk-sans/NotoSansCJK-Regular.ttc",
        "/run/current-system/sw/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def make_caption_overlay(top_text, bottom_text, w, h, font_path):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    def draw_label(text, position, size):
        try:
            font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (w - tw) // 2
        pad = 18
        y = 80 if position == "top" else h - th - 80
        draw.rectangle([x - pad, y - pad, x + tw + pad, y + th + pad], fill=(0, 0, 0, 185))
        draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 180))
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

    draw_label(top_text, "top", 44)
    draw_label(bottom_text, "bottom", 36)
    return img


def analyze_peaks(video_path, n=3, dur=CLIP_DURATION):
    from moviepy.editor import VideoFileClip
    clip = VideoFileClip(video_path)
    duration = clip.duration
    if clip.audio is None or duration <= dur:
        clip.close()
        step = max(0, duration - dur) / max(1, n - 1)
        return [i * step for i in range(n)]
    fps = 10
    try:
        arr = clip.audio.to_soundarray(fps=fps)
        rms = np.sqrt(np.mean(arr ** 2, axis=1)) if arr.ndim > 1 else np.abs(arr)
        smooth = np.convolve(rms, np.ones(fps) / fps, mode="same")
        min_sep = int(fps * dur)
        peaks, temp = [], smooth.copy()
        for _ in range(n):
            idx = int(np.argmax(temp))
            t = max(0.0, min(idx / fps - dur / 2, duration - dur))
            peaks.append(t)
            lo, hi = max(0, idx - min_sep), min(len(temp), idx + min_sep)
            temp[lo:hi] = 0
    except Exception:
        step = max(0, duration - dur) / max(1, n - 1)
        peaks = [i * step for i in range(n)]
    clip.close()
    return sorted(peaks)


def create_short(input_path, start, output_path, top_text, bottom_text, font_path, overlay_path):
    overlay_img = make_caption_overlay(top_text, bottom_text, TARGET_W, TARGET_H, font_path)
    overlay_img.save(overlay_path)

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", input_path,
        "-t", str(CLIP_DURATION),
        "-i", overlay_path,
        "-filter_complex",
        (
            f"[0:v]scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase,"
            f"crop={TARGET_W}:{TARGET_H}[v];"
            "[v][1:v]overlay=0:0[out]"
        ),
        "-map", "[out]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28",
        "-c:a", "aac",
        "-shortest",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-800:])


# ── Streamlit UI ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="AI Shorts Maker", page_icon="🎬", layout="centered")
st.title("🎬 AI Shorts Maker")
st.caption("Upload an MP4 — the app finds the 3 loudest moments and creates vertical 9:16 shorts with Korean captions.")

youtube_url = st.text_input("YouTube URL")

uploaded_file = st.file_uploader("Upload MP4 Video", type=["mp4"])

if not uploaded_file and not youtube_url:
    st.stop()

st.success(f"Uploaded: **{uploaded_file.name}**")

if st.button("✂️ Generate Shorts", type="primary", use_container_width=True):
    font_path = find_korean_font()

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.mp4")
      if uploaded_file:
    with open(input_path, "wb") as f:
        f.write(uploaded_file.read())

elif youtube_url:
    st.info("Downloading YouTube video...")
    download_youtube(youtube_url, input_path)

        with st.spinner("🔊 Analyzing audio…"):
            peaks = analyze_peaks(input_path)

        st.info(f"Peak moments: {', '.join(f'{t:.1f}s' for t in peaks)}")

        results = []
        for i, (start, caption) in enumerate(zip(peaks, KOREAN_HOOK_CAPTIONS)):
            with st.spinner(f"Rendering short {i + 1} / 3…"):
                out_path = os.path.join(tmpdir, f"short_{i + 1}.mp4")
                overlay_path = os.path.join(tmpdir, f"overlay_{i + 1}.png")
                try:
                    create_short(input_path, start, out_path, caption, BOTTOM_CAPTION, font_path, overlay_path)
                    with open(out_path, "rb") as f:
                        results.append((f.read(), caption, start))
                except Exception as e:
                    st.error(f"Short {i + 1} failed: {e}")
                    results.append((None, caption, start))

        st.session_state["results"] = results
        st.session_state["peaks"] = peaks

if st.session_state.get("results"):
    st.divider()
    st.subheader("🎥 Your Shorts")
    for i, (video_bytes, caption, start) in enumerate(st.session_state["results"]):
        if video_bytes is None:
            st.warning(f"Short {i + 1} could not be generated.")
            continue
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"**Short {i + 1}** — starts at {start:.1f}s")
            st.caption(f"🔝 {caption}  |  ⬇️ {BOTTOM_CAPTION}")
        with col2:
            st.download_button(
                label="⬇️ Save",
                data=video_bytes,
                file_name=f"short_{i + 1}.mp4",
                mime="video/mp4",
                use_container_width=True,
            )
        st.video(video_bytes)
        st.divider()
