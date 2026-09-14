"""Shared helpers for intel engines — TTL cache + rate-limited fetch with fallbacks."""
import time
import threading
from typing import Any, Callable, Optional

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None

_cache: dict = {}
_locks: dict = {}
_lock = threading.Lock()

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CryptoIntel/4.1"}


def cached(key: str, ttl: float, fn: Callable[[], Any], default: Any = None) -> Any:
    """TTL cache — same key ko ttl seconds tak repeat nahi karta."""
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    with _lock:
        lock = _locks.setdefault(key, threading.Lock())
    if not lock.acquire(blocking=False):
        # another thread is fetching — return stale if available
        return hit[1] if hit else default
    try:
        value = fn()
        if value is not None:
            _cache[key] = (time.time(), value)
            return value
        return hit[1] if hit else default
    except Exception:
        return hit[1] if hit else default
    finally:
        lock.release()


def get_json(url: str, params: Optional[dict] = None, timeout: float = 12.0) -> Optional[Any]:
    if httpx is None:
        return None
    try:
        r = httpx.get(url, params=params, timeout=timeout, headers=UA)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None


def get_text(url: str, params: Optional[dict] = None, timeout: float = 12.0) -> Optional[str]:
    if httpx is None:
        return None
    try:
        r = httpx.get(url, params=params, timeout=timeout, headers=UA)
        if r.status_code == 200:
            return r.text
    except Exception:
        return None
    return None