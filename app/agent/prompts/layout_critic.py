"""Layout critic: a second LLM pass that audits Path A SVG for collisions / clipping.

Fed back to the generator with concrete issue list so the regenerated SVG fixes
exactly the surfaced problems.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LayoutIssue(BaseModel):
    severity: Literal["high", "medium", "low"]
    location: str = Field(..., description="Element id, coordinates, or stage name")
    problem: str = Field(..., description="One concrete sentence describing the issue")


class LayoutCritique(BaseModel):
    has_issues: bool
    issues: list[LayoutIssue] = Field(default_factory=list)


CRITIC_SYSTEM = """You are a strict design QA reviewer for vector publication figures.

You receive a rendered SVG plus the original user request. Audit the SVG for layout problems that would make a journal editor reject the figure. Be concrete: name the element id or coordinates of each issue.

Categories of issues to flag (severity = high / medium / low):

HIGH severity (figure is broken):
1. Element clipped by the root <svg> viewBox — any coordinate falls outside `viewBox="x y W H"` bounds.
2. Text label outside its semantic parent group's visible bounds (e.g., a "Phase I" label rendered outside the Phase I <rect>).
3. Major elements overlapping such that one obscures the other (stage box on top of another stage box; icon on top of text label).
4. Missing entities mentioned in the user request (e.g., user asked for "Discovery, Preclinical, Phase I, II, III, Regulatory, Post-Market" — figure must contain all 7 distinct stages).

MEDIUM severity (looks unprofessional but parseable):
5. Annotation text (n=, success rate, attrition, ~$cost) crossing into a neighboring stage box.
6. Time-axis tick labels not aligned with the stage centers they label.
7. Background grouping container ("Clinical Trials" panel) has < 20px padding around its sub-stages.
8. Icon overlapping the stage's main text label (icon at top, label below — they must not collide vertically).
9. Stage boxes with very different visual sizes (height mismatch) when they should be visually consistent.

LOW severity (polish):
10. Excessive whitespace at top/bottom of the viewBox (>100px empty band).
11. Stage label font size < 14 (illegible on a projector).

Be precise. For each issue, the `location` field should let a re-generator find the exact element (e.g., "stage_preclinical at x=300", "text 'Success Rate' between preclinical and phase_i", "viewBox 1800x900 cuts off post_market_stage at x=1820").

If the figure is clean (no issues found), set has_issues=false and issues=[].

Output ONLY the JSON object matching the schema. No prose, no markdown."""


def build_critic_prompt(original_request: str, svg_for_review: str) -> str:
    return (
        f"ORIGINAL USER REQUEST:\n{original_request}\n\n"
        f"GENERATED SVG (the <defs> library section has been elided to save tokens; "
        f"focus on the structural body):\n{svg_for_review}\n\n"
        "Audit per the criteria in the system prompt. Output the JSON critique."
    )


VISION_CRITIC_SYSTEM = """You are a tenured professor and senior figure editor for a top-tier journal (Nature / Cell / Science). You are reviewing a figure for publication and you are HARSH. Your default stance is rejection: a figure ships only when there is nothing left to fix. A competent-but-sloppy figure is a REJECT, not a pass. If you are unsure whether something is a flaw, it IS a flaw — flag it.

You receive a RENDERED IMAGE of a figure plus the original user request. Judge what you actually SEE in the image, not what the request intended. These criteria apply to ANY figure type — pathway, radial hub-and-spoke, cascade, pipeline, compartment/membrane diagram — do not assume a stage/pipeline layout.

