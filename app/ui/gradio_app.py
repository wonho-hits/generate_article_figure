"""Gradio MVP UI for the figure generator.

Mounted at /ui by app.main. Each browser tab maintains its own session via
gr.State; backend session storage is shared (app.state.session_store).

Handlers call the orchestrator directly (not through HTTP) — Gradio is a thin
view layer here, the route layer is exercised by mocked + live tests.
"""

from __future__ import annotations

import asyncio
import base64
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import gradio as gr

from app.agent.orchestrator import Orchestrator
from app.agent.schemas import EditRequest, GenerateRequest

EMPTY_STATE: dict[str, Any] = {
    "session_id": None,
    "kind": None,
    "revision": 0,
    "artifact": None,
}

PLACEHOLDER_HTML = (
    '<div style="color:#999;padding:32px;text-align:center;'
    'border:1px dashed #ccc;border-radius:8px;">'
    "Type a prompt and click <b>Generate</b>."
    "</div>"
)

EMPTY_LOG = ""


def _format_log(lines: list[str]) -> str:
    """Render progress log lines as a monospace fenced block."""
    if not lines:
        return EMPTY_LOG
    body = "\n".join(lines)
    return f"```text\n{body}\n```"


# ── helpers ────────────────────────────────────────────────────────────────


def _orchestrator() -> Orchestrator:
    """Build a fresh orchestrator using the FastAPI-app-shared session store."""
    # Lazy import to avoid the circular: app.main → ui.gradio_app → app.main.
    from app.main import app as fastapi_app

    return Orchestrator(sessions=fastapi_app.state.session_store)


def _render_artifact(artifact: str, kind: str) -> str:
    if kind == "svg":
        return (
            '<div style="background:white;padding:8px;'
            'border:1px solid #eee;border-radius:6px;">'
            f"{artifact}"
            "</div>"
        )
    # raster: artifact is a data URI
    return (
        f'<img src="{artifact}" alt="figure" '
        'style="max-width:100%;display:block;'
        'border:1px solid #eee;border-radius:6px;" />'
    )


def _status_md(state: dict[str, Any], routing_reason: str | None = None) -> str:
    if not state.get("session_id"):
        return "_(no figure generated yet)_"
    parts = [
        f"**session**: `{state['session_id'][:8]}…`",
        f"**kind**: `{state['kind']}`",
        f"**revision**: `{state['revision']}`",
    ]
    if routing_reason:
        parts.append(f"**routing**: {routing_reason}")
    return "  \n".join(parts)


def _data_uri_to_bytes(data_uri: str) -> bytes:
    _, b64 = data_uri.split(",", 1)
    return base64.b64decode(b64)


def _write_to_temp(content: bytes, filename: str) -> str:
    tmp_dir = Path(tempfile.mkdtemp(prefix="figure_"))
    out_path = tmp_dir / filename
    out_path.write_bytes(content)
    return str(out_path)


# ── handlers ───────────────────────────────────────────────────────────────


async def on_generate(
    prompt: str, figure_kind: str, state: dict[str, Any]
) -> AsyncIterator[tuple[dict[str, Any], str, str, str, Any]]:
    """Stream generation progress.

    Yields five-tuples: (state, display_html, status_md, log_md, edit_btn_update).

    Path A emits ~5-7 progress events across initial-gen + critic passes +
    refinement; Paths B and C are single-step and yield only start + final.
    The Edit button is enabled iff the resulting session is raster.
    """
    if not prompt or not prompt.strip():
        yield (
            state,
            PLACEHOLDER_HTML,
            "⚠ Prompt is empty.",
            EMPTY_LOG,
            gr.update(),
        )
        return

    log_lines: list[str] = ["▸ Starting…"]
    # Sentinel `None` signals "generation finished, drain done".
    queue: asyncio.Queue[tuple[str, float] | None] = asyncio.Queue()

    def progress_cb(msg: str, frac: float) -> None:
        # Called from inside the generation coroutine on the same event loop,
        # so put_nowait is safe (no cross-loop / cross-thread hop).
        queue.put_nowait((msg, frac))

    async def _run() -> Any:
        try:
            return await _orchestrator().generate(
                GenerateRequest(prompt=prompt, figure_kind=figure_kind),  # type: ignore[arg-type]
                progress=progress_cb,
            )
        finally:
            queue.put_nowait(None)

    gen_task = asyncio.create_task(_run())

    # Initial yield so the user sees activity before the first model call returns.
    yield (
        state,
        PLACEHOLDER_HTML,
        "⏳ Working…",
        _format_log(log_lines),
        gr.update(interactive=False),
    )

    while True:
        item = await queue.get()
        if item is None:
            break
        msg, frac = item
        pct = int(frac * 100)
        log_lines.append(f"▸ [{pct:3d}%] {msg}")
        yield (
            state,
            PLACEHOLDER_HTML,
            f"⏳ {msg} ({pct}%)",
            _format_log(log_lines),
            gr.update(interactive=False),
        )

    try:
        result = await gen_task
    except Exception as exc:  # surface errors to the UI; orchestrator already logs
        log_lines.append(f"✗ {type(exc).__name__}: {exc}")
        yield (
            state,
            PLACEHOLDER_HTML,
            f"❌ {type(exc).__name__}: {exc}",
            _format_log(log_lines),
            gr.update(interactive=False),
        )
        return

    new_state = {
        "session_id": result.session_id,
        "kind": result.kind,
        "revision": 0,
        "artifact": result.artifact,
    }
    log_lines.append(
        f"✓ Done — kind={result.kind}, session={result.session_id[:8]}…"
    )
    yield (
        new_state,
        _render_artifact(result.artifact, result.kind),
        _status_md(new_state, result.routing_reason),
        _format_log(log_lines),
        gr.update(interactive=(result.kind == "raster")),
    )


