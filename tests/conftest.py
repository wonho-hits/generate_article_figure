"""Pytest configuration.

Sets a fake GOOGLE_API_KEY before any app module is imported, so Settings()
construction does not fail when a developer's .env is missing or being shadowed.

Live tests (marked @pytest.mark.live) hit the real Gemini API and are
SKIPPED by default. Pass --run-live to opt in. They require a real
GOOGLE_API_KEY in the environment.
"""

from __future__ import annotations

import os

os.environ.setdefault("GOOGLE_API_KEY", "test-key-not-real")
os.environ.setdefault("LOG_LEVEL", "WARNING")

import pytest  # noqa: E402

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _bootstrap_app_state():
    """Ensure app.state.session_store is fresh per test.

    httpx.ASGITransport does not run FastAPI lifespan handlers, so the
    session store that lifespan would normally create is missing. Tests
    that hit routes like /generate need it set explicitly.
    """
    from app.main import app
    from app.state.session import InMemorySessionStore

    app.state.session_store = InMemorySessionStore()
    yield


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Run live tests that call the real Gemini API (cost incurred).",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "live: marks tests that call the real Gemini API (deselect with default run)",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if config.getoption("--run-live"):
        return
    skip_live = pytest.mark.skip(reason="live test (use --run-live to enable)")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