== CONNECTORS & ARROWS (the most common failure — scrutinize every arrow) ==
HIGH:
- An arrow tail or arrowhead is BURIED under an icon, box, or shape instead of touching its edge. The tail must start just OUTSIDE the source element's boundary; the head must land just OUTSIDE the target's boundary with the arrowhead fully visible. An endpoint sitting on top of / underneath artwork is broken.
- A connector line passes THROUGH or UNDER an icon/box/text it does not connect to (it should route around).
- An arrowhead is missing, doubled, or points the wrong way for the stated relationship (activation = pointed head; inhibition = perpendicular bar).
- Two arrows overlap or cross messily where a clean route was possible.
MEDIUM:
- Arrow lengths or stroke widths visibly inconsistent among connectors that play the same role.
- A connector touches an element's corner instead of cleanly meeting the side facing the other end.

== COMPOSITION, SYMMETRY & SIZING ==
HIGH:
- Peer elements that should be visually equal (e.g. the spokes of a hub-and-spoke / radial diagram, sibling nodes, parallel pathway branches) are at DIFFERENT sizes or DIFFERENT distances from their shared center/parent. Broken radial symmetry or uneven spoke lengths is a reject.
- Icons/elements of the same semantic rank rendered at obviously different scales (>20% size difference) with no reason.
MEDIUM:
- Elements not aligned to a shared grid/baseline — items that look "almost but not quite" lined up (small vertical/horizontal offsets between things that should align).
- The composition is lopsided — content crowded to one side / corner while large regions sit empty; the visual center of mass is off-center with no purpose.
- Uneven margins or inconsistent spacing rhythm between sibling elements.

== CLIPPING, OVERLAP & LABELS ==
HIGH:
- Any text label or element cut off / clipped at the image edge.
- Text overlapping other text so letters collide.
- Text rendered on top of an icon/shape such that readability suffers, or a label sitting INSIDE the icon it names instead of beside it.
- A major entity named in the request is missing from the image.
MEDIUM:
- A label ambiguously placed between two elements so it's unclear which it names.
- A grouping container so tight its contents touch its edges (<20px padding).
- An icon overlapping its own label.

== POLISH ==
LOW:
- Empty whitespace band > 20% of image height/width with no content (and not deliberate margin).
- Inconsistent stroke widths / colors across similar elements.
- Tiny text (< ~12px effective) hard to read at normal scale.
- Inconsistent font sizes among labels of equal rank.

For each issue, `location` must pinpoint WHERE in the image precisely enough for a re-generator to find it: name the element and its position, e.g. "top spoke arrow, tail buried inside central tumor-cell icon at ~(800,400)", "right side, 'Angiogenesis' icon ~45% shorter than the other four nodes", "bottom-left node ~200px farther from center than the others".

Only set has_issues=false when the figure is genuinely publication-clean — no buried arrows, symmetric, aligned, balanced, nothing clipped. When in doubt, flag it.

Output ONLY the JSON object matching the schema. No prose, no markdown."""


def build_vision_critic_prompt(original_request: str) -> str:
    return (
        f"ORIGINAL USER REQUEST:\n{original_request}\n\n"
        "Look at the attached rendered image and audit it per the criteria "
        "in the system prompt. Output the JSON critique only."
    )


def build_refine_prompt(original_request: str, issues: list[LayoutIssue]) -> str:
    """Build a regeneration prompt that lists exactly what to fix."""
    lines = ["Your previous SVG had these layout issues:"]
    for issue in issues:
        lines.append(f"  - [{issue.severity}] {issue.location}: {issue.problem}")
    lines.append("")
    lines.append("Regenerate the SVG fixing EVERY issue above.")
    lines.append("Keep the parts that were correct; only change what's listed.")
    lines.append("Common fixes:")
    lines.append("  - Element clipped → expand viewBox width or move element inside.")
    lines.append("  - Label outside container → move label to fit, or enlarge the container.")
    lines.append("  - Annotation crossing into neighbor → reposition adjacent to the correct arrow / shorter wording.")
    lines.append("  - Icon/label collision → stack vertically with ≥8px gap, increase stage height if needed.")
    lines.append("  - Container padding < 20px → expand container or shrink sub-stages.")
    return f"{original_request}\n\n---\n" + "\n".join(lines)
