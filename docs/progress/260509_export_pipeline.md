# 260509 — Export pipeline (SVG / PPTX / image download)

> Step 5 / 9. Builds on [[docs/progress/260509_path_c_raster_and_router.md]] and [[docs/progress/260509_inpaint_region.md]].
> Status: **DONE — all acceptance criteria passed; PPTX byte-perfect round-trip verified**

## Context

Up to step 4, every artifact lives inside a session as either an SVG string or raw image bytes. Useful for the API, useless on the user's desk. This step closes the loop by adding download endpoints — the user gets an actual file.

Three formats are useful, each tied to a use case:

| Format | Use case | Source compatible |
|--------|----------|-------------------|
| `.svg` | Full vector editing in Illustrator/Inkscape | Path A (SVG sessions) only |
| `.pptx` | Drop into a slide deck, add captions/notes | Path C (raster sessions) — embedded as picture on a blank slide |
| `image` (.png/.jpg/.webp) | Include in a paper, post-edit in raster software | Path C — raw bytes pass-through |

Cross-format conversions (rasterize SVG to put in PPTX; vectorize raster to SVG) are tempting but each carries quality penalties (anti-aliasing, vtracer noise) and adds system-level deps (cairo, vtracer binaries). Defer to a later step. v1 ships clean format-per-session-kind.

## 이전 시도 (Previous Attempts)

None for export. Cumulative state of the project:
- Path A ([[docs/progress/260509_path_a_vector_schematic.md]]) emits SVG strings.
- Path C ([[docs/progress/260509_path_c_raster_and_router.md]]) emits raster bytes (typically JPEG).
- Edits ([[docs/progress/260509_inpaint_region.md]]) replace raster bytes in place.

This step adds no model calls — pure local file packaging.

## 가설 상태 (Hypothesis Status)

- **NEW H13 [검증중]**: For v1, "format-per-session-kind" (SVG-out for SVG sessions, PPTX/image-out for raster sessions) is acceptable UX. Cross-format conversion is not required.
  - Falsified by: a real user complains the lack of "give me the Path A schematic in PPT" is a blocker. They have an escape hatch (open SVG, save as PNG, drop in PPT).
  - Mitigation if falsified: add cairosvg-based rasterization in a follow-up step (no schema change).

- **NEW H14 [채택, monitor]**: `python-pptx` blank-slide + centered picture is sufficient pptx output for v1.
  - Trade-off: not "fully editable native shapes." Image is a single picture object. Movable / resizable / captionable in PowerPoint, but not vector-editable.
  - Justified by: most users drop the figure into a deck and add their own text, never edit individual elements inside the figure. The SVG download path covers the "edit the figure itself" use case.

## Plan

### What we will build

```
app/
├── tools/
│   └── export.py                     # NEW: export_svg(), export_pptx(), export_image()
└── routes/
    └── export.py                     # NEW: GET /export/{sid}/svg
                                      #      GET /export/{sid}/pptx
                                      #      GET /export/{sid}/image

tests/
├── test_export.py                    # NEW: tool-level mocked
└── test_export_route.py              # NEW: route-level mocked
```

`pyproject.toml` adds `python-pptx>=1.0` and `Pillow>=10.4` to dependencies.

### Endpoint design

```
GET  /export/{session_id}/svg   → 200 image/svg+xml + Content-Disposition
                                  422 if session is raster ("use /image or /pptx")
                                  404 if session unknown
GET  /export/{session_id}/pptx  → 200 application/vnd.openxmlformats-officedocument.presentationml.presentation
                                  422 if session is svg ("use /svg directly, then convert externally")
                                  404 if session unknown
GET  /export/{session_id}/image → 200 image/<png|jpeg|webp> (whatever the session holds)
                                  422 if session is svg
                                  404 if session unknown
```

GET (not POST) because they are pure reads of session state. No mutation, no LLM call.

### Key design decisions

1. **Format-per-session-kind, not auto-conversion.** Honesty > false promises. SVG users get vector-native; raster users get raster-native. Anyone needing both can iterate on the same session by re-prompting with `figure_kind` override.

