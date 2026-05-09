# 260509 — Path C raster + Router (Path A vs C dispatch)

> Step 3 / 9 (re-ordered after [[docs/progress/260509_path_c_probe.md]]).
> Builds on [[docs/progress/260509_path_a_vector_schematic.md]].
> Status: **DONE — all acceptance criteria passed including 8/8 router live eval**

## Context

The probe ([[docs/progress/260509_path_c_probe.md]]) showed `gemini-3.1-flash-image-preview` (Nano Banana 2) produces single-shot publication-quality multi-cell figures. This step graduates Path C from prototype to production: clean tool surface, integrated into the orchestrator, dispatched by an LLM router that decides Path A vs C per prompt.

After this step:
- Schematic prompts (pathway, mechanism, flowchart) → Path A → SVG
- Illustrative prompts (cells, anatomy, tumor microenvironment) → Path C → PNG
- The `/generate` route is the single entry point for both, with consumers receiving either raw SVG or a data-URI PNG plus a `kind` field.

This is also the first step where the **orchestrator does real work** — picking between tools instead of always calling Path A.

## 이전 시도 (Previous Attempts)

Path C single-call probe ([[analyze/260509_path_c_complex_figure_probe.py]]):
- Cost $0.04, latency 27.8s, score 6/8 → ADOPT.
- Identified two patterned defects: duplicate elements, occasional duplicate labels. Fixable in step 4 (inpainting).

Path A live test ([[tests/test_path_a_live.py]]):
- 12 named SVG groups for MAPK cascade prompt, no retries. H4/H5/H6 채택.

## 가설 상태 (Hypothesis Status)

- **NEW H9 [검증중]**: An LLM router (single text-only Gemini call, structured Pydantic output) classifies prompts into Path A vs Path C with ≥ 90% agreement on a small evaluation set.
  - Falsified by: misroutes a clearly-illustrative prompt to A or vice versa on the eval set.
  - Mitigation if falsified: tighten router system prompt; add few-shot examples; consider keyword pre-filter.

- **NEW H10 [검증중]**: A short style prefix prepended to the user's prompt is enough to enforce BioRender-like consistency, without needing a separate `system_instruction` channel.
  - Image models typically don't honor `system_instruction` reliably. Prefix-in-prompt is the universal escape hatch.

- **H7 [채택, monitor]**: Path C single-shot quality is sufficient for v1. Carry over from probe; revisit if defect rate spikes.

## Plan

### What we will build

```
app/
├── agent/
│   ├── orchestrator.py           # UPDATED: dispatch via router; explicit override
│   ├── router.py                  # NEW: LLM A/C classifier
│   ├── schemas.py                 # UPDATED: figure_kind, RoutingDecision
│   └── prompts/
│       ├── raster_illustration.py # NEW: BioRender-style prefix
│       └── router.py              # NEW: classifier system prompt
├── tools/
│   └── raster_illustration.py     # NEW: Gemini Image → PNG bytes
└── routes/
    └── generate.py                # UPDATED: base64 PNG, routing_reason field

tests/
├── test_router.py                 # NEW: mocked router
├── test_raster_illustration.py    # NEW: mocked Path C tool
├── test_generate_route.py         # UPDATED: tests both paths + override
├── test_path_a_live.py            # UNCHANGED
├── test_path_c_live.py            # NEW: live raster smoke test
└── test_router_live.py            # NEW: live routing eval (5 prompts)
```

### Key design decisions

1. **Routing trifecta — explicit `figure_kind` field on the request.**
   ```
   figure_kind: "auto" | "vector" | "raster"   (default "auto")
   ```
   - `"auto"` → router decides
   - `"vector"` → force Path A
   - `"raster"` → force Path C
   Lets users override the router when they know what they want. Costs nothing to expose.

