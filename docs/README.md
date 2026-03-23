# SnapBack

SnapBack is a lecture context recovery app for live classes. It supports a Zoom-style panel, a Google Meet Chrome extension, recap generation for missed lecture windows, transcript storage, export flows, and multiple host-adapter surfaces.

## Repository Layout

```text
snapback/
|-- apps/
|   |-- api/                  # FastAPI entrypoint and app startup
|   |-- zoom-app/             # React panel shell
|   `-- meet-extension/       # Google Meet Chrome extension
|-- services/
|   |-- analysis/             # recap intelligence, topic shift, summarization
|   |-- exporters/            # PDF, Markdown, Notion export logic
|   |-- storage/              # SQLite session, recap, transcript persistence
|   `-- transcription/        # AssemblyAI + whisper.cpp transcription client
|-- config/
|   `-- env/                  # environment templates and local env file
|-- docs/
|   `-- README.md             # project documentation
|-- data/                     # runtime database/audio output
`-- .gitignore
```

## Backend Setup

1. Create a virtual environment and install dependencies from [`apps/api/requirements.txt`](/Users/prana/OneDrive/Documents/Playground/snapback/apps/api/requirements.txt).
2. Copy [`config/env/.env.example`](/Users/prana/OneDrive/Documents/Playground/snapback/config/env/.env.example) to `config/env/.env`.
3. Add your AssemblyAI, Groq, and Notion keys to `config/env/.env`.
4. Start the API from the repo root:

```powershell
uvicorn apps.api.main:app --reload --port 8000
```

### Privacy Settings

- `AUTO_DELETE_AFTER_HOURS` controls how long sessions, recaps, transcript chunks, and saved audio files remain on disk.
- `TRANSCRIPTION_MODE=local` enables the `whisper.cpp` privacy path.
- `WHISPER_BINARY_PATH`, `WHISPER_MODEL_PATH`, `WHISPER_MODEL_URL`, `WHISPER_LANGUAGE`, `WHISPER_THREADS`, and `LOCAL_SEGMENT_SECONDS` tune local transcription.

### Transcription Client

Start a session first, then run the transcription client from the repo root:

```powershell
python -m services.transcription.transcription_client YOUR_SESSION_ID
python -m services.transcription.transcription_client YOUR_SESSION_ID --mode local
```

On first local run, SnapBack downloads the `ggml-base.en` whisper.cpp model automatically if it is missing.

## Frontend Setup

### Zoom App Panel

From [`apps/zoom-app`](/Users/prana/OneDrive/Documents/Playground/snapback/apps/zoom-app):

```powershell
npm install
npm run dev
```

### Chrome Extension

1. Open `chrome://extensions`.
2. Enable Developer Mode.
3. Load unpacked extension from [`apps/meet-extension`](/Users/prana/OneDrive/Documents/Playground/snapback/apps/meet-extension).

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
