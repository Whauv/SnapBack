# SnapBack

SnapBack is a lecture context recovery app for live classes. It supports a Zoom-style panel, a Google Meet Chrome extension, recap generation for missed lecture windows, transcript storage, export flows, and multiple host-adapter surfaces.

## Repository Layout

```text
snapback/
|-- apps/
|   |-- api/                  # FastAPI entrypoint and app startup
|   |-- zoom-app/             # React panel shell
|   `-- meet-extension/       # Google Meet Chrome extension
|-- tests/
|   |-- apps/                # tests mirrored to app surfaces
|   `-- services/            # tests mirrored to backend services
|-- services/
|   |-- analysis/             # recap intelligence, topic shift, summarization
|   |-- api/                  # auth, settings, rate limiting, session orchestration
|   |-- exporters/            # PDF, Markdown, Notion export logic
|   |-- storage/              # SQLite session, recap, transcript persistence
|   `-- transcription/        # AssemblyAI + whisper.cpp transcription client
|-- config/
|   `-- env/                  # environment templates and local env file
|-- docs/
|   `-- phase-8-roadmap.md    # upcoming roadmap
|-- data/                     # runtime database/audio output
|-- .github/                  # CI workflow and collaboration templates
`-- .gitignore
```

Each major folder now includes its own `README.md` so the structure can be navigated quickly without opening code first.

## Backend Setup

1. Create a virtual environment and install dependencies from [`apps/api/requirements.txt`](/Users/prana/OneDrive/Documents/Playground/snapback/apps/api/requirements.txt).
2. Copy either [`.env.example`](/Users/prana/OneDrive/Documents/Playground/snapback/.env.example) or [`config/env/.env.example`](/Users/prana/OneDrive/Documents/Playground/snapback/config/env/.env.example) to `config/env/.env`.
3. Add your AssemblyAI, Groq, and Notion keys to `config/env/.env`.
4. Set `SNAPBACK_API_TOKENS`. The default local token is `local-dev:snapback-local-dev-token`.
5. Start the API from the repo root:

```powershell
uvicorn apps.api.main:app --reload --port 8000
```

### Backend Quality Checks

Run the backend tests from the repo root:

```powershell
python -m unittest discover -s tests -t .
```

Run the frontend production build from [`apps/zoom-app`](/Users/prana/OneDrive/Documents/Playground/snapback/apps/zoom-app):

```powershell
npm.cmd run build
```

Run the extension contract test from the repo root:

```powershell
node --test tests/apps/meet_extension/host-adapter.test.mjs
```

### Privacy Settings

- `APP_ENV=production` disables development defaults and requires explicit API tokens.
- `SNAPBACK_API_TOKENS` configures bearer tokens in `label:token` format for scoped session ownership.
- `AUTO_DELETE_AFTER_HOURS` controls how long sessions, recaps, transcript chunks, and saved audio files remain on disk.
- `CORS_ALLOW_ORIGINS` configures which local frontend origins may call the API.
- `TRUSTED_HOSTS` restricts accepted host headers.
- `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS` cap per-principal request volume.
- `MAX_TRANSCRIPT_CHARS` and `MAX_AUDIO_CHUNK_BYTES` cap request sizes for transcript and audio uploads.
- the API also applies baseline security headers to every response for safer browser integration
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

The panel uses the same API token contract as the backend. Leave the default local token in place for local development, or override it in the Settings panel for a deployed environment.

### Chrome Extension

1. Open `chrome://extensions`.
2. Enable Developer Mode.
3. Load unpacked extension from [`apps/meet-extension`](/Users/prana/OneDrive/Documents/Playground/snapback/apps/meet-extension).

## Repository Automation

- [`Makefile`](/Users/prana/OneDrive/Documents/Playground/snapback/Makefile) provides shared lint, build, and test shortcuts.
- [`.github/workflows/ci.yml`](/Users/prana/OneDrive/Documents/Playground/snapback/.github/workflows/ci.yml) runs Ruff, backend tests, the Zoom app production build, and the Meet extension contract test on GitHub Actions.
- [`AGENTS.md`](/Users/prana/OneDrive/Documents/Playground/snapback/AGENTS.md) documents the repo map, setup, and validation commands for contributors and coding agents.

## Implemented Features

- FastAPI session lifecycle endpoints
- Service-layer API orchestration with dedicated auth, settings, telemetry, and rate-limiting modules
- SQLite transcript, recap, and audio chunk persistence
- Scoped session ownership enforced through bearer tokens
- Input validation for timestamps, session IDs, transcript sizes, and audio upload sizes
- Groq recap and keyword generation with fallback summaries
- Structured request logging, request IDs, trusted-host enforcement, and in-memory rate limiting
- Baseline response security headers and service-layer payload guardrails
- Backend integration tests for auth, ownership, recap/study-pack flows, validation errors, summarizer fallbacks, and alert detection
- Topic-shift and missed-alert detection
- PDF, Markdown, and Notion export endpoints
- AssemblyAI streaming and local `whisper.cpp` transcription client with reconnect, model bootstrap, and CLI startup flow
- Zoom-style React side panel with consent modal, absence timer, recap history, transcript drawer, persisted dark mode, and export actions
- Manifest V3 Chrome Extension with Meet pill launcher, consent-gated side panel, popup, and `Ctrl+Shift+L` catch-up hotkey
- Auto-delete cleanup for expired sessions and saved audio artifacts
- Shared frontend host-adapter structure for browser, Google Meet extension, Zoom app, and Teams app wrappers
- Google Meet extension popup and side panel now consume a shared Meet host adapter instead of directly wiring runtime calls in each file

## Phase 8

The next roadmap is documented in [`docs/phase-8-roadmap.md`](/Users/prana/OneDrive/Documents/Playground/snapback/docs/phase-8-roadmap.md).
The first Phase 8 slice now adds AI-generated study packs with outlines, flashcards, quiz questions, and review priorities.
