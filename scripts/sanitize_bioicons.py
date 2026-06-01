"""Fetch + sanitize a curated set of bioicons.com SVGs into the project library.

Run when you want to add more icons to the bundled set. Writes to
`app/domain/_bioicons_data.py`.

Pipeline:
  1. Download each picked SVG from raw.githubusercontent.com.
  2. Drop XML decl + comments, strip outer `<svg>` (keep viewBox).
  3. Strip inner `xmlns:*` declarations (they are inherited from <defs>'s parent).
  4. Namespace every internal `id="X"`, `url(#X)`, `href="#X"` to `<slug>__X`
     so multiple bundled icons cannot collide in the same `<defs>`.
  5. Optionally strip baked-in `<text>` labels + connecting arrow paths
     (useful for icons like chromosome_pair that ship with hard-coded
     "Allele 1/2/3" annotations the LLM should redraw).
  6. Wrap as `<symbol id="<slug>" viewBox="..." overflow="visible">`.

Usage:
    uv run python scripts/sanitize_bioicons.py
"""

from __future__ import annotations

import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path

BASE = "https://raw.githubusercontent.com/duerrsimon/bioicons/main/"
OUT = Path(__file__).resolve().parent.parent / "app" / "domain" / "_bioicons_data.py"

# Commercial-use guard. Only CC0 / CC BY (no ShareAlike, no NonCommercial) may
# enter the bundle: those are the licenses that permit commercial use with at
# most an attribution requirement. ShareAlike would force our figure output
# under the same license (copyleft contamination); NonCommercial forbids the
# product entirely. The bioicons repo encodes the license in the folder path
# (e.g. `static/icons/cc-by-3.0/...`), and each Pick re-declares it; both must
# agree and both must be on the allowlist.
#
# `repo_path` folder prefix -> canonical license string.
ALLOWED_LICENSES: dict[str, str] = {
    "static/icons/cc-0/": "CC0 1.0",
    "static/icons/cc-by-3.0/": "CC BY 3.0",
    "static/icons/cc-by-4.0/": "CC BY 4.0",
}


@dataclass(frozen=True)
class Pick:
    slug: str
    repo_path: str
    author: str
    license: str
    strip_baked_labels: bool = False


