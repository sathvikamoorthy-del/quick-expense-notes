"""In-memory cache: size-bounded (least recently used goes first) with a time-to-live per entry. One process only."""

import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

V = TypeVar("V")


@dataclass(frozen=True)
class CacheStats:
    hits: int
    misses: int
    size: int


class MemoryCache(Generic[V]):  # noqa: UP046  (PEP 695 syntax needs Python 3.12; the app supports 3.11)
    def __init__(
        self, max_entries: int = 500, ttl_seconds: float = 30.0, now: Callable[[], float] = time.monotonic
    ) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        self._items: OrderedDict[str, tuple[V, float]] = OrderedDict()
        self._max = max_entries
        self._ttl = ttl_seconds
        self._now = now
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> V | None:
        entry = self._items.get(key)
        if entry is None:
            self._misses += 1
            return None
        value, expires = entry
        if expires <= self._now():
            del self._items[key]
            self._misses += 1
            return None
        self._items.move_to_end(key)  # most recently used goes last
        self._hits += 1
        return value

    def set(self, key: str, value: V, ttl_seconds: float | None = None) -> None:
        self._items.pop(key, None)
        self._items[key] = (value, self._now() + (self._ttl if ttl_seconds is None else ttl_seconds))
        while len(self._items) > self._max:
            self._items.popitem(last=False)

    def delete(self, key: str) -> bool:
        return self._items.pop(key, None) is not None

    def delete_prefix(self, prefix: str) -> int:
        """Removes every key that starts with the prefix; returns how many."""
        keys = [k for k in self._items if k.startswith(prefix)]
        for key in keys:
            del self._items[key]
        return len(keys)

    def clear(self) -> None:
        self._items.clear()

    def stats(self) -> CacheStats:
        return CacheStats(self._hits, self._misses, len(self._items))