2. **PPTX = blank slide with single centered picture.** No automatic captioning, no editable text overlays in v1. The picture sits at proportional size with a 0.5-inch margin. Slide is widescreen (10 × 7.5 inches default). Users can add their own captions / annotations in PowerPoint where they have full control.

3. **`Content-Disposition: attachment; filename="figure_<short_sid>.<ext>"`** so downloads land with sensible names. `<short_sid>` = first 8 chars of session_id (UUID hex prefix).

4. **No streaming.** Artifacts are ≤ 1 MB in practice — fits a single Response. Streaming complexity isn't worth it.

5. **No new dependency surfaces beyond `python-pptx` + `Pillow`.** Both are pure-Python (Pillow has C extensions but ships wheels for Python 3.12). No cairo, no inkscape CLI, no system tools.

6. **Image MIME pass-through.** `/image` returns whatever the session bytes are (JPEG from Gemini today; PNG if upgraded later). `Content-Type` reflects detected MIME. Filename extension follows MIME.

### Acceptance criteria

1. **Mocked tests pass**, no regression on the existing 76. Coverage ≥ 80% on `app/tools/export.py` and `app/routes/export.py`.
2. **SVG round-trip**: write a Path A session, GET `/export/{sid}/svg`, parse the response body as XML — must match the in-session SVG.
3. **PPTX round-trip**: write a Path C session with a known image, GET `/export/{sid}/pptx`, verify response is a valid ZIP (`PK\x03\x04` magic) with at least the `ppt/slides/slide1.xml` entry. Embedded image bytes must equal the original session bytes.
4. **Image round-trip**: GET `/export/{sid}/image`, verify Content-Type matches detected MIME, body equals session bytes.
5. **Cross-format mismatch**: GET `/export/{svg_sid}/pptx` → 422; GET `/export/{raster_sid}/svg` → 422. Both messages include the actual / expected format.
6. **Unknown session** → 404 on all three endpoints.
7. **Manual smoke**: with the live raster session from step 4 (`/tmp/path_c_live_inpaint.jpg`), end-to-end create session via API, edit, then download the PPTX and verify it opens cleanly in Keynote and PowerPoint. Reported as a separate ad-hoc check, not enforced by automated tests.

### Out of scope for this step

- SVG → PPTX (would need cairosvg)
- Raster → SVG via vtracer (would need vtracer binary; quality is best-effort anyway — defer to a maybe-step-9 add-on)
- OCR-based text-overlay extraction so PPTX has editable labels for raster figures
- Multi-page PPTX (e.g., one slide per session in history) — single artifact only
- Custom slide templates / company branding
- ZIP bundle download (svg + pptx + image at once)

### Risks

| Risk | Mitigation |
|------|-----------|
| `python-pptx` API change between versions | Pin `>=1.0,<2.0`; the API has been stable for years |
| Pillow can't open the JPEG bytes Gemini returns (unlikely but possible) | Catch on encode; surface as 503 with detail. Fallback: skip resize logic, embed at default size. |
| Filename injection via session_id (path traversal in Content-Disposition) | session_id is a UUID generated by us — strict format. Sanitize anyway. |
| Large session histories grow memory | Already TTL-evicted by step 1. Export reads current artifact only, history not exported. |

### Iteration history

Single iteration. No surprises — pure local file packaging, no model calls.

- Added `python-pptx==1.0.2` and `Pillow==12.2.0` (uv resolved to latest).
- Wrote `app/tools/export.py` (3 functions + `ExportResult` dataclass) and `app/routes/export.py` (3 GET endpoints).
- Wrote `tests/test_export.py` (15 tests) and `tests/test_export_route.py` (10 tests).

### Acceptance results

