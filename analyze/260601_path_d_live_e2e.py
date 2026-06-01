"""
Analysis: Path D end-to-end live probe (H58 backbone+placeholder, H61 render).
Date: 2026-06-01
Related progress log: docs/progress/260601_path_d_mixed_vector_raster.md

Problem:
    Unit tests cover the Path D pipeline with mocked Gemini. Two hypotheses can
    only be checked live:
    H58 — does the Path D system prompt make the LLM emit a clean vector
        backbone with <rect class="gen-icon" data-desc> placeholders (one per
        entity, text-free boxes), rather than drawing cells from primitives or
        putting text inside icon boxes?
    H61 — does the assembled mixed SVG (vector backbone + base64 <image> icons)
        render correctly, and does the final data-image sanitizer pass?

    This runs generate_mixed_figure on a real prompt, reports placeholder /
    fill counts, then rasterizes the result to a PNG for eyeball review.

Judgment Criteria:
    - backbone has ≥1 gen-icon placeholder, all with non-empty data-desc, none
      containing text → H58 supported.
    - every placeholder filled with an <image> (or failures logged), final SVG
      validates with allow_data_image=True, rasterizes without error → H61.
    - eyeball PNG: vector arrows/labels crisp, icons present and on-style.

Conclusion (2026-06-01, macrophage-polarization prompt, 35.5s):
    H58 SUPPORTED. The Path D prompt produced a clean vector backbone with 5
    gen-icon placeholders (one per entity), 11 vector <text> labels, 0 text
    inside icon boxes. All 5 placeholders filled; 0 leftover. The LLM did NOT
    draw cells from primitives — it correctly reserved boxes.
    H61 SUPPORTED. Final mixed SVG (310 KB, 5 embedded data-URI icons)
    validated with allow_data_image=True and rasterized to PNG (qlmanage
    fallback; cairosvg lib absent on this host). Icons render on-style and
    consistent (matches the consistency probe).

    Known defect (NOT a Path D-specific bug): LAYOUT. Label collisions
    ("Monocyte" over arrows; cramped bottom-right cluster) and right-edge
    crowding — the same LLM-estimates-coordinates weakness Path A has
    (CLAUDE.md deferred: "Path A label-position auto-correction"). The icon
    mechanism and assembly are solid; layout polish is follow-up work, e.g.
    porting Path A's vision-critic refine loop to Path D.

    OVERALL: Path D is functional end-to-end. Core hypotheses proven. Ship as
    an experimental path; layout-critic refinement is the next iteration.

Usage:
    uv run python analyze/260601_path_d_live_e2e.py
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=True)

from app.clients.gemini import GeminiClient  # noqa: E402
from app.tools.mixed_schematic import generate_mixed_figure  # noqa: E402
from app.tools.svg_render import rasterize_svg  # noqa: E402

PROMPT = (
    "Schematic of macrophage polarization in the tumor microenvironment. "
    "A monocyte differentiates (dashed arrows) into an M1 macrophage and an "
    "M2 macrophage. The M2 macrophage promotes (solid arrow) a cluster of "
    "cancer cells. A CD8+ T cell is inhibited (bar-ended line) by the cancer "
    "cluster. Label every cell and every arrow. Extracellular at top."
)


async def main() -> None:
    print("=" * 70)
    print("[e2e] Path D live end-to-end")
    print("=" * 70)
    client = GeminiClient()

    def progress(msg: str, frac: float) -> None:
        print(f"[e2e] {frac*100:5.1f}%  {msg}")

    t0 = time.time()
    svg = await generate_mixed_figure(PROMPT, client=client, progress=progress)
    elapsed = time.time() - t0

    n_images = svg.count("data:image/")
    n_text = svg.count("<text")
    print("-" * 70)
    print(f"[e2e] elapsed:        {elapsed:.1f}s")
    print(f"[e2e] final SVG size: {len(svg)//1024} KB")
    print(f"[e2e] embedded icons: {n_images}")
    print(f"[e2e] vector labels:  {n_text}")
    print(f"[e2e] gen-icon leftover (unfilled): {svg.count('gen-icon')}")

    out_dir = Path("/tmp/path_d_probe")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    (out_dir / f"e2e_{ts}.svg").write_text(svg)
    try:
        png = rasterize_svg(svg, width=1600)
        (out_dir / f"e2e_{ts}.png").write_bytes(png)
        (out_dir / "e2e_latest.png").write_bytes(png)
        print(f"[e2e] rasterized OK:  {len(png)//1024} KB → {out_dir}/e2e_latest.png")
    except Exception as exc:  # noqa: BLE001
        print(f"[e2e] RASTERIZE FAILED: {type(exc).__name__}: {exc}")
        raise

    print()
    print("JUDGE: open e2e_latest.png — crisp vector arrows/labels + on-style "
          "icons? gen-icon leftover should be 0.")


if __name__ == "__main__":
    asyncio.run(main())
