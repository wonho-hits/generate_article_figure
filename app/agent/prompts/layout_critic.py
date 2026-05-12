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


VISION_CRITIC_SYSTEM = """You are a strict design QA reviewer for vector publication figures.

You receive a RENDERED IMAGE of an SVG figure plus the original user request. Look at the image and identify visible layout problems. Be specific about what you see in the image.

HIGH severity (figure is broken):
1. Any text label or major element cut off / clipped at the image edge.
2. A text label rendered on top of another text label such that letters overlap.
3. A text label rendered on top of an unrelated shape such that readability is hurt.
4. A major entity the user requested is missing from the image.

MEDIUM severity (looks unprofessional):
5. Small annotation text (n=, %, $, sample size) clearly crossing the boundary of a stage box into a neighboring box.
6. Time-axis tick labels not visibly aligned UNDER the stage boxes they refer to.
7. A background grouping container (e.g., a "Clinical Trials" panel) so tight that its sub-stages touch its edges.
8. An icon inside a stage box visibly overlapping the stage's main text label.
9. Stage boxes in the same row at visibly different heights (>30% size mismatch).

LOW severity (polish):
10. Excessive empty whitespace bands (a band > 20% of the image height with no content).
11. Visible inconsistencies in stroke width across similar elements.
12. Tiny text (< ~12px effective) hard to read at normal viewing scale.

For each issue, `location` should pinpoint WHERE in the image (e.g., "right edge of image, Phase III box clipped", "between Discovery and Preclinical, success-rate label crosses Preclinical's top-left", "bottom 30% of image is empty").

If the image looks clean, set has_issues=false and issues=[].

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
