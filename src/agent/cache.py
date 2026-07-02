"""Tiny file-based cache so repeat searches don't re-hit the APIs.

Entries live as JSON files in ``.cache/`` with a TTL (default 24 hours).
Anything that fails (corrupt file, no permissions) behaves like a cache
miss; caching must never be the reason a run breaks.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any

CACHE_DIR = os.environ.get("CACHE_DIR", ".cache")
TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", 24 * 3600))


def _path(kind: str, key: str) -> str:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return os.path.join(CACHE_DIR, f"{kind}-{digest}.json")


def get(kind: str, key: str) -> Any | None:
    """Return the cached value, or None if missing/expired/unreadable."""
    try:
        with open(_path(kind, key), encoding="utf-8") as fh:
            entry = json.load(fh)
        if time.time() - entry["at"] > TTL_SECONDS:
            return None
        return entry["data"]
    except Exception:
        return None


def put(kind: str, key: str, data: Any) -> None:
    """Store a JSON-serializable value. Failures are silently ignored."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(_path(kind, key), "w", encoding="utf-8") as fh:
            json.dump({"at": time.time(), "data": data}, fh)
    except Exception:
        pass
