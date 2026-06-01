# 260601 — Path D: vector backbone + all-generated raster icons

> Builds on [[docs/progress/260509_bio_symbol_library.md]] (hand-written symbols),
> [[docs/progress/260512_bioicons_pilot.md]] (bioicons bundling), and the
> Path A pipeline in `app/tools/vector_schematic.py`.
> Status: **IMPLEMENT COMPLETE + verified (mocked 258 pass + live e2e). Path D
> functional; layout-critic refinement is the next iteration.**

## Context

Path A (vector schematic) composes figures from a fixed catalog of 88
`<symbol>` defs (50 hand-written + 24 bioicons + 14 cropped wrappers),
referenced by the LLM via `<use href="#id">`. Everything is vector. The
catalog is finite, so Path A can only draw entities someone has already
authored. Two existing escape hatches, both blunt:

1. LLM approximates a missing entity from primitives → visibly worse than
   BioRender (triggered Step 9 + the bioicons pilot).
2. The whole figure routes to Path C (raster) → loses the precise,
   recolorable, PPTX-convertible vector backbone (arrows, labels, layout), AND
   inherits Path C's signature weakness: **garbled text inside the raster**.

**Path D** is a third path. Keep a *vector backbone* — arrows, connecting
lines, text labels, group/layout structure — all authored by the LLM as clean
SVG. But draw **every biological entity** (cell, receptor, organelle, molecule)
as a **Gemini-generated raster icon**, embedded as `<image>`. Path D does **not
mix in the bioicons / hand-written library at all** — every icon comes from
Gemini, so the figure has one consistent illustration source.

### Why all-generated (not library + gap-fill)

This is the 260601 design pivot. An earlier draft of Path D kept the library
symbols and only generated the *missing* icons. The researcher chose
all-generated instead:

- **No style clash.** Library symbols are flat Servier vector; generated icons
  are Gemini's style. Mixing them in one figure looks inconsistent. If *every*
  icon is generated, the figure has a single coherent look.
- **Sidesteps Path C's text weakness.** Text lives only in the vector backbone
  (crisp, recolorable, selectable). Icons are explicitly **text-free**, so
  there is no raster text to garble — Path C's biggest defect cannot occur.

### Icon requirements (researcher spec, 260601)

Every generated icon must be: **no text/letters**, **solid white background**,
**high-resolution**, **clean** (flat, no clutter). White bg → clean removal;
text-free → backbone owns all labels; high-res → no blur when the figure
scales.

### When Path D vs Path A vs Path C

- **Path A**: entities are well covered by the catalog. Pure vector, cheapest,
  fully editable.
- **Path D**: schematic-dominant figure (needs precise arrows/labels/layout)
  whose entities are NOT in the catalog or want a richer illustrated look.
- **Path C**: the whole figure is illustrative (cells/tissue scene) and a
  vector backbone adds little.

## 이전 시도 (Previous attempts)

- **Discussion 260601 (this session)**: user first proposed generating a
  missing icon and "cropping the white bg like SVG". Surfaced the core
  constraint — a Gemini icon is **raster (pixels)**, not vector; "SVG crop"
  (path clip) is impossible. Background removal yields a *transparent raster*,
  embedded as `<image href="data:...">`, not a vector `<symbol>`.
- **Pivot (same session)**: from "library + gap-fill mix" to "all icons
  generated, no library mixing" — for single-source style consistency and to
  sidestep raster text.
- **Blocker found**: `app/tools/svg_validate.py:23,78` explicitly forbids the
  `<image>` element. Path D requires a security-gated, data-uri-only exception.
- **Step 7 (background removal)**: deferred in CLAUDE.md but already scoped
  (rembg / U2Net). Path D is the concrete consumer that pulls it off the list.

## 가설 상태 (Hypothesis status)

- **H58 [채택]**: backbone + placeholders works. PROVEN by
  [[analyze/260601_path_d_live_e2e.py]]: the Path D prompt produced a vector
  backbone with 5 gen-icon placeholders (one per entity), 11 vector labels, 0
  text inside icon boxes, 0 unfilled leftover. LLM reserved boxes instead of
  drawing cells from primitives.
- **H59 [채택] (cross-icon consistency)**: A single fixed style prompt keeps
  *independently generated* icons in the same figure visually consistent.
  PROVEN by [[analyze/260601_path_d_icon_consistency_probe.py]]: 6 diverse
  entities, 6 separate calls → one coherent family. Fixed prefix sufficient;
  image-to-image fallback NOT needed.
- **H60 [채택 — threshold, no rembg]**: White-bg removal is clean. PROVEN with
  pure-Pillow white-threshold (no rembg) — the prefix-mandated dark outlines
  put the edge on a dark line, so minimal halo. The heavy rembg/onnxruntime
  dep is NOT required; Step 7 is satisfied by threshold removal.
- **H61 [채택]**: Embedding raster `<image>` in vector SVG renders + sanitizer
  exception is safe. PROVEN: the 310 KB mixed SVG (5 data-URI icons) validated
  with `allow_data_image=True` and rasterized to PNG ([[analyze/260601_path_d_live_e2e.py]]);
  6 sanitizer tests confirm http/external/`data:text/html`/href-less `<image>`
  are all still rejected, and `<image>` stays forbidden by default (Path A).
