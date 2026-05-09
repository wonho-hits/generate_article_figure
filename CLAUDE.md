# CLAUDE.md — generate_article_figure

> Project-specific context. Global research-workflow conventions live in `~/.claude/CLAUDE.md`.

## What this project is

A bio/chem publication-figure AI agent. Natural-language prompts → SVG / PPTX / PNG via three rendering paths (vector schematic, RDKit chemistry, raster illustration) selected by an LLM router.

Backend: FastAPI on Python 3.12, async Gemini client, in-memory session store. Frontend: Gradio MVP mounted at `/ui`.

## Current state (snapshot — 2026-05-09)

v1 complete with all six target features. 149 mocked tests + 4 live integration tests. Cumulative live API cost during development: ~$0.13.

See [README.md](README.md) for the full feature matrix and run instructions.

## Where to start a new session

1. Read this file.
2. Read [README.md](README.md) for the feature matrix.
3. Read [docs/progress/INDEX.md](docs/progress/INDEX.md) for the per-step development log.
4. The most recent progress log dictates where work paused.

## Architecture quick reference

| Layer | Module | Notes |
|-------|--------|-------|
| FastAPI app | `app/main.py` | session store init at module load; Gradio mount at `/ui` (after route mounts) |
| Gemini client | `app/clients/gemini.py` | async; `generate_text` / `generate_image` / `edit_image`; manual `model_validate_json` fallback for structured output (SDK doesn't auto-parse `.parsed`) |
| Orchestrator | `app/agent/orchestrator.py` | router-driven dispatch (A/B/C); custom exceptions: `SessionNotFoundError`, `UnsupportedSessionKindError` |
| Router | `app/agent/router.py` | single LLM call with `RoutingDecision` schema |
| Tools | `app/tools/*.py` | `vector_schematic` (A), `molecule` (B), `raster_illustration` (C), `inpaint` (Path C edit), `export` (PPTX/SVG/image), `export_svg_pptx` (L2 PPTX with asvg embed), `svg_validate` (XML+structural+sanitize) |
| Symbol library | `app/domain/bio_symbols.py` | 23 hand-written SVG symbols + catalog used by Path A's system prompt |
| Routes | `app/routes/{generate,edit,export}.py` | mounted on FastAPI |
| Session state | `app/state/session.py` | `InMemorySessionStore` with TTL eviction, async-locked |
| UI | `app/ui/gradio_app.py` | mounted at `/ui` via `gr.mount_gradio_app` |

## Critical landmines / gotchas (learned the hard way)

1. **`google-genai` 1.x does not auto-populate `response.parsed`** for structured output even when `response_schema` is set. `GeminiClient.generate_text` falls back to `response_schema.model_validate_json(response.text)`. Don't remove that fallback.
2. **`gemini-3.1-flash-image-preview` returns JPEG, not PNG.** MIME is detected via `app/tools/raster_illustration.detect_image_mime` and threaded through data URIs. Hardcoding `image/png` would ship corrupt downloads.
3. **OOXML is prefix-sensitive in practice.** PowerPoint silently ignores SVG embed if the namespace prefix isn't literally `asvg:`. lxml's auto-generated `ns0:` prefix breaks this. Always pass `nsmap={"asvg": ASVG_NS}` to `etree.SubElement(...)`. Regression test in `tests/test_export.py::test_export_pptx_from_svg_uses_asvg_prefix_not_generated_one`.
4. **httpx `ASGITransport` does NOT run FastAPI lifespan handlers.** Tests that hit routes need to set `app.state.session_store` explicitly (autouse fixture in `tests/conftest.py`).
5. **Gemini 2.5+ `total_token_count` includes thinking tokens** — `prompt + response` usually << `total`. Use `total_token_count` for cost estimation.
6. **RDKit import**: `from rdkit.Chem.Draw import rdMolDraw2D` (NOT `from rdkit.Chem`). Common mistake.
7. **Conftest pins `GOOGLE_API_KEY=test-key-not-real`** to keep mocked tests hermetic. Live tests do `load_dotenv(override=True)` themselves to pick up the real key.
8. **Lipid bilayer symbol** has natural aspect ~4:1; stretching it across a wide figure scales the head/tail anatomy weirdly. Path A system prompt explicitly steers Gemini to use 2 horizontal lines for figure-spanning membranes instead.

## Hypothesis ledger

All hypotheses tracked across the progress logs. Final status:

- H1–H3 (skeleton choices): all 채택
- H4–H6 (Path A SVG-from-LLM viability + validation strategy): all 채택
- H7 (Path C single-shot quality sufficient): 채택
- H8 (conversational reprompt removes duplicates): 채택
- H9 (LLM router ≥ 90% on eval): 채택(100% on 11-prompt eval)
- H10 (style prefix > system_instruction for image models): 채택
- H11 (style-preserving instruction prefix preserves figure): 채택
- H12 (`isinstance(bytes)` gate sufficient for raster session): 채택
- H13–H14 (format-per-session-kind PPTX UX): 채택
- H15 (PowerPoint Convert-to-Shape works on Path A SVG vocabulary): 채택
- H16–H18 (Gradio MVP sufficient): 채택
- H19–H21 (~20 hand-written symbols cover pathway figures): 채택
- H22–H24 (LLM extraction + RDKit pipeline; PubChemPy fallback; router A/B/C extension): 채택

No 기각 hypotheses to date.

## Deferred

- **Step 7: Background removal (rembg / U2Net)** — Path C output is already on white in practice. Library exists; integration is straightforward when needed.
- **Reaction rendering in Path B** — RDKit supports it; just needs reaction-specific extraction prompt + drawer.
- **Next.js + Konva frontend** — Gradio MVP covers dogfooding. Migrate when interaction needs (lasso, drag-to-position) outgrow Gradio.
- **Symbol library expansion to ~50+ icons** — current 23 cover pathway-style schematics; cell illustrations remain Path C territory.
- **Path A label-position auto-correction** — minor label collisions persist after Step 9 prompt tuning. Could add a critic/retry pass.
- **Authentication / multi-tenancy** — single-user assumption.
- **Persistent session storage** — currently in-memory only.

## Run / test

```bash
uv sync                                      # install
cp .env.example .env                         # add GOOGLE_API_KEY
uv run uvicorn app.main:app --port 8000      # serve API + UI
# UI at http://localhost:8000/ui

uv run pytest                                # 149 mocked
uv run pytest --run-live                     # ~$0.13 in API costs
```

## Conventions

- **`uv` for Python tooling** (pinned to 3.12 in `.python-version`).
- **Pre-report → implement → verify → post-report** cycle per `~/.claude/CLAUDE.md` global. Each step in `docs/progress/<date>_<slug>.md`.
- **Live tests are opt-in** via `--run-live`. Default skip keeps CI/local cheap.
- **No mutation of artifacts in place**: orchestrator stores raw bytes (raster) or SVG strings, encodes to data URIs only at the route boundary.
