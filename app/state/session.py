"""Session store: holds the current artifact + history per figure session.

v1: in-memory, single-process, TTL-evicted.
v2 candidate: Redis-backed implementation conforming to the same Protocol.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import uuid4


@dataclass
class SessionEntry:
    session_id: str
    artifact: Any = None
    history: list[Any] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class SessionStore(Protocol):
    async def create(self) -> SessionEntry: ...
    async def get(self, session_id: str) -> SessionEntry | None: ...
    async def update(self, session_id: str, artifact: Any) -> SessionEntry | None: ...
    async def delete(self, session_id: str) -> bool: ...


class InMemorySessionStore:
    def __init__(self, *, ttl_seconds: int = 3600) -> None:
        self._ttl = ttl_seconds
        self._sessions: dict[str, SessionEntry] = {}
        self._lock = asyncio.Lock()

    def _evict_expired_locked(self) -> None:
        now = time.time()
        expired = [
            sid
            for sid, entry in self._sessions.items()
            if now - entry.updated_at > self._ttl
        ]
        for sid in expired:
            del self._sessions[sid]

    async def create(self) -> SessionEntry:
        async with self._lock:
            self._evict_expired_locked()
            entry = SessionEntry(session_id=str(uuid4()))
            self._sessions[entry.session_id] = entry
            return entry

    async def get(self, session_id: str) -> SessionEntry | None:
        async with self._lock:
            self._evict_expired_locked()
            return self._sessions.get(session_id)

    async def update(self, session_id: str, artifact: Any) -> SessionEntry | None:
        async with self._lock:
            self._evict_expired_locked()
            entry = self._sessions.get(session_id)
            if entry is None:
                return None
            if entry.artifact is not None:
                entry.history.append(entry.artifact)
            entry.artifact = artifact
            entry.updated_at = time.time()
            return entry

    async def delete(self, session_id: str) -> bool:
        async with self._lock:
            return self._sessions.pop(session_id, None) is not None
