# 260601 — Path D: label declutter + icon size balance + model bump

> Follow-up to [[docs/progress/260601_path_d_arrow_clip_strict_critic.md]].
> Second dogfood round on the radial "Hallmarks of cancer" figure
> (`figure_8f826505.svg`). Arrows now attach at edges (clipping landed); two
> residual defects remained.

## 1. Problem (from the new figure's geometry)

1. **Arrow ↔ text overlap.** Central label `Tumor Cell` at `(800,570)` centered;
   the downward spoke `<line x1="800" y1="550" x2="800" y2="700">` runs straight
   through it. The clip pass fixed endpoints but is blind to text.
2. **Icon size imbalance.** Node boxes all `width=100` (radial uniformity OK), but
   rendered heights ranged `38.4 … 92.5` (2.4× area spread). Cause: `meet` +
   `_fit_box` fit each PNG's own aspect into equal boxes → "longest side = 100"
   but thin icons look tiny.

Also requested: bump `gemini_text_model` `gemini-2.5-flash` → `gemini-3.5-flash`.

## 2. Fixes

**A. Area-fill icon sizing** (`app/tools/mixed_schematic.py::_fit_box`). Replaced
longest-side `meet` with **area normalization**: an icon fills a fixed fraction
(`ICON_AREA_FILL=0.78`) of its box's AREA, aspect preserved, with a modest
per-dimension overflow cap (`ICON_MAX_OVERFLOW=1.18`) so flat icons aren't
slivered and extreme aspects clamp instead of blowing up. Equal boxes → equal
icon area → balanced set. Verified on the real aspects: area spread tightened
**2.4× → 1.46×** (sustained 9259→7800, metastasis 3846→5355 +39%).

**B. Deterministic label declutter** (`app/tools/label_declutter.py`, new).
Estimates each `<text>` bbox (font-size × char count × Helvetica advance), and if
it collides with a connector `<line>` (Liang–Barsky segment/rect test) or an icon
box, nudges the label off along the shortest clear axis direction (bounded
search, stays in viewBox; unmovable → left unchanged, never worsened). Runs in
`_assemble_mixed` AFTER arrow-clip so it sees final connector geometry. Verified
on the real figure: 3 labels moved, `Tumor Cell` x 800→856 clears the down-spoke.

**C. Model bump.** `app/config.py` default + `.env.example`:
`gemini-3.5-flash` for text. (Image model `gemini-3.1-flash-image-preview`
unchanged.)

## 3. Verify

- `uv run pytest` → 275 passed, 5 skipped. Import gate ✓.
- New tests: `tests/test_label_declutter.py` (7), area-fill covered by existing
  mixed assembly tests (dimension-agnostic) + the real-figure replay above.

## 4. Two-layer defense (Path D composition), now complete

```
LLM backbone → strict vision critic ×3   (sizing/symmetry/balance/overlap — LLM fixes)
            → arrow_clip                  (connector endpoints → icon edges)
            → declutter_labels            (labels off connectors/icons)
            → area-fill _fit_box          (equal-box → equal icon area)
```

## Hypotheses

- H65 (area-fill sizing balances mixed-aspect icon sets better than longest-side
  meet): 채택 — 2.4×→1.46× area spread on the real figure.
- H66 (deterministic label nudge removes arrow↔text overlap the critic/prompt
  miss): 채택 — 3/3 collisions cleared on the real figure + 7 unit tests.

## Deferred

- Bezier `<path>` connectors: neither clip nor declutter handle curved routes.
- Extreme-aspect icons still clamp below target area (metastasis). A better fix is
  upstream: steer `ICON_STYLE_PREFIX` toward square-ish framing so aspects
  converge — left for a generation-side round.
- Label nudge is axis-aligned + greedy; dense figures could still leave a residual
  overlap. Revisit with a small force-directed pass if dogfooding shows it.
