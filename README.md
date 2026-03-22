# LectureLens

LectureLens is a Zoom App and Chrome Extension for lecture context recovery. It captures live transcript chunks, stores them locally in SQLite, and generates focused recap summaries for the exact period a student missed.

## Structure

```text
lecturelens/
├── backend/
│   ├── main.py
│   ├── transcription_client.py
│   ├── summarizer.py
│   ├── detector.py
│   ├── database.py
│   ├── export.py
│   ├── .env
│   └── data/
├── frontend/
│   ├── zoom-app/
│   └── chrome-extension/
└── README.md
```

## Backend Setup

1. Create a virtual environment and install dependencies from `backend/requirements.txt`.
2. Update `backend/.env` with your AssemblyAI, Groq, and Notion keys.
3. Start the API with `uvicorn main:app --reload --port 8000` from `backend/`.

### Phase 2 Transcription Client

1. Start a session with `POST /session/start` and copy the returned `session_id`.
2. Run `python transcription_client.py <session_id>` from `backend/` for cloud mode.
3. Run `python transcription_client.py <session_id> --mode local` for local `whisper.cpp` mode.
4. Optionally set `MICROPHONE_DEVICE_INDEX` in `backend/.env` if your default input device is not the right microphone.

## Frontend Setup

### Zoom App Panel

1. Run `npm install` in `frontend/zoom-app/`.
2. Run `npm run dev`.

### Chrome Extension

1. Open `chrome://extensions`.
2. Enable Developer Mode.
3. Load unpacked extension from `frontend/chrome-extension/`.

## Implemented Features

- FastAPI session lifecycle endpoints
- SQLite transcript and recap persistence
- Groq recap and keyword generation with fallback summaries
- Topic-shift and missed-alert detection
- PDF, Markdown, and Notion export endpoints
- AssemblyAI streaming and local `whisper.cpp` transcription client with reconnect and CLI startup flow
- Zoom-style React side panel with consent banner, absence timer, recap history, transcript drawer, dark mode, and export actions
- Manifest V3 Chrome Extension with Meet pill launcher, side panel, popup, and hotkey hook
