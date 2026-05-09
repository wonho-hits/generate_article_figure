"""InMemorySessionStore CRUD + TTL eviction."""

from __future__ import annotations

import asyncio
import time

import pytest

from app.state.session import InMemorySessionStore


@pytest.mark.asyncio
async def test_create_returns_unique_ids() -> None:
    store = InMemorySessionStore()
    a = await store.create()
    b = await store.create()
    assert a.session_id != b.session_id
    assert a.artifact is None
    assert a.history == []


@pytest.mark.asyncio
async def test_get_returns_none_for_missing() -> None:
    store = InMemorySessionStore()
    assert await store.get("does-not-exist") is None


@pytest.mark.asyncio
async def test_update_promotes_previous_artifact_to_history() -> None:
    store = InMemorySessionStore()
    entry = await store.create()

    await store.update(entry.session_id, "<svg>v1</svg>")
    after_v1 = await store.get(entry.session_id)
    assert after_v1 is not None
    assert after_v1.artifact == "<svg>v1</svg>"
    assert after_v1.history == []

    await store.update(entry.session_id, "<svg>v2</svg>")
    after_v2 = await store.get(entry.session_id)
    assert after_v2 is not None
    assert after_v2.artifact == "<svg>v2</svg>"
    assert after_v2.history == ["<svg>v1</svg>"]


@pytest.mark.asyncio
async def test_update_returns_none_for_missing_session() -> None:
    store = InMemorySessionStore()
    assert await store.update("nope", "data") is None


@pytest.mark.asyncio
async def test_delete_removes_entry() -> None:
    store = InMemorySessionStore()
    entry = await store.create()
    assert await store.delete(entry.session_id) is True
    assert await store.delete(entry.session_id) is False
    assert await store.get(entry.session_id) is None


@pytest.mark.asyncio
async def test_ttl_eviction_removes_stale_entries() -> None:
    store = InMemorySessionStore(ttl_seconds=1)
    entry = await store.create()
    # Force the entry to look old
    entry.updated_at = time.time() - 10
    # Any subsequent op triggers eviction
    assert await store.get(entry.session_id) is None


@pytest.mark.asyncio
async def test_concurrent_creates_do_not_collide() -> None:
    store = InMemorySessionStore()
    results = await asyncio.gather(*(store.create() for _ in range(50)))
    ids = {e.session_id for e in results}
    assert len(ids) == 50
