# API App

This folder contains the FastAPI entrypoint, app startup wiring, and backend dependency manifest for SnapBack.

- `main.py` keeps the public ASGI entrypoint stable
- `app_factory.py` builds the FastAPI application
- `dependencies.py` owns shared middleware, auth context, and service wiring
- `routes/` contains HTTP route modules grouped by concern
