# 260601 — Path D: strict layout critic + deterministic arrow clipping

> Follow-up to [[docs/progress/260601_path_d_mixed_vector_raster.md]]. Triggered by
> dogfooding: a real Path D figure (`figure_712736c6.svg`, "Hallmarks of cancer"
> radial diagram) shipped with good icons but broken composition.

## 1. Context / problem

User feedback: "각각 component는 괜찮은데 합치는게 엉망이야. 화살표나 그림 크기나."
(Components fine, composition garbage — arrows and sizes.)

Diagnosed from the shipped SVG geometry (hub-and-spoke radial, central tumor cell
+ 5 hallmark nodes):

| Symptom | Geometry evidence |
|---------|-------------------|
| Arrow tails buried in hub | every `<line>` starts at `(800,400)` = dead center of hub `<image>` (700–900 × 305–495) |
| Arrowheads buried under node icons | each line *ends* at the node icon's center (e.g. `(800,100)` inside node box 750–850 × 50–150) |
| Node icons unequal size | node heights `99,100,54,49,90` — angiogenesis/immune-evasion squished |
| Lopsided radial | node distances from center `300` vs `~447–500`, not equidistant |

Root cause: **Path D backbone is 100% LLM-authored geometry** with naive
center-to-center connectors and no peer-size/radial normalization. The existing
vision critic (`VISION_CRITIC_SYSTEM`) was **pipeline/stage-box-specific** — its 12
categories (Phase I/II/III boxes, time-axis ticks, "stage boxes in same row") do not
describe a radial diagram, so it returned `has_issues=false` and shipped pass 1.

## 2. Plan

User direction: "critic을 교수님 수준으로 굉장히 엄격하게" + "deterministic 클리핑도 추가".

1. Rewrite `VISION_CRITIC_SYSTEM` → professor / top-journal-editor persona,
   figure-type-agnostic, with new geometric categories: buried-arrow detection,
   connector-through-icon, peer symmetry (equal size + equal radius), grid
   alignment, composition balance. Default stance = reject; "when in doubt, flag".
2. Add matching generator rules to Path D `SYSTEM_PROMPT`: arrows attach to icon
   EDGES (≈5–8px gap), never centers; radial peer uniformity; grid alignment.
   Mirror in `build_refine_prompt` common-fixes so regen can act.
3. Bump `DEFAULT_MAX_REFINE_PASSES` 2 → 3 (strict critic needs convergence room).
4. **Deterministic backstop**: new `app/tools/arrow_clip.py` clips every `<line>`
   endpoint inside an icon box back to the box boundary + gap, along the line's own
   direction. Runs in `_assemble_mixed` after icon fill. Pure geometry, no LLM.

## 3. Execution

- `app/tools/arrow_clip.py` (new) — `clip_connectors_to_icons(root)`. Collects icon
  boxes (`<image>` + unfilled `<rect class="gen-icon">`), pushes any `<line>`
  endpoint inside a box out to the boundary + `DEFAULT_GAP=6.0`, toward the other
  endpoint. Iterates for overlapping boxes. Scope: straight `<line>` only (bezier
  `<path>` deferred).
- `app/tools/mixed_schematic.py` — import + call clip after icon fill, before final
  validate; `DEFAULT_MAX_REFINE_PASSES` 2 → 3.
- `app/agent/prompts/layout_critic.py` — `VISION_CRITIC_SYSTEM` fully rewritten
  (shared by Path A + D, so both get stricter).
- `app/agent/prompts/mixed_schematic.py` — arrow-attachment + peer-symmetry +
  grid-alignment rules in `SYSTEM_PROMPT`; matching lines in `build_refine_prompt`.
- `tests/test_arrow_clip.py` (new) — 7 tests: no-icons no-op, outside untouched,
  tail-buried→edge, both-endpoints clipped between two boxes, diagonal, unfilled
  gen-rect, margin.

## 4. Verify

- `uv run pytest` — full suite green (5 skipped = live). Import gate ✓.
- Replayed the **real** shipped figure through `clip_connectors_to_icons`:
  all 10 endpoints adjusted. e.g. `(800,400)→(800,100)` → `(800,299.3)→(800,155.7)`
  (tail above hub top 305, head below node bottom 150);
  `(800,400)→(1200,200)` → `(905.4,347.3)→(1145.7,227.1)` (hub right-edge → node
  left-edge). Buried arrows eliminated deterministically.

## 5. Lessons

- The critic was **silently myopic**: a rubric written for one figure type (pipeline)
  passes everything else. Vision critics must be framed figure-type-agnostically or
  they create false confidence.
- LLM geometry needs a **deterministic floor**. Even with stricter prompts + critic,
  center-to-center connectors are a systemic generation habit; the clipping pass
  guarantees correct attachment regardless of LLM variance.

## Hypotheses

- H63 (strict figure-agnostic vision critic flags radial/arrow defects the
  pipeline-specific critic missed): 검증중 — needs live dogfood regen.
- H64 (deterministic arrow clipping removes buried tails/heads with zero LLM
  variance): 채택 — proven on the real figure (10/10 endpoints) + 7 unit tests.

## Deferred

- Bezier `<path>` connector clipping (only straight `<line>` handled in v1).
- Wire `clip_connectors_to_icons` into Path A if `<use>`-symbol figures show the
  same buried-arrow pattern.
- Deterministic peer-size / radial-radius normalization (currently prompt+critic
  only; clipping fixes arrows but not unequal node sizes).
