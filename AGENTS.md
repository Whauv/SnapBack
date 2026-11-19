# SnapBack Agents Guide

## Setup

Backend:

```powershell
python -m venv apps/api/.venv
.\apps\api\.venv\Scripts\Activate.ps1
pip install -r apps/api/requirements.txt
copy .env.example config\env\.env
uvicorn apps.api.main:app --reload --port 8000
```

Frontend:

```powershell
cd apps/zoom-app
npm install
npm run dev
```

Extension test:

```powershell
node --test tests/apps/meet_extension/host-adapter.test.mjs
```

## Folder Map

- `apps/api`: FastAPI entrypoint and HTTP surface
- `apps/zoom-app`: React + TypeScript panel app
- `apps/meet-extension`: Google Meet extension assets
- `packages/shared`: framework-agnostic code shared by the frontends (plain ESM + `.d.ts`, no build step)
- `services`: shared Python domain and infrastructure services
- `config/env`: environment templates and local env storage
- `docs`: roadmap and supporting documents
- `tests`: mirrored test layout for apps and services
- `data`: runtime SQLite and audio artifacts

## Code Style

- Preserve business logic when restructuring files.
- Python uses Ruff and snake_case naming.
- TypeScript and extension code keep the existing Vite and browser module conventions.
- Keep secrets out of source and use `.env` files or browser settings only for local development.

## Test Commands

```powershell
ruff check .
python -m unittest discover -s tests -t .
cd apps/zoom-app; npm run lint
cd apps/zoom-app; npm run build
cd apps/zoom-app; npm test
node --test tests/packages/shared/*.test.mjs tests/apps/meet_extension/*.test.mjs
```

The frontends share code via `packages/shared` (plain ESM). The zoom-app imports
it through the `@snapback/shared` Vite/TS alias; the Meet extension has no
bundler, so run `npm run sync:shared` from the repo root after changing
`packages/shared` to refresh the copy under `apps/meet-extension/src/shared`.
