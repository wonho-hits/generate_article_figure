# Progress log index

> Per-step development logs in chronological order. Each step followed the pre-report → implement → verify → post-report cycle from `~/.claude/CLAUDE.md`.

## Steps

| # | Date | Step | Outcome |
|---|------|------|---------|
| 1 | 260509 | [Backend skeleton](260509_backend_skeleton.md) | FastAPI + session store + Gemini client wrapper |
| 2 | 260509 | [Path A — text → SVG](260509_path_a_vector_schematic.md) | LLM emits SVG with `<g id="...">` groups; XML-validate + sanitize |
| — | 260509 | [Path C probe (analyze)](260509_path_c_probe.md) | Verdict ADOPT; reorders build queue (Path C → primary, inpaint → step 4) |
| 3 | 260509 | [Path C raster + Router](260509_path_c_raster_and_router.md) | Gemini Image generation; LLM router A/C with 8-prompt live eval (8/8 correct) |
| 4 | 260509 | [Inpaint / region redraw](260509_inpaint_region.md) | Conversational reprompt + mask-based edit; live test elevates probe artifact 6/8 → 8/8 |
| 5 | 260509 | [Export pipeline](260509_export_pipeline.md) | SVG / PPTX (L1 picture) / image downloads. **Addendum**: L2 PPTX with SVG embedded as `asvg:svgBlip` for Convert-to-Shape editability |
| 8 | 260509 | [Gradio MVP](260509_gradio_mvp.md) | UI mounted at `/ui`; user dogfooding identified Path A quality gap |
| 9 | 260509 | [Bio symbol library](260509_bio_symbol_library.md) | 23 hand-written SVG symbols + system-prompt catalog. Resolves all 5 step-8 failure modes |
| 6 | 260509 | [Path B — RDKit](260509_path_b_rdkit.md) | Chemistry extraction + RDKit + PubChemPy fallback; router extends to A/B/C (11/11 live) |

Steps 1, 2, 3, 4, 5, 8, 9, 6 in actual execution order — the build order was reordered after the Path C probe (probe scored Path C 6/8 ADOPT, promoting it ahead of Path B and pulling inpainting forward as the fixer for Path C defects). Step 8 (Gradio) was promoted ahead of Path B because dogfooding had higher signal value than another generation path. Step 9 (symbol library) was demoted to optional after the Path C probe but re-promoted after Step 8 dogfooding revealed Path A quality issues.

Step 7 (background removal) deferred — Path C output is already on white in practice.

## Key hypotheses (final status)

| ID | Statement | Status |
|----|-----------|--------|
| H1 | Single orchestrator + typed tools is sufficient | 채택 |
| H2 | In-memory session store sufficient for v1 | 채택 |
| H3 | Python 3.12 pin (not 3.14) | 채택 |
| H4 | Gemini 2.5 Flash emits valid SVG with conventions | 채택 |
| H5 | Free-form SVG > structured shape schema | 채택 |
| H6 | XML-parse + structural assertions is enough validation | 채택 |
| H7 | Path C single-shot quality sufficient for v1 | 채택 |
| H8 | Conversational reprompt fixes duplicate elements | 채택 |
| H9 | LLM router ≥ 90% on eval | 채택 (100% on 11 prompts) |
| H10 | Style prefix in prompt > system_instruction for image models | 채택 |
| H11 | Style-preserving instruction prefix preserves unedited regions | 채택 |
| H12 | `isinstance(bytes)` gate is enough for raster-session edit | 채택 |
| H13 | Format-per-session-kind PPTX UX is acceptable | 채택 |
| H14 | Single-picture PPTX sufficient for v1 (raster path) | 채택 |
| H15 | PowerPoint Convert-to-Shape works on Path A SVG vocabulary | 채택 |
| H16 | Gradio sufficient to validate full backend loop | 채택 |
| H17 | Mounting Gradio at `/ui` with direct orchestrator calls | 채택 |
| H18 | Real human use surfaces ≥ 1 priority shift | 채택 — prompted Step 9 |
| H19 | ~20 hand-written symbols suffice for pathway schematics | 채택 |
| H20 | Hand-write faster than SciDraw web fetch | 채택 |
| H21 | Catalog in system prompt + spatial rules → LLM composes with `<use>` | 채택 |
| H22 | LLM extraction + RDKit pipeline produces correct chemistry | 채택 |
| H23 | PubChemPy fallback covers compounds the LLM doesn't know SMILES for | 채택 (mocks; not exercised live yet) |
| H24 | Router extends to A/B/C via prompt-only changes | 채택 |

No hypotheses 기각 to date.

## Cumulative live API cost during development

~$0.13 across all `--run-live` test runs and probe scripts.

## Pivots / discoveries that changed the plan

1. **Step 0 probe verdict**: Path C produces BioRender-quality figures one-shot. This restructured the build queue (Path C promoted, symbol library demoted, inpainting promoted to fix Path C defects).
2. **Two SDK gotchas surfaced in step 3**: `google-genai` 1.x doesn't auto-populate `response.parsed`; `gemini-3.1-flash-image-preview` returns JPEG, not PNG. Both required code changes that affected later steps.
3. **OOXML prefix sensitivity (step 5 addendum)**: PowerPoint silently ignores `<asvg:svgBlip>` if the prefix isn't literally `asvg:`. lxml auto-generates `ns0:` and breaks it. Pass `nsmap` explicitly to force the prefix.
4. **Step 8 dogfooding revealed Path A quality gap**: prompted Step 9 symbol library (re-promoted from "deferred").
5. **Step 9 iter 1 → iter 2**: hand-written symbols alone weren't sufficient — needed explicit "extracellular = top, cytoplasm = bottom" spatial rules in the prompt to fix membrane orientation.
