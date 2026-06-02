"""Smoke tests for the Gradio UI module.

Goal: catch import drift and basic Blocks-construction errors. The interactive
behavior is validated by manual use.
"""

from __future__ import annotations

import gradio as gr

from app.ui.gradio_app import (
    EMPTY_STATE,
    PLACEHOLDER_HTML,
    _render_artifact,
    _status_md,
    build_ui,
)


def test_build_ui_returns_blocks() -> None:
    ui = build_ui()
    assert isinstance(ui, gr.Blocks)


def test_render_artifact_svg_wraps_in_div() -> None:
    out = _render_artifact("<svg/>", "svg")
    assert "<svg/>" in out
    assert "fig-frame" in out


def test_render_artifact_raster_uses_img() -> None:
    out = _render_artifact("data:image/jpeg;base64,XXXX", "raster")
    assert '<img src="data:image/jpeg;base64,XXXX"' in out


def test_status_md_empty_state() -> None:
    assert "no figure" in _status_md(EMPTY_STATE).lower()


def test_status_md_uses_friendly_noun_not_jargon() -> None:
    """Status surfaces 'Illustration'/'Diagram', never session id / kind jargon."""
    raster = {
        "session_id": "0123456789abcdef" * 2,
        "kind": "raster",
        "revision": 3,
        "artifact": "...",
    }
    md = _status_md(raster)
    assert "Illustration" in md
    assert "3 refinements" in md
    # no internal identifiers leaked
    assert "01234567" not in md
    assert "raster" not in md

    vector = {"session_id": "abc", "kind": "svg", "revision": 0, "artifact": "..."}
    md2 = _status_md(vector)
    assert "Vector" in md2
    assert "refinement" not in md2  # revision 0 → no count shown


def test_mode_choices_hide_path_vocabulary() -> None:
    """Backend values are raster/mixed; labels never expose 'Path A/B/C/D'."""
    from app.ui.gradio_app import MODE_CHOICES

    labels = [label for label, _ in MODE_CHOICES]
    values = [value for _, value in MODE_CHOICES]
    assert values == ["raster", "mixed"]
    joined = " ".join(labels).lower()
    assert "path" not in joined and "raster" not in joined and "mixed" not in joined
    assert "Illustration" in " ".join(labels)
    assert "Vector" in " ".join(labels)


def test_placeholder_html_constant() -> None:
    assert "Generate" in PLACEHOLDER_HTML