# Curated pilot set. Adding more here re-generates _bioicons_data.py.
# Now that lazy injection (app/tools/vector_schematic.inject_defs) ships
# only the symbols the LLM actually references, expanding this list is
# effectively free: each new icon costs 0 bytes in responses that don't
# use it.
PICKS: list[Pick] = [
    # ── Cell division (Servier line-art, CC BY 3.0) ────────────────────────
    Pick(
        slug="bioicons_mitosis",
        repo_path="static/icons/cc-by-3.0/Genetics/Servier/Mitosis.svg",
        author="Servier Medical Art",
        license="CC BY 3.0",
    ),
    Pick(
        slug="bioicons_meiosis",
        repo_path="static/icons/cc-by-3.0/Genetics/Servier/meiosis.svg",
        author="Servier Medical Art",
        license="CC BY 3.0",
    ),
    Pick(
        slug="bioicons_chromosome",
        repo_path="static/icons/cc-by-3.0/Genetics/Servier/chromosome.svg",
        author="Servier Medical Art",
        license="CC BY 3.0",
        strip_baked_labels=True,  # has hard-coded "Allele 1/2/3" annotations
    ),
    # ── Early embryo development (Xi Chen, CC-0 — no attribution required
    #    but we credit anyway). Photorealistic-leaning style, but small.
    Pick(
        slug="bioicons_zygote",
        repo_path="static/icons/cc-0/Cell_types/Xi-Chen/1cell_pn4_zygote.svg",
        author="Xi Chen",
        license="CC0 1.0",
    ),
    Pick(
        slug="bioicons_embryo_2cell",
        repo_path="static/icons/cc-0/Cell_types/Xi-Chen/2c_embryo.svg",
        author="Xi Chen",
        license="CC0 1.0",
    ),
    Pick(
        slug="bioicons_sperm",
        repo_path="static/icons/cc-0/Cell_types/Xi-Chen/sperm.svg",
        author="Xi Chen",
        license="CC0 1.0",
    ),
    Pick(
        slug="bioicons_embryo_morula",
        repo_path="static/icons/cc-0/Cell_types/Xi-Chen/morula_embryo.svg",
        author="Xi Chen",
        license="CC0 1.0",
    ),
    Pick(
        slug="bioicons_embryo_blastocyst",
        repo_path="static/icons/cc-0/Cell_types/Xi-Chen/early_blastocyst_embryo.svg",
        author="Xi Chen",
        license="CC0 1.0",
    ),
    # ── ECM / tissue (Servier line-art, CC BY 3.0) ───────────────────────
    Pick(
        slug="bioicons_collagen",
        repo_path="static/icons/cc-by-3.0/Tissues/Servier/collagen-1.svg",
        author="Servier Medical Art",
        license="CC BY 3.0",
    ),
    Pick(
        slug="bioicons_collagen_3d",
        repo_path="static/icons/cc-by-3.0/Tissues/Servier/collagen-3d.svg",
        author="Servier Medical Art",
        license="CC BY 3.0",
    ),
    Pick(
        slug="bioicons_fibroblast",
        repo_path="static/icons/cc-by-3.0/Tissues/Servier/fibroblast-1.svg",
        author="Servier Medical Art",
        license="CC BY 3.0",
    ),
    Pick(
        slug="bioicons_tight_junction",
        repo_path="static/icons/cc-by-3.0/Tissues/Servier/tight-junction.svg",
        author="Servier Medical Art",
        license="CC BY 3.0",
    ),
    Pick(
        slug="bioicons_desmosome",
        repo_path="static/icons/cc-by-3.0/Tissues/Servier/spot-desmosome.svg",
        author="Servier Medical Art",
        license="CC BY 3.0",
    ),
    # ── Cytoskeleton (Servier, CC BY 3.0) ────────────────────────────────
    Pick(
        slug="bioicons_microtubule",
        repo_path="static/icons/cc-by-3.0/Intracellular_components/Servier/microtubule.svg",
        author="Servier Medical Art",
        license="CC BY 3.0",
    ),
    Pick(
        slug="bioicons_actin_filament",
        repo_path="static/icons/cc-by-3.0/Intracellular_components/Servier/actine-filament.svg",
        author="Servier Medical Art",
        license="CC BY 3.0",
    ),
    # Gap junction (Tissues — completes cell-cell junction trio
    # alongside tight_junction + desmosome).
    Pick(
        slug="bioicons_gap_junction",
        repo_path="static/icons/cc-by-3.0/Tissues/Servier/gap-junction.svg",
        author="Servier Medical Art",
        license="CC BY 3.0",
    ),
    # Vesicle trafficking + translation (Servier).
    Pick(
        slug="bioicons_endocytosis",
        repo_path="static/icons/cc-by-3.0/Cell_membrane/Servier/endocytosis-2d.svg",
        author="Servier Medical Art",
        license="CC BY 3.0",
    ),
    Pick(
        slug="bioicons_ribosome",
        repo_path="static/icons/cc-by-3.0/Nucleic_acids/Servier/ribosome-translation.svg",
        author="Servier Medical Art",
        license="CC BY 3.0",
    ),
    # Oncology — single cancer cell + tumor mass.
    Pick(
        slug="bioicons_cancer_cell",
        repo_path="static/icons/cc-by-3.0/Oncology/Servier/cancerous-cell-1.svg",
        author="Servier Medical Art",
        license="CC BY 3.0",
    ),
    Pick(
        slug="bioicons_tumor",
        repo_path="static/icons/cc-by-3.0/Oncology/Servier/tumor.svg",
        author="Servier Medical Art",
        license="CC BY 3.0",
    ),
    # Immune system (Servier Blood_Immunology).
    Pick(
        slug="bioicons_antibody",
        repo_path="static/icons/cc-by-3.0/Blood_Immunology/Servier/antibody.svg",
        author="Servier Medical Art",
        license="CC BY 3.0",
    ),
    Pick(
        slug="bioicons_t_lymphocyte",
        repo_path="static/icons/cc-by-3.0/Blood_Immunology/Servier/t-lymphocyte.svg",
        author="Servier Medical Art",
        license="CC BY 3.0",
    ),
    Pick(
        slug="bioicons_b_lymphocyte",
        repo_path="static/icons/cc-by-3.0/Blood_Immunology/Servier/b-lymphocyte.svg",
        author="Servier Medical Art",
        license="CC BY 3.0",
    ),
    Pick(
        slug="bioicons_macrophage",
        repo_path="static/icons/cc-by-3.0/Blood_Immunology/Servier/macrophage.svg",
        author="Servier Medical Art",
        license="CC BY 3.0",
    ),
]


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def sanitize(slug: str, raw: str, *, strip_baked_labels: bool) -> tuple[str, str]:
    """Return (symbol_xml, viewBox_str)."""
    raw = re.sub(r"<\?xml[^?]+\?>", "", raw)
    raw = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)

    m_open = re.search(r"<svg\b([^>]*)>", raw, flags=re.DOTALL)
    if not m_open:
        raise ValueError(f"{slug}: no opening <svg> tag")
    attrs = m_open.group(1)
    m_vb = re.search(r'viewBox\s*=\s*"([^"]+)"', attrs)
    if not m_vb:
        raise ValueError(f"{slug}: no viewBox on outer <svg>")
    viewbox = m_vb.group(1)

    end_idx = raw.rfind("</svg>")
    body = raw[m_open.end() : end_idx]

    # 3. Strip xmlns from inner elements (inherited from parent <svg> root).
    body = re.sub(r'\s+xmlns:?\w*="[^"]*"', "", body)
    # 3b. Convert legacy `xlink:href` to the SVG2 `href` (no namespace prefix
    #     needed). Some Servier icons still use the old form and the host
    #     SVG would otherwise need to declare `xmlns:xlink`.
    body = re.sub(r"\bxlink:href\s*=", "href=", body)
    # 4. Namespace internal references so different bundled icons don't collide.
    body = re.sub(r'\bid\s*=\s*"([^"]+)"', rf'id="{slug}__\1"', body)
    body = re.sub(r"url\(#([A-Za-z_][\w-]*)\)", rf"url(#{slug}__\1)", body)
    body = re.sub(
        r'\bhref\s*=\s*"#([A-Za-z_][\w-]*)"',
        rf'href="#{slug}__\1"',
        body,
    )

    if strip_baked_labels:
        body = re.sub(r"<text\b[^>]*>.*?</text>", "", body, flags=re.DOTALL)
        # Servier annotation arrows use #0070c0 blue fill.
        body = re.sub(r'<path\b[^/]*fill="#0070c0"[^/]*/>', "", body, flags=re.DOTALL)
        # White rect "label backgrounds" emitted by Servier's annotation template.
        body = re.sub(
            r'<path\b[^/]*\bstyle="marker:none"[^/]*\btransform="translate\([^)]+\)"'
            r'[^/]*\bfill="#fff"[^/]*/>',
            "",
            body,
            flags=re.DOTALL,
        )

    sym = (
        f'<symbol id="{slug}" viewBox="{viewbox}" overflow="visible">\n'
        f"{body.strip()}\n"
        f"</symbol>"
    )
    return sym, viewbox


