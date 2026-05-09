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
    assert "background:white" in out


def test_render_artifact_raster_uses_img() -> None:
    out = _render_artifact("data:image/jpeg;base64,XXXX", "raster")
    assert '<img src="data:image/jpeg;base64,XXXX"' in out


def test_status_md_empty_state() -> None:
    assert "no figure" in _status_md(EMPTY_STATE).lower()


def test_status_md_populated_state_includes_session_short_id() -> None:
    state = {
        "session_id": "0123456789abcdef" * 2,
        "kind": "raster",
        "revision": 3,
        "artifact": "...",
    }
    md = _status_md(state, routing_reason="multi-cell illustration")
    assert "01234567" in md
    assert "raster" in md
    assert "3" in md
    assert "multi-cell illustration" in md


def test_placeholder_html_constant() -> None:
    assert "Generate" in PLACEHOLDER_HTML
