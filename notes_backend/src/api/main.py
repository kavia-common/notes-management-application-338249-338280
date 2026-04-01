from __future__ import annotations

import logging
import os
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.init_db import init_db
from src.api.routes_notes import router as notes_router
from src.api.routes_tags import router as tags_router

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger("notes_backend")

openapi_tags = [
    {"name": "health", "description": "Health and service status endpoints."},
    {"name": "notes", "description": "CRUD and search for notes."},
    {"name": "tags", "description": "Tag listing endpoints."},
]

app = FastAPI(
    title="Notes Backend API",
    description=(
        "FastAPI backend for the Notes app.\n\n"
        "Provides REST endpoints for notes CRUD, search, and tags."
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

# CORS:
# Frontend can be configured via env; we keep permissive fallback for local dev.
_frontend_url = os.environ.get("REACT_APP_FRONTEND_URL")
_default_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
allow_origins = [_frontend_url] if _frontend_url else _default_origins + ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(notes_router)
app.include_router(tags_router)


@app.on_event("startup")
def _on_startup() -> None:
    """Initialize DB schema when the service starts."""
    init_db()


@app.get(
    "/",
    tags=["health"],
    summary="Health check",
    description="Simple health check endpoint for service readiness.",
    operation_id="health_check",
)
# PUBLIC_INTERFACE
def health_check():
    """Health check endpoint.

    Returns:
        dict: {"message": "Healthy"}
    """
    return {"message": "Healthy"}
