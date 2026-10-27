"""
FastAPI entrypoint.

Why this file exists:
- One place to wire the app together: routes, middleware, startup checks.
- Render runs `uvicorn app.main:app` — this is the `app` object it loads.
- Nothing else in the codebase imports FastAPI directly, so the framework stays swappable.

Deployment notes:
- CORS origins come from env, so local dev and Render don't collide.
- Startup validation fails fast if LLM_API_KEY is missing.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app import config


def _allowed_origins() -> list[str]:
    """
    Read CORS origins from environment.

    Why env-driven:
    - Local dev needs http://localhost:5173 (Vite default).
    - Render needs the deployed frontend URL.
    - Hardcoding either breaks the other. Env var solves both without code changes.

    Default "*" is safe for a POC but should be tightened in production.
    """
    raw = os.getenv("CORS_ORIGINS", "*").strip()
    if raw == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(
    title="Regulatory Knowledge Base API",
    version="0.1.0",
    description="RAG chat over regulatory rulebooks. Multi-jurisdiction by design.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# All API routes live under /api so a reverse proxy or static frontend
# can coexist on the same domain without path conflicts.
app.include_router(router, prefix="/api")


@app.on_event("startup")
def startup_check():
    """
    Fail fast if the app is misconfigured.

    Why crash at startup:
    - A missing API key discovered on the first chat request looks like a bug.
    - A missing API key discovered at boot looks like a config error — which it is.
    """
    config.validate_config()


@app.get("/")
def root():
    """Root endpoint — helpful for confirming the service is alive during deploy."""
    return {
        "service": "regulatory-knowledge-base",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health",
    }