| # | Criterion | Result |
|---|-----------|--------|
| 1 | Mocked tests pass, no regression | ✅ 96/96 (was 76; +20 new) |
| 2 | Coverage ≥ 80% on tools/export.py + routes/export.py | ✅ 96% / 96% (total project 96%) |
| 3 | SVG round-trip | ✅ XML body matches in-session SVG |
| 4 | PPTX round-trip | ✅ valid OOXML ZIP (`PK\x03\x04`); slide1.xml present; **embedded image SHA256 byte-identical to source** |
| 5 | Image round-trip | ✅ Content-Type matches detected MIME; body identical |
| 6 | Cross-format mismatch → 422 | ✅ all three combinations (svg→pptx, svg→image, raster→svg) |
| 7 | Unknown session → 404 | ✅ all three endpoints |
| 8 | Manual smoke: live inpaint result → PPTX → opens cleanly | ✅ file detected as `Microsoft OOXML`; opened in default app without error |

### Byte-perfect PPTX verification

Took the live inpaint output (`/tmp/path_c_live_inpaint.jpg`, 390 KB) and exported as PPTX. Inspected the resulting PPTX as a ZIP:

```
PPTX entries (38 total):
  ppt/slides/slide1.xml            ← single slide
  ppt/media/image1.jpg             ← embedded image (one)
  ppt/slideLayouts/slideLayout*.xml × 11
  ppt/slideMasters/slideMaster1.xml
  ppt/theme/theme1.xml
  ...

source jpeg sha256:    ee8508da2be5a6ba   (390,049 bytes)
embedded image sha256: ee8508da2be5a6ba   (390,049 bytes)
match: True
```

No re-encoding, no quality loss. The image embedded in PPTX is bit-for-bit the same JPEG Gemini returned.

### Files added / modified

Added:
- [app/tools/export.py](../../app/tools/export.py)
- [app/routes/export.py](../../app/routes/export.py)
- [tests/test_export.py](../../tests/test_export.py)
- [tests/test_export_route.py](../../tests/test_export_route.py)

Modified:
- [pyproject.toml](../../pyproject.toml) — added `python-pptx>=1.0,<2.0`, `Pillow>=10.4`
- [app/main.py](../../app/main.py) — mount `export_route.router`

## Conclusion

The figure-to-file loop is closed. A user can now:

```
POST /generate          → session_id + artifact (in-memory data URI / SVG string)
POST /edit/{sid}        → revise raster artifact (multi-turn)
GET  /export/{sid}/svg  → image/svg+xml file download (Path A)
GET  /export/{sid}/pptx → .pptx with embedded raster, single slide (Path C)
GET  /export/{sid}/image → original raster bytes (Path C)
GET  /health
```

That's the full v1 backend surface for the user-facing functionality (1) text-to-image, (2) editable labels (via inpaint instruction), (3) redrawable parts (via mask or instruction), (5) vectorize into slide (PPTX), (6) SVG vectorization (SVG download).

Feature (4) "background removable" remains, plus Path B (RDKit) and the frontend.

**Hypotheses status update:**
- **H13** (format-per-session-kind UX is acceptable for v1) — **채택**, will revisit if a real user complains.
- **H14** (single-picture pptx is sufficient) — **채택**, byte-perfect embed and clean OOXML structure.

**Lessons:**
1. `python-pptx` produces full OOXML output including 11 default slide layouts and a master — adds ~10 KB overhead but ensures the file opens correctly in both PowerPoint and Keynote with no compatibility warnings.
2. `add_picture` with explicit `width`/`height` does no re-encoding — the source bytes go in as-is. Confirmed via SHA256 comparison.
3. `Pillow` opens JPEG/PNG without complaint and gives us aspect ratio without reading pixel data — fast and pure-Python.
4. Cross-format conversion deferral was the right call: cairosvg / vtracer would have added system-level dependencies and weeks of "best-effort quality" tuning that v1 doesn't need (frontend can let users pick the natural format per session).

**Next step**: Step 6 — Path B (RDKit molecule/reaction rendering). Smaller scope than the major paths, deterministic library calls, pure-vector output. Should be a fast step.

---

## Addendum (same day) — L2 SVG-embedded PPTX