2. **Router as a single LLM call, not a hand-coded heuristic.**
   - Pydantic schema `RoutingDecision { path: "A"|"C", reason: str }`.
   - Uses `GeminiClient.generate_text(prompt, system=ROUTER_SYSTEM, response_schema=RoutingDecision)`.
   - Cost ≪ generation cost, ~1s latency, easy to evolve via prompt edits.
   - Heuristics (keyword match) considered and rejected — too brittle for free-form scientific prompts.

3. **Path C tool emits raw `bytes`, not a data URI.**
   - Session store keeps raw bytes — needed for step 4 (inpainting) which feeds bytes back to Gemini.
   - Route layer serializes to `data:image/png;base64,<...>` only for HTTP response.
   - Result: `artifact: str` in the response carries either SVG XML (`kind="svg"`) or a data URI (`kind="png"`). Consumer branches on `kind`.

4. **Style prefix in prompt, not `system_instruction`.**
   - Image models inconsistently honor system_instruction. Prefix the user's prompt with the BioRender-style preamble we know works (from the probe).
   - Style prefix kept in [`app/agent/prompts/raster_illustration.py`](../../app/agent/prompts/raster_illustration.py) for easy iteration.

5. **No retry on Path C.**
   - Image generation is non-deterministic and expensive ($0.04/call). A failed generation more often means a bad prompt than a transient error. Surface the failure to the caller; let them re-prompt or use override.
   - The Gemini SDK's own retry on 5xx/429 is preserved (in `_call_with_retry`).

### Acceptance criteria

1. **Mocked unit tests pass.** All new test files green; existing tests unaffected.
2. **Coverage** ≥ 80% on `app/agent/router.py`, `app/tools/raster_illustration.py`, and updated `app/agent/orchestrator.py`.
3. **Routing live test** (`test_router_live.py`): on an 8-prompt eval set (3 A + 5 C, including 3 user-supplied edge cases), router correctly classifies all 8. Eval set:
   - "MAPK signaling cascade with EGF, Ras, Raf, MEK, ERK" → **A**
   - "phosphorylation cycle of a kinase substrate" → **A**
   - "western blot quantification flowchart" → **A**
   - "tumor microenvironment with cancer cells, M1/M2 macrophages, dendritic cells, T cells" → **C**
   - "structural overview of a eukaryotic cell with labeled organelles" → **C**
   - (user) Fe catalyst on graphene with ball-and-stick model → **C** (atomic models)
   - (user) Naked Mole-rat DNA damage pathway w/ "2D vector style" + lab-animal icons → **C** (content overrides style hint; lab animals need raster)
   - (user) cinematic savanna/rainforest landscape, photorealistic → **C** (photorealistic)
4. **Path C live test** (`test_path_c_live.py`): one real call, asserts non-empty PNG bytes returned; saved to `/tmp/path_c_live_smoke.png` for eyeball check. No quality assertion (visual judgment is human-in-the-loop).
5. **End-to-end mocked**: `POST /generate {"prompt": "...", "figure_kind": "raster"}` returns `kind: "png"`, artifact starts with `data:image/png;base64,`. Same with `"vector"` returns `kind: "svg"`.
6. **Bad upstream → 503**: Gemini APIError on Path C generation surfaces as 503 with useful detail (mirrors Path A behavior).

### Out of scope for this step

- Inpainting / region redraw (step 4)
- Editing labels on raster output (step 4 / 7)
- Background removal (step 7)
- PPTX export of raster (step 5)
- Frontend UI changes (step 8)
- Symbol library — confirmed deferred per probe verdict

### Risks

| Risk | Mitigation |
|------|-----------|
| Router misclassifies edge prompts (e.g., "schematic of a cell membrane with embedded receptors" — could be either) | `figure_kind` override is the user escape hatch. Live eval catches systematic miscategorization. |
| Router cost adds up over many requests | One short text call (~50 input + ~30 output tokens) per request. Negligible vs. image gen cost. Could cache by prompt hash if it ever matters. |
| Image model returns text-only response (no image part) | `GeminiClient.generate_image` already raises `GeminiResponseError`; route layer maps to 503. |
| `system_instruction` channel for image model: untested whether honored | Sidestepped — using prompt prefix. |
| Total token count vs prompt+response gap (lesson from step 2) | Path C cost reporting needs to use `total_token_count` field for accuracy. Update logging accordingly. |