- **H62 [채택 — with post-process]** (resolution vs embed size): raw embed is
  578-923 KB/icon (too big). FIXED by
  [[analyze/260601_path_d_icon_postprocess_size.py]]: crop-to-bbox +
  downscale(320px) + quantize(64) → 23-84 KB/icon, ~347 KB per 6-icon figure,
  no visible degradation. The post-process is mandatory in the pipeline.

## Locked design decisions (260601 discussion)

| Decision | Choice | Rationale |
|---|---|---|
| Icon source | **All generated by Gemini; no library mixing** | Single coherent style; avoids Servier-vs-Gemini clash. |
| Icon constraints | **No text, solid white bg, high-res, clean** | Text → backbone only (sidesteps raster-text garble); white bg → clean removal; high-res → no scale blur. |
| Entity declaration | **LLM placeholder** `<rect class="gen-icon" data-desc>` | LLM marks every entity slot; post-pass fills it. |
| Background removal | **white-threshold (Pillow), NOT rembg** | Probe H60 showed threshold is clean (dark outlines minimize halo). Drops the heavy onnxruntime dep. |
| Icon size | **crop-bbox + downscale 320px + quantize 64** | Probe H62: raw 578-923 KB/icon → 23-84 KB. Mandatory post-process. |
| PPTX behavior | **warn + embed as-is** | Vector backbone still converts to shape; raster icons stay as images; user warned. |

## Analyze conclusion (2026-06-01)

Two probes, both ADOPT — see
[[analyze/260601_path_d_icon_consistency_probe.py]] (live, 6 icons, ~97s) and
[[analyze/260601_path_d_icon_postprocess_size.py]] (offline size pipeline):

- **Consistency works (H59).** The single fixed `ICON_STYLE_PREFIX` produced a
  coherent icon family across 6 independent calls. No image-to-image fallback
  needed. This was the headline risk — it cleared.
- **Cheap bg removal (H60).** Pure-Pillow white-threshold is clean; **rembg
  dropped.** The style prefix's dark-outline rule is what makes threshold work.
- **Size solved (H62).** crop+downscale+quantize → 23-84 KB/icon. The model
  emits 1408×768 with large white margins; bbox crop also fixes icon aspect.
- **Still open (implement phase):** H58 (backbone+placeholder prompt — not yet
  written) and H61 (`<image>` embed + sanitizer exception render/security).

## Plan

### Phase A — analyze (probes before any production code)

