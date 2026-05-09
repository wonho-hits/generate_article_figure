"""Style prefix for Path C (raster illustration via Gemini Image).

Inserted at the front of the user's prompt because image models do not
reliably honor system_instruction. Prefix carries the BioRender-style
conventions verified by the probe in
[[analyze/260509_path_c_complex_figure_probe.py]].
"""

from __future__ import annotations

STYLE_PREFIX = """Create a publication-quality scientific figure in the BioRender illustration style.

Visual conventions:
- Clean white background, no decorative borders, no watermarks.
- Soft pastel cell colors with subtle shading; cells morphologically distinct (e.g., kidney-shaped nucleus for monocyte, dendrites for dendritic cells, spindle for fibroblasts).
- Crisp black labels in clean sans-serif. Mutation markers and gene names may sit in pill-shaped badges.
- Crisp black arrows: solid arrowhead = activation; perpendicular bar (⊣) = inhibition; dashed = derivation/transition.
- Cytokines and small molecules drawn as small filled circles near their labels.
- Balanced layout, no element clipped, no duplicate entities.

User request:
"""
