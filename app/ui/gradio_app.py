"""Gradio UI for the figure generator.

Mounted at /ui by app.main. Each browser tab maintains its own session via
gr.State; backend session storage is shared (app.state.session_store).

Handlers call the orchestrator directly (not through HTTP) — Gradio is a thin
view layer here, the route layer is exercised by mocked + live tests.

The UI deliberately hides internal routing vocabulary. Users pick between two
named outcomes — **Illustration** and **Diagram** — which map to the backend's
`raster` / `mixed` figure kinds. No "Path A/B/C/D" language is ever surfaced.
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
    # Vector runs only: every candidate the critic produced, oldest→newest, so
    # the user can step through them with ◀ ▶ and pick one.
    "candidates": [],
    "cand_index": 0,
}

# Friendly mode labels → backend figure_kind. The user never sees "raster" /
# "mixed" / "Path *"; the Radio carries the backend value while showing a label.
MODE_CHOICES = [
    ("🎨  Illustration", "raster"),
    ("📊  Vector", "mixed"),
]
DEFAULT_MODE = "mixed"  # Vector — the publication-schematic showcase.

# Model pickers (label → API model id). Kept short on purpose.
LANGUAGE_MODELS = [
    ("Gemini 3.5 Flash — fast", "gemini-3.5-flash"),
    ("Gemini 3.1 Pro — highest quality", "gemini-3.1-pro"),
]
IMAGE_MODELS = [
    ("Nano Banana 2 — fast", "gemini-3.1-flash-image-preview"),
    ("Nano Banana Pro — highest quality", "gemini-3-pro-image-preview"),
]
DEFAULT_LANGUAGE_MODEL = "gemini-3.5-flash"
DEFAULT_IMAGE_MODEL = "gemini-3.1-flash-image-preview"

# Artifact kind → friendly noun for status / messaging.
_KIND_NOUN = {"svg": "Vector", "raster": "Illustration"}

PLACEHOLDER_HTML = (
    '<div class="fig-empty">'
    '<div class="fig-empty-mark">✦</div>'
    "<p>Your figure will appear here.</p>"
    "<span>Describe it on the left, then <b>Generate</b>.</span>"
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


def _orchestrator(
    text_model: str | None = None, image_model: str | None = None
) -> Orchestrator:
    """Build a fresh orchestrator using the FastAPI-app-shared session store.

    When model ids are supplied (from the UI pickers), a GeminiClient pinned to
    those models is threaded through to every tool; otherwise tools fall back to
    the configured defaults.
    """
    # Lazy import to avoid the circular: app.main → ui.gradio_app → app.main.
    from app.main import app as fastapi_app
    from app.clients.gemini import GeminiClient

    client = None
    if text_model or image_model:
        client = GeminiClient(
            text_model=text_model or DEFAULT_LANGUAGE_MODEL,
            image_model=image_model or DEFAULT_IMAGE_MODEL,
        )
    return Orchestrator(
        sessions=fastapi_app.state.session_store, client=client
    )


def _render_artifact(artifact: str, kind: str) -> str:
    if kind == "svg":
        return f'<div class="fig-frame fig-frame-svg">{artifact}</div>'
    # raster: artifact is a data URI
    return (
        '<div class="fig-frame">'
        f'<img src="{artifact}" alt="generated figure" />'
        "</div>"
    )


def _status_md(state: dict[str, Any]) -> str:
    """Friendly one-line status. No session ids / routing / kind jargon."""
    if not state.get("session_id"):
        return "_No figure generated yet._"
    noun = _KIND_NOUN.get(state.get("kind", ""), "Figure")
    line = f"✓ **{noun}** ready"
    rev = int(state.get("revision", 0) or 0)
    if rev > 0:
        line += f"  ·  {rev} refinement{'s' if rev != 1 else ''}"
    return line


def _cand_label(state: dict[str, Any]) -> str:
    """`Candidate i / N — pass note` for the navigation strip."""
    cands = state.get("candidates") or []
    n = len(cands)
    if n <= 1:
        return ""
    i = int(state.get("cand_index", 0)) + 1
    note = "draft" if i == 1 else ("final" if i == n else f"pass {i - 1}")
    return f"**{i} / {n}**  ·  {note}"


def _data_uri_to_bytes(data_uri: str) -> bytes:
    _, b64 = data_uri.split(",", 1)
    return base64.b64decode(b64)


def _write_to_temp(content: bytes, filename: str) -> str:
    tmp_dir = Path(tempfile.mkdtemp(prefix="figure_"))
    out_path = tmp_dir / filename
    out_path.write_bytes(content)
    return str(out_path)


_DISABLED_DL = None  # placeholder; real updates built per-result below


def _build_downloads(state: dict[str, Any]) -> tuple[Any, Any, Any]:
    """Export files NOW and bind them to the (svg, pptx, image) buttons.

    A `gr.DownloadButton` downloads its own `value`. If the value is set by a
    click-handler it takes a SECOND click to actually download; binding the
    file path up-front (here, at generation time) makes it a single click.
    Only the buttons valid for the current kind are enabled; others disabled.

    Returns gr.update tuples for (svg_btn, pptx_btn, image_btn).
    """
    off = gr.update(interactive=False, value=None)
    kind = state.get("kind")
    artifact = state.get("artifact")
    sid = state.get("session_id")
    if not sid or not artifact:
        return off, off, off

    from app.tools.export import (
        export_image,
        export_pptx,
        export_pptx_from_svg,
        export_svg,
    )

    svg_u = pptx_u = image_u = off
    try:
        if kind == "svg":
            r = export_svg(artifact, session_id=sid)
            svg_u = gr.update(
                value=_write_to_temp(r.content, r.filename), interactive=True
            )
            r = export_pptx_from_svg(artifact, session_id=sid)
            pptx_u = gr.update(
                value=_write_to_temp(r.content, r.filename), interactive=True
            )
        elif kind == "raster":
            img = _data_uri_to_bytes(artifact)
            r = export_image(img, session_id=sid)
            image_u = gr.update(
                value=_write_to_temp(r.content, r.filename), interactive=True
            )
            r = export_pptx(img, session_id=sid)
            pptx_u = gr.update(
                value=_write_to_temp(r.content, r.filename), interactive=True
            )
    except Exception:  # noqa: BLE001 — export is best-effort; UI shows enabled-only
        pass
    return svg_u, pptx_u, image_u


# ── handlers ───────────────────────────────────────────────────────────────


async def on_generate(
    prompt: str,
    figure_kind: str,
    text_model: str,
    image_model: str,
    state: dict[str, Any],
) -> AsyncIterator[tuple[Any, ...]]:
    """Stream generation progress.

    Yields 10-tuples:
      (state, display, status_md, log_md, refine_group,
       svg_btn, pptx_btn, image_btn, nav_row, cand_label)

    Vector (mixed) emits a preview per critic pass; we collect them so the user
    can step through candidates afterward. Illustration (raster) is single-step.
    """
    hide = tuple(gr.update() for _ in range(6))  # 6 trailing no-ops

    if not prompt or not prompt.strip():
        yield (state, PLACEHOLDER_HTML, "⚠ Please enter a prompt.", EMPTY_LOG, *hide)
        return

    log_lines: list[str] = ["▸ Starting…"]
    # Queue items: ("progress", msg, frac) | ("preview", svg) | None (done).
    queue: asyncio.Queue[tuple[Any, ...] | None] = asyncio.Queue()

    def progress_cb(msg: str, frac: float) -> None:
        # Called from inside the generation coroutine on the same event loop,
        # so put_nowait is safe (no cross-loop / cross-thread hop).
        queue.put_nowait(("progress", msg, frac))

    def preview_cb(svg: str) -> None:
        queue.put_nowait(("preview", svg))

    async def _run() -> Any:
        try:
            return await _orchestrator(text_model, image_model).generate(
                GenerateRequest(prompt=prompt, figure_kind=figure_kind),  # type: ignore[arg-type]
                progress=progress_cb,
                on_preview=preview_cb,
            )
        finally:
            queue.put_nowait(None)

    gen_task = asyncio.create_task(_run())

    last_display = PLACEHOLDER_HTML
    last_status = "⏳ Working…"
    candidates: list[str] = []

    # Initial yield so the user sees activity before the first model call returns.
    yield (state, last_display, last_status, _format_log(log_lines), *hide)

    while True:
        item = await queue.get()
        if item is None:
            break
        if item[0] == "preview":
            # An intermediate candidate — render it live AND collect it so the
            # user can step back through the critic's progression afterward.
            svg = item[1]
            if not candidates or candidates[-1] != svg:
                candidates.append(svg)
            last_display = _render_artifact(svg, "svg")
            yield (state, last_display, last_status, _format_log(log_lines), *hide)
            continue
        _, msg, frac = item
        pct = int(frac * 100)
        last_status = f"⏳ {msg} ({pct}%)"
        log_lines.append(f"▸ [{pct:3d}%] {msg}")
        yield (state, last_display, last_status, _format_log(log_lines), *hide)

    try:
        result = await gen_task
    except Exception as exc:  # surface errors to the UI; orchestrator already logs
        log_lines.append(f"✗ {type(exc).__name__}: {exc}")
        yield (
            state,
            PLACEHOLDER_HTML,
            f"❌ Something went wrong: {exc}",
            _format_log(log_lines),
            *hide,
        )
        return

    # The final result is the chosen candidate; for Vector it equals the last
    # preview already in `candidates`.
    cand_index = max(0, len(candidates) - 1)
    new_state = {
        "session_id": result.session_id,
        "kind": result.kind,
        "revision": 0,
        "artifact": result.artifact,
        "candidates": candidates,
        "cand_index": cand_index,
    }
    log_lines.append(f"✓ Done — {_KIND_NOUN.get(result.kind, result.kind)}")
    svg_u, pptx_u, image_u = _build_downloads(new_state)
    multi = len(candidates) > 1 and result.kind == "svg"
    yield (
        new_state,
        _render_artifact(result.artifact, result.kind),
        _status_md(new_state),
        _format_log(log_lines),
        gr.update(visible=(result.kind == "raster")),  # Refine panel
        svg_u,
        pptx_u,
        image_u,
        gr.update(visible=multi),  # nav row
        gr.update(value=_cand_label(new_state)),  # candidate label
    )


async def on_nav(delta: int, state: dict[str, Any]) -> tuple[Any, ...]:
    """Step through collected candidates. Returns
    (state, display, cand_label, svg_btn, pptx_btn, image_btn)."""
    cands = state.get("candidates") or []
    if len(cands) <= 1:
        return state, gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
    idx = min(max(int(state.get("cand_index", 0)) + delta, 0), len(cands) - 1)
    svg = cands[idx]
    new_state = {**state, "cand_index": idx, "artifact": svg}
    svg_u, pptx_u, image_u = _build_downloads(new_state)
    return (
        new_state,
        _render_artifact(svg, "svg"),
        _cand_label(new_state),
        svg_u,
        pptx_u,
        image_u,
    )


async def on_prev(state: dict[str, Any]) -> tuple[Any, ...]:
    return await on_nav(-1, state)


async def on_next(state: dict[str, Any]) -> tuple[Any, ...]:
    return await on_nav(1, state)


async def on_edit(
    instruction: str, image_model: str, state: dict[str, Any]
) -> tuple[Any, ...]:
    """Returns (state, display, status, pptx_btn, image_btn).

    Download buttons are refreshed so the edited image downloads in one click.
    """
    noop = (gr.update(), gr.update())  # pptx, image unchanged
    if not state.get("session_id"):
        return state, PLACEHOLDER_HTML, "⚠ Generate a figure first.", *noop
    if state.get("kind") != "raster":
        return (
            state,
            _render_artifact(state["artifact"], state["kind"]),
            "⚠ Refining is available for Illustrations only.",
            *noop,
        )
    if not instruction or not instruction.strip():
        return (
            state,
            _render_artifact(state["artifact"], state["kind"]),
            "⚠ Describe what to change.",
            *noop,
        )
    try:
        result = await _orchestrator(image_model=image_model).edit(
            state["session_id"], EditRequest(instruction=instruction)
        )
    except Exception as exc:
        return (
            state,
            _render_artifact(state["artifact"], state["kind"]),
            f"❌ Refine failed: {exc}",
            *noop,
        )

    new_state = {
        **state,
        "kind": result.kind,
        "revision": result.revision,
        "artifact": result.artifact,
    }
    _, pptx_u, image_u = _build_downloads(new_state)
    return (
        new_state,
        _render_artifact(result.artifact, result.kind),
        _status_md(new_state),
        pptx_u,
        image_u,
    )


# ── theme + styling ──────────────────────────────────────────────────────────

THEME = gr.themes.Soft(
    primary_hue=gr.themes.colors.indigo,
    secondary_hue=gr.themes.colors.indigo,
    neutral_hue=gr.themes.colors.slate,
    font=[gr.themes.GoogleFont("Inter"), "system-ui", "-apple-system", "sans-serif"],
    radius_size=gr.themes.sizes.radius_lg,
).set(
    body_background_fill="#f6f7f9",
    body_text_color="#1e2330",
    block_background_fill="#ffffff",
    block_border_width="1px",
    block_border_color="#e7e9ee",
    block_shadow="0 1px 2px rgba(16,24,40,0.04)",
    block_label_text_weight="600",
    button_primary_background_fill="*primary_600",
    button_primary_background_fill_hover="*primary_700",
    button_large_radius="12px",
    input_background_fill="#fbfcfd",
)

# Force the app into light mode regardless of the browser's prefers-color-scheme.
# The design direction is "clean scientific light"; without this, a dark-mode
# browser renders our dark text on Gradio's dark surfaces (invisible labels).
FORCE_LIGHT_JS = """
() => {
  const u = new URL(window.location.href);
  if (u.searchParams.get('__theme') !== 'light') {
    u.searchParams.set('__theme', 'light');
    window.location.replace(u.toString());
  }
}
"""

CSS = """
:root { --fig-accent:#4f46e5; --fig-ink:#1e2330; --fig-muted:#737884; }

/* Belt-and-suspenders: pin our palette even if a dark theme slips through. */
body, .gradio-container { background: #f6f7f9 !important; color: var(--fig-ink); }

/* The width cap lives on Gradio's *versioned* container class + .fillable
   wrapper (JS-injected), so target by partial class match and free them to
   full width. The row below becomes the real width anchor. */
div[class*="gradio-container"], .fillable, .app, .wrap.contain {
  max-width: 100% !important; width: 100% !important;
}
.fig-main-row {
  max-width: 1480px !important; margin: 0 auto !important;
  align-items: flex-start !important;  /* top-align both columns */
}
/* Zero the top margin/padding on each column's first block so the controls
   card and the figure canvas line up exactly at the top. */
.fig-controls > *:first-child,
.fig-output > *:first-child { margin-top: 0 !important; padding-top: 0 !important; }
.gradio-container { font-size: 16px; }

/* Header — share the row's centered width anchor so they align. */
#fig-header { padding: 14px 2px 4px; max-width: 1480px; margin: 0 auto; width: 100%; }
#fig-header h1 {
  font-size: 2.5rem; font-weight: 700; letter-spacing: -0.025em;
  margin: 0; color: var(--fig-ink);
}
#fig-header .fig-sub { color: var(--fig-muted); font-size: 1.1rem; margin-top: 4px; }
#fig-header .fig-rule {
  height: 4px; width: 72px; border-radius: 3px; margin-top: 14px;
  background: linear-gradient(90deg, var(--fig-accent), #818cf8);
}

/* Section labels */
.fig-section-title {
  font-size: 0.85rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.07em; color: var(--fig-muted); margin: 0 0 4px;
}

/* Mode selector → cards */
.mode-select fieldset { border: none !important; display: flex; gap: 10px; }
.mode-select input[type=radio] { display: none !important; }  /* hide raw dot */
.mode-select label {
  flex: 1; border: 1.5px solid #e2e5ec !important; border-radius: 12px !important;
  padding: 14px 12px !important; background: #fbfcfd !important;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  text-align: center; min-height: 42px; font-size: 1.02rem;
  transition: border-color .15s, box-shadow .15s, background .15s; cursor: pointer;
  font-weight: 600 !important; color: var(--fig-ink) !important;
}
.mode-select label * { color: var(--fig-ink) !important; }
.mode-select label:hover { border-color: #c7cbf5 !important; }
.mode-select label:has(input:checked) {
  border-color: var(--fig-accent) !important; background: #eef0ff !important;
  box-shadow: 0 0 0 3px rgba(79,70,229,0.14) !important;
}

/* Figure canvas — fixed, generous height (not viewport-bound, so the page
   doesn't stretch tall and the Progress panel stays in view). */
.fig-frame {
  background: #ffffff; border: 1px solid #e7e9ee; border-radius: 16px;
  padding: 18px; min-height: 560px;
  display: flex; align-items: center; justify-content: center;
}
.fig-frame img, .fig-frame svg {
  max-width: 100%; max-height: 720px; height: auto; display: block;
}
.fig-frame-svg { background:
  linear-gradient(#fff,#fff) padding-box,
  repeating-conic-gradient(#f3f4f6 0% 25%, #fff 0% 50%) 0/18px 18px; }

.fig-empty {
  min-height: 560px; border: 1.5px dashed #d6dae2; border-radius: 16px;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: var(--fig-muted); text-align: center; gap: 6px; background: #fcfcfd;
}
.fig-empty-mark { font-size: 2.2rem; color: #c2c7d0; }
.fig-empty p { margin: 10px 0 0; font-weight: 600; font-size: 1.05rem; color: #565c69; }
.fig-empty span { font-size: 0.98rem; }

/* Candidate navigation strip — keep ◀ label ▶ on ONE row, centered. */
.fig-nav {
  display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important;
  gap: 12px; margin-top: 12px; align-items: center !important; justify-content: center !important;
}
.fig-nav > * { flex: 0 0 auto !important; width: auto !important; min-width: 0 !important; }
.fig-nav .fig-nav-btn { min-width: 56px !important; }
.fig-nav .fig-nav-label { text-align: center; min-width: 96px; }
.fig-nav .fig-nav-label p { margin: 0; color: var(--fig-muted); white-space: nowrap; }

/* Download row — visible buttons split the width evenly. */
.fig-downloads { gap: 10px; margin-top: 12px; }
.fig-downloads > * { flex: 1 1 0 !important; }

footer { display: none !important; }
"""


# ── UI definition ──────────────────────────────────────────────────────────


def build_ui() -> gr.Blocks:
    with gr.Blocks(
        title="Figure Studio",
        theme=THEME,
        css=CSS,
        js=FORCE_LIGHT_JS,
        fill_width=True,
    ) as ui:
        with gr.Column(elem_id="fig-header"):
            gr.HTML(
                "<h1>Figure Studio</h1>"
                '<div class="fig-sub">Publication-quality bio &amp; chem figures '
                "from a text prompt.</div>"
                '<div class="fig-rule"></div>'
            )

        state = gr.State(value=dict(EMPTY_STATE))

        with gr.Row(equal_height=False, elem_classes="fig-main-row"):
            # ── Controls ──────────────────────────────────────────────
            with gr.Column(scale=5, elem_classes="fig-controls"):
                with gr.Group():
                    gr.HTML('<p class="fig-section-title">Describe your figure</p>')
                    prompt_in = gr.Textbox(
                        label="",
                        lines=7,
                        max_lines=16,
                        placeholder=(
                            "e.g. MAPK signaling cascade: EGF binds EGFR, "
                            "activating Ras → Raf → MEK → ERK, leading to "
                            "cell proliferation."
                        ),
                        show_label=False,
                    )
                    mode_in = gr.Radio(
                        choices=MODE_CHOICES,
                        value=DEFAULT_MODE,
                        show_label=False,
                        elem_classes="mode-select",
                        info=(
                            "Illustration — a full styled artwork. "
                            "Vector — a labeled schematic with clean arrows "
                            "(refining is available for Illustrations)."
                        ),
                    )
                    generate_btn = gr.Button(
                        "Generate figure", variant="primary", size="lg"
                    )

                with gr.Accordion("⚙  Models", open=False):
                    lang_model_in = gr.Dropdown(
                        choices=LANGUAGE_MODELS,
                        value=DEFAULT_LANGUAGE_MODEL,
                        label="Language model",
                        info="Drives layout, labels and the diagram backbone.",
                    )
                    image_model_in = gr.Dropdown(
                        choices=IMAGE_MODELS,
                        value=DEFAULT_IMAGE_MODEL,
                        label="Image model",
                        info="Draws the illustrations and icons.",
                    )

                # Refine — only meaningful for Illustrations; hidden until one lands.
                with gr.Group(visible=False) as refine_group:
                    gr.HTML('<p class="fig-section-title">Refine</p>')
                    instruction_in = gr.Textbox(
                        label="",
                        lines=2,
                        placeholder="e.g. remove the duplicate cell at top-right",
                        show_label=False,
                    )
                    edit_btn = gr.Button("Apply change", size="lg")

                status_md = gr.Markdown("_No figure generated yet._")

            # ── Output ────────────────────────────────────────────────
            with gr.Column(scale=7, elem_classes="fig-output"):
                display = gr.HTML(value=PLACEHOLDER_HTML)

                # Candidate navigation — shown only when the critic produced more
                # than one Vector candidate. Step ◀ ▶ and download the one you pick.
                with gr.Row(visible=False, elem_classes="fig-nav") as nav_row:
                    prev_btn = gr.Button("◀", elem_classes="fig-nav-btn")
                    cand_label = gr.Markdown("", elem_classes="fig-nav-label")
                    next_btn = gr.Button("▶", elem_classes="fig-nav-btn")

                with gr.Row(elem_classes="fig-downloads"):
                    svg_btn = gr.DownloadButton("⬇ SVG", interactive=False)
                    pptx_btn = gr.DownloadButton("⬇ PowerPoint", interactive=False)
                    image_btn = gr.DownloadButton("⬇ PNG", interactive=False)

                with gr.Accordion("Progress", open=False):
                    log_md = gr.Markdown(value=EMPTY_LOG)

        generate_btn.click(
            on_generate,
            inputs=[prompt_in, mode_in, lang_model_in, image_model_in, state],
            outputs=[
                state,
                display,
                status_md,
                log_md,
                refine_group,
                svg_btn,
                pptx_btn,
                image_btn,
                nav_row,
                cand_label,
            ],
            # We drive our own status text + live preview, so keep Gradio's
            # progress animation ONLY on the Progress log — not on the canvas
            # or the left status line.
            show_progress="full",
            show_progress_on=[log_md],
        )
        edit_btn.click(
            on_edit,
            inputs=[instruction_in, image_model_in, state],
            outputs=[state, display, status_md, pptx_btn, image_btn],
            show_progress="hidden",
        )
        _nav_outputs = [state, display, cand_label, svg_btn, pptx_btn, image_btn]
        prev_btn.click(on_prev, inputs=[state], outputs=_nav_outputs)
        next_btn.click(on_next, inputs=[state], outputs=_nav_outputs)
        # No download click-handlers: each DownloadButton carries its file path
        # (bound at generate/refine time), so it downloads in a single click.

    return ui