1. `analyze/260601_path_d_backbone_probe.py` — feed a Path-D-extended prompt
   (backbone rules + "every entity → `gen-icon` placeholder, no text in
   boxes") and verify the LLM produces a valid vector backbone with
   well-placed, text-free placeholders. (H58)
2. `analyze/260601_path_d_icon_consistency_probe.py` — generate the set of
   icons for ONE figure with the fixed style prompt; eyeball cross-icon
   consistency (palette / line weight / lighting). If they drift, test
   fallback (a) image-to-image conditioning. Also measure bg-removal quality
   (rembg vs threshold) and the resolution/embed-size knee. (H59, H60, H62)
3. Judgment criteria: backbone valid + placeholders sane; icons of one figure
   look like a set, not a mismatch; bg-removed icons composite cleanly on a
   non-white test rect; icon embed size acceptable at chosen resolution cap.

### Phase B — implement (only if probes ADOPT)

1. **Sanitizer exception** — `svg_validate.py`: allow `<image>` iff `href`
   matches `^data:image/(png|jpeg);base64,`; reject any other href (http /
   external stays forbidden). Regression test for allow + reject.
2. **Path D system prompt** — `app/agent/prompts/mixed_schematic.py`: Path A
   spatial/arrow/label rules **minus the catalog**, plus the `gen-icon`
   placeholder convention and "all entities are placeholders, no text inside".
3. **Icon style prompt** — `app/agent/prompts/gen_icon.py`: fixed flat /
   no-text / solid-white-bg / high-res / clean prefix with explicit palette +
   line weight (the consistency anchor for H59).
4. **icon post-process tool** — `app/tools/icon_postprocess.py` (Pillow only):
   white-threshold alpha → crop to bbox → downscale (320px cap) →
   quantize(64) → optimized PNG bytes. NO rembg. Satisfies Step 7.
5. **Path D pipeline** — `app/tools/mixed_schematic.py`: generate backbone SVG
   → extract `gen-icon` placeholders → parallel { gen icon image →
   icon_postprocess → data-uri } → replace each placeholder with `<image>`
   (preserve x/y; re-fit w/h to the post-processed icon's real aspect) →
   final sanitize. No `inject_defs` / library use.
6. **Icon cache** — content-hash (desc + style) → cached transparent PNG so
   repeated entities across/within figures don't re-call Gemini.
7. **Orchestrator** — `_dispatch_mixed`; session `kind="mixed"`. Router learns
   when to pick Path D.
8. **Export** — PPTX export warns on `kind="mixed"`; PNG/SVG-raster unaffected.

### Phase C — verify

- Integrity gates: import; sanitizer allow/reject tests; shape (placeholder
  coords preserved through replacement).
- Live test (opt-in `--run-live`): one schematic prompt whose entities are all
  outside the catalog → assert backbone is vector (`<use>`-free or
  primitive-only), every entity is an `<image>`, no text inside icons, renders
  to PNG, exports to PPTX with warning.
- Success criteria: schematic-dominant figure renders with a crisp vector
  backbone + a consistent set of text-free generated icons.

## Open risks

- **Cross-icon consistency (H59)** is the headline risk — independent Gemini
  calls drift. If the fixed prefix fails, fallback adds latency (sequential
  image-to-image) or complexity (sprite slicing).
- Placeholder coords are LLM estimates → icon aspect may mismatch the box;
  mitigated by re-fitting w/h to the generated icon's real aspect.
- High-res icons bloat the SVG (data-uri). Resolution cap (H62) is the lever.
- rembg is a heavy dep (onnxruntime + model). Drop for threshold if H60 shows
  parity.

## Execution (post-report, 2026-06-01)

Built in 6 gated steps, integrity gate (import + tests) green after each.

### Files
- `app/agent/prompts/gen_icon.py` — NEW. `ICON_STYLE_PREFIX` (the H59 consistency anchor).
- `app/agent/prompts/mixed_schematic.py` — NEW. Path D system prompt (backbone + gen-icon placeholder; no catalog) + retry_prompt.
- `app/tools/icon_postprocess.py` — NEW. Pillow threshold → bbox-crop → downscale(320) → quantize(64) → optimized PNG. No rembg.
- `app/tools/mixed_schematic.py` — NEW. Path D pipeline: backbone → extract placeholders → parallel gen+postprocess (cached) → ET in-place swap `<rect>`→`<image>` (aspect-fit) → final data-image validate.
- `app/tools/svg_validate.py` — `validate_and_canonicalize(..., allow_data_image=False)`; data-URI-only `<image>` exception (`_SAFE_DATA_IMAGE_RE`). `<image>` forbidden by default unchanged.
- `app/tools/export.py` — `svg_has_embedded_raster()`; `export_pptx_from_svg` warns on mixed.
- `app/agent/schemas.py` — `FigureKind` += `mixed`; `RoutingPath` += `D`.
- `app/agent/orchestrator.py` — `_dispatch_mixed`; `figure_kind=mixed`→D; vector mode degrades C/D→A.
- `app/agent/prompts/router.py` — Path D option (narrow guidance; primary entry is the `mixed` override since router-D accuracy is unproven).

### Tests (+24, total 258 pass / 5 live-skip)
- `tests/test_svg_validate.py` +6 (data-image allow/reject, default-forbidden, xlink, href-less).
- `tests/test_icon_postprocess.py` +6 (NEW).
- `tests/test_mixed_schematic.py` +5 (NEW: placeholder→image, no-placeholder vector, icon-failure tolerance, cache dedup, empty prompt).
- `tests/test_generate_route.py` +3 (auto→D, mixed override, vector→D degrade).
- `tests/test_export.py` +4 (raster detection + warn / no-warn).

### Analyze artifacts
- [[analyze/260601_path_d_icon_consistency_probe.py]] (live, H59/H60/H62)
- [[analyze/260601_path_d_icon_postprocess_size.py]] (offline, H62)
- [[analyze/260601_path_d_live_e2e.py]] (live e2e, H58/H61)

## Conclusion

The original motivation — fill icon coverage gaps WITHOUT dumping the whole
figure to raster — is met. Path D keeps a crisp, editable vector backbone (and
all text, sidestepping Path C's text-garble weakness) while drawing every
biological entity as a style-consistent generated icon. End-to-end live run
produced a coherent macrophage-polarization figure. No rembg needed; embed
size solved by post-process.

## Lessons

1. **The style prefix does double duty.** Mandating "clean dark outlines" for
   visual consistency (H59) also made threshold bg-removal clean (H60) — the
   edge sits on a dark line, so no white halo. One rule, two wins; rembg
   dropped entirely.
2. **The model ignores size, so reserve + refit.** The icon model emits
   1408×768 with wide margins regardless of ask. bbox-crop + downscale +
   quantize cut embed 8-28×; aspect is recovered post-hoc and the placeholder
   box is just a reservation.
3. **Path D inherits Path A's layout weakness.** Backbone coordinates are LLM
   estimates → label collisions / edge crowding persist. The icon mechanism is
   solid; the next iteration is porting Path A's vision-critic refine loop to
   Path D's backbone.

## Deferred (Path D follow-ups)
- Vision-critic layout refinement for the backbone (reuse Path A's loop).
- Router-D accuracy eval (currently conservative; primary entry is the `mixed` override).
- UI surfacing of the mixed/PPTX raster warning (currently a structlog warning only).
- `data-desc` tightening for ambiguous morphologies (M2 macrophage rendered spindle-ish).
