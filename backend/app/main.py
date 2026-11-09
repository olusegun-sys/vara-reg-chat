"""
FastAPI entrypoint.

Why this file exists:
- One place to wire the app together: routes, middleware, startup checks.
- Render runs `uvicorn app.main:app` — this is the `app` object it loads.
- Nothing else in the codebase imports FastAPI directly, so the framework stays swappable.

Deployment notes:
- CORS origins come from env, so local dev and Render don't collide.
- Startup validation fails fast if LLM_API_KEY is missing.
- `timeout_keep_alive` is raised so long streaming responses (RAG + Critic)
  don't get their HTTP connection killed mid-stream.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app import config


# --- Keep-alive default ---
# Uvicorn's default is 5 seconds. That kills a streaming connection whenever
# the backend is silent for more than 5s (e.g. while the Critic runs).
# We raise it to 120s so long LLM calls can complete before the socket closes.
# On Render this MUST also be set via the start command flag, because the
# `if __name__ == "__main__"` block below never executes there.
DEFAULT_KEEP_ALIVE = 120


def _cors_config() -> dict:
    """
    Build CORS middleware kwargs from environment.

    Why this shape:
    - allow_origins=["*"] + allow_credentials=True is ILLEGAL per W3C spec.
      The browser silently discards the wildcard header, which manifests as
      a misleading "No 'Access-Control-Allow-Origin' header" error.
    - To allow credentials from any origin, the spec-compliant path is
      allow_origin_regex=".*" (regex wildcard), NOT allow_origins=["*"].
    - If specific origins are provided, use allow_origins normally.
    """
    raw = os.getenv("CORS_ORIGINS", "*").strip()

    if raw == "*":
        # Wildcard mode: allow any origin, but via regex (required when
        # credentials are enabled — allow_origins=["*"] would be rejected).
        return {
            "allow_origin_regex": ".*",
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }

    # Explicit list mode: comma-separated origins from env.
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return {
        "allow_origins": origins,
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup + shutdown in one place.

    Why this replaces @app.on_event("startup"):
    - @app.on_event is deprecated in FastAPI and will be removed.
    - The lifespan context manager is the documented modern replacement.
    - Behaviour is identical: validate_config() runs once at boot and
      raises if required env vars are missing, so the process fails fast.
    """
    config.validate_config()  # fail fast at boot on missing env vars (unchanged behaviour)
    yield
    # (No teardown work needed today — kept here so future cleanup has a home.)


app = FastAPI(
    title="Regulatory Knowledge Base API",
    version="0.1.0",
    description="RAG chat over regulatory rulebooks. Multi-jurisdiction by design.",
    lifespan=lifespan,  # wire the startup/shutdown hook above
)

app.add_middleware(CORSMiddleware, **_cors_config())

# All API routes live under /api so a reverse proxy or static frontend
# can coexist on the same domain without path conflicts.
app.include_router(router, prefix="/api")


@app.get("/")
def root():
    """Root endpoint — helpful for confirming the service is alive during deploy."""
    return {
        "service": "regulatory-knowledge-base",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    # Local dev convenience: `python -m app.main` picks up the raised timeout.
    # On Render, this block is NOT executed — see render.yaml / Procfile note in docs.
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        timeout_keep_alive=DEFAULT_KEEP_ALIVE,  # raised from Uvicorn's default 5s
    )