### Iteration history

Two iterations.

**Iteration 1**: write all modules + tests → 52/52 mocked pass, 95% coverage. Run live → 2 failures surfaced two SDK realities I hadn't seen documented:

1. `google-genai` 1.x does NOT auto-populate `response.parsed` for structured output even when `response_schema` is set. The router got `GeminiResponseError("response_schema requested but SDK returned no parsed object")` on every call.
2. `gemini-3.1-flash-image-preview` returns **JPEG**, not PNG. The hardcoded `data:image/png;base64,` prefix would have served broken data URIs to clients.

**Iteration 2**: surgical fixes.
- [app/clients/gemini.py](../../app/clients/gemini.py): when `response.parsed` is `None`, fall back to `response_schema.model_validate_json(response.text)`. Both paths return the same Pydantic instance.
- [app/tools/raster_illustration.py](../../app/tools/raster_illustration.py): added `detect_image_mime(bytes) -> str` that inspects magic bytes (PNG / JPEG / WebP / GIF / fallback `application/octet-stream`).
- [app/agent/orchestrator.py](../../app/agent/orchestrator.py): build data URI with detected MIME instead of hardcoded `image/png`.
- [app/agent/schemas.py](../../app/agent/schemas.py): renamed `ArtifactKind` literal `"png"` → `"raster"` (semantic — actual format lives in the data URI).
- Tests: `FAKE_PNG` made to use real magic bytes; added `test_path_c_jpeg_response_uses_image_jpeg_mime`; added `test_detect_*` for each MIME.

Re-run: 58/58 mocked, 8/8 router live, 1/1 Path C live.

### Acceptance results

| # | Criterion | Result |
|---|-----------|--------|
| 1 | All mocked tests pass | ✅ 58/58 |
| 2 | Coverage ≥ 80% on router.py + raster_illustration.py + orchestrator.py | ✅ 100% / 100% / 100% (total 95%) |
| 3 | Router live eval: 8/8 correct on user-provided + standard prompts | ✅ **8/8** including the ambiguous "2D vector style" + lab-animal Naked Mole-rat case (correctly classified to C) |
| 4 | Path C live: returns valid image bytes | ✅ 493 KB JPEG, magic bytes verified |
| 5 | E2E `figure_kind="raster"`/"vector"/"auto" | ✅ all three paths covered with mocks |
| 6 | Bad upstream → 503 | ✅ APIError + GeminiResponseError both mapped |

### Router live eval — full results

```
expected=A got=A  MAPK signaling cascade ...     | reasoning: signaling cascade as abstract block diagram
expected=A got=A  Phosphorylation cycle ...      | reasoning: cycle as abstract structure
expected=A got=A  Western blot flowchart ...     | reasoning: experimental workflow flowchart
expected=C got=C  Tumor microenvironment ...     | reasoning: morphologically-distinct cell types
expected=C got=C  eukaryotic cell organelles ... | reasoning: drawn as biological illustrations
expected=C got=C  Fe catalyst graphene ...       | reasoning: ball-and-stick model of atoms
expected=C got=C  Naked Mole-rat DNA damage ...  | reasoning: scientific icons of lab animals
expected=C got=C  cinematic savanna ...          | reasoning: photorealistic landscape with natural forms
```

Token economics: 466–524 input tokens (system prompt is the bulk), 36–47 output tokens. ~$0.0001 per routing call. Negligible.

### Path C live smoke — visual inspection

Prompt: T cell receptor binding to MHC class I on a tumor cell with downstream signaling.

