# Streaming progress + critic visibility in the Gradio UI

Date: 2026-05-13
Related: [[260509_gradio_mvp.md]], [[260512_bioicons_pilot.md]]

## WHY (motivation)

Path A generation runs ~3-4 minutes when the vision critic engages
(initial gen → up to 2 critic passes → refines). During that window the
Gradio MVP showed nothing — no progress, no log, no indication that the
agent was working. Users couldn't tell whether the run was stuck, mid-
critic, or about to finish. That ambiguity is the single largest UX
defect remaining after the 20-round library pilot.

[[260509_gradio_mvp.md]] explicitly deferred streaming progress as
post-MVP work. Now that the pilot is closed and the library is stable,
this is the highest-leverage UI improvement.

## Plan

1. Add an optional `progress: ProgressCallback | None = None` parameter
   to `generate_vector_schematic`, emitting `(message, fraction)` events
   at each pipeline step (initial gen → each critic pass → each refine →
   final ship).
2. Thread the callback through `Orchestrator.generate(..., progress=…)`
   into `_dispatch_vector`. Paths B and C are single-step; they don't
   emit progress and don't need a hook today.
3. Rewrite the Gradio `on_generate` handler as an async generator that:
   - kicks off generation as an `asyncio.create_task`,
   - bridges the sync callback to async via `asyncio.Queue.put_nowait`,
   - yields `(state, display, status, log_md, edit_btn_update)` tuples
     on every progress tick + final.
4. Surface a collapsible "Progress log" markdown panel and gate the
   Edit button on `kind == "raster"` (was always-on before, but errors
   were only surfaced after click).
5. Lock the contract with regression tests: monotonic non-decreasing
   fractions, final tick at 1.0, default `progress=None` still works.

## Execution

- `app/tools/vector_schematic.py` — added `ProgressCallback` type alias
  and a local `_emit(msg, frac)` helper. Fractions are computed against
  `total_steps = 1 + max_refine_passes * 2` (initial + critic+regen per
  pass) and clamped to ≤ 0.99 until the final ship.
- `app/agent/orchestrator.py` — `generate()` and `_dispatch_vector()`
  now accept `progress` as a keyword-only kwarg. B/C dispatchers are
  unchanged.
- `app/ui/gradio_app.py` — `on_generate` converted to async generator
  (`AsyncIterator[tuple[...]]`). Internally uses an `asyncio.Queue`
  with a `None` sentinel posted in the `_run()` finally block to signal
  drain completion. Initial yield fires immediately so the UI doesn't
  look frozen during the first Gemini call (~30s).
- New `<Accordion>Progress log</Accordion>` containing a `gr.Markdown`
  that accumulates `▸ [pp%] message` lines as a fenced text block.
- Edit button starts `interactive=False`; `on_generate` flips it to
  `interactive=True` only when the resulting session is `raster`.
- `tests/test_vector_schematic.py` — added
  `test_progress_callback_receives_monotonic_updates` and
  `test_progress_callback_default_none_is_no_op`.

## Verification

- 234 passed, 5 skipped (was 232 before; +2 progress callback tests).
- `build_ui()` smoke-tested: imports clean, `on_generate` confirmed as
  an async generator via `inspect.isasyncgenfunction`.
- `_format_log` formatter verified on empty + populated input.

## Lessons

1. **Bridge sync→async with `asyncio.Queue.put_nowait` when both ends
   share the loop.** No `run_in_executor`, no threading. The callback
   is invoked from within the generation coroutine, so it lands on the
   same loop the consumer is awaiting on — `put_nowait` is sufficient
   and avoids cross-thread hazards.
2. **Yield once before awaiting the queue.** Without an initial yield,
   Gradio shows the previous frame until the first progress tick lands,
   which can be 20-30s into a Path A run. A no-op "⏳ Working…" yield
   makes the click feel responsive.
3. **Default-None kwarg preserves back-compat for free.** All 30+
   existing call sites of `generate_vector_schematic` (analyze scripts,
   tests, orchestrator) continue to work unchanged. The new behavior is
   strictly opt-in.

## Hypothesis ledger

- **H38** [채택] Sync `progress(msg, frac)` callback threaded through
  the async pipeline is sufficient to stream UI updates; no need for
  observer patterns, pub/sub, or task introspection.
- **H39** [채택] Gradio async generators yielding per-step tuples
  surface progress smoothly without `gr.Progress()` track_tqdm
  plumbing. The Markdown log + status line carry enough signal.
