"""Style-preserving instruction prefix for raster edits (Path C inpainting)."""

from __future__ import annotations

INSTRUCTION_PREFIX = """You are editing an existing publication-quality scientific figure created in BioRender illustration style.

PRESERVE strictly:
- Overall composition, layout, and proportions of unedited regions.
- All other entities (cells, arrows, labels, badges) not mentioned in the instruction.
- Color palette, line weights, typography, white background.
- BioRender illustration style.

CHANGE only what the instruction below requests. If a separate mask image is also provided alongside this instruction, restrict ALL changes to the masked region — pixels that are WHITE in the mask are the only pixels you may modify; BLACK pixels must remain identical to the input image.

Now apply this instruction:
"""
