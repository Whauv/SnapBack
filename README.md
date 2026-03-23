# SnapBack

SnapBack is a Zoom App and Chrome Extension for lecture context recovery. It captures live transcript chunks, stores them locally in SQLite, and generates focused recap summaries for the exact period a student missed.

## Structure

```text
snapback/
|-- backend/
|   |-- main.py
|   |-- transcription_client.py
|   |-- summarizer.py
|   |-- detector.py
|   |-- database.py
|   |-- export.py
|   |-- .env
|   `-- data/
|-- frontend/
|   |-- zoom-app/
|   |   |-- src/core/
|   |   |-- src/hosts/
|   |   `-- src/components/
|   `-- chrome-extension/
`-- README.md
```

## Backend Setup

1. Create a virtual environment and install dependencies from `backend/requirements.txt`.
2. Update `backend/.env` with your AssemblyAI, Groq, and Notion keys.
3. Start the API with `uvicorn main:app --reload --port 8000` from `backend/`.

### Phase 7 Privacy Defaults

- `AUTO_DELETE_AFTER_HOURS` controls how long sessions, recaps, transcript chunks, and saved audio files remain on disk.
- `TRANSCRIPTION_MODE=local` enables the `whisper.cpp` privacy path.
- `WHISPER_BINARY_PATH`, `WHISPER_MODEL_PATH`, `WHISPER_MODEL_URL`, `WHISPER_LANGUAGE`, `WHISPER_THREADS`, and `LOCAL_SEGMENT_SECONDS` tune local transcription.

### Transcription Client

1. Start a session with `POST /session/start` and copy the returned `session_id`.
2. Run `python transcription_client.py <session_id>` from `backend/` for cloud mode.
3. Run `python transcription_client.py <session_id> --mode local` for local `whisper.cpp` mode.
4. On first local run, SnapBack downloads the `ggml-base.en` whisper.cpp model automatically if it is missing.
5. Optionally set `MICROPHONE_DEVICE_INDEX` in `backend/.env` if your default input device is not the right microphone.

## Frontend Setup

### Zoom App Panel

1. Run `npm install` in `frontend/zoom-app/`.
2. Run `npm run dev`.
3. The current React app is now structured as a shared SnapBack panel plus host adapters. Today it ships with a browser-backed Zoom-style wrapper and scaffolding for Google Meet, Zoom, and Teams hosts.

### Chrome Extension

1. Open `chrome://extensions`.
2. Enable Developer Mode.
3. Load unpacked extension from `frontend/chrome-extension/`.

## Implemented Features

- FastAPI session lifecycle endpoints
- SQLite transcript, recap, and audio chunk persistence
- Groq recap and keyword generation with fallback summaries
- Topic-shift and missed-alert detection
- PDF, Markdown, and Notion export endpoints
- AssemblyAI streaming and local `whisper.cpp` transcription client with reconnect, model bootstrap, and CLI startup flow
- Zoom-style React side panel with consent modal, absence timer, recap history, transcript drawer, persisted dark mode, and export actions
- Manifest V3 Chrome Extension with Meet pill launcher, consent-gated side panel, popup, and `Ctrl+Shift+L` catch-up hotkey
- Auto-delete cleanup for expired sessions and saved audio artifacts
- Shared frontend host-adapter structure for browser, Google Meet extension, Zoom app, and Teams app wrappers
- Google Meet extension popup and side panel now consume a shared Meet host adapter instead of directly wiring runtime calls in each file
