"""Path B tool: chemistry → SVG via RDKit, with optional PubChem name resolution.

Pipeline:
  prompt → LLM extraction → ChemistryExtraction (kind, smiles?, name?, title?)
         → if no smiles, resolve name via PubChemPy
         → RDKit renders 2D SVG
         → wrap in <g id="molecule"> for downstream svg_validate compatibility
"""

from __future__ import annotations

import re
from typing import Literal

import pubchempy as pcp
import structlog
from pydantic import BaseModel
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit.Chem.Draw import rdMolDraw2D

from app.agent.prompts.molecule_extract import EXTRACTION_SYSTEM
from app.clients.gemini import GeminiClient

logger = structlog.get_logger(__name__)

_RDKIT_NS = "http://www.rdkit.org/xml"
_XLINK_NS = "http://www.w3.org/1999/xlink"


class ChemistryExtraction(BaseModel):
    kind: Literal["molecule", "reaction"]
    smiles: str | None = None
    name: str | None = None
    title: str | None = None


class MoleculeRenderError(ValueError):
    """Chemistry extraction or RDKit rendering failed."""


async def render_molecule(
    prompt: str,
    *,
    client: GeminiClient | None = None,
) -> str:
    """Generate an SVG of a chemical structure from a natural-language prompt."""
    if not prompt or not prompt.strip():
        raise ValueError("prompt is empty")

    client = client or GeminiClient()
    extraction = await _extract_chemistry(prompt, client)
    logger.info(
        "path_b.extraction",
        kind=extraction.kind,
        has_smiles=extraction.smiles is not None,
        name=extraction.name,
    )

    if extraction.kind == "reaction":
        raise MoleculeRenderError(
            "reaction rendering is not implemented in v1; "
            "ask for a single molecule structure instead"
        )

    smiles = extraction.smiles
    if not smiles and extraction.name:
        smiles = _resolve_name_to_smiles(extraction.name)
    if not smiles:
        raise MoleculeRenderError(
            "could not extract a SMILES or resolve a compound name from the prompt"
        )

    rdkit_svg = _render_rdkit_molecule(smiles)
    return _wrap_for_validation(rdkit_svg)


async def _extract_chemistry(
    prompt: str, client: GeminiClient
) -> ChemistryExtraction:
    result = await client.generate_text(
        prompt,
        system=EXTRACTION_SYSTEM,
        response_schema=ChemistryExtraction,
    )
    if not isinstance(result, ChemistryExtraction):
        raise MoleculeRenderError(
            f"chemistry extraction returned wrong type: {type(result).__name__}"
        )
    return result


def _resolve_name_to_smiles(name: str) -> str | None:
    """Resolve a compound name to canonical SMILES via PubChem REST.

    Returns None on lookup failure or empty result. Network call.
    """
    try:
        compounds = pcp.get_compounds(name, "name")
    except Exception as exc:
        logger.warning("pubchem.lookup_failed", name=name, error=str(exc))
        return None
    if not compounds:
        return None
    smiles = compounds[0].canonical_smiles
    logger.info("pubchem.resolved", name=name, smiles=smiles[:60] if smiles else None)
    return smiles


def _render_rdkit_molecule(
    smiles: str, width: int = 600, height: int = 400
) -> str:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise MoleculeRenderError(f"invalid SMILES: {smiles!r}")
    AllChem.Compute2DCoords(mol)
    drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    return drawer.GetDrawingText()


_XML_DECL_RE = re.compile(r"^\s*<\?xml[^?]*\?>\s*", re.DOTALL)
_SVG_OPEN_RE = re.compile(r"<svg([^>]*)>", re.DOTALL)
_VIEWBOX_ATTR_RE = re.compile(r'viewBox="([^"]+)"')


def _wrap_for_validation(rdkit_svg: str) -> str:
    """Replace RDKit's <svg>...</svg> wrapper with our standard skeleton.

    Keeps RDKit's internal content (paths, text, ellipses) but ensures the root
    <svg> declares only the namespaces we need (svg, rdkit, xlink) and contains
    a <g id="molecule"> wrapper that satisfies svg_validate's structural rules.
    """
    cleaned = _XML_DECL_RE.sub("", rdkit_svg).strip()

    open_match = _SVG_OPEN_RE.search(cleaned)
    if not open_match:
        raise MoleculeRenderError("RDKit SVG missing <svg> opening tag")
    inner_start = open_match.end()
    close_idx = cleaned.rfind("</svg>")
    if close_idx == -1:
        raise MoleculeRenderError("RDKit SVG missing </svg>")

    svg_attrs = open_match.group(1)
    vb_match = _VIEWBOX_ATTR_RE.search(svg_attrs)
    viewbox = vb_match.group(1) if vb_match else "0 0 600 400"

    inner = cleaned[inner_start:close_idx].strip()

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:rdkit="{_RDKIT_NS}" xmlns:xlink="{_XLINK_NS}" '
        f'viewBox="{viewbox}">'
        '<g id="molecule" data-role="chemistry">'
        f"{inner}"
        "</g>"
        "</svg>"
    )
