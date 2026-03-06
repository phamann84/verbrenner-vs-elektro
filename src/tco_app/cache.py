from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CacheReadResult:
    data: dict[str, Any]
    age_seconds: float
    is_fresh: bool


class JsonTTLCache:
    def __init__(self, cache_dir: str | Path, default_ttl_seconds: int = 1200) -> None:
        self.cache_dir = Path(cache_dir)
        self.default_ttl_seconds = default_ttl_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_name(key: str) -> str:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
        return f"{digest}.json"

    def _path(self, key: str) -> Path:
        return self.cache_dir / self._safe_name(key)

    def set(self, key: str, data: dict[str, Any]) -> None:
        path = self._path(key)
        payload = {
            "ts": time.time(),
            "data": data,
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(tmp, path)

    def get(self, key: str, ttl_seconds: int | None = None) -> CacheReadResult | None:
        path = self._path(key)
        if not path.exists():
            return None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            ts = float(payload["ts"])
            data = payload["data"]
        except Exception:
            return None

        age = max(0.0, time.time() - ts)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        return CacheReadResult(data=data, age_seconds=age, is_fresh=age <= ttl)