Output: 493 KB JPEG. Inspected. Renders:
- CD8+ T cell with mitochondria, ER, nucleus labeled "Transcription of T Cell Activation Genes" + IFNγ / Perforin / Granzyme effector molecules
- Full TCR signaling cascade: ZAP-70 → LAT → SLP-76 → PLCγ1 → IP₃ → Ca²⁺ Release → NFAT → AP-1 (with mixed dashed/solid arrows used appropriately)
- Tumor cell on right with three MHC Class I receptor complexes drawn as multi-domain quaternary structures
- TCR-pMHC binding interface highlighted with a dashed circle

This output is *more elaborate than the prompt requested* — the model auto-elaborated the TCR signaling pathway with biologically-correct molecular nomenclature (ZAP-70, PLCγ1, AP-1). Greek letters, subscripts, and pathway logic are all correctly rendered. This validates that Path C is the correct primary path for complex bio figures.

### Files added / modified

Added:
- [app/agent/router.py](../../app/agent/router.py)
- [app/agent/prompts/router.py](../../app/agent/prompts/router.py)
- [app/agent/prompts/raster_illustration.py](../../app/agent/prompts/raster_illustration.py)
- [app/tools/raster_illustration.py](../../app/tools/raster_illustration.py) (with `detect_image_mime`)
- [tests/test_router.py](../../tests/test_router.py)
- [tests/test_raster_illustration.py](../../tests/test_raster_illustration.py)
- [tests/test_router_live.py](../../tests/test_router_live.py)
- [tests/test_path_c_live.py](../../tests/test_path_c_live.py)

Modified:
- [app/agent/schemas.py](../../app/agent/schemas.py): added `figure_kind`, `RoutingDecision`, `routing_reason`; renamed kind `"png"` → `"raster"`
- [app/agent/orchestrator.py](../../app/agent/orchestrator.py): full rewrite for two-path dispatch
- [app/routes/generate.py](../../app/routes/generate.py): handle `GeminiResponseError`
- [app/clients/gemini.py](../../app/clients/gemini.py): manual JSON-validation fallback for structured output
- [tests/test_generate_route.py](../../tests/test_generate_route.py): both-paths + override coverage

## Conclusion

Path C is operational and is the correct primary path for complex bio/chem illustrations. The router classifies prompts reliably enough on a small but stress-tested eval set (8/8). The orchestrator now does real work — choosing a path and dispatching with explicit override support.

**Hypotheses status update:**
- **H7** (Path C single-shot quality sufficient) — **채택**, double-confirmed by the smoke test which auto-elaborated correct molecular nomenclature.
- **H9** (LLM router ≥ 90% on eval) — **채택** — 100% (8/8). Router system prompt's explicit "content overrides style hints" rule was load-bearing for the Naked Mole-rat case.
- **H10** (style prefix > system_instruction) — **채택**, prefix produced the BioRender styling consistently in the smoke output.
- H8 (inpainting fixes Path C duplicate-element defects) — still 검증중, deferred to step 4.

**Lessons:**
1. **`google-genai` 1.x structured-output gotcha**: `response.parsed` is not auto-populated; manual fallback via `model_validate_json(response.text)` is necessary. Worth a CODENOTES entry — every future structured-output caller will hit this.
2. **Image format isn't PNG**: Gemini 3.1 image preview returns JPEG. Schema/MIME assumptions baked into early code would have shipped corrupted data URIs.
3. **Router cost is irrelevant**: ~$0.0001 per call is rounding error vs. image gen ($0.04). Don't optimize routing latency until the rest of the pipeline is in place.
4. **Image gen elaborates beyond the prompt**: this is a feature for "first draft" usage but means quality is non-deterministic — same prompt can yield different complexity levels. Step 4 (inpainting) gives users back control.

**Next step**: Step 4 — Inpainting / region redraw. This is now load-bearing because Path C outputs occasionally have local defects (probe found duplicate T cell + duplicate label) and inpainting is how users surgically fix them.
