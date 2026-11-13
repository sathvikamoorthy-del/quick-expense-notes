import pytest

from app.cache.memory import MemoryCache


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def test_stores_and_returns_values_and_counts_hits_and_misses():
    cache: MemoryCache[str] = MemoryCache()
    cache.set("a", "1")
    assert cache.get("a") == "1" and cache.get("b") is None
    stats = cache.stats()
    assert (stats.hits, stats.misses, stats.size) == (1, 1, 1)


def test_entries_expire_after_their_time_to_live():
    clock = Clock()
    cache: MemoryCache[str] = MemoryCache(ttl_seconds=10, now=clock)
    cache.set("a", "1")
    cache.set("b", "2", ttl_seconds=60)
    clock.t += 11
    assert cache.get("a") is None and cache.get("b") == "2"
    assert cache.stats().size == 1


def test_the_least_recently_used_entry_goes_first_when_full():
    cache: MemoryCache[str] = MemoryCache(max_entries=2)
    cache.set("a", "1")
    cache.set("b", "2")
    cache.get("a")  # a is now more recent than b
    cache.set("c", "3")
    assert cache.get("b") is None and cache.get("a") == "1" and cache.get("c") == "3"


def test_setting_an_existing_key_replaces_it_and_refreshes_its_time():
    clock = Clock()
    cache: MemoryCache[str] = MemoryCache(ttl_seconds=10, now=clock)
    cache.set("a", "1")
    clock.t += 8
    cache.set("a", "2")
    clock.t += 8
    assert cache.get("a") == "2"


def test_delete_delete_prefix_and_clear():
    cache: MemoryCache[int] = MemoryCache()
    for key in ("t1|u1|/a", "t1|u1|/b", "t2|u1|/a"):
        cache.set(key, 1)
    assert cache.delete("t2|u1|/a") is True and cache.delete("missing") is False
    assert cache.delete_prefix("t1|") == 2
    cache.set("x", 1)
    cache.clear()
    assert cache.stats().size == 0


def test_a_cache_needs_room_for_at_least_one_entry():
    with pytest.raises(ValueError):
        MemoryCache(max_entries=0)
