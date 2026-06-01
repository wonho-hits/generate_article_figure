"""Style prefix for Path D generated icons (single-entity raster icons).

Path D draws every biological entity as an independently generated Gemini
raster icon, embedded into a vector backbone. Because each icon is a SEPARATE
image call, the central risk (H59 in
[[docs/progress/260601_path_d_mixed_vector_raster.md]]) is that icons in the
same figure drift in palette / line weight / lighting and look mismatched.

This prefix is the consistency anchor: it pins the *general* BioRender /
bioicons (Servier Medical Art) aesthetic precisely enough that independent
calls converge on one look, while staying general enough to render any entity.

Hard constraints baked in for the downstream pipeline:
- NO text/letters anywhere — all labels live in the vector backbone, so the
  icon never carries garble-prone raster text (Path C's weakness).
- Pure solid white background — required for clean background removal
  (rembg / threshold) into a transparent PNG.
- Single isolated subject, high resolution, no cast shadow on the background.

Inserted at the front of the entity description, same pattern as Path C's
`STYLE_PREFIX`: composed = f"{ICON_STYLE_PREFIX}{entity_description}".
"""

from __future__ import annotations

ICON_STYLE_PREFIX = """Draw a single scientific illustration ICON in the clean, flat BioRender / Servier Medical Art style. This is one isolated icon for a scientific schematic, not a full scene.

STYLE (keep this identical across icons so a set of them looks like one consistent family):
- Flat 2D vector-style illustration. Not photorealistic, not a 3D render, no realistic lighting or reflections.
- Clean, uniform dark outlines of consistent medium weight around every shape (think a steady ~2px ink line, never sketchy or hand-drawn).
- Soft, muted pastel fills with gentle flat two-tone shading for volume (one base tone + one slightly darker tone). No glossy highlights, no photographic gradients, no neon or saturated colors.
- Simplified, schematic anatomy: recognizable and biologically faithful but stylized and uncluttered. Show only the defining features of the subject.
- Calm, professional scientific palette (soft blues, greens, pinks, purples, warm neutrals).

COMPOSITION:
- Exactly ONE subject, centered, facing front / flat-on, filling roughly 80% of the frame with even margin on all sides.
- High resolution, crisp edges, fully in frame, nothing cropped.

HARD RULES (do not violate):
- NO text, letters, numbers, labels, captions, arrows, or annotations anywhere in the image.
- Background MUST be pure solid white (#FFFFFF), perfectly uniform — no gradient, no texture, no border, no frame.
- NO drop shadow or cast shadow on the background behind the subject (soft shading INSIDE the subject is fine; shadow on the white is not).
- No watermark, no logo, no decorative elements.

Subject of this icon:
"""
