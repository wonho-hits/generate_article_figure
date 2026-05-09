# 260509 — Gradio MVP frontend

> Step 8 / 9 (re-ordered — promoted ahead of Path B & BG removal because UI-driven validation has higher signal at this point).
> Builds on every prior step.
> Status: **PRE-REPORT — pending approval**

## Context

Five steps in, the backend covers the core figure-generation loop end-to-end. But there's no human-facing surface — every test so far has been pytest, curl, or pre-built artifacts. The next bottleneck isn't more features; it's whether the existing pipeline actually feels right when a person uses it.

This step adds a thin Gradio UI mounted at `http://localhost:8000/ui`. The goal is **dogfooding**: the user (you) types a prompt, sees a figure, edits it, downloads it, and tells the system whether the loop is actually pleasant. Discoveries from real use will reorder Step 6, 7, 9 priorities better than continued speculation.

This is intentionally an **MVP, not the final frontend**. The architecture plan calls for Next.js + Konva.js eventually (real canvas editing, lasso selection, drag-to-position labels). Gradio gets us 80% of the validation value at 5% of the engineering cost; we migrate when interaction needs outgrow it.

## 이전 시도 (Previous Attempts)

None for the UI layer. The architecture plan ([[~/.claude/plans/agile-growing-flamingo.md]]) explicitly recommends "spend 1 day on Gradio MVP to validate backend, then build proper frontend."

## 가설 상태 (Hypothesis Status)

- **NEW H16 [검증중]**: Gradio is sufficient to validate the full backend loop (generate → edit → export) for a single user. UX limitations (no canvas brush, no lasso) won't block this validation because conversational reprompt already proved sufficient for editing in [[docs/progress/260509_inpaint_region.md]].

- **NEW H17 [검증중]**: Mounting Gradio at `/ui` on the same FastAPI app, using direct orchestrator calls (not HTTP) inside handlers, is the right ergonomics for an MVP. Single-process, single-port, single command (`uv run uvicorn app.main:app`).

- **NEW H18 [검증중]**: Real human use will surface ≥ 1 issue or priority shift not predicted by the build plan. Worth dogfooding before committing to Step 6 (Path B) or Step 7 (BG removal).

## Plan

### What we will build

```
app/
├── ui/
│   ├── __init__.py
│   └── gradio_app.py             # NEW: Blocks UI definition
└── main.py                        # UPDATED:
                                   #   - move session_store init out of lifespan
                                   #     (UI needs it at module load time)
                                   #   - mount gradio app at /ui

tests/
└── test_gradio_smoke.py           # NEW: import + build_ui() doesn't error
```

`pyproject.toml` adds `gradio>=5.0`.

### UI surface

Single page, no tabs. Three regions:

```
┌──────────────────────────────────────────────────────────────────┐
│  Article Figure Generator (MVP)                                  │
├──────────────────────────────────────────────────────────────────┤
│  ┌── Generate ────────┐    ┌── Display ───────────────────────┐ │
│  │ prompt [textarea]  │    │ [<svg> or <img> rendered here]   │ │
│  │ kind: [auto▼]      │    │                                  │ │
│  │ [Generate]         │    │ session: ...  kind: ...  rev: 0  │ │
│  │                    │    │ routing reason: ...              │ │
│  ├── Edit ────────────┤    └──────────────────────────────────┘ │
│  │ instruction [text] │    ┌── Export ────────────────────────┐ │
│  │ [Edit]             │    │  [Download SVG] [PPTX] [Image]   │ │
│  └────────────────────┘    └──────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### Key design decisions

1. **Direct orchestrator calls inside handlers, not HTTP**: simpler, no port plumbing, no httpx dance. Gradio handlers do `Orchestrator(sessions=app.state.session_store).generate(req)` directly. Validates the orchestrator and tools, not the HTTP route layer (already covered by mocked + live tests).

2. **`gr.HTML` for the display, not `gr.Image`**: holds either inline `<svg>` or `<img src="data-uri">`, no visibility juggling between two components. SVG renders crisply at any zoom; data URI is just dropped in.

3. **Per-tab session via `gr.State`**: each browser tab gets its own session_id. Refresh = new figure. No login, no persistence — single-user MVP scope.

4. **Skip mask brush in v1**: conversational reprompt was proven sufficient in step 4. Mask UI is a Gradio limitation — `gr.Image(tool="sketch")` exists but maps awkwardly to our base64-PNG mask format. Defer to Next.js phase. Document as known limitation.

5. **`figure_kind` dropdown exposed**: lets the user override the router. Verifies the override behavior is reachable and useful.

6. **Download buttons via `gr.DownloadButton`**: writes the export bytes to a temp path and offers a browser download. Buttons are visible all the time but trigger the appropriate route under the hood; if the format is incompatible (e.g., SVG download on a raster session), the button surfaces a friendly error rather than failing silently.

7. **Session store lives at module load time**: refactor `app/main.py` to create `InMemorySessionStore` at module top-level (not in `lifespan`). The Gradio mount happens at module load, so the session store must already exist.

### Acceptance criteria

1. `uv run uvicorn app.main:app --reload` starts cleanly. `/health` still works.
2. Browser at `http://localhost:8000/ui` shows the Gradio UI without errors.
3. **Generate flow**: type a bio prompt (e.g., "MAPK signaling cascade"), click Generate. SVG appears in the display panel. Status shows session_id, kind=svg, routing reason.
4. **Auto-routing flow**: type an illustrative prompt (e.g., "tumor microenvironment with macrophages"). Display shows raster image. Status shows kind=raster.
5. **Override flow**: same illustrative prompt with `figure_kind=vector` forces SVG output (lower visual quality acceptable — verifies override works).
6. **Edit flow**: after a raster generation, type "remove duplicate elements", click Edit. New image appears. Revision counter increments.
7. **Export flow**: download buttons work and produce the right format files. PPTX downloads open in PowerPoint per step 5 (raster picture for raster session, editable SVG-embedded for SVG session).
8. **Mocked smoke test**: `tests/test_gradio_smoke.py` imports the module and calls `build_ui()` without errors. Catches import drift.
9. Existing 100 mocked tests still pass.

### Out of scope for this step

- Brush/lasso for masks (Next.js phase)
- Multi-figure history view across the same session
- Side-by-side before/after diff
- Authentication / multi-user
- Streaming generation progress
- Mobile responsive layout
- Keyboard shortcuts
- Theming beyond Gradio defaults

### Risks

| Risk | Mitigation |
|------|-----------|
| Gradio's mount changes app's lifecycle in ways that break tests | Test suite uses `ASGITransport` against the FastAPI app, not the Gradio path. Mount happens at module load; tests' autouse fixture still creates a fresh session store per test. |
| Session-store init outside lifespan triggers configure_logging() before pytest's caplog hooks | `configure_logging()` is idempotent. If problematic, leave logging in lifespan and move only session_store init. |
| `gr.HTML` blocks JavaScript / SVG events for security | We don't need JS in the SVG. SVG renders as inert vector. |
| Gradio version drift breaks API | Pin `gradio>=5.0,<6.0`. Re-verify on every uv sync. |
| Real use surfaces too many issues to address in v1 | Triage; capture each as a follow-up issue. The point of this step is to surface them, not solve them. |

### Iteration history

To be filled during execution.

## Conclusion

To be filled after execution.
