"""FastAPI app + Gradio UI mount.

Session store is created at module-load time (not in lifespan) because the
Gradio UI is mounted at /ui at module load and needs the store ready.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import gradio as gr
import structlog
from fastapi import FastAPI

from app.config import get_settings
from app.logging import configure_logging
from app.routes import edit as edit_route
from app.routes import export as export_route
from app.routes import generate as generate_route
from app.state.session import InMemorySessionStore
from app.ui.gradio_app import build_ui

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    logger.info(
        "app.start",
        text_model=settings.gemini_text_model,
        image_model=settings.gemini_image_model,
    )
    try:
        yield
    finally:
        logger.info("app.stop")


app = FastAPI(
    title="generate_article_figure",
    description="Bio/Chem publication-figure AI agent",
    version="0.1.0",
    lifespan=lifespan,
)

# Session store ready at module load (Gradio mount needs it now, not at startup).
_settings = get_settings()
app.state.session_store = InMemorySessionStore(
    ttl_seconds=_settings.session_ttl_seconds
)

app.include_router(generate_route.router)
app.include_router(edit_route.router)
app.include_router(export_route.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Mount the Gradio UI. App is reassigned because gr.mount_gradio_app returns
# a new ASGI app that wraps the original FastAPI instance.
app = gr.mount_gradio_app(app, build_ui(), path="/ui")