async def on_edit(
    instruction: str, state: dict[str, Any]
) -> tuple[dict[str, Any], str, str]:
    if not state.get("session_id"):
        return state, PLACEHOLDER_HTML, "⚠ Generate a figure first."
    if state.get("kind") != "raster":
        return (
            state,
            _render_artifact(state["artifact"], state["kind"]),
            "⚠ Edit only works on raster figures. Re-generate with figure_kind=raster.",
        )
    if not instruction or not instruction.strip():
        return (
            state,
            _render_artifact(state["artifact"], state["kind"]),
            "⚠ Instruction is empty.",
        )
    try:
        result = await _orchestrator().edit(
            state["session_id"], EditRequest(instruction=instruction)
        )
    except Exception as exc:
        return (
            state,
            _render_artifact(state["artifact"], state["kind"]),
            f"❌ {type(exc).__name__}: {exc}",
        )

    new_state = {
        **state,
        "kind": result.kind,
        "revision": result.revision,
        "artifact": result.artifact,
    }
    return (
        new_state,
        _render_artifact(result.artifact, result.kind),
        _status_md(new_state),
    )


def on_download_svg(state: dict[str, Any]) -> str | None:
    if not state.get("session_id"):
        gr.Warning("Generate a figure first.")
        return None
    if state.get("kind") != "svg":
        gr.Warning("SVG download is only available for vector sessions.")
        return None
    from app.tools.export import export_svg

    result = export_svg(state["artifact"], session_id=state["session_id"])
    return _write_to_temp(result.content, result.filename)


def on_download_pptx(state: dict[str, Any]) -> str | None:
    if not state.get("session_id"):
        gr.Warning("Generate a figure first.")
        return None
    from app.tools.export import export_pptx, export_pptx_from_svg

    try:
        if state["kind"] == "svg":
            result = export_pptx_from_svg(
                state["artifact"], session_id=state["session_id"]
            )
        else:
            image_bytes = _data_uri_to_bytes(state["artifact"])
            result = export_pptx(image_bytes, session_id=state["session_id"])
    except ValueError as exc:
        gr.Warning(f"Export failed: {exc}")
        return None
    return _write_to_temp(result.content, result.filename)


def on_download_image(state: dict[str, Any]) -> str | None:
    if not state.get("session_id"):
        gr.Warning("Generate a figure first.")
        return None
    if state.get("kind") != "raster":
        gr.Warning("Image download is only for raster sessions.")
        return None
    from app.tools.export import export_image

    image_bytes = _data_uri_to_bytes(state["artifact"])
    try:
        result = export_image(image_bytes, session_id=state["session_id"])
    except ValueError as exc:
        gr.Warning(f"Export failed: {exc}")
        return None
    return _write_to_temp(result.content, result.filename)


# ── UI definition ──────────────────────────────────────────────────────────


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Article Figure Generator") as ui:
        gr.Markdown("# Article Figure Generator (MVP)")
        gr.Markdown(
            "Bio/chem publication-quality figures from text prompts. "
            "Auto-routes between **Path A** (vector schematic, SVG), "
            "**Path C** (raster illustration, BioRender-style), and "
            "**Path D** (mixed: vector backbone + generated raster icons). "
            "Edit raster outputs with conversational reprompts. "
            "Download as SVG / PPTX / image."
        )

        state = gr.State(value=dict(EMPTY_STATE))

        with gr.Row():
            with gr.Column(scale=1):
                with gr.Group():
                    gr.Markdown("### Generate")
                    prompt_in = gr.Textbox(
                        label="Prompt",
                        lines=4,
                        placeholder="e.g., MAPK signaling cascade with EGF, Ras, Raf, MEK, ERK",
                    )
                    kind_in = gr.Dropdown(
                        choices=["auto", "vector", "raster", "mixed"],
                        value="auto",
                        label="Figure kind",
                        info=(
                            "auto = router decides; vector = force Path A; "
                            "raster = force Path C; mixed = force Path D "
                            "(vector backbone + generated raster icons)"
                        ),
                    )
                    generate_btn = gr.Button("Generate", variant="primary")

                with gr.Group():
                    gr.Markdown("### Edit (raster sessions only)")
                    instruction_in = gr.Textbox(
                        label="Instruction",
                        lines=3,
                        placeholder="e.g., remove the duplicate T cell at top-right",
                    )
                    # Disabled until a raster session lands; on_generate flips
                    # this based on result.kind.
                    edit_btn = gr.Button("Edit", interactive=False)

                with gr.Group():
                    gr.Markdown("### Status")
                    status_md = gr.Markdown("_(no figure generated yet)_")

            with gr.Column(scale=2):
                display = gr.HTML(value=PLACEHOLDER_HTML)

                with gr.Accordion("Progress log", open=False):
                    log_md = gr.Markdown(value=EMPTY_LOG)

                with gr.Group():
                    gr.Markdown("### Download")
                    with gr.Row():
                        svg_btn = gr.DownloadButton("SVG")
                        pptx_btn = gr.DownloadButton("PPTX")
                        image_btn = gr.DownloadButton("Image")

        generate_btn.click(
            on_generate,
            inputs=[prompt_in, kind_in, state],
            outputs=[state, display, status_md, log_md, edit_btn],
        )
        edit_btn.click(
            on_edit,
            inputs=[instruction_in, state],
            outputs=[state, display, status_md],
        )
        svg_btn.click(on_download_svg, inputs=[state], outputs=[svg_btn])
        pptx_btn.click(on_download_pptx, inputs=[state], outputs=[pptx_btn])
        image_btn.click(on_download_image, inputs=[state], outputs=[image_btn])

    return ui
