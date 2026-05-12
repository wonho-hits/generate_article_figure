"""Tests for the hand-written bio/chem symbol library."""

from __future__ import annotations

from xml.etree import ElementTree as ET

import pytest

from app.domain.bio_symbols import (
    CATALOG,
    SYMBOLS,
    SymbolEntry,
    build_catalog_for_prompt,
    build_defs_block,
)


def test_symbols_and_catalog_have_matching_keys() -> None:
    """Every SYMBOLS key must appear in CATALOG and vice versa."""
    symbol_ids = set(SYMBOLS.keys())
    catalog_ids = {e.id for e in CATALOG}
    assert symbol_ids == catalog_ids, (
        f"mismatch: only in SYMBOLS={symbol_ids - catalog_ids}, "
        f"only in CATALOG={catalog_ids - symbol_ids}"
    )


def test_catalog_entries_are_well_formed() -> None:
    seen_ids: set[str] = set()
    for e in CATALOG:
        assert isinstance(e, SymbolEntry)
        assert e.id and e.id.replace("_", "").isalnum()
        assert e.id not in seen_ids, f"duplicate catalog id: {e.id}"
        seen_ids.add(e.id)
        assert e.name
        assert e.category in {
            "receptor", "enzyme", "small_molecule",
            "modification", "organelle", "structural", "general",
        }
        assert e.use_when
        assert e.default_w > 0 and e.default_h > 0


@pytest.mark.parametrize("symbol_id", list(SYMBOLS.keys()))
def test_each_symbol_parses_as_xml(symbol_id: str) -> None:
    raw = SYMBOLS[symbol_id]
    root = ET.fromstring(raw)
    # Tag is `symbol` (no namespace because we don't declare one)
    assert root.tag == "symbol"
    assert root.attrib.get("id") == symbol_id
    assert "viewBox" in root.attrib


def test_build_defs_block_contains_all_symbols() -> None:
    block = build_defs_block()
    assert block.startswith("<defs>")
    assert block.rstrip().endswith("</defs>")
    for sid in SYMBOLS:
        assert f'id="{sid}"' in block


def test_build_defs_block_is_valid_xml_when_wrapped_in_svg() -> None:
    """Sanity: defs block can be embedded in <svg> and the result parses."""
    block = build_defs_block()
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        f"{block}"
        '<g id="content"><rect/></g>'
        "</svg>"
    )
    ET.fromstring(svg)


def test_build_catalog_for_prompt_is_grouped_by_category() -> None:
    md = build_catalog_for_prompt()
    # Each category header appears
    for header in (
        "Receptors",
        "enzymes",
        "Ions and small molecules",
        "modifications",
        "Organelles",
        "Structural",
    ):
        assert header in md, f"missing category section: {header}"
    # Every symbol id appears
    for sid in SYMBOLS:
        assert f"`{sid}`" in md
