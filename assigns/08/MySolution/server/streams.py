"""Process-local table of open Queen streams.

Each entry stores the current *unforced* LAMBDA3 stream value.  queens.next
forces at most ``limit`` cells under the entry's lock and stores the tail, so
one request's update is atomic.  Exhausted streams drop their LAMBDA3 state
immediately and keep only a small tombstone so later ``next`` calls can still
answer ``events: [], done: true`` until the tombstone expires.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field

from solver import queens

STREAM_TTL_SECONDS = 600        # inactivity lifetime of an open stream
MAX_OPEN_STREAMS = 64           # simultaneous open streams per process
MIN_LIMIT, MAX_LIMIT = 1, 32


class UnknownStream(LookupError):
    """Stream id never existed, was closed, or expired."""


class TooManyStreams(RuntimeError):
    pass


@dataclass
class _Entry:
    size: int
    stream: object | None          # unforced LAMBDA3 Strm, None once exhausted
    last_used: float
    lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def exhausted(self) -> bool:
        return self.stream is None


class StreamTable:
    def __init__(self, clock=time.monotonic, ttl: float = STREAM_TTL_SECONDS,
                 max_open: int = MAX_OPEN_STREAMS):
        self._clock, self._ttl, self._max = clock, ttl, max_open
        self._entries: dict[str, _Entry] = {}
        self._lock = threading.Lock()

    # -- housekeeping ------------------------------------------------------
    def sweep(self) -> int:
        """Drop entries idle longer than the TTL; returns how many."""
        now = self._clock()
        with self._lock:
            dead = [k for k, e in self._entries.items() if now - e.last_used > self._ttl]
            for k in dead:
                del self._entries[k]
        return len(dead)

    def __len__(self) -> int:
        return len(self._entries)

    def live_count(self) -> int:
        return sum(1 for e in self._entries.values() if not e.exhausted)

    def _get(self, stream_id: str) -> _Entry:
        self.sweep()
        with self._lock:
            entry = self._entries.get(stream_id)
        if entry is None:
            raise UnknownStream(stream_id)
        return entry

    # -- operations --------------------------------------------------------
    def open(self, size: int) -> str:
        self.sweep()
        stream = queens.open_stream(size)          # validated, NOT forced
        with self._lock:
            if self.live_count() >= self._max:
                raise TooManyStreams()
            stream_id = str(uuid.uuid4())
            self._entries[stream_id] = _Entry(size, stream, self._clock())
        return stream_id

    def next(self, stream_id: str, limit: int) -> tuple[list[dict], bool]:
        entry = self._get(stream_id)
        with entry.lock:
            entry.last_used = self._clock()
            events: list[dict] = []
            while not entry.exhausted and len(events) < limit:
                event, tail = queens.next_event(entry.stream)
                if event is None:                    # defensive: nil after done
                    entry.stream = None
                    break
                events.append(event)
                entry.stream = tail
                if event["event"] == "done":
                    entry.stream = None              # release LAMBDA3 state now
            return events, entry.exhausted

    def close(self, stream_id: str) -> None:
        self._get(stream_id)
        with self._lock:
            self._entries.pop(stream_id, None)