HEADER = '''"""Bundled third-party SVG symbols (sanitised from bioicons.com).

DO NOT EDIT BY HAND. Regenerate via scripts/sanitize_bioicons.py.

Source: https://github.com/duerrsimon/bioicons
Authors / licenses are tracked per-key in the comments below and in
[ATTRIBUTIONS.md](../../ATTRIBUTIONS.md).

Sanitisation pipeline (per icon):
  1. Drop the outer `<svg>` wrapper, keep `viewBox`.
  2. Strip `xmlns:*` declarations on inner elements (inherited from parent).
  3. Namespace all internal `id="..."`, `url(#...)` and `href="#..."` refs
     with the symbol slug so multiple bundled icons can co-exist in one
     `<defs>` block without collisions.
  4. For icons with baked-in `<text>` annotations (e.g. chromosome_pair's
     "Allele 1/2/3" labels), strip the text + the connecting arrow paths
     so the LLM controls labelling.
  5. Wrap as `<symbol id="<slug>" viewBox="..." overflow="visible">`.

The result is referenced from `bio_symbols.py` and merged into the public
`SYMBOLS` dict and `CATALOG`.
"""

'''


def validate_licenses(picks: list[Pick]) -> None:
    """Reject any Pick that isn't commercial-use-safe.

    A Pick passes only if its `repo_path` sits under an allowlisted license
    folder AND its declared `license` string matches that folder's canonical
    license. Raises ValueError on the first violation so a bad icon can never
    silently enter `_bioicons_data.py`.
    """
    for pick in picks:
        matched = next(
            (
                canonical
                for prefix, canonical in ALLOWED_LICENSES.items()
                if pick.repo_path.startswith(prefix)
            ),
            None,
        )
        if matched is None:
            raise ValueError(
                f"{pick.slug!r}: repo_path {pick.repo_path!r} is not under an "
                f"allowlisted license folder. Commercial use requires CC0 or "
                f"CC BY (3.0/4.0); ShareAlike and NonCommercial are rejected. "
                f"Allowed prefixes: {sorted(ALLOWED_LICENSES)}"
            )
        if pick.license != matched:
            raise ValueError(
                f"{pick.slug!r}: declared license {pick.license!r} disagrees "
                f"with the {matched!r} implied by repo_path {pick.repo_path!r}."
            )


def main() -> None:
    validate_licenses(PICKS)
    sanitized: dict[str, tuple[str, Pick]] = {}
    for pick in PICKS:
        raw = fetch(BASE + pick.repo_path)
        sym, vb = sanitize(
            pick.slug, raw, strip_baked_labels=pick.strip_baked_labels
        )
        sanitized[pick.slug] = (sym, pick)
        print(f"[OK] {pick.slug:25s} viewBox={vb}  size={len(sym):,}")

    with open(OUT, "w") as f:
        f.write(HEADER)
        f.write("BIOICONS: dict[str, str] = {\n")
        for slug, (sym, pick) in sanitized.items():
            f.write(
                f'    # {slug}: {Path(pick.repo_path).name} | '
                f"{pick.author} | {pick.license}\n"
            )
            f.write(f'    "{slug}": """{sym}""",\n')
        f.write("}\n")
    print(f"\nWritten: {OUT}  ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
