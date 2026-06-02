# generate_article_figure

> [한국어 README](README.ko.md)

A Bio/Chem **publication-figure AI agent**. Turns natural-language prompts into editable figures and exports to SVG / PPTX / PNG.

![Figure Studio](assets/figure-studio.png)

The web app — **Figure Studio** — exposes two outcomes; internally the agent routes across four rendering paths.

| User-facing mode | Path(s) | Backend | Best for | Output |
|------------------|---------|---------|----------|--------|
| **Illustration** | C | Gemini Image (Nano Banana) | BioRender-style cells, anatomy, multi-cell scenes | `image/jpeg` |
| **Vector** | D (+ A, B internally) | Gemini text → SVG backbone + generated raster icons | pathways, cascades, hub-and-spoke, mechanism diagrams | `image/svg+xml` |

Internal paths (selected by an LLM router when `figure_kind=auto`):

| Path | Backend | Notes |
|------|---------|-------|
| **A** — Vector schematic | Gemini text → SVG + curated bio symbol library | `<use>` of ~23 hand-written symbols |
| **B** — Chemistry structure | Gemini extraction → RDKit → SVG | atom-level molecules; PubChemPy fallback |
| **C** — Raster illustration | Gemini Image | editable via conversational reprompt |
| **D** — Mixed (Vector) | Gemini text backbone + per-entity generated raster icons | text-free icons, all labels in vector |

**Illustration** outputs are editable through **conversational reprompt** ("remove the duplicate T cell"). **Vector** SVG outputs embed as native PowerPoint shapes via the `<asvg:svgBlip>` OOXML embed (right-click → Convert to Shape).

## Composition quality (Path D)

Vector figures pass through a layered defense so components don't just look good individually but compose cleanly:

```
LLM backbone
  → strict vision critic ×3      (Nature/Cell-editor rubric: buried arrows,
                                   broken symmetry, misalignment, overlap)
  → arrow_clip (deterministic)   connector endpoints → icon edges, never buried
  → label_declutter (det.)       nudge labels off connectors / icons
  → area-fill icon sizing (det.) equal box → equal icon AREA, balanced set
```

The critic runs up to 3 refine passes (keep-best); the deterministic passes guarantee correct arrow attachment, label clearance, and icon-size balance regardless of LLM variance. The UI streams each candidate live and lets you step through them.

## Status

**v1 + Path D + Figure Studio UI.**

| # | Feature | Status |
|---|---------|--------|
| 1 | Text-to-figure | ✅ Illustration + Vector (Paths A/B/C/D, auto-routing) |
| 2 | Editable labels | ✅ Illustration conversational reprompt |
| 3 | Redrawable parts | ✅ Illustration inpaint (mask or instruction) |
| 4 | Background removable | ⏸ deferred — outputs already on white in practice |
| 5 | Vectorize into slide (PPTX) | ✅ L1 picture (raster), L2 SVG-embedded (vector, Convert to Shape) |
| 6 | SVG vectorization | ✅ direct download |

276 mocked tests + live integration tests (behind `--run-live`).

## Setup

