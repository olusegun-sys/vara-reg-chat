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


app = FastAPI(
    title="Regulatory Knowledge Base API",
    version="0.1.0",
    description="RAG chat over regulatory rulebooks. Multi-jurisdiction by design.",
)

app.add_middleware(CORSMiddleware, **_cors_config())

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