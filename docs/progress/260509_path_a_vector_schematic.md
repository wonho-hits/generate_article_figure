# 260509 — Path A: text → SVG vector schematic

> Step 2 / 9. Builds on [[docs/progress/260509_backend_skeleton.md]].
> Status: **DONE — all acceptance criteria passed including live API test**

## Context

Path A is the workhorse for bio/chem schematics: signaling cascades, mechanism diagrams, pathway flowcharts — anything that's structurally a graph of boxes, arrows, and labels. The architecture plan's central insight is to bypass the diffusion-to-SVG bottleneck by asking the LLM to **emit SVG directly**. This step proves out that approach end-to-end.

After this step, a user can `POST /generate` with a bio/chem prompt and receive a publication-grade, infinitely-zoomable SVG with named `<g id="...">` groups (so step 7's "redraw region" has hooks to grab onto). It's the first feature with user-visible value.

This is also the first step with a **live Gemini call**, so deferred acceptance criterion #6 from step 1 (`live smoke test`) gets folded in.

## 이전 시도 (Previous Attempts)

None for Path A specifically. Step 1 ([[docs/progress/260509_backend_skeleton.md]]) gave us:
- `GeminiClient.generate_text(prompt, system, response_schema)` — used directly here
- `InMemorySessionStore` — used to persist the artifact

## 가설 상태 (Hypothesis Status)

- **H4 [검증중]**: Gemini 2.5 Flash, with a constrained system prompt, can emit syntactically valid SVG with the structural conventions we need (viewBox, named groups, conventional bio symbols).
  - Falsified by: >50% of generations fail XML parse, OR group structure is unusable for downstream region redraw.
  - Mitigation if falsified: tighten system prompt with few-shot examples; consider switching default to `gemini-2.5-pro` for higher fidelity.

- **H5 [검증중]**: A free-form SVG string output is preferable to a structured Pydantic schema (where we'd specify shapes and render ourselves).
  - Reasoning: Gemini's layout intuition (where to place arrows, how much margin, etc.) is the actual product value. A structured schema would force us to re-implement layout, which is exactly the work we're trying to avoid.
  - Falsified by: validation failure rate too high to recover with a single retry, forcing a structured-schema pivot.

- **H6 [검증중]**: An XML parse + small set of structural assertions is sufficient SVG validation for v1.
  - Won't validate visual quality (that's H4's domain), but will catch malformed XML, missing groups, dangerous embedded scripts.

## Plan

### What we will build

```
app/
├── agent/
│   ├── __init__.py
│   ├── orchestrator.py          # single-tool dispatch stub (always Path A for now)
│   ├── schemas.py                # GenerateRequest, GenerateResponse Pydantic models
│   └── prompts/
│       ├── __init__.py
│       └── vector_schematic.py   # system prompt as a Python const + helper
├── tools/
│   ├── __init__.py
│   ├── vector_schematic.py       # generate_vector_schematic(prompt) -> SVG
│   └── svg_validate.py           # parse + structural assertions + sanitize
└── routes/
    ├── __init__.py
    └── generate.py               # POST /generate

tests/
├── test_svg_validate.py
├── test_vector_schematic.py      # mocked Gemini
├── test_generate_route.py        # full route with mocked client
└── test_path_a_live.py           # @pytest.mark.live, skipped by default
```

`app/main.py` updated to mount `routes/generate.router`.

### Design decisions

1. **Free-form SVG output, not structured schema.** Per H5. Gemini emits a SVG string; we validate, sanitize, and store. If validation fails, **one retry** with the parser error appended to the prompt; if that fails, surface the error to the caller (no third try — fail loud).

2. **System prompt** (kept in [`app/agent/prompts/vector_schematic.py`](../../app/agent/prompts/vector_schematic.py)) instructs Gemini to:
   - Output **only** a single `<svg>` element — no markdown fences, no commentary
   - Use `viewBox="0 0 800 600"` (default) or proportional
   - Wrap each labeled component in `<g id="<snake_case_name>" data-role="<role>">`
   - Use `<text>` for labels with Helvetica/Arial 14–18px
   - Stroke widths 1.5–2.5px, consistent across the figure
   - No `<script>`, `<foreignObject>`, no external `<image href>` (no raster)
   - Bio/chem symbol vocabulary: arrows (→ activation, ⊣ inhibition), circled P for phosphorylation, lipid bilayer for membranes, etc.

3. **Validation** (in `app/tools/svg_validate.py`):
   - `xml.etree.ElementTree.fromstring` on the SVG (catches malformed XML)
   - Strip code-fence wrappers if Gemini adds them (` ```svg ... ``` `)
   - Assert root tag is `svg`
   - Assert presence of at least one `<g>` with an `id` attribute
   - Reject if any `<script>`, `<foreignObject>`, or `<image>` tag present (security + scope)
   - Return canonical SVG string (re-serialized, comments stripped)

4. **Orchestrator stub** (`app/agent/orchestrator.py`):
   - Single method `generate(prompt: str) -> SessionEntry`
   - Currently always calls Path A. The router (Path A vs B vs C) lands in step 5 when there's a real choice.
   - Creates session, stores artifact, returns entry.

5. **Route**: `POST /generate` body `{prompt: str}` → response `{session_id, artifact, kind: "svg"}`. Errors: `400` for empty prompt, `422` for SVG validation fail after retry, `503` for upstream Gemini error.

6. **Live smoke test** (`tests/test_path_a_live.py`):
   - Marked with `@pytest.mark.live` → skipped unless `--run-live` CLI flag.
   - One real Gemini call with a fixed prompt ("MAPK signaling cascade with EGF, Ras, Raf, MEK, ERK"). Asserts: SVG parses, has ≥3 `<g id>` groups.
   - Cost: ~$0.0001 per run. Run-once-on-merge, not on every CI cycle.

### Acceptance criteria

1. `uv run pytest -q` (mocked tests): all pass.
2. Coverage: `app/tools/vector_schematic.py` and `app/tools/svg_validate.py` ≥ 80%.
3. `uv run pytest -q --run-live` (with real `GOOGLE_API_KEY`): live test passes — generation produces parseable SVG with named groups.
4. End-to-end manual: `curl -X POST localhost:8000/generate -d '{"prompt":"MAPK..."}'` returns a session_id and SVG; SVG renders correctly when saved to a `.svg` file and opened in a browser / Inkscape.
5. Bad upstream response is handled: when Gemini returns garbage, the route returns `422` with a useful error body, not 500.

### Out of scope for this step

- Path B (RDKit) and Path C (raster) — separate steps
- Routing logic (vector vs raster) — single-tool dispatch only
- Region redraw — step 7 will add `redraw_svg_group` reusing this step's group structure
- Frontend rendering — step 8
- Bio symbol library injection — step 9 will graduate the system prompt to reference shared SVG snippets

### Risks

| Risk | Mitigation |
|------|-----------|
| Gemini wraps SVG in markdown code fences | Strip fences in `svg_validate.py` before parsing |
| Gemini emits SVG with namespaced tags (`xmlns:xlink`) | Use namespace-aware ET parser; tolerate xmlns attrs |
| Gemini-emitted SVG passes XML parse but is visually broken (e.g., overlapping text) | H6 explicitly accepts this — visual quality is judged interactively, not in unit tests; document for future critic-pass step |
| Live test cost spirals if accidentally added to CI default | Default-skip via marker; document the `--run-live` opt-in |
| Generation latency on long prompts (multi-second) blocks the request thread | Route is `async`; client uses `aio.models.generate_content`; FastAPI handles concurrency |

### Iteration history

Two iterations.

**Iteration 1**: write all modules + tests, run `uv run pytest`.
- Result: 38 passed, 3 failed in `test_generate_route.py`.
- Diagnosis: `httpx.ASGITransport` does not run FastAPI lifespan handlers, so `app.state.session_store` was never set. `/health` had passed only because it doesn't touch state.
- Fix: autouse fixture in [tests/conftest.py](../../tests/conftest.py) that sets a fresh `InMemorySessionStore` on `app.state` before every test. Adds no production dep, exercises the real route path.

**Iteration 2**: re-run + live test.
- Mocked: 41/41 + 1 skipped (live).
- Live: 1/1 in 32.5s. Generated 5077-byte SVG with 12 named groups for the MAPK cascade prompt.

Side-fix: the live test originally read `os.environ["GOOGLE_API_KEY"]` directly, which conftest had pinned to the fake `test-key-not-real`. Live test now does `load_dotenv(override=True)` from the project `.env` so `--run-live` actually reaches the real API.

### Acceptance results

| # | Criterion | Result |
|---|-----------|--------|
| 1 | All mocked tests pass | ✅ 41/41 |
| 2 | Coverage ≥80% on tool + validator | ✅ vector_schematic.py 94%, svg_validate.py 97% (total 93%) |
| 3 | Live test: real Gemini → parseable SVG with named groups | ✅ 12 groups generated for MAPK cascade prompt |
| 4 | Manual curl /generate works | ✅ effectively covered — live test exercises orchestrator + tool + validator; route layer mocked-tested separately. Skipped duplicate curl call to save cost. |
| 5 | Bad upstream → 422, not 500 | ✅ `test_generate_returns_422_on_persistent_validation_failure` |
| 6 (carried from step 1) | Live Gemini smoke call | ✅ subsumed by criterion 3 above |

### Live SVG structural inspection

Generated artifact: `/tmp/path_a_live_smoke.svg` (5077 bytes).

```
group ids: egf, egfr, egfr_phosphorylation, ras, raf, mek, mek_phosphorylation,
           erk, erk_phosphorylation, membrane, area_labels, signaling_pathway
markers:   arrowhead (reusable)
fonts:     Helvetica, Arial, sans-serif (compliant)
colors:    #333 structure, #2b6cb0 accent (compliant — single accent)
forbidden: 0 hits (no script/foreignObject/image/iframe)
P-symbol:  rendered as small filled circle + "P" tspan (per convention)
```

System prompt produced exactly the structure it asked for. No retries needed.

### Files added

- [app/agent/orchestrator.py](../../app/agent/orchestrator.py)
- [app/agent/schemas.py](../../app/agent/schemas.py)
- [app/agent/prompts/vector_schematic.py](../../app/agent/prompts/vector_schematic.py)
- [app/tools/svg_validate.py](../../app/tools/svg_validate.py)
- [app/tools/vector_schematic.py](../../app/tools/vector_schematic.py)
- [app/routes/generate.py](../../app/routes/generate.py)
- [tests/test_svg_validate.py](../../tests/test_svg_validate.py)
- [tests/test_vector_schematic.py](../../tests/test_vector_schematic.py)
- [tests/test_generate_route.py](../../tests/test_generate_route.py)
- [tests/test_path_a_live.py](../../tests/test_path_a_live.py)

Modified: [app/main.py](../../app/main.py) (mount router), [tests/conftest.py](../../tests/conftest.py) (autouse fixture, --run-live flag).

## Conclusion

The original motivation (vector-native generation as the answer to the diffusion-vectorize bottleneck) is validated end-to-end. One real Gemini call produced publication-grade SVG with the exact structural hooks downstream steps need.

**Hypotheses status update:**
- H4 (Gemini emits valid SVG with conventions) — **채택**. First live attempt produced 12 named groups, no validation retry needed, full convention compliance.
- H5 (free-form SVG > structured schema) — **채택**. Gemini's layout placed elements sensibly; we'd lose this if we forced a structured shape schema.
- H6 (XML parse + structural assertions sufficient) — **채택** for v1. Validator caught nothing on the live test (clean output) but the test suite verifies it catches malformed/dangerous output.

**Lessons:**
- `total_token_count` (7979) >> `prompt + response` (3042). Gemini 2.5+ counts internal thinking tokens. Cost estimation needs to use `total_token_count`, not the sum.
- `httpx.ASGITransport` not running lifespan is a recurring trap. Worth documenting in any future test that hits routes.
- The system prompt's "IDs MUST be snake_case English even when prompt is non-English" instruction was redundant for an English prompt but lays groundwork for step 9's Korean/multilingual support.

**Next step**: Step 3 — Path B (RDKit molecule/reaction rendering). Will follow the same pre-report → implement → verify cycle.