Requires Python 3.12 (pinned via `.python-version`). Install via [uv](https://docs.astral.sh/uv/):

```bash
uv sync
cp .env.example .env  # then fill in GOOGLE_API_KEY
```

Default models (override in `.env` or per-request from the UI):
- Language: `gemini-3.5-flash`
- Image: `gemini-3.1-flash-image-preview` (Nano Banana 2)

## Run

```bash
uv run uvicorn app.main:app --port 8000
```

Open **Figure Studio** at [http://localhost:8000/ui](http://localhost:8000/ui).

### Figure Studio UI

- **Two modes**: Illustration (full styled artwork) / Vector (labeled schematic).
- **Model pickers** (⚙ Models): swap the language model (`3.5 Flash` / `3.1 Pro`) and image model (`Nano Banana 2` / `Nano Banana Pro`) per request.
- **Live preview**: watch the Vector figure improve across critic passes in the canvas.
- **Candidate navigation**: step through every critic candidate with `◀ ▶` and download the one you pick.
- **Refine** (Illustration only): conversational reprompt to edit the image.
- **Downloads**: SVG / PowerPoint / PNG, enabled per figure kind, single-click.

REST API:
- `POST /generate` — `{"prompt": "...", "figure_kind": "auto|vector|raster|mixed"}` → `{session_id, artifact, kind, routing_reason}`
- `POST /edit/{session_id}` — `{"instruction": "...", "mask": "<base64 PNG>?"}` → `{session_id, artifact, kind, revision}`
- `GET /export/{session_id}/svg` — SVG sessions only
- `GET /export/{session_id}/pptx` — both kinds (L1 picture for raster, L2 SVG-embedded for vector)
- `GET /export/{session_id}/image` — raster sessions only
- `GET /health`

## Test

```bash
uv run pytest                                           # 276 mocked
uv run pytest --cov=app --cov-report=term-missing
uv run pytest --run-live                                # incurs Gemini costs
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  FIGURE STUDIO (Gradio UI, mounted at /ui)                       │
│  modes · model pickers · live preview · candidate nav · exports  │
└─────────────┬────────────────────────────────────────────────────┘
              │
┌─────────────▼────────────────────────────────────────────────────┐
│  FastAPI app                                                      │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Orchestrator                                            │    │
│  │  router.decide() → A | B | C | D   (or explicit override) │    │
│  │  dispatch → tool   (progress + on_preview callbacks)      │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  Tools:                                                           │
│   ├── vector_schematic   Path A: Gemini text + symbol library    │
│   ├── molecule           Path B: Gemini extraction + RDKit       │
│   ├── raster_illustration Path C: Gemini Image (Nano Banana)     │
│   ├── mixed_schematic     Path D: backbone + generated icons     │
│   │     ├── arrow_clip          connector → icon-edge clipping   │
│   │     ├── label_declutter     label/connector de-collision     │
│   │     └── layout_review        vision critic (keep-best ×3)     │
│   ├── inpaint            Path C edit: mask or conversational      │
│   ├── export            SVG / PPTX (L1) / image                  │
│   └── export_svg_pptx   PPTX (L2) — SVG embedded as asvg:svgBlip │
│                                                                   │
│  Session store: in-memory, TTL-evicted                            │
│  Gemini client: async wrapper with retry, structured output,     │
│                 per-request model override                        │
└───────────────────────────────────────────────────────────────────┘
```

See `docs/progress/INDEX.md` for the per-step development log.

## Known limitations

- **Path C / icons are JPEG**: `gemini-3.1-flash-image-preview` returns JPEG. MIME is detected automatically and threaded through data URIs and exports.
- **Background removal deferred**: feature #4. Outputs already arrive on white. Library candidate: `rembg` (U2Net).
- **PowerPoint <2016**: L2 PPTX (SVG-embedded) falls back to a 1×1 placeholder PNG; modern PowerPoint (2016+) renders the SVG and supports Convert to Shape.
- **Deterministic passes cover straight `<line>` connectors**: bezier `<path>` routing isn't clipped/decluttered yet.
- **Extreme-aspect icons** still clamp below the target area; converging icon framing upstream (icon style prompt) is a future improvement.
- **No persistence**: sessions and candidates are in-memory. Files reach disk only on download (browser download folder; server stages them under `$TMPDIR/figure_*`).
- **Frontend is Gradio**: the longer-term plan is Next.js + Konva for richer canvas editing (lasso, drag-to-reposition).

## Costs

Per-request cost estimates:
- Vector (Path D) generation: ~$0.0001 text per pass + image-gen per unique icon (cached by description); critic adds one vision call per pass.
- Path A / B generation: ~$0.0001 (text) — negligible.
- Illustration (Path C) generation: ~$0.04 (image).
- Inpainting: ~$0.04 (image edit).
- Routing: ~$0.0001 per request (skipped for explicit Illustration/Vector).

## License

MIT — see [LICENSE](LICENSE).
