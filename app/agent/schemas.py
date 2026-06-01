"""Request / response / decision schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ArtifactKind = Literal["svg", "raster"]
"""SVG (Path A) or raster (Path C). Actual format (PNG/JPEG/WebP) is encoded
in the data URI's MIME type when kind='raster'."""

FigureKind = Literal["auto", "vector", "raster", "mixed"]
"""Caller's preference. "auto" → router decides. "vector"→A, "raster"→C,
"mixed"→D (vector backbone + generated raster icons)."""

RoutingPath = Literal["A", "B", "C", "D"]
"""A=vector schematic, B=RDKit chemistry, C=raster illustration,
D=mixed vector backbone + generated raster icons."""


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Natural-language description of the figure")
    figure_kind: FigureKind = Field("auto", description="auto | vector | raster")


class RoutingDecision(BaseModel):
    """Structured output from the router LLM."""

    path: RoutingPath
    reason: str = Field(..., min_length=1)


class GenerateResult(BaseModel):
    session_id: str
    artifact: str
    """SVG XML when kind='svg'; data URI ('data:image/<png|jpeg|...>;base64,...') when kind='raster'."""

    kind: ArtifactKind
    routing_reason: str | None = None


class EditRequest(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=2000)
    mask: str | None = Field(
        None,
        description=(
            "Optional base64-encoded PNG mask. Industry convention: "
            "white pixels = region to edit; black pixels = region to preserve. "
            "Same dimensions as the source image recommended."
        ),
    )


class EditResult(BaseModel):
    session_id: str
    artifact: str  # data URI
    kind: ArtifactKind
    revision: int
    """Number of edits applied to this session, including this one. 1 = first edit."""
