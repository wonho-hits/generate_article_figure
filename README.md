# generate_article_figure

> [한국어 README](README.ko.md)

A Bio/Chem **publication-figure AI agent**. Turns natural-language prompts into editable figures and exports to SVG / PPTX / PNG.

Auto-routes between three rendering paths:

| Path | Backend | Best for | Output |
|------|---------|----------|--------|
| **A** — Vector schematic | Gemini text → SVG (with curated bio symbol library) | pathways, cascades, flowcharts, mechanism diagrams | `image/svg+xml` |
| **B** — Chemistry structure | Gemini extraction → RDKit → SVG | molecules, drugs, metabolites, atom-level structures | `image/svg+xml` |
| **C** — Raster illustration | Gemini Image (Nano Banana 2 / `gemini-3.1-flash-image-preview`) | BioRender-style cells, anatomy, multi-cell scenes | `image/jpeg` |

Path C outputs are editable through **conversational reprompt** ("remove the duplicate T cell"); Path A outputs become editable native PowerPoint shapes via the `<asvg:svgBlip>` OOXML embed (right-click → Convert to Shape).

## Status

**v1, all six target features delivered**:

| # | Feature | Status |
|---|---------|--------|
| 1 | Text-to-image schematic | ✅ Path A + B + C with auto-routing |
| 2 | Editable labels | ✅ via Path C inpaint instructions |
| 3 | Redrawable parts | ✅ via Path C inpaint (mask or instruction) |
| 4 | Background removable | ⏸ deferred — Path C output already on white in practice |
| 5 | Vectorize into slide (PPTX) | ✅ L1 picture for raster, L2 SVG-embedded for vector (Convert to Shape works) |
| 6 | SVG vectorization | ✅ direct download for Path A and B |

149 mocked tests + 4 live integration tests (router 11/11, Path A live, Path C live, Path B aspirin live, inpaint live). 87% coverage.

## Setup

Requires Python 3.12 (pinned via `.python-version`). Install via [uv](https://docs.astral.sh/uv/):

```bash
uv sync
cp .env.example .env  # then fill in GOOGLE_API_KEY
```

## Run

```bash
uv run uvicorn app.main:app --port 8000
```

Then open the Gradio UI at [http://localhost:8000/ui](http://localhost:8000/ui).

REST API:
- `POST /generate` — `{"prompt": "...", "figure_kind": "auto|vector|raster"}` → `{session_id, artifact, kind, routing_reason}`
- `POST /edit/{session_id}` — `{"instruction": "...", "mask": "<base64 PNG>?"}` → `{session_id, artifact, kind, revision}`
- `GET /export/{session_id}/svg` — SVG sessions only
- `GET /export/{session_id}/pptx` — both kinds (L1 picture for raster, L2 SVG-embedded for vector)
- `GET /export/{session_id}/image` — raster sessions only
- `GET /health`

## Test

```bash
uv run pytest                                           # 149 mocked
uv run pytest --cov=app --cov-report=term-missing
uv run pytest --run-live                                # incurs ~$0.13 in Gemini costs
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  GRADIO UI (mounted at /ui)                                      │
└─────────────┬────────────────────────────────────────────────────┘
              │
┌─────────────▼────────────────────────────────────────────────────┐
│  FastAPI app                                                      │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Orchestrator                                            │    │
│  │  router.decide() → A | B | C                             │    │
│  │  dispatch → tool                                         │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  Tools:                                                           │
│   ├── vector_schematic  Path A: Gemini text + symbol library     │
│   ├── molecule          Path B: Gemini extraction + RDKit        │
│   ├── raster_illustration  Path C: Gemini Image (Nano Banana 2)  │
│   ├── inpaint           Path C edit: mask or conversational      │
│   ├── export            SVG / PPTX (L1) / image                  │
│   └── export_svg_pptx   PPTX (L2) — SVG embedded as asvg:svgBlip │
│                                                                   │
│  Session store: in-memory, TTL-evicted                            │
│  Gemini client: async wrapper with retry, structured output      │
└───────────────────────────────────────────────────────────────────┘
```

See `docs/progress/INDEX.md` for the per-step development log and `docs/progress/*.md` for detailed implementation notes per step.

## Known limitations

- **Path A label positioning**: Gemini occasionally places labels with minor overlaps (e.g., compartment labels brushing element edges). Mitigated by the symbol library + tightened system prompt but not fully solved.
- **Path C is JPEG, not PNG**: `gemini-3.1-flash-image-preview` returns JPEG by default. The MIME is detected automatically and surfaced through data URIs and exports.
- **Background removal deferred**: feature #4 from the original spec. Path C outputs already arrive on a white background, so the ergonomic gap is small. Library candidate: `rembg` (U2Net).
- **PowerPoint <2016**: L2 PPTX (SVG-embedded) falls back to a 1×1 placeholder PNG on older PowerPoint versions. Modern PowerPoint (Mac/Windows 2016+) renders the SVG and supports Convert to Shape.
- **Frontend is Gradio MVP**: the canonical plan is Next.js + Konva for richer canvas editing (lasso selection, drag-to-reposition labels). Gradio covers the dogfooding loop.

## Costs

Cumulative live API costs across all live tests during development: **~$0.13**.

Per-request cost estimates:
- Path A generation: ~$0.0001 (text) — negligible
- Path B generation: ~$0.0001 (text) + free RDKit + ~free PubChem — negligible
- Path C generation: ~$0.04 (image)
- Inpainting: ~$0.04 (image edit)
- Routing: ~$0.0001 per request

## License

MIT — see [LICENSE](LICENSE).
