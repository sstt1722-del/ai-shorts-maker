# AI Shorts Maker

A Streamlit web app that analyzes an uploaded MP4 video, finds the 3 loudest reaction moments in the audio, and automatically generates vertical 9:16 shorts (15 seconds each) with Korean hook captions.

## Run & Operate

- `streamlit run app.py --server.port 5000` — run the Streamlit app
- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- Required env: `DATABASE_URL` — Postgres connection string

## Stack

- Python 3, Streamlit
- moviepy==1.0.3 for video processing
- PIL/Pillow for caption rendering
- numpy for audio analysis
- pnpm workspaces, Node.js 24, TypeScript 5.9 (API side)
- API: Express 5
- DB: PostgreSQL + Drizzle ORM

## Where things live

- `app.py` — main Streamlit application
- `requirements.txt` — Python dependencies

## Architecture decisions

- Audio is sampled at 10 fps using moviepy's `to_soundarray`, then RMS-smoothed to find peak energy moments.
- Clips are center-cropped to 9:16 (1080×1920) using moviepy's `crop`.
- Captions are burned into frames using PIL RGBA compositing to support Korean Unicode text with noto-fonts-cjk-sans.
- Generated video bytes are stored in `st.session_state` so previews persist across Streamlit reruns.
- `ultrafast` libx264 preset is used to keep encoding fast at the cost of slight file size increase.

## Product

Users upload an MP4, click "Generate Shorts", and get 3 downloadable vertical shorts with a Korean hook caption at the top and "끝까지 보면 이해됨" at the bottom.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- Korean font requires `noto-fonts-cjk-sans` system package installed via Nix.
- moviepy is pinned to 1.0.3; do not upgrade — breaking API changes in 2.x.
- ffmpeg must be installed as a system dependency for moviepy to encode output.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