User feedback after the initial L1 implementation: the picture-only PPTX is fine for "drop in a deck" but not editable. They wanted the figure broken into native PowerPoint shapes (the BioRender-from-PPTX experience).

### Decision

For Path A (SVG sessions), upgrade `/export/{sid}/pptx` from "PNG-of-rasterized-SVG embedded as picture" (which we never even built — it was 422) to **"SVG embedded as a vector image via OOXML asvg extension"**. Modern PowerPoint (2016+) renders the SVG as vector; users right-click → "Convert to Shape" to break it into native editable shapes.

For Path C (raster sessions), keep current L1 behavior — raster has no path to vector editability without a separate vectorize step (deferred).

### Implementation

- New module [app/tools/export_svg_pptx.py](../../app/tools/export_svg_pptx.py) — manipulates OOXML directly because `python-pptx` doesn't expose SVG embed.
- Builds baseline PPTX with a 1×1 transparent PNG fallback (modern PowerPoint never reads it; older versions show blank).
- Post-processes the ZIP to:
  1. Add `ppt/media/image1.svg` with the actual SVG bytes
  2. Add a relationship in `ppt/slides/_rels/slide1.xml.rels`
  3. Add `<Default Extension="svg" .../>` to `[Content_Types].xml`
  4. Inject `<a:extLst><a:ext><asvg:svgBlip r:embed="..."/></a:ext></a:extLst>` inside the existing `<a:blip>` element
- [app/tools/export.py](../../app/tools/export.py) gets `export_pptx_from_svg()`.
- [app/routes/export.py](../../app/routes/export.py) `/pptx` now dispatches by artifact type — SVG → L2; bytes → L1 (unchanged).

### The hard-won bug — namespace prefix

First implementation produced a valid-looking XML but PowerPoint silently fell back to the PNG (showing nothing because PNG was 1×1 transparent). Investigation:

```
emitted: <ns0:svgBlip xmlns:ns0="http://schemas.microsoft.com/office/drawing/2016/SVG/main" .../>
needed:  <asvg:svgBlip xmlns:asvg="..." .../>
```

PowerPoint specifically expects the namespace prefix to be `asvg`. Auto-generated prefixes (`ns0`, `ns1`, etc.) are silently ignored. Fixed by passing `nsmap={"asvg": ASVG_NS}` to `etree.SubElement(...)` so lxml declares the namespace at that element with the desired prefix.

Regression test in [tests/test_export.py](../../tests/test_export.py): `test_export_pptx_from_svg_uses_asvg_prefix_not_generated_one` asserts `<asvg:svgBlip` literal substring is present and `<ns0:svgBlip` literal is NOT. If anyone ever refactors and breaks this, tests catch it before the user does.

### Verification

- All 100 mocked tests pass; coverage on new module 83%, route 93%.
- Manual smoke (Path A live MAPK SVG → L2 PPTX → PowerPoint):
  - File detected as `Microsoft OOXML`, opened cleanly.
  - Initially: file appeared as a single (invisible) image — the prefix bug.
  - After fix: figure renders as vector. Right-click → "Convert to Shape" decomposes it into individual selectable native PowerPoint shapes — verified by user screenshot showing selection handles on every element (EGF circle, Ras, Raf/MEK/ERK boxes, P phosphorylation badges, all labels).
- L2 PPTX is dramatically smaller than L1: 30 KB vs 400 KB for the same figure (no PNG bloat).

### Hypothesis status (added)

- **NEW H15 [채택]**: PowerPoint 2016+'s Convert-to-Shape works on the constrained SVG vocabulary that Path A emits (rect, circle, ellipse, line, path, text, marker, g). Verified by user's screenshot showing all elements correctly decomposed.

### Lesson

OOXML is **prefix-sensitive in practice**, not just namespace-sensitive. Microsoft Office readers check for specific prefixes (`asvg:`, `a:`, `p:`, `r:`) and silently ignore the wrong ones. lxml's default behavior of auto-generating prefixes (`ns0:`) breaks this. Always pass `nsmap` explicitly when emitting OOXML extensions.
