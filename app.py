import streamlit as st
import yt_dlp
import os

st.set_page_config(page_title="AI Shorts Maker")

st.title("🎬 AI Shorts Maker")

youtube_url = st.text_input("YouTube URL 입력")

if st.button("영상 다운로드 시작"):

    if youtube_url == "":
        st.warning("유튜브 링크를 입력하세요.")
    else:

        output_path = "downloads"

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        ydl_opts = {
            'outtmpl': f'{output_path}/%(title)s.%(ext)s',
            'format': 'mp4'
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])

            st.success("다운로드 완료!")

        except Exception as e:
            st.error(f"에러 발생: {e}")
