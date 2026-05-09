# 260509 — Path C probe (analyze, not build)

> Out-of-band analysis triggered by user feedback on Path A's expressiveness.
> Status: **DONE — verdict ADOPT**

## Context

After Step 2 ([[docs/progress/260509_path_a_vector_schematic.md]]) verified Path A produces clean SVG schematics, the user shared a BioRender-style tumor microenvironment figure and asked whether the system can produce that level of complexity. The honest answer was *no — not with Path A's LLM-emits-SVG approach*, because that path can't render stylized cell illustrations (M1/M2 macrophages, dendritic cells with dendrites, cancer-cluster shading, etc.) without exploding token cost or producing cartoonish output.

This experiment tests whether **Path C (Gemini Image generation, model `gemini-3.1-flash-image-preview` a.k.a. Nano Banana 2)** can one-shot a figure of comparable quality. Result reshapes the build order.

## Method

Single image generation call with a structured ~360-word prompt describing the user-provided reference figure (cell types, arrows, cytokines, labels, layout). Prompt deliberately specifies BioRender style. See [[analyze/260509_path_c_complex_figure_probe.py]] for the exact prompt.

- **Cost**: ~$0.04
- **Latency**: 27.8s
- **Output**: 400 KB PNG, saved to `/tmp/path_c_probe_latest.png`

## Result

Scored against four axes (0/1/2 each):

| Axis | Score | Notes |
|------|-------|-------|
| Cell identification | 2/2 | All 7 cell types morphologically correct and visually distinct |
| Schematic clarity | 1/2 | Activation, inhibition (⊣), dashed arrows, cytokine bubbles all present; CD8+ T cell duplicated |
| Label legibility | 2/2 | Crisp sans-serif, no garbled text, mutation badges in pill shapes; one duplicate label |
| Layout / publication-readiness | 1/2 | White background clean, no border/watermark; T cell + label duplication |
| **Total** | **6/8** | **ADOPT** threshold |

The output is qualitatively close to the user-provided reference. Defects are local (duplicate elements) and fall exactly in the wheelhouse of Step 7 (inpainting).

## Decision: re-order build queue

| Original order | New order | Reason |
|----------------|-----------|--------|
| 3. Path B (RDKit) | 3. Path C (raster) | Promoted — primary path for complex bio figures |
| 4. Export (PPTX/SVG) | 4. Inpainting / redraw region | Promoted — needed to clean Path C defects |
| 5. Path C (raster) | 5. Export (PPTX/SVG) | Was primary motivation pre-experiment; still high value |
| 6. Background removal | 6. Path B (RDKit) | Demoted — focused use case (chemistry) |
| 7. Inpainting / redraw | 7. Background removal | Demoted — Path C output is already on white |
| 8. Frontend | 8. Frontend | Unchanged |
| 9. Domain refinement (symbol library) | 9. (optional) Symbol library | Demoted — Path C alone is sufficient for v1 |

The router (Path A vs B vs C) becomes more important now that Path C is a real choice. Will land alongside Step 3 (Path C).

## Hypothesis Status

- **NEW H7 [채택]**: `gemini-3.1-flash-image-preview` produces single-shot publication-quality multi-cell illustrative figures with high enough fidelity that curated symbol-library composition is not required for v1.
  - Evidence: 6/8 score on the user's reference figure on the first attempt with no prompt engineering iteration.
  - Caveats: one sample; defect rate on broader prompt distribution unknown. Recommend a 5-prompt confirmation probe before full commit if early Path C results disappoint.

- **NEW H8 [검증중]**: Inpainting (mask + reprompt) can reliably remove duplicate elements like the rendered T cell.
  - Will be tested in Step 4 (now inpainting/redraw).

## Artifacts

- Probe script: [[analyze/260509_path_c_complex_figure_probe.py]]
- Generated PNG: `/tmp/path_c_probe_latest.png` (also `/tmp/path_c_probe_<timestamp>.png`)
- Metadata sidecar: `/tmp/path_c_probe_<timestamp>.json`

## Lessons

- Image-gen text rendering is no longer the bottleneck it was a year ago. Nano Banana 2 produces clean, scientifically accurate labels including superscripts and pill-shaped badges without prompt-engineering tricks.
- Defects are *patterned* (duplicate elements) rather than *systemic* (bad anatomy). This makes them addressable with localized edits — exactly what step 4 (inpainting) is for.
- Cost economics favor Path C for complex figures: $0.04 / 28s vs. dozens of LLM-SVG iteration attempts to get a comparable result.

**Next step**: re-confirm new build order with user, then proceed with Step 3 (Path C raster).
