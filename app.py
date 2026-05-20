import streamlit as st
import tempfile
import random
from pathlib import Path

import numpy as np
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip

st.set_page_config(page_title="AI Shorts Maker", page_icon="🎬")

st.title("🎬 AI Shorts Maker")
st.write("MP4 영상을 업로드하면 소리 큰 구간을 찾아 쇼츠 후보를 자동 생성합니다.")

uploaded_file = st.file_uploader(
    "MP4 영상 업로드",
    type=["mp4", "mov", "mkv", "webm"]
)

shorts_length = st.slider("쇼츠 길이(초)", 8, 30, 15)
candidate_count = st.slider("후보 개수", 1, 5, 3)

hooks = [
    "이 장면 하나로 분위기 터짐ㅋㅋ",
    "끝까지 보면 이해됨",
    "여기서 반응 터졌습니다",
    "이건 못 참지ㅋㅋ",
    "댓글창 난리날 장면"
]

def sec_to_time(sec):
    sec = int(sec)
    return f"{sec // 60:02d}:{sec % 60:02d}"

def get_audio_scores(video, window_sec=1.0):
    if video.audio is None:
        return []

    scores = []
    fps = 16000

    for start in np.arange(0, video.duration, window_sec):
        end = min(start + window_sec, video.duration)

        try:
            audio = video.audio.subclip(start, end).to_soundarray(fps=fps)

            if audio.ndim == 2:
                audio = audio.mean(axis=1)

            rms = float(np.sqrt(np.mean(audio ** 2)))
            peak = float(np.max(np.abs(audio)))
            score = rms * 0.7 + peak * 0.3

            scores.append((float(start), score))

        except Exception:
            continue

    return scores

def pick_segments(scores, duration, shorts_length, count):
    if not scores:
        return [(0, min(shorts_length, duration))]

    sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)

    selected = []
    min_gap = max(8, shorts_length)

    for peak_time, score in sorted_scores:
        start = max(0, peak_time - shorts_length * 0.35)
        end = min(duration, start + shorts_length)

        if end - start < shorts_length:
            start = max(0, end - shorts_length)

        if all(abs(start - s) > min_gap for s, e in selected):
            selected.append((start, end))

        if len(selected) >= count:
            break

    return selected

def make_vertical_clip(video, start, end):
    clip = video.subclip(start, end)

    target_w = 1080
    target_h = 1920

    clip = clip.resize(height=target_h)

    if clip.w < target_w:
        clip = clip.resize(width=target_w)

    x_center = clip.w / 2
    x1 = max(0, x_center - target_w / 2)

    clip = clip.crop(x1=x1, y1=0, width=target_w, height=target_h)

    return clip

def render_short(input_path, output_path, start, end, hook):
    video = VideoFileClip(str(input_path))
    clip = make_vertical_clip(video, start, end)

    try:
        title = TextClip(
            hook,
            fontsize=64,
            color="white",
            stroke_color="black",
            stroke_width=3,
            method="caption",
            size=(980, None),
            align="center"
        ).set_position(("center", 130)).set_duration(clip.duration)

        bottom = TextClip(
            "끝까지 보면 이해됨",
            fontsize=54,
            color="white",
            stroke_color="black",
            stroke_width=3,
            method="caption",
            size=(980, None),
            align="center"
        ).set_position(("center", 1560)).set_duration(clip.duration)

        final = CompositeVideoClip([clip, title, bottom])

    except Exception:
        final = clip

    final.write_videofile(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        fps=30,
        preset="veryfast",
        threads=2
    )

    video.close()
    clip.close()
    final.close()

if uploaded_file:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        input_path = temp_dir / uploaded_file.name
        input_path.write_bytes(uploaded_file.read())

        if st.button("AI 쇼츠 후보 만들기"):
            with st.spinner("영상 분석 중입니다..."):
                video = VideoFileClip(str(input_path))
                scores = get_audio_scores(video)
                segments = pick_segments(
                    scores,
                    video.duration,
                    shorts_length,
                    candidate_count
                )
                video.close()

            st.success("쇼츠 후보 생성 완료!")

            for idx, (start, end) in enumerate(segments, 1):
                hook = random.choice(hooks)
                output_path = temp_dir / f"shorts_candidate_{idx}.mp4"

                with st.spinner(f"{idx}번 후보 생성 중..."):
                    render_short(input_path, output_path, start, end, hook)

                st.subheader(f"후보 {idx}")
                st.write(f"구간: {sec_to_time(start)} ~ {sec_to_time(end)}")
                st.write(f"후킹: {hook}")
                st.video(str(output_path))

                with open(output_path, "rb") as f:
                    st.download_button(
                        f"후보 {idx} 다운로드",
                        f,
                        file_name=f"shorts_candidate_{idx}.mp4",
                        mime="video/mp4"
                    )
