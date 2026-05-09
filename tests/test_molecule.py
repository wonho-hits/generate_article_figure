"""Mocked tests for the Path B chemistry tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.clients.gemini import GeminiClient
from app.tools.molecule import (
    ChemistryExtraction,
    MoleculeRenderError,
    _render_rdkit_molecule,
    _wrap_for_validation,
    render_molecule,
)


# ── core RDKit + wrap ─────────────────────────────────────────────────────


def test_render_rdkit_aspirin_produces_svg() -> None:
    svg = _render_rdkit_molecule("CC(=O)Oc1ccccc1C(=O)O")
    assert svg.startswith("<?xml") or svg.startswith("<svg")
    assert "</svg>" in svg


def test_render_rdkit_invalid_smiles_raises() -> None:
    with pytest.raises(MoleculeRenderError, match="invalid SMILES"):
        _render_rdkit_molecule("nonsense---xyz")


def test_wrap_for_validation_produces_g_id_molecule() -> None:
    rdkit_svg = _render_rdkit_molecule("CC(=O)Oc1ccccc1C(=O)O")
    wrapped = _wrap_for_validation(rdkit_svg)
    assert wrapped.startswith("<svg")
    assert 'xmlns="http://www.w3.org/2000/svg"' in wrapped
    assert 'id="molecule"' in wrapped
    assert 'data-role="chemistry"' in wrapped
    assert "viewBox=" in wrapped
    assert "</svg>" in wrapped


def test_wrap_for_validation_passes_svg_validate() -> None:
    """The wrapped output must satisfy our SVG validator."""
    from app.tools.svg_validate import validate_and_canonicalize

    rdkit_svg = _render_rdkit_molecule("CC(=O)Oc1ccccc1C(=O)O")
    wrapped = _wrap_for_validation(rdkit_svg)
    canonical = validate_and_canonicalize(wrapped)
    assert "<svg" in canonical
    assert 'id="molecule"' in canonical


# ── render_molecule pipeline (mocked) ──────────────────────────────────────


@pytest.mark.asyncio
async def test_render_molecule_uses_extracted_smiles_directly() -> None:
    extraction = ChemistryExtraction(
        kind="molecule", smiles="CC(=O)Oc1ccccc1C(=O)O", name="aspirin"
    )
    client = MagicMock(spec=GeminiClient)
    client.generate_text = AsyncMock(return_value=extraction)

    svg = await render_molecule("draw aspirin", client=client)

    assert 'id="molecule"' in svg
    assert "<svg" in svg
    client.generate_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_render_molecule_falls_back_to_pubchem_when_no_smiles() -> None:
    extraction = ChemistryExtraction(kind="molecule", smiles=None, name="berberine")
    client = MagicMock(spec=GeminiClient)
    client.generate_text = AsyncMock(return_value=extraction)

    fake_compound = MagicMock()
    fake_compound.canonical_smiles = "CC(=O)Oc1ccccc1C(=O)O"  # use known-good SMILES
    with patch("app.tools.molecule.pcp.get_compounds", return_value=[fake_compound]):
        svg = await render_molecule("draw berberine", client=client)

    assert "<svg" in svg
    assert 'id="molecule"' in svg


@pytest.mark.asyncio
async def test_render_molecule_pubchem_miss_raises() -> None:
    extraction = ChemistryExtraction(kind="molecule", smiles=None, name="qzyq-fakecompound")
    client = MagicMock(spec=GeminiClient)
    client.generate_text = AsyncMock(return_value=extraction)

    with patch("app.tools.molecule.pcp.get_compounds", return_value=[]):
        with pytest.raises(MoleculeRenderError, match="could not"):
            await render_molecule("draw qzyq-fakecompound", client=client)


@pytest.mark.asyncio
async def test_render_molecule_pubchem_network_error_raises() -> None:
    extraction = ChemistryExtraction(kind="molecule", smiles=None, name="x")
    client = MagicMock(spec=GeminiClient)
    client.generate_text = AsyncMock(return_value=extraction)

    with patch(
        "app.tools.molecule.pcp.get_compounds", side_effect=RuntimeError("network down")
    ):
        with pytest.raises(MoleculeRenderError):
            await render_molecule("anything", client=client)


@pytest.mark.asyncio
async def test_render_molecule_reaction_kind_raises() -> None:
    extraction = ChemistryExtraction(
        kind="reaction", smiles="CC(=O)O.CCO>>CC(=O)OCC.O"
    )
    client = MagicMock(spec=GeminiClient)
    client.generate_text = AsyncMock(return_value=extraction)

    with pytest.raises(MoleculeRenderError, match="reaction"):
        await render_molecule("esterification", client=client)


@pytest.mark.asyncio
async def test_render_molecule_empty_prompt_raises() -> None:
    client = MagicMock(spec=GeminiClient)
    with pytest.raises(ValueError, match="empty"):
        await render_molecule("", client=client)
    with pytest.raises(ValueError, match="empty"):
        await render_molecule("   ", client=client)


@pytest.mark.asyncio
async def test_render_molecule_invalid_smiles_raises() -> None:
    extraction = ChemistryExtraction(kind="molecule", smiles="NOT_VALID_SMILES_???")
    client = MagicMock(spec=GeminiClient)
    client.generate_text = AsyncMock(return_value=extraction)

    with pytest.raises(MoleculeRenderError, match="invalid SMILES"):
        await render_molecule("anything", client=client)
