# 260509 — Backend Skeleton

> Step 1 / 9 of build order in [[docs/plans/architecture.md]] (mirrored from `~/.claude/plans/agile-growing-flamingo.md`).
> Status: **DONE — all 5 acceptance criteria passed**

## Context

Greenfield project. The full architecture has been agreed:
text → publication-quality figure for **bio/chem** domain, single orchestrator agent, three rendering paths (LLM-SVG / RDKit / Gemini Image), exported to PPTX & SVG.

This step lays the foundation. Without a stable skeleton — config, session state, Gemini client, FastAPI shell — nothing downstream can be implemented or tested. The skeleton's job is **not** to do anything user-visible yet. Its job is to make subsequent steps (Path A, Path B, exporters, etc.) cheap to add.

Why this step matters now:
- All downstream tools need a single, validated Gemini client wrapper (auth, retry, cost logging) — building it once at the start avoids drift.
- Session state (`figure_id → current_artifact + history`) is required by step 2 (Path A) onward; deferring forces awkward refactors.
- FastAPI surface gives us a deterministic local target to call during Path A development, before any frontend exists.

## 이전 시도 (Previous Attempts)

None. Greenfield.

## 가설 상태 (Hypothesis Status)

- **H1 [검증중]**: A single orchestrator agent + typed Python tools is sufficient; no multi-agent system needed for v1.
  - Evidence so far: pipeline is router + tool-call shape, no concurrent-reasoning workload.
  - To be falsified by: tool-routing prompt becomes unmaintainable, OR latency forces parallelism.

- **H2 [검증중]**: In-memory session store (dict keyed by session_id, TTL eviction) is sufficient for v1.
  - Evidence so far: single-user, single-process target. No persistence requirement stated.
  - To be falsified by: session loss on restart becomes painful, OR multi-process deployment becomes a goal.

- **H3 [채택]**: Python 3.12 (not 3.14) is the right pin.
  - Evidence: system Python is 3.14.4, but RDKit / rembg / numpy 2.x ecosystem most reliably ships wheels for 3.11–3.12. Path B and step 6 will hit this directly.
  - Action: `uv python pin 3.12` and use `uv sync` for the env.

## Plan

### What we will build in this step

```
generate_article_figure/
├── pyproject.toml              # uv-managed; Python 3.12 pin; deps: fastapi, uvicorn, pydantic, pydantic-settings, google-genai, python-dotenv, httpx, structlog
├── .python-version             # "3.12"
├── .gitignore                  # .env, .venv, __pycache__, *.pyc, dist/, build/
├── .env.example                # GOOGLE_API_KEY=
├── README.md                   # bare-bones: how to run
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app factory, /health endpoint
│   ├── config.py               # pydantic-settings reading .env
│   ├── logging.py              # structlog config
│   ├── clients/
│   │   ├── __init__.py
│   │   └── gemini.py           # async wrapper: text + image, retry, cost log
│   └── state/
│       ├── __init__.py
│       └── session.py          # SessionStore protocol + InMemorySessionStore impl
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_health.py          # GET /health returns 200
    ├── test_gemini_client.py   # mocked: text call, error retry, cost log shape
    └── test_session_store.py   # put/get/expire
```

### Key design decisions

- **Gemini client**: use the new `google-genai` SDK (current Python SDK for Gemini, supersedes `google-generativeai`). Async only. Two methods: `generate_text(prompt, *, system: str | None, response_schema: type[BaseModel] | None)` and `generate_image(prompt, *, reference_images: list | None)`. Built-in:
  - Exponential backoff on 5xx / 429 (max 3 retries)
  - Per-call cost logging (token counts → structlog event)
  - Response-schema validation via Pydantic when caller asks for structured output (used by router and Path A)
- **Session store**: `Protocol` + in-memory impl now; future Redis impl can be a drop-in.
- **Config**: `pydantic-settings.BaseSettings` reading `.env`. Required: `GOOGLE_API_KEY`. Optional: `LOG_LEVEL`, `SESSION_TTL_SECONDS=3600`, `GEMINI_TEXT_MODEL`, `GEMINI_IMAGE_MODEL`.
- **No tool registry yet**. Tools will be added in step 2+. Orchestrator stays empty in this step — just the shell.

### How we verify (acceptance criteria)

Each must pass before this step is marked complete:

1. `uv sync` succeeds on Python 3.12.
2. `uv run uvicorn app.main:app --reload` starts cleanly.
3. `curl localhost:8000/health` returns `{"status": "ok"}`.
4. `uv run pytest -q` passes; coverage on `app/clients/gemini.py` and `app/state/session.py` ≥ 80% (mocking the network).
5. `app.config.Settings()` raises a clear validation error when `GOOGLE_API_KEY` is missing (smoke-tested with a temp `.env`).
6. Live smoke test (manual, optional): `uv run python -c "import asyncio; from app.clients.gemini import GeminiClient; print(asyncio.run(GeminiClient().generate_text('say hi in 3 words')))"` — confirms real API reachability before moving to step 2.

### Out of scope for this step

- Any tool implementation (vector_schematic, molecule, etc.) — those are step 2+
- Frontend — even Gradio MVP is step 8
- Database / persistence — in-memory only
- Auth / multi-tenancy — single-user assumption

### Risks

| Risk | Mitigation |
|------|-----------|
| `google-genai` SDK API surface different from what I expect | Pin a known version; write the wrapper against the pinned version's docs (Context7 lookup before coding) |
| RDKit wheel availability later (step 3) on Python 3.12 | Verified separately before step 3; if 3.12 fails, downgrade to 3.11. Not a blocker for this step. |
| Async + sync mixing in tests | Use `pytest-asyncio` from the start |

### Iteration history

Single iteration — no surprises.

- Created project scaffold: `pyproject.toml` (uv-managed, Python 3.12 pin), `.python-version`, `.gitignore`, `.env.example`, `README.md`
- Wrote `app/{config,logging,main}.py` + `app/clients/gemini.py` + `app/state/session.py`
- Wrote 3 test modules: 15 tests total
- `uv sync` resolved cleanly: `google-genai 1.x`, `fastapi 0.46`, `pydantic 2.13`, `structlog 25.5`, `pytest 9.0`
- Tests passed first run; no integrity-gate failures encountered

### Acceptance results

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `uv sync` succeeds on Python 3.12 | ✅ Python 3.12.13 |
| 2 | `uvicorn app.main:app` starts cleanly | ✅ structured `app.start` log emitted |
| 3 | `/health` returns `{"status":"ok"}` | ✅ verified via curl |
| 4 | `pytest` passes; gemini.py + session.py ≥ 80% cov | ✅ 15/15 pass; **gemini.py 95%, session.py 94%, total 90%** |
| 5 | Settings raises validation error without `GOOGLE_API_KEY` | ✅ `ValidationError: google_api_key Field required` |
| 6 | Live Gemini smoke call (optional) | ⏸ deferred — cost-conscious; will run on first Path A use |

### Files added

- [pyproject.toml](../../pyproject.toml)
- [app/config.py](../../app/config.py)
- [app/logging.py](../../app/logging.py)
- [app/main.py](../../app/main.py)
- [app/clients/gemini.py](../../app/clients/gemini.py)
- [app/state/session.py](../../app/state/session.py)
- [tests/conftest.py](../../tests/conftest.py)
- [tests/test_health.py](../../tests/test_health.py)
- [tests/test_session_store.py](../../tests/test_session_store.py)
- [tests/test_gemini_client.py](../../tests/test_gemini_client.py)

### Coverage gaps (acceptable for skeleton)

- `app/logging.py` 56% — `configure_logging` only partially executed in test path; covered by lifespan smoke. Will be exercised more once routes log real events.
- `app/main.py` 67% — lifespan `finally` branch not asserted in test. Trivial; not worth a dedicated test.

## Conclusion

The motivation (give every downstream tool a stable, validated foundation) is satisfied. Subsequent steps can now:

- import `app.clients.gemini.GeminiClient` and call `generate_text` / `generate_image` without re-implementing auth, retry, or schema validation
- store and retrieve figure session state via `app.state.session.InMemorySessionStore`
- add new FastAPI routes by mounting on the existing `app` object

**Hypotheses status update:**
- H1 (single-agent sufficient) — still 검증중; will be tested when the orchestrator + router is built in step 2.
- H2 (in-memory session store) — still 검증중; first stress will come once Path A actually persists artifacts.
- H3 (Python 3.12 pin) — 채택 confirmed; all dependencies resolved cleanly.

**Lessons:**
- `google-genai` 1.x SDK exposes async via `client.aio.models.generate_content` and supports Pydantic `response_schema` directly — no manual JSON parsing needed. This will pay off in step 2 (router) and Path A (SVG schema validation).
- pydantic-settings env-var precedence over `.env` makes test isolation simple via `os.environ.setdefault` in conftest.

**Next step**: Step 2 — Path A (text → SVG vector schematic). Will follow the same pre-report → implement → verify cycle.
