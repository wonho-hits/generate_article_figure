"""
Analysis: Path D icon post-process size pipeline (H62 confirmation).
Date: 2026-06-01
Related progress log: docs/progress/260601_path_d_mixed_vector_raster.md

Problem:
    The consistency probe (260601_path_d_icon_consistency_probe.py) showed
    H62 FAIL: each generated icon embeds as a 578-923 KB base64 data-uri
    (6 icons ≈ 4 MB of SVG). Three causes: (1) model outputs 1408x768 with
    most of the frame as white margin (no bbox crop), (2) lossless PNG of a
    shaded illustration is large, (3) no downscale/quantize.

    Question: does a crop-to-alpha-bbox → downscale-to-cap → quantize pipeline
    bring per-icon embed size under the ~200 KB flag (target ideally < 60 KB)
    WITHOUT visibly degrading the icon? Runs offline on the saved probe icons
    — no live API.

Judgment Criteria:
    - Per-icon data-uri after pipeline < 200 KB → ACCEPTABLE; < 60 KB → GOOD.
    - Visual: quantized/downscaled icon still clean on the contact sheet
      (no banding, no jagged edges at display size).
    Decision: confirms the implement-phase post-process for Path D icons.

Conclusion (2026-06-01, offline on the 6 saved probe icons):
    ACCEPTABLE. crop-to-alpha-bbox + downscale(320px long edge) +
    quantize(64 colors) + optimized PNG:
        monocyte 47KB, m1_macrophage 77KB, dendritic 84KB, cd8_tcell 47KB,
        cancer_cluster 69KB, fibroblast 23KB.
    Worst icon 84KB (was 736KB) — 8-28x reduction. 6-icon figure total
    ~347 KB. No visible degradation at display size (no banding, edges crisp
    on gray). bbox crop also fixes aspect (fibroblast 320x84, tight).
    To reach GOOD (<60KB) drop cap to 256 or colors to 48 — not necessary.
    Pipeline confirmed for the Path D implement phase.

Usage:
    uv run python analyze/260601_path_d_icon_postprocess_size.py
"""

from __future__ import annotations

import base64
import json
import sys
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

IN_DIR = Path("/tmp/path_d_probe")
DISPLAY_CAP = 320  # px on the long edge — ~2x a typical icon box in a figure
QUANTIZE_COLORS = 64  # flat pastel art quantizes well; 64 is generous

SLUGS = [
    "monocyte", "m1_macrophage", "dendritic_cell",
    "cd8_tcell", "cancer_cluster", "fibroblast",
]


def data_uri_len(png_bytes: bytes) -> int:
    return len(base64.b64encode(png_bytes))


def postprocess(rgba: Image.Image) -> tuple[Image.Image, bytes]:
    """crop to alpha bbox → downscale to cap → quantize → optimized PNG."""
    bbox = rgba.getbbox()  # bbox of non-zero (alpha included) region
    cropped = rgba.crop(bbox) if bbox else rgba
    cropped.thumbnail((DISPLAY_CAP, DISPLAY_CAP), Image.LANCZOS)
    # Quantize RGB but preserve alpha: split, quantize color, recombine.
    alpha = cropped.getchannel("A")
    rgb = cropped.convert("RGB").quantize(
        colors=QUANTIZE_COLORS, method=Image.FASTOCTREE
    ).convert("RGB")
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    buf = BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return out, buf.getvalue()


def main() -> None:
    print("=" * 70)
    print("[size] Path D icon post-process — crop+downscale+quantize")
    print(f"[size] cap={DISPLAY_CAP}px colors={QUANTIZE_COLORS}")
    print("=" * 70)

    thumbs: list[Image.Image] = []
    recs: list[dict] = []
    for slug in SLUGS:
        cut = IN_DIR / f"{slug}_cut.png"
        if not cut.exists():
            print(f"[size] {slug}: missing {cut} — run the consistency probe first")
            continue
        rgba = Image.open(cut).convert("RGBA")
        before = data_uri_len(cut.read_bytes())
        out, png = postprocess(rgba)
        after = data_uri_len(png)
        (IN_DIR / f"{slug}_final.png").write_bytes(png)

        thumb = Image.new("RGB", (DISPLAY_CAP, DISPLAY_CAP), (150, 150, 150))
        comp = Image.new("RGBA", out.size, (150, 150, 150, 255))
        comp.alpha_composite(out)
        comp = comp.convert("RGB")
        thumb.paste(comp, ((DISPLAY_CAP - out.width) // 2, (DISPLAY_CAP - out.height) // 2))
        thumbs.append(thumb)

        recs.append({
            "slug": slug, "out_dims": out.size,
            "uri_before_kb": before // 1024, "uri_after_kb": after // 1024,
            "reduction_x": round(before / after, 1),
        })
        print(
            f"[size] {slug:16s} {out.size[0]}x{out.size[1]:<4d} "
            f"uri {before//1024:4d}KB → {after//1024:3d}KB "
            f"({before/after:.1f}x smaller)"
        )

    if thumbs:
        pad = 12
        w = len(thumbs) * DISPLAY_CAP + (len(thumbs) + 1) * pad
        sheet = Image.new("RGB", (w, DISPLAY_CAP + 2 * pad), (255, 255, 255))
        for i, t in enumerate(thumbs):
            sheet.paste(t, (pad + i * (DISPLAY_CAP + pad), pad))
        sheet.save(IN_DIR / "final_contact_sheet.png")
        print("-" * 70)
        print(f"[size] final sheet (on gray): {IN_DIR / 'final_contact_sheet.png'}")

    (IN_DIR / "size_report.json").write_text(json.dumps(recs, indent=2))
    if recs:
        worst = max(r["uri_after_kb"] for r in recs)
        total = sum(r["uri_after_kb"] for r in recs)
        print(f"[size] worst icon: {worst}KB   6-icon SVG total: ~{total}KB")
        print(f"[size] verdict: {'GOOD' if worst < 60 else 'ACCEPTABLE' if worst < 200 else 'STILL TOO BIG'}")


if __name__ == "__main__":
    main()
